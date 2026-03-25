const { app } = require('electron');
const fs = require('fs');
const path = require('path');
const { log } = require('../utils/logger');

class DataService {
    constructor() {
        this.winRates = {};
        this.userDataPath = app.getPath('userData');
        this.onlineDbPath = path.join(this.userDataPath, 'hex_data_online.json');
        this.buildsDir = path.join(this.userDataPath, 'cache', 'hero-builds');
        
        this.loadDatabase();
    }

    async loadDatabase() {
        try {
            // 1. 优先加载本地已更新的在线数据 (最鲜活)
            if (fs.existsSync(this.onlineDbPath)) {
                this.winRates = JSON.parse(fs.readFileSync(this.onlineDbPath, 'utf8'));
                log('Data', `Loaded updated winrates from AppData. Total: ${Object.keys(this.winRates).length}`);
            }

            // 2. 如果 AppData 里没有，则加载打包内置的保底数据
            if (Object.keys(this.winRates).length === 0) {
                try {
                    const data = require('../hex_data.json');
                    this.winRates = data.heroes || data;
                    log('Data', `Loaded internal winrates. Total: ${Object.keys(this.winRates).length}`);
                } catch (e) {
                    log('Data', `Internal load failed: ${e.message}`);
                }
            }
        } catch (e) {
            log('Data', `Fatal load error: ${e.message}`);
        }
    }

    // --- 自动更新机制 ---
    async syncWinRates(scraper) {
        // 如果数据量太少，或者距离上次更新太久 (目前设为每次冷启动尝试更新)
        log('Data', 'Triggering background data sync...');
        const newData = await scraper.scrapeAllHeroWinRates();
        if (newData && Object.keys(newData).length > 50) {
            this.winRates = newData;
            // 持久化到 AppData
            fs.writeFileSync(this.onlineDbPath, JSON.stringify(newData, null, 2));
            log('Data', 'Online winrates synced and saved.');
            return true;
        }
        return false;
    }

    isToday(filePath) {
        try {
            if (!fs.existsSync(filePath)) return false;
            const stats = fs.statSync(filePath);
            const today = new Date().toDateString();
            const fileDate = new Date(stats.mtime).toDateString();
            return today === fileDate;
        } catch (e) { return false; }
    }

    async getHeroBuild(heroId, scraper) {
        try {
            const baseInfo = this.winRates[heroId.toString()];
            const filePath = path.join(this.buildsDir, `${heroId}.json`);
            let detailData = null;

            if (this.isToday(filePath)) {
                try {
                    detailData = JSON.parse(fs.readFileSync(filePath, 'utf8'));
                } catch (e) {}
            }

            if (!detailData && scraper) {
                detailData = await scraper.scrapeHextechData(heroId);
                if (detailData) {
                    if (!fs.existsSync(this.buildsDir)) fs.mkdirSync(this.buildsDir, { recursive: true });
                    fs.writeFileSync(filePath, JSON.stringify(detailData, null, 2));
                }
            }

            return {
                name: baseInfo ? baseInfo.name : `ID: ${heroId}`,
                winRate: baseInfo ? baseInfo.winRate : '??%',
                ...(detailData || {})
            };
        } catch (e) {
            log('Data', `[ERROR] getHeroBuild failed: ${e.message}`);
            return null;
        }
    }
}

module.exports = new DataService();
