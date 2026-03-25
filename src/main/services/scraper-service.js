const { app, BrowserWindow } = require('electron');
const { log } = require('../utils/logger');
const fs = require('fs');
const path = require('path');

class ScraperService {
    constructor() {
        this.tierMap = {};
        this.loadTierMap();
    }

    loadTierMap() {
        try {
            this.tierMap = require('../augments_tier_map.json');
            log('Scraper', `Tier map loaded via require: ${Object.keys(this.tierMap).length} items.`);
        } catch (e) {
            try {
                const backupPath = path.join(app.getAppPath(), 'src/main/augments_tier_map.json');
                if (fs.existsSync(backupPath)) this.tierMap = JSON.parse(fs.readFileSync(backupPath, 'utf8'));
            } catch(e2) {}
        }
    }

    // --- 新增：抓取所有英雄的基础胜率列表 (解决数据滞后问题) ---
    async scrapeAllHeroWinRates() {
        log('Scraper', 'Starting full hero winrate sync...');
        const win = new BrowserWindow({ show: false, webPreferences: { offscreen: true } });
        try {
            await win.loadURL('https://hextech.dtodo.cn/zh-CN/champion-stats');
            await new Promise(r => setTimeout(r, 6000)); // 等待全量列表加载

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
                        
                        // 寻找胜率文本
                        const wrMatch = row.innerText.match(/(\\d+\\.?\\d*)%/);
                        const winRate = wrMatch ? wrMatch[0] : "??%";

                        if (name) {
                            heroes[id] = { name, winRate };
                        }
                    });
                    return heroes;
                })()
            `);

            if (Object.keys(data).length > 50) {
                log('Scraper', `Successfully scraped ${Object.keys(data).length} heroes.`);
                return data;
            }
        } catch (e) {
            log('Scraper', `Global sync failed: ${e.message}`);
        } finally {
            if (!win.isDestroyed()) win.destroy();
        }
        return null;
    }

    async scrapeHeroDetailFromBlitz(championId) {
        log('Scraper', `Nuclear-Level Packet Sniffing for hero ID ${championId}...`);
        const win = new BrowserWindow({ show: false, webPreferences: { offscreen: true } });
        let capturedData = null;
        const { debugger: dbg } = win.webContents;
        try {
            dbg.attach('1.3');
            dbg.sendCommand('Network.enable');
            dbg.on('message', async (event, method, params) => {
                if (method === 'Network.responseReceived') {
                    const { url } = params.response;
                    if (url.includes('graphql') || url.includes('stats')) {
                        try {
                            const body = await dbg.sendCommand('Network.getResponseBody', { requestId: params.requestId });
                            const json = JSON.parse(body.body);
                            const buildData = this._findBuildInData(json);
                            if (buildData) capturedData = buildData;
                        } catch (e) {}
                    }
                }
            });
            await win.loadURL(`https://blitz.gg/lol/champions/katarina/aram-mayhem`);
            for (let i = 0; i < 20; i++) {
                if (capturedData) break;
                await new Promise(r => setTimeout(r, 1000));
            }
            if (capturedData) {
                const augments = capturedData.recommendedAugments || [];
                const formatHex = (t) => augments.filter(a => a.tier === t)
                    .map(a => ({ name: a.name, winRate: (a.winRate * 100).toFixed(2) + '%' }))
                    .sort((a,b) => parseFloat(b.winRate) - parseFloat(a.winRate));
                return {
                    situationalItems: (capturedData.items?.situationalItems || []).map(i => i.name || i.id.toString()).slice(0, 12),
                    prismatic: formatHex('PRISMATIC'), gold: formatHex('GOLD'), silver: formatHex('SILVER')
                };
            }
        } catch (e) {
            log('Scraper', `Sniffing failed: ${e.message}`);
        } finally {
            if (!win.isDestroyed()) win.destroy();
        }
        return null;
    }

    async scrapeHextechData(championId) {
        log('Scraper', `[Hextech] Target: Hero ID ${championId}, Precision Map Mode...`);
        const win = new BrowserWindow({ show: false, webPreferences: { nodeIntegration: false, contextIsolation: true } });
        try {
            await win.loadURL(`https://hextech.dtodo.cn/zh-CN/champion-stats/${championId}`);
            await new Promise(r => setTimeout(r, 4000));
            const data = await win.webContents.executeJavaScript(`
                (async function() {
                    const btn = Array.from(document.querySelectorAll('button, span, div'))
                        .find(b => /显示全部|全部.*条|加载更多/i.test(b.innerText));
                    if (btn) btn.click();
                    for(let i=0; i<8; i++) {
                        await new Promise(r => setTimeout(r, 1000));
                        if (document.querySelectorAll('a[href*="/augments/"]').length > 50) break;
                    }

                    const augments = [];
                    const seen = new Set(); 

                    document.querySelectorAll('a[href*="/augments/"]').forEach(link => {
                        if (link.href.includes('/augment-combos/')) return;
                        const img = link.querySelector('img');
                        let name = (img?.alt || link.title || link.innerText || "").replace(/#|海克斯强化/g, '').trim();
                        if (!name || seen.has(name)) return;
                        seen.add(name);

                        const container = link.closest('div[class*="item"], div[class*="row"], tr, li') || link.parentElement;
                        const text = container ? container.innerText : "";
                        let winRate = "??%";
                        const wrMatch = text.match(/(?:胜率|WR).*?(\\d+\\.?\\d*)%/i) || text.match(/(\\d+\\.?\\d*)%/);
                        if (wrMatch) winRate = wrMatch[1] + "%";

                        augments.push({ name, winRate });
                    });

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
                    return { championName: document.querySelector('h1')?.innerText || 'Unknown', augments, situationalItems: situationalItems.slice(9, 21) };
                })();
            `);

            if (data && data.augments) {
                const result = { prismatic: [], gold: [], silver: [] };
                const classifiedNames = new Set(); 

                data.augments.forEach(a => {
                    if (classifiedNames.has(a.name)) return;
                    if (!a.winRate || a.winRate === "??%") return;

                    let tier = null;
                    if (this.tierMap[a.name]) {
                        tier = this.tierMap[a.name];
                    } else {
                        for (let key in this.tierMap) {
                            if (a.name.includes(key) || key.includes(a.name)) {
                                tier = this.tierMap[key];
                                break;
                            }
                        }
                    }

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
