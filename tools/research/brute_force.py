
import requests
from bs4 import BeautifulSoup
import re
import json

def brute_force_extract_augments(champion_id):
    url = f"https://hextech.dtodo.cn/zh-CN/champion-stats/{champion_id}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    print(f"--- 开启暴力搜索 (全量提取) ---")
    resp = requests.get(url, headers=headers, timeout=20)
    
    # 策略 1: 寻找任何包含海克斯 ID 和名称的 JSON 结构
    # 海克斯通常有 id, name, winRate 字段
    # 正则搜索所有的 JSON 对象
    json_blobs = re.findall(r'(\{.*?\})', resp.text)
    print(f"初步扫描到 {len(json_blobs)} 个可能的 JSON 片段")
    
    # 策略 2: 既然 HTML 只显示 25 个，但“显示全部 177 条”存在
    # 很有可能这 177 条就在某个脚本的数组里
    all_names = re.findall(r'"name":"(.*?)"', resp.text)
    unique_names = list(set(all_names))
    print(f"源码中所有包含 'name' 的字段数: {len(all_names)}，去重后: {len(unique_names)}")
    
    # 策略 3: 如果全量数据不在 HTML 里，那它一定是当你点击时去服务器拿的
    # 但是我们现在没有动态分析工具，我决定尝试一种“盲搜”API 的方法
    # 很多 Next.js 站点的数据接口是这样的:
    # https://hextech.dtodo.cn/zh-CN/champion-stats/10?_data=routes%2Fchampion-stats%2F%24championId
    
    # 我先保存整个 HTML，让你看看
    with open("full_page_source.html", "w", encoding="utf-8") as f:
        f.write(resp.text)
    print("全量源码已保存到 full_page_source.html")
    
    # 如果全量数据就在源码里，这个搜索能证明:
    # 查找是否有 177 个相似的结构
    aug_matches = re.findall(r'href=\"/augments/\d+\"', resp.text)
    print(f"HTML 源码中 href=\"/augments/xxx\" 的出现次数: {len(aug_matches)}")

if __name__ == "__main__":
    brute_force_extract_augments(10)
