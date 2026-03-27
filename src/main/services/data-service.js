/**
 * 数据管理服务 (Data Service)
 * 负责英雄胜率数据库的加载、自动更新、以及英雄详情数据的磁盘缓存管理。
 */
const { app } = require('electron');
const fs = require('fs');
const path = require('path');
const { log } = require('../utils/logger');

class DataService {
    constructor() {
        this.winRates = {};
        this.userDataPath = app.getPath('userData');
        // 在线抓取到的最新胜率库存储路径
        this.onlineDbPath = path.join(this.userDataPath, 'hex_data_online.json');
        // 英雄出装/海克斯详情的缓存目录
        this.buildsDir = path.join(this.userDataPath, 'cache', 'hero-builds');
        
        this.loadDatabase();
    }

    /**
     * 加载胜率数据库
     * 逻辑：优先尝试加载 AppData 里的在线更新版，如果不存在则 require 打包内置的保底数据。
     */
    async loadDatabase() {
        try {
            // 1. 尝试加载用户目录下的“已同步”数据
            if (fs.existsSync(this.onlineDbPath)) {
                this.winRates = JSON.parse(fs.readFileSync(this.onlineDbPath, 'utf8'));
                log('Data', `Loaded updated winrates from AppData. Total: ${Object.keys(this.winRates).length}`);
            }

            // 2. 如果没有更新过，或者文件损坏，则加载打包时硬编码进去的资源
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
            log('Data', `Fatal database load error: ${e.message}`);
        }
    }

    /**
     * 执行后台数据同步
     * 目的：让工具具备“自我进化”能力，无需重新打包即可获取最新英雄胜率。
     * @param {ScraperService} scraper 爬虫实例
     */
    async syncWinRates(scraper) {
        log('Data', 'Triggering background data sync...');
        if (this.isToday(this.onlineDbPath)) {
            log('Data', 'Online winrates already synced today. Skipping.');
            return false;
        }
        const newData = await scraper.scrapeAllHeroWinRates();
        if (newData && Object.keys(newData).length > 50) {
            this.winRates = newData;
            // 将抓取到的全量数据持久化，下次启动直接变为 LOAD 1 模式
            fs.writeFileSync(this.onlineDbPath, JSON.stringify(newData, null, 2));
            log('Data', 'Online winrates synced and saved.');
            return true;
        }
        return false;
    }

    /**
     * 校验文件是否为今日生成
     * 用于确保缓存的“今日有效性”。
     */
    isToday(filePath) {
        try {
            if (!fs.existsSync(filePath)) return false;
            const stats = fs.statSync(filePath);
            const today = new Date().toDateString();
            const fileDate = new Date(stats.mtime).toDateString();
            return today === fileDate;
        } catch (e) { return false; }
    }

    /**
     * 获取指定英雄的完整攻略 (基础胜率 + 深度抓取的海克斯/出装)
     * @param {number} heroId 英雄 ID
     * @param {ScraperService} scraper 爬虫实例
     */
    async getHeroBuild(heroId, scraper) {
        try {
            const baseInfo = this.winRates[heroId.toString()];
            const filePath = path.join(this.buildsDir, `${heroId}.json`);
            let detailData = null;

            // 检查缓存
            if (this.isToday(filePath)) {
                try {
                    detailData = JSON.parse(fs.readFileSync(filePath, 'utf8'));
                } catch (e) {}
            }

            // 如果缓存失效，则触发实时抓取
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
            log('Data', `[ERROR] getHeroBuild failed for ID ${heroId}: ${e.message}`);
            return null;
        }
    }
}

module.exports = new DataService();
