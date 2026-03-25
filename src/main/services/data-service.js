const { app } = require('electron');
const fs = require('fs');
const path = require('path');
const { log } = require('../utils/logger');

class DataService {
    constructor() {
        // 只读资源：打包后在 app.asar 内，开发时在项目根目录
        const appPath = app.getAppPath();
        this.dbPath = path.join(appPath, 'hex_data.json');
        
        // 可写缓存：存放在用户的 AppData 目录
        this.buildsDir = path.join(app.getPath('userData'), 'cache', 'hero-builds');
        
        this.winRates = {};
        this.loadDatabase();
    }

    loadDatabase() {
        log('Data', `Loading database from: ${this.dbPath}`);
        try {
            if (fs.existsSync(this.dbPath)) {
                this.winRates = JSON.parse(fs.readFileSync(this.dbPath, 'utf8'));
                log('Data', `[SUCCESS] Database loaded. Found ${Object.keys(this.winRates).length} heroes.`);
            } else {
                log('Data', `[ERROR] Database file not found at ${this.dbPath}`);
            }
        } catch (e) {
            log('Data', `[ERROR] Load database failed: ${e.message}`);
        }
    }

    isToday(filePath) {
        try {
            if (!fs.existsSync(filePath)) return false;
            const stats = fs.statSync(filePath);
            const today = new Date().toDateString();
            const fileDate = new Date(stats.mtime).toDateString();
            return today === fileDate;
        } catch (e) {
            return false;
        }
    }

    async getHeroBuild(heroId, scraper) {
        log('Data', `Querying build for hero ID: ${heroId}`);
        try {
            const baseInfo = this.winRates[heroId.toString()];
            const filePath = path.join(this.buildsDir, `${heroId}.json`);
            let detailData = null;

            if (this.isToday(filePath)) {
                try {
                    detailData = JSON.parse(fs.readFileSync(filePath, 'utf8'));
                    log('Data', `[CACHE] Found local cache for hero ${heroId}`);
                } catch (e) {}
            }

            if (!detailData && scraper) {
                log('Data', `[SCRAPE] Starting live scrape for hero ${heroId}`);
                detailData = await scraper.scrapeHextechData(heroId);
                if (detailData) {
                    if (!fs.existsSync(this.buildsDir)) fs.mkdirSync(this.buildsDir, { recursive: true });
                    fs.writeFileSync(filePath, JSON.stringify(detailData, null, 2));
                    log('Data', `[SUCCESS] Scraped and cached for ${heroId}`);
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
