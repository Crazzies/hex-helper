/**
 * 爬虫服务 (Scraper Service)
 * 核心功能：
 * 1. 静默抓取全量英雄基础胜率。
 * 2. 在线抓取特定英雄的海克斯与出装建议。
 * 3. 基于本地映射表进行海克斯品阶校准。
 */
const { app, BrowserWindow } = require('electron');
const { log } = require('../utils/logger');
const fs = require('fs');
const path = require('path');

class ScraperService {
    constructor() {
        this.tierMap = {};
        this.loadTierMap();
    }

    /**
     * 加载海克斯品阶映射库
     * 作用：确保棱彩/金色/银色分类 100% 准确，不依赖网页不可靠的动态布局。
     */
    loadTierMap() {
        try {
            this.tierMap = require('../augments_tier_map.json');
            log('Scraper', `Tier map loaded via require: ${Object.keys(this.tierMap).length} items.`);
        } catch (e) {
            try {
                // 备份加载路径 (针对打包后的不同资源结构)
                const backupPath = path.join(app.getAppPath(), 'src/main/augments_tier_map.json');
                if (fs.existsSync(backupPath)) this.tierMap = JSON.parse(fs.readFileSync(backupPath, 'utf8'));
            } catch(e2) {}
        }
    }

    /**
     * 全量数据同步：从统计首页抓取所有英雄的胜率列表
     */
    async scrapeAllHeroWinRates() {
        log('Scraper', 'Starting full hero winrate sync...');
        const win = new BrowserWindow({ show: false, webPreferences: { offscreen: true } });
        try {
            await win.loadURL('https://hextech.dtodo.cn/zh-CN/champion-stats');
            await new Promise(r => setTimeout(r, 6000));

            const data = await win.webContents.executeJavaScript(`
                (() => {
                    const heroes = {};
                    const rows = document.querySelectorAll('tr');
                    rows.forEach(row => {
                        const link = row.querySelector('a[href*="/champion-stats/"]');
                        if (!link) return;
                        
                        const idMatch = link.href.match(/champion-stats\\/(\\d+)/);
                        if (!idMatch) return;
                        const id = idMatch[1];

                        const img = link.querySelector('img');
                        const name = (img?.alt || link.title || link.innerText || "").trim();
                        
                        const wrMatch = row.innerText.match(/(\\d+\\.?\\d*)%/);
                        const winRate = wrMatch ? wrMatch[0] : "??%";

                        if (name) { heroes[id] = { name, winRate }; }
                    });
                    return heroes;
                })()
            `);

            if (Object.keys(data).length > 50) return data;
        } catch (e) {
            log('Scraper', `Global sync failed: ${e.message}`);
        } finally {
            if (!win.isDestroyed()) win.destroy();
        }
        return null;
    }

    /**
     * 核心业务：抓取单个英雄的深度攻略数据
     * 包含：海克斯去重、胜率识别、品阶查表、情境装备切片。
     */
    async scrapeHextechData(championId) {
        log('Scraper', `[Hextech] Scrape Target ID ${championId}...`);
        const win = new BrowserWindow({ show: false, webPreferences: { nodeIntegration: false, contextIsolation: true } });
        try {
            await win.loadURL(`https://hextech.dtodo.cn/zh-CN/champion-stats/${championId}`);
            await new Promise(r => setTimeout(r, 4000)); // 等待初始渲染

            const data = await win.webContents.executeJavaScript(`
                (async function() {
                    // 1. 模拟点击“显示全部”以获取完整 177+ 条海克斯
                    const btn = Array.from(document.querySelectorAll('button, span, div'))
                        .find(b => /显示全部|全部.*条|加载更多/i.test(b.innerText));
                    if (btn) btn.click();
                    for(let i=0; i<8; i++) {
                        await new Promise(r => setTimeout(r, 1000));
                        if (document.querySelectorAll('a[href*="/augments/"]').length > 50) break;
                    }

                    // 2. 提取海克斯原始数据
                    const augments = [];
                    const seen = new Set(); 
                    document.querySelectorAll('a[href*="/augments/"]').forEach(link => {
                        if (link.href.includes('/augment-combos/')) return;
                        const img = link.querySelector('img');
                        // 名称清洗：删除“海克斯强化”及“#”干扰字符
                        let name = (img?.alt || link.title || link.innerText || "").replace(/#|海克斯强化/g, '').trim();
                        if (!name || seen.has(name)) return;
                        seen.add(name);

                        const container = link.closest('div[class*="item"], div[class*="row"], tr, li') || link.parentElement;
                        const text = container ? container.innerText : "";
                        // 胜率识别：优先取“胜率”字样附近的百分比，避免误取“选取率”
                        let winRate = "??%";
                        const wrMatch = text.match(/(?:胜率|WR).*?(\\d+\\.?\\d*)%/i) || text.match(/(\\d+\\.?\\d*)%/);
                        if (wrMatch) winRate = wrMatch[1] + "%";

                        augments.push({ name, winRate });
                    });

                    // 3. 提取情境装备
                    let situationalItems = [];
                    const headers = Array.from(document.querySelectorAll('h1, h2, h3, h4, span, div, strong'));
                    const sitHeader = headers.find(el => el.innerText.includes('情境装备') || el.innerText.includes('装备配置'));
                    if (sitHeader) {
                        let zone = sitHeader.parentElement;
                        for(let i=0; i<8; i++) {
                            if (!zone) break;
                            const imgs = zone.querySelectorAll('img[src*="item-icons"]');
                            if (imgs.length > 5) {
                                imgs.forEach(img => {
                                    let itemName = img.alt || img.title || img.getAttribute('aria-label') || img.closest('a')?.title;
                                    if(itemName && itemName !== "undefined") situationalItems.push(itemName.trim());
                                });
                                break;
                            }
                            zone = zone.nextElementSibling || zone.parentElement;
                        }
                    }
                    // 仅保留网页排布中的第 10 到第 21 个装备（这是真正的情境装备区）
                    return { championName: document.querySelector('h1')?.innerText || 'Unknown', augments, situationalItems: situationalItems.slice(9, 21) };
                })();
            `);

            if (data && data.augments) {
                const result = { prismatic: [], gold: [], silver: [] };
                const classifiedNames = new Set(); 

                data.augments.forEach(a => {
                    if (classifiedNames.has(a.name)) return;
                    if (!a.winRate || a.winRate === "??%") return; // 过滤乱码数据

                    // 分类逻辑：基于本地 TierMap 精准匹配
                    let tier = null;
                    if (this.tierMap[a.name]) tier = this.tierMap[a.name];
                    else {
                        // 模糊匹配：处理全角半角及微小文案差异
                        for (let key in this.tierMap) {
                            if (a.name.includes(key) || key.includes(a.name)) {
                                tier = this.tierMap[key];
                                break;
                            }
                        }
                    }

                    // 保底分类猜想
                    if (!tier) {
                        if (a.name.includes('棱彩')) tier = 'prismatic';
                        else if (a.name.includes('黄金')) tier = 'gold';
                        else tier = 'silver'; 
                    }

                    if (result[tier]) {
                        result[tier].push(a);
                        classifiedNames.add(a.name);
                    }
                });

                // 按胜率从高到低排序
                const sortFn = (a, b) => parseFloat(b.winRate) - parseFloat(a.winRate);
                return {
                    championName: data.championName,
                    prismatic: result.prismatic.sort(sortFn),
                    gold: result.gold.sort(sortFn),
                    silver: result.silver.sort(sortFn),
                    situationalItems: data.situationalItems
                };
            }
        } catch (e) {
            log('Scraper', `[Hextech] DOM Error: ${e.message}`);
        } finally {
            if (!win.isDestroyed()) win.destroy();
        }
        return null;
    }

    /**
     * 辅助函数：递归寻找包含特定模式的数据节点
     */
    _findBuildInData(json) {
        const find = (obj) => {
            if (obj && obj.queue === "ARAM_MAYHEM" && obj.recommendedAugments) return obj;
            if (Array.isArray(obj)) { for (let item of obj) { const res = find(item); if (res) return res; } }
            else if (typeof obj === 'object' && obj !== null) { for (let k in obj) { const res = find(obj[k]); if (res) return res; } }
            return null;
        };
        return find(json);
    }
}
module.exports = new ScraperService();
