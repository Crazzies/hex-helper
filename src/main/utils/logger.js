const fs = require('fs');
const path = require('path');
const { app } = require('electron');

const DEFAULT_RETENTION_DAYS = 7;
const DEFAULT_MAX_FILES = 10;

let logOptions = {
    retentionDays: DEFAULT_RETENTION_DAYS,
    maxFiles: DEFAULT_MAX_FILES
};

const getPrimaryLogDir = () => {
    try {
        if (app && app.isPackaged) {
            return path.join(app.getPath('userData'), 'logs');
        }
    } catch (e) {}
    return path.join(__dirname, '../../../logs');
};

const getFallbackLogDir = () => {
    try {
        if (app) {
            const exeDir = path.dirname(app.getPath('exe'));
            return path.join(exeDir, 'logs');
        }
    } catch (e) {}
    return path.join(__dirname, '../../../logs');
};

const ensureLogDir = (dirPath) => {
    try {
        if (!fs.existsSync(dirPath)) {
            fs.mkdirSync(dirPath, { recursive: true });
        }
        return true;
    } catch (e) {
        return false;
    }
};

const resolveLogDir = () => {
    const primary = getPrimaryLogDir();
    if (ensureLogDir(primary)) return primary;
    const fallback = getFallbackLogDir();
    ensureLogDir(fallback);
    return fallback;
};

const buildLogFileName = () => {
    const now = new Date();
    const pad = (num) => String(num).padStart(2, '0');
    const name = `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}-${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
    return `app-${name}.log`;
};

const getLogFilePath = () => logFile;

let logDir = resolveLogDir();
let logFile = path.join(logDir, buildLogFileName());

// 清理过期日志并限制日志文件数量
const cleanupLogs = () => {
    try {
        if (!fs.existsSync(logDir)) return;
        const files = fs.readdirSync(logDir)
            .filter(name => name.endsWith('.log'))
            .map(name => ({
                name,
                path: path.join(logDir, name),
                mtime: fs.statSync(path.join(logDir, name)).mtime.getTime()
            }))
            .sort((a, b) => b.mtime - a.mtime);

        const now = Date.now();
        const retentionMs = logOptions.retentionDays * 24 * 60 * 60 * 1000;

        // 先清理超过保留天数的文件
        files.forEach(file => {
            if (now - file.mtime > retentionMs && file.path !== logFile) {
                try { fs.unlinkSync(file.path); } catch (e) {}
            }
        });

        // 重新读取并按数量限制
        const remaining = fs.readdirSync(logDir)
            .filter(name => name.endsWith('.log'))
            .map(name => ({
                name,
                path: path.join(logDir, name),
                mtime: fs.statSync(path.join(logDir, name)).mtime.getTime()
            }))
            .sort((a, b) => b.mtime - a.mtime);

        if (remaining.length > logOptions.maxFiles) {
            remaining.slice(logOptions.maxFiles).forEach(file => {
                if (file.path !== logFile) {
                    try { fs.unlinkSync(file.path); } catch (e) {}
                }
            });
        }
    } catch (e) {}
};

const setLogOptions = (options = {}) => {
    const retention = Number.parseInt(options.retentionDays, 10);
    const maxFiles = Number.parseInt(options.maxFiles, 10);
    if (!Number.isNaN(retention) && retention > 0) logOptions.retentionDays = retention;
    if (!Number.isNaN(maxFiles) && maxFiles > 0) logOptions.maxFiles = maxFiles;
    cleanupLogs();
};

const chcp = () => {
    try { require('child_process').execSync('chcp 65001'); } catch(e) {}
};

const log = (module, message, data = "") => {
    const timestamp = new Date().toLocaleTimeString();
    const logLine = `[${timestamp}] [${module}] ${message} ${data ? JSON.stringify(data) : ""}\n`;
    console.log(logLine.trim());
    try {
        if (!fs.existsSync(logDir)) {
            logDir = resolveLogDir();
        }
        if (!fs.existsSync(logFile)) {
            logFile = path.join(logDir, buildLogFileName());
        }
        fs.appendFileSync(logFile, logLine);
    } catch (e) {}
};

/**
 * 读取日志文件内容
 * @param {number} lines - 返回最近 N 行，默认 100
 * @returns {string} 日志内容
 */
const readLog = (lines = 100) => {
    try {
        if (fs.existsSync(logFile)) {
            const content = fs.readFileSync(logFile, 'utf8');
            const allLines = content.split('\n');
            return allLines.slice(-lines).join('\n');
        }
    } catch (e) {}
    return '';
};

/**
 * 获取日志文件路径，供前端下载使用
 * @returns {string} 日志文件完整路径
 */
module.exports = { log, chcp, readLog, getLogFilePath, setLogOptions };
