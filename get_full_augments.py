
import requests
import re
import json

def get_full_data(champion_id):
    base_url = "https://hextech.dtodo.cn"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    print(f"--- 正在攻克全量数据 (ID: {champion_id}) ---")
    
    # 1. 访问主页获取 Build ID
    try:
        main_url = f"{base_url}/zh-CN/champion-stats/{champion_id}"
        resp = requests.get(main_url, headers=headers, timeout=15)
        
        # 提取 buildId
        build_id_match = re.search(r'"buildId":"(.*?)"', resp.text)
        if not build_id_match:
            print("无法获取 buildId，尝试备用解析...")
            # 备用：从 __NEXT_DATA__ 脚本块中找
            data_match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', resp.text, re.DOTALL)
            if data_match:
                json_raw = json.loads(data_match.group(1))
                build_id = json_raw.get('buildId')
            else:
                print("严重错误：无法找到 Next.js 运行标志")
                return
        else:
            build_id = build_id_match.group(1)
            
        print(f"成功获取 Build ID: {build_id}")
        
        # 2. 构建全量数据 API 地址
        # Next.js 默认的数据接口路径规律
        api_url = f"{base_url}/_next/data/{build_id}/zh-CN/champion-stats/{champion_id}.json"
        print(f"正在请求全量 API: {api_url}")
        
        api_resp = requests.get(api_url, headers=headers, timeout=15)
        if api_resp.status_code != 200:
            print(f"API 请求失败 (状态码: {api_resp.status_code})，可能路径规则已变。")
            return
            
        full_json = api_resp.json()
        
        # 3. 解析全量海克斯
        # 路径通常在: props -> pageProps -> championStats -> augments
        stats = full_json.get('pageProps', {}).get('championStats', {})
        if not stats:
            # 兼容不同版本 Next.js 结构
            stats = full_json.get('props', {}).get('pageProps', {}).get('championStats', {})
            
        augments = stats.get('augments', [])
        print(f"🎉 成功拿到全量海克斯！总计: {len(augments)} 条")
        
        # 格式化
        result = {
            "name": stats.get('championName'),
            "count": len(augments),
            "augments": []
        }
        
        for aug in augments:
            result['augments'].append({
                "name": aug.get('name'),
                "tier": aug.get('tier'),
                "winRate": f"{aug.get('winRate', 0):.2f}%",
                "pickRate": f"{aug.get('pickRate', 0):.2f}%"
            })
            
        # 排序并保存
        with open(f"kayle_full_177_{champion_id}.json", "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
            
        print(f"全量数据已保存至 kayle_full_177_{champion_id}.json")
        
        # 打印验证
        print("\n验证全量抓取结果 (前 10 条):")
        for i, aug in enumerate(result['augments'][:10], 1):
            print(f"  {i}. {aug['name']} ({aug['tier']}) - 胜率: {aug['winRate']}")

    except Exception as e:
        print(f"全量抓取异常: {e}")

if __name__ == "__main__":
    get_full_data(10)
