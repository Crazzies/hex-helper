const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
    onStatus: (callback) => ipcRenderer.on('status', (_event, value) => callback(value)),
    onBench: (callback) => ipcRenderer.on('update-bench', (_event, value) => callback(value)),
    onBuild: (callback) => ipcRenderer.on('update-build', (_event, value) => callback(value)),
    onReset: (callback) => ipcRenderer.on('reset-ui', (_event) => callback()),
    onSwitchView: (callback) => ipcRenderer.on('switch-view', (_event, value) => callback(value))
});
