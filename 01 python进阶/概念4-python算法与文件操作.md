# 概念4：Python算法与文件操作

## 文件操作：`with open` 基本用法

### 为什么用 `with open`

`open()` 和 `with` 都是 **Python 原生内置**，无需 import。`with` 语句能**自动关闭文件句柄**，即使中途报错也不会漏关，是官方推荐的写法。

```python
# ❌ 手动 open + close：read() 报错时 close() 永远执行不到
f = open('data.txt', 'r', encoding='utf-8')
content = f.read()
f.close()

# ✅ with open：出 with 块自动关闭，无论正常或异常
with open('data.txt', 'r', encoding='utf-8') as f:
    content = f.read()
```

> 文件句柄是操作系统管理的有限资源（Linux 默认单进程 1024 个）。循环里反复 `open` 不 `close`，会触发 `OSError: Too many open files`。

### `open()` 最常用参数

| 参数 | 说明 | 常用取值 |
|------|------|---------|
| `file` | 文件路径（必填） | 字符串或 `Path` 对象，如 `'data.txt'` |
| `mode` | 打开模式 | `'r'`（读，默认）、`'w'`（覆盖写）、`'a'`（追加）、`'b'`（二进制）、`'r+'`（读写） |
| `encoding` | 文本编码（文本模式强烈建议加） | `'utf-8'`（跨平台首选） |
| `errors` | 解码出错处理 | `'ignore'`（跳过）、`'replace'`（替换为�） |
| `newline` | 换行符控制 | 写 CSV 用 `''` 避免 Windows 空行 |

**mode 主字符对比：**

| 模式 | 含义 | 文件不存在 | 文件已存在 |
|------|------|-----------|-----------|
| `'r'` | 只读（默认） | 报错 | 从头读 |
| `'w'` | 只写 | 创建 | **清空原内容** |
| `'a'` | 追加 | 创建 | 末尾追加 |
| `'x'` | 独占创建 | 创建 | 报错（防覆盖） |
| `'r+'` | 读写 | 报错 | 保留内容 |

> 修饰符 `'t'`（文本，默认）/ `'b'`（二进制）可叠加，如 `'rb'` 读图片、`'wb'` 写二进制。二进制模式原样读写字节，文本模式会做换行符转换和编码解码。

### 打开文件最常用的例子

```python
# ① 读文本（配置、日志）—— 一次读完，适合小文件
with open('data.txt', 'r', encoding='utf-8') as f:
    text = f.read()

# ② 读大文件 —— 逐行迭代，内存友好
with open('huge_log.csv', 'r', encoding='utf-8') as f:
    for line in f:
        process(line)

# ③ 写文本（覆盖）
with open('out.txt', 'w', encoding='utf-8') as f:
    f.write('hello')

# ④ 追加文本（日志）
with open('log.txt', 'a', encoding='utf-8') as f:
    f.write('new line\n')

# ⑤ 读/写二进制（图片、模型权重、pickle）
with open('model.pkl', 'rb') as f:
    data = f.read()
with open('copy.png', 'wb') as f:
    f.write(img_bytes)

# ⑥ 同时打开多个文件（3.10+ 推荐括号写法）
with (
    open('in.txt', encoding='utf-8') as fin,
    open('out.txt', 'w', encoding='utf-8') as fout,
):
    fout.write(fin.read())
```

> **口诀**：读 `'r'`，覆盖写 `'w'`，追加 `'a'`，二进制加 `'b'`，文本加 `encoding='utf-8'`。

### 文件对象的读写方法

以 `with open(...) as f:` 中的 `f` 为例：

| 方法 | 作用 | 返回 / 注意 |
|------|------|------------|
| `f.read(size=-1)` | 一次读取全部（或前 `size` 个字符/字节） | 返回 `str`（文本）或 `bytes`（二进制）；大文件慎用 |
| `f.readline()` | 读一行 | 返回带末尾 `\n` 的字符串；到文件末尾返回 `''` |
| `f.readlines()` | 读所有行存成列表 | 返回 `list[str]`，每行一个元素；大文件占内存 |
| `for line in f` | 逐行迭代（推荐） | 惰性读取，内存友好，处理大文件首选 |
| `f.write(s)` | 写入字符串/字节 | 返回写入的字符/字节数；不会自动加换行 |
| `f.writelines(lst)` | 批量写入列表 | 元素需自带 `\n`，不会自动换行 |
| `f.tell()` | 返回当前文件指针位置 | 整数 |
| `f.seek(offset)` | 移动文件指针 | 如 `f.seek(0)` 回到开头 |
| `f.flush()` | 把缓冲区刷到磁盘 | 不关闭文件，常用于日志实时落盘 |
| `f.close()` | 关闭文件 | `with` 会自动调用，无需手写 |

> 对比记忆：`read()` 全读、`readline()` 读一行、`readlines()` 读成列表；写对应 `write()`。**处理大文件用 `for line in f`，不要 `readlines()`。**

### `os` 与 `pathlib` 对比

`pathlib`（Python 3.4+）是面向对象的路径库，路径相关操作更直观 Pythonic；`os` 在系统/进程相关操作上仍不可替代。

| 功能 | `os` 写法 | `pathlib` 写法 | 推荐 |
|------|----------|---------------|------|
| 拼接路径 | `os.path.join('a','b.csv')` | `Path('a') / 'b.csv'` | pathlib |
| 当前脚本目录 | `os.path.dirname(__file__)` | `Path(__file__).parent` | pathlib |
| 绝对路径 | `os.path.abspath(p)` | `Path(p).resolve()` | pathlib |
| 文件名 | `os.path.basename(p)` | `Path(p).name` | pathlib |
| 后缀名 | `os.path.splitext(p)[1]` | `Path(p).suffix` | pathlib |
| 无后缀名 | `os.path.splitext(p)[0]` | `Path(p).stem` | pathlib |
| 判断存在 | `os.path.exists(p)` | `Path(p).exists()` | 均可 |
| 判断文件/目录 | `os.path.isfile/`isdir`` | `Path(p).is_file/`is_dir()` | pathlib |
| 列出目录文件 | `os.listdir('data')` | `list(Path('data').iterdir())` | pathlib |
| 通配匹配 | `glob` 模块 | `list(Path('data').glob('*.csv'))` | pathlib |
| 递归匹配 | `glob(recursive=True)` | `Path('data').rglob('*.csv')` 或 `glob('**/*.csv')` | pathlib |
| 创建目录 | `os.makedirs(p, exist_ok=True)` | `Path(p).mkdir(parents=True, exist_ok=True)` | pathlib |
| 读小文件 | `open(p).read()` | `Path(p).read_text(encoding='utf-8')` | pathlib |
| 写小文件 | `open(p,'w').write(s)` | `Path(p).write_text(s, encoding='utf-8')` | pathlib |
| 环境变量 | `os.getenv('HOME')` | —— | os |
| 执行系统命令 | `os.system('ls')` | —— | os |
| 进程 ID | `os.getpid()` | —— | os |

> **结论**：路径拼接、查找、判断、小文件读写 → 优先 `pathlib`；环境变量、系统命令、进程相关 → 仍用 `os`。

## 三种查找方式对比

查找问题的本质是"在数据里找东西"。三种策略速度差距巨大：`n=100万` 时，线性查找最多 100 万次，二分查找约 20 次，哈希表 1 次。

| 查找方式 | 核心思路 | 数据前提 | 时间复杂度 | 适用场景 |
|---------|---------|---------|-----------|---------|
| **线性查找** | 从头到尾逐个比对 | 无 | O(n) | 数据量小、或只查一次 |
| **二分查找** | 每次从中间切，丢掉一半，在剩余里继续切 | **必须有序** | O(log n) | 数据量大、有序、查多次 |
| **哈希表（字典）** | 按 key 算出地址，直接定位 | 无（用空间换时间） | O(1) | 查很多次、能接受多占内存 |

**决策一句话**：小/查一次→线性；大/有序/查多次→二分；查很多次→哈希表。

## 爬虫基础：`requests` + `BeautifulSoup`

爬虫本质就两步：① 向服务器发请求拿网页；② 从 HTML 里提取要的数据。分别对应 `requests` 和 `BeautifulSoup` 两个库。

### `requests` 用法

发送 HTTP 请求、模拟浏览器访问网页。`pip install requests`。

```python
import requests

response = requests.get(url, headers=headers, timeout=10)   # 发 GET 请求
response.raise_for_status()          # 状态码 4xx/5xx 抛异常
response.encoding = response.apparent_encoding   # 自动识别编码，避免中文乱码
print(response.status_code)          # 200 成功
print(response.text)                 # HTML 源码字符串
```

三个必懂参数：
- **`headers`**：伪装成浏览器（带 `User-Agent`），否则很多网站返回 403 拒绝裸 Python 请求。
- **`timeout`**：超时秒数，**必须加**，否则对方无响应程序会永久卡死。
- **`params`**：URL 查询参数，传字典自动拼成 `?key=value`，不用手拼字符串。

常用属性：`status_code`（状态码）、`text`（HTML 文本）、`content`（二进制，下图片用）、`json()`（JSON 响应直接转 dict/list）、`apparent_encoding`（自动探测编码）。

异常处理（网络不稳定是常态，必须捕获）：
```python
try:
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
except requests.exceptions.Timeout:
    print('超时')
except requests.exceptions.RequestException as e:   # 所有 requests 异常基类
    print(f'请求出错: {e}')
```

### `BeautifulSoup` 用法

把 HTML 文本解析成"标签树"，方便查找标签、属性、文本。`pip install beautifulsoup4`（包名带 4）。

```python
from bs4 import BeautifulSoup

soup = BeautifulSoup(html_text, 'html.parser')   # 'html.parser' 是 Python 内置解析器
```

四个最常用提取方法：
- `soup.find('tag')` —— 找**第一个**匹配标签，返回单个 Tag（找不到返回 `None`）
- `soup.find_all('tag')` —— 找**所有**匹配，返回列表
- `soup.select('css选择器')` —— CSS 选择器查找，最灵活，返回列表
- `soup.select_one('css选择器')` —— CSS 选择器找第一个

可加过滤条件：`find_all('p', class_='temp')`（`class_` 带下划线，因为 `class` 是关键字）、`find('div', id='main')`、`find_all('p', limit=5)`。

取内容与属性：
- `tag.text` —— 标签里的纯文本
- `tag['href']` —— 取属性（不存在会报 KeyError）
- `tag.get('href')` —— 取属性（不存在返回 None，更安全）

CSS 选择器速查：`.temp`（class）、`#main`（id）、`div.weather p`（后代）、`div > p`（直接子级）。

### 标准流程

```python
import requests
from bs4 import BeautifulSoup

# 1. requests 拿网页
response = requests.get(url, headers=headers, timeout=10)
response.raise_for_status()
response.encoding = response.apparent_encoding

# 2. BeautifulSoup 解析 HTML
soup = BeautifulSoup(response.text, 'html.parser')

# 3. 提取数据
for tag in soup.find_all('i'):
    print(tag.text)
```

### 两者功能对比

| 维度 | `requests` | `BeautifulSoup` |
|------|-----------|----------------|
| 职责 | 通信（发请求、收响应） | 解析（处理 HTML 文本） |
| 输入 | URL + 参数 | HTML 字符串 |
| 输出 | Response 对象 | 标签树（可查询） |
| 核心方法 | `get` / `post` | `find` / `find_all` / `select` |
| 必加项 | `headers` + `timeout` | 解析器 `'html.parser'` |
| 安装 | `pip install requests` | `pip install beautifulsoup4` |
| 类比 | 去图书馆借书 | 从借来的书里找某段话 |

> 一句话记忆：**requests 负责把网页"下载"下来，BeautifulSoup 负责从 HTML 里"找"你要的数据。**
 