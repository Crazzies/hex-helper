# HEX-helper (英雄联盟海克斯大乱斗辅助工具)

一款面向《英雄联盟》极地大乱斗（ARAM）及海克斯大乱斗模式的实时数据辅助工具。

![CI](https://github.com/Crazzies/hex-helper/actions/workflows/ci.yml/badge.svg)

## 🌟 核心特性
- **数据自动进化**：应用启动后自动后台同步全量英雄胜率，尽量保持数据最新。
- **实时阶段感应**：选人阶段显示“备战席胜率列表”，进入对局显示“锁定英雄攻略”。
- **队友一览**：选人阶段显示队友英雄并按胜率排序，便于快速判断阵容。
- **海克斯分类**：基于本地映射库归类棱彩/金色/银色，并过滤无效数据。
- **智能出装推荐**：抓取情境装备与海克斯推荐，减少手动查找时间。
- **自定义交互**：
  - 托盘常驻、显示/隐藏窗口。
  - 支持透明度、UI 缩放、点击穿透。
  - 支持全局快捷键 `Alt+V`（可改）。
  - 支持日志查看、查看日志目录、清理缓存。

## 🚀 快速开始（普通用户）
1. 打开 Releases 页面并下载最新 `HexHelper.exe`。
2. 双击运行（首次可能有系统安全提示）。
3. 进入 LOL 客户端后，工具会自动识别阶段并更新视图。

Releases: https://github.com/Crazzies/hex-helper/releases

## 📦 分发给朋友怎么用
- 直接发 `HexHelper.exe` 即可（无需安装）。
- 推荐让朋友从 Releases 下载，方便拿到对应版本和校验文件。
- 如朋友遇到“未知发布者”提示，按系统提示继续运行即可（或加入信任）。

## ✅ 运行前提
- Windows x64
- 本地已安装并运行 LOL 客户端
- 允许程序在 `%APPDATA%` 写入配置与日志

## 🧭 托盘菜单
- 显示/隐藏窗口
- 打开设置面板
- 重置位置
- 查看日志（日志内容）
- 查看日志目录（直接打开日志文件夹）
- 退出程序

## 🛠 技术维护
- **配置与缓存路径**：`%APPDATA%\HexHelper\`
- **日志路径**：`%APPDATA%\HexHelper\logs\app-YYYYMMDD-HHMMSS.log`
- **日志策略**：可在设置中调整保留天数与最大文件数
- **缓存刷新**：设置中点击“清理本地抓取缓存”

## 📁 项目结构（整理后）
- **生产代码**：`src/`
- **历史原型**：`legacy/prototype-electron/`
- **研发脚本**：`tools/research/`
- **旧版测试脚本**：`tools/legacy-tests/`

当前运行入口为 `src/main/index.js`，打包内容由 `package.json` 的 `build.files` 控制。

## 👨‍💻 开发与打包
```bash
npm ci
npm run build:win:linux
```

打包产物：`dist/HexHelper.exe`
