#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hextech.dtodo.cn 数据抓取脚本
用于抓取英雄的推荐海克斯和情境装备数据
"""

import requests
from bs4 import BeautifulSoup
import json
import re
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from urllib.parse import urljoin


@dataclass
class Augment:
    """海克斯强化数据"""
    id: int
    name: str
    tier: str
    win_rate: float
    pick_rate: float
    icon_url: str


@dataclass
class Item:
    """装备数据"""
    id: int
    name: str
    icon_url: str


@dataclass
class CoreBuild:
    """核心出装方案"""
    rank: int
    items: List[Item]
    win_rate: float
    pick_rate: float


@dataclass
class BuildConfig:
    """装备配置"""
    build_type: str
    win_rate: float
    core_builds: List[CoreBuild]
    situational_items: List[Item]
    starter_items: List[Item]


@dataclass
class AugmentCombo:
    """海克斯组合"""
    rank: int
    augments: List[Augment]
    tier: str


@dataclass
class ChampionData:
    """英雄完整数据"""
    champion_id: int
    champion_name: str
    version: str
    tier: str
    win_rate: float
    pick_rate: float
    augments: List[Augment]
    augment_combos: List[AugmentCombo]
    build_configs: List[BuildConfig]


class HextechScraper:
    """Hextech数据抓取器"""
    
    BASE_URL = "https://hextech.dtodo.cn"
    CDN_URL = "https://cdn.dtodo.cn/hextech"
    
    # 装备ID到名称的映射（常见装备）
    ITEM_NAMES = {
        2503: "黯炎火炬",
        3020: "法师之靴",
        6653: "兰德里的折磨",
        3116: "瑞莱的冰晶节杖",
        4629: "星界驱驰",
        3157: "中娅沙漏",
        3165: "莫雷洛秘典",
        3089: "灭世者的死亡之帽",
        3118: "残疫",
        4645: "影焰",
        6655: "卢登的回声",
        3158: "明朗之靴",
        2031: "复用型药水",
        3802: "遗失的章节",
        3147: "幽魂面具",
        # 可以根据需要继续添加更多装备
    }
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        })
    
    def _get_item_name(self, item_id: int) -> str:
        """获取装备名称"""
        return self.ITEM_NAMES.get(item_id, f"装备_{item_id}")
    
    def fetch_champion_page(self, champion_id: int, lang: str = "zh-CN") -> Optional[str]:
        """
        获取英雄详情页面HTML
        
        Args:
            champion_id: 英雄ID
            lang: 语言代码
            
        Returns:
            HTML内容或None
        """
        url = f"{self.BASE_URL}/{lang}/champion-stats/{champion_id}"
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"获取页面失败: {e}")
            return None
    
    def parse_situational_items(self, soup: BeautifulSoup) -> List[Item]:
        """
        解析情境装备数据
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            情境装备列表
        """
        items = []
        
        # 查找"情境装备"标题
        situational_heading = soup.find(string=re.compile(r'情境装备'))
        if not situational_heading:
            return items
        
        # 获取情境装备区域
        situational_section = situational_heading.find_parent('h3') or situational_heading.find_parent()
        if not situational_section:
            return items
        
        # 查找该区域内的所有装备图片
        # 方法1: 直接查找所有img标签
        imgs = situational_section.find_all('img')
        for img in imgs:
            src = img.get('src', '')
            # 从URL中提取装备ID
            match = re.search(r'/item-icons/(\d+)\.png', src)
            if match:
                item_id = int(match.group(1))
                # 尝试从alt属性获取装备名称
                item_name = img.get('alt', '') or self._get_item_name(item_id)
                item = Item(
                    id=item_id,
                    name=item_name,
                    icon_url=src if src.startswith('http') else urljoin(self.CDN_URL, src)
                )
                items.append(item)
        
        # 方法2: 如果没找到，查找后续兄弟元素中的图片
        if not items:
            next_elem = situational_section.find_next_sibling()
            while next_elem and next_elem.name != 'h3':  # 直到下一个h3标题
                imgs = next_elem.find_all('img')
                for img in imgs:
                    src = img.get('src', '')
                    match = re.search(r'/item-icons/(\d+)\.png', src)
                    if match:
                        item_id = int(match.group(1))
                        item_name = img.get('alt', '') or self._get_item_name(item_id)
                        item = Item(
                            id=item_id,
                            name=item_name,
                            icon_url=src if src.startswith('http') else urljoin(self.CDN_URL, src)
                        )
                        if item_id not in [i.id for i in items]:  # 去重
                            items.append(item)
                next_elem = next_elem.find_next_sibling()
        
        return items
    
    def parse_augments(self, soup: BeautifulSoup) -> List[Augment]:
        """
        解析推荐海克斯数据
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            海克斯列表
        """
        augments = []
        
        # 查找"海克斯推荐"标题
        augment_heading = soup.find(string=re.compile(r'海克斯推荐'))
        if not augment_heading:
            return augments
        
        # 获取海克斯表格或列表区域
        augment_section = augment_heading.find_parent('h2') or augment_heading.find_parent()
        if not augment_section:
            return augments
        
        # 查找所有海克斯链接（在推荐区域内）
        # 先找到包含海克斯列表的表格或容器
        augment_list = augment_section.find_next_sibling()
        if not augment_list:
            augment_list = soup
        
        # 查找所有海克斯链接
        augment_links = augment_list.find_all('a', href=re.compile(r'/augments/\d+'))
        
        seen_ids = set()
        for link in augment_links:
            href = link.get('href', '')
            match = re.search(r'/augments/(\d+)', href)
            if match:
                augment_id = int(match.group(1))
                if augment_id in seen_ids:
                    continue
                seen_ids.add(augment_id)
                
                # 获取海克斯名称（从title属性）
                name = link.get('title', '')
                if not name:
                    # 如果没有title，尝试从链接文本获取
                    name = link.get_text(strip=True)
                    # 去掉#号前缀
                    name = re.sub(r'^#', '', name)
                
                # 尝试获取图标URL
                img = link.find('img')
                icon_url = ''
                if img:
                    icon_url = img.get('src', '')
                    # 如果图标URL是相对路径，转换为绝对路径
                    if icon_url and not icon_url.startswith('http'):
                        icon_url = urljoin(self.CDN_URL, icon_url)
                
                # 尝试从父元素或相邻元素获取统计数据
                win_rate = 0.0
                pick_rate = 0.0
                tier = "T1"
                
                # 查找父元素中的统计数据
                parent = link.find_parent(['tr', 'div', 'li', 'td'])
                if parent:
                    # 获取父元素及其后续兄弟元素的文本
                    text = parent.get_text()
                    # 查找所有百分比数字
                    percentages = re.findall(r'(\d+\.?\d*)%', text)
                    if len(percentages) >= 2:
                        win_rate = float(percentages[0])
                        pick_rate = float(percentages[1])
                    elif len(percentages) == 1:
                        win_rate = float(percentages[0])
                    
                    # 提取层级
                    tier_match = re.search(r'(T[1-5])', text)
                    if tier_match:
                        tier = tier_match.group(1)
                
                augment = Augment(
                    id=augment_id,
                    name=name,
                    tier=tier,
                    win_rate=win_rate,
                    pick_rate=pick_rate,
                    icon_url=icon_url
                )
                augments.append(augment)
        
        return augments[:150]  # 限制返回前150个（页面显示"显示全部 150 条"）
    
    def _extract_item_id_from_url(self, url: str) -> Optional[int]:
        """从装备图标URL中提取装备ID"""
        match = re.search(r'/item-icons/(\d+)\.png', url)
        if match:
            return int(match.group(1))
        return None
    
    def _extract_augment_id_from_url(self, url: str) -> Optional[int]:
        """从海克斯链接URL中提取ID"""
        match = re.search(r'/augments/(\d+)', url)
        if match:
            return int(match.group(1))
        return None
    
    def _extract_augment_name_from_icon_url(self, url: str) -> str:
        """从海克斯图标URL中提取名称"""
        match = re.search(r'/augment-icons/([^_]+)_small\.png', url)
        if match:
            # 将下划线分隔的名称转换为可读格式
            name = match.group(1)
            # 这里可以添加名称映射表
            return name
        return ""
    
    def parse_core_builds(self, soup: BeautifulSoup) -> List[CoreBuild]:
        """
        解析核心出装方案
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            核心出装方案列表
        """
        builds = []
        
        # 查找"核心装备"标题
        core_heading = soup.find(string=re.compile(r'核心装备'))
        if not core_heading:
            return builds
        
        # 获取核心装备区域
        core_section = core_heading.find_parent('h3') or core_heading.find_parent()
        if not core_section:
            return builds
        
        # 查找所有出装方案（通常以#1, #2, #3等标识）
        # 在核心装备区域内查找
        build_markers = core_section.find_all(string=re.compile(r'^#\d+'))
    
    def parse_starter_items(self, soup: BeautifulSoup) -> List[Item]:
        """
        解析出门装
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            出门装列表
        """
        items = []
        
        # 查找"出门装"标题
        starter_heading = soup.find(string=re.compile(r'出门装'))
        if not starter_heading:
            return items
        
        # 获取出门装区域
        starter_section = starter_heading.find_parent('h3') or starter_heading.find_parent()
        if not starter_section:
            return items
        
        # 查找该区域内的所有装备图片
        imgs = starter_section.find_all('img')
        for img in imgs:
            src = img.get('src', '')
            match = re.search(r'/item-icons/(\d+)\.png', src)
            if match:
                item_id = int(match.group(1))
                item_name = img.get('alt', '') or self._get_item_name(item_id)
                item = Item(
                    id=item_id,
                    name=item_name,
                    icon_url=src if src.startswith('http') else urljoin(self.CDN_URL, src)
                )
                items.append(item)
        
        # 如果没找到，查找后续兄弟元素中的图片
        if not items:
            next_elem = starter_section.find_next_sibling()
            while next_elem and next_elem.name != 'h3':
                imgs = next_elem.find_all('img')
                for img in imgs:
                    src = img.get('src', '')
                    match = re.search(r'/item-icons/(\d+)\.png', src)
                    if match:
                        item_id = int(match.group(1))
                        item_name = img.get('alt', '') or self._get_item_name(item_id)
                        item = Item(
                            id=item_id,
                            name=item_name,
                            icon_url=src if src.startswith('http') else urljoin(self.CDN_URL, src)
                        )
                        if item_id not in [i.id for i in items]:  # 去重
                            items.append(item)
                next_elem = next_elem.find_next_sibling()
        
        return items
    
    def parse_build_configs(self, soup: BeautifulSoup) -> List[BuildConfig]:
        """
        解析所有装备配置
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            装备配置列表
        """
        configs = []
        
        # 查找"装备配置"区域
        build_heading = soup.find(string=re.compile(r'装备配置'))
        if not build_heading:
            return configs
        
        # 获取版本号
        version = "16.6"  # 默认值
        build_section = build_heading.find_parent('h3') or build_heading.find_parent()
        if build_section:
            text = build_section.get_text()
            version_match = re.search(r'(\d+\.\d+)', text)
            if version_match:
                version = version_match.group(1)
        
        # 查找所有出装类型（AP, APBruiser等）
        # 这些通常在装备配置标题后面
        build_types = []
        if build_section:
            # 查找后续兄弟元素中的出装类型
            next_elem = build_section.find_next_sibling()
            while next_elem:
                text = next_elem.get_text(strip=True)
                if re.match(r'^(AP|AD|Tank|Support|APBruiser|ADAssassin|Fighter|Mage|Marksman)
    
    def parse_augment_combos(self, soup: BeautifulSoup) -> List[AugmentCombo]:
        """
        解析推荐海克斯组合
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            海克斯组合列表
        """
        combos = []
        
        # 查找"推荐海克斯组合"标题
        combo_heading = soup.find(string=re.compile(r'推荐海克斯组合'))
        if not combo_heading:
            return combos
        
        # 获取组合区域
        combo_section = combo_heading.find_parent('h3') or combo_heading.find_parent()
        if not combo_section:
            return combos
        
        # 查找所有组合（通常以#组合1, #组合2等标识）
        combo_markers = combo_section.find_all(string=re.compile(r'^#组合\d+
    
    def parse_champion_info(self, soup: BeautifulSoup) -> Dict:
        """
        解析英雄基本信息
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            英雄信息字典
        """
        info = {
            'champion_id': 0,
            'champion_name': '',
            'version': '16.6',
            'tier': 'T1',
            'win_rate': 0.0,
            'pick_rate': 0.0
        }
        
        # 获取英雄名称
        name_heading = soup.find('h1')
        if name_heading:
            info['champion_name'] = name_heading.get_text(strip=True)
        
        # 获取版本
        version_elem = soup.find(string=re.compile(r'版本:\s*\d+\.\d+'))
        if version_elem:
            match = re.search(r'(\d+\.\d+)', version_elem)
            if match:
                info['version'] = match.group(1)
        
        # 获取层级
        tier_elem = soup.find(string=re.compile(r'^T[1-5]$'))
        if tier_elem:
            info['tier'] = tier_elem.get_text(strip=True)
        
        # 获取胜率和选取率
        text = soup.get_text()
        win_match = re.search(r'胜率\s*\n?\s*(\d+\.?\d*)%', text)
        if win_match:
            info['win_rate'] = float(win_match.group(1))
        
        pick_match = re.search(r'选取率\s*\n?\s*(\d+\.?\d*)%', text)
        if pick_match:
            info['pick_rate'] = float(pick_match.group(1))
        
        # 从URL获取英雄ID
        canonical = soup.find('link', rel='canonical')
        if canonical:
            href = canonical.get('href', '')
            match = re.search(r'/champion-stats/(\d+)', href)
            if match:
                info['champion_id'] = int(match.group(1))
        
        return info
    
    def scrape_champion(self, champion_id: int, lang: str = "zh-CN") -> Optional[ChampionData]:
        """
        抓取单个英雄的完整数据
        
        Args:
            champion_id: 英雄ID
            lang: 语言代码
            
        Returns:
            ChampionData对象或None
        """
        print(f"正在抓取英雄ID: {champion_id}...")
        
        html = self.fetch_champion_page(champion_id, lang)
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # 解析英雄信息
        info = self.parse_champion_info(soup)
        info['champion_id'] = champion_id  # 确保ID正确
        
        # 解析各项数据
        augments = self.parse_augments(soup)
        augment_combos = self.parse_augment_combos(soup)
        build_configs = self.parse_build_configs(soup)
        
        champion_data = ChampionData(
            champion_id=info['champion_id'],
            champion_name=info['champion_name'],
            version=info['version'],
            tier=info['tier'],
            win_rate=info['win_rate'],
            pick_rate=info['pick_rate'],
            augments=augments,
            augment_combos=augment_combos,
            build_configs=build_configs
        )
        
        return champion_data
    
    def scrape_multiple_champions(self, champion_ids: List[int], lang: str = "zh-CN") -> List[ChampionData]:
        """
        批量抓取多个英雄的数据
        
        Args:
            champion_ids: 英雄ID列表
            lang: 语言代码
            
        Returns:
            ChampionData列表
        """
        results = []
        for champion_id in champion_ids:
            data = self.scrape_champion(champion_id, lang)
            if data:
                results.append(data)
        return results


def save_to_json(data: ChampionData, filepath: str):
    """保存数据到JSON文件"""
    # 将dataclass转换为字典
    def dataclass_to_dict(obj):
        if isinstance(obj, list):
            return [dataclass_to_dict(item) for item in obj]
        elif hasattr(obj, '__dataclass_fields__'):
            return {k: dataclass_to_dict(v) for k, v in asdict(obj).items()}
        else:
            return obj
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(dataclass_to_dict(data), f, ensure_ascii=False, indent=2)
    print(f"数据已保存到: {filepath}")


def print_champion_summary(data: ChampionData):
    """打印英雄数据摘要"""
    print("\n" + "="*60)
    print(f"英雄: {data.champion_name} (ID: {data.champion_id})")
    print(f"版本: {data.version} | 层级: {data.tier}")
    print(f"胜率: {data.win_rate}% | 选取率: {data.pick_rate}%")
    print("="*60)
    
    print("\n【推荐海克斯】(前10个)")
    for i, aug in enumerate(data.augments[:10], 1):
        print(f"  {i}. {aug.name} (ID: {aug.id}) - {aug.tier} - 胜率: {aug.win_rate}%")
    
    print("\n【情境装备】")
    for config in data.build_configs:
        print(f"\n  配置类型: {config.build_type}")
        print(f"  情境装备:")
        for item in config.situational_items:
            print(f"    - {item.name} (ID: {item.id})")
    
    print("\n【推荐海克斯组合】(前5个)")
    for i, combo in enumerate(data.augment_combos[:5], 1):
        aug_names = ", ".join([aug.name for aug in combo.augments])
        print(f"  {i}. {aug_names} - {combo.tier}")


# 使用示例
if __name__ == "__main__":
    scraper = HextechScraper()
    
    # 抓取单个英雄（莉莉娅，ID: 876）
    champion_id = 876
    data = scraper.scrape_champion(champion_id)
    
    if data:
        # 打印摘要
        print_champion_summary(data)
        
        # 保存到JSON
        save_to_json(data, f"champion_{champion_id}_data.json")
    else:
        print(f"抓取英雄 {champion_id} 失败")
    
    # 批量抓取示例
    # champion_ids = [876, 63, 904, 147]  # 莉莉娅、布兰德、亚恒、萨勒芬妮
    # results = scraper.scrape_multiple_champions(champion_ids)
    # for result in results:
    #     save_to_json(result, f"champion_{result.champion_id}_data.json")
))
        
        for idx, marker in enumerate(build_markers, 1):
            items = []
            win_rate = 0.0
            pick_rate = 0.0
            
            # 获取该方案的元素
            parent = marker.find_parent()
            if parent:
                # 查找装备图片
                imgs = parent.find_all('img')
                for img in imgs:
                    src = img.get('src', '')
                    match = re.search(r'/item-icons/(\d+)\.png', src)
                    if match:
                        item_id = int(match.group(1))
                        item_name = img.get('alt', '') or self._get_item_name(item_id)
                        item = Item(
                            id=item_id,
                            name=item_name,
                            icon_url=src if src.startswith('http') else urljoin(self.CDN_URL, src)
                        )
                        items.append(item)
                
                # 查找胜率和选取率文本
                text = parent.get_text()
                win_match = re.search(r'胜率[:\s]+(\d+\.?\d*)%', text)
                if win_match:
                    win_rate = float(win_match.group(1))
                pick_match = re.search(r'选取率[:\s]+(\d+\.?\d*)%', text)
                if pick_match:
                    pick_rate = float(pick_match.group(1))
            
            if items:
                build = CoreBuild(
                    rank=idx,
                    items=items,
                    win_rate=win_rate,
                    pick_rate=pick_rate
                )
                builds.append(build)
        
        return builds
    
    def parse_starter_items(self, soup: BeautifulSoup) -> List[Item]:
        """
        解析出门装
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            出门装列表
        """
        items = []
        
        # 查找"出门装"标题
        starter_heading = soup.find(string=re.compile(r'出门装'))
        if not starter_heading:
            return items
        
        # 获取出门装区域
        starter_section = starter_heading.find_parent('h3') or starter_heading.find_parent()
        if starter_section:
            imgs = starter_section.find_all('img')
            for img in imgs:
                src = img.get('src', '')
                match = re.search(r'/item-icons/(\d+)\.png', src)
                if match:
                    item_id = int(match.group(1))
                    item = Item(
                        id=item_id,
                        name=self._get_item_name(item_id),
                        icon_url=src
                    )
                    items.append(item)
        
        return items
    
    def parse_build_configs(self, soup: BeautifulSoup) -> List[BuildConfig]:
        """
        解析所有装备配置
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            装备配置列表
        """
        configs = []
        
        # 查找"装备配置"区域
        build_heading = soup.find(string=re.compile(r'装备配置'))
        if not build_heading:
            return configs
        
        # 获取版本号
        version = "16.6"  # 默认值
        version_match = re.search(r'(\d+\.\d+)', build_heading.get_text() if hasattr(build_heading, 'get_text') else str(build_heading))
        if version_match:
            version = version_match.group(1)
        
        # 查找所有出装类型（AP, APBruiser等）
        build_types = soup.find_all(string=re.compile(r'^(AP|AD|Tank|Support|APBruiser|ADAssassin)$'))
        
        for build_type_elem in build_types:
            build_type = build_type_elem.get_text(strip=True)
            
            # 获取该类型的胜率
            win_rate = 0.0
            parent = build_type_elem.find_parent()
            if parent:
                text = parent.get_text()
                win_match = re.search(r'(\d+\.?\d*)%', text)
                if win_match:
                    win_rate = float(win_match.group(1))
            
            # 解析核心出装和情境装备
            core_builds = self.parse_core_builds(soup)
            situational_items = self.parse_situational_items(soup)
            starter_items = self.parse_starter_items(soup)
            
            config = BuildConfig(
                build_type=build_type,
                win_rate=win_rate,
                core_builds=core_builds,
                situational_items=situational_items,
                starter_items=starter_items
            )
            configs.append(config)
        
        # 如果没有找到具体类型，创建一个默认配置
        if not configs:
            core_builds = self.parse_core_builds(soup)
            situational_items = self.parse_situational_items(soup)
            starter_items = self.parse_starter_items(soup)
            
            if core_builds or situational_items:
                config = BuildConfig(
                    build_type="Default",
                    win_rate=0.0,
                    core_builds=core_builds,
                    situational_items=situational_items,
                    starter_items=starter_items
                )
                configs.append(config)
        
        return configs
    
    def parse_augment_combos(self, soup: BeautifulSoup) -> List[AugmentCombo]:
        """
        解析推荐海克斯组合
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            海克斯组合列表
        """
        combos = []
        
        # 查找"推荐海克斯组合"标题
        combo_heading = soup.find(string=re.compile(r'推荐海克斯组合'))
        if not combo_heading:
            return combos
        
        # 获取组合区域
        combo_section = combo_heading.find_parent('h3') or combo_heading.find_parent()
        if combo_section:
            # 查找所有组合（通常以#1, #2等标识）
            combo_divs = soup.find_all(string=re.compile(r'^#组合'))
            
            for idx, combo_div in enumerate(combo_divs, 1):
                augments = []
                tier = "T1"
                
                parent = combo_div.find_parent()
                if parent:
                    # 查找该组合中的海克斯链接
                    augment_links = parent.find_all('a', href=re.compile(r'/augments/\d+'))
                    for link in augment_links:
                        href = link.get('href', '')
                        match = re.search(r'/augments/(\d+)', href)
                        if match:
                            augment_id = int(match.group(1))
                            name = link.get('title', '') or link.get_text(strip=True)
                            
                            img = link.find('img')
                            icon_url = img.get('src', '') if img else ''
                            
                            augment = Augment(
                                id=augment_id,
                                name=name,
                                tier="T1",
                                win_rate=0.0,
                                pick_rate=0.0,
                                icon_url=icon_url
                            )
                            augments.append(augment)
                    
                    # 提取层级
                    text = parent.get_text()
                    tier_match = re.search(r'(T\d)', text)
                    if tier_match:
                        tier = tier_match.group(1)
                
                if augments:
                    combo = AugmentCombo(
                        rank=idx,
                        augments=augments,
                        tier=tier
                    )
                    combos.append(combo)
        
        return combos
    
    def parse_champion_info(self, soup: BeautifulSoup) -> Dict:
        """
        解析英雄基本信息
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            英雄信息字典
        """
        info = {
            'champion_id': 0,
            'champion_name': '',
            'version': '16.6',
            'tier': 'T1',
            'win_rate': 0.0,
            'pick_rate': 0.0
        }
        
        # 获取英雄名称
        name_heading = soup.find('h1')
        if name_heading:
            info['champion_name'] = name_heading.get_text(strip=True)
        
        # 获取版本
        version_elem = soup.find(string=re.compile(r'版本:\s*\d+\.\d+'))
        if version_elem:
            match = re.search(r'(\d+\.\d+)', version_elem)
            if match:
                info['version'] = match.group(1)
        
        # 获取层级
        tier_elem = soup.find(string=re.compile(r'^T[1-5]$'))
        if tier_elem:
            info['tier'] = tier_elem.get_text(strip=True)
        
        # 获取胜率和选取率
        text = soup.get_text()
        win_match = re.search(r'胜率\s*\n?\s*(\d+\.?\d*)%', text)
        if win_match:
            info['win_rate'] = float(win_match.group(1))
        
        pick_match = re.search(r'选取率\s*\n?\s*(\d+\.?\d*)%', text)
        if pick_match:
            info['pick_rate'] = float(pick_match.group(1))
        
        # 从URL获取英雄ID
        canonical = soup.find('link', rel='canonical')
        if canonical:
            href = canonical.get('href', '')
            match = re.search(r'/champion-stats/(\d+)', href)
            if match:
                info['champion_id'] = int(match.group(1))
        
        return info
    
    def scrape_champion(self, champion_id: int, lang: str = "zh-CN") -> Optional[ChampionData]:
        """
        抓取单个英雄的完整数据
        
        Args:
            champion_id: 英雄ID
            lang: 语言代码
            
        Returns:
            ChampionData对象或None
        """
        print(f"正在抓取英雄ID: {champion_id}...")
        
        html = self.fetch_champion_page(champion_id, lang)
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # 解析英雄信息
        info = self.parse_champion_info(soup)
        info['champion_id'] = champion_id  # 确保ID正确
        
        # 解析各项数据
        augments = self.parse_augments(soup)
        augment_combos = self.parse_augment_combos(soup)
        build_configs = self.parse_build_configs(soup)
        
        champion_data = ChampionData(
            champion_id=info['champion_id'],
            champion_name=info['champion_name'],
            version=info['version'],
            tier=info['tier'],
            win_rate=info['win_rate'],
            pick_rate=info['pick_rate'],
            augments=augments,
            augment_combos=augment_combos,
            build_configs=build_configs
        )
        
        return champion_data
    
    def scrape_multiple_champions(self, champion_ids: List[int], lang: str = "zh-CN") -> List[ChampionData]:
        """
        批量抓取多个英雄的数据
        
        Args:
            champion_ids: 英雄ID列表
            lang: 语言代码
            
        Returns:
            ChampionData列表
        """
        results = []
        for champion_id in champion_ids:
            data = self.scrape_champion(champion_id, lang)
            if data:
                results.append(data)
        return results


def save_to_json(data: ChampionData, filepath: str):
    """保存数据到JSON文件"""
    # 将dataclass转换为字典
    def dataclass_to_dict(obj):
        if isinstance(obj, list):
            return [dataclass_to_dict(item) for item in obj]
        elif hasattr(obj, '__dataclass_fields__'):
            return {k: dataclass_to_dict(v) for k, v in asdict(obj).items()}
        else:
            return obj
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(dataclass_to_dict(data), f, ensure_ascii=False, indent=2)
    print(f"数据已保存到: {filepath}")


def print_champion_summary(data: ChampionData):
    """打印英雄数据摘要"""
    print("\n" + "="*60)
    print(f"英雄: {data.champion_name} (ID: {data.champion_id})")
    print(f"版本: {data.version} | 层级: {data.tier}")
    print(f"胜率: {data.win_rate}% | 选取率: {data.pick_rate}%")
    print("="*60)
    
    print("\n【推荐海克斯】(前10个)")
    for i, aug in enumerate(data.augments[:10], 1):
        print(f"  {i}. {aug.name} (ID: {aug.id}) - {aug.tier} - 胜率: {aug.win_rate}%")
    
    print("\n【情境装备】")
    for config in data.build_configs:
        print(f"\n  配置类型: {config.build_type}")
        print(f"  情境装备:")
        for item in config.situational_items:
            print(f"    - {item.name} (ID: {item.id})")
    
    print("\n【推荐海克斯组合】(前5个)")
    for i, combo in enumerate(data.augment_combos[:5], 1):
        aug_names = ", ".join([aug.name for aug in combo.augments])
        print(f"  {i}. {aug_names} - {combo.tier}")


# 使用示例
if __name__ == "__main__":
    scraper = HextechScraper()
    
    # 抓取单个英雄（莉莉娅，ID: 876）
    champion_id = 876
    data = scraper.scrape_champion(champion_id)
    
    if data:
        # 打印摘要
        print_champion_summary(data)
        
        # 保存到JSON
        save_to_json(data, f"champion_{champion_id}_data.json")
    else:
        print(f"抓取英雄 {champion_id} 失败")
    
    # 批量抓取示例
    # champion_ids = [876, 63, 904, 147]  # 莉莉娅、布兰德、亚恒、萨勒芬妮
    # results = scraper.scrape_multiple_champions(champion_ids)
    # for result in results:
    #     save_to_json(result, f"champion_{result.champion_id}_data.json")
))
        
        for idx, marker in enumerate(combo_markers, 1):
            augments = []
            tier = "T1"
            
            parent = marker.find_parent()
            if parent:
                # 查找该组合中的海克斯链接
                augment_links = parent.find_all('a', href=re.compile(r'/augments/\d+'))
                for link in augment_links:
                    href = link.get('href', '')
                    match = re.search(r'/augments/(\d+)', href)
                    if match:
                        augment_id = int(match.group(1))
                        name = link.get('title', '') or link.get_text(strip=True)
                        # 去掉#号
                        name = re.sub(r'^#', '', name)
                        
                        img = link.find('img')
                        icon_url = ''
                        if img:
                            icon_url = img.get('src', '')
                            if icon_url and not icon_url.startswith('http'):
                                icon_url = urljoin(self.CDN_URL, icon_url)
                        
                        augment = Augment(
                            id=augment_id,
                            name=name,
                            tier="T1",
                            win_rate=0.0,
                            pick_rate=0.0,
                            icon_url=icon_url
                        )
                        augments.append(augment)
                
                # 提取层级
                text = parent.get_text()
                tier_match = re.search(r'(T[1-5])', text)
                if tier_match:
                    tier = tier_match.group(1)
            
            if augments:
                combo = AugmentCombo(
                    rank=idx,
                    augments=augments,
                    tier=tier
                )
                combos.append(combo)
        
        return combos
    
    def parse_champion_info(self, soup: BeautifulSoup) -> Dict:
        """
        解析英雄基本信息
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            英雄信息字典
        """
        info = {
            'champion_id': 0,
            'champion_name': '',
            'version': '16.6',
            'tier': 'T1',
            'win_rate': 0.0,
            'pick_rate': 0.0
        }
        
        # 获取英雄名称
        name_heading = soup.find('h1')
        if name_heading:
            info['champion_name'] = name_heading.get_text(strip=True)
        
        # 获取版本
        version_elem = soup.find(string=re.compile(r'版本:\s*\d+\.\d+'))
        if version_elem:
            match = re.search(r'(\d+\.\d+)', version_elem)
            if match:
                info['version'] = match.group(1)
        
        # 获取层级
        tier_elem = soup.find(string=re.compile(r'^T[1-5]$'))
        if tier_elem:
            info['tier'] = tier_elem.get_text(strip=True)
        
        # 获取胜率和选取率
        text = soup.get_text()
        win_match = re.search(r'胜率\s*\n?\s*(\d+\.?\d*)%', text)
        if win_match:
            info['win_rate'] = float(win_match.group(1))
        
        pick_match = re.search(r'选取率\s*\n?\s*(\d+\.?\d*)%', text)
        if pick_match:
            info['pick_rate'] = float(pick_match.group(1))
        
        # 从URL获取英雄ID
        canonical = soup.find('link', rel='canonical')
        if canonical:
            href = canonical.get('href', '')
            match = re.search(r'/champion-stats/(\d+)', href)
            if match:
                info['champion_id'] = int(match.group(1))
        
        return info
    
    def scrape_champion(self, champion_id: int, lang: str = "zh-CN") -> Optional[ChampionData]:
        """
        抓取单个英雄的完整数据
        
        Args:
            champion_id: 英雄ID
            lang: 语言代码
            
        Returns:
            ChampionData对象或None
        """
        print(f"正在抓取英雄ID: {champion_id}...")
        
        html = self.fetch_champion_page(champion_id, lang)
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # 解析英雄信息
        info = self.parse_champion_info(soup)
        info['champion_id'] = champion_id  # 确保ID正确
        
        # 解析各项数据
        augments = self.parse_augments(soup)
        augment_combos = self.parse_augment_combos(soup)
        build_configs = self.parse_build_configs(soup)
        
        champion_data = ChampionData(
            champion_id=info['champion_id'],
            champion_name=info['champion_name'],
            version=info['version'],
            tier=info['tier'],
            win_rate=info['win_rate'],
            pick_rate=info['pick_rate'],
            augments=augments,
            augment_combos=augment_combos,
            build_configs=build_configs
        )
        
        return champion_data
    
    def scrape_multiple_champions(self, champion_ids: List[int], lang: str = "zh-CN") -> List[ChampionData]:
        """
        批量抓取多个英雄的数据
        
        Args:
            champion_ids: 英雄ID列表
            lang: 语言代码
            
        Returns:
            ChampionData列表
        """
        results = []
        for champion_id in champion_ids:
            data = self.scrape_champion(champion_id, lang)
            if data:
                results.append(data)
        return results


def save_to_json(data: ChampionData, filepath: str):
    """保存数据到JSON文件"""
    # 将dataclass转换为字典
    def dataclass_to_dict(obj):
        if isinstance(obj, list):
            return [dataclass_to_dict(item) for item in obj]
        elif hasattr(obj, '__dataclass_fields__'):
            return {k: dataclass_to_dict(v) for k, v in asdict(obj).items()}
        else:
            return obj
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(dataclass_to_dict(data), f, ensure_ascii=False, indent=2)
    print(f"数据已保存到: {filepath}")


def print_champion_summary(data: ChampionData):
    """打印英雄数据摘要"""
    print("\n" + "="*60)
    print(f"英雄: {data.champion_name} (ID: {data.champion_id})")
    print(f"版本: {data.version} | 层级: {data.tier}")
    print(f"胜率: {data.win_rate}% | 选取率: {data.pick_rate}%")
    print("="*60)
    
    print("\n【推荐海克斯】(前10个)")
    for i, aug in enumerate(data.augments[:10], 1):
        print(f"  {i}. {aug.name} (ID: {aug.id}) - {aug.tier} - 胜率: {aug.win_rate}%")
    
    print("\n【情境装备】")
    for config in data.build_configs:
        print(f"\n  配置类型: {config.build_type}")
        print(f"  情境装备:")
        for item in config.situational_items:
            print(f"    - {item.name} (ID: {item.id})")
    
    print("\n【推荐海克斯组合】(前5个)")
    for i, combo in enumerate(data.augment_combos[:5], 1):
        aug_names = ", ".join([aug.name for aug in combo.augments])
        print(f"  {i}. {aug_names} - {combo.tier}")


# 使用示例
if __name__ == "__main__":
    scraper = HextechScraper()
    
    # 抓取单个英雄（莉莉娅，ID: 876）
    champion_id = 876
    data = scraper.scrape_champion(champion_id)
    
    if data:
        # 打印摘要
        print_champion_summary(data)
        
        # 保存到JSON
        save_to_json(data, f"champion_{champion_id}_data.json")
    else:
        print(f"抓取英雄 {champion_id} 失败")
    
    # 批量抓取示例
    # champion_ids = [876, 63, 904, 147]  # 莉莉娅、布兰德、亚恒、萨勒芬妮
    # results = scraper.scrape_multiple_champions(champion_ids)
    # for result in results:
    #     save_to_json(result, f"champion_{result.champion_id}_data.json")
))
        
        for idx, marker in enumerate(build_markers, 1):
            items = []
            win_rate = 0.0
            pick_rate = 0.0
            
            # 获取该方案的元素
            parent = marker.find_parent()
            if parent:
                # 查找装备图片
                imgs = parent.find_all('img')
                for img in imgs:
                    src = img.get('src', '')
                    match = re.search(r'/item-icons/(\d+)\.png', src)
                    if match:
                        item_id = int(match.group(1))
                        item_name = img.get('alt', '') or self._get_item_name(item_id)
                        item = Item(
                            id=item_id,
                            name=item_name,
                            icon_url=src if src.startswith('http') else urljoin(self.CDN_URL, src)
                        )
                        items.append(item)
                
                # 查找胜率和选取率文本
                text = parent.get_text()
                win_match = re.search(r'胜率[:\s]+(\d+\.?\d*)%', text)
                if win_match:
                    win_rate = float(win_match.group(1))
                pick_match = re.search(r'选取率[:\s]+(\d+\.?\d*)%', text)
                if pick_match:
                    pick_rate = float(pick_match.group(1))
            
            if items:
                build = CoreBuild(
                    rank=idx,
                    items=items,
                    win_rate=win_rate,
                    pick_rate=pick_rate
                )
                builds.append(build)
        
        return builds
    
    def parse_starter_items(self, soup: BeautifulSoup) -> List[Item]:
        """
        解析出门装
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            出门装列表
        """
        items = []
        
        # 查找"出门装"标题
        starter_heading = soup.find(string=re.compile(r'出门装'))
        if not starter_heading:
            return items
        
        # 获取出门装区域
        starter_section = starter_heading.find_parent('h3') or starter_heading.find_parent()
        if starter_section:
            imgs = starter_section.find_all('img')
            for img in imgs:
                src = img.get('src', '')
                match = re.search(r'/item-icons/(\d+)\.png', src)
                if match:
                    item_id = int(match.group(1))
                    item = Item(
                        id=item_id,
                        name=self._get_item_name(item_id),
                        icon_url=src
                    )
                    items.append(item)
        
        return items
    
    def parse_build_configs(self, soup: BeautifulSoup) -> List[BuildConfig]:
        """
        解析所有装备配置
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            装备配置列表
        """
        configs = []
        
        # 查找"装备配置"区域
        build_heading = soup.find(string=re.compile(r'装备配置'))
        if not build_heading:
            return configs
        
        # 获取版本号
        version = "16.6"  # 默认值
        version_match = re.search(r'(\d+\.\d+)', build_heading.get_text() if hasattr(build_heading, 'get_text') else str(build_heading))
        if version_match:
            version = version_match.group(1)
        
        # 查找所有出装类型（AP, APBruiser等）
        build_types = soup.find_all(string=re.compile(r'^(AP|AD|Tank|Support|APBruiser|ADAssassin)$'))
        
        for build_type_elem in build_types:
            build_type = build_type_elem.get_text(strip=True)
            
            # 获取该类型的胜率
            win_rate = 0.0
            parent = build_type_elem.find_parent()
            if parent:
                text = parent.get_text()
                win_match = re.search(r'(\d+\.?\d*)%', text)
                if win_match:
                    win_rate = float(win_match.group(1))
            
            # 解析核心出装和情境装备
            core_builds = self.parse_core_builds(soup)
            situational_items = self.parse_situational_items(soup)
            starter_items = self.parse_starter_items(soup)
            
            config = BuildConfig(
                build_type=build_type,
                win_rate=win_rate,
                core_builds=core_builds,
                situational_items=situational_items,
                starter_items=starter_items
            )
            configs.append(config)
        
        # 如果没有找到具体类型，创建一个默认配置
        if not configs:
            core_builds = self.parse_core_builds(soup)
            situational_items = self.parse_situational_items(soup)
            starter_items = self.parse_starter_items(soup)
            
            if core_builds or situational_items:
                config = BuildConfig(
                    build_type="Default",
                    win_rate=0.0,
                    core_builds=core_builds,
                    situational_items=situational_items,
                    starter_items=starter_items
                )
                configs.append(config)
        
        return configs
    
    def parse_augment_combos(self, soup: BeautifulSoup) -> List[AugmentCombo]:
        """
        解析推荐海克斯组合
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            海克斯组合列表
        """
        combos = []
        
        # 查找"推荐海克斯组合"标题
        combo_heading = soup.find(string=re.compile(r'推荐海克斯组合'))
        if not combo_heading:
            return combos
        
        # 获取组合区域
        combo_section = combo_heading.find_parent('h3') or combo_heading.find_parent()
        if combo_section:
            # 查找所有组合（通常以#1, #2等标识）
            combo_divs = soup.find_all(string=re.compile(r'^#组合'))
            
            for idx, combo_div in enumerate(combo_divs, 1):
                augments = []
                tier = "T1"
                
                parent = combo_div.find_parent()
                if parent:
                    # 查找该组合中的海克斯链接
                    augment_links = parent.find_all('a', href=re.compile(r'/augments/\d+'))
                    for link in augment_links:
                        href = link.get('href', '')
                        match = re.search(r'/augments/(\d+)', href)
                        if match:
                            augment_id = int(match.group(1))
                            name = link.get('title', '') or link.get_text(strip=True)
                            
                            img = link.find('img')
                            icon_url = img.get('src', '') if img else ''
                            
                            augment = Augment(
                                id=augment_id,
                                name=name,
                                tier="T1",
                                win_rate=0.0,
                                pick_rate=0.0,
                                icon_url=icon_url
                            )
                            augments.append(augment)
                    
                    # 提取层级
                    text = parent.get_text()
                    tier_match = re.search(r'(T\d)', text)
                    if tier_match:
                        tier = tier_match.group(1)
                
                if augments:
                    combo = AugmentCombo(
                        rank=idx,
                        augments=augments,
                        tier=tier
                    )
                    combos.append(combo)
        
        return combos
    
    def parse_champion_info(self, soup: BeautifulSoup) -> Dict:
        """
        解析英雄基本信息
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            英雄信息字典
        """
        info = {
            'champion_id': 0,
            'champion_name': '',
            'version': '16.6',
            'tier': 'T1',
            'win_rate': 0.0,
            'pick_rate': 0.0
        }
        
        # 获取英雄名称
        name_heading = soup.find('h1')
        if name_heading:
            info['champion_name'] = name_heading.get_text(strip=True)
        
        # 获取版本
        version_elem = soup.find(string=re.compile(r'版本:\s*\d+\.\d+'))
        if version_elem:
            match = re.search(r'(\d+\.\d+)', version_elem)
            if match:
                info['version'] = match.group(1)
        
        # 获取层级
        tier_elem = soup.find(string=re.compile(r'^T[1-5]$'))
        if tier_elem:
            info['tier'] = tier_elem.get_text(strip=True)
        
        # 获取胜率和选取率
        text = soup.get_text()
        win_match = re.search(r'胜率\s*\n?\s*(\d+\.?\d*)%', text)
        if win_match:
            info['win_rate'] = float(win_match.group(1))
        
        pick_match = re.search(r'选取率\s*\n?\s*(\d+\.?\d*)%', text)
        if pick_match:
            info['pick_rate'] = float(pick_match.group(1))
        
        # 从URL获取英雄ID
        canonical = soup.find('link', rel='canonical')
        if canonical:
            href = canonical.get('href', '')
            match = re.search(r'/champion-stats/(\d+)', href)
            if match:
                info['champion_id'] = int(match.group(1))
        
        return info
    
    def scrape_champion(self, champion_id: int, lang: str = "zh-CN") -> Optional[ChampionData]:
        """
        抓取单个英雄的完整数据
        
        Args:
            champion_id: 英雄ID
            lang: 语言代码
            
        Returns:
            ChampionData对象或None
        """
        print(f"正在抓取英雄ID: {champion_id}...")
        
        html = self.fetch_champion_page(champion_id, lang)
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # 解析英雄信息
        info = self.parse_champion_info(soup)
        info['champion_id'] = champion_id  # 确保ID正确
        
        # 解析各项数据
        augments = self.parse_augments(soup)
        augment_combos = self.parse_augment_combos(soup)
        build_configs = self.parse_build_configs(soup)
        
        champion_data = ChampionData(
            champion_id=info['champion_id'],
            champion_name=info['champion_name'],
            version=info['version'],
            tier=info['tier'],
            win_rate=info['win_rate'],
            pick_rate=info['pick_rate'],
            augments=augments,
            augment_combos=augment_combos,
            build_configs=build_configs
        )
        
        return champion_data
    
    def scrape_multiple_champions(self, champion_ids: List[int], lang: str = "zh-CN") -> List[ChampionData]:
        """
        批量抓取多个英雄的数据
        
        Args:
            champion_ids: 英雄ID列表
            lang: 语言代码
            
        Returns:
            ChampionData列表
        """
        results = []
        for champion_id in champion_ids:
            data = self.scrape_champion(champion_id, lang)
            if data:
                results.append(data)
        return results


def save_to_json(data: ChampionData, filepath: str):
    """保存数据到JSON文件"""
    # 将dataclass转换为字典
    def dataclass_to_dict(obj):
        if isinstance(obj, list):
            return [dataclass_to_dict(item) for item in obj]
        elif hasattr(obj, '__dataclass_fields__'):
            return {k: dataclass_to_dict(v) for k, v in asdict(obj).items()}
        else:
            return obj
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(dataclass_to_dict(data), f, ensure_ascii=False, indent=2)
    print(f"数据已保存到: {filepath}")


def print_champion_summary(data: ChampionData):
    """打印英雄数据摘要"""
    print("\n" + "="*60)
    print(f"英雄: {data.champion_name} (ID: {data.champion_id})")
    print(f"版本: {data.version} | 层级: {data.tier}")
    print(f"胜率: {data.win_rate}% | 选取率: {data.pick_rate}%")
    print("="*60)
    
    print("\n【推荐海克斯】(前10个)")
    for i, aug in enumerate(data.augments[:10], 1):
        print(f"  {i}. {aug.name} (ID: {aug.id}) - {aug.tier} - 胜率: {aug.win_rate}%")
    
    print("\n【情境装备】")
    for config in data.build_configs:
        print(f"\n  配置类型: {config.build_type}")
        print(f"  情境装备:")
        for item in config.situational_items:
            print(f"    - {item.name} (ID: {item.id})")
    
    print("\n【推荐海克斯组合】(前5个)")
    for i, combo in enumerate(data.augment_combos[:5], 1):
        aug_names = ", ".join([aug.name for aug in combo.augments])
        print(f"  {i}. {aug_names} - {combo.tier}")


# 使用示例
if __name__ == "__main__":
    scraper = HextechScraper()
    
    # 抓取单个英雄（莉莉娅，ID: 876）
    champion_id = 876
    data = scraper.scrape_champion(champion_id)
    
    if data:
        # 打印摘要
        print_champion_summary(data)
        
        # 保存到JSON
        save_to_json(data, f"champion_{champion_id}_data.json")
    else:
        print(f"抓取英雄 {champion_id} 失败")
    
    # 批量抓取示例
    # champion_ids = [876, 63, 904, 147]  # 莉莉娅、布兰德、亚恒、萨勒芬妮
    # results = scraper.scrape_multiple_champions(champion_ids)
    # for result in results:
    #     save_to_json(result, f"champion_{result.champion_id}_data.json")
, text):
                    build_types.append((next_elem, text))
                next_elem = next_elem.find_next_sibling()
        
        # 解析核心出装、情境装备和出门装（这些是共享的）
        core_builds = self.parse_core_builds(soup)
        situational_items = self.parse_situational_items(soup)
        starter_items = self.parse_starter_items(soup)
        
        for build_type_elem, build_type in build_types:
            # 获取该类型的胜率
            win_rate = 0.0
            parent = build_type_elem.find_parent()
            if parent:
                text = parent.get_text()
                # 查找该类型后面的百分比
                win_match = re.search(rf'{re.escape(build_type)}.*?\n?\s*(\d+\.?\d*)%', text, re.DOTALL)
                if win_match:
                    win_rate = float(win_match.group(1))
            
            config = BuildConfig(
                build_type=build_type,
                win_rate=win_rate,
                core_builds=core_builds,
                situational_items=situational_items,
                starter_items=starter_items
            )
            configs.append(config)
        
        # 如果没有找到具体类型，创建一个默认配置
        if not configs:
            if core_builds or situational_items or starter_items:
                config = BuildConfig(
                    build_type="Default",
                    win_rate=0.0,
                    core_builds=core_builds,
                    situational_items=situational_items,
                    starter_items=starter_items
                )
                configs.append(config)
        
        return configs
    
    def parse_augment_combos(self, soup: BeautifulSoup) -> List[AugmentCombo]:
        """
        解析推荐海克斯组合
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            海克斯组合列表
        """
        combos = []
        
        # 查找"推荐海克斯组合"标题
        combo_heading = soup.find(string=re.compile(r'推荐海克斯组合'))
        if not combo_heading:
            return combos
        
        # 获取组合区域
        combo_section = combo_heading.find_parent('h3') or combo_heading.find_parent()
        if not combo_section:
            return combos
        
        # 查找所有组合（通常以#组合1, #组合2等标识）
        combo_markers = combo_section.find_all(string=re.compile(r'^#组合\d+
    
    def parse_champion_info(self, soup: BeautifulSoup) -> Dict:
        """
        解析英雄基本信息
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            英雄信息字典
        """
        info = {
            'champion_id': 0,
            'champion_name': '',
            'version': '16.6',
            'tier': 'T1',
            'win_rate': 0.0,
            'pick_rate': 0.0
        }
        
        # 获取英雄名称
        name_heading = soup.find('h1')
        if name_heading:
            info['champion_name'] = name_heading.get_text(strip=True)
        
        # 获取版本
        version_elem = soup.find(string=re.compile(r'版本:\s*\d+\.\d+'))
        if version_elem:
            match = re.search(r'(\d+\.\d+)', version_elem)
            if match:
                info['version'] = match.group(1)
        
        # 获取层级
        tier_elem = soup.find(string=re.compile(r'^T[1-5]$'))
        if tier_elem:
            info['tier'] = tier_elem.get_text(strip=True)
        
        # 获取胜率和选取率
        text = soup.get_text()
        win_match = re.search(r'胜率\s*\n?\s*(\d+\.?\d*)%', text)
        if win_match:
            info['win_rate'] = float(win_match.group(1))
        
        pick_match = re.search(r'选取率\s*\n?\s*(\d+\.?\d*)%', text)
        if pick_match:
            info['pick_rate'] = float(pick_match.group(1))
        
        # 从URL获取英雄ID
        canonical = soup.find('link', rel='canonical')
        if canonical:
            href = canonical.get('href', '')
            match = re.search(r'/champion-stats/(\d+)', href)
            if match:
                info['champion_id'] = int(match.group(1))
        
        return info
    
    def scrape_champion(self, champion_id: int, lang: str = "zh-CN") -> Optional[ChampionData]:
        """
        抓取单个英雄的完整数据
        
        Args:
            champion_id: 英雄ID
            lang: 语言代码
            
        Returns:
            ChampionData对象或None
        """
        print(f"正在抓取英雄ID: {champion_id}...")
        
        html = self.fetch_champion_page(champion_id, lang)
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # 解析英雄信息
        info = self.parse_champion_info(soup)
        info['champion_id'] = champion_id  # 确保ID正确
        
        # 解析各项数据
        augments = self.parse_augments(soup)
        augment_combos = self.parse_augment_combos(soup)
        build_configs = self.parse_build_configs(soup)
        
        champion_data = ChampionData(
            champion_id=info['champion_id'],
            champion_name=info['champion_name'],
            version=info['version'],
            tier=info['tier'],
            win_rate=info['win_rate'],
            pick_rate=info['pick_rate'],
            augments=augments,
            augment_combos=augment_combos,
            build_configs=build_configs
        )
        
        return champion_data
    
    def scrape_multiple_champions(self, champion_ids: List[int], lang: str = "zh-CN") -> List[ChampionData]:
        """
        批量抓取多个英雄的数据
        
        Args:
            champion_ids: 英雄ID列表
            lang: 语言代码
            
        Returns:
            ChampionData列表
        """
        results = []
        for champion_id in champion_ids:
            data = self.scrape_champion(champion_id, lang)
            if data:
                results.append(data)
        return results


def save_to_json(data: ChampionData, filepath: str):
    """保存数据到JSON文件"""
    # 将dataclass转换为字典
    def dataclass_to_dict(obj):
        if isinstance(obj, list):
            return [dataclass_to_dict(item) for item in obj]
        elif hasattr(obj, '__dataclass_fields__'):
            return {k: dataclass_to_dict(v) for k, v in asdict(obj).items()}
        else:
            return obj
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(dataclass_to_dict(data), f, ensure_ascii=False, indent=2)
    print(f"数据已保存到: {filepath}")


def print_champion_summary(data: ChampionData):
    """打印英雄数据摘要"""
    print("\n" + "="*60)
    print(f"英雄: {data.champion_name} (ID: {data.champion_id})")
    print(f"版本: {data.version} | 层级: {data.tier}")
    print(f"胜率: {data.win_rate}% | 选取率: {data.pick_rate}%")
    print("="*60)
    
    print("\n【推荐海克斯】(前10个)")
    for i, aug in enumerate(data.augments[:10], 1):
        print(f"  {i}. {aug.name} (ID: {aug.id}) - {aug.tier} - 胜率: {aug.win_rate}%")
    
    print("\n【情境装备】")
    for config in data.build_configs:
        print(f"\n  配置类型: {config.build_type}")
        print(f"  情境装备:")
        for item in config.situational_items:
            print(f"    - {item.name} (ID: {item.id})")
    
    print("\n【推荐海克斯组合】(前5个)")
    for i, combo in enumerate(data.augment_combos[:5], 1):
        aug_names = ", ".join([aug.name for aug in combo.augments])
        print(f"  {i}. {aug_names} - {combo.tier}")


# 使用示例
if __name__ == "__main__":
    scraper = HextechScraper()
    
    # 抓取单个英雄（莉莉娅，ID: 876）
    champion_id = 876
    data = scraper.scrape_champion(champion_id)
    
    if data:
        # 打印摘要
        print_champion_summary(data)
        
        # 保存到JSON
        save_to_json(data, f"champion_{champion_id}_data.json")
    else:
        print(f"抓取英雄 {champion_id} 失败")
    
    # 批量抓取示例
    # champion_ids = [876, 63, 904, 147]  # 莉莉娅、布兰德、亚恒、萨勒芬妮
    # results = scraper.scrape_multiple_champions(champion_ids)
    # for result in results:
    #     save_to_json(result, f"champion_{result.champion_id}_data.json")
))
        
        for idx, marker in enumerate(build_markers, 1):
            items = []
            win_rate = 0.0
            pick_rate = 0.0
            
            # 获取该方案的元素
            parent = marker.find_parent()
            if parent:
                # 查找装备图片
                imgs = parent.find_all('img')
                for img in imgs:
                    src = img.get('src', '')
                    match = re.search(r'/item-icons/(\d+)\.png', src)
                    if match:
                        item_id = int(match.group(1))
                        item_name = img.get('alt', '') or self._get_item_name(item_id)
                        item = Item(
                            id=item_id,
                            name=item_name,
                            icon_url=src if src.startswith('http') else urljoin(self.CDN_URL, src)
                        )
                        items.append(item)
                
                # 查找胜率和选取率文本
                text = parent.get_text()
                win_match = re.search(r'胜率[:\s]+(\d+\.?\d*)%', text)
                if win_match:
                    win_rate = float(win_match.group(1))
                pick_match = re.search(r'选取率[:\s]+(\d+\.?\d*)%', text)
                if pick_match:
                    pick_rate = float(pick_match.group(1))
            
            if items:
                build = CoreBuild(
                    rank=idx,
                    items=items,
                    win_rate=win_rate,
                    pick_rate=pick_rate
                )
                builds.append(build)
        
        return builds
    
    def parse_starter_items(self, soup: BeautifulSoup) -> List[Item]:
        """
        解析出门装
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            出门装列表
        """
        items = []
        
        # 查找"出门装"标题
        starter_heading = soup.find(string=re.compile(r'出门装'))
        if not starter_heading:
            return items
        
        # 获取出门装区域
        starter_section = starter_heading.find_parent('h3') or starter_heading.find_parent()
        if starter_section:
            imgs = starter_section.find_all('img')
            for img in imgs:
                src = img.get('src', '')
                match = re.search(r'/item-icons/(\d+)\.png', src)
                if match:
                    item_id = int(match.group(1))
                    item = Item(
                        id=item_id,
                        name=self._get_item_name(item_id),
                        icon_url=src
                    )
                    items.append(item)
        
        return items
    
    def parse_build_configs(self, soup: BeautifulSoup) -> List[BuildConfig]:
        """
        解析所有装备配置
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            装备配置列表
        """
        configs = []
        
        # 查找"装备配置"区域
        build_heading = soup.find(string=re.compile(r'装备配置'))
        if not build_heading:
            return configs
        
        # 获取版本号
        version = "16.6"  # 默认值
        version_match = re.search(r'(\d+\.\d+)', build_heading.get_text() if hasattr(build_heading, 'get_text') else str(build_heading))
        if version_match:
            version = version_match.group(1)
        
        # 查找所有出装类型（AP, APBruiser等）
        build_types = soup.find_all(string=re.compile(r'^(AP|AD|Tank|Support|APBruiser|ADAssassin)$'))
        
        for build_type_elem in build_types:
            build_type = build_type_elem.get_text(strip=True)
            
            # 获取该类型的胜率
            win_rate = 0.0
            parent = build_type_elem.find_parent()
            if parent:
                text = parent.get_text()
                win_match = re.search(r'(\d+\.?\d*)%', text)
                if win_match:
                    win_rate = float(win_match.group(1))
            
            # 解析核心出装和情境装备
            core_builds = self.parse_core_builds(soup)
            situational_items = self.parse_situational_items(soup)
            starter_items = self.parse_starter_items(soup)
            
            config = BuildConfig(
                build_type=build_type,
                win_rate=win_rate,
                core_builds=core_builds,
                situational_items=situational_items,
                starter_items=starter_items
            )
            configs.append(config)
        
        # 如果没有找到具体类型，创建一个默认配置
        if not configs:
            core_builds = self.parse_core_builds(soup)
            situational_items = self.parse_situational_items(soup)
            starter_items = self.parse_starter_items(soup)
            
            if core_builds or situational_items:
                config = BuildConfig(
                    build_type="Default",
                    win_rate=0.0,
                    core_builds=core_builds,
                    situational_items=situational_items,
                    starter_items=starter_items
                )
                configs.append(config)
        
        return configs
    
    def parse_augment_combos(self, soup: BeautifulSoup) -> List[AugmentCombo]:
        """
        解析推荐海克斯组合
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            海克斯组合列表
        """
        combos = []
        
        # 查找"推荐海克斯组合"标题
        combo_heading = soup.find(string=re.compile(r'推荐海克斯组合'))
        if not combo_heading:
            return combos
        
        # 获取组合区域
        combo_section = combo_heading.find_parent('h3') or combo_heading.find_parent()
        if combo_section:
            # 查找所有组合（通常以#1, #2等标识）
            combo_divs = soup.find_all(string=re.compile(r'^#组合'))
            
            for idx, combo_div in enumerate(combo_divs, 1):
                augments = []
                tier = "T1"
                
                parent = combo_div.find_parent()
                if parent:
                    # 查找该组合中的海克斯链接
                    augment_links = parent.find_all('a', href=re.compile(r'/augments/\d+'))
                    for link in augment_links:
                        href = link.get('href', '')
                        match = re.search(r'/augments/(\d+)', href)
                        if match:
                            augment_id = int(match.group(1))
                            name = link.get('title', '') or link.get_text(strip=True)
                            
                            img = link.find('img')
                            icon_url = img.get('src', '') if img else ''
                            
                            augment = Augment(
                                id=augment_id,
                                name=name,
                                tier="T1",
                                win_rate=0.0,
                                pick_rate=0.0,
                                icon_url=icon_url
                            )
                            augments.append(augment)
                    
                    # 提取层级
                    text = parent.get_text()
                    tier_match = re.search(r'(T\d)', text)
                    if tier_match:
                        tier = tier_match.group(1)
                
                if augments:
                    combo = AugmentCombo(
                        rank=idx,
                        augments=augments,
                        tier=tier
                    )
                    combos.append(combo)
        
        return combos
    
    def parse_champion_info(self, soup: BeautifulSoup) -> Dict:
        """
        解析英雄基本信息
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            英雄信息字典
        """
        info = {
            'champion_id': 0,
            'champion_name': '',
            'version': '16.6',
            'tier': 'T1',
            'win_rate': 0.0,
            'pick_rate': 0.0
        }
        
        # 获取英雄名称
        name_heading = soup.find('h1')
        if name_heading:
            info['champion_name'] = name_heading.get_text(strip=True)
        
        # 获取版本
        version_elem = soup.find(string=re.compile(r'版本:\s*\d+\.\d+'))
        if version_elem:
            match = re.search(r'(\d+\.\d+)', version_elem)
            if match:
                info['version'] = match.group(1)
        
        # 获取层级
        tier_elem = soup.find(string=re.compile(r'^T[1-5]$'))
        if tier_elem:
            info['tier'] = tier_elem.get_text(strip=True)
        
        # 获取胜率和选取率
        text = soup.get_text()
        win_match = re.search(r'胜率\s*\n?\s*(\d+\.?\d*)%', text)
        if win_match:
            info['win_rate'] = float(win_match.group(1))
        
        pick_match = re.search(r'选取率\s*\n?\s*(\d+\.?\d*)%', text)
        if pick_match:
            info['pick_rate'] = float(pick_match.group(1))
        
        # 从URL获取英雄ID
        canonical = soup.find('link', rel='canonical')
        if canonical:
            href = canonical.get('href', '')
            match = re.search(r'/champion-stats/(\d+)', href)
            if match:
                info['champion_id'] = int(match.group(1))
        
        return info
    
    def scrape_champion(self, champion_id: int, lang: str = "zh-CN") -> Optional[ChampionData]:
        """
        抓取单个英雄的完整数据
        
        Args:
            champion_id: 英雄ID
            lang: 语言代码
            
        Returns:
            ChampionData对象或None
        """
        print(f"正在抓取英雄ID: {champion_id}...")
        
        html = self.fetch_champion_page(champion_id, lang)
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # 解析英雄信息
        info = self.parse_champion_info(soup)
        info['champion_id'] = champion_id  # 确保ID正确
        
        # 解析各项数据
        augments = self.parse_augments(soup)
        augment_combos = self.parse_augment_combos(soup)
        build_configs = self.parse_build_configs(soup)
        
        champion_data = ChampionData(
            champion_id=info['champion_id'],
            champion_name=info['champion_name'],
            version=info['version'],
            tier=info['tier'],
            win_rate=info['win_rate'],
            pick_rate=info['pick_rate'],
            augments=augments,
            augment_combos=augment_combos,
            build_configs=build_configs
        )
        
        return champion_data
    
    def scrape_multiple_champions(self, champion_ids: List[int], lang: str = "zh-CN") -> List[ChampionData]:
        """
        批量抓取多个英雄的数据
        
        Args:
            champion_ids: 英雄ID列表
            lang: 语言代码
            
        Returns:
            ChampionData列表
        """
        results = []
        for champion_id in champion_ids:
            data = self.scrape_champion(champion_id, lang)
            if data:
                results.append(data)
        return results


def save_to_json(data: ChampionData, filepath: str):
    """保存数据到JSON文件"""
    # 将dataclass转换为字典
    def dataclass_to_dict(obj):
        if isinstance(obj, list):
            return [dataclass_to_dict(item) for item in obj]
        elif hasattr(obj, '__dataclass_fields__'):
            return {k: dataclass_to_dict(v) for k, v in asdict(obj).items()}
        else:
            return obj
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(dataclass_to_dict(data), f, ensure_ascii=False, indent=2)
    print(f"数据已保存到: {filepath}")


def print_champion_summary(data: ChampionData):
    """打印英雄数据摘要"""
    print("\n" + "="*60)
    print(f"英雄: {data.champion_name} (ID: {data.champion_id})")
    print(f"版本: {data.version} | 层级: {data.tier}")
    print(f"胜率: {data.win_rate}% | 选取率: {data.pick_rate}%")
    print("="*60)
    
    print("\n【推荐海克斯】(前10个)")
    for i, aug in enumerate(data.augments[:10], 1):
        print(f"  {i}. {aug.name} (ID: {aug.id}) - {aug.tier} - 胜率: {aug.win_rate}%")
    
    print("\n【情境装备】")
    for config in data.build_configs:
        print(f"\n  配置类型: {config.build_type}")
        print(f"  情境装备:")
        for item in config.situational_items:
            print(f"    - {item.name} (ID: {item.id})")
    
    print("\n【推荐海克斯组合】(前5个)")
    for i, combo in enumerate(data.augment_combos[:5], 1):
        aug_names = ", ".join([aug.name for aug in combo.augments])
        print(f"  {i}. {aug_names} - {combo.tier}")


# 使用示例
if __name__ == "__main__":
    scraper = HextechScraper()
    
    # 抓取单个英雄（莉莉娅，ID: 876）
    champion_id = 876
    data = scraper.scrape_champion(champion_id)
    
    if data:
        # 打印摘要
        print_champion_summary(data)
        
        # 保存到JSON
        save_to_json(data, f"champion_{champion_id}_data.json")
    else:
        print(f"抓取英雄 {champion_id} 失败")
    
    # 批量抓取示例
    # champion_ids = [876, 63, 904, 147]  # 莉莉娅、布兰德、亚恒、萨勒芬妮
    # results = scraper.scrape_multiple_champions(champion_ids)
    # for result in results:
    #     save_to_json(result, f"champion_{result.champion_id}_data.json")
))
        
        for idx, marker in enumerate(combo_markers, 1):
            augments = []
            tier = "T1"
            
            parent = marker.find_parent()
            if parent:
                # 查找该组合中的海克斯链接
                augment_links = parent.find_all('a', href=re.compile(r'/augments/\d+'))
                for link in augment_links:
                    href = link.get('href', '')
                    match = re.search(r'/augments/(\d+)', href)
                    if match:
                        augment_id = int(match.group(1))
                        name = link.get('title', '') or link.get_text(strip=True)
                        # 去掉#号
                        name = re.sub(r'^#', '', name)
                        
                        img = link.find('img')
                        icon_url = ''
                        if img:
                            icon_url = img.get('src', '')
                            if icon_url and not icon_url.startswith('http'):
                                icon_url = urljoin(self.CDN_URL, icon_url)
                        
                        augment = Augment(
                            id=augment_id,
                            name=name,
                            tier="T1",
                            win_rate=0.0,
                            pick_rate=0.0,
                            icon_url=icon_url
                        )
                        augments.append(augment)
                
                # 提取层级
                text = parent.get_text()
                tier_match = re.search(r'(T[1-5])', text)
                if tier_match:
                    tier = tier_match.group(1)
            
            if augments:
                combo = AugmentCombo(
                    rank=idx,
                    augments=augments,
                    tier=tier
                )
                combos.append(combo)
        
        return combos
    
    def parse_champion_info(self, soup: BeautifulSoup) -> Dict:
        """
        解析英雄基本信息
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            英雄信息字典
        """
        info = {
            'champion_id': 0,
            'champion_name': '',
            'version': '16.6',
            'tier': 'T1',
            'win_rate': 0.0,
            'pick_rate': 0.0
        }
        
        # 获取英雄名称
        name_heading = soup.find('h1')
        if name_heading:
            info['champion_name'] = name_heading.get_text(strip=True)
        
        # 获取版本
        version_elem = soup.find(string=re.compile(r'版本:\s*\d+\.\d+'))
        if version_elem:
            match = re.search(r'(\d+\.\d+)', version_elem)
            if match:
                info['version'] = match.group(1)
        
        # 获取层级
        tier_elem = soup.find(string=re.compile(r'^T[1-5]$'))
        if tier_elem:
            info['tier'] = tier_elem.get_text(strip=True)
        
        # 获取胜率和选取率
        text = soup.get_text()
        win_match = re.search(r'胜率\s*\n?\s*(\d+\.?\d*)%', text)
        if win_match:
            info['win_rate'] = float(win_match.group(1))
        
        pick_match = re.search(r'选取率\s*\n?\s*(\d+\.?\d*)%', text)
        if pick_match:
            info['pick_rate'] = float(pick_match.group(1))
        
        # 从URL获取英雄ID
        canonical = soup.find('link', rel='canonical')
        if canonical:
            href = canonical.get('href', '')
            match = re.search(r'/champion-stats/(\d+)', href)
            if match:
                info['champion_id'] = int(match.group(1))
        
        return info
    
    def scrape_champion(self, champion_id: int, lang: str = "zh-CN") -> Optional[ChampionData]:
        """
        抓取单个英雄的完整数据
        
        Args:
            champion_id: 英雄ID
            lang: 语言代码
            
        Returns:
            ChampionData对象或None
        """
        print(f"正在抓取英雄ID: {champion_id}...")
        
        html = self.fetch_champion_page(champion_id, lang)
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # 解析英雄信息
        info = self.parse_champion_info(soup)
        info['champion_id'] = champion_id  # 确保ID正确
        
        # 解析各项数据
        augments = self.parse_augments(soup)
        augment_combos = self.parse_augment_combos(soup)
        build_configs = self.parse_build_configs(soup)
        
        champion_data = ChampionData(
            champion_id=info['champion_id'],
            champion_name=info['champion_name'],
            version=info['version'],
            tier=info['tier'],
            win_rate=info['win_rate'],
            pick_rate=info['pick_rate'],
            augments=augments,
            augment_combos=augment_combos,
            build_configs=build_configs
        )
        
        return champion_data
    
    def scrape_multiple_champions(self, champion_ids: List[int], lang: str = "zh-CN") -> List[ChampionData]:
        """
        批量抓取多个英雄的数据
        
        Args:
            champion_ids: 英雄ID列表
            lang: 语言代码
            
        Returns:
            ChampionData列表
        """
        results = []
        for champion_id in champion_ids:
            data = self.scrape_champion(champion_id, lang)
            if data:
                results.append(data)
        return results


def save_to_json(data: ChampionData, filepath: str):
    """保存数据到JSON文件"""
    # 将dataclass转换为字典
    def dataclass_to_dict(obj):
        if isinstance(obj, list):
            return [dataclass_to_dict(item) for item in obj]
        elif hasattr(obj, '__dataclass_fields__'):
            return {k: dataclass_to_dict(v) for k, v in asdict(obj).items()}
        else:
            return obj
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(dataclass_to_dict(data), f, ensure_ascii=False, indent=2)
    print(f"数据已保存到: {filepath}")


def print_champion_summary(data: ChampionData):
    """打印英雄数据摘要"""
    print("\n" + "="*60)
    print(f"英雄: {data.champion_name} (ID: {data.champion_id})")
    print(f"版本: {data.version} | 层级: {data.tier}")
    print(f"胜率: {data.win_rate}% | 选取率: {data.pick_rate}%")
    print("="*60)
    
    print("\n【推荐海克斯】(前10个)")
    for i, aug in enumerate(data.augments[:10], 1):
        print(f"  {i}. {aug.name} (ID: {aug.id}) - {aug.tier} - 胜率: {aug.win_rate}%")
    
    print("\n【情境装备】")
    for config in data.build_configs:
        print(f"\n  配置类型: {config.build_type}")
        print(f"  情境装备:")
        for item in config.situational_items:
            print(f"    - {item.name} (ID: {item.id})")
    
    print("\n【推荐海克斯组合】(前5个)")
    for i, combo in enumerate(data.augment_combos[:5], 1):
        aug_names = ", ".join([aug.name for aug in combo.augments])
        print(f"  {i}. {aug_names} - {combo.tier}")


# 使用示例
if __name__ == "__main__":
    scraper = HextechScraper()
    
    # 抓取单个英雄（莉莉娅，ID: 876）
    champion_id = 876
    data = scraper.scrape_champion(champion_id)
    
    if data:
        # 打印摘要
        print_champion_summary(data)
        
        # 保存到JSON
        save_to_json(data, f"champion_{champion_id}_data.json")
    else:
        print(f"抓取英雄 {champion_id} 失败")
    
    # 批量抓取示例
    # champion_ids = [876, 63, 904, 147]  # 莉莉娅、布兰德、亚恒、萨勒芬妮
    # results = scraper.scrape_multiple_champions(champion_ids)
    # for result in results:
    #     save_to_json(result, f"champion_{result.champion_id}_data.json")
))
        
        for idx, marker in enumerate(build_markers, 1):
            items = []
            win_rate = 0.0
            pick_rate = 0.0
            
            # 获取该方案的元素
            parent = marker.find_parent()
            if parent:
                # 查找装备图片
                imgs = parent.find_all('img')
                for img in imgs:
                    src = img.get('src', '')
                    match = re.search(r'/item-icons/(\d+)\.png', src)
                    if match:
                        item_id = int(match.group(1))
                        item_name = img.get('alt', '') or self._get_item_name(item_id)
                        item = Item(
                            id=item_id,
                            name=item_name,
                            icon_url=src if src.startswith('http') else urljoin(self.CDN_URL, src)
                        )
                        items.append(item)
                
                # 查找胜率和选取率文本
                text = parent.get_text()
                win_match = re.search(r'胜率[:\s]+(\d+\.?\d*)%', text)
                if win_match:
                    win_rate = float(win_match.group(1))
                pick_match = re.search(r'选取率[:\s]+(\d+\.?\d*)%', text)
                if pick_match:
                    pick_rate = float(pick_match.group(1))
            
            if items:
                build = CoreBuild(
                    rank=idx,
                    items=items,
                    win_rate=win_rate,
                    pick_rate=pick_rate
                )
                builds.append(build)
        
        return builds
    
    def parse_starter_items(self, soup: BeautifulSoup) -> List[Item]:
        """
        解析出门装
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            出门装列表
        """
        items = []
        
        # 查找"出门装"标题
        starter_heading = soup.find(string=re.compile(r'出门装'))
        if not starter_heading:
            return items
        
        # 获取出门装区域
        starter_section = starter_heading.find_parent('h3') or starter_heading.find_parent()
        if starter_section:
            imgs = starter_section.find_all('img')
            for img in imgs:
                src = img.get('src', '')
                match = re.search(r'/item-icons/(\d+)\.png', src)
                if match:
                    item_id = int(match.group(1))
                    item = Item(
                        id=item_id,
                        name=self._get_item_name(item_id),
                        icon_url=src
                    )
                    items.append(item)
        
        return items
    
    def parse_build_configs(self, soup: BeautifulSoup) -> List[BuildConfig]:
        """
        解析所有装备配置
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            装备配置列表
        """
        configs = []
        
        # 查找"装备配置"区域
        build_heading = soup.find(string=re.compile(r'装备配置'))
        if not build_heading:
            return configs
        
        # 获取版本号
        version = "16.6"  # 默认值
        version_match = re.search(r'(\d+\.\d+)', build_heading.get_text() if hasattr(build_heading, 'get_text') else str(build_heading))
        if version_match:
            version = version_match.group(1)
        
        # 查找所有出装类型（AP, APBruiser等）
        build_types = soup.find_all(string=re.compile(r'^(AP|AD|Tank|Support|APBruiser|ADAssassin)$'))
        
        for build_type_elem in build_types:
            build_type = build_type_elem.get_text(strip=True)
            
            # 获取该类型的胜率
            win_rate = 0.0
            parent = build_type_elem.find_parent()
            if parent:
                text = parent.get_text()
                win_match = re.search(r'(\d+\.?\d*)%', text)
                if win_match:
                    win_rate = float(win_match.group(1))
            
            # 解析核心出装和情境装备
            core_builds = self.parse_core_builds(soup)
            situational_items = self.parse_situational_items(soup)
            starter_items = self.parse_starter_items(soup)
            
            config = BuildConfig(
                build_type=build_type,
                win_rate=win_rate,
                core_builds=core_builds,
                situational_items=situational_items,
                starter_items=starter_items
            )
            configs.append(config)
        
        # 如果没有找到具体类型，创建一个默认配置
        if not configs:
            core_builds = self.parse_core_builds(soup)
            situational_items = self.parse_situational_items(soup)
            starter_items = self.parse_starter_items(soup)
            
            if core_builds or situational_items:
                config = BuildConfig(
                    build_type="Default",
                    win_rate=0.0,
                    core_builds=core_builds,
                    situational_items=situational_items,
                    starter_items=starter_items
                )
                configs.append(config)
        
        return configs
    
    def parse_augment_combos(self, soup: BeautifulSoup) -> List[AugmentCombo]:
        """
        解析推荐海克斯组合
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            海克斯组合列表
        """
        combos = []
        
        # 查找"推荐海克斯组合"标题
        combo_heading = soup.find(string=re.compile(r'推荐海克斯组合'))
        if not combo_heading:
            return combos
        
        # 获取组合区域
        combo_section = combo_heading.find_parent('h3') or combo_heading.find_parent()
        if combo_section:
            # 查找所有组合（通常以#1, #2等标识）
            combo_divs = soup.find_all(string=re.compile(r'^#组合'))
            
            for idx, combo_div in enumerate(combo_divs, 1):
                augments = []
                tier = "T1"
                
                parent = combo_div.find_parent()
                if parent:
                    # 查找该组合中的海克斯链接
                    augment_links = parent.find_all('a', href=re.compile(r'/augments/\d+'))
                    for link in augment_links:
                        href = link.get('href', '')
                        match = re.search(r'/augments/(\d+)', href)
                        if match:
                            augment_id = int(match.group(1))
                            name = link.get('title', '') or link.get_text(strip=True)
                            
                            img = link.find('img')
                            icon_url = img.get('src', '') if img else ''
                            
                            augment = Augment(
                                id=augment_id,
                                name=name,
                                tier="T1",
                                win_rate=0.0,
                                pick_rate=0.0,
                                icon_url=icon_url
                            )
                            augments.append(augment)
                    
                    # 提取层级
                    text = parent.get_text()
                    tier_match = re.search(r'(T\d)', text)
                    if tier_match:
                        tier = tier_match.group(1)
                
                if augments:
                    combo = AugmentCombo(
                        rank=idx,
                        augments=augments,
                        tier=tier
                    )
                    combos.append(combo)
        
        return combos
    
    def parse_champion_info(self, soup: BeautifulSoup) -> Dict:
        """
        解析英雄基本信息
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            英雄信息字典
        """
        info = {
            'champion_id': 0,
            'champion_name': '',
            'version': '16.6',
            'tier': 'T1',
            'win_rate': 0.0,
            'pick_rate': 0.0
        }
        
        # 获取英雄名称
        name_heading = soup.find('h1')
        if name_heading:
            info['champion_name'] = name_heading.get_text(strip=True)
        
        # 获取版本
        version_elem = soup.find(string=re.compile(r'版本:\s*\d+\.\d+'))
        if version_elem:
            match = re.search(r'(\d+\.\d+)', version_elem)
            if match:
                info['version'] = match.group(1)
        
        # 获取层级
        tier_elem = soup.find(string=re.compile(r'^T[1-5]$'))
        if tier_elem:
            info['tier'] = tier_elem.get_text(strip=True)
        
        # 获取胜率和选取率
        text = soup.get_text()
        win_match = re.search(r'胜率\s*\n?\s*(\d+\.?\d*)%', text)
        if win_match:
            info['win_rate'] = float(win_match.group(1))
        
        pick_match = re.search(r'选取率\s*\n?\s*(\d+\.?\d*)%', text)
        if pick_match:
            info['pick_rate'] = float(pick_match.group(1))
        
        # 从URL获取英雄ID
        canonical = soup.find('link', rel='canonical')
        if canonical:
            href = canonical.get('href', '')
            match = re.search(r'/champion-stats/(\d+)', href)
            if match:
                info['champion_id'] = int(match.group(1))
        
        return info
    
    def scrape_champion(self, champion_id: int, lang: str = "zh-CN") -> Optional[ChampionData]:
        """
        抓取单个英雄的完整数据
        
        Args:
            champion_id: 英雄ID
            lang: 语言代码
            
        Returns:
            ChampionData对象或None
        """
        print(f"正在抓取英雄ID: {champion_id}...")
        
        html = self.fetch_champion_page(champion_id, lang)
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # 解析英雄信息
        info = self.parse_champion_info(soup)
        info['champion_id'] = champion_id  # 确保ID正确
        
        # 解析各项数据
        augments = self.parse_augments(soup)
        augment_combos = self.parse_augment_combos(soup)
        build_configs = self.parse_build_configs(soup)
        
        champion_data = ChampionData(
            champion_id=info['champion_id'],
            champion_name=info['champion_name'],
            version=info['version'],
            tier=info['tier'],
            win_rate=info['win_rate'],
            pick_rate=info['pick_rate'],
            augments=augments,
            augment_combos=augment_combos,
            build_configs=build_configs
        )
        
        return champion_data
    
    def scrape_multiple_champions(self, champion_ids: List[int], lang: str = "zh-CN") -> List[ChampionData]:
        """
        批量抓取多个英雄的数据
        
        Args:
            champion_ids: 英雄ID列表
            lang: 语言代码
            
        Returns:
            ChampionData列表
        """
        results = []
        for champion_id in champion_ids:
            data = self.scrape_champion(champion_id, lang)
            if data:
                results.append(data)
        return results


def save_to_json(data: ChampionData, filepath: str):
    """保存数据到JSON文件"""
    # 将dataclass转换为字典
    def dataclass_to_dict(obj):
        if isinstance(obj, list):
            return [dataclass_to_dict(item) for item in obj]
        elif hasattr(obj, '__dataclass_fields__'):
            return {k: dataclass_to_dict(v) for k, v in asdict(obj).items()}
        else:
            return obj
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(dataclass_to_dict(data), f, ensure_ascii=False, indent=2)
    print(f"数据已保存到: {filepath}")


def print_champion_summary(data: ChampionData):
    """打印英雄数据摘要"""
    print("\n" + "="*60)
    print(f"英雄: {data.champion_name} (ID: {data.champion_id})")
    print(f"版本: {data.version} | 层级: {data.tier}")
    print(f"胜率: {data.win_rate}% | 选取率: {data.pick_rate}%")
    print("="*60)
    
    print("\n【推荐海克斯】(前10个)")
    for i, aug in enumerate(data.augments[:10], 1):
        print(f"  {i}. {aug.name} (ID: {aug.id}) - {aug.tier} - 胜率: {aug.win_rate}%")
    
    print("\n【情境装备】")
    for config in data.build_configs:
        print(f"\n  配置类型: {config.build_type}")
        print(f"  情境装备:")
        for item in config.situational_items:
            print(f"    - {item.name} (ID: {item.id})")
    
    print("\n【推荐海克斯组合】(前5个)")
    for i, combo in enumerate(data.augment_combos[:5], 1):
        aug_names = ", ".join([aug.name for aug in combo.augments])
        print(f"  {i}. {aug_names} - {combo.tier}")


# 使用示例
if __name__ == "__main__":
    scraper = HextechScraper()
    
    # 抓取单个英雄（莉莉娅，ID: 876）
    champion_id = 876
    data = scraper.scrape_champion(champion_id)
    
    if data:
        # 打印摘要
        print_champion_summary(data)
        
        # 保存到JSON
        save_to_json(data, f"champion_{champion_id}_data.json")
    else:
        print(f"抓取英雄 {champion_id} 失败")
    
    # 批量抓取示例
    # champion_ids = [876, 63, 904, 147]  # 莉莉娅、布兰德、亚恒、萨勒芬妮
    # results = scraper.scrape_multiple_champions(champion_ids)
    # for result in results:
    #     save_to_json(result, f"champion_{result.champion_id}_data.json")
))
        
        for idx, marker in enumerate(build_markers, 1):
            items = []
            win_rate = 0.0
            pick_rate = 0.0
            
            # 获取该方案的元素
            parent = marker.find_parent()
            if parent:
                # 查找装备图片
                imgs = parent.find_all('img')
                for img in imgs:
                    src = img.get('src', '')
                    match = re.search(r'/item-icons/(\d+)\.png', src)
                    if match:
                        item_id = int(match.group(1))
                        item_name = img.get('alt', '') or self._get_item_name(item_id)
                        item = Item(
                            id=item_id,
                            name=item_name,
                            icon_url=src if src.startswith('http') else urljoin(self.CDN_URL, src)
                        )
                        items.append(item)
                
                # 查找胜率和选取率文本
                text = parent.get_text()
                win_match = re.search(r'胜率[:\s]+(\d+\.?\d*)%', text)
                if win_match:
                    win_rate = float(win_match.group(1))
                pick_match = re.search(r'选取率[:\s]+(\d+\.?\d*)%', text)
                if pick_match:
                    pick_rate = float(pick_match.group(1))
            
            if items:
                build = CoreBuild(
                    rank=idx,
                    items=items,
                    win_rate=win_rate,
                    pick_rate=pick_rate
                )
                builds.append(build)
        
        return builds
    
    def parse_starter_items(self, soup: BeautifulSoup) -> List[Item]:
        """
        解析出门装
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            出门装列表
        """
        items = []
        
        # 查找"出门装"标题
        starter_heading = soup.find(string=re.compile(r'出门装'))
        if not starter_heading:
            return items
        
        # 获取出门装区域
        starter_section = starter_heading.find_parent('h3') or starter_heading.find_parent()
        if not starter_section:
            return items
        
        # 查找该区域内的所有装备图片
        imgs = starter_section.find_all('img')
        for img in imgs:
            src = img.get('src', '')
            match = re.search(r'/item-icons/(\d+)\.png', src)
            if match:
                item_id = int(match.group(1))
                item_name = img.get('alt', '') or self._get_item_name(item_id)
                item = Item(
                    id=item_id,
                    name=item_name,
                    icon_url=src if src.startswith('http') else urljoin(self.CDN_URL, src)
                )
                items.append(item)
        
        # 如果没找到，查找后续兄弟元素中的图片
        if not items:
            next_elem = starter_section.find_next_sibling()
            while next_elem and next_elem.name != 'h3':
                imgs = next_elem.find_all('img')
                for img in imgs:
                    src = img.get('src', '')
                    match = re.search(r'/item-icons/(\d+)\.png', src)
                    if match:
                        item_id = int(match.group(1))
                        item_name = img.get('alt', '') or self._get_item_name(item_id)
                        item = Item(
                            id=item_id,
                            name=item_name,
                            icon_url=src if src.startswith('http') else urljoin(self.CDN_URL, src)
                        )
                        if item_id not in [i.id for i in items]:  # 去重
                            items.append(item)
                next_elem = next_elem.find_next_sibling()
        
        return items
    
    def parse_build_configs(self, soup: BeautifulSoup) -> List[BuildConfig]:
        """
        解析所有装备配置
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            装备配置列表
        """
        configs = []
        
        # 查找"装备配置"区域
        build_heading = soup.find(string=re.compile(r'装备配置'))
        if not build_heading:
            return configs
        
        # 获取版本号
        version = "16.6"  # 默认值
        build_section = build_heading.find_parent('h3') or build_heading.find_parent()
        if build_section:
            text = build_section.get_text()
            version_match = re.search(r'(\d+\.\d+)', text)
            if version_match:
                version = version_match.group(1)
        
        # 查找所有出装类型（AP, APBruiser等）
        # 这些通常在装备配置标题后面
        build_types = []
        if build_section:
            # 查找后续兄弟元素中的出装类型
            next_elem = build_section.find_next_sibling()
            while next_elem:
                text = next_elem.get_text(strip=True)
                if re.match(r'^(AP|AD|Tank|Support|APBruiser|ADAssassin|Fighter|Mage|Marksman)
    
    def parse_augment_combos(self, soup: BeautifulSoup) -> List[AugmentCombo]:
        """
        解析推荐海克斯组合
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            海克斯组合列表
        """
        combos = []
        
        # 查找"推荐海克斯组合"标题
        combo_heading = soup.find(string=re.compile(r'推荐海克斯组合'))
        if not combo_heading:
            return combos
        
        # 获取组合区域
        combo_section = combo_heading.find_parent('h3') or combo_heading.find_parent()
        if not combo_section:
            return combos
        
        # 查找所有组合（通常以#组合1, #组合2等标识）
        combo_markers = combo_section.find_all(string=re.compile(r'^#组合\d+
    
    def parse_champion_info(self, soup: BeautifulSoup) -> Dict:
        """
        解析英雄基本信息
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            英雄信息字典
        """
        info = {
            'champion_id': 0,
            'champion_name': '',
            'version': '16.6',
            'tier': 'T1',
            'win_rate': 0.0,
            'pick_rate': 0.0
        }
        
        # 获取英雄名称
        name_heading = soup.find('h1')
        if name_heading:
            info['champion_name'] = name_heading.get_text(strip=True)
        
        # 获取版本
        version_elem = soup.find(string=re.compile(r'版本:\s*\d+\.\d+'))
        if version_elem:
            match = re.search(r'(\d+\.\d+)', version_elem)
            if match:
                info['version'] = match.group(1)
        
        # 获取层级
        tier_elem = soup.find(string=re.compile(r'^T[1-5]$'))
        if tier_elem:
            info['tier'] = tier_elem.get_text(strip=True)
        
        # 获取胜率和选取率
        text = soup.get_text()
        win_match = re.search(r'胜率\s*\n?\s*(\d+\.?\d*)%', text)
        if win_match:
            info['win_rate'] = float(win_match.group(1))
        
        pick_match = re.search(r'选取率\s*\n?\s*(\d+\.?\d*)%', text)
        if pick_match:
            info['pick_rate'] = float(pick_match.group(1))
        
        # 从URL获取英雄ID
        canonical = soup.find('link', rel='canonical')
        if canonical:
            href = canonical.get('href', '')
            match = re.search(r'/champion-stats/(\d+)', href)
            if match:
                info['champion_id'] = int(match.group(1))
        
        return info
    
    def scrape_champion(self, champion_id: int, lang: str = "zh-CN") -> Optional[ChampionData]:
        """
        抓取单个英雄的完整数据
        
        Args:
            champion_id: 英雄ID
            lang: 语言代码
            
        Returns:
            ChampionData对象或None
        """
        print(f"正在抓取英雄ID: {champion_id}...")
        
        html = self.fetch_champion_page(champion_id, lang)
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # 解析英雄信息
        info = self.parse_champion_info(soup)
        info['champion_id'] = champion_id  # 确保ID正确
        
        # 解析各项数据
        augments = self.parse_augments(soup)
        augment_combos = self.parse_augment_combos(soup)
        build_configs = self.parse_build_configs(soup)
        
        champion_data = ChampionData(
            champion_id=info['champion_id'],
            champion_name=info['champion_name'],
            version=info['version'],
            tier=info['tier'],
            win_rate=info['win_rate'],
            pick_rate=info['pick_rate'],
            augments=augments,
            augment_combos=augment_combos,
            build_configs=build_configs
        )
        
        return champion_data
    
    def scrape_multiple_champions(self, champion_ids: List[int], lang: str = "zh-CN") -> List[ChampionData]:
        """
        批量抓取多个英雄的数据
        
        Args:
            champion_ids: 英雄ID列表
            lang: 语言代码
            
        Returns:
            ChampionData列表
        """
        results = []
        for champion_id in champion_ids:
            data = self.scrape_champion(champion_id, lang)
            if data:
                results.append(data)
        return results


def save_to_json(data: ChampionData, filepath: str):
    """保存数据到JSON文件"""
    # 将dataclass转换为字典
    def dataclass_to_dict(obj):
        if isinstance(obj, list):
            return [dataclass_to_dict(item) for item in obj]
        elif hasattr(obj, '__dataclass_fields__'):
            return {k: dataclass_to_dict(v) for k, v in asdict(obj).items()}
        else:
            return obj
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(dataclass_to_dict(data), f, ensure_ascii=False, indent=2)
    print(f"数据已保存到: {filepath}")


def print_champion_summary(data: ChampionData):
    """打印英雄数据摘要"""
    print("\n" + "="*60)
    print(f"英雄: {data.champion_name} (ID: {data.champion_id})")
    print(f"版本: {data.version} | 层级: {data.tier}")
    print(f"胜率: {data.win_rate}% | 选取率: {data.pick_rate}%")
    print("="*60)
    
    print("\n【推荐海克斯】(前10个)")
    for i, aug in enumerate(data.augments[:10], 1):
        print(f"  {i}. {aug.name} (ID: {aug.id}) - {aug.tier} - 胜率: {aug.win_rate}%")
    
    print("\n【情境装备】")
    for config in data.build_configs:
        print(f"\n  配置类型: {config.build_type}")
        print(f"  情境装备:")
        for item in config.situational_items:
            print(f"    - {item.name} (ID: {item.id})")
    
    print("\n【推荐海克斯组合】(前5个)")
    for i, combo in enumerate(data.augment_combos[:5], 1):
        aug_names = ", ".join([aug.name for aug in combo.augments])
        print(f"  {i}. {aug_names} - {combo.tier}")


# 使用示例
if __name__ == "__main__":
    scraper = HextechScraper()
    
    # 抓取单个英雄（莉莉娅，ID: 876）
    champion_id = 876
    data = scraper.scrape_champion(champion_id)
    
    if data:
        # 打印摘要
        print_champion_summary(data)
        
        # 保存到JSON
        save_to_json(data, f"champion_{champion_id}_data.json")
    else:
        print(f"抓取英雄 {champion_id} 失败")
    
    # 批量抓取示例
    # champion_ids = [876, 63, 904, 147]  # 莉莉娅、布兰德、亚恒、萨勒芬妮
    # results = scraper.scrape_multiple_champions(champion_ids)
    # for result in results:
    #     save_to_json(result, f"champion_{result.champion_id}_data.json")
))
        
        for idx, marker in enumerate(build_markers, 1):
            items = []
            win_rate = 0.0
            pick_rate = 0.0
            
            # 获取该方案的元素
            parent = marker.find_parent()
            if parent:
                # 查找装备图片
                imgs = parent.find_all('img')
                for img in imgs:
                    src = img.get('src', '')
                    match = re.search(r'/item-icons/(\d+)\.png', src)
                    if match:
                        item_id = int(match.group(1))
                        item_name = img.get('alt', '') or self._get_item_name(item_id)
                        item = Item(
                            id=item_id,
                            name=item_name,
                            icon_url=src if src.startswith('http') else urljoin(self.CDN_URL, src)
                        )
                        items.append(item)
                
                # 查找胜率和选取率文本
                text = parent.get_text()
                win_match = re.search(r'胜率[:\s]+(\d+\.?\d*)%', text)
                if win_match:
                    win_rate = float(win_match.group(1))
                pick_match = re.search(r'选取率[:\s]+(\d+\.?\d*)%', text)
                if pick_match:
                    pick_rate = float(pick_match.group(1))
            
            if items:
                build = CoreBuild(
                    rank=idx,
                    items=items,
                    win_rate=win_rate,
                    pick_rate=pick_rate
                )
                builds.append(build)
        
        return builds
    
    def parse_starter_items(self, soup: BeautifulSoup) -> List[Item]:
        """
        解析出门装
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            出门装列表
        """
        items = []
        
        # 查找"出门装"标题
        starter_heading = soup.find(string=re.compile(r'出门装'))
        if not starter_heading:
            return items
        
        # 获取出门装区域
        starter_section = starter_heading.find_parent('h3') or starter_heading.find_parent()
        if starter_section:
            imgs = starter_section.find_all('img')
            for img in imgs:
                src = img.get('src', '')
                match = re.search(r'/item-icons/(\d+)\.png', src)
                if match:
                    item_id = int(match.group(1))
                    item = Item(
                        id=item_id,
                        name=self._get_item_name(item_id),
                        icon_url=src
                    )
                    items.append(item)
        
        return items
    
    def parse_build_configs(self, soup: BeautifulSoup) -> List[BuildConfig]:
        """
        解析所有装备配置
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            装备配置列表
        """
        configs = []
        
        # 查找"装备配置"区域
        build_heading = soup.find(string=re.compile(r'装备配置'))
        if not build_heading:
            return configs
        
        # 获取版本号
        version = "16.6"  # 默认值
        version_match = re.search(r'(\d+\.\d+)', build_heading.get_text() if hasattr(build_heading, 'get_text') else str(build_heading))
        if version_match:
            version = version_match.group(1)
        
        # 查找所有出装类型（AP, APBruiser等）
        build_types = soup.find_all(string=re.compile(r'^(AP|AD|Tank|Support|APBruiser|ADAssassin)$'))
        
        for build_type_elem in build_types:
            build_type = build_type_elem.get_text(strip=True)
            
            # 获取该类型的胜率
            win_rate = 0.0
            parent = build_type_elem.find_parent()
            if parent:
                text = parent.get_text()
                win_match = re.search(r'(\d+\.?\d*)%', text)
                if win_match:
                    win_rate = float(win_match.group(1))
            
            # 解析核心出装和情境装备
            core_builds = self.parse_core_builds(soup)
            situational_items = self.parse_situational_items(soup)
            starter_items = self.parse_starter_items(soup)
            
            config = BuildConfig(
                build_type=build_type,
                win_rate=win_rate,
                core_builds=core_builds,
                situational_items=situational_items,
                starter_items=starter_items
            )
            configs.append(config)
        
        # 如果没有找到具体类型，创建一个默认配置
        if not configs:
            core_builds = self.parse_core_builds(soup)
            situational_items = self.parse_situational_items(soup)
            starter_items = self.parse_starter_items(soup)
            
            if core_builds or situational_items:
                config = BuildConfig(
                    build_type="Default",
                    win_rate=0.0,
                    core_builds=core_builds,
                    situational_items=situational_items,
                    starter_items=starter_items
                )
                configs.append(config)
        
        return configs
    
    def parse_augment_combos(self, soup: BeautifulSoup) -> List[AugmentCombo]:
        """
        解析推荐海克斯组合
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            海克斯组合列表
        """
        combos = []
        
        # 查找"推荐海克斯组合"标题
        combo_heading = soup.find(string=re.compile(r'推荐海克斯组合'))
        if not combo_heading:
            return combos
        
        # 获取组合区域
        combo_section = combo_heading.find_parent('h3') or combo_heading.find_parent()
        if combo_section:
            # 查找所有组合（通常以#1, #2等标识）
            combo_divs = soup.find_all(string=re.compile(r'^#组合'))
            
            for idx, combo_div in enumerate(combo_divs, 1):
                augments = []
                tier = "T1"
                
                parent = combo_div.find_parent()
                if parent:
                    # 查找该组合中的海克斯链接
                    augment_links = parent.find_all('a', href=re.compile(r'/augments/\d+'))
                    for link in augment_links:
                        href = link.get('href', '')
                        match = re.search(r'/augments/(\d+)', href)
                        if match:
                            augment_id = int(match.group(1))
                            name = link.get('title', '') or link.get_text(strip=True)
                            
                            img = link.find('img')
                            icon_url = img.get('src', '') if img else ''
                            
                            augment = Augment(
                                id=augment_id,
                                name=name,
                                tier="T1",
                                win_rate=0.0,
                                pick_rate=0.0,
                                icon_url=icon_url
                            )
                            augments.append(augment)
                    
                    # 提取层级
                    text = parent.get_text()
                    tier_match = re.search(r'(T\d)', text)
                    if tier_match:
                        tier = tier_match.group(1)
                
                if augments:
                    combo = AugmentCombo(
                        rank=idx,
                        augments=augments,
                        tier=tier
                    )
                    combos.append(combo)
        
        return combos
    
    def parse_champion_info(self, soup: BeautifulSoup) -> Dict:
        """
        解析英雄基本信息
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            英雄信息字典
        """
        info = {
            'champion_id': 0,
            'champion_name': '',
            'version': '16.6',
            'tier': 'T1',
            'win_rate': 0.0,
            'pick_rate': 0.0
        }
        
        # 获取英雄名称
        name_heading = soup.find('h1')
        if name_heading:
            info['champion_name'] = name_heading.get_text(strip=True)
        
        # 获取版本
        version_elem = soup.find(string=re.compile(r'版本:\s*\d+\.\d+'))
        if version_elem:
            match = re.search(r'(\d+\.\d+)', version_elem)
            if match:
                info['version'] = match.group(1)
        
        # 获取层级
        tier_elem = soup.find(string=re.compile(r'^T[1-5]$'))
        if tier_elem:
            info['tier'] = tier_elem.get_text(strip=True)
        
        # 获取胜率和选取率
        text = soup.get_text()
        win_match = re.search(r'胜率\s*\n?\s*(\d+\.?\d*)%', text)
        if win_match:
            info['win_rate'] = float(win_match.group(1))
        
        pick_match = re.search(r'选取率\s*\n?\s*(\d+\.?\d*)%', text)
        if pick_match:
            info['pick_rate'] = float(pick_match.group(1))
        
        # 从URL获取英雄ID
        canonical = soup.find('link', rel='canonical')
        if canonical:
            href = canonical.get('href', '')
            match = re.search(r'/champion-stats/(\d+)', href)
            if match:
                info['champion_id'] = int(match.group(1))
        
        return info
    
    def scrape_champion(self, champion_id: int, lang: str = "zh-CN") -> Optional[ChampionData]:
        """
        抓取单个英雄的完整数据
        
        Args:
            champion_id: 英雄ID
            lang: 语言代码
            
        Returns:
            ChampionData对象或None
        """
        print(f"正在抓取英雄ID: {champion_id}...")
        
        html = self.fetch_champion_page(champion_id, lang)
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # 解析英雄信息
        info = self.parse_champion_info(soup)
        info['champion_id'] = champion_id  # 确保ID正确
        
        # 解析各项数据
        augments = self.parse_augments(soup)
        augment_combos = self.parse_augment_combos(soup)
        build_configs = self.parse_build_configs(soup)
        
        champion_data = ChampionData(
            champion_id=info['champion_id'],
            champion_name=info['champion_name'],
            version=info['version'],
            tier=info['tier'],
            win_rate=info['win_rate'],
            pick_rate=info['pick_rate'],
            augments=augments,
            augment_combos=augment_combos,
            build_configs=build_configs
        )
        
        return champion_data
    
    def scrape_multiple_champions(self, champion_ids: List[int], lang: str = "zh-CN") -> List[ChampionData]:
        """
        批量抓取多个英雄的数据
        
        Args:
            champion_ids: 英雄ID列表
            lang: 语言代码
            
        Returns:
            ChampionData列表
        """
        results = []
        for champion_id in champion_ids:
            data = self.scrape_champion(champion_id, lang)
            if data:
                results.append(data)
        return results


def save_to_json(data: ChampionData, filepath: str):
    """保存数据到JSON文件"""
    # 将dataclass转换为字典
    def dataclass_to_dict(obj):
        if isinstance(obj, list):
            return [dataclass_to_dict(item) for item in obj]
        elif hasattr(obj, '__dataclass_fields__'):
            return {k: dataclass_to_dict(v) for k, v in asdict(obj).items()}
        else:
            return obj
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(dataclass_to_dict(data), f, ensure_ascii=False, indent=2)
    print(f"数据已保存到: {filepath}")


def print_champion_summary(data: ChampionData):
    """打印英雄数据摘要"""
    print("\n" + "="*60)
    print(f"英雄: {data.champion_name} (ID: {data.champion_id})")
    print(f"版本: {data.version} | 层级: {data.tier}")
    print(f"胜率: {data.win_rate}% | 选取率: {data.pick_rate}%")
    print("="*60)
    
    print("\n【推荐海克斯】(前10个)")
    for i, aug in enumerate(data.augments[:10], 1):
        print(f"  {i}. {aug.name} (ID: {aug.id}) - {aug.tier} - 胜率: {aug.win_rate}%")
    
    print("\n【情境装备】")
    for config in data.build_configs:
        print(f"\n  配置类型: {config.build_type}")
        print(f"  情境装备:")
        for item in config.situational_items:
            print(f"    - {item.name} (ID: {item.id})")
    
    print("\n【推荐海克斯组合】(前5个)")
    for i, combo in enumerate(data.augment_combos[:5], 1):
        aug_names = ", ".join([aug.name for aug in combo.augments])
        print(f"  {i}. {aug_names} - {combo.tier}")


# 使用示例
if __name__ == "__main__":
    scraper = HextechScraper()
    
    # 抓取单个英雄（莉莉娅，ID: 876）
    champion_id = 876
    data = scraper.scrape_champion(champion_id)
    
    if data:
        # 打印摘要
        print_champion_summary(data)
        
        # 保存到JSON
        save_to_json(data, f"champion_{champion_id}_data.json")
    else:
        print(f"抓取英雄 {champion_id} 失败")
    
    # 批量抓取示例
    # champion_ids = [876, 63, 904, 147]  # 莉莉娅、布兰德、亚恒、萨勒芬妮
    # results = scraper.scrape_multiple_champions(champion_ids)
    # for result in results:
    #     save_to_json(result, f"champion_{result.champion_id}_data.json")
))
        
        for idx, marker in enumerate(combo_markers, 1):
            augments = []
            tier = "T1"
            
            parent = marker.find_parent()
            if parent:
                # 查找该组合中的海克斯链接
                augment_links = parent.find_all('a', href=re.compile(r'/augments/\d+'))
                for link in augment_links:
                    href = link.get('href', '')
                    match = re.search(r'/augments/(\d+)', href)
                    if match:
                        augment_id = int(match.group(1))
                        name = link.get('title', '') or link.get_text(strip=True)
                        # 去掉#号
                        name = re.sub(r'^#', '', name)
                        
                        img = link.find('img')
                        icon_url = ''
                        if img:
                            icon_url = img.get('src', '')
                            if icon_url and not icon_url.startswith('http'):
                                icon_url = urljoin(self.CDN_URL, icon_url)
                        
                        augment = Augment(
                            id=augment_id,
                            name=name,
                            tier="T1",
                            win_rate=0.0,
                            pick_rate=0.0,
                            icon_url=icon_url
                        )
                        augments.append(augment)
                
                # 提取层级
                text = parent.get_text()
                tier_match = re.search(r'(T[1-5])', text)
                if tier_match:
                    tier = tier_match.group(1)
            
            if augments:
                combo = AugmentCombo(
                    rank=idx,
                    augments=augments,
                    tier=tier
                )
                combos.append(combo)
        
        return combos
    
    def parse_champion_info(self, soup: BeautifulSoup) -> Dict:
        """
        解析英雄基本信息
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            英雄信息字典
        """
        info = {
            'champion_id': 0,
            'champion_name': '',
            'version': '16.6',
            'tier': 'T1',
            'win_rate': 0.0,
            'pick_rate': 0.0
        }
        
        # 获取英雄名称
        name_heading = soup.find('h1')
        if name_heading:
            info['champion_name'] = name_heading.get_text(strip=True)
        
        # 获取版本
        version_elem = soup.find(string=re.compile(r'版本:\s*\d+\.\d+'))
        if version_elem:
            match = re.search(r'(\d+\.\d+)', version_elem)
            if match:
                info['version'] = match.group(1)
        
        # 获取层级
        tier_elem = soup.find(string=re.compile(r'^T[1-5]$'))
        if tier_elem:
            info['tier'] = tier_elem.get_text(strip=True)
        
        # 获取胜率和选取率
        text = soup.get_text()
        win_match = re.search(r'胜率\s*\n?\s*(\d+\.?\d*)%', text)
        if win_match:
            info['win_rate'] = float(win_match.group(1))
        
        pick_match = re.search(r'选取率\s*\n?\s*(\d+\.?\d*)%', text)
        if pick_match:
            info['pick_rate'] = float(pick_match.group(1))
        
        # 从URL获取英雄ID
        canonical = soup.find('link', rel='canonical')
        if canonical:
            href = canonical.get('href', '')
            match = re.search(r'/champion-stats/(\d+)', href)
            if match:
                info['champion_id'] = int(match.group(1))
        
        return info
    
    def scrape_champion(self, champion_id: int, lang: str = "zh-CN") -> Optional[ChampionData]:
        """
        抓取单个英雄的完整数据
        
        Args:
            champion_id: 英雄ID
            lang: 语言代码
            
        Returns:
            ChampionData对象或None
        """
        print(f"正在抓取英雄ID: {champion_id}...")
        
        html = self.fetch_champion_page(champion_id, lang)
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # 解析英雄信息
        info = self.parse_champion_info(soup)
        info['champion_id'] = champion_id  # 确保ID正确
        
        # 解析各项数据
        augments = self.parse_augments(soup)
        augment_combos = self.parse_augment_combos(soup)
        build_configs = self.parse_build_configs(soup)
        
        champion_data = ChampionData(
            champion_id=info['champion_id'],
            champion_name=info['champion_name'],
            version=info['version'],
            tier=info['tier'],
            win_rate=info['win_rate'],
            pick_rate=info['pick_rate'],
            augments=augments,
            augment_combos=augment_combos,
            build_configs=build_configs
        )
        
        return champion_data
    
    def scrape_multiple_champions(self, champion_ids: List[int], lang: str = "zh-CN") -> List[ChampionData]:
        """
        批量抓取多个英雄的数据
        
        Args:
            champion_ids: 英雄ID列表
            lang: 语言代码
            
        Returns:
            ChampionData列表
        """
        results = []
        for champion_id in champion_ids:
            data = self.scrape_champion(champion_id, lang)
            if data:
                results.append(data)
        return results


def save_to_json(data: ChampionData, filepath: str):
    """保存数据到JSON文件"""
    # 将dataclass转换为字典
    def dataclass_to_dict(obj):
        if isinstance(obj, list):
            return [dataclass_to_dict(item) for item in obj]
        elif hasattr(obj, '__dataclass_fields__'):
            return {k: dataclass_to_dict(v) for k, v in asdict(obj).items()}
        else:
            return obj
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(dataclass_to_dict(data), f, ensure_ascii=False, indent=2)
    print(f"数据已保存到: {filepath}")


def print_champion_summary(data: ChampionData):
    """打印英雄数据摘要"""
    print("\n" + "="*60)
    print(f"英雄: {data.champion_name} (ID: {data.champion_id})")
    print(f"版本: {data.version} | 层级: {data.tier}")
    print(f"胜率: {data.win_rate}% | 选取率: {data.pick_rate}%")
    print("="*60)
    
    print("\n【推荐海克斯】(前10个)")
    for i, aug in enumerate(data.augments[:10], 1):
        print(f"  {i}. {aug.name} (ID: {aug.id}) - {aug.tier} - 胜率: {aug.win_rate}%")
    
    print("\n【情境装备】")
    for config in data.build_configs:
        print(f"\n  配置类型: {config.build_type}")
        print(f"  情境装备:")
        for item in config.situational_items:
            print(f"    - {item.name} (ID: {item.id})")
    
    print("\n【推荐海克斯组合】(前5个)")
    for i, combo in enumerate(data.augment_combos[:5], 1):
        aug_names = ", ".join([aug.name for aug in combo.augments])
        print(f"  {i}. {aug_names} - {combo.tier}")


# 使用示例
if __name__ == "__main__":
    scraper = HextechScraper()
    
    # 抓取单个英雄（莉莉娅，ID: 876）
    champion_id = 876
    data = scraper.scrape_champion(champion_id)
    
    if data:
        # 打印摘要
        print_champion_summary(data)
        
        # 保存到JSON
        save_to_json(data, f"champion_{champion_id}_data.json")
    else:
        print(f"抓取英雄 {champion_id} 失败")
    
    # 批量抓取示例
    # champion_ids = [876, 63, 904, 147]  # 莉莉娅、布兰德、亚恒、萨勒芬妮
    # results = scraper.scrape_multiple_champions(champion_ids)
    # for result in results:
    #     save_to_json(result, f"champion_{result.champion_id}_data.json")
))
        
        for idx, marker in enumerate(build_markers, 1):
            items = []
            win_rate = 0.0
            pick_rate = 0.0
            
            # 获取该方案的元素
            parent = marker.find_parent()
            if parent:
                # 查找装备图片
                imgs = parent.find_all('img')
                for img in imgs:
                    src = img.get('src', '')
                    match = re.search(r'/item-icons/(\d+)\.png', src)
                    if match:
                        item_id = int(match.group(1))
                        item_name = img.get('alt', '') or self._get_item_name(item_id)
                        item = Item(
                            id=item_id,
                            name=item_name,
                            icon_url=src if src.startswith('http') else urljoin(self.CDN_URL, src)
                        )
                        items.append(item)
                
                # 查找胜率和选取率文本
                text = parent.get_text()
                win_match = re.search(r'胜率[:\s]+(\d+\.?\d*)%', text)
                if win_match:
                    win_rate = float(win_match.group(1))
                pick_match = re.search(r'选取率[:\s]+(\d+\.?\d*)%', text)
                if pick_match:
                    pick_rate = float(pick_match.group(1))
            
            if items:
                build = CoreBuild(
                    rank=idx,
                    items=items,
                    win_rate=win_rate,
                    pick_rate=pick_rate
                )
                builds.append(build)
        
        return builds
    
    def parse_starter_items(self, soup: BeautifulSoup) -> List[Item]:
        """
        解析出门装
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            出门装列表
        """
        items = []
        
        # 查找"出门装"标题
        starter_heading = soup.find(string=re.compile(r'出门装'))
        if not starter_heading:
            return items
        
        # 获取出门装区域
        starter_section = starter_heading.find_parent('h3') or starter_heading.find_parent()
        if starter_section:
            imgs = starter_section.find_all('img')
            for img in imgs:
                src = img.get('src', '')
                match = re.search(r'/item-icons/(\d+)\.png', src)
                if match:
                    item_id = int(match.group(1))
                    item = Item(
                        id=item_id,
                        name=self._get_item_name(item_id),
                        icon_url=src
                    )
                    items.append(item)
        
        return items
    
    def parse_build_configs(self, soup: BeautifulSoup) -> List[BuildConfig]:
        """
        解析所有装备配置
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            装备配置列表
        """
        configs = []
        
        # 查找"装备配置"区域
        build_heading = soup.find(string=re.compile(r'装备配置'))
        if not build_heading:
            return configs
        
        # 获取版本号
        version = "16.6"  # 默认值
        version_match = re.search(r'(\d+\.\d+)', build_heading.get_text() if hasattr(build_heading, 'get_text') else str(build_heading))
        if version_match:
            version = version_match.group(1)
        
        # 查找所有出装类型（AP, APBruiser等）
        build_types = soup.find_all(string=re.compile(r'^(AP|AD|Tank|Support|APBruiser|ADAssassin)$'))
        
        for build_type_elem in build_types:
            build_type = build_type_elem.get_text(strip=True)
            
            # 获取该类型的胜率
            win_rate = 0.0
            parent = build_type_elem.find_parent()
            if parent:
                text = parent.get_text()
                win_match = re.search(r'(\d+\.?\d*)%', text)
                if win_match:
                    win_rate = float(win_match.group(1))
            
            # 解析核心出装和情境装备
            core_builds = self.parse_core_builds(soup)
            situational_items = self.parse_situational_items(soup)
            starter_items = self.parse_starter_items(soup)
            
            config = BuildConfig(
                build_type=build_type,
                win_rate=win_rate,
                core_builds=core_builds,
                situational_items=situational_items,
                starter_items=starter_items
            )
            configs.append(config)
        
        # 如果没有找到具体类型，创建一个默认配置
        if not configs:
            core_builds = self.parse_core_builds(soup)
            situational_items = self.parse_situational_items(soup)
            starter_items = self.parse_starter_items(soup)
            
            if core_builds or situational_items:
                config = BuildConfig(
                    build_type="Default",
                    win_rate=0.0,
                    core_builds=core_builds,
                    situational_items=situational_items,
                    starter_items=starter_items
                )
                configs.append(config)
        
        return configs
    
    def parse_augment_combos(self, soup: BeautifulSoup) -> List[AugmentCombo]:
        """
        解析推荐海克斯组合
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            海克斯组合列表
        """
        combos = []
        
        # 查找"推荐海克斯组合"标题
        combo_heading = soup.find(string=re.compile(r'推荐海克斯组合'))
        if not combo_heading:
            return combos
        
        # 获取组合区域
        combo_section = combo_heading.find_parent('h3') or combo_heading.find_parent()
        if combo_section:
            # 查找所有组合（通常以#1, #2等标识）
            combo_divs = soup.find_all(string=re.compile(r'^#组合'))
            
            for idx, combo_div in enumerate(combo_divs, 1):
                augments = []
                tier = "T1"
                
                parent = combo_div.find_parent()
                if parent:
                    # 查找该组合中的海克斯链接
                    augment_links = parent.find_all('a', href=re.compile(r'/augments/\d+'))
                    for link in augment_links:
                        href = link.get('href', '')
                        match = re.search(r'/augments/(\d+)', href)
                        if match:
                            augment_id = int(match.group(1))
                            name = link.get('title', '') or link.get_text(strip=True)
                            
                            img = link.find('img')
                            icon_url = img.get('src', '') if img else ''
                            
                            augment = Augment(
                                id=augment_id,
                                name=name,
                                tier="T1",
                                win_rate=0.0,
                                pick_rate=0.0,
                                icon_url=icon_url
                            )
                            augments.append(augment)
                    
                    # 提取层级
                    text = parent.get_text()
                    tier_match = re.search(r'(T\d)', text)
                    if tier_match:
                        tier = tier_match.group(1)
                
                if augments:
                    combo = AugmentCombo(
                        rank=idx,
                        augments=augments,
                        tier=tier
                    )
                    combos.append(combo)
        
        return combos
    
    def parse_champion_info(self, soup: BeautifulSoup) -> Dict:
        """
        解析英雄基本信息
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            英雄信息字典
        """
        info = {
            'champion_id': 0,
            'champion_name': '',
            'version': '16.6',
            'tier': 'T1',
            'win_rate': 0.0,
            'pick_rate': 0.0
        }
        
        # 获取英雄名称
        name_heading = soup.find('h1')
        if name_heading:
            info['champion_name'] = name_heading.get_text(strip=True)
        
        # 获取版本
        version_elem = soup.find(string=re.compile(r'版本:\s*\d+\.\d+'))
        if version_elem:
            match = re.search(r'(\d+\.\d+)', version_elem)
            if match:
                info['version'] = match.group(1)
        
        # 获取层级
        tier_elem = soup.find(string=re.compile(r'^T[1-5]$'))
        if tier_elem:
            info['tier'] = tier_elem.get_text(strip=True)
        
        # 获取胜率和选取率
        text = soup.get_text()
        win_match = re.search(r'胜率\s*\n?\s*(\d+\.?\d*)%', text)
        if win_match:
            info['win_rate'] = float(win_match.group(1))
        
        pick_match = re.search(r'选取率\s*\n?\s*(\d+\.?\d*)%', text)
        if pick_match:
            info['pick_rate'] = float(pick_match.group(1))
        
        # 从URL获取英雄ID
        canonical = soup.find('link', rel='canonical')
        if canonical:
            href = canonical.get('href', '')
            match = re.search(r'/champion-stats/(\d+)', href)
            if match:
                info['champion_id'] = int(match.group(1))
        
        return info
    
    def scrape_champion(self, champion_id: int, lang: str = "zh-CN") -> Optional[ChampionData]:
        """
        抓取单个英雄的完整数据
        
        Args:
            champion_id: 英雄ID
            lang: 语言代码
            
        Returns:
            ChampionData对象或None
        """
        print(f"正在抓取英雄ID: {champion_id}...")
        
        html = self.fetch_champion_page(champion_id, lang)
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # 解析英雄信息
        info = self.parse_champion_info(soup)
        info['champion_id'] = champion_id  # 确保ID正确
        
        # 解析各项数据
        augments = self.parse_augments(soup)
        augment_combos = self.parse_augment_combos(soup)
        build_configs = self.parse_build_configs(soup)
        
        champion_data = ChampionData(
            champion_id=info['champion_id'],
            champion_name=info['champion_name'],
            version=info['version'],
            tier=info['tier'],
            win_rate=info['win_rate'],
            pick_rate=info['pick_rate'],
            augments=augments,
            augment_combos=augment_combos,
            build_configs=build_configs
        )
        
        return champion_data
    
    def scrape_multiple_champions(self, champion_ids: List[int], lang: str = "zh-CN") -> List[ChampionData]:
        """
        批量抓取多个英雄的数据
        
        Args:
            champion_ids: 英雄ID列表
            lang: 语言代码
            
        Returns:
            ChampionData列表
        """
        results = []
        for champion_id in champion_ids:
            data = self.scrape_champion(champion_id, lang)
            if data:
                results.append(data)
        return results


def save_to_json(data: ChampionData, filepath: str):
    """保存数据到JSON文件"""
    # 将dataclass转换为字典
    def dataclass_to_dict(obj):
        if isinstance(obj, list):
            return [dataclass_to_dict(item) for item in obj]
        elif hasattr(obj, '__dataclass_fields__'):
            return {k: dataclass_to_dict(v) for k, v in asdict(obj).items()}
        else:
            return obj
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(dataclass_to_dict(data), f, ensure_ascii=False, indent=2)
    print(f"数据已保存到: {filepath}")


def print_champion_summary(data: ChampionData):
    """打印英雄数据摘要"""
    print("\n" + "="*60)
    print(f"英雄: {data.champion_name} (ID: {data.champion_id})")
    print(f"版本: {data.version} | 层级: {data.tier}")
    print(f"胜率: {data.win_rate}% | 选取率: {data.pick_rate}%")
    print("="*60)
    
    print("\n【推荐海克斯】(前10个)")
    for i, aug in enumerate(data.augments[:10], 1):
        print(f"  {i}. {aug.name} (ID: {aug.id}) - {aug.tier} - 胜率: {aug.win_rate}%")
    
    print("\n【情境装备】")
    for config in data.build_configs:
        print(f"\n  配置类型: {config.build_type}")
        print(f"  情境装备:")
        for item in config.situational_items:
            print(f"    - {item.name} (ID: {item.id})")
    
    print("\n【推荐海克斯组合】(前5个)")
    for i, combo in enumerate(data.augment_combos[:5], 1):
        aug_names = ", ".join([aug.name for aug in combo.augments])
        print(f"  {i}. {aug_names} - {combo.tier}")


# 使用示例
if __name__ == "__main__":
    scraper = HextechScraper()
    
    # 抓取单个英雄（莉莉娅，ID: 876）
    champion_id = 876
    data = scraper.scrape_champion(champion_id)
    
    if data:
        # 打印摘要
        print_champion_summary(data)
        
        # 保存到JSON
        save_to_json(data, f"champion_{champion_id}_data.json")
    else:
        print(f"抓取英雄 {champion_id} 失败")
    
    # 批量抓取示例
    # champion_ids = [876, 63, 904, 147]  # 莉莉娅、布兰德、亚恒、萨勒芬妮
    # results = scraper.scrape_multiple_champions(champion_ids)
    # for result in results:
    #     save_to_json(result, f"champion_{result.champion_id}_data.json")
, text):
                    build_types.append((next_elem, text))
                next_elem = next_elem.find_next_sibling()
        
        # 解析核心出装、情境装备和出门装（这些是共享的）
        core_builds = self.parse_core_builds(soup)
        situational_items = self.parse_situational_items(soup)
        starter_items = self.parse_starter_items(soup)
        
        for build_type_elem, build_type in build_types:
            # 获取该类型的胜率
            win_rate = 0.0
            parent = build_type_elem.find_parent()
            if parent:
                text = parent.get_text()
                # 查找该类型后面的百分比
                win_match = re.search(rf'{re.escape(build_type)}.*?\n?\s*(\d+\.?\d*)%', text, re.DOTALL)
                if win_match:
                    win_rate = float(win_match.group(1))
            
            config = BuildConfig(
                build_type=build_type,
                win_rate=win_rate,
                core_builds=core_builds,
                situational_items=situational_items,
                starter_items=starter_items
            )
            configs.append(config)
        
        # 如果没有找到具体类型，创建一个默认配置
        if not configs:
            if core_builds or situational_items or starter_items:
                config = BuildConfig(
                    build_type="Default",
                    win_rate=0.0,
                    core_builds=core_builds,
                    situational_items=situational_items,
                    starter_items=starter_items
                )
                configs.append(config)
        
        return configs
    
    def parse_augment_combos(self, soup: BeautifulSoup) -> List[AugmentCombo]:
        """
        解析推荐海克斯组合
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            海克斯组合列表
        """
        combos = []
        
        # 查找"推荐海克斯组合"标题
        combo_heading = soup.find(string=re.compile(r'推荐海克斯组合'))
        if not combo_heading:
            return combos
        
        # 获取组合区域
        combo_section = combo_heading.find_parent('h3') or combo_heading.find_parent()
        if not combo_section:
            return combos
        
        # 查找所有组合（通常以#组合1, #组合2等标识）
        combo_markers = combo_section.find_all(string=re.compile(r'^#组合\d+
    
    def parse_champion_info(self, soup: BeautifulSoup) -> Dict:
        """
        解析英雄基本信息
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            英雄信息字典
        """
        info = {
            'champion_id': 0,
            'champion_name': '',
            'version': '16.6',
            'tier': 'T1',
            'win_rate': 0.0,
            'pick_rate': 0.0
        }
        
        # 获取英雄名称
        name_heading = soup.find('h1')
        if name_heading:
            info['champion_name'] = name_heading.get_text(strip=True)
        
        # 获取版本
        version_elem = soup.find(string=re.compile(r'版本:\s*\d+\.\d+'))
        if version_elem:
            match = re.search(r'(\d+\.\d+)', version_elem)
            if match:
                info['version'] = match.group(1)
        
        # 获取层级
        tier_elem = soup.find(string=re.compile(r'^T[1-5]$'))
        if tier_elem:
            info['tier'] = tier_elem.get_text(strip=True)
        
        # 获取胜率和选取率
        text = soup.get_text()
        win_match = re.search(r'胜率\s*\n?\s*(\d+\.?\d*)%', text)
        if win_match:
            info['win_rate'] = float(win_match.group(1))
        
        pick_match = re.search(r'选取率\s*\n?\s*(\d+\.?\d*)%', text)
        if pick_match:
            info['pick_rate'] = float(pick_match.group(1))
        
        # 从URL获取英雄ID
        canonical = soup.find('link', rel='canonical')
        if canonical:
            href = canonical.get('href', '')
            match = re.search(r'/champion-stats/(\d+)', href)
            if match:
                info['champion_id'] = int(match.group(1))
        
        return info
    
    def scrape_champion(self, champion_id: int, lang: str = "zh-CN") -> Optional[ChampionData]:
        """
        抓取单个英雄的完整数据
        
        Args:
            champion_id: 英雄ID
            lang: 语言代码
            
        Returns:
            ChampionData对象或None
        """
        print(f"正在抓取英雄ID: {champion_id}...")
        
        html = self.fetch_champion_page(champion_id, lang)
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # 解析英雄信息
        info = self.parse_champion_info(soup)
        info['champion_id'] = champion_id  # 确保ID正确
        
        # 解析各项数据
        augments = self.parse_augments(soup)
        augment_combos = self.parse_augment_combos(soup)
        build_configs = self.parse_build_configs(soup)
        
        champion_data = ChampionData(
            champion_id=info['champion_id'],
            champion_name=info['champion_name'],
            version=info['version'],
            tier=info['tier'],
            win_rate=info['win_rate'],
            pick_rate=info['pick_rate'],
            augments=augments,
            augment_combos=augment_combos,
            build_configs=build_configs
        )
        
        return champion_data
    
    def scrape_multiple_champions(self, champion_ids: List[int], lang: str = "zh-CN") -> List[ChampionData]:
        """
        批量抓取多个英雄的数据
        
        Args:
            champion_ids: 英雄ID列表
            lang: 语言代码
            
        Returns:
            ChampionData列表
        """
        results = []
        for champion_id in champion_ids:
            data = self.scrape_champion(champion_id, lang)
            if data:
                results.append(data)
        return results


def save_to_json(data: ChampionData, filepath: str):
    """保存数据到JSON文件"""
    # 将dataclass转换为字典
    def dataclass_to_dict(obj):
        if isinstance(obj, list):
            return [dataclass_to_dict(item) for item in obj]
        elif hasattr(obj, '__dataclass_fields__'):
            return {k: dataclass_to_dict(v) for k, v in asdict(obj).items()}
        else:
            return obj
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(dataclass_to_dict(data), f, ensure_ascii=False, indent=2)
    print(f"数据已保存到: {filepath}")


def print_champion_summary(data: ChampionData):
    """打印英雄数据摘要"""
    print("\n" + "="*60)
    print(f"英雄: {data.champion_name} (ID: {data.champion_id})")
    print(f"版本: {data.version} | 层级: {data.tier}")
    print(f"胜率: {data.win_rate}% | 选取率: {data.pick_rate}%")
    print("="*60)
    
    print("\n【推荐海克斯】(前10个)")
    for i, aug in enumerate(data.augments[:10], 1):
        print(f"  {i}. {aug.name} (ID: {aug.id}) - {aug.tier} - 胜率: {aug.win_rate}%")
    
    print("\n【情境装备】")
    for config in data.build_configs:
        print(f"\n  配置类型: {config.build_type}")
        print(f"  情境装备:")
        for item in config.situational_items:
            print(f"    - {item.name} (ID: {item.id})")
    
    print("\n【推荐海克斯组合】(前5个)")
    for i, combo in enumerate(data.augment_combos[:5], 1):
        aug_names = ", ".join([aug.name for aug in combo.augments])
        print(f"  {i}. {aug_names} - {combo.tier}")


# 使用示例
if __name__ == "__main__":
    scraper = HextechScraper()
    
    # 抓取单个英雄（莉莉娅，ID: 876）
    champion_id = 876
    data = scraper.scrape_champion(champion_id)
    
    if data:
        # 打印摘要
        print_champion_summary(data)
        
        # 保存到JSON
        save_to_json(data, f"champion_{champion_id}_data.json")
    else:
        print(f"抓取英雄 {champion_id} 失败")
    
    # 批量抓取示例
    # champion_ids = [876, 63, 904, 147]  # 莉莉娅、布兰德、亚恒、萨勒芬妮
    # results = scraper.scrape_multiple_champions(champion_ids)
    # for result in results:
    #     save_to_json(result, f"champion_{result.champion_id}_data.json")
))
        
        for idx, marker in enumerate(build_markers, 1):
            items = []
            win_rate = 0.0
            pick_rate = 0.0
            
            # 获取该方案的元素
            parent = marker.find_parent()
            if parent:
                # 查找装备图片
                imgs = parent.find_all('img')
                for img in imgs:
                    src = img.get('src', '')
                    match = re.search(r'/item-icons/(\d+)\.png', src)
                    if match:
                        item_id = int(match.group(1))
                        item_name = img.get('alt', '') or self._get_item_name(item_id)
                        item = Item(
                            id=item_id,
                            name=item_name,
                            icon_url=src if src.startswith('http') else urljoin(self.CDN_URL, src)
                        )
                        items.append(item)
                
                # 查找胜率和选取率文本
                text = parent.get_text()
                win_match = re.search(r'胜率[:\s]+(\d+\.?\d*)%', text)
                if win_match:
                    win_rate = float(win_match.group(1))
                pick_match = re.search(r'选取率[:\s]+(\d+\.?\d*)%', text)
                if pick_match:
                    pick_rate = float(pick_match.group(1))
            
            if items:
                build = CoreBuild(
                    rank=idx,
                    items=items,
                    win_rate=win_rate,
                    pick_rate=pick_rate
                )
                builds.append(build)
        
        return builds
    
    def parse_starter_items(self, soup: BeautifulSoup) -> List[Item]:
        """
        解析出门装
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            出门装列表
        """
        items = []
        
        # 查找"出门装"标题
        starter_heading = soup.find(string=re.compile(r'出门装'))
        if not starter_heading:
            return items
        
        # 获取出门装区域
        starter_section = starter_heading.find_parent('h3') or starter_heading.find_parent()
        if starter_section:
            imgs = starter_section.find_all('img')
            for img in imgs:
                src = img.get('src', '')
                match = re.search(r'/item-icons/(\d+)\.png', src)
                if match:
                    item_id = int(match.group(1))
                    item = Item(
                        id=item_id,
                        name=self._get_item_name(item_id),
                        icon_url=src
                    )
                    items.append(item)
        
        return items
    
    def parse_build_configs(self, soup: BeautifulSoup) -> List[BuildConfig]:
        """
        解析所有装备配置
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            装备配置列表
        """
        configs = []
        
        # 查找"装备配置"区域
        build_heading = soup.find(string=re.compile(r'装备配置'))
        if not build_heading:
            return configs
        
        # 获取版本号
        version = "16.6"  # 默认值
        version_match = re.search(r'(\d+\.\d+)', build_heading.get_text() if hasattr(build_heading, 'get_text') else str(build_heading))
        if version_match:
            version = version_match.group(1)
        
        # 查找所有出装类型（AP, APBruiser等）
        build_types = soup.find_all(string=re.compile(r'^(AP|AD|Tank|Support|APBruiser|ADAssassin)$'))
        
        for build_type_elem in build_types:
            build_type = build_type_elem.get_text(strip=True)
            
            # 获取该类型的胜率
            win_rate = 0.0
            parent = build_type_elem.find_parent()
            if parent:
                text = parent.get_text()
                win_match = re.search(r'(\d+\.?\d*)%', text)
                if win_match:
                    win_rate = float(win_match.group(1))
            
            # 解析核心出装和情境装备
            core_builds = self.parse_core_builds(soup)
            situational_items = self.parse_situational_items(soup)
            starter_items = self.parse_starter_items(soup)
            
            config = BuildConfig(
                build_type=build_type,
                win_rate=win_rate,
                core_builds=core_builds,
                situational_items=situational_items,
                starter_items=starter_items
            )
            configs.append(config)
        
        # 如果没有找到具体类型，创建一个默认配置
        if not configs:
            core_builds = self.parse_core_builds(soup)
            situational_items = self.parse_situational_items(soup)
            starter_items = self.parse_starter_items(soup)
            
            if core_builds or situational_items:
                config = BuildConfig(
                    build_type="Default",
                    win_rate=0.0,
                    core_builds=core_builds,
                    situational_items=situational_items,
                    starter_items=starter_items
                )
                configs.append(config)
        
        return configs
    
    def parse_augment_combos(self, soup: BeautifulSoup) -> List[AugmentCombo]:
        """
        解析推荐海克斯组合
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            海克斯组合列表
        """
        combos = []
        
        # 查找"推荐海克斯组合"标题
        combo_heading = soup.find(string=re.compile(r'推荐海克斯组合'))
        if not combo_heading:
            return combos
        
        # 获取组合区域
        combo_section = combo_heading.find_parent('h3') or combo_heading.find_parent()
        if combo_section:
            # 查找所有组合（通常以#1, #2等标识）
            combo_divs = soup.find_all(string=re.compile(r'^#组合'))
            
            for idx, combo_div in enumerate(combo_divs, 1):
                augments = []
                tier = "T1"
                
                parent = combo_div.find_parent()
                if parent:
                    # 查找该组合中的海克斯链接
                    augment_links = parent.find_all('a', href=re.compile(r'/augments/\d+'))
                    for link in augment_links:
                        href = link.get('href', '')
                        match = re.search(r'/augments/(\d+)', href)
                        if match:
                            augment_id = int(match.group(1))
                            name = link.get('title', '') or link.get_text(strip=True)
                            
                            img = link.find('img')
                            icon_url = img.get('src', '') if img else ''
                            
                            augment = Augment(
                                id=augment_id,
                                name=name,
                                tier="T1",
                                win_rate=0.0,
                                pick_rate=0.0,
                                icon_url=icon_url
                            )
                            augments.append(augment)
                    
                    # 提取层级
                    text = parent.get_text()
                    tier_match = re.search(r'(T\d)', text)
                    if tier_match:
                        tier = tier_match.group(1)
                
                if augments:
                    combo = AugmentCombo(
                        rank=idx,
                        augments=augments,
                        tier=tier
                    )
                    combos.append(combo)
        
        return combos
    
    def parse_champion_info(self, soup: BeautifulSoup) -> Dict:
        """
        解析英雄基本信息
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            英雄信息字典
        """
        info = {
            'champion_id': 0,
            'champion_name': '',
            'version': '16.6',
            'tier': 'T1',
            'win_rate': 0.0,
            'pick_rate': 0.0
        }
        
        # 获取英雄名称
        name_heading = soup.find('h1')
        if name_heading:
            info['champion_name'] = name_heading.get_text(strip=True)
        
        # 获取版本
        version_elem = soup.find(string=re.compile(r'版本:\s*\d+\.\d+'))
        if version_elem:
            match = re.search(r'(\d+\.\d+)', version_elem)
            if match:
                info['version'] = match.group(1)
        
        # 获取层级
        tier_elem = soup.find(string=re.compile(r'^T[1-5]$'))
        if tier_elem:
            info['tier'] = tier_elem.get_text(strip=True)
        
        # 获取胜率和选取率
        text = soup.get_text()
        win_match = re.search(r'胜率\s*\n?\s*(\d+\.?\d*)%', text)
        if win_match:
            info['win_rate'] = float(win_match.group(1))
        
        pick_match = re.search(r'选取率\s*\n?\s*(\d+\.?\d*)%', text)
        if pick_match:
            info['pick_rate'] = float(pick_match.group(1))
        
        # 从URL获取英雄ID
        canonical = soup.find('link', rel='canonical')
        if canonical:
            href = canonical.get('href', '')
            match = re.search(r'/champion-stats/(\d+)', href)
            if match:
                info['champion_id'] = int(match.group(1))
        
        return info
    
    def scrape_champion(self, champion_id: int, lang: str = "zh-CN") -> Optional[ChampionData]:
        """
        抓取单个英雄的完整数据
        
        Args:
            champion_id: 英雄ID
            lang: 语言代码
            
        Returns:
            ChampionData对象或None
        """
        print(f"正在抓取英雄ID: {champion_id}...")
        
        html = self.fetch_champion_page(champion_id, lang)
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # 解析英雄信息
        info = self.parse_champion_info(soup)
        info['champion_id'] = champion_id  # 确保ID正确
        
        # 解析各项数据
        augments = self.parse_augments(soup)
        augment_combos = self.parse_augment_combos(soup)
        build_configs = self.parse_build_configs(soup)
        
        champion_data = ChampionData(
            champion_id=info['champion_id'],
            champion_name=info['champion_name'],
            version=info['version'],
            tier=info['tier'],
            win_rate=info['win_rate'],
            pick_rate=info['pick_rate'],
            augments=augments,
            augment_combos=augment_combos,
            build_configs=build_configs
        )
        
        return champion_data
    
    def scrape_multiple_champions(self, champion_ids: List[int], lang: str = "zh-CN") -> List[ChampionData]:
        """
        批量抓取多个英雄的数据
        
        Args:
            champion_ids: 英雄ID列表
            lang: 语言代码
            
        Returns:
            ChampionData列表
        """
        results = []
        for champion_id in champion_ids:
            data = self.scrape_champion(champion_id, lang)
            if data:
                results.append(data)
        return results


def save_to_json(data: ChampionData, filepath: str):
    """保存数据到JSON文件"""
    # 将dataclass转换为字典
    def dataclass_to_dict(obj):
        if isinstance(obj, list):
            return [dataclass_to_dict(item) for item in obj]
        elif hasattr(obj, '__dataclass_fields__'):
            return {k: dataclass_to_dict(v) for k, v in asdict(obj).items()}
        else:
            return obj
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(dataclass_to_dict(data), f, ensure_ascii=False, indent=2)
    print(f"数据已保存到: {filepath}")


def print_champion_summary(data: ChampionData):
    """打印英雄数据摘要"""
    print("\n" + "="*60)
    print(f"英雄: {data.champion_name} (ID: {data.champion_id})")
    print(f"版本: {data.version} | 层级: {data.tier}")
    print(f"胜率: {data.win_rate}% | 选取率: {data.pick_rate}%")
    print("="*60)
    
    print("\n【推荐海克斯】(前10个)")
    for i, aug in enumerate(data.augments[:10], 1):
        print(f"  {i}. {aug.name} (ID: {aug.id}) - {aug.tier} - 胜率: {aug.win_rate}%")
    
    print("\n【情境装备】")
    for config in data.build_configs:
        print(f"\n  配置类型: {config.build_type}")
        print(f"  情境装备:")
        for item in config.situational_items:
            print(f"    - {item.name} (ID: {item.id})")
    
    print("\n【推荐海克斯组合】(前5个)")
    for i, combo in enumerate(data.augment_combos[:5], 1):
        aug_names = ", ".join([aug.name for aug in combo.augments])
        print(f"  {i}. {aug_names} - {combo.tier}")


# 使用示例
if __name__ == "__main__":
    scraper = HextechScraper()
    
    # 抓取单个英雄（莉莉娅，ID: 876）
    champion_id = 876
    data = scraper.scrape_champion(champion_id)
    
    if data:
        # 打印摘要
        print_champion_summary(data)
        
        # 保存到JSON
        save_to_json(data, f"champion_{champion_id}_data.json")
    else:
        print(f"抓取英雄 {champion_id} 失败")
    
    # 批量抓取示例
    # champion_ids = [876, 63, 904, 147]  # 莉莉娅、布兰德、亚恒、萨勒芬妮
    # results = scraper.scrape_multiple_champions(champion_ids)
    # for result in results:
    #     save_to_json(result, f"champion_{result.champion_id}_data.json")
))
        
        for idx, marker in enumerate(combo_markers, 1):
            augments = []
            tier = "T1"
            
            parent = marker.find_parent()
            if parent:
                # 查找该组合中的海克斯链接
                augment_links = parent.find_all('a', href=re.compile(r'/augments/\d+'))
                for link in augment_links:
                    href = link.get('href', '')
                    match = re.search(r'/augments/(\d+)', href)
                    if match:
                        augment_id = int(match.group(1))
                        name = link.get('title', '') or link.get_text(strip=True)
                        # 去掉#号
                        name = re.sub(r'^#', '', name)
                        
                        img = link.find('img')
                        icon_url = ''
                        if img:
                            icon_url = img.get('src', '')
                            if icon_url and not icon_url.startswith('http'):
                                icon_url = urljoin(self.CDN_URL, icon_url)
                        
                        augment = Augment(
                            id=augment_id,
                            name=name,
                            tier="T1",
                            win_rate=0.0,
                            pick_rate=0.0,
                            icon_url=icon_url
                        )
                        augments.append(augment)
                
                # 提取层级
                text = parent.get_text()
                tier_match = re.search(r'(T[1-5])', text)
                if tier_match:
                    tier = tier_match.group(1)
            
            if augments:
                combo = AugmentCombo(
                    rank=idx,
                    augments=augments,
                    tier=tier
                )
                combos.append(combo)
        
        return combos
    
    def parse_champion_info(self, soup: BeautifulSoup) -> Dict:
        """
        解析英雄基本信息
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            英雄信息字典
        """
        info = {
            'champion_id': 0,
            'champion_name': '',
            'version': '16.6',
            'tier': 'T1',
            'win_rate': 0.0,
            'pick_rate': 0.0
        }
        
        # 获取英雄名称
        name_heading = soup.find('h1')
        if name_heading:
            info['champion_name'] = name_heading.get_text(strip=True)
        
        # 获取版本
        version_elem = soup.find(string=re.compile(r'版本:\s*\d+\.\d+'))
        if version_elem:
            match = re.search(r'(\d+\.\d+)', version_elem)
            if match:
                info['version'] = match.group(1)
        
        # 获取层级
        tier_elem = soup.find(string=re.compile(r'^T[1-5]$'))
        if tier_elem:
            info['tier'] = tier_elem.get_text(strip=True)
        
        # 获取胜率和选取率
        text = soup.get_text()
        win_match = re.search(r'胜率\s*\n?\s*(\d+\.?\d*)%', text)
        if win_match:
            info['win_rate'] = float(win_match.group(1))
        
        pick_match = re.search(r'选取率\s*\n?\s*(\d+\.?\d*)%', text)
        if pick_match:
            info['pick_rate'] = float(pick_match.group(1))
        
        # 从URL获取英雄ID
        canonical = soup.find('link', rel='canonical')
        if canonical:
            href = canonical.get('href', '')
            match = re.search(r'/champion-stats/(\d+)', href)
            if match:
                info['champion_id'] = int(match.group(1))
        
        return info
    
    def scrape_champion(self, champion_id: int, lang: str = "zh-CN") -> Optional[ChampionData]:
        """
        抓取单个英雄的完整数据
        
        Args:
            champion_id: 英雄ID
            lang: 语言代码
            
        Returns:
            ChampionData对象或None
        """
        print(f"正在抓取英雄ID: {champion_id}...")
        
        html = self.fetch_champion_page(champion_id, lang)
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # 解析英雄信息
        info = self.parse_champion_info(soup)
        info['champion_id'] = champion_id  # 确保ID正确
        
        # 解析各项数据
        augments = self.parse_augments(soup)
        augment_combos = self.parse_augment_combos(soup)
        build_configs = self.parse_build_configs(soup)
        
        champion_data = ChampionData(
            champion_id=info['champion_id'],
            champion_name=info['champion_name'],
            version=info['version'],
            tier=info['tier'],
            win_rate=info['win_rate'],
            pick_rate=info['pick_rate'],
            augments=augments,
            augment_combos=augment_combos,
            build_configs=build_configs
        )
        
        return champion_data
    
    def scrape_multiple_champions(self, champion_ids: List[int], lang: str = "zh-CN") -> List[ChampionData]:
        """
        批量抓取多个英雄的数据
        
        Args:
            champion_ids: 英雄ID列表
            lang: 语言代码
            
        Returns:
            ChampionData列表
        """
        results = []
        for champion_id in champion_ids:
            data = self.scrape_champion(champion_id, lang)
            if data:
                results.append(data)
        return results


def save_to_json(data: ChampionData, filepath: str):
    """保存数据到JSON文件"""
    # 将dataclass转换为字典
    def dataclass_to_dict(obj):
        if isinstance(obj, list):
            return [dataclass_to_dict(item) for item in obj]
        elif hasattr(obj, '__dataclass_fields__'):
            return {k: dataclass_to_dict(v) for k, v in asdict(obj).items()}
        else:
            return obj
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(dataclass_to_dict(data), f, ensure_ascii=False, indent=2)
    print(f"数据已保存到: {filepath}")


def print_champion_summary(data: ChampionData):
    """打印英雄数据摘要"""
    print("\n" + "="*60)
    print(f"英雄: {data.champion_name} (ID: {data.champion_id})")
    print(f"版本: {data.version} | 层级: {data.tier}")
    print(f"胜率: {data.win_rate}% | 选取率: {data.pick_rate}%")
    print("="*60)
    
    print("\n【推荐海克斯】(前10个)")
    for i, aug in enumerate(data.augments[:10], 1):
        print(f"  {i}. {aug.name} (ID: {aug.id}) - {aug.tier} - 胜率: {aug.win_rate}%")
    
    print("\n【情境装备】")
    for config in data.build_configs:
        print(f"\n  配置类型: {config.build_type}")
        print(f"  情境装备:")
        for item in config.situational_items:
            print(f"    - {item.name} (ID: {item.id})")
    
    print("\n【推荐海克斯组合】(前5个)")
    for i, combo in enumerate(data.augment_combos[:5], 1):
        aug_names = ", ".join([aug.name for aug in combo.augments])
        print(f"  {i}. {aug_names} - {combo.tier}")


# 使用示例
if __name__ == "__main__":
    scraper = HextechScraper()
    
    # 抓取单个英雄（莉莉娅，ID: 876）
    champion_id = 876
    data = scraper.scrape_champion(champion_id)
    
    if data:
        # 打印摘要
        print_champion_summary(data)
        
        # 保存到JSON
        save_to_json(data, f"champion_{champion_id}_data.json")
    else:
        print(f"抓取英雄 {champion_id} 失败")
    
    # 批量抓取示例
    # champion_ids = [876, 63, 904, 147]  # 莉莉娅、布兰德、亚恒、萨勒芬妮
    # results = scraper.scrape_multiple_champions(champion_ids)
    # for result in results:
    #     save_to_json(result, f"champion_{result.champion_id}_data.json")
))
        
        for idx, marker in enumerate(build_markers, 1):
            items = []
            win_rate = 0.0
            pick_rate = 0.0
            
            # 获取该方案的元素
            parent = marker.find_parent()
            if parent:
                # 查找装备图片
                imgs = parent.find_all('img')
                for img in imgs:
                    src = img.get('src', '')
                    match = re.search(r'/item-icons/(\d+)\.png', src)
                    if match:
                        item_id = int(match.group(1))
                        item_name = img.get('alt', '') or self._get_item_name(item_id)
                        item = Item(
                            id=item_id,
                            name=item_name,
                            icon_url=src if src.startswith('http') else urljoin(self.CDN_URL, src)
                        )
                        items.append(item)
                
                # 查找胜率和选取率文本
                text = parent.get_text()
                win_match = re.search(r'胜率[:\s]+(\d+\.?\d*)%', text)
                if win_match:
                    win_rate = float(win_match.group(1))
                pick_match = re.search(r'选取率[:\s]+(\d+\.?\d*)%', text)
                if pick_match:
                    pick_rate = float(pick_match.group(1))
            
            if items:
                build = CoreBuild(
                    rank=idx,
                    items=items,
                    win_rate=win_rate,
                    pick_rate=pick_rate
                )
                builds.append(build)
        
        return builds
    
    def parse_starter_items(self, soup: BeautifulSoup) -> List[Item]:
        """
        解析出门装
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            出门装列表
        """
        items = []
        
        # 查找"出门装"标题
        starter_heading = soup.find(string=re.compile(r'出门装'))
        if not starter_heading:
            return items
        
        # 获取出门装区域
        starter_section = starter_heading.find_parent('h3') or starter_heading.find_parent()
        if starter_section:
            imgs = starter_section.find_all('img')
            for img in imgs:
                src = img.get('src', '')
                match = re.search(r'/item-icons/(\d+)\.png', src)
                if match:
                    item_id = int(match.group(1))
                    item = Item(
                        id=item_id,
                        name=self._get_item_name(item_id),
                        icon_url=src
                    )
                    items.append(item)
        
        return items
    
    def parse_build_configs(self, soup: BeautifulSoup) -> List[BuildConfig]:
        """
        解析所有装备配置
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            装备配置列表
        """
        configs = []
        
        # 查找"装备配置"区域
        build_heading = soup.find(string=re.compile(r'装备配置'))
        if not build_heading:
            return configs
        
        # 获取版本号
        version = "16.6"  # 默认值
        version_match = re.search(r'(\d+\.\d+)', build_heading.get_text() if hasattr(build_heading, 'get_text') else str(build_heading))
        if version_match:
            version = version_match.group(1)
        
        # 查找所有出装类型（AP, APBruiser等）
        build_types = soup.find_all(string=re.compile(r'^(AP|AD|Tank|Support|APBruiser|ADAssassin)$'))
        
        for build_type_elem in build_types:
            build_type = build_type_elem.get_text(strip=True)
            
            # 获取该类型的胜率
            win_rate = 0.0
            parent = build_type_elem.find_parent()
            if parent:
                text = parent.get_text()
                win_match = re.search(r'(\d+\.?\d*)%', text)
                if win_match:
                    win_rate = float(win_match.group(1))
            
            # 解析核心出装和情境装备
            core_builds = self.parse_core_builds(soup)
            situational_items = self.parse_situational_items(soup)
            starter_items = self.parse_starter_items(soup)
            
            config = BuildConfig(
                build_type=build_type,
                win_rate=win_rate,
                core_builds=core_builds,
                situational_items=situational_items,
                starter_items=starter_items
            )
            configs.append(config)
        
        # 如果没有找到具体类型，创建一个默认配置
        if not configs:
            core_builds = self.parse_core_builds(soup)
            situational_items = self.parse_situational_items(soup)
            starter_items = self.parse_starter_items(soup)
            
            if core_builds or situational_items:
                config = BuildConfig(
                    build_type="Default",
                    win_rate=0.0,
                    core_builds=core_builds,
                    situational_items=situational_items,
                    starter_items=starter_items
                )
                configs.append(config)
        
        return configs
    
    def parse_augment_combos(self, soup: BeautifulSoup) -> List[AugmentCombo]:
        """
        解析推荐海克斯组合
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            海克斯组合列表
        """
        combos = []
        
        # 查找"推荐海克斯组合"标题
        combo_heading = soup.find(string=re.compile(r'推荐海克斯组合'))
        if not combo_heading:
            return combos
        
        # 获取组合区域
        combo_section = combo_heading.find_parent('h3') or combo_heading.find_parent()
        if combo_section:
            # 查找所有组合（通常以#1, #2等标识）
            combo_divs = soup.find_all(string=re.compile(r'^#组合'))
            
            for idx, combo_div in enumerate(combo_divs, 1):
                augments = []
                tier = "T1"
                
                parent = combo_div.find_parent()
                if parent:
                    # 查找该组合中的海克斯链接
                    augment_links = parent.find_all('a', href=re.compile(r'/augments/\d+'))
                    for link in augment_links:
                        href = link.get('href', '')
                        match = re.search(r'/augments/(\d+)', href)
                        if match:
                            augment_id = int(match.group(1))
                            name = link.get('title', '') or link.get_text(strip=True)
                            
                            img = link.find('img')
                            icon_url = img.get('src', '') if img else ''
                            
                            augment = Augment(
                                id=augment_id,
                                name=name,
                                tier="T1",
                                win_rate=0.0,
                                pick_rate=0.0,
                                icon_url=icon_url
                            )
                            augments.append(augment)
                    
                    # 提取层级
                    text = parent.get_text()
                    tier_match = re.search(r'(T\d)', text)
                    if tier_match:
                        tier = tier_match.group(1)
                
                if augments:
                    combo = AugmentCombo(
                        rank=idx,
                        augments=augments,
                        tier=tier
                    )
                    combos.append(combo)
        
        return combos
    
    def parse_champion_info(self, soup: BeautifulSoup) -> Dict:
        """
        解析英雄基本信息
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            英雄信息字典
        """
        info = {
            'champion_id': 0,
            'champion_name': '',
            'version': '16.6',
            'tier': 'T1',
            'win_rate': 0.0,
            'pick_rate': 0.0
        }
        
        # 获取英雄名称
        name_heading = soup.find('h1')
        if name_heading:
            info['champion_name'] = name_heading.get_text(strip=True)
        
        # 获取版本
        version_elem = soup.find(string=re.compile(r'版本:\s*\d+\.\d+'))
        if version_elem:
            match = re.search(r'(\d+\.\d+)', version_elem)
            if match:
                info['version'] = match.group(1)
        
        # 获取层级
        tier_elem = soup.find(string=re.compile(r'^T[1-5]$'))
        if tier_elem:
            info['tier'] = tier_elem.get_text(strip=True)
        
        # 获取胜率和选取率
        text = soup.get_text()
        win_match = re.search(r'胜率\s*\n?\s*(\d+\.?\d*)%', text)
        if win_match:
            info['win_rate'] = float(win_match.group(1))
        
        pick_match = re.search(r'选取率\s*\n?\s*(\d+\.?\d*)%', text)
        if pick_match:
            info['pick_rate'] = float(pick_match.group(1))
        
        # 从URL获取英雄ID
        canonical = soup.find('link', rel='canonical')
        if canonical:
            href = canonical.get('href', '')
            match = re.search(r'/champion-stats/(\d+)', href)
            if match:
                info['champion_id'] = int(match.group(1))
        
        return info
    
    def scrape_champion(self, champion_id: int, lang: str = "zh-CN") -> Optional[ChampionData]:
        """
        抓取单个英雄的完整数据
        
        Args:
            champion_id: 英雄ID
            lang: 语言代码
            
        Returns:
            ChampionData对象或None
        """
        print(f"正在抓取英雄ID: {champion_id}...")
        
        html = self.fetch_champion_page(champion_id, lang)
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # 解析英雄信息
        info = self.parse_champion_info(soup)
        info['champion_id'] = champion_id  # 确保ID正确
        
        # 解析各项数据
        augments = self.parse_augments(soup)
        augment_combos = self.parse_augment_combos(soup)
        build_configs = self.parse_build_configs(soup)
        
        champion_data = ChampionData(
            champion_id=info['champion_id'],
            champion_name=info['champion_name'],
            version=info['version'],
            tier=info['tier'],
            win_rate=info['win_rate'],
            pick_rate=info['pick_rate'],
            augments=augments,
            augment_combos=augment_combos,
            build_configs=build_configs
        )
        
        return champion_data
    
    def scrape_multiple_champions(self, champion_ids: List[int], lang: str = "zh-CN") -> List[ChampionData]:
        """
        批量抓取多个英雄的数据
        
        Args:
            champion_ids: 英雄ID列表
            lang: 语言代码
            
        Returns:
            ChampionData列表
        """
        results = []
        for champion_id in champion_ids:
            data = self.scrape_champion(champion_id, lang)
            if data:
                results.append(data)
        return results


def save_to_json(data: ChampionData, filepath: str):
    """保存数据到JSON文件"""
    # 将dataclass转换为字典
    def dataclass_to_dict(obj):
        if isinstance(obj, list):
            return [dataclass_to_dict(item) for item in obj]
        elif hasattr(obj, '__dataclass_fields__'):
            return {k: dataclass_to_dict(v) for k, v in asdict(obj).items()}
        else:
            return obj
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(dataclass_to_dict(data), f, ensure_ascii=False, indent=2)
    print(f"数据已保存到: {filepath}")


def print_champion_summary(data: ChampionData):
    """打印英雄数据摘要"""
    print("\n" + "="*60)
    print(f"英雄: {data.champion_name} (ID: {data.champion_id})")
    print(f"版本: {data.version} | 层级: {data.tier}")
    print(f"胜率: {data.win_rate}% | 选取率: {data.pick_rate}%")
    print("="*60)
    
    print("\n【推荐海克斯】(前10个)")
    for i, aug in enumerate(data.augments[:10], 1):
        print(f"  {i}. {aug.name} (ID: {aug.id}) - {aug.tier} - 胜率: {aug.win_rate}%")
    
    print("\n【情境装备】")
    for config in data.build_configs:
        print(f"\n  配置类型: {config.build_type}")
        print(f"  情境装备:")
        for item in config.situational_items:
            print(f"    - {item.name} (ID: {item.id})")
    
    print("\n【推荐海克斯组合】(前5个)")
    for i, combo in enumerate(data.augment_combos[:5], 1):
        aug_names = ", ".join([aug.name for aug in combo.augments])
        print(f"  {i}. {aug_names} - {combo.tier}")


# 使用示例
if __name__ == "__main__":
    scraper = HextechScraper()
    
    # 抓取单个英雄（莉莉娅，ID: 876）
    champion_id = 876
    data = scraper.scrape_champion(champion_id)
    
    if data:
        # 打印摘要
        print_champion_summary(data)
        
        # 保存到JSON
        save_to_json(data, f"champion_{champion_id}_data.json")
    else:
        print(f"抓取英雄 {champion_id} 失败")
    
    # 批量抓取示例
    # champion_ids = [876, 63, 904, 147]  # 莉莉娅、布兰德、亚恒、萨勒芬妮
    # results = scraper.scrape_multiple_champions(champion_ids)
    # for result in results:
    #     save_to_json(result, f"champion_{result.champion_id}_data.json")
