"""读取 config.json 并应用参数"""
import json
from pathlib import Path

# 读取配置文件
with open(Path(__file__).parent.parent / "cfg" / "config.json") as f:
    config = json.load(f)

threshold = config["threshold"]
window_size = config["window_size"]

# 应用参数
data = [8, 12, 5, 15, 3, 20, 9]
result = [x for x in data if x > threshold]

print(f"threshold = {threshold}, window_size = {window_size}")
print(f"原始数据: {data}")
print(f"过滤后 (> {threshold}): {result}")
print(f"窗口大小: {window_size}")

# 模拟滑动窗口
for i in range(0, len(result), window_size):
    window = result[i : i + window_size]
    print(f"窗口 {i // window_size}: {window}")
