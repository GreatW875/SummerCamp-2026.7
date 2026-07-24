"""
1.2 手写逻辑回归（NumPy 实现 + 对比 L2 正则化）
=================================================
学习目标：
  1. 不用 sklearn，纯 NumPy 实现逻辑回归
  2. 理解 Sigmoid + 交叉熵损失的梯度推导
  3. 对比加/不加 L2 正则化的效果（权重大小、决策边界、过拟合）

核心公式回顾：
  - 模型：       y_hat = sigmoid(X @ w + b)
  - 损失(CE)：   L = -(1/n) * sum[y*log(y_hat) + (1-y)*log(1-y_hat)]
  - 梯度：       dL/dw = (1/n) * X.T @ (y_hat - y)
                dL/db = (1/n) * sum(y_hat - y)
  - L2 正则化：  L_total = L + lambda * sum(w^2)
                dL/dw = (1/n) * X.T @ (y_hat - y) + 2 * lambda * w
  - 更新：       w = w - lr * dL/dw
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
# 工具函数
# ============================================================
def sigmoid(z):
    """Sigmoid 激活函数：将任意实数压缩到 (0, 1)"""
    # clip 防止 exp 溢出
    z = np.clip(z, -500, 500)
    return 1.0 / (1.0 + np.exp(-z))


def cross_entropy_loss(y_hat, y, w=None, l2_lambda=0.0):
    """
    计算交叉熵损失（可选 L2 正则化）
    - y_hat: 预测概率 (n,)
    - y:     真实标签 (n,)
    - w:     权重（L2 正则化用）
    - l2_lambda: L2 正则化系数
    """
    n = len(y)
    # 加 1e-8 防止 log(0)
    ce = -np.mean(y * np.log(y_hat + 1e-8) + (1 - y) * np.log(1 - y_hat + 1e-8))
    if l2_lambda > 0 and w is not None:
        ce += l2_lambda * np.sum(w ** 2)
    return ce


def train_logistic_regression(X, y, lr=0.1, n_epochs=1000, l2_lambda=0.0):
    """
    逻辑回归训练（梯度下降）
    - X: (n, d) 特征矩阵
    - y: (n,)  标签 {0, 1}
    - lr: 学习率
    - n_epochs: 训练轮数
    - l2_lambda: L2 正则化系数（0 = 不加正则化）

    返回：w, b, loss_history
    """
    n, d = X.shape
    w = np.zeros(d)   # 权重初始化为 0
    b = 0.0            # 偏置初始化为 0
    loss_history = []

    for epoch in range(n_epochs):
        # --- 前向传播 ---
        y_hat = sigmoid(X @ w + b)

        # --- 计算损失 ---
        loss = cross_entropy_loss(y_hat, y, w, l2_lambda)
        loss_history.append(loss)

        # --- 计算梯度 ---
        # 交叉熵 + Sigmoid 的梯度：dL/dw = (1/n) * X.T @ (y_hat - y)
        dw = (1 / n) * X.T @ (y_hat - y)
        db = (1 / n) * np.sum(y_hat - y)

        # --- L2 正则化项的梯度 ---
        if l2_lambda > 0:
            dw += 2 * l2_lambda * w   # L2 对 w 的梯度
            # b 不加正则化（习惯上不正则化偏置）

        # --- 更新参数 ---
        w = w - lr * dw
        b = b - lr * db

    return w, b, loss_history


def predict(X, w, b, threshold=0.5):
    """预测：概率 > threshold 判为 1，否则 0"""
    return (sigmoid(X @ w + b) >= threshold).astype(int)


def accuracy(y_pred, y_true):
    """计算准确率"""
    return np.mean(y_pred == y_true)


# ============================================================
# 第一步：造数据 -- 两个类别的二分类数据
# ============================================================
np.random.seed(42)

n_samples = 200  # 每类 100 个

# 类别 0：以 (2, 2) 为中心
X0 = np.random.randn(n_samples // 2, 2) + np.array([2, 2])
y0 = np.zeros(n_samples // 2)

# 类别 1：以 (-2, -2) 为中心
X1 = np.random.randn(n_samples // 2, 2) + np.array([-2, -2])
y1 = np.ones(n_samples // 2)

# 合并并打乱
X = np.vstack([X0, X1])
y = np.concatenate([y0, y1])
shuffle_idx = np.random.permutation(n_samples)
X = X[shuffle_idx]
y = y[shuffle_idx]

# 划分训练集 / 测试集（80% / 20%）
split = int(0.8 * n_samples)
X_train, X_test = X[:split], X[split:]
y_train, y_test = y[:split], y[split:]

print(f"数据形状: X_train {X_train.shape}, X_test {X_test.shape}")
print(f"训练集正类比例: {y_train.mean():.1%}")
print(f"测试集正类比例: {y_test.mean():.1%}")
print("-" * 60)

# ============================================================
# 第二步：训练 -- 对比无正则化 vs L2 正则化
# ============================================================
lr = 0.1
n_epochs = 500
l2_lambda = 0.5  # L2 正则化系数

# --- 模型 A：无正则化 ---
w_no_reg, b_no_reg, loss_no_reg = train_logistic_regression(
    X_train, y_train, lr=lr, n_epochs=n_epochs, l2_lambda=0.0
)

# --- 模型 B：L2 正则化 ---
w_l2, b_l2, loss_l2 = train_logistic_regression(
    X_train, y_train, lr=lr, n_epochs=n_epochs, l2_lambda=l2_lambda
)

# ============================================================
# 第三步：评估与对比
# ============================================================
train_pred_no = predict(X_train, w_no_reg, b_no_reg)
test_pred_no = predict(X_test, w_no_reg, b_no_reg)
train_pred_l2 = predict(X_train, w_l2, b_l2)
test_pred_l2 = predict(X_test, w_l2, b_l2)

print("模型对比结果：")
print(f"{'':20s} {'无正则化':>12s} {'L2正则化':>12s}")
print(f"{'权重 w':20s} {str(w_no_reg):>12s} {str(w_l2):>12s}")
print(f"{'偏置 b':20s} {b_no_reg:>12.4f} {b_l2:>12.4f}")
print(f"{'权重平方和 ||w||²':20s} {np.sum(w_no_reg**2):>12.4f} {np.sum(w_l2**2):>12.4f}")
print(f"{'训练集准确率':20s} {accuracy(train_pred_no, y_train):>12.2%} {accuracy(train_pred_l2, y_train):>12.2%}")
print(f"{'测试集准确率':20s} {accuracy(test_pred_no, y_test):>12.2%} {accuracy(test_pred_l2, y_test):>12.2%}")
print(f"{'最终损失':20s} {loss_no_reg[-1]:>12.4f} {loss_l2[-1]:>12.4f}")
print("-" * 60)
print(f"观察：L2 正则化使权重平方和更小（{np.sum(w_l2**2):.4f} < {np.sum(w_no_reg**2):.4f}），")
print(f"权重被'压小'了，模型更简单，防止过拟合。")

# ============================================================
# 第四步：可视化
# ============================================================
fig, axes = plt.subplots(2, 2, figsize=(14, 11))

# --- 图1：数据散点图 + 决策边界 ---
axes[0][0].scatter(X_train[y_train == 0][:, 0], X_train[y_train == 0][:, 1],
                   c='steelblue', s=20, alpha=0.6, label='类别 0 (训练)')
axes[0][0].scatter(X_train[y_train == 1][:, 0], X_train[y_train == 1][:, 1],
                   c='crimson', s=20, alpha=0.6, label='类别 1 (训练)')
axes[0][0].scatter(X_test[:, 0], X_test[:, 1],
                   c='gray', s=30, marker='x', label='测试集')

# 画决策边界：w0*x0 + w1*x1 + b = 0  =>  x1 = -(w0*x0 + b) / w1
x_boundary = np.linspace(X[:, 0].min() - 1, X[:, 0].max() + 1, 100)
# 无正则化
y_boundary_no = -(w_no_reg[0] * x_boundary + b_no_reg) / w_no_reg[1]
axes[0][0].plot(x_boundary, y_boundary_no, color='orange', linewidth=2,
                linestyle='-', label='无正则化')
# L2 正则化
y_boundary_l2 = -(w_l2[0] * x_boundary + b_l2) / w_l2[1]
axes[0][0].plot(x_boundary, y_boundary_l2, color='green', linewidth=2,
                linestyle='--', label=f'L2 (λ={l2_lambda})')

axes[0][0].set_title("数据分布与决策边界对比")
axes[0][0].set_xlabel("特征 x1")
axes[0][0].set_ylabel("特征 x2")
axes[0][0].legend(fontsize=8)
axes[0][0].grid(True, alpha=0.3)

# --- 图2：损失下降曲线 ---
axes[0][1].plot(range(1, n_epochs + 1), loss_no_reg, color='orange',
                linewidth=2, label='无正则化')
axes[0][1].plot(range(1, n_epochs + 1), loss_l2, color='green',
                linewidth=2, linestyle='--', label=f'L2 (λ={l2_lambda})')
axes[0][1].set_title("损失下降曲线对比（交叉熵 + L2）")
axes[0][1].set_xlabel("Epoch（训练轮数）")
axes[0][1].set_ylabel("Loss")
axes[0][1].legend()
axes[0][1].grid(True, alpha=0.3)

# --- 图3：Sigmoid 函数可视化 ---
z = np.linspace(-6, 6, 200)
axes[1][0].plot(z, sigmoid(z), color='steelblue', linewidth=2, label='σ(z)')
axes[1][0].axhline(y=0.5, color='gray', linestyle='--', alpha=0.5, label='决策阈值 0.5')
axes[1][0].axvline(x=0, color='gray', linestyle=':', alpha=0.5)
axes[1][0].set_title("Sigmoid 函数：σ(z) = 1 / (1 + exp(-z))")
axes[1][0].set_xlabel("z = w·x + b")
axes[1][0].set_ylabel("σ(z) = P(y=1|x)")
axes[1][0].legend()
axes[1][0].grid(True, alpha=0.3)

# --- 图4：权重大小对比（柱状图）---
bar_width = 0.3
x_pos = np.arange(len(w_no_reg))
axes[1][1].bar(x_pos - bar_width / 2, np.abs(w_no_reg), bar_width,
               color='orange', label='无正则化')
axes[1][1].bar(x_pos + bar_width / 2, np.abs(w_l2), bar_width,
               color='green', label=f'L2 (λ={l2_lambda})')
axes[1][1].set_xticks(x_pos)
axes[1][1].set_xticklabels([f'w{i}' for i in range(len(w_no_reg))])
axes[1][1].set_title("权重绝对值对比（L2 使权重更小）")
axes[1][1].set_ylabel("|w|（权重绝对值）")
axes[1][1].legend()
axes[1][1].grid(True, alpha=0.3, axis='y')

plt.tight_layout()
_output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "outputs")
os.makedirs(_output_dir, exist_ok=True)
_output_path = os.path.join(_output_dir, "1.2-逻辑回归结果.png")
plt.savefig(_output_path, dpi=150)
plt.show()
print(f"\n图表已保存至: {_output_path}")
