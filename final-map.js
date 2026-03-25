const { app, BrowserWindow } = require('electron');

app.whenReady().then(async () => {
    const win = new BrowserWindow({ show: false });
    try {
        await win.loadURL('https://hextech.dtodo.cn/zh-CN/champion-stats/55');
        await new Promise(r => setTimeout(r, 12000));
        
        const info = await win.webContents.executeJavaScript(`
            (() => {
                return {
                    buttons: Array.from(document.querySelectorAll('button')).map(b => b.innerText),
                    headers: Array.from(document.querySelectorAll('h1,h2,h3,h4,div')).filter(d => d.innerText.length < 20).map(d => d.innerText)
                };
            })()
        `);
        console.log('--- Page Map ---');
        console.log(JSON.stringify(info, null, 2));
    } finally { app.quit(); }
});
