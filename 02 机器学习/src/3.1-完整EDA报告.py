"""
3.1 House Prices 完整 EDA 报告
=====================================================
学习目标：
  1. 走通 EDA 五步走流程：全局概览 -> 目标变量 -> 单变量 -> 双变量 -> 缺失与异常
  2. 产出一份"待办清单"：分布问题、强相关特征、缺失模式、异常点
  3. 为后续特征工程（对数变换、缺失插补、异常剔除、冗余删除）提供依据

数据说明：
  优先读取本地 data/train.csv（Kaggle House Prices）；
  若不存在则通过 sklearn fetch_openml 自动下载 Ames Housing（同一数据源）。

核心流程：
  Step 1: 全局概览（shape / dtypes / describe）
  Step 2: 目标变量分析（分布 + 偏度 + log 变换对比 + QQ 图）
  Step 3: 缺失模式分析（缺失排行榜 + MNAR 判断）
  Step 4: 相关性分析（Top 特征 + 共线对）
  Step 5: 异常值检测（IQR 法）
  Step 6: 输出"待办清单"
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
from matplotlib.font_manager import fontManager, FontProperties
import seaborn as sns
from scipy import stats

# 配置中文字体
_cjk_font_path = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
if os.path.exists(_cjk_font_path):
    fontManager.addfont(_cjk_font_path)
    _font_name = FontProperties(fname=_cjk_font_path).get_name()
    matplotlib.rcParams['font.sans-serif'] = [_font_name]
    matplotlib.rcParams['axes.unicode_minus'] = False

np.random.seed(42)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, 'outputs')
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ============================================================
# Step 0: 加载数据
# ============================================================
def load_data():
    local_candidates = [
        os.path.join(BASE_DIR, 'data', 'train.csv'),
        os.path.join(BASE_DIR, 'data', 'house_prices_train.csv'),
    ]
    for path in local_candidates:
        if os.path.exists(path):
            print(f"使用本地数据: {path}")
            return pd.read_csv(path)

    print("本地未找到数据，通过 fetch_openml 下载 Ames Housing（约 1MB，仅首次下载）...")
    from sklearn.datasets import fetch_openml
    housing = fetch_openml(name="house_prices", version=1, as_frame=True)
    df = housing.frame
    # openml 中部分数值列被标为 category，尝试转回数值
    for col in df.columns:
        if df[col].dtype.name == 'category':
            converted = pd.to_numeric(df[col], errors='coerce')
            if converted.notna().mean() > 0.9:  # 90% 以上能转数值 -> 判定为数值列
                df[col] = converted
    return df


df = load_data()

# ============================================================
# Step 1: 全局概览 —— 拿到数据先"称体重、量身高"
# ============================================================
print("\n" + "=" * 60)
print("① 全局概览")
print("=" * 60)
num_cols = df.select_dtypes(include=[np.number]).columns
cat_cols = df.columns.difference(num_cols)
print(f"数据规模: {df.shape[0]} 行 x {df.shape[1]} 列")
print(f"数值特征: {len(num_cols)} 个 | 类别特征: {len(cat_cols)} 个")
print("\n数值特征描述性统计（前 8 列）:")
print(df[num_cols[:8]].describe().round(2).to_string())

# ============================================================
# Step 2: 目标变量分析 —— 先搞清楚"要预测的对象"
# ============================================================
print("\n" + "=" * 60)
print("② 目标变量 SalePrice 分析")
print("=" * 60)
y = df['SalePrice'].astype(float)
skew_raw = y.skew()
skew_log = np.log1p(y).skew()
print(f"偏度(原始)      = {skew_raw:.2f}   (>1 为明显右偏，少数豪宅拖长尾)")
print(f"偏度(log1p 后)  = {skew_log:.2f}   (接近 0 说明变换有效)")

# ============================================================
# Step 3: 缺失模式分析 —— 缺失排行榜 + 判断缺失类型
# ============================================================
print("\n" + "=" * 60)
print("③ 缺失模式分析")
print("=" * 60)
missing = df.isnull().sum()
missing = missing[missing > 0].sort_values(ascending=False)
missing_pct = (missing / len(df) * 100).round(1)
missing_tbl = pd.DataFrame({'缺失数': missing, '缺失比例%': missing_pct})
print(f"共 {len(missing)} 列存在缺失，Top 15:")
print(missing_tbl.head(15).to_string())
print("\n>> 判断: PoolQC/Alley/Fence 等高缺失列，缺失 = '没有该设施'(MNAR)，")
print("   缺失本身就是信息，应填 'None' 单独成类，而不是插补数值。")

# ============================================================
# Step 4: 相关性分析 —— 找"重点嫌疑人"和"冗余同伙"
# ============================================================
print("\n" + "=" * 60)
print("④ 相关性分析")
print("=" * 60)
num_df = df.select_dtypes(include=[np.number]).drop(columns=['Id'], errors='ignore')
corr = num_df.corr()
top_corr = corr['SalePrice'].drop('SalePrice').sort_values(
    key=lambda s: s.abs(), ascending=False)
print("与 SalePrice 相关性 Top 10:")
for name, val in top_corr.head(10).items():
    print(f"  {name:<18} {val:+.3f}")

# 特征间高共线对（|r| >= 0.8）
high_pairs = []
cols = corr.columns
for i in range(len(cols)):
    for j in range(i + 1, len(cols)):
        if abs(corr.iloc[i, j]) >= 0.8 and cols[i] != 'SalePrice' and cols[j] != 'SalePrice':
            high_pairs.append((cols[i], cols[j], corr.iloc[i, j]))
print("\n特征间高共线对 (|r| >= 0.8，信息重复可删一个):")
for a, b, v in sorted(high_pairs, key=lambda x: -abs(x[2])):
    print(f"  {a} ~ {b}: {v:+.3f}")

# ============================================================
# Step 5: 异常值检测 —— IQR 法（以 GrLivArea 为例）
# ============================================================
print("\n" + "=" * 60)
print("⑤ 异常值检测（IQR 法）")
print("=" * 60)
q1, q3 = df['GrLivArea'].quantile([0.25, 0.75])
iqr = q3 - q1
upper_bound = q3 + 1.5 * iqr
outliers = df[df['GrLivArea'] > upper_bound]
print(f"GrLivArea 上界 = Q3 + 1.5*IQR = {upper_bound:.0f} sqft")
print(f"超出上界的异常点: {len(outliers)} 个")
print(">> 重点关注: 面积 > 4000 但售价偏低的样本（右下角的坑）:")
weird = df[(df['GrLivArea'] > 4000) & (df['SalePrice'] < 300000)]
print(weird[['GrLivArea', 'SalePrice']].to_string())

# ============================================================
# Step 6: 综合可视化（一张图 = 一份报告）
# ============================================================
fig, axes = plt.subplots(2, 3, figsize=(20, 11))

# (0,0) 目标变量原始分布
ax = axes[0, 0]
sns.histplot(y, kde=True, ax=ax, color='steelblue')
ax.set_title(f'① 目标变量分布（偏度={skew_raw:.2f}，右偏）', fontsize=13)
ax.set_xlabel('SalePrice')

# (0,1) log1p 变换后分布
ax = axes[0, 1]
sns.histplot(np.log1p(y), kde=True, ax=ax, color='seagreen')
ax.set_title(f'② log1p 变换后（偏度={skew_log:.2f}，接近正态）', fontsize=13)
ax.set_xlabel('log1p(SalePrice)')

# (0,2) QQ 图：检验变换后是否正态
ax = axes[0, 2]
stats.probplot(np.log1p(y), dist='norm', plot=ax)
ax.set_title('③ log 变换后 QQ 图（点越贴线越正态）', fontsize=13)

# (1,0) 缺失值 Top15
ax = axes[1, 0]
top_missing = missing_pct.head(15)
ax.barh(range(len(top_missing)), top_missing.values, color='salmon')
ax.set_yticks(range(len(top_missing)))
ax.set_yticklabels(top_missing.index, fontsize=9)
ax.invert_yaxis()
ax.set_xlabel('缺失比例 (%)')
ax.set_title('④ 缺失值 Top15（高缺失多为"没该设施"）', fontsize=13)

# (1,1) 相关性热力图（Top12 + SalePrice）
ax = axes[1, 1]
top_feats = top_corr.head(12).index.tolist() + ['SalePrice']
sns.heatmap(num_df[top_feats].corr(), annot=True, fmt='.2f', cmap='coolwarm',
            center=0, ax=ax, annot_kws={'size': 7}, cbar_kws={'shrink': 0.8},
            xticklabels=top_feats, yticklabels=top_feats)
ax.set_title('⑤ 与房价相关性 Top12 热力图', fontsize=13)
ax.tick_params(labelsize=8)

# (1,2) GrLivArea vs SalePrice 散点（标注异常）
ax = axes[1, 2]
ax.scatter(df['GrLivArea'], y, alpha=0.4, s=12, label='正常样本')
ax.scatter(outliers['GrLivArea'], outliers['SalePrice'], color='red', s=25,
           label=f'IQR 异常点 ({len(outliers)} 个)')
ax.axvline(upper_bound, color='red', linestyle='--', alpha=0.6)
ax.set_xlabel('GrLivArea 地上居住面积 (sqft)')
ax.set_ylabel('SalePrice')
ax.set_title('⑥ 面积 vs 房价（红点 = 异常点）', fontsize=13)
ax.legend()

fig.suptitle('House Prices 完整 EDA 报告', fontsize=16, fontweight='bold')
plt.tight_layout(rect=[0, 0, 1, 0.97])
out_path = os.path.join(OUTPUT_DIR, '3.1-EDA报告.png')
plt.savefig(out_path, dpi=150, bbox_inches='tight')
print(f"\n图表已保存: {out_path}")

# ============================================================
# 输出: EDA 待办清单（EDA 的真正产出）
# ============================================================
print("\n" + "=" * 60)
print("EDA 结论：待办清单（喂给下一步特征工程）")
print("=" * 60)
print(f"1. SalePrice 偏度 {skew_raw:.2f} -> log1p 后 {skew_log:.2f}"
      f"  -> 【变换】目标变量做 log1p，评估时用 RMSLE")
high_missing = missing_pct[missing_pct > 40].index.tolist()
print(f"2. 高缺失列 {high_missing}"
      f"  -> 【缺失】MNAR，填 'None'/0，缺失即信息")
print(f"3. GrLivArea 有 {len(weird)} 个'面积大售价低'异常点"
      f"  -> 【异常】直接删除，避免带歪模型")
if high_pairs:
    a, b, v = high_pairs[0]
    print(f"4. 共线对如 {a} ~ {b} (r={v:+.2f})"
          f"  -> 【冗余】保留一个，或做特征组合")
print(f"5. 强相关特征 {top_corr.head(5).index.tolist()}"
      f"  -> 【保留】建模重点特征")
