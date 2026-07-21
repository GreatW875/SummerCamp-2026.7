# 运动分析 Web 应用 — 运行 SOP

> 目标设备：Ubuntu 22.04 开发机 + 华为 P50 Pro 手机
> 技术栈：Flask + Flask-SocketIO + gevent + Scikit-learn + ECharts + Leaflet

---

## 一、前置条件

- **Conda**（Miniconda / Anaconda）已安装
- **OpenSSL** 已安装（`sudo apt install openssl`）
- 开发机和手机在 **同一局域网**（确保手机能访问开发机 IP）

---

## 二、首次运行（仅需一次）

### 2.1 创建 Conda 环境

```bash
cd ~/暑期培训/sport_reco
bash scripts/setup_env.sh
```

脚本自动完成：
1. 检查 conda 是否可用
2. 根据 `environment.yml` 创建/更新 `sport_reco` 环境
3. 安装所有 Python 依赖
4. 输出各依赖版本号供确认

### 2.2 训练 ML 模型（如果还没有模型文件）

```bash
conda activate sport_reco
cd ~/暑期培训/sport_reco
python -m ml.train
```

> 模型将保存到 `artifacts/models/gait_classifier.pkl`，支持 4 类运动识别：walking、running、jumping、high_knees。

### 2.3 评估模型（可选）

```bash
python -m ml.evaluate
```

---

## 三、启动应用

```bash
cd ~/暑期培训/sport_reco
conda activate sport_reco
bash scripts/run_dev.sh
```

脚本自动完成：
1. 获取本机 LAN IP
2. 生成/检查 SSL 自签名证书（CN=当前IP，SAN 包含当前 IP + 127.0.0.1 + localhost）
3. 创建必要目录（logs、data、artifacts）
4. 打印手机端和电脑端访问地址
5. 启动 Flask + WebSocket 服务（HTTPS，端口 5000，绑定 0.0.0.0）

> **重要：** 应用使用 Socket.IO 进行实时通信，前端依赖 `cdn.socket.io` CDN 加载客户端库。手机端必须能访问外网（或已将 CDN 资源本地化）。在纯内网环境下，需提前将 `socket.io.min.js` 下载到 `src/frontend/static/js/` 并修改模板引用路径。

**启动成功后输出：**

```
  📱 手机端 (传感器采集):
     https://192.168.10.96:5000/mobile

  🖥  电脑端 (监控 Dashboard):
     https://192.168.10.96:5000/
```

---

## 四、使用流程

### 4.1 手机端（华为 P50 Pro）

| 步骤 | 操作 |
|------|------|
| 1 | 确保手机与开发机连接**同一 WiFi**，且手机能访问外网（需加载 CDN 资源） |
| 2 | 打开手机浏览器（**必须使用 Chrome**，微信/QQ 内置浏览器不支持 DeviceMotion） |
| 3 | 访问 `https://<开发机IP>:5000/mobile` |
| 4 | 首次访问会提示证书不安全 → **点击「高级」→「继续前往」**（iOS 点「继续访问」） |
| 5 | 等待页面顶部状态栏显示「已连接」（Socket.IO 连接成功） |
| 6 | 在配置页选择运动类型（walking / running / jumping / high_knees） |
| 7 | 点击「开始运动」，授权传感器权限（DeviceMotion） |
| 8 | 将手机固定在身上，开始运动 |
| 9 | 运动结束后点击「结束运动」 |

> **注意：** 
> - iPhone 需要 iOS 12.2+ 并在「设置→Safari→隐私与安全性→动作与方向访问」中开启
> - 华为 P50 Pro（Android）一般默认支持，无需额外设置
> - 浏览器**首选 Chrome**，Firefox/Safari 可能对 DeviceMotion API 支持不完整
> - 若手机无法访问外网加载 CDN，状态栏会显示「初始化失败」，参考 6.7 节处理

### 4.2 电脑端（Dashboard 监控）

| 步骤 | 操作 |
|------|------|
| 1 | 打开浏览器访问 `https://<开发机IP>:5000/` |
| 2 | 点击「高级→继续前往」信任自签名证书 |
| 3 | 等待右上角连接状态显示「已连接」 |
| 4 | 左侧面板：查看实时运动类型识别结果 |
| 5 | 中间面板：6 通道波形图（加速度 3 轴 + 角速度 3 轴） |
| 6 | 右侧面板：GPS 轨迹地图 |

### 4.3 双端联动工作流

```
       手机端 (mobile 房间)          电脑端 (dashboard 房间)
    ┌──────────────────┐         ┌──────────────────────┐
    │ 传感器采集          │  WS →  │  实时波形显示           │
    │ IMU + GPS         │  WS →  │  运动类型识别 (ML推理)    │
    │ 接收推理结果         │  ← WS  │  手动纠正标签           │
    │ 步频/速度/距离估算   │         │  历史会话管理           │
    └──────────────────┘         └──────────────────────┘
    
    架构特点：
    - 移动端和桌面端通过 Socket.IO 房间隔离，互不干扰
    - 移动端优先使用 HTTP long-polling 传输（自签名证书下更可靠）
    - 传感器数据经服务端校验后批量写入 SQLite
    - ML 推理结果同时发送给两端
```

---

## 五、常用命令速查

```bash
# 激活环境
conda activate sport_reco

# 启动应用
bash scripts/run_dev.sh

# 仅生成/更新 SSL 证书（如 IP 变了）
bash scripts/gen_ssl.sh 192.168.1.100

# 重新训练模型
python -m ml.train

# 运行单元测试
python -m pytest tests/unit/ -v

# 运行集成测试
python -m pytest tests/integration/ -v
```

---

## 六、常见问题排查

### 6.1 端口被占用

```bash
Error: Address already in use: ('0.0.0.0', 5000)
```

**解决：**
```bash
lsof -ti:5000 | xargs -r kill -9
bash scripts/run_dev.sh
```

### 6.2 手机浏览器无法访问

| 检查项 | 命令/操作 |
|--------|----------|
| 确认同一局域网 | 手机和开发机连同一个 WiFi |
| 确认开发机 IP | `hostname -I \| awk '{print $1}'` |
| 确认防火墙放行 5000 | `sudo ufw allow 5000`（或 `sudo firewall-cmd --add-port=5000/tcp`） |
| 测试连通性 | 手机浏览器临时访问 `https://<IP>:5000/api/health`（需先信任证书） |
| 用 curl 测试 | 在开发机上执行 `curl -sk https://127.0.0.1:5000/api/health` 确认服务正常 |
| 确认外网可达 | 手机浏览器访问 `https://cdn.socket.io` 确认能加载 CDN（见 6.7） |

### 6.3 手机端显示「未连接」或「初始化失败」

| 症状 | 可能原因 | 解决方案 |
|------|----------|----------|
| 页面能打开但顶部一直显示「未连接」 | Socket.IO CDN 未加载 | 检查手机能否访问外网（`cdn.socket.io`），参考 6.7 |
| 显示「初始化失败」 | CDN 在 15 秒内未加载完成 | 同上，或将 CDN 资源本地化 |
| 显示「连接失败」 | Socket.IO 握手失败 | 检查是否已完成 SSL 证书信任；确认防火墙放行 5000/tcp |
| 间断性「断开→连接」 | 网络不稳定或证书验证问题 | 降低 `ping_interval`；检查 WiFi 信号强度 |

### 6.4 手机端传感器无数据

- 确认使用 **HTTPS** 访问（DeviceMotion API 强制要求 HTTPS）
- Chrome 浏览器支持最好，微信/QQ 内置浏览器不支持
- 首次访问需授予「运动与方向」权限
- 在华为 P50 Pro 上，进入 Chrome「设置→网站设置→运动传感器」确认已开启

### 6.5 SSL 证书警告

自签名证书无法被系统信任，属于正常现象。手机浏览器需手动点「继续访问」。如需消除警告，可申请 Let's Encrypt 正式证书替换 `ssl/` 目录下的文件。

> **技术细节：** 证书 CN（Common Name）已设置为当前 LAN IP，SAN 包含 `IP:<LAN_IP>, IP:127.0.0.1, DNS:localhost`。如果开发机 IP 变更，需重新运行 `bash scripts/gen_ssl.sh <新IP>` 生成证书后重启服务。

### 6.6 Conda 环境创建失败

确认 `environment.yml` 中的版本号与 conda-forge 实际可用版本一致。当前已验证可用的版本组合：

| 包 | 版本 |
|----|------|
| Python | 3.10 |
| Flask | 3.1.3 |
| Flask-SocketIO | 5.6.1 |
| gevent | 26.5.0 |
| numpy | 2.2.6 |
| scikit-learn | 1.7.2 |
| scipy | 1.15.3 |
| pandas | 2.3.3 |

### 6.7 模型预测全是 unknown

检查模型是否正确加载：
```bash
curl -sk https://127.0.0.1:5000/api/model/info
```
应返回 `"loaded": true`。若为 `false`，检查 `artifacts/models/gait_classifier.pkl` 是否存在。

### 6.8 手机无法访问外网（CDN 加载失败）

如果手机在纯内网环境无法访问 `cdn.socket.io`，需要将 CDN 资源本地化：

```bash
# 在开发机上执行
cd ~/暑期培训/sport_reco/src/frontend/static/js/
wget https://cdn.socket.io/4.7.4/socket.io.min.js
```

然后修改 `src/frontend/templates/mobile.html` 中的 CDN 引用：
```html
<!-- 原先: -->
<script src="https://cdn.socket.io/4.7.4/socket.io.min.js"></script>
<!-- 改为: -->
<script src="{{ url_for('static', filename='js/socket.io.min.js') }}"></script>
```

> 电脑端 `index.html` 同理，如果电脑也无法访问外网需一并修改。

---

## 七、配置说明

| 配置项 | 文件 | 说明 |
|--------|------|------|
| 端口、主机 | `configs/default.yaml` → `app` | 默认 0.0.0.0:5000 |
| WebSocket 参数 | `configs/default.yaml` → `websocket` | 窗口 2s，推理间隔 1s |
| 滤波器参数 | `configs/model/preprocess.yaml` | Butterworth 4 阶，截止 20Hz |
| 特征选择 | `configs/model/features.yaml` | 时域 10 + 频域 8 特征 |
| 模型配置 | `configs/model/training.yaml` | RF 100 trees |
| 开发环境覆盖 | `configs/dev.yaml` | debug=true，日志 DEBUG 级别 |

环境变量 `SPORT_RECO_ENV=dev`（开发）或 `production`（生产）控制加载哪套配置。

**Socket.IO 架构说明：**
- 移动端自动加入 `mobile` 房间，桌面端加入 `dashboard` 房间
- 传感器数据流仅从 `mobile:motor_data` → `dashboard:sensor_stream`（定向推送到 dashboard 房间）
- 推理结果同时发送给两个房间
- 移动端优先使用 HTTP long-polling 传输（对自签名证书更友好），成功连接后自动升级到 WebSocket

---

## 八、项目文件结构

```
sport_reco/
├── environment.yml          # Conda 环境定义
├── run.md                   # 本文件
├── scripts/
│   ├── setup_env.sh         # 环境创建
│   ├── gen_ssl.sh           # SSL 证书生成
│   └── run_dev.sh           # 开发启动
├── configs/
│   ├── default.yaml         # 默认配置
│   ├── dev.yaml             # 开发环境覆盖
│   └── model/               # 模型子配置
├── src/
│   ├── app.py               # Flask 主入口
│   ├── api/
│   │   ├── routes.py        # REST API
│   │   └── socket_handlers.py  # WebSocket 处理
│   ├── core/
│   │   ├── config.py        # 配置加载器
│   │   ├── preprocess.py    # 信号预处理
│   │   └── features.py      # 特征提取
│   ├── data/
│   │   ├── database.py      # SQLite 连接
│   │   └── repository.py    # 数据访问层
│   ├── service/
│   │   ├── collector.py     # 数据采集
│   │   └── inference.py     # 推理引擎
│   └── frontend/
│       ├── templates/       # HTML 模板
│       └── static/js/       # 前端 JS
├── ml/
│   ├── train.py             # 模型训练
│   ├── dataset.py           # 数据集生成
│   └── evaluate.py          # 模型评估
├── tests/                   # 测试用例
├── artifacts/models/        # 训练好的模型
├── ssl/                     # SSL 证书
├── logs/                    # 运行日志
└── docker/                  # Docker 部署
```
