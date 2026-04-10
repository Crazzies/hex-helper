/**
 * LCU (League Client Update) 通信服务
 * 负责提取游戏客户端端口与认证令牌，并监听游戏阶段与英雄选择变化。
 */
const { execFile } = require('child_process');
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
        this.pollBusy = false;
        this.connectBusy = false;

        this.pollIntervalMs = 3000;
        this.minReconnectMs = 3000;
        this.maxReconnectMs = 15000;
        this.reconnectDelayMs = this.minReconnectMs;
        this.nextConnectAt = 0;
    }

    parseLcuCommandLine(stdout) {
        if (!stdout) return null;
        const portMatch = stdout.match(/--app-port=(\d+)/);
        const tokenMatch = stdout.match(/--remoting-auth-token=([\w-]+)/);
        if (!portMatch || !tokenMatch) return null;
        return {
            port: portMatch[1],
            auth: Buffer.from(`riot:${tokenMatch[1]}`).toString('base64')
        };
    }

    execCommand(file, args, timeout = 1500) {
        return new Promise(resolve => {
            execFile(
                file,
                args,
                {
                    windowsHide: true,
                    timeout,
                    maxBuffer: 1024 * 1024
                },
                (error, stdout) => {
                    if (error || !stdout) {
                        resolve('');
                        return;
                    }
                    resolve(stdout.toString());
                }
            );
        });
    }

    async queryLeagueCommandLine() {
        // 优先 PowerShell (新系统更稳定)，失败时回退 WMIC。
        const psScript = "$p = Get-CimInstance Win32_Process -Filter \"name='LeagueClientUx.exe'\" | Select-Object -ExpandProperty CommandLine; if ($p) { $p }";
        const fromPowerShell = await this.execCommand('powershell.exe', ['-NoProfile', '-NonInteractive', '-Command', psScript]);
        if (fromPowerShell && fromPowerShell.includes('--app-port=')) {
            return fromPowerShell;
        }
        return this.execCommand('cmd.exe', ['/d', '/s', '/c', 'wmic process where name="LeagueClientUx.exe" get commandline']);
    }

    markDisconnected(reason = '') {
        if (!this.lcuData) return;
        this.lcuData = null;
        this.lastChampionId = null;
        if (reason) log('LCU', `Disconnected: ${reason}`);
        else log('LCU', 'Disconnected.');
        this.emit('disconnected');
    }

    /**
     * 异步获取 LCU 连接凭证，避免阻塞 Electron 主线程。
     */
    async connect() {
        if (process.platform !== 'win32') return false;
        if (this.connectBusy) return !!this.lcuData;

        this.connectBusy = true;
        try {
            const stdout = await this.queryLeagueCommandLine();
            const newData = this.parseLcuCommandLine(stdout);
            if (!newData) {
                this.markDisconnected('League Client not found');
                return false;
            }

            const changed =
                !this.lcuData ||
                this.lcuData.port !== newData.port ||
                this.lcuData.auth !== newData.auth;

            this.lcuData = newData;
            this.reconnectDelayMs = this.minReconnectMs;
            this.nextConnectAt = 0;

            if (changed) {
                log('LCU', 'Connected to League Client.');
                this.emit('connected', this.lcuData);
            }
            return true;
        } catch (e) {
            this.markDisconnected(e.message);
            return false;
        } finally {
            this.connectBusy = false;
        }
    }

    /**
     * 发送 HTTPS 请求到 LCU 本地 API
     */
    async request(url) {
        if (!this.lcuData) return null;
        return new Promise((resolve) => {
            let settled = false;
            const done = (value) => {
                if (settled) return;
                settled = true;
                resolve(value);
            };

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
                    if (res.statusCode && res.statusCode >= 400) {
                        log('LCU', `Request failed ${res.statusCode} for ${url}`);
                        done(null);
                        return;
                    }
                    try {
                        done(JSON.parse(data));
                    } catch (e) {
                        log('LCU', `JSON parse error for ${url}: ${e.message}`);
                        done(null);
                    }
                });
            });

            req.setTimeout(1500, () => {
                req.destroy(new Error('timeout'));
            });
            req.on('error', () => done(null));
            req.end();
        });
    }

    async pollTick() {
        if (this.pollBusy) return;
        this.pollBusy = true;
        try {
            if (!this.lcuData) {
                const now = Date.now();
                if (now < this.nextConnectAt) return;
                const connected = await this.connect();
                if (!connected) {
                    this.nextConnectAt = now + this.reconnectDelayMs;
                    this.reconnectDelayMs = Math.min(this.reconnectDelayMs * 2, this.maxReconnectMs);
                    return;
                }
            }

            // 1. 监听游戏流阶段 (Lobby -> ChampSelect -> InProgress)
            const phaseRaw = await this.request('/lol-gameflow/v1/gameflow-phase');
            const phase = typeof phaseRaw === 'string' ? phaseRaw : (phaseRaw?.phase || null);
            if (!phase) {
                this.markDisconnected('LCU request failed');
                this.nextConnectAt = Date.now() + this.minReconnectMs;
                this.reconnectDelayMs = this.minReconnectMs;
                return;
            }

            if (phase !== this.lastPhase) {
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
        } finally {
            this.pollBusy = false;
        }
    }

    /**
     * 开启心跳轮询，监听阶段切换与英雄选择。
     */
    startPolling() {
        if (this.pollTimer) return;
        this.pollTimer = setInterval(() => {
            this.pollTick();
        }, this.pollIntervalMs);
        this.pollTick();
    }
}

module.exports = new LcuService();
