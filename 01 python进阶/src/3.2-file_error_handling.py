"""捕获文件不存在异常并创建空文件 —— 使用 loguru 记录日志"""
import os
from pathlib import Path
from loguru import logger

# 0. 定位项目根目录（src/ 的上级 = 01 python/）
PROJECT_DIR = Path(__file__).parent.parent

# 1. 配置日志：文件写入项目根目录
logger.add(PROJECT_DIR / "data" / "file_error.log", rotation="1 MB",
           format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}")

# 2. 指定要操作的文件（在项目根目录下）
filename = PROJECT_DIR / "data" / "missing.csv"

# 3. 尝试打开文件（只读模式 'r'）
try:
    with open(filename) as f:       # 尝试以只读模式打开
        content = f.read()          # 读取文件内容
        logger.info(f"读取成功，文件内容: {content}")

# 4. 如果文件不存在，捕获异常
except FileNotFoundError:
    # 5. 使用 ERROR 级别记录异常日志
    logger.error(f"文件 '{filename}' 不存在，即将创建空文件代替")

    # 6. 以写入模式打开，创建空文件代替
    with open(filename, "w") as f:  # 'w' 模式：文件不存在则自动创建
        f.write("")

    # 7. 使用 INFO 级别记录创建成功
    logger.info(f"空文件已创建: {filename.absolute()}")
