const axios = require('axios');
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

class DataFetcher {
    constructor() {
        this.cacheFile = path.join(__dirname, 'hex_data.json');
        this.baseUrl = 'https://hextech.dtodo.cn/zh-CN';
        this.heroes = {};
    }

    loadLocal() {
        if (fs.existsSync(this.cacheFile)) {
            try {
                const data = JSON.parse(fs.readFileSync(this.cacheFile, 'utf8'));
                this.heroes = data.heroes || {};
                return true;
            } catch(e) {}
        }
        return false;
    }

    async syncFromWeb() {
        try {
            console.log('[Scraper] Using PowerShell to bypass Cloudflare/403...');
            
            // 终极武器：使用 PowerShell 模拟真实浏览器请求
            const psCmd = `powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $r = Invoke-WebRequest -Uri '${this.baseUrl}' -UserAgent 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36' -UseBasicParsing; $r.Content"`;
            
            const html = execSync(psCmd, { maxBuffer: 1024 * 1024 * 5 }).toString('utf8');
            const match = html.match(/<script id="__NEXT_DATA__" type="application\/json">([\s\S]*?)<\/script>/);
            
            if (match && match[1]) {
                const fullData = JSON.parse(match[1]);
                const list = fullData.props?.pageProps?.championStats || [];
                
                if (Array.isArray(list) && list.length > 0) {
                    list.forEach(item => {
                        if (item.championId) {
                            const wr = item.winRate || 0;
                            this.heroes[item.championId.toString()] = {
                                name: item.name,
                                winRate: (wr * 100).toFixed(1) + '%'
                            };
                        }
                    });

                    fs.writeFileSync(this.cacheFile, JSON.stringify({ heroes: this.heroes }, null, 2));
                    console.log(`[Scraper] Success! Synchronized ${Object.keys(this.heroes).length} heroes.`);
                    return true;
                }
            }
            console.warn('[Scraper] Data structure changed or empty response.');
        } catch (e) {
            console.error('[Scraper] PS Command failed:', e.message);
        }
        return false;
    }

    async getHeroBuild(heroId) {
        try {
            const url = `${this.baseUrl}/champion-stats/${heroId}`;
            const psCmd = `powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $r = Invoke-WebRequest -Uri '${url}' -UserAgent 'Mozilla/5.0' -UseBasicParsing; $r.Content"`;
            const html = execSync(psCmd, { maxBuffer: 1024 * 1024 * 2 }).toString('utf8');
            const match = html.match(/<script id="__NEXT_DATA__" type="application\/json">([\s\S]*?)<\/script>/);
            
            if (match && match[1]) {
                const data = JSON.parse(match[1]);
                const stats = data.props?.pageProps?.championStats;
                return {
                    items: stats?.recommendedItems?.map(i => i.name) || [],
                    hextech: stats?.recommendedAugments?.map(a => a.name) || []
                };
            }
        } catch (e) {}
        return { items: [], hextech: [] };
    }
}

module.exports = new DataFetcher();
