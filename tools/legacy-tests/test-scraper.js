const { app, BrowserWindow } = require('electron');
const path = require('path');
// 模拟环境
global.require = require;

// 启动测试
app.whenReady().then(async () => {
    console.log('--- [TEST] Starting Katarina (ID: 55) Data Extraction Test ---');
    
    // 动态加载我们重构后的爬虫服务
    const scraper = require('./src/main/services/scraper-service');
    
    try {
        console.log('Step 1: Accessing hextech.dtodo.cn/zh-CN/champion-stats/55...');
        const result = await scraper.scrapeHeroDetail("55");
        
        if (result) {
            console.log('--- [TEST SUCCESS] ---');
            console.log('Hero: 卡特琳娜 (Katarina)');
            console.log('Recommended Items:', result.items.join(' | '));
            console.log('Hextech Augments:', result.hextech.join(' | '));
        } else {
            console.log('--- [TEST FAILED] ---');
            console.log('Reason: Scraper returned null. Possible 403 or DOM mismatch.');
        }
    } catch (e) {
        console.error('--- [TEST CRASHED] ---');
        console.error(e.message);
    } finally {
        console.log('--- [TEST ENDED] ---');
        app.quit();
    }
});
