const { app } = require('electron');
const fs = require('fs');
const path = require('path');

class ConfigService {
    constructor() {
        // 在打包后，使用系统的 AppData 目录存放配置文件
        this.configPath = path.join(app.getPath('userData'), 'config.json');
        this.defaults = {
            opacity: 0.85,
            zoom: 1.0,
            autoHide: false,
            shortcut: 'Alt+V',
            alwaysOnTop: true
        };
        this.config = this.load();
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
        try {
            // 确保目录存在
            const dir = path.dirname(this.configPath);
            if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
            fs.writeFileSync(this.configPath, JSON.stringify(this.config, null, 2));
        } catch (e) {}
    }

    get(key) { return this.config[key]; }
}

module.exports = new ConfigService();
