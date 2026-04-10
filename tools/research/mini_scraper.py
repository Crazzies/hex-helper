import requests
from bs4 import BeautifulSoup
import json
import re

def scrape_champion(champion_id):
    url = f"https://hextech.dtodo.cn/zh-CN/champion-stats/{champion_id}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    print(f"正在抓取英雄 {champion_id}...")
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # 寻找海克斯链接
        augments = []
        links = soup.find_all('a', href=re.compile(r'/augments/\d+'))
        for a in links:
            name = a.get('title') or a.get_text(strip=True)
            # 寻找胜率 (在父级单元格中)
            parent_text = a.find_parent('tr').get_text() if a.find_parent('tr') else ""
            wr_match = re.search(r'(\d+\.?\d*)%', parent_text)
            win_rate = wr_match.group(0) if wr_match else "??%"
            
            augments.append({"name": name.replace('#', ''), "winRate": win_rate})
        
        # 去重
        seen = set()
        unique_augments = []
        for aug in augments:
            if aug['name'] not in seen:
                unique_augments.append(aug)
                seen.add(aug['name'])
        
        result = {
            "situationalItems": ["纳什之牙", "兰德里的折磨"], # 简化处理
            "prismatic": unique_augments[:20],
            "gold": unique_augments[20:40],
            "silver": unique_augments[40:60]
        }
        
        with open(f"cache/hero-builds/{champion_id}.json", "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"成功！已保存数据到 cache/hero-builds/{champion_id}.json")
        
    except Exception as e:
        print(f"抓取失败: {e}")

if __name__ == "__main__":
    scrape_champion(876)
