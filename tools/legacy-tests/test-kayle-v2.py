
import requests
from bs4 import BeautifulSoup
import json
import re

def fix_scrape_champion(champion_id):
    url = f"https://hextech.dtodo.cn/zh-CN/champion-stats/{champion_id}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    print(f"正在尝试抓取英雄 ID: {champion_id}...")
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            print("页面请求失败")
            return
            
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # 1. 英雄名称
        name_tag = soup.find('h1')
        champion_name = name_tag.get_text(strip=True) if name_tag else "未知"
        
        # 2. 海克斯
        augments = []
        # 找到所有海克斯链接
        links = soup.find_all('a', href=re.compile(r'/augments/\d+'))
        
        for a in links:
            name = a.get('title') or a.get_text(strip=True)
            # 处理 # 名称
            name = name.replace('#', '').strip()
            
            # 找到父级 tr
            parent_tr = a.find_parent('tr')
            if not parent_tr: continue
            
            text = parent_tr.get_text()
            
            # --- 关键：层级与胜率剥离逻辑 ---
            # 原文可能是 "T159.20%"，我们要提取 T1 和 59.20%
            tier = "未知"
            win_rate = "0.00%"
            
            # 匹配模式：(T层级)(胜率)
            match = re.search(r'(T[1-5])(\d+\.?\d*)%', text)
            if match:
                tier = match.group(1)
                win_rate = match.group(2) + "%"
            else:
                # 备选匹配：如果没有 T 层级，直接找百分比
                wr_match = re.search(r'(\d+\.?\d*)%', text)
                if wr_match:
                    win_rate = wr_match.group(0)
            
            augments.append({
                "name": name,
                "tier": tier,
                "winRate": win_rate
            })
            
        # 去重并排序 (按胜率)
        seen = set()
        unique_augments = []
        for aug in augments:
            if aug['name'] not in seen:
                unique_augments.append(aug)
                seen.add(aug['name'])
        
        # 3. 提取装备
        items = []
        item_imgs = soup.select('img[src*="item-icons"]')
        for img in item_imgs:
            item_name = img.get('alt') or ""
            if item_name and item_name not in items:
                items.append(item_name)
        
        result = {
            "championName": champion_name,
            "id": champion_id,
            "augmentsCount": len(unique_augments),
            "augments": unique_augments,
            "items": items
        }
        
        # 保存
        filename = f"kayle_fixed_{champion_id}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
            
        print(f"抓取成功！保存到 {filename}")
        print(f"找到海克斯数量: {len(unique_augments)}")
        print("\n前 5 条海克斯校验:")
        for i, aug in enumerate(unique_augments[:5], 1):
            print(f"  {i}. {aug['name']} - 层级: {aug['tier']} - 胜率: {aug['winRate']}")

    except Exception as e:
        print(f"抓取异常: {e}")

if __name__ == "__main__":
    fix_scrape_champion(10)
