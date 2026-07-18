"""
概念5 任务：用 NumPy 生成模拟 IMU 数据并计算三轴加速度模长
- 数据：三轴正弦波 + 随机高斯噪声 + z 轴重力分量
- 模长：||a|| = sqrt(x^2 + y^2 + z^2)
- 约束：全程禁用 for 循环（全部向量化 + 广播）

知识点串联：
- 创建 Ndarray：linspace / zeros / random.normal
- 广播：标量、(3,) 与 (N,3) 运算
- 轴与聚合：sum(axis=1) 跨三轴求和
- 矩阵运算：逐元素平方 **2、np.sqrt
"""

import numpy as np


def generate_imu(n_samples=1000, fs=100.0, seed=42):
    """生成模拟 IMU 三轴加速度数据。

    返回:
        t:       (N,)   时间轴，秒
        imu:     (N, 3) 三轴加速度 [x, y, z]，含噪声 + 重力
        gravity: (3,)   重力分量（z 轴 9.8 m/s^2）
    """
    np.random.seed(seed)                                  # 固定种子，可复现

    # 1. 时间轴：0 ~ N/fs 秒，共 N 个采样点（linspace 含终点）
    t = np.linspace(0, n_samples / fs, n_samples)         # shape (N,)

    # 2. 三轴理想正弦信号（不同频率/相位，模拟真实运动）
    x = np.sin(2 * np.pi * 1.0 * t)                       # 1 Hz 振荡
    y = np.sin(2 * np.pi * 0.5 * t + np.pi / 4)           # 0.5 Hz，相移 π/4
    z = np.zeros_like(t)                                  # z 轴静止分量先置 0

    # 3. 高斯噪声：均值 0、标准差 0.1，形状直接 (N, 3) 一次生成
    noise = np.random.normal(0, 0.1, (n_samples, 3))      # 广播友好的形状

    # 4. 合并三轴成 (N, 3)：用 column_stack 把三个 (N,) 拼成 (N, 3)
    ideal = np.column_stack([x, y, z])                    # shape (N, 3)

    # 5. 加噪声 + 重力分量（z 轴加 9.8 m/s^2，静止 IMU 的典型读数）
    gravity = np.array([0.0, 0.0, 9.8])                   # shape (3,)
    imu = ideal + noise + gravity                         # (N,3)+(N,3)+(3,) → 广播成 (N,3)

    return t, imu, gravity


def compute_magnitude(imu):
    """计算每个采样点的加速度模长 ||a|| = sqrt(x^2+y^2+z^2)。

    输入:  imu  (N, 3)
    返回:  |a|  (N,)
    """
    # 逐元素平方 → 跨三轴(axis=1)求和 → 开方，全程无 for 循环
    return np.sqrt((imu ** 2).sum(axis=1))


def main():
    n_samples = 1000
    t, imu, gravity = generate_imu(n_samples=n_samples, fs=100.0)
    magnitude = compute_magnitude(imu)

    # ---- 打印形状，验证维度/广播/axis 用对了 ----
    print("=== 形状检查 ===")
    print(f"t        shape: {t.shape}")        # (1000,)
    print(f"imu      shape: {imu.shape}")      # (1000, 3)
    print(f"magnitude shape: {magnitude.shape}")  # (1000,)

    # ---- 基本统计（axis=0：每轴跨所有样本的统计）----
    print("\n=== 每轴统计 (axis=0) ===")
    print(f"均值: {imu.mean(axis=0)}")         # 接近 [0, 0, 9.8]
    print(f"标准差: {imu.std(axis=0)}")        # x/y 约 0.707(正弦), z 约 0.1(纯噪声)

    # ---- 模长统计 ----
    print("\n=== 加速度模长 ||a|| ===")
    print(f"均值: {magnitude.mean():.4f} m/s^2")
    print(f"范围: [{magnitude.min():.4f}, {magnitude.max():.4f}] m/s^2")
    print(f"前 5 个采样点模长: {magnitude[:5]}")

    # ---- 验证：去重力后模长应接近纯信号 ----
    imu_no_g = imu - gravity                    # (N,3) - (3,) 广播，减掉重力
    mag_no_g = compute_magnitude(imu_no_g)
    print(f"\n去重力后模长均值: {mag_no_g.mean():.4f} m/s^2  (应远小于 {magnitude.mean():.4f})")

    # ---- 内存视图演示：修改切片会影响原数组 ----
    view = imu[:3]                              # 视图，共享内存
    snapshot = imu[:3].copy()                   # 副本，独立
    view[0, 0] = -999.0
    print(f"\n视图改 [0,0] 后原数组 imu[0,0] = {imu[0, 0]}  (视图影响了原数组)")
    print(f"副本 snapshot[0,0] = {snapshot[0, 0]}  (副本不受影响)")
    imu[0, 0] = snapshot[0, 0]                  # 还原


if __name__ == "__main__":
    main()
