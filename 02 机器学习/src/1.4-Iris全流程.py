"""
1.4 Iris 数据集全流程（EDA -> 训练 3 种模型 -> 对比评估）
============================================================
学习目标：
  1. 完整走一遍 ML 标准流程：EDA -> 划分 -> 训练 -> 评估 -> 对比
  2. 对比逻辑回归、KNN、SVM 三种模型在 Iris 上的表现
  3. 理解不同模型的特点差异

流程概览：
  Step 1: EDA（探索性数据分析）-- 摸底数据
  Step 2: 数据划分 -- 训练集/测试集
  Step 3: 标准化 -- 距离类算法必须做
  Step 4: 训练 3 种模型 -- LR、KNN、SVM
  Step 5: 评估与对比 -- 准确率、混淆矩阵
  Step 6: 可视化 -- 决策边界对比
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from matplotlib.font_manager import fontManager, FontProperties
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score, confusion_matrix
import os

# 配置中文字体
_cjk_font_path = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
if os.path.exists(_cjk_font_path):
    fontManager.addfont(_cjk_font_path)
    _font_name = FontProperties(fname=_cjk_font_path).get_name()
    matplotlib.rcParams['font.sans-serif'] = [_font_name]
    matplotlib.rcParams['axes.unicode_minus'] = False

np.random.seed(42)

# ============================================================
# Step 1: EDA -- 探索性数据分析
# ============================================================
print("=" * 60)
print("Step 1: EDA -- 探索性数据分析")
print("=" * 60)

iris = load_iris()
X = iris.data        # (150, 4)
y = iris.target       # (150,)
feature_names = iris.feature_names
target_names = list(iris.target_names)

print(f"数据形状: {X.shape}")
print(f"特征: {feature_names}")
print(f"类别: {target_names}")
print(f"各类样本数: {np.bincount(y)}")
print(f"\n各特征统计摘要:")
print(f"{'特征':25s} {'均值':>8s} {'标准差':>8s} {'最小值':>8s} {'最大值':>8s}")
for i, name in enumerate(feature_names):
    print(f"{name:25s} {X[:, i].mean():>8.2f} {X[:, i].std():>8.2f} "
          f"{X[:, i].min():>8.2f} {X[:, i].max():>8.2f}")

# 特征间相关性
corr = np.corrcoef(X.T)
print(f"\n特征间相关系数矩阵:")
print(f"{'':25s}", end="")
for name in feature_names:
    print(f"{name[:10]:>12s}", end="")
print()
for i, name in enumerate(feature_names):
    print(f"{name:25s}", end="")
    for j in range(4):
        print(f"{corr[i, j]:>12.2f}", end="")
    print()

# 用前2个特征画散点图（花瓣长 vs 花瓣宽最易区分）
fig_eda, axes_eda = plt.subplots(1, 2, figsize=(14, 5))

# 散点图：花瓣长度 vs 花瓣宽度
colors = ['steelblue', 'crimson', 'orange']
for i in range(3):
    mask = y == i
    axes_eda[0].scatter(X[mask, 2], X[mask, 3], c=colors[i], s=30, alpha=0.6, label=target_names[i])
axes_eda[0].set_title("EDA: 花瓣长度 vs 花瓣宽度")
axes_eda[0].set_xlabel(feature_names[2])
axes_eda[0].set_ylabel(feature_names[3])
axes_eda[0].legend()
axes_eda[0].grid(True, alpha=0.3)

# 相关性热力图
im = axes_eda[1].imshow(corr, cmap='coolwarm', vmin=-1, vmax=1, aspect='auto')
axes_eda[1].set_xticks(range(4))
axes_eda[1].set_yticks(range(4))
axes_eda[1].set_xticklabels([n[:8] for n in feature_names], rotation=45, ha='right')
axes_eda[1].set_yticklabels([n[:8] for n in feature_names])
axes_eda[1].set_title("EDA: 特征相关性矩阵")
# 标注数值
for i in range(4):
    for j in range(4):
        axes_eda[1].text(j, i, f"{corr[i, j]:.2f}", ha='center', va='center',
                         color='white' if abs(corr[i, j]) > 0.5 else 'black', fontsize=9)
fig_eda.colorbar(im, ax=axes_eda[1])
plt.tight_layout()

_output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "outputs")
os.makedirs(_output_dir, exist_ok=True)
_eda_path = os.path.join(_output_dir, "1.4-EDA.png")
plt.savefig(_eda_path, dpi=150)
plt.close()
print(f"\nEDA 图表已保存至: {_eda_path}")

# ============================================================
# Step 2: 数据划分
# ============================================================
print("\n" + "=" * 60)
print("Step 2: 数据划分（80% 训练 / 20% 测试）")
print("=" * 60)

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
print(f"训练集: {X_train.shape}, 测试集: {X_test.shape}")
print(f"训练集各类: {np.bincount(y_train)}, 测试集各类: {np.bincount(y_test)}")

# ============================================================
# Step 3: 标准化（KNN 和 SVM 必须做，LR 也建议做）
# ============================================================
print("\n" + "=" * 60)
print("Step 3: 标准化")
print("=" * 60)

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)   # 用训练集拟合，再转换
X_test_scaled = scaler.transform(X_test)          # 用同样的参数转换测试集

print(f"标准化前 - 均值: {X_train.mean(axis=0).round(2)}, 标准差: {X_train.std(axis=0).round(2)}")
print(f"标准化后 - 均值: {X_train_scaled.mean(axis=0).round(2)}, 标准差: {X_train_scaled.std(axis=0).round(2)}")
print("注意: 只用训练集拟合 scaler，测试集用 transform（防止数据泄漏）")

# ============================================================
# Step 4: 训练 3 种模型
# ============================================================
print("\n" + "=" * 60)
print("Step 4: 训练 3 种模型")
print("=" * 60)

models = {
    '逻辑回归': LogisticRegression(max_iter=200, random_state=42),
    'KNN (K=5)': KNeighborsClassifier(n_neighbors=5),
    'SVM (RBF)': SVC(kernel='rbf', C=1.0, gamma='scale', random_state=42),
}

results = {}
for name, model in models.items():
    model.fit(X_train_scaled, y_train)
    y_train_pred = model.predict(X_train_scaled)
    y_test_pred = model.predict(X_test_scaled)
    train_acc = accuracy_score(y_train, y_train_pred)
    test_acc = accuracy_score(y_test, y_test_pred)
    results[name] = {
        'model': model,
        'train_acc': train_acc,
        'test_acc': test_acc,
        'y_pred': y_test_pred,
    }
    print(f"  {name:12s}: 训练集 {train_acc:.2%} | 测试集 {test_acc:.2%}")

# ============================================================
# Step 5: 评估与对比
# ============================================================
print("\n" + "=" * 60)
print("Step 5: 评估与对比")
print("=" * 60)

print(f"\n{'模型':12s} {'训练集准确率':>12s} {'测试集准确率':>12s} {'过拟合差距':>12s}")
print("-" * 50)
for name, res in results.items():
    gap = res['train_acc'] - res['test_acc']
    print(f"{name:12s} {res['train_acc']:>12.2%} {res['test_acc']:>12.2%} {gap:>12.2%}")

print("\n混淆矩阵（测试集）:")
for name, res in results.items():
    cm = confusion_matrix(y_test, res['y_pred'])
    print(f"\n  {name}:")
    print(f"  {'':15s} {'预测setosa':>12s} {'预测versicolor':>16s} {'预测virginica':>15s}")
    for i, species in enumerate(target_names):
        print(f"  {'真实'+species:15s} {cm[i,0]:>12d} {cm[i,1]:>16d} {cm[i,2]:>15d}")

# ============================================================
# Step 6: 可视化 -- 决策边界对比
# ============================================================
print("\n" + "=" * 60)
print("Step 6: 可视化决策边界（用花瓣长度 vs 花瓣宽度）")
print("=" * 60)

# 只用花瓣长度和宽度（第2、3列）来画2D决策边界
X_2d = X[:, [2, 3]]
X_train_2d, X_test_2d, y_train_2d, y_test_2d = train_test_split(
    X_2d, y, test_size=0.2, random_state=42, stratify=y
)
scaler_2d = StandardScaler()
X_train_2d_s = scaler_2d.fit_transform(X_train_2d)
X_test_2d_s = scaler_2d.transform(X_test_2d)

# 用2维数据重新训练3个模型（只为了画决策边界）
models_2d = {
    '逻辑回归': LogisticRegression(max_iter=200, random_state=42),
    'KNN (K=5)': KNeighborsClassifier(n_neighbors=5),
    'SVM (RBF)': SVC(kernel='rbf', C=1.0, gamma='scale', random_state=42),
}

fig, axes = plt.subplots(1, 3, figsize=(18, 5))

# 创建网格用于画决策边界
x_min, x_max = X_train_2d[:, 0].min() - 0.5, X_train_2d[:, 0].max() + 0.5
y_min, y_max = X_train_2d[:, 1].min() - 0.5, X_train_2d[:, 1].max() + 0.5
xx, yy = np.meshgrid(np.linspace(x_min, x_max, 200),
                     np.linspace(y_min, y_max, 200))

for idx, (name, model) in enumerate(models_2d.items()):
    model.fit(X_train_2d_s, y_train_2d)
    acc = model.score(X_test_2d_s, y_test_2d)

    # 预测网格点
    grid = scaler_2d.transform(np.c_[xx.ravel(), yy.ravel()])
    Z = model.predict(grid).reshape(xx.shape)

    # 画决策区域
    axes[idx].contourf(xx, yy, Z, alpha=0.3, cmap=matplotlib.colors.ListedColormap(colors))

    # 画训练数据点
    for i in range(3):
        mask = y_train_2d == i
        axes[idx].scatter(X_train_2d[mask, 0], X_train_2d[mask, 1],
                          c=colors[i], s=20, alpha=0.6, edgecolors='k', linewidths=0.5)

    axes[idx].set_title(f"{name}\n测试集准确率: {acc:.2%}（仅用花瓣2特征）")
    axes[idx].set_xlabel(feature_names[2])
    axes[idx].set_ylabel(feature_names[3])
    print(f"  {name:12s} (2特征): 测试集 {acc:.2%}")

print(f"\n注意：Step 5 用4个特征评估（正式结果），Step 6 仅用2个特征画图（可视化用），两者准确率可能不同。")

# 添加图例
from matplotlib.lines import Line2D
legend_elements = [Line2D([0], [0], marker='o', color='w', markerfacecolor=colors[i],
                          markersize=8, label=target_names[i]) for i in range(3)]
fig.legend(handles=legend_elements, loc='lower center', ncol=3, fontsize=10)

plt.tight_layout(rect=[0, 0.05, 1, 1])
_output_path = os.path.join(_output_dir, "1.4-模型对比.png")
plt.savefig(_output_path, dpi=150)
plt.show()
print(f"\n模型对比图表已保存至: {_output_path}")
