const { app, BrowserWindow } = require('electron');

app.whenReady().then(async () => {
    const win = new BrowserWindow({ show: false });
    try {
        await win.loadURL('https://hextech.dtodo.cn/zh-CN/champion-stats/55');
        await new Promise(r => setTimeout(r, 15000));
        
        const tabs = await win.webContents.executeJavaScript(`
            Array.from(document.querySelectorAll('button, div, span'))
                .filter(el => ['棱彩', '黄金', '白银'].includes(el.innerText))
                .map(el => ({
                    text: el.innerText,
                    tagName: el.tagName,
                    clickable: typeof el.onclick === 'function' || getComputedStyle(el).cursor === 'pointer'
                }))
        `);
        console.log('--- Tab 探测结果 ---');
        console.log(tabs);
    } finally { app.quit(); }
});
