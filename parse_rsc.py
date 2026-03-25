
import re
import json

def parse_rsc_file(filepath):
    print(f"--- 正在从 RSC 数据中解析 177 条海克斯 ---")
    
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    # RSC 格式有很多转义和特殊的 chunk ID
    # 我们直接利用正则提取所有像海克斯 JSON 的结构
    # 海克斯特征：{"name":"xxx","tier":"T1","winRate":59.2...}
    
    # 步骤 1: 寻找所有包含 "augments" 数组的 JSON 片段
    # 既然文件很大，我们直接找海克斯的数据块
    
    # 使用正则匹配海克斯数据的数组
    # 模式: "name":"(.*?)"
    # 我们找寻所有带有 winRate 的海克斯数据点
    
    # 提取所有海克斯对象
    # 模式: {"id":\d+,"name":"[^"]+","tier":"T[1-5]","winRate":\d+\.?\d*,"pickRate":\d+\.?\d*}
    
    # 由于 RSC 数据对引号进行了转义，我们先做一次全局替换让它好处理
    # 或者直接用针对转义 JSON 的正则
    
    # 提取方法：利用 re.finditer 寻找所有包含 name, tier, winRate 的字典
    augments = []
    
    # 匹配模式 (针对转义后的 JSON): 
    # \"name\":\"([^\"]+)\",\"tier\":\"(T[1-5])\",\"winRate\":(\d+\.?\d*)
    matches = re.finditer(r'\\"name\\":\\"([^\\"]+)\\",\\"tier\\":\\"(T[1-5])\\",\\"winRate\\":(\d+\.?\d*)', content)
    
    seen = set()
    for m in matches:
        name = m.group(1)
        tier = m.group(2)
        wr = float(m.group(3))
        
        # 提取 pickRate (通常紧跟在 winRate 后面)
        # 我们再往后搜一点
        pick_match = re.search(r'\\"pickRate\\":(\d+\.?\d*)', content[m.end():m.end()+100])
        pr = float(pick_match.group(1)) if pick_match else 0.0
        
        if name not in seen:
            augments.append({
                "name": name,
                "tier": tier,
                "winRate": f"{wr:.2f}%",
                "pickRate": f"{pr:.2f}%",
                "score": wr  # 用于排序
            })
            seen.add(name)
            
    # 按胜率排序
    augments.sort(key=lambda x: x['score'], reverse=True)
    
    # 保存结果
    result = {
        "champion": "凯尔 (Kayle)",
        "totalCount": len(augments),
        "augments": augments
    }
    
    output_file = "kayle_final_177_full.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        
    print(f"🎉 任务圆满完成！")
    print(f"成功解析出全量海克斯: {len(augments)} 条 (目标 177 条)")
    print(f"数据已保存至: {output_file}")
    
    # 打印前 10 名校验数据质量
    print("\n【海克斯胜率排行榜 (Top 10)】")
    for i, aug in enumerate(augments[:10], 1):
        print(f"  {i}. {aug['name']} ({aug['tier']}) - 胜率: {aug['winRate']} | 登场率: {aug['pickRate']}")

if __name__ == "__main__":
    parse_rsc_file("kayle_rsc_data.txt")
