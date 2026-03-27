const { app } = require('electron');
const fs = require('fs');
const path = require('path');

// 保留的配置项用于冲突检测
const RESERVED_SHORTCUTS = [
    'Alt+V', 'Ctrl+C', 'Ctrl+V', 'Ctrl+Z', 'Ctrl+A', 'Ctrl+S',
    'Ctrl+W', 'Ctrl+Q', 'Ctrl+T', 'Ctrl+Tab', 'Ctrl+Shift+Tab',
    'F5', 'F11', 'PrintScreen', 'Win', 'Alt+Tab', 'Alt+F4',
    'Ctrl+Alt+Delete', 'Escape'
];

class ConfigService {
    constructor() {
        // 在打包后，使用系统的 AppData 目录存放配置文件
        this.configPath = path.join(app.getPath('userData'), 'config.json');
        this.defaults = {
            opacity: 0.85,
            zoom: 1.0,
            autoHide: false,
            shortcut: 'Alt+V',
            alwaysOnTop: true,
            dragKey: 'Ctrl',  // 用于拖动窗口的按键，默认为 Ctrl
            clickThrough: true  // 窗口默认是否穿透
        };
        this.config = this.load();
        // 临时存储未保存的更改，用于取消功能
        this.pendingConfig = null;
    }

    load() {
        try {
            if (fs.existsSync(this.configPath)) {
                return { ...this.defaults, ...JSON.parse(fs.readFileSync(this.configPath, 'utf8')) };
            }
        } catch (e) {}
        return { ...this.defaults };
    }

    save(newConfig) {
        this.config = { ...this.config, ...newConfig };
        // 清除待生效的临时配置
        this.pendingConfig = null;
        try {
            // 确保目录存在
            const dir = path.dirname(this.configPath);
            if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
            fs.writeFileSync(this.configPath, JSON.stringify(this.config, null, 2));
        } catch (e) {}
    }

    /**
     * 获取当前配置（用于前端显示）
     */
    getAll() {
        return { ...this.config };
    }

    /**
     * 设置待生效的配置（尚未写入文件，用于预览/取消）
     * @param {Object} newConfig 新的配置项
     */
    setPending(newConfig) {
        this.pendingConfig = { ...this.config, ...newConfig };
        return this.pendingConfig;
    }

    /**
     * 获取待生效的配置
     */
    getPending() {
        return this.pendingConfig ? { ...this.pendingConfig } : null;
    }

    /**
     * 取消待生效的更改
     */
    cancelPending() {
        this.pendingConfig = null;
    }

    /**
     * 检查快捷键是否冲突
     * @param {string} shortcut 要检查的快捷键
     * @returns {Object} { isConflict: boolean, message: string }
     */
    checkShortcutConflict(shortcut) {
        if (!shortcut) {
            return { isConflict: true, message: '快捷键不能为空' };
        }

        const normalized = shortcut.trim();

        // 检查是否是保留的系统快捷键
        if (RESERVED_SHORTCUTS.some(s => s.toLowerCase() === normalized.toLowerCase())) {
            return { isConflict: true, message: `快捷键 ${normalized} 是系统保留的，不建议使用` };
        }

        // 检查是否与当前使用的快捷键冲突
        if (this.config.shortcut && this.config.shortcut.toLowerCase() === normalized.toLowerCase()) {
            return { isConflict: false, message: '快捷键未变更' };
        }

        return { isConflict: false, message: '快捷键可用' };
    }

    get(key) { return this.config[key]; }
}

module.exports = new ConfigService();
