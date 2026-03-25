const { app, BrowserWindow, session } = require('electron');
const path = require('path');
const fs = require('fs');
const lcu = require('./lcu_connector');
const dataFetcher = require('./data_fetcher');

app.commandLine.appendSwitch('ignore-certificate-errors');

let overlayWindow;
let champMap = {}; 

function createOverlayWindow() {
    overlayWindow = new BrowserWindow({
        width: 320, height: 600, frame: false, transparent: true,
        alwaysOnTop: true, skipTaskbar: true,
        webPreferences: { nodeIntegration: true, contextIsolation: false }
    });
    overlayWindow.setPosition(1600, 100);
    overlayWindow.loadFile('index.html');
}

// 核心数据提取逻辑
async function scrapeDetailedInfo(heroId) {
    if (!heroId) return;
    const scraperWin = new BrowserWindow({ show: false, webPreferences: { offscreen: true } });
    try {
        await scraperWin.loadURL(`https://hextech.dtodo.cn/zh-CN/champion-stats/${heroId}`);
        await new Promise(r => setTimeout(r, 12000));
        const data = await scraperWin.webContents.executeJavaScript(`
            (() => {
                const raw = window.__NEXT_DATA__;
                if (!raw) return null;
                const stats = raw.props?.pageProps?.championStats || {};
                return {
                    items: (stats.recommendedItems || []).map(i => i.name).filter(n => n),
                    hextech: (stats.recommendedAugments || []).map(a => a.name).filter(n => n)
                };
            })()
        `);
        if (data) {
            overlayWindow.webContents.send('update-game-build', data);
        }
    } catch (e) {} finally {
        if (!scraperWin.isDestroyed()) scraperWin.destroy();
    }
}

async function syncNames() {
    try {
        const list = await lcu.request('/lol-game-data/assets/v1/champion-summary.json');
        if (Array.isArray(list)) {
            list.forEach(c => { if (c.id > 0) champMap[c.id.toString()] = c.name; });
        }
    } catch (e) {}
}

app.whenReady().then(async () => {
    createOverlayWindow();
    dataFetcher.loadLocal();

    // 默认演示：莉莉娅
    setTimeout(() => scrapeDetailedInfo("876"), 3000);

    setInterval(async () => {
        try {
            await lcu.connect();
            if (Object.keys(champMap).length < 50) await syncNames();

            let phaseRaw = await lcu.request('/lol-gameflow/v1/gameflow-phase');
            let phase = (typeof phaseRaw === 'string') ? phaseRaw : (phaseRaw.phase || "Lobby");

            if (phase === 'ChampSelect') {
                const sessionData = await lcu.request('/lol-champ-select/v1/session');
                if (sessionData) {
                    const benchIds = (sessionData.benchChampions || []).map(c => c.championId);
                    const myId = (sessionData.myTeam || []).find(m => m.cellId === sessionData.localPlayerCellId)?.championId;
                    
                    if (myId && myId !== dataFetcher.lastId) {
                        dataFetcher.lastId = myId;
                        scrapeDetailedInfo(myId.toString());
                    }

                    const allIds = [...new Set([myId, ...benchIds])].filter(id => id);
                    const displayData = allIds.map(id => ({
                        id, name: champMap[id.toString()] || `Hero: ${id}`,
                        winRate: (dataFetcher.heroes[id.toString()]?.winRate || "??%").match(/(\d{1,2}\.\d+)%/)?.[0] || "??%"
                    }));
                    overlayWindow.webContents.send('update-bench-detailed', displayData);
                    overlayWindow.webContents.send('status', `Select Phase: ${displayData.length} found`);
                }
            } else if (phase === 'InProgress' || phase === 'GameStart') {
                overlayWindow.webContents.send('status', 'Gaming - Syncing Build');
                const activeChamp = await lcu.request('/lol-champ-select/v1/current-champion');
                if (activeChamp && typeof activeChamp === 'number' && activeChamp !== dataFetcher.lastId) {
                    dataFetcher.lastId = activeChamp;
                    scrapeDetailedInfo(activeChamp.toString());
                }
            } else {
                overlayWindow.webContents.send('status', 'HexHelper Ready');
            }
        } catch (e) {
            overlayWindow.webContents.send('status', 'Waiting for LOL...');
        }
    }, 3000);
});

app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit(); });
