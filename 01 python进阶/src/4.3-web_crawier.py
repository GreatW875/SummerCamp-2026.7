"""
概念4 练习4：极简爬虫
从中国天气网抓取北京天气预报页面，用 BeautifulSoup 提取温度数据并打印。

知识点：
- requests.get 发请求（必须带 headers 伪装浏览器 + timeout 防卡死）
- response.status_code / response.text / response.apparent_encoding
- BeautifulSoup 解析 HTML，find / find_all 提取标签内容
- try-except 捕获网络异常
"""

import re
import requests
from bs4 import BeautifulSoup

# 北京天气预报页面（101010100 是北京的城市代码）
URL = "https://www.weather.com.cn/weather1d/101010100.shtml"

# 伪装成浏览器：很多网站会拒绝裸 Python 请求
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    )
}


def fetch_temperature(url):
    """抓取网页并提取温度数据，返回 [(原始文本, 最低温, 最高温), ...]"""
    # 1. 发请求拿网页（timeout 必须加，否则对方无响应会永久卡住）
    response = requests.get(url, headers=HEADERS, timeout=10)
    response.raise_for_status()                        # 状态码非 2xx 抛异常
    response.encoding = response.apparent_encoding      # 自动识别编码，避免中文乱码

    # 2. 解析 HTML
    soup = BeautifulSoup(response.text, "html.parser")

    # 3. 提取温度：页面里 <i> 标签文本形如 "20/30°C"（最低/最高）
    results = []
    seen = set()                                        # 用集合去重，同一温度串只记一次
    for i_tag in soup.find_all("i"):
        text = i_tag.get_text(strip=True)
        m = re.match(r"^(-?\d+)/(-?\d+)°C$", text)      # 匹配 "最低/最高°C"
        if m and text not in seen:
            seen.add(text)
            low, high = int(m.group(1)), int(m.group(2))
            results.append((text, low, high))
    return results


def main():
    try:
        temps = fetch_temperature(URL)
    except requests.exceptions.Timeout:
        print("❌ 请求超时，请检查网络或稍后重试")
        return
    except requests.exceptions.RequestException as e:
        print(f"❌ 网络请求失败: {e}")
        return

    print(f"北京天气预报（来源: {URL}）")
    print(f"共抓到 {len(temps)} 条温度记录：")
    print("-" * 40)
    for idx, (text, low, high) in enumerate(temps, 1):
        print(f"{idx:>2}. 最低 {low:>3}°C / 最高 {high:>3}°C   (原始: {text})")


if __name__ == "__main__":
    main()
