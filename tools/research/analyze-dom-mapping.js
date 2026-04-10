const { app, BrowserWindow } = require('electron');
const fs = require('fs');

app.whenReady().then(async () => {
    const win = new BrowserWindow({ show: false });
    try {
        await win.loadURL('https://hextech.dtodo.cn/zh-CN/champion-stats/55');
        await new Promise(r => setTimeout(r, 15000));
        
        // 导出所有图片的 alt 和它们父级的文字，用来找规律
        const map = await win.webContents.executeJavaScript(`
            Array.from(document.querySelectorAll('img')).map(img => ({
                alt: img.alt,
                parentText: img.parentElement.innerText.substring(0, 50),
                grandParentText: img.parentElement.parentElement.innerText.substring(0, 100)
            }))
        `);
        fs.writeFileSync('img_map.json', JSON.stringify(map, null, 2));
        console.log('规律地图已生成: img_map.json');
    } finally { app.quit(); }
});
