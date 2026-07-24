"""
1.1 手写线性回归（NumPy 实现 + 梯度下降）
==========================================
学习目标：
  1. 不用 sklearn，纯 NumPy 实现线性回归
  2. 理解梯度下降的每一步在做什么
  3. 画出损失下降曲线，直观看到"学习"过程

核心公式回顾：
  - 模型：     y_hat = X @ w + b
  - 损失(MSE)： L = (1/n) * sum((y_hat - y)^2)
  - 梯度：     dL/dw = (2/n) * X.T @ (y_hat - y)
               dL/db = (2/n) * sum(y_hat - y)
  - 更新：     w = w - lr * dL/dw
               b = b - lr * dL/db
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from matplotlib.font_manager import fontManager, FontProperties
import os

# 配置中文字体，防止中文显示为方框
_cjk_font_path = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
if os.path.exists(_cjk_font_path):
    fontManager.addfont(_cjk_font_path)
    _font_name = FontProperties(fname=_cjk_font_path).get_name()
    matplotlib.rcParams['font.sans-serif'] = [_font_name]
    matplotlib.rcParams['axes.unicode_minus'] = False

# ============================================================
# 第一步：造数据 —— 模拟 y = 3x + 2 + 噪声
# ============================================================
np.random.seed(42)  # 固定随机种子，保证结果可复现

n_samples = 200          # 样本数
X = np.random.uniform(-5, 5, size=n_samples)          # 生成 200 个均匀分布 x 值
true_w, true_b = 3.0, 2.0                               # 真实权重和偏置
noise = np.random.normal(0, 2, size=n_samples)         # 高斯噪声（正态分布）
y = true_w * X + true_b + noise                         # 真实标签

# 画一下原始数据，看看长什么样
fig, axes = plt.subplots(1, 3, figsize=(18, 5))

axes[0].scatter(X, y, s=10, alpha=0.6, color='steelblue')
axes[0].set_title("原始数据散点图\n(真实关系: y = 3x + 2 + 噪声)")
axes[0].set_xlabel("X")
axes[0].set_ylabel("y")
axes[0].grid(True, alpha=0.3)

# ============================================================
# 第二步：初始化参数
# ============================================================
w = np.random.randn()   # 随机初始化权重
b = 0.0                  # 偏置初始化为 0

learning_rate = 0.01     # 学习率（步长）
n_epochs = 100           # 训练轮数（遍历全部数据的次数）

loss_history = []        # 记录每轮的损失，用于画曲线

print(f"初始参数: w = {w:.4f}, b = {b:.4f}")
print(f"真实参数: w = {true_w}, b = {true_b}")
print(f"学习率: {learning_rate}, 训练轮数: {n_epochs}")
print("-" * 50)

# ============================================================
# 第三步：梯度下降训练循环
# ============================================================
for epoch in range(n_epochs):
    # --- 前向传播：算预测值 ---
    y_hat = w * X + b

    # --- 算损失（MSE）---
    loss = np.mean((y_hat - y) ** 2)
    loss_history.append(loss)

    # --- 算梯度 ---
    # dL/dw = (2/n) * sum((y_hat - y) * X)
    # dL/db = (2/n) * sum(y_hat - y)
    n = len(X)
    dw = (2 / n) * np.sum((y_hat - y) * X)
    db = (2 / n) * np.sum(y_hat - y)

    # --- 更新参数 ---
    w = w - learning_rate * dw
    b = b - learning_rate * db

    # 每 10 轮打印一次进度
    if (epoch + 1) % 10 == 0:
        print(f"Epoch {epoch + 1:3d} | Loss: {loss:10.4f} | w: {w:.4f} | b: {b:.4f}")

print("-" * 50)
print(f"训练完成: w = {w:.4f} (真实 {true_w}), b = {b:.4f} (真实 {true_b})")
print(f"最终 Loss: {loss_history[-1]:.4f}")

# ============================================================
# 第四步：可视化
# ============================================================

# --- 图1（已画）：原始数据散点图 ---

# --- 图2：损失下降曲线 ---
axes[1].plot(range(1, n_epochs + 1), loss_history, color='red', linewidth=2)
axes[1].set_title("损失下降曲线（MSE vs Epoch）")
axes[1].set_xlabel("Epoch（训练轮数）")
axes[1].set_ylabel("Loss（MSE）")
axes[1].grid(True, alpha=0.3)

# --- 图3：拟合效果 ---
axes[2].scatter(X, y, s=10, alpha=0.4, color='steelblue', label='原始数据')
# 画拟合直线
x_line = np.linspace(X.min(), X.max(), 100)
y_line = w * x_line + b
axes[2].plot(x_line, y_line, color='red', linewidth=2, label=f'拟合: y = {w:.2f}x + {b:.2f}')
# 画真实直线（虚线对比）
y_true_line = true_w * x_line + true_b
axes[2].plot(x_line, y_true_line, color='green', linewidth=2, linestyle='--', label=f'真实: y = {true_w}x + {true_b}')
axes[2].set_title("拟合效果对比")
axes[2].set_xlabel("X")
axes[2].set_ylabel("y")
axes[2].legend()
axes[2].grid(True, alpha=0.3)

plt.tight_layout()
_output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "outputs")
os.makedirs(_output_dir, exist_ok=True)
_output_path = os.path.join(_output_dir, "1.1-线性回归结果.png")
plt.savefig(_output_path, dpi=150)
plt.show()
print(f"\n图表已保存至: {_output_path}")
