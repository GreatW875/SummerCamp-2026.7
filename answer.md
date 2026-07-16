# 科研前置基础学习指南 — 答案与实操记录

---

# 第一部分：基础环境

---

## 1 计算机系统与体系结构基础

### 实操任务 1：画出"一段Python代码从运行到输出"经过的层次

```
┌──────────────────────────────────────────────────────┐
│  Python 代码：print("Hello, World!")                  │
└────────────────────┬─────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────┐
│  第5层：应用层（Python 解释器）                        │
│  - CPython 把 .py 编译成 .pyc 字节码                   │
│  - 逐条解释字节码，print() 最终调用 C 标准库的 write()  │
└────────────────────┬─────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────┐
│  第4层：语言运行时 / 标准库（libc）                     │
│  - libc 的 write() 函数准备系统调用参数                 │
│  - 填入：fd=1(stdout), buf="Hello, World!", count=13  │
└────────────────────┬─────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────┐
│  第3层：操作系统内核（Kernel）                          │
│  - 发生系统调用（syscall），CPU从用户态切换到内核态      │
│  - 内核的 VFS 层找到 stdout 对应的终端设备文件           │
│  - 内核把数据交给 tty/pty 驱动                          │
└────────────────────┬─────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────┐
│  第2层：设备驱动                                       │
│  - 终端驱动把字符渲染成像素                             │
│  - 通过 PCIe/USB 总线把数据送到显卡/终端                │
└────────────────────┬─────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────┐
│  第1层：硬件（CPU + 显卡 + 显示器）                     │
│  - 显卡把像素信号通过 HDMI/DP 送到显示器                │
│  - 屏幕上显示：Hello, World!                           │
└──────────────────────────────────────────────────────┘
```

**关键点**：每一层只和相邻层打交道。Python 不知道也不关心显示器是 HDMI 还是 DP，内核也不知道你用的是 Python 还是 C。

---

### 实操任务 2：为什么程序在 Windows 跑得好好的，到 Linux 就乱码？

**根本原因：Windows 默认编码是 GBK（或 GB2312），Linux 默认编码是 UTF-8。**

具体机制：

```
Windows 上写文件：
  open("data.txt", "w")  → 未指定 encoding → 使用系统默认 GBK 编码写入
  文件内容以 GBK 字节序列存在硬盘上

Linux 上读同一个文件：
  open("data.txt", "r")  → 未指定 encoding → 使用系统默认 UTF-8 解码
  GBK 的字节序列被当成 UTF-8 解释 → 乱码！
```

**为什么 Windows 是 GBK？**
- 历史原因：GBK 是中国国家标准，Windows 中文版为了兼容大量历史中文软件，默认使用 GBK 作为 ANSI 代码页
- Linux 从一开始就面向国际，默认使用 UTF-8

**解决方案：显式指定编码**
```python
# 写文件时指定 UTF-8
with open("data.txt", "w", encoding="utf-8") as f:
    f.write("中文内容")

# 读文件时也指定 UTF-8
with open("data.txt", "r", encoding="utf-8") as f:
    content = f.read()
```

---

### 实操任务 3：CPU 和 GPU 各适合什么任务？

| | CPU | GPU |
|---|---|---|
| **核心设计** | 低延迟、复杂控制流 | 高吞吐、海量并行 |
| **核心数** | 8-64 个大核 | 数千个小核 |
| **缓存** | 多级大缓存（L1/L2/L3） | 缓存较小，靠并行隐藏延迟 |
| **擅长** | 分支预测、逻辑判断、串行任务 | 矩阵乘法、向量运算、数据并行 |

**CPU 适合**：
- 操作系统调度、数据库查询
- 复杂 if/else 逻辑多的代码
- Web 服务器请求处理
- 单线程性能敏感的任务

**GPU 适合**：
- 深度学习训练/推理（矩阵乘法是核心）
- 图形渲染
- 科学计算（向量加法、矩阵运算）
- 大规模并行数据处理

**原因**：CPU 追求"单兵作战能力"（一个线程尽可能快），GPU 追求"人海战术"（几千个线程同时干活）。深度学习的矩阵乘法 `A×B` 中每个输出元素的计算是独立的，可以被 GPU 的几千个核同时计算。

---

### 实操任务 4：PATH、LD_LIBRARY_PATH、PYTHONPATH 的作用

| 环境变量 | 作用 | 搜索什么 | 谁用 |
|---|---|---|---|
| `PATH` | 可执行文件的搜索路径 | 可执行程序（`cp`、`python`等） | Shell |
| `LD_LIBRARY_PATH` | 动态链接库的搜索路径 | `.so` 共享库文件 | 动态链接器（ld.so） |
| `PYTHONPATH` | Python 模块的搜索路径 | `.py` Python 源文件 | Python 解释器 |

```
三者各自的搜索时机：

PATH → 你在终端敲 "python" → Shell 沿着 PATH 找 python 程序
LD_LIBRARY_PATH → python 启动后需要 libcuda.so → 动态链接器沿着它找 CUDA 库
PYTHONPATH → python 里 import numpy → Python 沿着它找 numpy 包
```

**常见问题**：

```bash
# "装了软件却找不到命令" → PATH 问题
$ echo $PATH
# 检查软件安装目录是否在 PATH 里

# "import 找不到包但 pip list 里有" → PYTHONPATH + 检查在哪个 python 环境下
$ echo $PYTHONPATH
$ which python

# "运行时找不到 .so 文件" → LD_LIBRARY_PATH 问题
$ echo $LD_LIBRARY_PATH
$ export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH
```

---

## 2 Linux 系统与 Shell 命令

### 实操任务 1：纯命令行完成"创建目录→写文件→查找内容→打包备份"

完整操作过程：

```bash
# 第一步：创建目录结构
$ mkdir -p myproject/src myproject/data myproject/scripts
$ tree myproject/
myproject/
├── data
├── scripts
└── src

# 第二步：写文件（用 > 重定向或 cat 写入）
$ echo "这是第一个测试文件" > myproject/src/test1.txt
$ echo "这是第二个测试文件，包含error关键词" > myproject/src/test2.txt
$ echo "# My Project" > myproject/README.md

# 第三步：查找内容
$ grep -r "error" myproject/
myproject/src/test2.txt:这是第二个测试文件，包含error关键词

$ grep -r "第一个" myproject/
myproject/src/test1.txt:这是第一个测试文件

# 第四步：打包备份
$ tar -czf myproject_backup.tar.gz myproject/src/ myproject/README.md myproject/data/ myproject/scripts/
$ ls -lh myproject_backup.tar.gz
-rw-r--r-- 1 xavier xavier 324 Jul 16 16:42 myproject_backup.tar.gz
```

**用到的命令一览**：
- `mkdir -p`：创建多级目录
- `echo ... > file`：写内容到文件
- `grep -r`：递归查找
- `tar -czf`：打包并压缩

---

### 实操任务 2：tmux 会话保持

```bash
# 1. SSH 连上服务器后，启动 tmux
$ ssh user@server
$ tmux                    # 创建新会话

# 2. 在 tmux 里跑训练
$ cd project
$ python train.py         # 开始训练，看到 loss 在下降

# 3. 脱离会话（程序继续在服务器上跑）：按 Ctrl+b 再按 d
#    你会看到：[detached]

# 4. 关掉终端、断开 SSH、合上电脑……训练在服务器上照跑不误

# 5. 第二天重新 SSH 连上，回到昨天的工作状态
$ ssh user@server
$ tmux attach             # 回到昨天的会话，看到训练还在跑，loss 已经降到 0.01！
```

**tmux 快捷键速查**：
| 操作 | 按键 |
|---|---|
| 脱离会话 | `Ctrl+b` 然后 `d` |
| 左右分屏 | `Ctrl+b` 然后 `%` |
| 上下分屏 | `Ctrl+b` 然后 `"` |
| 新建窗口 | `Ctrl+b` 然后 `c` |
| 切换窗口 | `Ctrl+b` 然后 `0-9` |
| 重新连接 | `tmux attach` |

---

### 实操任务 3：用 grep + awk 从日志中提取 ERROR 行并统计

假设日志文件 `server.log` 内容：

```
2026-07-16 08:00:01 INFO Server started
2026-07-16 08:05:23 ERROR Connection timeout on port 8080
2026-07-16 08:07:45 WARN Memory usage exceeds 80%
2026-07-16 08:10:12 ERROR Database connection failed: too many connections
2026-07-16 08:12:30 INFO Health check passed
2026-07-16 08:15:00 ERROR Disk I/O error on /dev/sda
2026-07-16 08:18:22 ERROR Connection timeout on port 8080
```

**步骤一：grep 提取所有 ERROR 行**

```bash
$ grep "ERROR" server.log
2026-07-16 08:05:23 ERROR Connection timeout on port 8080
2026-07-16 08:10:12 ERROR Database connection failed: too many connections
2026-07-16 08:15:00 ERROR Disk I/O error on /dev/sda
2026-07-16 08:18:22 ERROR Connection timeout on port 8080
```

**步骤二：grep -c 统计总次数**

```bash
$ grep -c "ERROR" server.log
4
```

**步骤三：awk 提取时间 + 错误信息**

```bash
$ awk '/ERROR/ {print "时间:", $1, $2, "错误:", $4, $5, $6, $7, $8}' server.log
时间: 2026-07-16 08:05:23 错误: Connection timeout on port 8080
时间: 2026-07-16 08:10:12 错误: Database connection failed: too many connections
时间: 2026-07-16 08:15:00 错误: Disk I/O error on /dev/sda
时间: 2026-07-16 08:18:22 错误: Connection timeout on port 8080
```

**步骤四：awk 按错误类型分组统计**

```bash
$ awk '/ERROR/ {type=$4" "$5; count[type]++} END {for (t in count) print count[t]"次: "t}' server.log
2次: Connection timeout
1次: Disk I/O
1次: Database connection
```

**一条命令搞定提取+统计**：
```bash
$ grep "ERROR" server.log | awk '{print $4, $5}' | sort | uniq -c
      2 Connection timeout
      1 Database connection
      1 Disk I/O
```

---

### 实操任务 4：Shell 脚本批量重命名 .txt → .md

```bash
#!/bin/bash
# 文件: rename_txt2md.sh

for file in *.txt; do
    # 如果没有 .txt 文件，*.txt 会保留字面量，跳过
    if [ ! -f "$file" ]; then
        echo "当前目录没有 .txt 文件"
        break
    fi

    # ${file%.txt} 去掉末尾的 .txt，再加上 .md
    mv "$file" "${file%.txt}.md"
    echo "$file → ${file%.txt}.md"
done
```

**使用方式**：
```bash
$ chmod +x rename_txt2md.sh
$ ./rename_txt2md.sh
a.txt → a.md
b.txt → b.md
readme.txt → readme.md
```

**核心语法解释**：
- `for file in *.txt` —— 遍历当前目录所有 .txt 文件
- `${file%.txt}` —— 从变量末尾去掉 `.txt`（Shell 字符串操作）
- `[ ! -f "$file" ]` —— 判断 $file 是否不是一个普通文件（防止 `.txt` 不存在时出 bug）

---

## 3 SSH 与远程服务器/GPU 集群管理

### 实操任务 1：配置 ~/.ssh/config 一键登录

```bash
# 1. 生成密钥对（如果还没有）
$ ssh-keygen -t ed25519 -C "your_email@example.com"
# 一路回车，会在 ~/.ssh/ 下生成：
#   id_ed25519（私钥，绝不要分享）
#   id_ed25519.pub（公钥，可以分享）

# 2. 上传公钥到服务器
$ ssh-copy-id user@192.168.1.100

# 3. 编辑 ~/.ssh/config，添加别名
$ cat >> ~/.ssh/config << 'EOF'
Host gpu-server
    HostName 192.168.1.100
    User xavier
    Port 22
    IdentityFile ~/.ssh/id_ed25519

Host lab-cluster
    HostName 10.0.0.50
    User zhang
    Port 2222
    IdentityFile ~/.ssh/id_ed25519
EOF

# 4. 现在可以一键登录，不用输密码和 IP 了
$ ssh gpu-server
# 直接连上！
```

**配置后对比**：
```bash
# 配置前（又长又烦）
$ ssh xavier@192.168.1.100 -p 22

# 配置后（简短清爽）
$ ssh gpu-server
```

---

### 实操任务 2：scp 上传 + rsync 增量同步

```bash
# ─── scp：上传整个文件夹到服务器 ───
$ scp -r ~/project/ gpu-server:~/project/
# -r 递归复制整个目录
# 所有文件都会传输，不管服务器上有没有

# ─── rsync：后来改了部分文件，增量同步（只传差异） ───
$ rsync -avz --partial --progress ~/project/ gpu-server:~/project/
# -a  保留权限/时间戳/软链接（归档模式）
# -v  显示详细过程
# -z  传输时压缩
# --partial  支持断点续传（断了可以继续）
# --progress 显示进度条

# ─── 关键区别 ───
# scp：全量复制（每次传全部）
# rsync：增量同步（只传改了的部分，快很多）
```

---

### 实操任务 3：ssh -L 端口转发访问远程 JupyterLab

```bash
# 场景：在 GPU 服务器上启动了 JupyterLab，端口 8888，无法直接访问（防火墙/内网）

# 在服务器上启动 JupyterLab
$ ssh gpu-server
$ jupyter lab --no-browser --port=8888
# 输出：http://localhost:8888/lab?token=abc123...

# 在你本地电脑另开一个终端，做端口转发
$ ssh -L 8888:localhost:8888 gpu-server
#  ───┬───  ──────┬──────
#     │           └─ 服务器上的 localhost:8888（JupyterLab 所在位置）
#     └─ 本地 8888 端口（浏览器访问这个）

# 现在在本地浏览器打开 http://localhost:8888 就能访问远程 JupyterLab 了！
```

**原理**：
```
本地浏览器 → localhost:8888 → SSH 加密隧道 → 服务器 localhost:8888 → JupyterLab
```

---

### 实操任务 4：CUDA_VISIBLE_DEVICES 指定 GPU

```bash
# 查看服务器上有哪些 GPU
$ nvidia-smi
# 看到 GPU 0 空闲，GPU 1 有人在用

# 只使用第 0 号 GPU（不影响第 1 号 GPU 上别人的任务）
$ CUDA_VISIBLE_DEVICES=0 python train.py

# Python 代码里只能看到一张卡（索引 0），对应的是物理 GPU 0
# 别人在 GPU 1 上跑的任务不受影响
```

```python
# Python 代码里验证
import torch
print(f"可见 GPU 数量: {torch.cuda.device_count()}")  # 输出 1
print(f"当前 GPU: {torch.cuda.current_device()}")     # 输出 0
```

---

## 4 开发环境与工具链

### 实操任务 1：VSCode + Python + Remote-SSH 断点调试

**配置步骤**：
1. 安装 VSCode
2. 安装插件：Python、Pylance、Jupyter、Remote-SSH
3. `Ctrl+Shift+P` → 输入 "Remote-SSH: Connect to Host..." → 选择之前配置的 `gpu-server`
4. 连接后，VSCode 窗口变成远程环境 → 打开远程文件夹 → 编辑代码
5. 在代码行号左边单击设断点（红点）→ F5 启动调试 → 代码停在断点处 → 查看变量值

**launch.json 基本配置**：
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: 当前文件",
            "type": "python",
            "request": "launch",
            "program": "${file}",
            "console": "integratedTerminal"
        }
    ]
}
```

---

### 实操任务 2：cookiecutter 生成标准项目骨架

```bash
# 安装 cookiecutter
$ pip install cookiecutter

# 用模板生成项目（data-science 模板为例）
$ cookiecutter https://github.com/drivendata/cookiecutter-data-science

# 按提示填写项目名、作者等，自动生成：
my_project/
├── README.md
├── requirements.txt
├── .gitignore
├── setup.py
├── src/
│   └── data/
│   └── features/
│   └── models/
│   └── visualization/
├── notebooks/
├── data/
│   ├── raw/
│   ├── processed/
│   └── external/
└── models/
```

---

### 实操任务 3：.env 管理 API 密钥 + python-dotenv 读取

**第一步：创建 .env 文件**
```bash
# .env 文件（这个文件绝不提交到 Git！）
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
HUGGINGFACE_TOKEN=hf_xxxxxxxxxxxxxxxxxxxx
DATA_PATH=/mnt/data/dataset/
```

**第二步：创建 .env.example（提交到 Git 的模板）**
```bash
# .env.example（不含真实密钥，告诉别人需要配什么变量）
OPENAI_API_KEY=your_openai_api_key_here
HUGGINGFACE_TOKEN=your_hf_token_here
DATA_PATH=/path/to/dataset/
```

**第三步：Python 代码读取**
```python
# config.py
from dotenv import load_dotenv
import os

load_dotenv()  # 自动从项目根目录的 .env 文件加载到环境变量

api_key = os.getenv("OPENAI_API_KEY")
hf_token = os.getenv("HUGGINGFACE_TOKEN")
data_dir = os.getenv("DATA_PATH", "/data/default/")  # 第二个参数是默认值
```

**第四步：.gitignore 排除 .env**
```
# .gitignore
.env
*.pth
*.pt
__pycache__/
data/
```

---

### 实操任务 4：.gitignore 配置

```gitignore
# .gitignore

# 敏感信息
.env

# 数据文件（太大，且不应版本化）
data/
*.csv
*.parquet
*.h5

# 模型权重文件（太大）
*.pth
*.pt
*.bin
*.safetensors
models/
checkpoints/

# Python 缓存
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.eggs/

# IDE 配置
.vscode/
.idea/
*.swp

# Jupyter 检查点
.ipynb_checkpoints/

# 虚拟环境
venv/
.venv/
env/
```

---

## 5 Python 虚拟环境与包管理

### 实操任务 1：用 conda 创建 dl 环境并安装 PyTorch+CUDA

```bash
# 1. 创建环境（Python 3.11）
$ conda create -n dl python=3.11
$ conda activate dl

# 2. 安装 PyTorch（带 CUDA 支持）
# 先去 https://pytorch.org/get-started/locally/ 查对应命令
# 假设 CUDA 12.1：
$ conda install pytorch torchvision torchaudio pytorch-cuda=12.1 -c pytorch -c nvidia

# 3. 验证安装
$ python -c "import torch; print(torch.__version__); print(torch.cuda.is_available())"
2.5.0
True
```

---

### 实操任务 2：导出 → 删除 → 从 yaml 重建

```bash
# 1. 导出环境配置
$ conda env export > environment.yml
# 或者只导出显式安装的包（更干净）：
$ conda env export --from-history > environment.yml

# 2. 删除环境
$ conda deactivate
$ conda env remove -n dl

# 3. 从 yaml 重建环境
$ conda env create -f environment.yml

# 4. 验证一致性
$ conda activate dl
$ python -c "import torch; print(torch.cuda.is_available())"
True   # 一切正常！
```

---

### 实操任务 3：pip install -e . 可编辑安装

```
my_lib/
├── pyproject.toml    # 包元数据
├── src/
│   └── my_lib/
│       ├── __init__.py
│       └── utils.py
└── scripts/
    └── train.py      # 这里可以 import my_lib
```

```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "my_lib"
version = "0.1.0"
```

```bash
# 可编辑安装（-e 关键）
$ cd my_lib
$ pip install -e .
# -e 的意思是 editable —— 改代码不需要重新 install，实时生效

# 现在在任何地方都能导入自己的包了
$ python -c "import my_lib; print('导入成功!')"
```

---

### 实操任务 4：配置 pip 镜像源

```bash
# 配置清华源（永久生效）
$ pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 或者临时使用某源（-i）
$ pip install numpy -i https://pypi.tuna.tsinghua.edu.cn/simple

# 其他常用镜像源
# 清华：https://pypi.tuna.tsinghua.edu.cn/simple
# 阿里：https://mirrors.aliyun.com/pypi/simple/
# 中科大：https://pypi.mirrors.ustc.edu.cn/simple/

# 查看当前配置
$ pip config list
global.index-url='https://pypi.tuna.tsinghua.edu.cn/simple'
```

---

# 第二部分：版本控制与协作

---

## 6 Git 版本控制与协作工作流

### 实操任务 1：在 GitHub 创建仓库 + SSH 免密推送

```bash
# 1. 生成 SSH 密钥（如果已生成则跳过）
$ ssh-keygen -t ed25519 -C "your_email@example.com"
# 公钥在 ~/.ssh/id_ed25519.pub

# 2. 把公钥添加到 GitHub
#    cat ~/.ssh/id_ed25519.pub
#    复制内容 → GitHub → Settings → SSH and GPG keys → New SSH key → 粘贴

# 3. 测试连接
$ ssh -T git@github.com
Hi username! You've successfully authenticated.

# 4. 在 GitHub 网页上创建仓库（比如叫 my-project）

# 5. 本地操作
$ git clone git@github.com:username/my-project.git   # SSH 方式 clone

# 或者已有仓库改用 SSH：
$ cd existing_project
$ git remote set-url origin git@github.com:username/my-project.git
$ git push -u origin main
```

---

### 实操任务 2：完成一次完整 PR 流程

```bash
# 1. 从 main 分出功能分支
$ git checkout main
$ git pull origin main
$ git checkout -b feature/add-login

# 2. 改代码 + commit
$ echo "def login(): pass" > login.py
$ git add login.py
$ git commit -m "feat: add login function

实现了基本的用户登录功能
- 支持用户名密码登录
- 返回 JWT token"

# 3. 推送到远程
$ git push -u origin feature/add-login

# 4. 在 GitHub 网页上：
#    你的分支旁边会出现 "Compare & pull request" 按钮
#    → 点击 → 填写 PR 描述（改了什么、为什么改）
#    → Create Pull Request

# 5. 自我审查
#    在 PR 的 "Files changed" 标签逐行检查：
#    - 有没有打印敏感信息的 debug 代码？
#    - 命名是否清晰？
#    - 注释是否充分？

# 6. 审查通过 → 在 GitHub 网页上点 "Merge pull request"

# 7. 清理本地
$ git checkout main
$ git pull origin main
$ git branch -d feature/add-login   # 删除本地功能分支
```

**commit message 规范（Conventional Commits）**：
```
feat:   新功能
fix:    修 bug
docs:   文档
refactor: 重构（不改功能，只改结构）
test:   测试
chore:  杂务（更新依赖、配置等）
```

---

### 实操任务 3：配置 pre-commit 自动检查

```bash
# 1. 安装 pre-commit
$ pip install pre-commit

# 2. 在项目根目录创建 .pre-commit-config.yaml
$ cat > .pre-commit-config.yaml << 'EOF'
repos:
  - repo: https://github.com/psf/black
    rev: 24.1.0
    hooks:
      - id: black
        language_version: python3
  - repo: https://github.com/pycqa/flake8
    rev: 7.0.0
    hooks:
      - id: flake8
EOF

# 3. 安装 git hooks
$ pre-commit install
# pre-commit installed at .git/hooks/pre-commit

# 4. 现在每次 git commit 前会自动跑 black（格式化）和 flake8（风格检查）
$ git commit -m "test"
black................................................(no files to check)Skipped
flake8...............................................(no files to check)Skipped
# 如果检查不通过，commit 会被阻止，修好再提交
```

---

### 实操任务 4：用 git bisect 定位 bug

```bash
# 场景：model 现在预测全输出 0，三个月前是正常的，中间有 100 个 commit

# 1. 开始 bisect
$ git bisect start

# 2. 标记当前版本是坏的
$ git bisect bad HEAD

# 3. 标记一个以前的版本是好的
$ git bisect good abc1234   # 三个月前的 commit

# 4. Git 自动 checkout 到中间某个版本，你去跑测试
$ python test.py
# 如果输出正常 → git bisect good
# 如果输出全是 0 → git bisect bad

# 5. Git 继续二分，重复步骤 4，直到定位到具体的 commit：
# abc5678 is the first bad commit
# "修改了数据预处理，把归一化范围从 [0,1] 改成了 [-1,1]"
```

---

### 实操任务 5：给开源项目提 PR（以修文档 typo 为例）

```bash
# 1. Fork 那个项目（在 GitHub 网页上点 Fork 按钮）

# 2. Clone 你 fork 的仓库
$ git clone git@github.com:your-username/open-source-project.git
$ cd open-source-project

# 3. 创建分支修 bug
$ git checkout -b fix/typo-in-readme

# 4. 修改文件 → commit → push
$ vim README.md          # 把 "recieve" 改成 "receive"
$ git add README.md
$ git commit -m "docs: fix typo in README"
$ git push -u origin fix/typo-in-readme

# 5. 在 GitHub 网页上，你的 fork 里会出现 "Compare & pull request"
#    → 点击 → 写好 PR 描述 → 提交
```

---

## 补充：避坑提示汇总

1. **`rm -rf /` 或 `rm -rf ~`** — 删除前先用 `ls` 确认路径
2. **不要用 root 做日常操作** — `sudo` 足够
3. **跑长时间实验务必用 `tmux` 或 `nohup`** — SSH 断线不会毁掉三天的训练
4. **`conda` 和 `pip` 尽量不要混装** — 一个环境内统一用一种
5. **不要在 base 环境装东西** — base 只用来管理 conda 本身
6. **`.env`、`data/`、`*.pth` 绝不能提交到 Git** — 配好 `.gitignore`
7. **commit message 不要写 "update" 或 "fix bug"** — 三个月后自己都看不懂
8. **跨平台读写文件必须显式指定 `encoding='utf-8'`**
9. **`git push --force` 很危险** — 用 `--force-with-lease` 更安全
10. **共享 GPU 要讲礼仪** — `nvidia-smi` 看到别人在跑就别抢同张卡
