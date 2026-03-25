
import re

def scan():
    with open('kayle_rsc_data.txt', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 搜索常见的海克斯名或关键词
    # 注意：在 RSC 中，中文可能是以 Unicode 形式存在的 (\u6211)
    # 也可能是原生的
    
    print(f"文件总长度: {len(content)}")
    
    # 尝试匹配常见的属性
    found = re.findall(r'"winRate":(\d+\.?\d*)', content)
    print(f"匹配到 'winRate' 的次数: {len(found)}")
    
    if found:
        # 打印第一个 winRate 附近的文本
        idx = content.find('"winRate"')
        print(f"第一个 winRate 附近的 300 字符:\n{content[idx-100:idx+200]}")

scan()
