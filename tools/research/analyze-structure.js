const { app, BrowserWindow } = require('electron');
const fs = require('fs');
const path = require('path');

app.whenReady().then(async () => {
    console.log('正在深度分析卡特琳娜的数据包结构...');
    const win = new BrowserWindow({ show: false, webPreferences: { offscreen: true } });
    try {
        await win.loadURL('https://hextech.dtodo.cn/zh-CN/champion-stats/55');
        await new Promise(r => setTimeout(r, 10000));
        
        const fullJson = await win.webContents.executeJavaScript('JSON.stringify(window.__NEXT_DATA__)');
        fs.writeFileSync('debug_structure.json', fullJson, 'utf8');
        console.log('分析完成，结构已保存至 debug_structure.json');
    } catch (e) {
        console.error('分析失败:', e.message);
    } finally {
        app.quit();
    }
});
