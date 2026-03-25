const fs = require('fs');
const path = require('path');
const logFile = path.join(__dirname, '../../../app.log');

const chcp = () => {
    try { require('child_process').execSync('chcp 65001'); } catch(e) {}
};

const log = (module, message, data = "") => {
    const timestamp = new Date().toLocaleTimeString();
    const logLine = `[${timestamp}] [${module}] ${message} ${data ? JSON.stringify(data) : ""}\n`;
    console.log(logLine.trim());
    try {
        fs.appendFileSync(logFile, logLine);
    } catch (e) {}
};

module.exports = { log, chcp };
