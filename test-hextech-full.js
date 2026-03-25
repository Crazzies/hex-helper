
const { app } = require('electron');
const scraperService = require('./src/main/services/scraper-service');
const { log, chcp } = require('./src/main/utils/logger');

// 确保控制台支持中文
chcp();

// 忽略证书错误以解决 SSL Handshake Failed
app.commandLine.appendSwitch('ignore-certificate-errors');
app.commandLine.appendSwitch('allow-insecure-localhost');

async function runTest() {
    log('Test', '--- Starting Full 177 Augments Scrape Test (ID: 10 - Kayle) ---');
    
    try {
        app.on('certificate-error', (event, webContents, url, error, certificate, callback) => {
            event.preventDefault();
            callback(true);
        });

        const data = await scraperService.scrapeHextechData(10);
        
        if (data) {
            log('Test', `Successfully scraped data for: ${data.championName}`);
            log('Test', `Total Augments Captured: ${data.count}`);
            log('Test', `Version: ${data.version}`);
            
            log('Test', '--- Prismatic (T1) Top 5 ---');
            console.table(data.prismatic.slice(0, 5));
            
            log('Test', '--- Gold (T2) Top 5 ---');
            console.table(data.gold.slice(0, 5));
            
            log('Test', '--- Silver (T3) Top 5 ---');
            console.table(data.silver.slice(0, 5));
            
            // 验证是否真的拿到了 177 条（或接近这个数）
            if (data.count > 100) {
                log('Test', '🎉 PASS: Successfully bypassed the 25-limit and captured full data!');
            } else {
                log('Test', `⚠️ WARNING: Only captured ${data.count} augments. Check if "Show All" button click failed.`);
            }
        } else {
            log('Test', 'FAILED: No data returned from ScraperService.');
        }
    } catch (e) {
        log('Test', `CRITICAL ERROR: ${e.message}`);
    } finally {
        app.quit();
    }
}

app.whenReady().then(runTest);
