# NIVI｜AI 主播陪练

**开播前，先练一次。**

NIVI 是面向个人主播与新人主播的 AI 模拟训练工具。用户可以在正式开播前练习内容表达、观众互动和临场应对，练习后查看带时间点的反馈，并针对具体问题立即重练。

项目覆盖带货、娱乐互动和知识内容等直播场景，提供完整模拟直播、难点练习和教程学习三个入口。

> 当前为邀请测试版，支持下载后在本地运行。仓库包含前后端源码、前端构建文件、内容库和自动测试。完整 AI 功能需要自行配置 DeepSeek 与腾讯云实时语音识别服务。

## 核心功能

| 功能 | 说明 |
| --- | --- |
| 完整模拟直播 | 选择直播类型与训练目标，可补充主题、商品资料或脚本 |
| 实时语音转写 | 通过腾讯云实时语音识别，将主播发言转换为文字 |
| 动态模拟弹幕 | 结合预设训练场景和近期发言，生成追问、质疑、互动回应及环境弹幕 |
| 难点练习 | 针对表达、互动或应对中的具体问题开展专项训练 |
| 训练反馈 | 根据转写与互动记录提供带时间点的反馈和改进建议 |
| 回放与重练 | 查看视频或音频回放，针对问题重练并对比前后表现 |
| 教程学习 | 查看内置教程，保存学习进度，并从相关教程进入练习 |
| 成长记录 | 查看历史训练、互动统计和学习进度 |
| 邀请登录 | 使用昵称与邀请码登录，训练记录按账号隔离 |
| 管理员看板 | 使用独立管理员口令查看使用情况与训练漏斗 |

麦克风是语音训练的必需设备，摄像头可选。关闭摄像头时，可以进行音频训练并保存音频回放。

当前版本服务个人主播，不包含机构成员管理、训练任务分配或机构考核功能。

## AI 如何参与训练

训练过程由以下环节组成：

1. **创建练习**：选择直播类型与目标，可补充主题、商品资料或脚本。
2. **实时转写**：浏览器将音频发送到后端，由腾讯云实时识别主播发言。
3. **模拟互动**：结合预设训练场景、环境弹幕和主播近期发言安排模拟观众回应。
4. **生成反馈**：结合转写、互动记录和内容库规则，定位值得改进的问题。
5. **继续训练**：回看片段、查看相关教程，或直接进入重练并比较表现。

所有观众互动均为模拟。AI 反馈用于辅助练习，不代表真实直播效果或上播资格评定；缺少商品资料时，也不能据此核实商品事实。

## 快速开始

### 1. 准备环境

- Python 3.12 或更高版本。
- [uv](https://docs.astral.sh/uv/getting-started/installation/) Python 依赖管理工具。
- Chrome 或 Edge 浏览器。
- 可用的麦克风，摄像头按需准备。
- 自己的 DeepSeek API 密钥与腾讯云实时语音识别配置。

修改或重新构建前端时，需要 Node.js 20 或更高版本。

**仓库已附带前端构建文件，直接运行时不需要先安装前端依赖。**

### 2. 下载项目

```bash
git clone https://github.com/khu016/ai-live-coach-workspace.git
cd ai-live-coach-workspace
```

也可以点击仓库页面的 **Code → Download ZIP**，解压后在项目根目录打开终端。

后续命令均以仓库根目录为起点，另有说明的除外。

### 3. 创建配置文件

将 `.env.example` 复制为 `.env`。

macOS / Linux：

```bash
cp .env.example .env
```

Windows PowerShell：

```powershell
Copy-Item .env.example .env
```

打开 `.env`，填写以下配置。其他配置可先保留模板默认值。

```dotenv
# 大模型服务
MODEL_PROVIDER=deepseek
MODEL_NAME=deepseek-chat
MODEL_BASE_URL=https://api.deepseek.com/v1
MODEL_API_KEY=替换为自己的DeepSeek密钥

# 腾讯云实时语音识别
ASR_PROVIDER=tencent_realtime
TENCENT_ASR_APPID=替换为自己的腾讯云APPID
TENCENT_ASR_SECRET_ID=替换为自己的腾讯云SecretId
TENCENT_ASR_SECRET_KEY=替换为自己的腾讯云SecretKey

# 主播登录
INVITE_CODES=替换为自己设置的邀请码
SESSION_COOKIE_SECURE=false

# 管理员看板，可按需配置
ADMIN_ACCESS_CODE=替换为独立的管理员口令
```

配置说明：

- `INVITE_CODES` 支持多个邀请码，使用英文逗号分隔；登录时填写其中一个。
- 管理员口令应与主播邀请码不同。不使用管理员看板时，可留空。
- 本地 HTTP 运行时使用 `SESSION_COOKIE_SECURE=false`；公网 HTTPS 部署时应设为 `true`。
- 模型与语音服务需要自行开通并保持可用额度，调用可能产生费用。
- `.env` 包含敏感配置，只保存在本地，不要提交到仓库。

### 4. 启动服务

#### macOS / Linux

```bash
bash scripts/start_nivi_full.sh
```

脚本会安装锁定版本的依赖、检查必要配置，并启动后端与已构建的前端页面。

也可以手动启动：

```bash
uv sync --frozen
PYTHONPATH=backend uv run uvicorn app.main:app --host 127.0.0.1 --port 8001
```

#### Windows PowerShell

```powershell
uv sync --frozen
$env:PYTHONPATH = "backend"
uv run uvicorn app.main:app --host 127.0.0.1 --port 8001
```

### 5. 打开与体验

浏览器访问：

**http://127.0.0.1:8001**

输入昵称和自己配置的邀请码登录，选择“完整模拟直播”或“难点练习”，并允许浏览器使用麦克风。

建议首次体验按以下顺序进行：

1. 创建一次练习，选择直播类型和目标。
2. 检测麦克风，按需开启摄像头。
3. 开始讲话，观察实时转写和模拟弹幕。
4. 结束练习，查看回放与训练反馈。
5. 选择一个问题重练，查看前后对比。

终端按 `Ctrl+C` 停止服务。

| 入口 | 地址 |
| --- | --- |
| 产品首页 | http://127.0.0.1:8001 |
| 接口文档 | http://127.0.0.1:8001/docs |
| 管理员看板 | http://127.0.0.1:8001/admin/analytics |

以上地址仅供运行项目的电脑访问，不是公开体验链接。首次运行会创建新的数据库，不包含作者的历史练习、账号会话或私人录像。

## 前端开发

前端使用 React、Vite 和 TypeScript，源代码位于 `frontend/`。

保持后端运行，在另一个终端执行：

```bash
cd frontend
npm ci
npm run dev
```

打开 **http://localhost:5174** 进行开发联调。

Vite 默认将 `/api` 请求及实时 WebSocket 代理到 `http://127.0.0.1:8001`。需要连接其他后端地址时，可配置 `VITE_PROXY_TARGET`。

### 类型检查

在 `frontend/` 目录执行：

```bash
npm run typecheck
```

### 构建页面

在 `frontend/` 目录执行：

```bash
npm run build
```

该命令会先进行类型检查，再将前端构建到：

```text
backend/app/static/
```

构建完成后，刷新 **http://127.0.0.1:8001** 即可查看最新页面。

macOS / Linux 也可以在仓库根目录执行以下命令，重新构建并启动：

```bash
NIVI_REBUILD_FRONTEND=1 bash scripts/start_nivi_full.sh
```

## 测试与验证

在仓库根目录执行：

```bash
uv sync --frozen
uv run pytest backend/tests
```

自动测试使用临时数据库与模拟服务，覆盖登录、数据隔离、训练流程、互动逻辑、反馈和统计等行为。

截至 **2026-10-15**，本次同步版本的验证结果为：

- 前端类型检查通过。
- 前端生产构建通过。
- 按依赖锁文件创建新环境成功。
- 161 项后端自动测试通过。

自动测试通过不等于真实服务的端到端体验已验收。麦克风采集、腾讯云实时识别、模型响应及完整训练流程，仍需在配置好服务后实际验证。本次同步未重新执行真实服务的完整端到端验收。

## 技术结构

| 层级 | 实现 |
| --- | --- |
| 前端 | React、TypeScript、Vite、React Router |
| 后端 | Python、FastAPI |
| 数据存储 | SQLite、SQLAlchemy |
| 实时通信 | WebSocket |
| 语音识别 | 腾讯云实时语音识别 |
| 大模型 | DeepSeek |
| 音视频采集 | 浏览器 MediaRecorder |
| 内容依据 | 随项目发布的场景卡、教学规则与教程 |
| 依赖管理 | uv、npm |

前端负责设备采集、训练交互和结果展示；后端负责账号隔离、实时语音接入、弹幕调度、反馈生成和数据持久化。

内容库通过内存索引与规则筛选加载，当前未使用向量检索。

## 内容库

内容库位于：

```text
backend/app/data/content_library/
```

主要包括：

- 训练场景卡与刁难场景。
- 环境弹幕。
- 教学规则与反馈依据。
- 教程内容。
- 来源登记与内容清单。

内容库随后端发布，不依赖作者电脑上的外部路径。部分内容为依据公开资料整理的编辑稿，人工审核与使用授权状态应以内容库中的记录为准，不应将其描述为已经验证的真实直播原句。

## 数据与配置

- 默认运行数据保存在项目根目录的 `data/` 中，包括 SQLite 数据库和训练媒体。
- 可通过 `.env` 中的 `DATA_DIR` 调整数据目录。
- 训练、反馈、录像和学习进度按登录账号隔离。
- `.env`、运行数据库、私人录像、虚拟环境和缓存不纳入版本管理。
- 仓库中的 `frontend/public/video-demo/` 为演示用合成语音素材，不是用户训练数据。
- `backend/scripts/merge_nivi_data.py` 是离线维护工具，正常安装和启动无需执行。
- 公网部署需要另外配置 HTTPS、服务运行环境与访问控制；本 README 的启动方式面向本地体验。

## 目录结构

```text
ai-live-coach-workspace/
├── README.md
├── AGENTS.md
├── .env.example
├── .gitignore
├── .python-version
├── pyproject.toml
├── uv.lock
├── backend/
│   ├── app/
│   │   ├── api/                  # HTTP 与实时接口
│   │   ├── core/                 # 配置
│   │   ├── data/content_library/ # 场景、规则与教程
│   │   ├── models/               # 数据模型
│   │   ├── schemas/              # 接口数据结构
│   │   ├── services/             # 训练、弹幕、反馈等业务逻辑
│   │   └── static/               # 已构建的前端页面
│   ├── scripts/                  # 验证与维护工具
│   └── tests/                    # 后端自动测试
├── frontend/                     # React 前端源码
├── scripts/
│   └── start_nivi_full.sh         # 本地启动入口
├── data/                         # 运行时生成，不提交
└── docs/                         # 产品文档、阶段记录与证据
```

## 常见问题

### 下载后能直接使用吗？

需要先安装运行环境并填写 `.env`。仓库已附带前端构建文件，无需先构建页面，但完整 AI 训练需要自己的模型与语音服务配置。

### 邀请码从哪里获取？

本地部署时，由运行者在 `.env` 的 `INVITE_CODES` 中自行设置。保存配置并重启服务后，使用该邀请码登录。

### 为什么能打开页面，却没有实时转写或 AI 反馈？

页面运行与外部 AI 服务调用是不同环节。请检查 `.env` 中的密钥、服务开通情况、可用额度和网络连接，再查看后端终端的报错信息。

默认真实语音配置应为：

```dotenv
ASR_PROVIDER=tencent_realtime
```

`mock` 用于开发测试，不能替代真实语音识别体验。

### 为什么修改页面后，8001 端口的页面没有变化？

8001 端口提供的是构建后的页面。在 `frontend/` 目录执行 `npm run build` 后刷新，或使用 5174 端口进行开发联调。

### 为什么首次打开没有历史记录？

仓库不包含作者的个人数据。首次运行从空数据库开始，完成训练后会逐步生成自己的记录与统计。

### 能把本地地址直接发给别人体验吗？

不能。`127.0.0.1` 指向访问者自己的电脑。对方可以下载项目并自行运行；如果希望通过一个网址直接体验，需要另外部署公网服务。

## 项目文档

进一步了解产品范围、设计依据与开发历史，可查看：

- [产品需求文档 v1.8](https://github.com/khu016/ai-live-coach-workspace/blob/main/docs/PRD/AI主播陪练_PRD_v1.8.md)
- [项目状态与决策记录](https://github.com/khu016/ai-live-coach-workspace/blob/main/docs/项目状态.md)
- [PRD 补全清单](https://github.com/khu016/ai-live-coach-workspace/blob/main/docs/阶段文档/PRD补全清单.md)
- [第一阶段技术适配声明](https://github.com/khu016/ai-live-coach-workspace/blob/main/docs/阶段文档/第一阶段技术适配声明.md)
- [第一阶段技术开发文档](https://github.com/khu016/ai-live-coach-workspace/blob/main/docs/阶段文档/第一阶段技术开发文档.md)

阶段文档保留历史设计与决策背景，当前安装方式以本 README 和仓库配置为准。

## 更新记录

### 2026-10-15 · 本地完整版同步

代码提交：[`cea3a17`](https://github.com/khu016/ai-live-coach-workspace/commit/cea3a17)

本次将本地正在使用的完整前后端同步至仓库，并完善下载后的运行流程。

**界面与运行**

- 加入 NIVI 品牌启动页及配套样式。
- 统一仓库前后端目录，移除对本机预览目录结构的依赖。
- 新增可移植启动脚本，补充配置模板与安装说明。
- 重新构建前端页面，使仓库附带页面与本次源码一致。

**训练与反馈**

- 增加语音活动判断，改进持续讲话时的冷场判定。
- 改进中文数字、中文选项及多意图互动号召的识别与回应。
- 调整弹幕展示时间与统计逻辑，避免将未展示弹幕作为未回应证据。
- 加入反馈过滤，减少将偏好问句误判为未经核实商品承诺的情况。
- 调整不同直播类型的反馈提示，减少知识场景套用商品模板的问题。

**验证**

- 补充相关回归测试。
- 前端类型检查与生产构建通过。
- 新安装环境中，161 项后端自动测试通过。
- 真实语音与模型服务的完整流程仍需结合实际配置进行体验验收。
