/**
 * LCU (League Client Update) 通信服务
 * 负责通过命令行提取游戏客户端的端口与认证令牌，并监听游戏阶段与英雄选择变化。
 */
const { execSync } = require('child_process');
const https = require('https');
const EventEmitter = require('events');
const { log } = require('../utils/logger');

class LcuService extends EventEmitter {
    constructor() {
        super();
        this.lcuData = null;
        this.agent = new https.Agent({ rejectUnauthorized: false }); // 忽略 LCU 自签名证书错误
        this.lastPhase = null;
        this.lastChampionId = null;
        this.pollTimer = null;
    }

    /**
     * 自动通过命令行提取 LCU 连接凭证
     * 原理：LeagueClientUx.exe 启动时会在命令行参数中包含 --app-port 和 --remoting-auth-token
     */
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

    /**
     * 发送 HTTPS 请求到 LCU 本地 API
     */
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

    /**
     * 开启心跳轮询，监听阶段切换与英雄选择
     */
    startPolling() {
        if (this.pollTimer) return;
        this.pollTimer = setInterval(async () => {
            const connected = await this.connect();
            if (!connected) return;

            // 1. 监听游戏流阶段 (Lobby -> ChampSelect -> InProgress)
            const phase = await this.request('/lol-gameflow/v1/gameflow-phase');
            if (phase && phase !== this.lastPhase) {
                this.lastPhase = phase;
                this.emit('phase-changed', phase);
                log('LCU', `Phase changed: ${phase}`);
            }

            // 2. 监听玩家当前正在查看/选择的英雄 ID
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
        }, 3000); // 3秒/次的心跳检测，在性能与实时性间取得平衡
    }
}

module.exports = new LcuService();
