# AI 主播陪练

AI 主播陪练 Agent 的独立项目目录。项目文件路径均以本目录为基准，不以外层工具包根目录为基准。

**当前阶段**：阶段 2 后端 MVP（第二阶段·实时语音转写驱动动态弹幕）已完成；必考轮换、环境弹幕、统一调度、评分过滤与调试标签已实现，D2/D3 已定线。第一版范围已收敛为个人主播 MVP（PRD v1.5），机构端为后续版本、不开发。

## 产品一句话
个人主播（第一版）在开播前，用摄像头和麦克风进入模拟直播间练习表达与互动（预设关键问题 + 动态 AI 弹幕），练后得到带时间点证据的反馈，并能立即重练、对比前后进步。直播机构为后续版本，第一版不开发机构端功能与页面。

## 第一版范围（v1.5）
- **第一版保留（个人主播闭环）**：创建训练、自由选择先看教程或直接练习、单项难点练习、完整模拟直播、摄像头和麦克风训练、腾讯云实时语音转写、按主播发言动态生成模拟弹幕、必考/刁难/无关/路人/噪声弹幕、录像回看、有具体依据的 AI 反馈、每次指出 1–2 个优先问题、立即重练、个人成长记录、调试标签（默认关闭）。
- **移至“后续版本规划”**：机构账号和机构登录、机构工作台、主播成员管理、分配训练任务、机构上传/管理培训内容、机构查看旗下主播录像、机构查看成长记录、机构配置考核项、带教老师上播审批、机构权限和角色管理、所有机构端前端页面。

## 阅读入口
- [PRD v1.5](docs/PRD/AI主播陪练_PRD_v1.5.md)：第一版范围收敛版（个人主播 MVP；唯一权威版本；v1.4/v1.3/v1.2/v1.1/v0.1 保留作历史）。
- [项目状态](docs/项目状态.md)：决策台账、待确认问题与阶段历史。
- [PRD 补全清单](docs/阶段文档/PRD补全清单.md)：阶段 0 体检产出（已关闭）。
- [技术适配声明](docs/阶段文档/第一阶段技术适配声明.md)：阶段 1 产出（已确认）。
- [第一阶段技术开发文档](docs/阶段文档/第一阶段技术开发文档.md)：阶段 2 开发依据。

## 本地运行

### 环境要求
- Python 3.12（项目用 uv 管理）；uv 已装到 `~/.local/bin/uv`，缺失时 `curl -LsSf https://astral.sh/uv/install.sh | sh`
- 最新版 Chrome / Edge（需摄像头、麦克风）

### 安装依赖
```bash
cd AI主播陪练开发
uv sync
```

### 启动
```bash
cd AI主播陪练开发
PYTHONPATH=backend uv run uvicorn app.main:app --host 127.0.0.1 --port 8001
```
浏览器打开 http://127.0.0.1:8001/ （验收页）。端口 8000 被其他项目占用，默认用 8001。

### 运行测试
```bash
cd AI主播陪练开发
uv run pytest      # 105 项 mock 测试
```

### 内容库
弹幕与反馈由内容库驱动。内容库文件位于 `backend/app/data/content_library/`
（`scenario_cards.jsonl` 84 张场景卡（含 30 张刁难）、`teaching_rules.jsonl` 20 张规则卡、
`ambient_bullets.jsonl` 90 张环境弹幕（无关/路人/噪声各 30）、`source_registry.json`、
`manifest.json`），随后端发布，不依赖外部绝对路径。
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

独立于后端验收页的正式 React 前端，位于 `frontend/`。当前阶段全部使用本地模拟数据（`src/data/mock.ts`），不连接真实接口；代码结构预留了后续接入 `/api/v1` 的边界。

技术栈：React + Vite + TypeScript + React Router + Lucide React + 普通 CSS（设计变量见 `src/styles/index.css`）。

```bash
cd AI主播陪练开发/frontend
npm install
npm run dev        # http://localhost:5173
npm run typecheck  # 类型检查
npm run build      # 类型检查 + 生产构建（dist/）
npm run preview    # 预览生产构建
```

页面路由：`/login` 登录 · `/` 首页 · `/tutorials` 教程中心 · `/practice/new` 创建练习与设备检测 · `/practice/live` 完整模拟直播 · `/practice/focus` 难点练习 · `/reports/:id` 训练报告 · `/practice/:id/compare` 重练对比 · `/growth` 成长记录 · `/recordings` 录像管理 · `/profile` 个人中心。

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
├── frontend/          # React + Vite + TS 正式前端（本地模拟数据）
├── data/              # SQLite 数据库与录像（gitignore）
└── docs/              # PRD、阶段文档、证据、项目状态
```
