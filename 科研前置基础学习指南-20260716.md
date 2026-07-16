# 科研前置基础学习指南

---

# 第一部分：基础环境

## 1 计算机系统与体系结构基础

**学习目标**：理解"代码→运行"中间发生了什么，不再把计算机当黑盒。

### 核心知识点

- `✓` **计算机层级结构**：硬件 → 操作系统 → 运行时 → 应用
  - CPU架构（x86/ARM/RISC-V）、指令集、流水线
  - 内存层次：寄存器 → L1/L2/L3 Cache → RAM → 磁盘 → 网络
- `✓` **操作系统原理**：
  - 进程 vs 线程 vs 协程
  - 虚拟内存、分页、内存映射
  - 文件系统（inode、挂载点）
  - 系统调用（syscall）与用户态/内核态
- `➕` **CPU与GPU架构差异**：
  - CPU：低延迟、复杂控制流、多级Cache（适合串行逻辑）
  - GPU：高吞吐、简单控制流、海量并行单元（适合数据并行）
  - SIMD指令集与向量化
- `✓` **并行计算基础**：线程级并行 / 指令级并行 / 数据级并行（SIMD）/ GPU并行
- `✓` **环境变量与PATH机制**：为什么"装了软件却找不到命令"
- `➕` **编码与字符集**：ASCII / GBK / UTF-8 / Unicode —— Windows学生最大痛点之一
- `➕` **浮点数表示**：IEEE 754、精度损失、为什么 `0.1 + 0.2 != 0.3`（深度学习数值稳定性的根因）

### 推荐资源

- 视频：CSAPP（深入理解计算机系统）配套课程，B站有中文字幕
- 书籍：《深入理解计算机系统》（CSAPP）第1-3章、第6章（存储器层次）
- 速查：`https://cs.brown.edu/courses/cs033/docs/`

### 实操任务（验收标准）

- [ ] 能画出"一段Python代码从运行到输出"经过的层次
- [ ] 能解释"为什么我的程序在Windows跑得好好的，到Linux就乱码"
- [ ] 能说出CPU和GPU各适合什么任务，并解释原因
- [ ] 能解释 `PATH`、`LD_LIBRARY_PATH`、`PYTHONPATH` 三个环境变量的作用

### 避坑提示

- **痛点**：90%的环境配置失败源于不理解PATH和编码
- **大坑**：Windows默认GBK编码，Linux默认UTF-8，跨平台文件读写必须显式指定 `encoding='utf-8'`

---

## 2 Linux系统与Shell命令

**学习目标**：从"鼠标党"变成"命令行党"，能在服务器上独立工作。

### 核心知识点

- `✓` **Linux文件系统结构（FHS）**：`/bin /sbin /etc /home /usr /var /opt /tmp /proc /dev`
- `✓` **用户与权限**：root / 普通用户 / 用户组 / `chmod` / `chown` / `sudo`
- `✓` **核心命令行操作**：
  - 导航：`cd pwd ls tree`
  - 文件：`cp mv rm mkdir touch cat less head tail`
  - 查找：`find locate which whereis`
- `➕` **文本处理三剑客**：`grep`（搜索）/ `sed`（流编辑）/ `awk`（字段处理）—— 日志分析必备
- `✓` **管道与重定向**：`|` / `>` / `>>` / `2>` / `<`
- `✓` **Shell脚本基础**：
  - 变量、条件、循环（for/while）、函数
  - Shebang `#!/bin/bash`
  - 退出码 `$?` 与 `&&` `||`
- `✓` **Bash与Zsh**：默认Bash，Zsh+Oh-My-Zsh更友好（自动补全、主题）
- `➕` **终端增强工具**：
  - `tmux` / `screen`：SSH断线后会话保持（科研必备，跑长时间实验不会被断网坑死）
  - `tldr`：命令速查（比 `man` 友好100倍）
  - `fzf`：模糊查找历史命令和文件
  - `htop` / `btop`：进程监控（比 `top` 直观）
- `➕` **编辑器基础**：
  - `vim` / `neovim`：在服务器上改配置文件必备（至少会 `i Esc :wq`）
  - `nano`：极简替代（不会vim的应急方案）
- `➕` **进程管理**：`ps` / `kill` / `killall` / `jobs` / `bg` / `fg` / `nohup` / `&`
- `➕` **磁盘与网络**：`df` / `du` / `ncdu` / `ifconfig` / `ip` / `netstat` / `ss`

### 推荐资源

- 书籍：《鸟哥的Linux私房菜·基础学习篇》（中文实战首选）
- 视频：MIT 6.NULL（The Missing Semester of Your CS Education，免费英文，强烈推荐）
- 速查：`https://tldr.sh/`

### 实操任务

- [ ] 不用鼠标，纯命令行完成"创建目录→写文件→查找内容→打包备份"
- [ ] 用 `tmux` 开一个会话跑训练，断开SSH重连后还能看到训练继续
- [ ] 用 `grep + awk` 从日志文件中提取所有 `ERROR` 行并统计出现次数
- [ ] 写一个Shell脚本：批量重命名某目录下所有 `.txt` 为 `.md`

### 避坑提示

- **大坑**：`rm -rf /` 或 `rm -rf ~` 是科研生涯的"核按钮"，删除前先 `ls` 确认路径
- **大坑**：不要用root账号做日常操作，sudo足够
- **痛点**：服务器跑实验忘了用 `nohup` 或 `tmux`，SSH一断三天白跑

---

## 3 SSH与远程服务器/GPU集群管理

**学习目标**：能安全、高效地使用远程GPU服务器，告别"在我电脑上能跑"。

### 核心知识点

- `✓` **SSH基础**：
  - 密码登录 vs 密钥登录（强烈推荐密钥）
  - 生成密钥对：`ssh-keygen -t ed25519`
  - 上传公钥：`ssh-copy-id user@host`
  - SSH配置文件 `~/.ssh/config`：管理多服务器别名
- `➕` **SSH端口转发与隧道**：
  - 本地转发 `-L`：访问远程Jupyter/TensorBoard
  - 远程转发 `-R`
  - 动态转发 `-D`：SOCKS代理
- `➕` **文件传输**：
  - `scp`：简单单文件
  - `rsync`：增量同步大目录（带 `--partial --progress`）
  - `sftp`：交互式
- `➕` **GPU集群使用规范**：
  - `nvidia-smi`：查看GPU占用、显存、进程
  - `watch -n 1 nvidia-smi`：实时监控
  - 多人共享集群的礼仪：不独占GPU、用 `CUDA_VISIBLE_DEVICES` 指定卡
  - 任务排队系统（如Slurm/PBS）基础 —— 部分实验室会用
- `➕` **远程开发环境**：
  - VSCode Remote-SSH：本地IDE编辑远程代码（强烈推荐）
  - JupyterLab远程访问：端口转发 + token认证
  - code-server：浏览器版VSCode
- `➕` **网络基础常识**：
  - IP / 端口 / 域名 / DNS
  - 防火墙（iptables / ufw）
  - VPN / 代理 / 镜像源（科研网络访问GitHub/arXiv的常见障碍）

### 推荐资源

- 文档：`https://www.ssh.com/academy/ssh`（官方）
- 视频：MIT 6.NULL 第5讲"Shell Tools & Scripting"

### 实操任务

- [ ] 配置 `~/.ssh/config`，用 `ssh gpu-server` 一键登录（不带密码）
- [ ] 用 `scp` 上传一个文件夹到服务器，再用 `rsync` 增量同步更新
- [ ] 用 `ssh -L` 端口转发，在本地浏览器访问远程JupyterLab
- [ ] 在共享GPU服务器上，正确使用 `CUDA_VISIBLE_DEVICES=0` 指定某张卡跑训练

### 避坑提示

- **痛点**：每次输密码太烦 —— 一定要配密钥
- **大坑**：在公共网络裸奔SSH不安全 —— 用密钥+禁用密码登录
- **礼仪**：共享GPU时，`nvidia-smi` 看到别人在跑就别抢同张卡

---

## 4 开发环境与工具链

**学习目标**：搭好"顺手"的开发环境，让工具为你服务而非拖累你。

### 核心知识点

- `✓` **IDE选型**：

  - **VSCode**（首选）：轻量、插件生态、远程开发、调试、Git集成
  - **PyCharm**：重型Python IDE，重构/调试强，社区版免费
  - **JupyterLab**：交互式数据探索、可视化、教学
  - **Cursor**、Codebuddy、Codex、Kimi Code 

- `✓` **VSCode深度配置**：

  - 必装插件：Python、Pylance、Jupyter、GitLens、Remote-SSH、Docker、LaTeX Workshop
  - 调试配置（`launch.json`）：断点、条件断点、watch
  - 工作区配置（`.vscode/settings.json`）：项目级配置同步
  - Settings Sync：跨设备同步配置

- `➕` **其他工具**：

  - **CMake**（C++项目，机器人方向必备）：`CMakeLists.txt` 基础
  - **Make**：`Makefile` 基础
  - **Docker Desktop**（见第12章）

- `➕` **配置文件管理**：

  - `.env` 文件 + `python-dotenv`：管理API密钥、路径等敏感信息
  - YAML / TOML：配置文件格式选型
  - 不要把密钥硬编码进代码、不要把密钥提交进Git

- `➕` **项目结构规范**：

  ```
  my_project/
  ├── README.md
  ├── pyproject.toml / requirements.txt
  ├── .gitignore
  ├── .env.example
  ├── src/
  │   └── my_package/
  ├── notebooks/
  ├── scripts/
  ├── configs/
  ├── tests/
  └── data/  (gitignore掉)
  ```

  - 推荐工具：`cookiecutter`（项目模板生成）

### 推荐资源

- 官方文档：VSCode Docs（`https://code.visualstudio.com/docs`）
- 视频：VSCode 官方YouTube频道"Getting Started"系列

### 实操任务

- [ ] 配置好VSCode + Python + Remote-SSH，能本地编辑远程代码并断点调试
- [ ] 用 `cookiecutter` 生成一个标准项目骨架
- [ ] 写一个 `.env` 管理API密钥，并用 `python-dotenv` 读取
- [ ] 配置 `.gitignore`，确保 `data/`、`.env`、`__pycache__/` 不会被提交

---

## 5 Python虚拟环境与包管理

**学习目标**：告别"装了这个包就坏了那个包"的依赖地狱。

### 核心知识点

- `✓` **为什么需要虚拟环境**：项目A要PyTorch 1.13，项目B要PyTorch 2.1 —— 隔离

- `➕` **虚拟环境方案对比**：

  | 工具               | 优点                                       | 缺点                 | 推荐场景     |
  | ------------------ | ------------------------------------------ | -------------------- | ------------ |
  | **venv**（标准库） | 内置、轻量、稳定                           | 不能管理非Python依赖 | 简单项目     |
  | **conda / mamba**  | 可管理CUDA/C++等非Python依赖、适合数据科学 | 重、慢、占用大       | 深度学习首选 |
  | **poetry**         | 现代、依赖锁定、打包发布                   | 学习曲线             | 库开发       |
  | **uv**（新一代）   | 极快（Rust实现）、兼容pip                  | 较新                 | 性能敏感     |

- `✓` **Conda / Miniconda / Mamba**：

  - 创建环境：`conda create -n myenv python=3.11`
  - 激活/退出：`conda activate myenv` / `conda deactivate`
  - 安装包：`conda install` vs `pip install`（优先用conda装重依赖如PyTorch，pip装纯Python包）
  - 导出环境：`conda env export > environment.yml`
  - 复现环境：`conda env create -f environment.yml`
  - **Mamba**：C++重写的conda，速度快10倍，强烈推荐替代conda

- `➕` **pip进阶**：

  - `requirements.txt` vs `requirements-dev.txt`
  - `pip install -e .`（可编辑安装，开发自己的包时用）
  - 镜像源：`pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple`

- `➕` **现代打包规范**：`pyproject.toml`（PEP 518/621）取代 `setup.py`

### 推荐资源

- 官方文档：`https://docs.conda.io/`、`https://packaging.python.org/`
- 速查：`https://mamba.readthedocs.io/`

### 实操任务

- [ ] 用conda创建一个名为 `dl` 的环境（Python 3.11），安装PyTorch+CUDA
- [ ] 导出 `environment.yml`，删除环境，再用yaml重建，验证一致性
- [ ] 用 `pip install -e .` 把自己的代码包安装成可导入模块
- [ ] 配置pip镜像源为清华源，加速下载

### 避坑提示

- **大坑**：不要在base环境装东西 —— base只用来管理conda本身
- **大坑**：conda和pip混装可能冲突 —— 一个环境内尽量统一用一种
- **痛点**：`conda install` 慢 —— 换mamba，或加 `-c conda-forge` 通道

---

# 第二部分：版本控制与协作

## 6 Git版本控制与协作工作流

**学习目标**：从"会commit"到"会用Git做团队协作与科研追溯"。

### 核心知识点

- `✓` **Git核心概念**：工作区 / 暂存区 / 版本库 / 远程仓库

- `✓` **基本操作**：`init` / `clone` / `add` / `commit` / `push` / `pull` / `fetch` / `status` / `log` / `diff`

- `✓` **分支管理**：

  - `branch` / `checkout` / `switch` / `merge` / `rebase`
  - 分支策略：`main`（稳定）/ `dev`（开发）/ `feature/*` / `hotfix/*`
  - `git rebase -i` 交互式变基（整理commit历史）
  - `git cherry-pick` 摘樱桃（把某个commit应用到当前分支）

- `✓` **冲突解决**：

  - `git mergetool` 配置（VSCode内置合并工具）
  - 手动解决 `<<<<<<<` `=======` `>>>>>>>` 标记

- `✓` **Pull Request与代码审查**：

  - PR流程：fork → branch → commit → push → PR → review → merge
  - 代码审查清单：逻辑正确性、边界条件、命名规范、性能、安全
  - 评审礼仪：对事不对人、给具体建议、区分"必须改"和"建议改"

- `➕` **commit message规范**（Conventional Commits）：

  ```
  feat: 新功能
  fix: 修bug
  docs: 文档
  refactor: 重构
  test: 测试
  chore: 杂务
  ```

  - 科研代码至少写清楚"改了什么/为什么改/结果如何"

- `➕` **Git Hooks**：

  - `pre-commit`：提交前自动检查（代码风格、密钥泄露）
  - 工具：`pre-commit`框架 + `husky`

- `➕` **GitHub/GitLab高级功能**：

  - **GitHub Actions**：CI/CD自动化（自动跑测试、自动部署文档）
  - **Issues**：Bug追踪、任务管理
  - **Projects**：看板式项目管理
  - **Wiki**：项目文档
  - **Releases**：版本发布（带语义化版本号 `v1.2.3`）

- `➕` **开源协议选型**：

  - MIT：最宽松，几乎所有人用
  - Apache 2.0：含专利授权，企业友好
  - GPL：传染性，衍生作品必须开源
  - 科研代码默认推荐MIT或Apache 2.0

- `➕` **科研专用Git技巧**：

  - `git bisect`：二分定位"哪次commit引入了bug"
  - `git stash`：临时保存改动
  - `git reflog`：找回"误删"的commit
  - **大文件管理**：Git LFS（模型权重、数据集）

### 推荐资源

- 书籍：《Pro Git》（官方，免费在线，前3章覆盖90%日常需求）
- 视频：MIT 6.NULL 第6讲"Version Control"
- 交互教程：`https://learngitbranching.js.org/`

### 实操任务

- [ ] 在GitHub创建一个仓库，用SSH key免密推送
- [ ] 完成一次完整的PR流程：新建分支→改代码→提PR→自我审查→合并
- [ ] 配置 `pre-commit`，提交前自动跑 `black` 和 `flake8`
- [ ] 用 `git bisect` 定位一个"以前能跑现在不能跑"的bug
- [ ] 给一个开源项目提一个PR（哪怕只是修文档typo）

### 避坑提示

- **大坑**：不要把 `data/`、`*.pth`、`.env` 提交进Git —— 配好 `.gitignore`
- **大坑**：commit message写"update"或"fix bug" —— 三个月后自己都看不懂
- **大坑**：在 `main` 分支直接改代码 —— 出了问题难以回退
- **痛点**：`git push --force` 会覆盖远程历史 —— 用 `--force-with-lease` 更安全