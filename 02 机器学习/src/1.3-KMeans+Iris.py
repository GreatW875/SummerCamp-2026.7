"""
1.3 手写 K-Means + Iris 聚类可视化
====================================
学习目标：
  1. 不用 sklearn 的 KMeans，纯 NumPy 实现 K-Means
  2. 在 Iris 数据集上跑聚类，并与真实标签对比
  3. 画手肘法选 K 值，画聚类结果可视化

核心公式回顾：
  - 距离：     d(a, b) = sqrt(sum((a - b)^2))    （欧氏距离）
  - 分配：     每个样本归入最近的中心所在簇
  - 更新：     中心 = 该簇所有样本的均值
  - 损失：     WCSS = sum(每个样本到其簇中心的距离平方)  （簇内距离和）
  - 重复至收敛

注意：
  - K-Means 是无监督学习，不使用真实标签来训练
  - 但 Iris 有标签，可以用来"事后对比"看聚类效果
  - 距离算法必须先标准化
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from matplotlib.font_manager import fontManager, FontProperties
from sklearn.datasets import load_iris
import os

# 配置中文字体，防止中文显示为方框
_cjk_font_path = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
if os.path.exists(_cjk_font_path):
    fontManager.addfont(_cjk_font_path)
    _font_name = FontProperties(fname=_cjk_font_path).get_name()
    matplotlib.rcParams['font.sans-serif'] = [_font_name]
    matplotlib.rcParams['axes.unicode_minus'] = False


# ============================================================
# 工具函数
# ============================================================
def euclidean_distance(a, b):
    """
    欧氏距离
    - a: (d,) 单个样本
    - b: (d,) 单个样本（或中心点）
    返回：标量
    """
    return np.sqrt(np.sum((a - b) ** 2))


def compute_distances(X, centers):
    """
    计算每个样本到每个中心的距离
    - X: (n, d) 所有样本
    - centers: (K, d) K个簇中心
    返回：distances (n, K)，第i行第j列 = 样本i到中心j的距离
    """
    # 广播：X (n,d) -> (n,1,d)，centers (K,d) -> (1,K,d)
    # 相减后平方求和 -> (n, K)
    distances = np.sqrt(((X[:, np.newaxis, :] - centers[np.newaxis, :, :]) ** 2).sum(axis=2))
    return distances


def initialize_centers(X, K, seed=42):
    """
    随机初始化：从数据中随机选 K 个样本作为初始中心
    """
    np.random.seed(seed)
    indices = np.random.choice(len(X), K, replace=False)
    return X[indices].copy()


def kmeans(X, K, max_iters=100, tol=1e-4, seed=42):
    """
    K-Means 主算法（纯 NumPy 实现）

    参数：
    - X: (n, d) 数据矩阵
    - K: 簇数
    - max_iters: 最大迭代次数
    - tol: 中心移动量小于此值则收敛
    - seed: 随机种子

    返回：
    - labels: (n,) 每个样本的簇标签
    - centers: (K, d) 最终簇中心
    - wcss_history: 每轮的簇内距离和
    """
    n, d = X.shape
    centers = initialize_centers(X, K, seed)
    wcss_history = []

    for iteration in range(max_iters):
        # --- Step 1: 分配 -- 每个样本归入最近的中心 ---
        distances = compute_distances(X, centers)      # (n, K)
        labels = np.argmin(distances, axis=1)           # (n,) 取最近中心的索引

        # --- 计算损失（WCSS = 簇内距离平方和）---
        wcss = 0.0
        for k in range(K):
            mask = labels == k
            if np.sum(mask) > 0:
                wcss += np.sum((X[mask] - centers[k]) ** 2)
        wcss_history.append(wcss)

        # --- Step 2: 更新 -- 中心移到簇内均值 ---
        new_centers = np.zeros_like(centers)
        for k in range(K):
            mask = labels == k
            if np.sum(mask) > 0:
                new_centers[k] = X[mask].mean(axis=0)
            else:
                new_centers[k] = centers[k]  # 空簇保留原中心

        # --- 检查收敛：中心移动量小于 tol ---
        shift = np.sqrt(np.sum((new_centers - centers) ** 2))
        centers = new_centers

        if shift < tol:
            print(f"  K={K}: 在第 {iteration + 1} 轮收敛 (中心移动 {shift:.6f} < {tol})")
            break

    # 最终再分配一次（确保标签和最终中心一致）
    distances = compute_distances(X, centers)
    labels = np.argmin(distances, axis=1)

    return labels, centers, wcss_history


def compute_wcss(X, labels, centers):
    """计算给定聚类结果的 WCSS"""
    wcss = 0.0
    for k in range(len(centers)):
        mask = labels == k
        if np.sum(mask) > 0:
            wcss += np.sum((X[mask] - centers[k]) ** 2)
    return wcss


# ============================================================
# 第一步：加载 Iris 数据并标准化
# ============================================================
iris = load_iris()
X_raw = iris.data        # (150, 4) 4个特征：花萼长/宽、花瓣长/宽
y_true = iris.target      # (150,) 真实标签（0=setosa, 1=versicolor, 2=virginica）
feature_names = iris.feature_names
target_names = iris.target_names

# 标准化（距离算法必须标准化！）
X_mean = X_raw.mean(axis=0)
X_std = X_raw.std(axis=0)
X = (X_raw - X_mean) / X_std   # 标准化后数据

print(f"数据形状: X {X.shape}")
print(f"特征: {feature_names}")
print(f"类别: {list(target_names)}")
print(f"标准化: 均值={X.mean(axis=0).round(2)}, 标准差={X.std(axis=0).round(2)}")
print("-" * 60)

# ============================================================
# 第二步：手肘法选 K 值
# ============================================================
print("手肘法：尝试 K=1~8")
k_range = range(1, 9)
wcss_list = []

for k in k_range:
    labels, centers, _ = kmeans(X, k, max_iters=100, seed=42)
    wcss = compute_wcss(X, labels, centers)
    wcss_list.append(wcss)
    print(f"  K={k}: WCSS = {wcss:.4f}")

print("-" * 60)

# ============================================================
# 第三步：用 K=3 聚类（Iris 有 3 个真实类别）
# ============================================================
K = 3
print(f"使用 K={K} 进行聚类...")
labels, centers, wcss_history = kmeans(X, K, max_iters=100, seed=42)
print(f"最终 WCSS: {wcss_history[-1]:.4f}")
print(f"各簇样本数: {np.bincount(labels)}")
print("-" * 60)

# ============================================================
# 第四步：聚类结果 vs 真实标签对比
# ============================================================
# 注意：聚类标签的编号(0,1,2)和真实标签的编号不一定对应
# 需要做"标签对齐"：找出每个簇最可能对应的真实类别

print("聚类结果 vs 真实标签对比：")
for k in range(K):
    cluster_mask = labels == k
    true_in_cluster = y_true[cluster_mask]
    counts = np.bincount(true_in_cluster, minlength=3)
    best_match = np.argmax(counts)
    print(f"  簇 {k}: {np.sum(cluster_mask)} 个样本, "
          f"真实分布={counts}, 最可能是 '{target_names[best_match]}'")

# 计算准确率（需先对齐标签）
label_mapping = {}
for k in range(K):
    cluster_mask = labels == k
    true_in_cluster = y_true[cluster_mask]
    counts = np.bincount(true_in_cluster, minlength=3)
    label_mapping[k] = np.argmax(counts)

aligned_labels = np.array([label_mapping[l] for l in labels])
acc = np.mean(aligned_labels == y_true)
print(f"\n聚类准确率（标签对齐后）: {acc:.2%}")
print("-" * 60)

# ============================================================
# 第五步：可视化
# ============================================================
fig, axes = plt.subplots(2, 2, figsize=(14, 11))

# --- 图1：手肘法 ---
axes[0][0].plot(list(k_range), wcss_list, 'o-', color='steelblue', linewidth=2, markersize=8)
axes[0][0].axvline(x=3, color='red', linestyle='--', alpha=0.5, label='K=3（拐点）')
axes[0][0].set_title("手肘法选 K 值")
axes[0][0].set_xlabel("K（簇数）")
axes[0][0].set_ylabel("WCSS（簇内距离平方和）")
axes[0][0].legend()
axes[0][0].grid(True, alpha=0.3)

# --- 图2：聚类损失下降曲线 ---
axes[0][1].plot(range(1, len(wcss_history) + 1), wcss_history, 'o-',
                color='crimson', linewidth=2, markersize=6)
axes[0][1].set_title(f"K={K} 聚类收敛过程（WCSS vs 迭代轮数）")
axes[0][1].set_xlabel("迭代轮数")
axes[0][1].set_ylabel("WCSS")
axes[0][1].grid(True, alpha=0.3)

# --- 图3：聚类结果散点图（用花瓣长 vs 花瓣宽，最易区分的两个特征）---
petal_length_idx = 2  # 花瓣长度
petal_width_idx = 3   # 花瓣宽度

colors = ['steelblue', 'crimson', 'orange']
for k in range(K):
    mask = labels == k
    species_idx = label_mapping[k]  # 该簇对应的真实类别索引，保证两图同色
    axes[1][0].scatter(X_raw[mask, petal_length_idx], X_raw[mask, petal_width_idx],
                       c=colors[species_idx], s=30, alpha=0.6,
                       label=f'{target_names[species_idx]} (簇{k})')
    # 画簇中心（反标准化回原始尺度）
    center_original = centers[k] * X_std + X_mean
    axes[1][0].scatter(center_original[petal_length_idx], center_original[petal_width_idx],
                       c=colors[species_idx], marker='X', s=200, edgecolors='black', linewidths=2)

axes[1][0].set_title(f"K-Means 聚类结果（K={K}）\n花瓣长度 vs 花瓣宽度")
axes[1][0].set_xlabel(feature_names[petal_length_idx])
axes[1][0].set_ylabel(feature_names[petal_width_idx])
axes[1][0].legend(fontsize=8)
axes[1][0].grid(True, alpha=0.3)

# --- 图4：真实标签散点图（对比用）---
for i in range(3):
    mask = y_true == i
    axes[1][1].scatter(X_raw[mask, petal_length_idx], X_raw[mask, petal_width_idx],
                       c=colors[i], s=30, alpha=0.6, label=target_names[i])

axes[1][1].set_title("真实标签分布（对比）\n花瓣长度 vs 花瓣宽度")
axes[1][1].set_xlabel(feature_names[petal_length_idx])
axes[1][1].set_ylabel(feature_names[petal_width_idx])
axes[1][1].legend(fontsize=8)
axes[1][1].grid(True, alpha=0.3)

plt.tight_layout()
_output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "outputs")
os.makedirs(_output_dir, exist_ok=True)
_output_path = os.path.join(_output_dir, "1.3-KMeans-Iris结果.png")
plt.savefig(_output_path, dpi=150)
plt.show()
print(f"\n图表已保存至: {_output_path}")
