
import requests
import json
import re

def extract_champion_json(champion_id):
    url = f"https://hextech.dtodo.cn/zh-CN/champion-stats/{champion_id}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    print(f"正在抓取英雄 {champion_id} 的原始 JSON 数据...")
    try:
        resp = requests.get(url, headers=headers, timeout=20)
        resp.raise_for_status()
        
        # 查找 Next.js 的页面数据脚本
        match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', resp.text, re.DOTALL)
        if not match:
            print("未找到 __NEXT_DATA__ 脚本")
            return
            
        json_data = json.loads(match.group(1))
        
        # 深入挖掘数据 (Next.js 的结构通常在 props.pageProps 中)
        page_props = json_data.get('props', {}).get('pageProps', {})
        champion_data = page_props.get('championStats', {})
        
        if not champion_data:
            print("脚本中未发现 championStats 数据")
            # 尝试打印出 pageProps 的键，看看结构
            print(f"可用数据键: {list(page_props.keys())}")
            return

        # 整理输出 (这部分会包含全量的海克斯)
        result = {
            "name": champion_data.get('championName', '未知'),
            "id": champion_id,
            "version": champion_data.get('version', '未知'),
            "augments": [],
            "items": []
        }
        
        # 提取全量海克斯
        # 注意：这里的数据通常是非常干净的，没有 T1/T2 干扰
        augments_list = champion_data.get('augments', [])
        print(f"成功找到全量海克斯: {len(augments_list)} 条")
        
        for aug in augments_list:
            result['augments'].append({
                "id": aug.get('id'),
                "name": aug.get('name'),
                "tier": aug.get('tier'),
                "winRate": f"{aug.get('winRate', 0):.2f}%",
                "pickRate": f"{aug.get('pickRate', 0):.2f}%"
            })
            
        # 提取装备数据
        build_configs = champion_data.get('buildConfigs', [])
        if build_configs:
            # 取第一套配置作为参考
            first_config = build_configs[0]
            for item in first_config.get('situationalItems', []):
                result['items'].append(item.get('name'))

        # 保存为 JSON
        filename = f"kayle_full_data_{champion_id}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
            
        print(f"数据已保存至 {filename}")
        print("\n前 5 条海克斯预览:")
        for i, aug in enumerate(result['augments'][:5], 1):
            print(f"  {i}. {aug['name']} (Tier: {aug['tier']}) - 胜率: {aug['winRate']}")

    except Exception as e:
        print(f"提取失败: {e}")

if __name__ == "__main__":
    # 凯尔 ID 10
    extract_champion_json(10)
