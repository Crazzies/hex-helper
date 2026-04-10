# HEX-helper 开发者维护手册

## 1. 核心架构
项目采用 **Electron 主进程 (Main)** 驱动后台逻辑，**渲染进程 (Renderer)** 呈现透明悬浮 UI。

### 数据流向：
1. **状态监听**：`lcu-service` 轮询 LCU API，感应游戏阶段（Phase）和英雄 ID。
2. **数据路由**：`index.js` 根据阶段切换视图，并调用 `data-service` 请求攻略。
3. **攻略获取**：`data-service` 优先查缓存，失效则启动 `scraper-service` 进行 DOM 抓取。
4. **分类与清洗**：`scraper-service` 抓取后，根据 `src/main/augments_tier_map.json` 进行品阶分类，并清洗冗余后缀。

## 2. 关键维护任务

### 更新英雄胜率库
应用启动时会自动执行 `scrapeAllHeroWinRates` 进行静默更新。如果需要强制更新，可以：
- 在设置面板点击“清理本地抓取缓存”。
- 或者删除 `%APPDATA%\HexHelper\hex_data_online.json`。

### 更新海克斯品阶映射 (`src/main/augments_tier_map.json`)
当游戏版本大更新引入全新海克斯时，需手动更新此文件以保证 UI 分类正确：
1. 运行 `init-tier-map.js` (在开发环境下)。
2. 将生成的新 JSON 覆盖 `src/main/augments_tier_map.json`。

## 3. 生产环境资源定位
由于打包后代码运行在 `.asar` 内部，所有文件读取遵循以下原则：
- **只读静态资源**：使用 `require('../file.json')` 加载，确保打包时资源被内联。
- **动态可写数据**：统一使用 `app.getPath('userData')` 获取系统的 AppData 目录，避免权限问题。

## 4. 爬虫适配指南
如果 `hextech.dtodo.cn` 发生改版，重点关注 `scraper-service.js` 中的 `executeJavaScript` 块：
- **情境装备**：当前逻辑为抓取“情境装备”或“装备配置”标题后的 `img` 列表，并取索引 `9-21`。
- **海克斯胜率**：正则匹配 `/(?:胜率|WR).*?(\d+\.?\d*)%/i`。
