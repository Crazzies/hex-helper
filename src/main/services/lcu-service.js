const { execSync } = require('child_process');
const https = require('https');
const EventEmitter = require('events');
const { log } = require('../utils/logger');

class LcuService extends EventEmitter {
    constructor() {
        super();
        this.lcuData = null;
        this.agent = new https.Agent({ rejectUnauthorized: false });
        this.lastPhase = null;
        this.lastChampionId = null;
        this.pollTimer = null;
    }

    // 提取密钥
    async connect() {
        try {
            const command = 'wmic process where name="LeagueClientUx.exe" get commandline';
            const stdout = execSync(command).toString();
            const portMatch = stdout.match(/--app-port=([0-9]+)/);
            const tokenMatch = stdout.match(/--remoting-auth-token=([\w-]+)/);

            if (portMatch && tokenMatch) {
                const newData = {
                    port: portMatch[1],
                    auth: Buffer.from(`riot:${tokenMatch[1]}`).toString('base64')
                };
                
                if (!this.lcuData) {
                    this.lcuData = newData;
                    log('LCU', 'Connected to League Client.');
                    this.emit('connected', this.lcuData);
                }
                return true;
            }
        } catch (e) {
            if (this.lcuData) {
                this.lcuData = null;
                log('LCU', 'Disconnected.');
                this.emit('disconnected');
            }
        }
        return false;
    }

    async request(url) {
        if (!this.lcuData) return null;
        return new Promise((resolve) => {
            const options = {
                method: 'GET',
                headers: {
                    'Authorization': `Basic ${this.lcuData.auth}`,
                    'Accept': 'application/json'
                },
                agent: this.agent
            };
            const req = https.request(`https://127.0.0.1:${this.lcuData.port}${url}`, options, (res) => {
                const chunks = [];
                res.on('data', (chunk) => chunks.push(chunk));
                res.on('end', () => {
                    const data = Buffer.concat(chunks).toString('utf8');
                    try { resolve(JSON.parse(data)); } catch (e) { resolve(data.replace(/"/g, '')); }
                });
            });
            req.on('error', () => resolve(null));
            req.end();
        });
    }

    startPolling() {
        if (this.pollTimer) return;
        this.pollTimer = setInterval(async () => {
            const connected = await this.connect();
            if (!connected) return;

            // 监听阶段变化
            const phase = await this.request('/lol-gameflow/v1/gameflow-phase');
            if (phase && phase !== this.lastPhase) {
                this.lastPhase = phase;
                this.emit('phase-changed', phase);
                log('LCU', `Phase changed: ${phase}`);
            }

            // 监听英雄变化
            if (phase === 'ChampSelect' || phase === 'InProgress') {
                const champId = await this.request('/lol-champ-select/v1/current-champion');
                if (typeof champId === 'number' && champId !== this.lastChampionId) {
                    this.lastChampionId = champId;
                    this.emit('champion-changed', champId);
                    log('LCU', `Champion changed: ${champId}`);
                }
            } else {
                this.lastChampionId = null;
            }
        }, 3000);
    }
}

module.exports = new LcuService();
