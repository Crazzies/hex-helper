const { app, BrowserWindow, globalShortcut, Tray, Menu, nativeImage, ipcMain, dialog } = require('electron');
const path = require('path');
const fs = require('fs');
const { uIOhook, UiohookKey } = require('uiohook-napi');
const lcu = require('./services/lcu-service');
const dataService = require('./services/data-service');
const scraper = require('./services/scraper-service');
const config = require('./services/config-service');
const { log, chcp, readLog, getLogFilePath } = require('./utils/logger');

app.commandLine.appendSwitch('ignore-certificate-errors');

let mainWindow;
let tray = null;
let champMap = {};
let lastHeroBuildId = null; // 记录最后一次成功显示的英雄 ID
let registeredShortcut = config.get('shortcut'); // 当前已注册的快捷键
let dragHookStarted = false;
let dragKeyActive = false;
let lastToggleAt = 0;
let lastBenchData = [];
const TOGGLE_COOLDOWN_MS = 350;

function applyClickThrough(enabled) {
    if (!mainWindow) return;
    mainWindow.setIgnoreMouseEvents(!!enabled, { forward: true });
}

function requestToggle() {
    const now = Date.now();
    if (now - lastToggleAt < TOGGLE_COOLDOWN_MS) return;
    lastToggleAt = now;
    toggleWindow();
}

function normalizeShortcut(shortcut) {
    if (!shortcut || typeof shortcut !== 'string') return null;
    const parts = shortcut.split('+').map(p => p.trim()).filter(Boolean);
    if (parts.length === 0) return null;
    const mods = { ctrl: false, alt: false, shift: false };
    let key = null;
    parts.forEach(part => {
        const upper = part.toUpperCase();
        if (upper === 'CTRL' || upper === 'CONTROL') mods.ctrl = true;
        else if (upper === 'ALT') mods.alt = true;
        else if (upper === 'SHIFT') mods.shift = true;
        else key = upper;
    });
    if (!key) return null;
    const keyCode = UiohookKey[key] || UiohookKey[`Key${key}`] || UiohookKey[key.toLowerCase()];
    if (!keyCode) return null;
    return { mods, keyCode };
}

function setupDragKeyHook() {
    if (dragHookStarted) return;
    dragHookStarted = true;

    const getToggleShortcut = () => normalizeShortcut(config.get('shortcut')) || { mods: { alt: true, ctrl: false, shift: false }, keyCode: UiohookKey.V };
    const isToggleMatch = (event, toggle) => {
        if (!toggle) return false;
        if (event.keycode !== toggle.keyCode) return false;
        if (toggle.mods.ctrl && !event.ctrlKey) return false;
        if (toggle.mods.alt && !event.altKey) return false;
        if (toggle.mods.shift && !event.shiftKey) return false;
        return true;
    };

    const isDragKeyPressed = (event) => {
        const dragKey = config.get('dragKey') || 'Ctrl';
        if (dragKey === 'Ctrl') return !!event.ctrlKey;
        if (dragKey === 'Alt') return !!event.altKey;
        if (dragKey === 'Shift') return !!event.shiftKey;
        return false;
    };

    uIOhook.on('keydown', event => {
        const toggle = getToggleShortcut();
        if (isToggleMatch(event, toggle)) {
            requestToggle();
        }
        if (!mainWindow || mainWindow.isSettingsOpen) return;
        const dragKey = config.get('dragKey') || 'Ctrl';
        if (dragKey === 'None') return;
        if (!dragKeyActive && isDragKeyPressed(event)) {
            dragKeyActive = true;
            applyClickThrough(false);
        }
    });

    uIOhook.on('keyup', event => {
        const dragKey = config.get('dragKey') || 'Ctrl';
        if (dragKey === 'None') return;
        if (dragKeyActive && !isDragKeyPressed(event) && !mainWindow?.isSettingsOpen && config.get('clickThrough') !== false) {
            dragKeyActive = false;
            applyClickThrough(true);
        }
    });

    uIOhook.start();
}

function createWindow() {
    const clickThrough = config.get('clickThrough') !== false; // 默认为 true
    
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
    applyClickThrough(clickThrough);
    mainWindow.loadFile(path.join(__dirname, '../renderer/index.html'));
    
    mainWindow.webContents.on('did-finish-load', () => {
        mainWindow.webContents.setZoomFactor(config.get('zoom'));
    });

    // 监听鼠标事件用于拖动
    mainWindow.on('moved', () => { isDragging = false; });
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
        { label: '查看日志', click: () => showLogDialog() },
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
    // 打开设置时暂时禁用穿透，以便用户可以操作
    applyClickThrough(false);
    mainWindow.isSettingsOpen = true;
    dragKeyActive = false;
    mainWindow.webContents.send('switch-view', 'settings');
}

// 监听视图切换，恢复穿透状态
ipcMain.on('switch-view', (event, view) => {
    if (view !== 'settings' && mainWindow.isSettingsOpen) {
        mainWindow.isSettingsOpen = false;
        dragKeyActive = false;
        // 恢复穿透设置
        applyClickThrough(config.get('clickThrough') !== false);
    }
});

function showLogDialog() {
    const logContent = readLog(200);
    dialog.showMessageBox(mainWindow, {
        type: 'info',
        title: '日志查看',
        message: '最近 200 行日志:',
        detail: logContent || '暂无日志',
        buttons: ['确定', '打开日志文件'],
        defaultId: 0
    }).then(result => {
        if (result.response === 1) {
            const logPath = getLogFilePath();
            require('electron').shell.openPath(logPath);
        }
    });
}

// 注册快捷键
function registerShortcut(newShortcut) {
    // 先注销旧的
    if (registeredShortcut) {
        try {
            globalShortcut.unregister(registeredShortcut);
        } catch (e) {}
    }
    // 注册新的
    try {
        globalShortcut.register(newShortcut, () => requestToggle());
        registeredShortcut = newShortcut;
        log('Main', `Shortcut registered: ${newShortcut}`);
        return true;
    } catch (e) {
        log('Main', `Failed to register shortcut: ${e.message}`);
        return false;
    }
}

// IPC 处理器
ipcMain.handle('get-log', async (event, lines = 100) => {
    return readLog(lines);
});

ipcMain.handle('get-log-path', async () => {
    return getLogFilePath();
});

ipcMain.handle('get-config', async () => {
    return config.getAll();
});

ipcMain.handle('set-config', async (event, newConfig) => {
    // 保存配置
    config.save(newConfig);
    
    // 应用各项配置
    if (newConfig.opacity !== undefined) {
        mainWindow.setOpacity(newConfig.opacity);
    }
    if (newConfig.zoom !== undefined) {
        mainWindow.webContents.setZoomFactor(newConfig.zoom);
    }
    if (newConfig.shortcut !== undefined) {
        registerShortcut(newConfig.shortcut);
    }
    if (newConfig.clickThrough !== undefined && !mainWindow.isSettingsOpen) {
        applyClickThrough(newConfig.clickThrough);
    }
    
    return true;
});

ipcMain.handle('check-shortcut-conflict', async (event, shortcut) => {
    return config.checkShortcutConflict(shortcut);
});

ipcMain.on('update-config', (event, newConfig) => {
    config.save(newConfig);
    if (newConfig.opacity !== undefined) mainWindow.setOpacity(newConfig.opacity);
    if (newConfig.zoom !== undefined) mainWindow.webContents.setZoomFactor(newConfig.zoom);
});

ipcMain.on('clear-cache', () => {
    const cacheDir = path.join(app.getPath('userData'), 'cache', 'hero-builds');
    if (fs.existsSync(cacheDir)) {
        try {
            fs.readdirSync(cacheDir).forEach(file => fs.unlinkSync(path.join(cacheDir, file)));
            log('Main', 'Cache cleared');
        } catch(e) { log('Main', `Cache clear failed: ${e.message}`); }
    }
});

app.whenReady().then(async () => {
    chcp();
    createWindow();
    createTray();
    setupDragKeyHook();
    
    // 注册初始快捷键
    registerShortcut(config.get('shortcut'));

    // 启动后执行一次后台静默数据同步（延迟 & 避免游戏中触发）
    setTimeout(() => {
        const phase = lcu.lastPhase || 'None';
        if (!['InProgress', 'GameStart', 'ChampSelect'].includes(phase)) {
            dataService.syncWinRates(scraper);
        }
    }, 20000);

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

    let buildFetchInFlight = false;

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
            if (id && id !== lastHeroBuildId && !buildFetchInFlight) {
                const heroFromDB = dataService.winRates[id.toString()];
                const name = heroFromDB ? heroFromDB.name : (champMap[id.toString()] || `ID: ${id}`);
                
                log('Main', `New build needed for: ${name}`);
                mainWindow.webContents.send('status', `Loading ${name}...`);

                // 先显示基础信息，避免空白
                mainWindow.webContents.send('update-build', {
                    name: name,
                    winRate: heroFromDB ? heroFromDB.winRate : '??%',
                    isFallback: true
                });
                lastHeroBuildId = id;

                buildFetchInFlight = true;
                const build = await dataService.getHeroBuild(id, scraper);
                buildFetchInFlight = false;
                if (build) {
                    mainWindow.webContents.send('update-build', build);
                }
            }
        }
    }

    async function updateBenchData() {
        const session = await lcu.request('/lol-champ-select/v1/session');
        if (!session || typeof session !== 'object') {
            log('Main', 'ChampSelect session unavailable');
            // fallback: use current champion id if available
            if (lcu.lastChampionId && lcu.lastChampionId > 0) {
                const hero = dataService.winRates[lcu.lastChampionId.toString()];
                const fallbackData = [{
                    id: lcu.lastChampionId,
                    name: hero ? hero.name : (champMap[lcu.lastChampionId.toString()] || `ID: ${lcu.lastChampionId}`),
                    winRate: hero ? hero.winRate : '??%'
                }];
                lastBenchData = fallbackData;
                mainWindow.webContents.send('update-bench', fallbackData);
                log('Main', `Fallback bench data from current champion: ${lcu.lastChampionId}`);
                return;
            }
            if (lastBenchData.length > 0) {
                mainWindow.webContents.send('update-bench', lastBenchData);
            } else {
                mainWindow.webContents.send('update-bench', [{ name: '等待选人数据...', winRate: '--' }]);
            }
            return;
        }

        const myTeam = Array.isArray(session.myTeam) ? session.myTeam : [];
        const benchChampions = Array.isArray(session.benchChampions) ? session.benchChampions : [];
        log('Main', `ChampSelect session loaded: team=${myTeam.length}, bench=${benchChampions.length}`);

        // 获取我的英雄ID
        const myId = myTeam.find(m => m.cellId === session.localPlayerCellId)?.championId;

        // 获取所有队友的英雄ID（包括板凳席）
        const teamIds = myTeam
            .map(m => m.championId)
            .filter(id => id && id > 0);

        const benchIds = benchChampions.map(c => c.championId).filter(id => id && id > 0);

        // 合并所有英雄ID（我的+队友+板凳），去重
        const allIds = [...new Set([myId, ...teamIds, ...benchIds])].filter(id => id);

        if (allIds.length === 0) {
            log('Main', 'ChampSelect session empty');
            // fallback: use current champion id if available
            if (lcu.lastChampionId && lcu.lastChampionId > 0) {
                const hero = dataService.winRates[lcu.lastChampionId.toString()];
                const fallbackData = [{
                    id: lcu.lastChampionId,
                    name: hero ? hero.name : (champMap[lcu.lastChampionId.toString()] || `ID: ${lcu.lastChampionId}`),
                    winRate: hero ? hero.winRate : '??%'
                }];
                lastBenchData = fallbackData;
                mainWindow.webContents.send('update-bench', fallbackData);
                log('Main', `Fallback bench data from current champion: ${lcu.lastChampionId}`);
                return;
            }
            if (lastBenchData.length > 0) {
                mainWindow.webContents.send('update-bench', lastBenchData);
            } else {
                mainWindow.webContents.send('update-bench', [{ name: '暂无英雄数据', winRate: '--' }]);
            }
            return;
        }

        // 获取每个英雄的胜率信息
        const displayData = allIds.map(id => {
            const hero = dataService.winRates[id.toString()];
            // 解析胜率为数值用于排序
            let winRateNum = 0;
            if (hero && hero.winRate) {
                const match = hero.winRate.match(/(\d+\.?\d*)/);
                if (match) winRateNum = parseFloat(match[1]);
            }
            return {
                id: id,
                name: hero ? hero.name : (champMap[id.toString()] || `ID: ${id}`),
                winRate: hero ? hero.winRate : "??%",
                winRateNum: winRateNum,
                isMe: id === myId // 标记是否是自己选择的英雄
            };
        });

        // 按胜率从高到低排序
        displayData.sort((a, b) => b.winRateNum - a.winRateNum);

        lastBenchData = displayData;
        mainWindow.webContents.send('update-bench', displayData);
        log('Main', `Bench updated: ${displayData.length} heroes`);
    }

    // 选人阶段逻辑 - 获取所有队友英雄并按胜率排序
    setInterval(async () => {
        if (lcu.lastPhase === 'ChampSelect') {
            updateBenchData();
        }
    }, 2000);
});

app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit(); });

app.on('before-quit', () => {
    try { if (uIOhook && uIOhook.stop) uIOhook.stop(); } catch (e) {}
});
