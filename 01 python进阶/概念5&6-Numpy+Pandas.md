# 概念5：NumPy

**NumPy** 是 Python 科研计算的基石。它的核心数据结构 **Ndarray**（N 维数组）用"同类型数据 + 连续内存 + C 底层实现"取代了 Python 列表的指针开销，让数值计算快上几十到上百倍，并支持向量化运算（一行代替 for 循环）和广播机制。科研中几乎所有数值数据——传感器采样、矩阵、图像、信号——最终都要变成 Ndarray 来算。

## 创建 Ndarray

| 方式 | 函数 / 写法 | 说明 | 示例 |
|------|------------|------|------|
| 从列表转换 | `np.array([1,2,3])` | 最基础；可指定 `dtype=float` | 一维数组 |
| 从嵌套列表 | `np.array([[1,2],[3,4]])` | 建二维矩阵 | 2×2 |
| 全零 | `np.zeros(shape)` | 默认 float64；可 `dtype=int` | `np.zeros((3,4))` |
| 全一 | `np.ones(shape)` | 同上 | `np.ones((2,3))` |
| 全指定值 | `np.full(shape, value)` | 填充任意值 | `np.full((2,2),7)` |
| 未初始化 | `np.empty(shape)` | 最快，值随机，用前需赋值 | 先分配后填充 |
| 等差数列 | `np.arange(start, stop, step)` | **按步长，不含终点** | `np.arange(0,10,2)` → [0,2,4,6,8] |
| 等间隔点 | `np.linspace(start, stop, num)` | **按个数，含终点** | `np.linspace(0,1,5)` → [0,0.25,0.5,0.75,1] |
| 单位矩阵 | `np.eye(n)` | 对角线为 1 | `np.eye(3)` |
| 对角矩阵 | `np.diag([1,2,3])` | 对角线为给定值 | —— |
| 均匀随机 | `np.random.rand(shape)` | `[0,1)` 均匀分布 | `np.random.rand(3,3)` |
| 正态随机 | `np.random.randn(shape)` | 标准正态(μ=0,σ=1) | —— |
| 带参正态 | `np.random.normal(mu, sigma, shape)` | **加噪声最常用** | `np.random.normal(0,0.1,1000)` |
| 整数随机 | `np.random.randint(low, high, shape)` | 含 low 不含 high | —— |
| 固定种子 | `np.random.seed(42)` | 保证结果可复现 | 每次运行一致 |
| 读 CSV | `np.loadtxt(f, delimiter=',', skiprows=1)` | 纯数值 | 跳过表头 |
| 读 npz | `np.load('model.npz')` | NumPy 专用格式 | —— |

> **`arange` vs `linspace`（高频混淆点）**：`arange` 按步长生成、不含终点（像 `range`）；`linspace` 按个数生成、含终点。画图/采样用 `linspace`（"0~2π 均匀 100 点"），生成索引用 `arange`。
>
> **dtype 是 Ndarray 灵魂**：默认全整数→`int64`，含浮点→`float64`；深度学习省内存用 `float32`，信号处理用 `complex128`。

## Ndarray 的核心属性

以 `a = np.array([[1,2,3],[4,5,6]])`（2 行 3 列）为例：

| 属性 | 含义 | 示例值 |
|------|------|--------|
| `a.shape` | 形状（各维度大小） | `(2, 3)` |
| `a.ndim` | 维度数（轴的个数） | `2` |
| `a.size` | 元素总数 = 各维度乘积 | `6` |
| `a.dtype` | 元素类型 | `int64` |
| `a.itemsize` | 每个元素字节数 | `8` |
| `a.nbytes` | 总字节数 = size × itemsize | `48` |
| `a.T` | 转置 | shape 变 `(3, 2)` |
| `len(a)` | 第一维大小（行数） | `2` |

## 广播机制（Broadcasting）

**广播不是包、不是函数**，是 NumPy 在数组运算时**自动套用的一套形状对齐规则**。当两个数组形状不同时，NumPy 自动判断能否对齐——能就自动"虚拟拉伸"小数组（不真复制内存）再逐元素算，不能就报错。你只管写 `+ - * /`，无需调用任何东西。

**规则**：两个数组从右向左逐位对齐（维度数不同时，左边自动补 1）。**每一对维度独立判断**，满足"**相等 或 一方为 1**"即通过；**所有维度对都通过**才能广播，结果每位取较大值。任何一对"不相等且都不为 1"则报错。

| 某一对维度 | 能否通过 | 靠什么 |
|-----------|---------|--------|
| 两尺寸相等（都不是1） | ✅ | 相等 |
| 一方为 1 | ✅ | 为1拉伸 |
| 不相等且都不为1 | ❌ | 报错 |

### 三个例子

```python
import numpy as np

# ① 形状完全相同 —— 无需任何 1，直接逐元素运算
a = np.array([[1, 2], [3, 4]])
b = np.array([[10, 20], [30, 40]])
print(a + b)
# [[11 22]
#  [33 44]]   结果 shape (2,2)

# ② 其中一个是一维（维度数不同，左边补1）—— 靠"相等 + 为1"组合通过
mat = np.array([[1, 2, 3],          # shape (2, 3)  2行3列
                [4, 5, 6]])
vec = np.array([100, 200, 300])     # shape (3,)    补1 → (1, 3)
# 对齐: (2,3) vs (1,3)
#   位0: 2 vs 1 → 为1拉伸 ✅   位1: 3 vs 3 → 相等 ✅
print(mat + vec)
# [[101 202 303]      # vec 被拉伸成2行，每行都加 [100,200,300]
#  [104 205 306]]     结果 shape (2,3)

# ③ 两个都是一维但形状不同 —— 必须有一方为1才能广播，否则报错
col = np.array([1, 2, 3]).reshape(-1, 1)   # shape (3,1) 列向量
row = np.array([10, 20, 30]).reshape(1, -1) # shape (1,3) 行向量
# 对齐: (3,1) vs (1,3)
#   位0: 3 vs 1 → 为1拉伸 ✅   位1: 1 vs 3 → 为1拉伸 ✅
print(col + row)
# [[11 21 31]         # 列向量+行向量 → (3,3) 网格（经典模式）
#  [12 22 32]
#  [13 23 33]]
```

> 例③说明：两个一维向量 `(3,)` 和 `(3,)` 直接相加是逐元素（形状相同）；想得到网格效果，必须先 `reshape` 成 `(3,1)` 列矩阵和 `(1,3)` 行矩阵，让"1"出现在相反的维度上，两个维度都靠"为1"通过。

## 轴（axis）与聚合运算

聚合（求和、均值、极值…）把一组数压成一个数。二维以上数组聚合时，`axis` 指定"沿哪个方向压缩"。**axis 的本质：该轴被消除，其余轴保留。**

### axis 核心规则

| axis | 含义 | 直觉 | 压缩方向 | 结果 shape（以 (2,3) 为例） |
|------|------|------|---------|--------------------------|
| `axis=0` | 沿第0轴聚合 | **跨行**算 → **每列**一个结果 | 行消失，保留列 | `(3,)` |
| `axis=1` | 沿第1轴聚合 | **跨列**算 → **每行**一个结果 | 列消失，保留行 | `(2,)` |
| 不传 axis | 整体聚合 | 全部元素压成标量 | 全部消除 | `()` 标量 |

**最大反直觉点**：`axis=0` 是"跨行算，得到每列"，不是"算每行"。

```python
m = np.array([[1, 2, 3],
              [4, 5, 6]])      # shape (2, 3)
m.sum()          # 21        整体求和
m.sum(axis=0)    # [5 7 9]   跨行 → 每列和（列0:1+4=5 …）
m.sum(axis=1)    # [6 15]    跨列 → 每行和（行0:1+2+3=6）
```

> **验证口诀**：看结果 shape 反推对不对——`sum(axis=0).shape==(3,)`（行没了），`sum(axis=1).shape==(2,)`（列没了）。
>
> **EE 默认方向**：数据按 (样本, 特征) 排列，如 IMU `(N, 3)`，求每特征跨样本的统计量 → `axis=0`。几乎所有传感器统计都是 axis=0。
>
> **`keepdims=True`**：聚合后保持维度数（被压缩的轴变 1 而非消失），高维广播对齐时更安全：
> ```python
> imu.mean(axis=0, keepdims=True)   # (1, 3)，可直接和 (N,3) 广播
> ```

### 常用聚合函数

| 函数 | 作用 | 说明 |
|------|------|------|
| `a.sum(axis)` | 求和 | |
| `a.mean(axis)` | 均值 | 去均值/去趋势用 |
| `a.std(axis)` | 标准差 | 估噪声水平 |
| `a.var(axis)` | 方差 | |
| `a.max(axis)` / `a.min(axis)` | 极值 | |
| `a.argmax(axis)` / `a.argmin(axis)` | 极值的**索引** | 找峰值位置 |
| `a.cumsum(axis)` | 累加和 | 信号积分 |
| `a.cumprod(axis)` | 累乘 | |
| `a.ptp(axis)` | 极差 max-min | |

### 经典联动：IMU 三轴模长（广播 + axis）

```python
imu = np.random.rand(1000, 3)                  # (1000, 3) 样本 × XYZ
magnitude = np.sqrt((imu ** 2).sum(axis=1))    # (1000,) 每个采样点的模长 ||a||
# imu**2: (1000,3) 逐元素平方
# .sum(axis=1): 跨三轴求和 → 每行一个值
# 必须用 axis=1（跨特征轴）；误用 axis=0 物理意义全错
```

## 矩阵运算与内存视图

### 矩阵运算

**核心区分**：`*` 是逐元素乘（Hadamard积），`@` 是线性代数矩阵乘——线性代数运算一律用 `@`，不要用 `*`。

| 运算 | 写法 | 含义 |
|------|------|------|
| 逐元素乘 | `A * B` | 对应位置相乘 |
| 矩阵乘法 | `A @ B` | 线性代数矩阵乘（**首选**） |
| 矩阵乘法 | `np.dot(A, B)` | 同 `@`，老写法，2D 等价 |
| 矩阵乘法 | `np.matmul(A, B)` | 与 `@` 完全等价 |
| 逐元素加/减 | `A + B` / `A - B` | 对应位置 |
| 逐元素幂 | `A ** 2` | 每元素平方 |
| 标量乘 | `A * 2` | 广播，每元素 ×2 |
| 转置 | `A.T` / `A.transpose()` | shape (m,n)→(n,m) |

`np.linalg` 常用函数：

| 函数 | 作用 | EE 用途 |
|------|------|---------|
| `np.linalg.inv(A)` | 矩阵求逆 | —— |
| `np.linalg.solve(A, b)` | 解 `Ax=b` | **解方程首选**（比 inv 稳定快） |
| `np.linalg.lstsq(A, b)` | 最小二乘解 | 数据拟合（概念8） |
| `np.linalg.norm(x)` | 范数 | 模长、误差度量 |
| `np.linalg.det(A)` | 行列式 | —— |
| `np.linalg.eig(A)` | 特征值/向量 | 振动、PCA |
| `np.linalg.svd(A)` | 奇异值分解 | 降维、去噪 |
| `np.trace(A)` | 迹（对角线和） | —— |

> 解 `Ax=b` 用 `solve(A,b)`，不要 `inv(A) @ b`——前者数值更稳更快。坐标变换（概念8）= 矩阵乘 `@`：`p_A = Rz @ p_B`。

### 内存视图（最隐蔽的坑）

**NumPy 切片返回"视图"，共享内存，改切片会影响原数组**——与 Python 列表（切片是副本）相反。这样设计是为了零拷贝、高性能。

```python
a = np.array([1, 2, 3, 4, 5])
b = a[1:4]          # 视图，共享内存
b[0] = 999
print(a)            # [  1 999   3   4   5]  ← 原数组被改了！

c = a[1:4].copy()   # 显式副本，独立
c[0] = -1
print(a)            # 不受影响
```

| 操作 | 返回 | 改它是否影响原数组 |
|------|------|------------------|
| 基本切片 `a[1:4]`、`a[:,0]` | 视图 | **会** |
| 转置 `a.T`、`a.reshape(...)` | 视图 | **会** |
| 花式索引 `a[[0,2]]` | 副本 | 不会 |
| 布尔索引 `a[a>2]` | 副本 | 不会 |
| 运算 `a*2`、`a+b` | 副本 | 不会 |
| `a.copy()` | 副本 | 不会 |
| `b = a`（赋值） | 别名（同一对象） | **会** |

> **判断是否共享内存**：`np.shares_memory(a, b)`。
>
> **三大陷阱**：① 函数内改切片污染调用者数据；② 改 `a.T` 会改 `a`；③ `b = a` 是别名不是复制，要复制必须 `a.copy()`。
>
> **原则**：只读切片用视图（默认高效）；一旦要**修改**切片且不希望副作用，就 `.copy()`。读多写少用视图，写且怕污染用副本。

# 概念6：Pandas

## NumPy vs Pandas 对比

NumPy 是"裸数组"（纯数值、统一类型、无标签）；Pandas 建在 NumPy 之上，专处理**带标签、混合类型、有缺失**的表格数据（CSV 日志、Excel、数据库表）。

| 对比项 | NumPy `ndarray` | Pandas `DataFrame` |
|--------|----------------|--------------------|
| 结构 | 纯数值数组 | 表格（行索引+列名+值） |
| 列类型 | 全数组必须统一 | 各列可不同类型 |
| 标签 | 无（只能用整数位置） | 有行索引和列名 |
| 缺失值 | 不友好（NaN 干扰计算） | 原生支持 NaN |
| 擅长 | 数学/矩阵/信号运算 | SQL 式筛选/分组/聚合 |
| 类比 | 数学矩阵 | Excel 表 / SQL 表 |
| 关系 | 底层引擎 | DataFrame.values 转回 NumPy |

## DataFrame 是什么

**DataFrame 是 Pandas 的二维表格数据结构**——代码里的 Excel 表/SQL 表。它**不是字典**（字典只是创建它的一种原料和访问列的语法糖），内部由"多个共享同一行索引的 Series"构成，每个 Series 底层是 NumPy 数组。能读写 CSV/Excel/JSON/SQL 等多种格式，核心价值是在内存里对表格数据做筛选/清洗/聚合，而非单纯存文件。

## DataFrame 的基本结构（三件套）

DataFrame 由三个核心部分组成，有这三样就足够定义一个完整 DataFrame：

```
        timestamp  sensor_id  value  is_valid     ← df.columns（列名）
index
0       '10:00'    'TMP'      29.59  False
1       '10:01'    'TMP'      24.13  True        ← df.values（底层 NumPy 2D 数组）
2       '10:02'    'PRS'      101.2  True
3       '10:03'    'TMP'      NaN    True
↑
df.index（行索引，默认 0,1,2,...）
```

| 组成 | 属性 | 含义 |
|------|------|------|
| 行索引 | `df.index` | 每行的标签，默认整数，可改成时间戳 |
| 列名 | `df.columns` | 每列的名字 |
| 值 | `df.values` | 底层 NumPy 二维数组（去标签的裸数据） |

> 内部实现：各列是 Series，**共享同一个行索引**对齐成表——这是字典做不到的（字典各值之间无对齐关系）。`columns` 本质是各 Series 的 name，`values` 是各 Series 的 values 拼成的二维数组。其余如 `shape`/`dtypes`/`size` 是从三件套派生的描述信息，非独立组成。

## DataFrame 常用函数

**创建与读写**：

| 函数 | 作用 |
|------|------|
| `pd.DataFrame(dict)` | 从字典创建 |
| `pd.read_csv(path)` | 读 CSV（科研最常用入口） |
| `pd.read_excel/read_json/read_sql` | 读其他格式 |
| `df.to_csv(path, index=False)` | 写 CSV（`index=False` 不写行索引） |

**查看与信息**：

| 函数/属性 | 作用 |
|----------|------|
| `df.head(n)` / `df.tail(n)` | 前/后 n 行（默认5） |
| `df.info()` | 类型+非空数+内存（查缺失值神器） |
| `df.describe()` | 数值列统计摘要（均值/标准差/分位数） |
| `df.shape` | (行数, 列数) |
| `df.dtypes` | 每列数据类型 |
| `df.index` / `df.columns` / `df.values` | 三件套 |

**选取数据**：

| 任务 | 写法 | 说明 |
|------|------|------|
| 选一列 | `df['value']` | 返回 Series |
| 选多列 | `df[['a','b']]` | 传列表，返回 DataFrame |
| 按标签选行 | `df.loc[0:2]` | 标签切片，**含**终点 |
| 按位置选行 | `df.iloc[0:2]` | 整数位置，**不含**终点（同 Python） |
| 行列同选 | `df.loc[mask, 'value']` | 行掩码 + 列名 |

> **`loc` vs `iloc` 最大坑**：按名字用 `loc`（含终点），按位置用 `iloc`（不含终点）。

## 缺失值处理

Pandas 用 `NaN` 表示缺失值。`NaN` 参与计算会"污染"结果（`NaN + x = NaN`），所以**必须先处理缺失值才能计算**。注意：整数列出现 NaN 会自动提升成 float（整数存不了 NaN）。

### 发现缺失值

| 方法 | 作用 |
|------|------|
| `df.isnull()` / `df.isna()` | 逐元素是否缺失（布尔表，两者等价） |
| `df.isnull().sum()` | **每列缺失计数（最常用）** |
| `df.isnull().sum(axis=1)` | 每行缺失计数 |
| `df.isnull().mean()` | 每列缺失比例 |
| `df.info()` | Non-Null Count 小于总行数 = 该列有缺失 |

> 经验：某列缺失 > 50% 通常直接丢整列；少量缺失才填充。

### 两大处理策略

**策略A：丢弃 `dropna`**（缺失少、扔掉不影响代表性）

| 参数 | 作用 |
|------|------|
| `df.dropna()` | 丢任何含缺失的行（默认 axis=0, how='any'） |
| `df.dropna(axis=1)` | 丢含缺失的整列 |
| `df.dropna(subset=['value'])` | 只看 value 列，该列缺失才丢行 |
| `df.dropna(how='all')` | 整行全空才丢 |
| `df.dropna(thresh=3)` | 至少 3 个非空才保留 |

**策略B：填充 `fillna`**（缺失多、扔掉丢样本，或时序需保持连续）

| 填充方式 | 写法 | 适用场景 |
|---------|------|---------|
| 常数 | `fillna(0)` | 缺失代表"无读数=0" |
| 均值 | `fillna(df['value'].mean())` | 数据平稳无趋势（练习2） |
| 中位数 | `fillna(df['value'].median())` | 有离群点比均值稳 |
| 前向填充 | `fillna(method='ffill')` | **时序首选**（用上一个有效值） |
| 后向填充 | `fillna(method='bfill')` | 用下一个有效值 |
| 线性插值 | `interpolate()` | 时序更平滑（相邻值估算） |

> **时序数据优先 `ffill`/`interpolate`，不要用均值**：传感器数据有时间相关性，相邻时刻值接近；用全局均值会破坏相关性、引入虚假信号。

### 关键陷阱：默认不改原数据

Pandas 绝大多数操作**返回新对象，不修改原 DataFrame**。要生效二选一：

```python
df = df.dropna()                              # 方式1：重新赋值（推荐）
df['value'].fillna(mean, inplace=True)        # 方式2：原地修改
```

### 其他坑

- **判断缺失只能用 `isnull()`**，不能用 `==`（`NaN == NaN` 是 `False`）。
- **整数列遇 NaN 变 float**；要保留整数用可空类型 `astype('Int64')`（大写 I）。
- **`dropna()` 默认 how='any' 会误删**：某列大量缺失会连累有效行被丢，用 `subset` 限定关键列。

### 决策速查

| 缺失情况 | 推荐处理 |
|---------|---------|
| 某列缺失 > 50% | 丢整列 `drop(columns=[...])` 或 `dropna(axis=1)` |
| 少量行缺失 | `dropna()` 或 `dropna(subset=[关键列])` |
| 数值列少量缺失、平稳 | 均值/中位数 `fillna` |
| 时序数据缺失 | `ffill` 或 `interpolate()` |
| 缺失代表"无事件" | 填常数（如 0） |
| 不确定 | 丢行最安全（不引入虚假值） |

## 布尔索引与切片

按条件筛选行，相当于 SQL 的 `WHERE`。核心三步：生成布尔掩码 → 用掩码筛行 → 实际合并写 `df[df['列'] > x]`。掩码本质是一列 True/False（布尔 Series），`df[掩码]` 只保留 True 的行。

### 单条件筛选

```python
df[df['value'] > 30]          # 大于
df[df['sensor_id'] == 'TMP']  # 等于
df[~df['is_valid']]           # 取反（~ 是非）
```

### 多条件筛选（最常踩坑）

逻辑运算符用 **`&` `|` `~`**（不是 `and or not`），且**每个条件必须加括号**——因为 `&` 优先级高于 `>` `==`，不加括号会先算 `10 & 列` 导致错误。

| 逻辑 | Python | Pandas |
|------|--------|--------|
| 且 | `and` | `&` |
| 或 | `or` | `\|` |
| 非 | `not` | `~` |

```python
df[(df['value'] > 10) & (df['is_valid'])]                          # 且
df[(df['sensor_id']=='TMP') | (df['sensor_id']=='PRS')]            # 或
df[((df['value']>10) | (df['value']<5)) & df['is_valid']]          # 复合
```

### 多值匹配 `isin`（避免堆 `|`）

```python
df[df['sensor_id'].isin(['TMP','PRS','HUM'])]   # 等价 SQL 的 IN
df[~df['sensor_id'].isin(['TMP'])]              # 取反：非 TMP
```

### 字符串条件 `.str`

```python
df[df['sensor_id'].str.contains('T')]           # 包含 T
df[df['note'].str.startswith('ok')]             # 以 ok 开头
df[df['note'].str.contains('ok', na=False)]     # 列含 NaN 时加 na=False
```

### 筛行 + 选列：`loc` 一步到位

```python
df.loc[df['value'] > 30, ['sensor_id','value']]   # 行掩码 + 列名
```

### 概念6任务示例

```python
df = pd.read_csv('sensor.csv')
filtered = df[(df['timestamp'] > 10) & (df['value'] < 50)]   # 读→筛→存
filtered.to_csv('filtered.csv', index=False)
```

### 常见坑

- **用 `&/|/~` 不是 `and/or/not`**：`and` 期望单个布尔值，Pandas 给的是一列，会报"真值不确定"错。
- **每个条件加括号**：`(df['x']>10) & df['y']`。
- **链式比较要拆开**：`10 < df['x'] < 20` 不行，写成 `(df['x']>10) & (df['x']<20)`。
- **链式赋值触发 `SettingWithCopyWarning`**：`df[df['x']>10]['y']=0` ❌；安全赋值用 `df.loc[df['x']>10, 'y'] = 0`。
- **布尔索引返回副本**（非视图），改它不影响原 df。






