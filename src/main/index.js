const { app, BrowserWindow, globalShortcut, Tray, Menu, nativeImage, ipcMain } = require('electron');
const path = require('path');
const fs = require('fs');
const lcu = require('./services/lcu-service');
const dataService = require('./services/data-service');
const scraper = require('./services/scraper-service');
const config = require('./services/config-service');
const { log, chcp } = require('./utils/logger');

app.commandLine.appendSwitch('ignore-certificate-errors');

let mainWindow;
let tray = null;
let champMap = {}; 
let lastHeroBuildId = null; // 记录最后一次成功显示的英雄 ID

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 320, height: 600,
        frame: false, transparent: true,
        alwaysOnTop: true, skipTaskbar: true,
        opacity: config.get('opacity'),
        webPreferences: {
            preload: path.join(__dirname, '../preload.js'),
            contextIsolation: true,
            nodeIntegration: false
        }
    });
    mainWindow.setAlwaysOnTop(true, 'screen-saver');
    mainWindow.setPosition(1600, 100);
    mainWindow.loadFile(path.join(__dirname, '../renderer/index.html'));
    
    mainWindow.webContents.on('did-finish-load', () => {
        mainWindow.webContents.setZoomFactor(config.get('zoom'));
    });
}

function createTray() {
    const iconPath = path.join(app.getAppPath(), 'icon.png');
    let icon = nativeImage.createFromPath(iconPath);
    if (icon.isEmpty()) {
        log('Main', `Tray icon missing at ${iconPath}, using fallback.`);
        icon = nativeImage.createEmpty();
    }
    
    tray = new Tray(icon);
    const contextMenu = Menu.buildFromTemplate([
        { label: '显示/隐藏窗口 (Alt+V)', click: () => toggleWindow() },
        { label: '打开设置面板', click: () => openSettings() },
        { label: '重置位置', click: () => mainWindow.setPosition(1600, 100) },
        { type: 'separator' },
        { label: '退出程序', click: () => { app.isQuiting = true; app.quit(); } }
    ]);
    tray.setToolTip('HexHelper');
    tray.setContextMenu(contextMenu);
    tray.on('click', () => toggleWindow());
}

function toggleWindow() {
    if (mainWindow.isVisible()) mainWindow.hide();
    else { mainWindow.show(); mainWindow.setAlwaysOnTop(true, 'screen-saver'); }
}

function openSettings() {
    if (!mainWindow.isVisible()) mainWindow.show();
    mainWindow.setAlwaysOnTop(true, 'screen-saver');
    mainWindow.webContents.send('switch-view', 'settings');
}

ipcMain.on('update-config', (event, newConfig) => {
    config.save(newConfig);
    if (newConfig.opacity !== undefined) mainWindow.setOpacity(newConfig.opacity);
    if (newConfig.zoom !== undefined) mainWindow.webContents.setZoomFactor(newConfig.zoom);
});

ipcMain.on('clear-cache', () => {
    const cacheDir = path.join(__dirname, '../../../cache/hero-builds');
    if (fs.existsSync(cacheDir)) {
        try {
            fs.readdirSync(cacheDir).forEach(file => fs.unlinkSync(path.join(cacheDir, file)));
        } catch(e) {}
    }
});

app.whenReady().then(async () => {
    chcp();
    createWindow();
    createTray();
    
    globalShortcut.register(config.get('shortcut'), () => toggleWindow());

    // 启动后执行一次后台静默数据同步
    setTimeout(() => {
        dataService.syncWinRates(scraper);
    }, 5000);

    lcu.startPolling();

    lcu.on('connected', async () => {
        mainWindow.webContents.send('status', 'League Connected');
        const list = await lcu.request('/lol-game-data/assets/v1/champion-summary.json');
        if (Array.isArray(list)) {
            list.forEach(c => { if (c.id > 0) champMap[c.id.toString()] = c.name; });
        }
    });

    lcu.on('phase-changed', (phase) => handlePhaseChange(phase));

    setInterval(() => {
        if (lcu.lastPhase) handlePhaseChange(lcu.lastPhase);
    }, 5000);

    async function handlePhaseChange(phase) {
        mainWindow.webContents.send('status', `Phase: ${phase}`);
        
        if (['Lobby', 'None', 'Matchmaking', 'ChampSelect'].includes(phase)) {
            if (lastHeroBuildId !== null) {
                mainWindow.webContents.send('reset-ui');
                lastHeroBuildId = null;
            }
        }
        
        if (['InProgress', 'GameStart'].includes(phase)) {
            mainWindow.webContents.send('switch-view', 'build');
            const id = lcu.lastChampionId;
            if (id && id !== lastHeroBuildId) {
                const heroFromDB = dataService.winRates[id.toString()];
                const name = heroFromDB ? heroFromDB.name : (champMap[id.toString()] || `ID: ${id}`);
                
                log('Main', `New build needed for: ${name}`);
                mainWindow.webContents.send('status', `Loading ${name}...`);
                
                const build = await dataService.getHeroBuild(id, scraper);
                if (build) {
                    mainWindow.webContents.send('update-build', build);
                    lastHeroBuildId = id;
                } else {
                    mainWindow.webContents.send('update-build', {
                        name: name, winRate: heroFromDB ? heroFromDB.winRate : '??%', isFallback: true
                    });
                    lastHeroBuildId = id;
                }
            }
        }
    }

    setInterval(async () => {
        if (lcu.lastPhase === 'ChampSelect') {
            const session = await lcu.request('/lol-champ-select/v1/session');
            if (session) {
                const benchIds = (session.benchChampions || []).map(c => c.championId);
                const myId = (session.myTeam || []).find(m => m.cellId === session.localPlayerCellId)?.championId;
                const allIds = [...new Set([myId, ...benchIds])].filter(id => id);
                const displayData = allIds.map(id => {
                    const hero = dataService.winRates[id.toString()];
                    return {
                        name: hero ? hero.name : (champMap[id.toString()] || `ID: ${id}`),
                        winRate: hero ? hero.winRate : "??%"
                    };
                });
                mainWindow.webContents.send('update-bench', displayData);
            }
        }
    }, 2000);
});

app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit(); });
