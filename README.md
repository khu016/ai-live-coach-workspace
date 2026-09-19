# AI 主播陪练

AI 主播陪练 Agent 的独立项目目录。项目文件路径均以本目录为基准，不以外层工具包根目录为基准。

**当前阶段**：阶段 2 后端 MVP（第一阶段·最小纵向切片）已完成，D2/D3 已定线；下一步方向待定。

## 产品一句话
个人主播和直播机构在开播前，用摄像头和麦克风进入模拟直播间练习表达与互动（预设关键问题 + 动态 AI 弹幕），练后得到带时间点证据的反馈，并能立即重练、对比前后进步。AI 不自动判定能否上播，上播资格由带教老师人工判断。

## 阅读入口
- [PRD v0.1](docs/PRD/AI主播陪练_PRD_v0.1.md)：需求对齐版（唯一权威版本）。
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
uv run pytest      # 35 项 mock 测试
```

### 内容库
弹幕与反馈由内容库驱动。内容库文件位于 `backend/app/data/content_library/`
（`scenario_cards.jsonl` 60 张场景卡、`teaching_rules.jsonl` 20 张规则卡、
`source_registry.json`、`manifest.json`），随后端发布，不依赖外部绝对路径。
加载服务见 `backend/app/services/content_library.py`（内存索引筛选，无向量检索）。

### 接入真实模型（真实验收前）
在项目根目录建 `.env`（已 gitignore，可从 `.env.example` 复制），填：
```
MODEL_PROVIDER=deepseek
MODEL_NAME=deepseek-chat
MODEL_API_KEY=<你的 DeepSeek Key>
MODEL_BASE_URL=https://api.deepseek.com/v1
ASR_PROVIDER=mock        # 语音转写暂用 mock；接入讯飞后改为 xfyun 并填 ASR_API_KEY
```
填好后重启服务即可跑真实模型冒烟。未填 Key 时练后反馈会走到 `failed` 状态（如实标注，不冒充真实效果）。

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
├── data/              # SQLite 数据库与录像（gitignore）
└── docs/              # PRD、阶段文档、证据、项目状态
```
