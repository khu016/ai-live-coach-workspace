# NIVI｜AI 主播陪练

**NIVI** 是一款面向个人主播的 AI 开播前陪练产品，帮助新人主播练习表达、互动与直播应对。本仓库是 NIVI 的独立项目目录，项目文件路径均以本目录为基准，不以外层工具包根目录为基准。

**当前阶段**：阶段 3 增量修复（PRD v1.6）已完成。难点练习真实链路、摄像头可选/麦克风必需、音频回放、真实首页与成长数据、真实媒体列表与删除、互动号召识别与回应队列、互动回归评测均已实现；等待产品经理真实设备验收。第一版范围已收敛为个人主播 MVP，机构端为后续版本、不开发。

## 产品一句话
个人主播（第一版）在开播前，用摄像头和麦克风进入模拟直播间练习表达与互动（预设关键问题 + 动态 AI 弹幕），练后得到带时间点证据的反馈，并能立即重练、对比前后进步。直播机构为后续版本，第一版不开发机构端功能与页面。

## 第一版范围（v1.5）
- **第一版保留（个人主播闭环）**：创建训练、自由选择先看教程或直接练习、单项难点练习、完整模拟直播、摄像头和麦克风训练、腾讯云实时语音转写、按主播发言动态生成模拟弹幕、必考/刁难/无关/路人/噪声弹幕、录像回看、有具体依据的 AI 反馈、每次指出 1–2 个优先问题、立即重练、个人成长记录、调试标签（默认关闭）。
- **移至“后续版本规划”**：机构账号和机构登录、机构工作台、主播成员管理、分配训练任务、机构上传/管理培训内容、机构查看旗下主播录像、机构查看成长记录、机构配置考核项、带教老师上播审批、机构权限和角色管理、所有机构端前端页面。

## 阅读入口
- [PRD v1.6](docs/PRD/AI主播陪练_PRD_v1.6.md)：真实训练闭环与互动响应修复（唯一权威版本；v1.5/v1.4/v1.3/v1.2/v1.1/v0.1 保留作历史）。
- [项目状态](docs/项目状态.md)：决策台账、待确认问题与阶段历史。
- [PRD 补全清单](docs/阶段文档/PRD补全清单.md)：阶段 0 体检产出（已关闭）。
- [技术适配声明](docs/阶段文档/第一阶段技术适配声明.md)：阶段 1 产出（已确认）。
- [第一阶段技术开发文档](docs/阶段文档/第一阶段技术开发文档.md)：阶段 2 开发依据。

## 本地运行

### 环境要求
- Python 3.12（项目用 uv 管理）；uv 已装到 `~/.local/bin/uv`，缺失时 `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Node.js 20 或更高版本
- 最新版 Chrome / Edge（需摄像头、麦克风）

### 安装依赖
```bash
cd AI主播陪练开发
uv sync
cd frontend
npm install
```

### 启动完整产品（一个链接）

首次运行或前端有更新时先构建一次：

```bash
cd AI主播陪练开发/frontend
npm run build
```

随后启动后端：

```bash
cd AI主播陪练开发
PYTHONPATH=backend uv run uvicorn app.main:app --host 127.0.0.1 --port 8001
```

浏览器只需打开 **http://127.0.0.1:8001**。首页、教程、练习、报告和成长记录都由这一地址提供；接口文档为 http://127.0.0.1:8001/docs。教程详情等前端地址可以直接刷新，不会再与后端分离。

### 前端开发模式（修改页面时使用）

保持后端终端运行，在第二个终端运行：

```bash
cd AI主播陪练开发/frontend
npm run dev
```

浏览器打开 **http://localhost:5173**。Vite 会将 `/api` 和实时 WebSocket 请求代理到本机 8001 端口；开发完成后重新执行 `npm run build`，即可在统一的 8001 地址看到最新页面。

### 运行测试
```bash
cd AI主播陪练开发
uv run pytest      # 135 项测试（含教程接口、学习进度、报告推荐与统一入口）
```

### 内容库
弹幕与反馈由内容库驱动。内容库文件位于 `backend/app/data/content_library/`
（`scenario_cards.jsonl` 84 张场景卡（含 30 张刁难）、`teaching_rules.jsonl` 20 张规则卡、
`ambient_bullets.jsonl` 90 张环境弹幕（无关/路人/噪声各 30）、`source_registry.json`、
`manifest.json`、`tutorials.json` 9 节文字微课），随后端发布，不依赖外部绝对路径。
加载服务见 `backend/app/services/content_library.py`（内存索引筛选，无向量检索）；
环境弹幕与统一调度见 `backend/app/services/ambient_bullets.py`。

### 接入真实模型（真实验收前）
在项目根目录建 `.env`（已 gitignore，可从 `.env.example` 复制），填：
```
MODEL_PROVIDER=deepseek
MODEL_NAME=deepseek-chat
MODEL_API_KEY=<你的 DeepSeek Key>
MODEL_BASE_URL=https://api.deepseek.com/v1
ASR_PROVIDER=tencent_realtime        # mock | tencent_realtime（第一版主 ASR）
TENCENT_ASR_APPID=<腾讯云 APPID>
TENCENT_ASR_SECRET_ID=<腾讯云 SecretId>
TENCENT_ASR_SECRET_KEY=<腾讯云 SecretKey>
```
填好后重启服务即可跑真实模型冒烟。未填 Key 时相关流程会如实标注/报错，不冒充真实效果。

## 前端（React）

正式 React 前端位于 `frontend/`。完整模拟直播与难点练习共用真实训练链路：创建练习、摄像头（可选）/麦克风（必需）、PCM 16kHz WebSocket 实时转写、动态弹幕、互动号召回应、MediaRecorder 录像（视频或音频）上传、真实反馈报告与重练对比。首页（本周训练/互动节奏）、成长记录、录像管理均读取后端真实数据，样本不足时显示"数据不足"。教程中心的 9 节微课由后端内容库统一提供，学习状态保存到数据库；训练报告会按实际问题推荐教程，教程可直接进入对应难点练习，成长页显示真实学习进度。教程初稿依据项目规则卡整理并标记为待老师复核。个人资料与登录仍使用 `src/data/mock.ts` 中的模拟数据，已明确标记。

技术栈：React + Vite + TypeScript + React Router + Lucide React + 普通 CSS（设计变量见 `src/styles/index.css`）。

```bash
cd AI主播陪练开发/frontend
npm install
npm run dev        # http://localhost:5173
npm run typecheck  # 类型检查
npm run build      # 类型检查 + 生产构建（dist/）
npm run preview    # 预览生产构建
```

本地联调时先按上文启动 FastAPI（默认 `127.0.0.1:8001`），再启动 Vite。Vite 会把 `/api` 与 WebSocket 代理到后端；若隔离测试后端使用其他端口，可在启动前设置 `VITE_PROXY_TARGET`。

页面路由：`/login` 登录 · `/` 首页 · `/tutorials` 教程中心 · `/tutorials/:id` 教程详情 · `/practice/new` 创建练习与设备检测 · `/practice/live` 完整模拟直播/难点练习 · `/practice/focus` 难点练习（重定向到创建页） · `/reports/:id` 训练报告 · `/practice/:id/compare` 重练对比 · `/growth` 成长记录 · `/recordings` 录像管理 · `/profile` 个人中心。

## 媒体模式与互动号召
- 麦克风为语音训练必需，摄像头可选；摄像头关闭时只申请音频轨道、保存音频回放（`media_kind=audio`），报告页显示音频播放器。
- 互动号召（扣1/选A还是B/听懂的打个懂/报到/点赞/接龙/开放意见）由规则 + AI 两层识别，进入不可丢弃的待回应队列，2–6 秒内展示 2–4 条差异化回应；DeepSeek 不可用时用预设回应组降级。
- 新增接口：`GET /api/v1/stats/week`（真实周统计）、`GET /api/v1/recordings`（真实媒体列表）、`GET /api/v1/trainings/{id}/media`（媒体元数据）、`DELETE /api/v1/trainings/{id}`（删除）。

## 配置边界
- 本项目只用自己目录内的 `.env` 和 API Key；不从外层工具包或其他 Agent 项目隐式读取。
- `.env`、`.venv`、`data/`、`__pycache__` 均已 gitignore，不提交密钥与用户数据。
- 沿用外层 Git 仓库，本目录未初始化嵌套 Git 仓库。

## 目录约定
```text
AI主播陪练开发/
├── README.md / AGENTS.md / .gitignore / .env.example / pyproject.toml / uv.lock / .python-version
├── backend/
│   ├── app/           # FastAPI：api/ core/ models/ schemas/ services/ static/
│   └── tests/         # pytest mock 测试
├── frontend/          # React + Vite + TS 正式前端（核心训练闭环已接后端）
├── data/              # SQLite 数据库与录像（gitignore）
└── docs/              # PRD、阶段文档、证据、项目状态
```
