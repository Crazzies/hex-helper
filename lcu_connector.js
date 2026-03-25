const { execSync } = require('child_process');
const https = require('https');

class LcuConnector {
    constructor() {
        this.lcuData = null;
        this.agent = new https.Agent({
            rejectUnauthorized: false
        });
    }

    async connect() {
        return new Promise((resolve, reject) => {
            try {
                const command = 'wmic process where name="LeagueClientUx.exe" get commandline';
                const stdout = execSync(command).toString();

                const portMatch = stdout.match(/--app-port=([0-9]+)/);
                const tokenMatch = stdout.match(/--remoting-auth-token=([\w-]+)/);

                if (portMatch && tokenMatch) {
                    const port = portMatch[1];
                    const password = tokenMatch[1];
                    this.lcuData = { 
                        port, 
                        password, 
                        auth: Buffer.from(`riot:${password}`).toString('base64') 
                    };
                    return resolve(this.lcuData);
                }
            } catch (e) {}
            reject("Waiting for League Client...");
        });
    }

    getBaseUrl() {
        if (!this.lcuData) return null;
        return `https://127.0.0.1:${this.lcuData.port}`;
    }

    async request(url, method = 'GET') {
        if (!this.lcuData) return null;
        return new Promise((resolve, reject) => {
            const options = {
                method: method,
                headers: {
                    'Authorization': `Basic ${this.lcuData.auth}`,
                    'Accept': 'application/json'
                },
                agent: this.agent
            };

            const req = https.request(`${this.getBaseUrl()}${url}`, options, (res) => {
                const chunks = [];
                res.on('data', (chunk) => chunks.push(chunk));
                res.on('end', () => {
                    const buffer = Buffer.concat(chunks);
                    const rawData = buffer.toString('utf8'); // 强制 UTF-8 解析
                    try {
                        resolve(JSON.parse(rawData));
                    } catch (e) {
                        resolve(rawData.replace(/^"|"$/g, ''));
                    }
                });
            });

            req.on('error', (e) => reject(e));
            req.end();
        });
    }
}

module.exports = new LcuConnector();
