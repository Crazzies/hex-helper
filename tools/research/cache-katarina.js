const { app } = require('electron');
const fs = require('fs');
const path = require('path');
const scraper = require('./src/main/services/scraper-service');

app.whenReady().then(async () => {
    console.log('正在抓取卡特琳娜 (ID: 55) 的海克斯推荐数据...');
    
    try {
        const result = await scraper.scrapeHeroDetail("55");
        
        if (result) {
            const cachePath = path.join(__dirname, 'cache/hero-builds/55.json');
            
            // 确保目录存在
            if (!fs.existsSync(path.dirname(cachePath))) {
                fs.mkdirSync(path.dirname(cachePath), { recursive: true });
            }

            // 以 UTF-8 编码写入文件
            fs.writeFileSync(cachePath, JSON.stringify(result, null, 2), 'utf8');
            
            console.log('--- 抓取成功 ---');
            console.log('文件已保存至:', cachePath);
            console.log('数据内容预览:', JSON.stringify(result));
        } else {
            console.error('抓取失败：未能在页面中找到数据。');
        }
    } catch (e) {
        console.error('程序崩溃:', e.message);
    } finally {
        app.quit();
    }
});
