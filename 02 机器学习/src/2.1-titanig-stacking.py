"""
2.1 Titanic Stacking（LR + RF + XGB -> LR 元模型）
=====================================================
学习目标：
  1. 完整走一遍 Stacking 流程：K折生成元特征 -> 元模型训练
  2. 第一层：LR + RF + XGB 三个多样性模型
  3. 第二层：LR 作为元模型
  4. 对比 Stacking 与单模型的准确率

核心流程：
  Step 1: 加载数据 + 特征工程
  Step 2: 训练3个基础模型（单模型基线）
  Step 3: K折交叉验证生成元特征（out-of-fold预测）
  Step 4: 训练元模型（第二层LR）
  Step 5: 对比评估
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
from matplotlib.font_manager import fontManager, FontProperties
import os

from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score

try:
    from xgboost import XGBClassifier
    HAS_XGB = True
except ImportError:
    HAS_XGB = False
    print("警告: xgboost 未安装，使用 sklearn 的 GradientBoosting 替代 XGB")

import seaborn as sns

# 配置中文字体
_cjk_font_path = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
if os.path.exists(_cjk_font_path):
    fontManager.addfont(_cjk_font_path)
    _font_name = FontProperties(fname=_cjk_font_path).get_name()
    matplotlib.rcParams['font.sans-serif'] = [_font_name]
    matplotlib.rcParams['axes.unicode_minus'] = False

np.random.seed(42)

# ============================================================
# Step 1: 加载 Titanic 数据 + 特征工程
# ============================================================
print("=" * 60)
print("Step 1: 加载数据 + 特征工程")
print("=" * 60)

# 使用 seaborn 内置的 Titanic 数据集
titanic = sns.load_dataset('titanic')
print(f"原始数据形状: {titanic.shape}")
print(f"列: {list(titanic.columns)}")

# --- 特征工程 ---
df = pd.DataFrame()

# Pclass: 船舱等级（1=头等, 2=二等, 3=三等），保留原值
df['pclass'] = titanic['pclass']

# Sex: 性别，转为 0/1
df['sex'] = (titanic['sex'] == 'male').astype(int)

# Age: 年龄，用中位数填充缺失值
df['age'] = titanic['age'].fillna(titanic['age'].median())

# SibSp + Parch -> 家庭规模特征
df['family_size'] = titanic['sibsp'] + titanic['parch'] + 1
df['is_alone'] = (df['family_size'] == 1).astype(int)

# Fare: 票价，用中位数填充
df['fare'] = titanic['fare'].fillna(titanic['fare'].median())

# Embarked: 登船港口，One-Hot 编码
embarked = pd.get_dummies(titanic['embarked'], prefix='embarked', dummy_na=False).astype(int)
df = pd.concat([df, embarked], axis=1)

# 标签
y = titanic['survived'].values
X = df.values

print(f"特征工程后: X {X.shape}, y {y.shape}")
print(f"特征: {list(df.columns)}")
print(f"存活率: {y.mean():.1%}")
print("-" * 60)

# --- 标准化（LR 需要，RF/XGB 不需要但不会有坏影响）---
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# 划分训练集/测试集
from sklearn.model_selection import train_test_split
X_train, X_test, y_train, y_test = train_test_split(
    X_scaled, y, test_size=0.2, random_state=42, stratify=y
)
print(f"训练集: {X_train.shape}, 测试集: {X_test.shape}")

# ============================================================
# Step 2: 训练3个基础模型（单模型基线）
# ============================================================
print("\n" + "=" * 60)
print("Step 2: 单模型基线")
print("=" * 60)

# 定义3个基础模型
base_models = {
    'LR': LogisticRegression(max_iter=500, random_state=42),
    'RF': RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42),
    'XGB': XGBClassifier(n_estimators=100, max_depth=4, learning_rate=0.1,
                          eval_metric='logloss',
                          random_state=42) if HAS_XGB
           else GradientBoostingClassifier(n_estimators=100, max_depth=4,
                                            learning_rate=0.1, random_state=42),
}

# 单模型 5 折交叉验证准确率
print("\n单模型 5 折交叉验证准确率:")
single_scores = {}
for name, model in base_models.items():
    scores = cross_val_score(model, X_train, y_train, cv=5, scoring='accuracy')
    single_scores[name] = scores.mean()
    print(f"  {name:4s}: {scores.mean():.4f} (+/- {scores.std():.4f})")

# ============================================================
# Step 3: K折交叉验证生成元特征（Stacking 核心）
# ============================================================
print("\n" + "=" * 60)
print("Step 3: K折交叉验证生成元特征")
print("=" * 60)

K = 5
skf = StratifiedKFold(n_splits=K, shuffle=True, random_state=42)

# 元特征矩阵：每个基础模型一列
n_train = X_train.shape[0]
n_models = len(base_models)
meta_train = np.zeros((n_train, n_models))

print(f"K={K} 折交叉验证，生成 {n_train}×{n_models} 元特征矩阵\n")

for fold_idx, (train_idx, val_idx) in enumerate(skf.split(X_train, y_train)):
    print(f"  Fold {fold_idx + 1}/{K}: 训练{len(train_idx)}个, 验证{len(val_idx)}个")
    X_tr, X_val = X_train[train_idx], X_train[val_idx]
    y_tr, y_val = y_train[train_idx], y_train[val_idx]

    for model_idx, (name, model) in enumerate(base_models.items()):
        # 每折重新创建模型（避免复用）
        from sklearn.base import clone
        m = clone(model)
        m.fit(X_tr, y_tr)
        # 预测验证集（概率，取正类概率）
        if hasattr(m, 'predict_proba'):
            meta_train[val_idx, model_idx] = m.predict_proba(X_val)[:, 1]
        else:
            meta_train[val_idx, model_idx] = m.predict(X_val)

print(f"\n元特征矩阵形状: {meta_train.shape}")
print(f"元特征示例（前5行）:")
print(f"  {'':4s}  {'LR':>8s}  {'RF':>8s}  {'XGB':>8s}  | {'y':>4s}")
for i in range(5):
    print(f"  样本{i+1}  {meta_train[i,0]:>8.4f}  {meta_train[i,1]:>8.4f}  {meta_train[i,2]:>8.4f}  | {y_train[i]:>4d}")

# ============================================================
# Step 4: 训练元模型（第二层 LR）
# ============================================================
print("\n" + "=" * 60)
print("Step 4: 训练元模型（第二层逻辑回归）")
print("=" * 60)

meta_model = LogisticRegression(max_iter=500, random_state=42)

# 元模型的 5 折交叉验证准确率
meta_cv_scores = cross_val_score(meta_model, meta_train, y_train, cv=5, scoring='accuracy')
print(f"Stacking 元模型 5 折交叉验证准确率: {meta_cv_scores.mean():.4f} (+/- {meta_cv_scores.std():.4f})")

# 用全部元特征训练最终的元模型
meta_model.fit(meta_train, y_train)

# 用全部训练数据重新训练基础模型（最终用的）
print("\n用全部训练数据重新训练基础模型...")
final_base_models = {}
for name, model in base_models.items():
    from sklearn.base import clone
    m = clone(model)
    m.fit(X_train, y_train)
    final_base_models[name] = m

# ============================================================
# Step 5: 对比评估
# ============================================================
print("\n" + "=" * 60)
print("Step 5: 测试集对比评估")
print("=" * 60)

# 单模型测试集准确率
print(f"\n{'模型':20s} {'CV准确率':>10s} {'测试集准确率':>12s}")
print("-" * 45)
for name, model in final_base_models.items():
    y_pred = model.predict(X_test)
    test_acc = accuracy_score(y_test, y_pred)
    print(f"{name:20s} {single_scores[name]:>10.4f} {test_acc:>12.4f}")

# Stacking 测试集准确率
# 先生成测试集的元特征
meta_test = np.zeros((X_test.shape[0], n_models))
for model_idx, (name, model) in enumerate(final_base_models.items()):
    if hasattr(model, 'predict_proba'):
        meta_test[:, model_idx] = model.predict_proba(X_test)[:, 1]
    else:
        meta_test[:, model_idx] = model.predict(X_test)

stacking_pred = meta_model.predict(meta_test)
stacking_acc = accuracy_score(y_test, stacking_pred)
print(f"{'Stacking (LR+RF+XGB->LR)':20s} {meta_cv_scores.mean():>10.4f} {stacking_acc:>12.4f}")

# ============================================================
# Step 6: 可视化
# ============================================================
print("\n" + "=" * 60)
print("Step 6: 可视化")
print("=" * 60)

fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# --- 图1：准确率对比柱状图 ---
model_names = list(base_models.keys()) + ['Stacking']
cv_scores = list(single_scores.values()) + [meta_cv_scores.mean()]
test_scores = [accuracy_score(y_test, final_base_models[n].predict(X_test)) for n in base_models.keys()]
test_scores.append(stacking_acc)

x_pos = np.arange(len(model_names))
bar_width = 0.35
axes[0].bar(x_pos - bar_width/2, cv_scores, bar_width, color='steelblue', label='CV准确率')
axes[0].bar(x_pos + bar_width/2, test_scores, bar_width, color='crimson', label='测试集准确率')

# 在柱子上标注数值
for i, (cv, test) in enumerate(zip(cv_scores, test_scores)):
    axes[0].text(i - bar_width/2, cv + 0.005, f'{cv:.3f}', ha='center', fontsize=8)
    axes[0].text(i + bar_width/2, test + 0.005, f'{test:.3f}', ha='center', fontsize=8)

axes[0].set_xticks(x_pos)
axes[0].set_xticklabels(model_names)
axes[0].set_title("Stacking vs 单模型准确率对比")
axes[0].set_ylabel("准确率")
axes[0].legend()
axes[0].grid(True, alpha=0.3, axis='y')
axes[0].set_ylim(0.7, 0.85)

# --- 图2：元特征可视化（LR vs RF vs XGB 的预测概率散点图）---
colors = ['steelblue' if y == 0 else 'crimson' for y in y_train]
axes[1].scatter(meta_train[:, 0], meta_train[:, 1], c=colors, s=15, alpha=0.5)
axes[1].set_xlabel('LR 预测概率')
axes[1].set_ylabel('RF 预测概率')
axes[1].set_title('元特征空间（LR预测 vs RF预测）\n蓝=未存活, 红=存活')
axes[1].grid(True, alpha=0.3)

from matplotlib.lines import Line2D
legend_elements = [Line2D([0], [0], marker='o', color='w', markerfacecolor='steelblue',
                          markersize=8, label='未存活'),
                   Line2D([0], [0], marker='o', color='w', markerfacecolor='crimson',
                          markersize=8, label='存活')]
axes[1].legend(handles=legend_elements)

plt.tight_layout()
_output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "outputs")
os.makedirs(_output_dir, exist_ok=True)
_output_path = os.path.join(_output_dir, "2.1-Titanic-Stacking结果.png")
plt.savefig(_output_path, dpi=150)
plt.show()
print(f"\n图表已保存至: {_output_path}")

# ============================================================
# 总结
# ============================================================
print("\n" + "=" * 60)
print("总结")
print("=" * 60)
best_single = max(single_scores.values())
improvement = meta_cv_scores.mean() - best_single
print(f"""
单模型最佳 CV 准确率: {best_single:.4f} ({max(single_scores, key=single_scores.get)})
Stacking CV 准确率:    {meta_cv_scores.mean():.4f}
提升:                 {improvement:+.4f} ({improvement/best_single*100:+.2f}%)

关键发现:
  1. Stacking 通常比单模型提升 1~3%（本数据集较小，提升可能有限）
  2. 三个基础模型有多样性：LR(线性) + RF(Bagging) + XGB(Boosting)
  3. 元模型用简单的逻辑回归，防止过拟合
  4. K折交叉验证保证元特征是 out-of-fold 预测，无数据泄漏
""")
