const fs = require('fs');
const path = require('path');
const { app } = require('electron');

const getLogPath = () => {
    // 在打包后使用 AppData 目录，否则使用项目根目录
    try {
        if (app && app.isPackaged) {
            return path.join(app.getPath('userData'), 'logs', 'app.log');
        }
    } catch (e) {}
    return path.join(__dirname, '../../../app.log');
};

let logFile = getLogPath();

const ensureLogDir = () => {
    try {
        const dir = path.dirname(logFile);
        if (!fs.existsSync(dir)) {
            fs.mkdirSync(dir, { recursive: true });
        }
    } catch (e) {}
};

const chcp = () => {
    try { require('child_process').execSync('chcp 65001'); } catch(e) {}
};

const log = (module, message, data = "") => {
    const timestamp = new Date().toLocaleTimeString();
    const logLine = `[${timestamp}] [${module}] ${message} ${data ? JSON.stringify(data) : ""}\n`;
    console.log(logLine.trim());
    try {
        ensureLogDir();
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
const getLogFilePath = () => logFile;

module.exports = { log, chcp, readLog, getLogFilePath };
