const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
    onStatus: (callback) => ipcRenderer.on('status', (_event, value) => callback(value)),
    onBench: (callback) => ipcRenderer.on('update-bench', (_event, value) => callback(value)),
    onBuild: (callback) => ipcRenderer.on('update-build', (_event, value) => callback(value)),
    onReset: (callback) => ipcRenderer.on('reset-ui', (_event) => callback()),
    onSwitchView: (callback) => ipcRenderer.on('switch-view', (_event, value) => callback(value)),
    notifyView: (view) => ipcRenderer.send('switch-view', view),
    // 日志相关
    getLog: (lines) => ipcRenderer.invoke('get-log', lines),
    getLogPath: () => ipcRenderer.invoke('get-log-path'),
    // 配置相关
    getConfig: () => ipcRenderer.invoke('get-config'),
    setConfig: (config) => ipcRenderer.invoke('set-config', config),
    // 快捷键相关
    checkShortcutConflict: (shortcut) => ipcRenderer.invoke('check-shortcut-conflict', shortcut),
    // 渲染层错误上报
    reportRendererError: (message) => ipcRenderer.send('renderer-error', message)
});
