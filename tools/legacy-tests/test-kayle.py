
import requests
from bs4 import BeautifulSoup
import json
import re

def test_scrape_champion(champion_id):
    url = f"https://hextech.dtodo.cn/zh-CN/champion-stats/{champion_id}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    print(f"正在尝试抓取英雄 ID: {champion_id}...")
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        print(f"状态码: {resp.status_code}")
        
        if resp.status_code != 200:
            print("页面请求失败")
            return
            
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # 1. 尝试获取英雄名称 (通常在 <h1>)
        name_tag = soup.find('h1')
        champion_name = name_tag.get_text(strip=True) if name_tag else "未知"
        print(f"检测到英雄名称: {champion_name}")
        
        # 2. 查找推荐海克斯 (通常包含在特定的表格或 <a> 标签中)
        augments = []
        # 网站的海克斯链接通常匹配 /augments/\d+
        links = soup.find_all('a', href=re.compile(r'/augments/\d+'))
        
        for a in links:
            name = a.get('title') or a.get_text(strip=True)
            # 网站结构通常在 <tr> 中显示胜率
            parent_tr = a.find_parent('tr')
            win_rate = "未知"
            if parent_tr:
                # 在同一行中查找包含 % 的文本
                text = parent_tr.get_text()
                wr_match = re.search(r'(\d+\.?\d*)%', text)
                if wr_match:
                    win_rate = wr_match.group(1) + "%"
            
            augments.append({
                "name": name.replace('#', ''),
                "winRate": win_rate
            })
            
        # 去重
        seen = set()
        unique_augments = []
        for aug in augments:
            if aug['name'] not in seen:
                unique_augments.append(aug)
                seen.add(aug['name'])
        
        print(f"共找到 {len(unique_augments)} 个海克斯")
        
        # 打印前 5 个展示一下结果
        for i, aug in enumerate(unique_augments[:5], 1):
            print(f"  {i}. {aug['name']} - 胜率: {aug['winRate']}")
            
        # 3. 尝试抓取核心出装
        print("\n正在抓取核心出装...")
        items = []
        # 网站通常使用图片 URL 来表示装备
        item_imgs = soup.select('img[src*="item-icons"]')
        for img in item_imgs:
            item_name = img.get('alt') or "未知装备"
            if item_name not in items:
                items.append(item_name)
        
        print(f"检测到装备: {', '.join(items[:10])}")
        
    except Exception as e:
        print(f"抓取异常: {e}")

if __name__ == "__main__":
    # 天使的 ID 是 10
    test_scrape_champion(10)
