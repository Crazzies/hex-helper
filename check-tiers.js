const { app, BrowserWindow } = require('electron');
const fs = require('fs');

app.whenReady().then(async () => {
    const win = new BrowserWindow({ show: false });
    try {
        await win.loadURL('https://hextech.dtodo.cn/zh-CN/champion-stats/55');
        await new Promise(r => setTimeout(r, 15000));
        
        // 打印所有的海克斯品阶特征
        const data = await win.webContents.executeJavaScript(`
            (() => {
                const stats = window.__NEXT_DATA__?.props?.pageProps?.championStats || {};
                const augments = stats.augmentStats || [];
                return augments.slice(0, 50).map(a => ({ name: a.name, tier: a.tier }));
            })()
        `);
        console.log('--- Augment Tier Samples ---');
        console.log(data);
    } finally { app.quit(); }
});
