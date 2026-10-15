# NIVI｜AI 主播陪练

**NIVI** 是一款面向个人主播的 AI 开播前陪练产品，帮助新人主播练习表达、互动与直播应对。本仓库是 NIVI 的独立项目目录，项目文件路径均以本目录为基准，不以外层工具包根目录为基准。

**当前阶段**：邀请测试版（PRD v1.8）已完成账号、权限、第一方埋点与管理员数据看板。真实邀请码登录、个人数据隔离和实时语音连接鉴权均已实现；等待公网部署环境验收。第一版范围已收敛为个人主播 MVP，机构端为后续版本、不开发。

## 产品一句话
个人主播（第一版）在开播前，用摄像头和麦克风进入模拟直播间练习表达与互动（预设关键问题 + 动态 AI 弹幕），练后得到带时间点证据的反馈，并能立即重练、对比前后进步。直播机构为后续版本，第一版不开发机构端功能与页面。

## 第一版范围（v1.8）
- **第一版保留（个人主播闭环）**：邀请码与昵称登录、个人数据隔离、创建训练、自由选择先看教程或直接练习、单项难点练习、完整模拟直播、摄像头和麦克风训练、腾讯云实时语音转写、按主播发言动态生成模拟弹幕、必考/刁难/无关/路人/噪声弹幕、录像回看、有具体依据的 AI 反馈、每次指出 1–2 个优先问题、立即重练、个人成长记录、调试标签（默认关闭）。
- **移至“后续版本规划”**：机构账号和机构登录、机构工作台、主播成员管理、分配训练任务、机构上传/管理培训内容、机构查看旗下主播录像、机构查看成长记录、机构配置考核项、带教老师上播审批、机构权限和角色管理、所有机构端前端页面。

## 当前代码同步（2026-10-15）

已同步本机完整版的品牌启动页、互动弹幕与冷场判定修复、反馈证据过滤、统计与回归测试。仓库统一使用 `frontend/` 和 `backend/`，不要求本机预览目录结构。`frontend/public/video-demo/` 为演示用合成语音素材，不是用户训练数据。`backend/scripts/merge_nivi_data.py` 为离线维护工具，正常运行不需要执行。

## 阅读入口
- [PRD v1.8](docs/PRD/AI主播陪练_PRD_v1.8.md)：邀请测试数据埋点与管理员看板（唯一权威版本；v1.7 及更早版本保留作历史）。
- [项目状态](docs/项目状态.md)：决策台账、待确认问题与阶段历史。
- [PRD 补全清单](docs/阶段文档/PRD补全清单.md)：阶段 0 体检产出（已关闭）。
- [技术适配声明](docs/阶段文档/第一阶段技术适配声明.md)：阶段 1 产出（已确认）。
- [第一阶段技术开发文档](docs/阶段文档/第一阶段技术开发文档.md)：阶段 2 开发依据。

## 本地运行

### 环境要求
- Python 3.12 或更高版本，以及 [uv](https://docs.astral.sh/uv/getting-started/installation/)。
- Chrome / Edge；练习需要麦克风，摄像头可选。
- 修改或重新构建页面需要 Node.js 20 或更高版本；仓库已附带当前前端构建产物。

### 下载与配置

下载并解压本仓库，或运行：

```bash
git clone https://github.com/khu016/ai-live-coach-workspace.git
cd ai-live-coach-workspace
cp .env.example .env
```

编辑根目录 `.env`，填写自己的 `MODEL_API_KEY`、腾讯云 `TENCENT_ASR_APPID` / `TENCENT_ASR_SECRET_ID` / `TENCENT_ASR_SECRET_KEY`，以及自定义 `INVITE_CODES`。需要管理员看板时另外设置 `ADMIN_ACCESS_CODE`。本地 HTTP 使用 `SESSION_COOKIE_SECURE=false`。

默认语音识别为腾讯云实时识别。模型与语音服务需要使用者自己的账号与有效额度，可能产生服务费用。仓库不包含作者的密钥、账号会话、历史练习或私人录像；首次运行会创建空数据库。登录时输入自己在 `.env` 设置的邀请码。

### 启动完整产品（一个链接）

macOS / Linux / Git Bash 在仓库根目录运行：

```bash
bash scripts/start_nivi_full.sh
```

或者手动启动（PowerShell 的环境变量语法见下方）：

```bash
uv sync --frozen
PYTHONPATH=backend uv run uvicorn app.main:app --host 127.0.0.1 --port 8001
```

PowerShell：

```powershell
$env:PYTHONPATH = "backend"
uv run uvicorn app.main:app --host 127.0.0.1 --port 8001
```

浏览器打开 **http://127.0.0.1:8001**，使用同一地址完成登录、教程、训练、反馈和成长记录。接口文档为 `/docs`，管理员看板为 `/admin/analytics`。这是运行者电脑的本地地址，不是公网体验链接。

### 前端开发与构建

保持后端运行，在另一个终端执行：

```bash
cd frontend
npm ci
npm run dev
```

开发入口为 **http://localhost:5174**，API 与 WebSocket 默认代理到 `127.0.0.1:8001`。可通过 `VITE_PROXY_TARGET` 调整后端地址。

前端修改后运行 `npm run build`，会将页面重新构建到 `backend/app/static/`，更新 8001 地址提供的页面。也可在仓库根目录执行 `NIVI_REBUILD_FRONTEND=1 bash scripts/start_nivi_full.sh`。

### 运行测试

```bash
uv run pytest backend/tests
```

自动测试使用隔离的临时数据库与模拟服务，不会证明真实麦克风、腾讯云和模型服务端到端可用；这些需要使用配置好的服务另行验收。

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
INVITE_CODES=<用英文逗号分隔的高强度邀请码>
SESSION_COOKIE_SECURE=false          # 本地为 false；公网 HTTPS 部署为 true
ADMIN_ACCESS_CODE=<独立的高强度管理员口令>
```
填好后重启服务即可跑真实模型冒烟。未填 Key 时相关流程会如实标注/报错，不冒充真实效果。

## 前端（React）

正式 React 前端位于 `frontend/`。邀请登录使用服务端 HttpOnly 会话；训练、录像、报告、统计、教程进度与实时语音连接均按当前账号隔离。完整模拟直播与难点练习共用真实训练链路：创建练习、摄像头（可选）/麦克风（必需）、PCM 16kHz WebSocket 实时转写、动态弹幕、互动号召回应、MediaRecorder 录像（视频或音频）上传、真实反馈报告与重练对比。首页（本周训练/互动节奏）、成长记录、录像管理均读取后端真实数据，样本不足时显示"数据不足"。教程中心的 9 节微课由后端内容库统一提供，学习状态保存到数据库；训练报告会按实际问题推荐教程，教程可直接进入对应难点练习，成长页显示真实学习进度。教程初稿依据项目规则卡整理并标记为待老师复核。除账号昵称外，个人资料中的设备偏好仍为浏览器内状态。

技术栈：React + Vite + TypeScript + React Router + Lucide React + 普通 CSS（设计变量见 `src/styles/index.css`）。

```bash
cd frontend
npm install
npm run dev        # http://localhost:5174
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
- 本仓库为独立产品仓库，所有运行路径均以仓库根目录为基准。

## 目录约定
```text
ai-live-coach-workspace/
├── README.md / AGENTS.md / .gitignore / .env.example / pyproject.toml / uv.lock / .python-version
├── backend/
│   ├── app/           # FastAPI：api/ core/ models/ schemas/ services/ static/
│   └── tests/         # pytest mock 测试
├── frontend/          # React + Vite + TS 正式前端（核心训练闭环已接后端）
├── data/              # SQLite 数据库与录像（gitignore）
└── docs/              # PRD、阶段文档、证据、项目状态
```
