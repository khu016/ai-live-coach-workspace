// ============================================================
// 集中管理的本地模拟数据
// 结构清晰，方便以后替换为真实接口（对应后端 /api/v1）
// ============================================================

export type LiveType = '带货' | '娱乐互动' | '知识内容'
export type PracticeMode = 'full' | 'focus'
export type BulletCategory = '必考' | '刁难' | '无关' | '路人' | '噪声' | '追问' | '话题'

export const LIVE_TYPES: LiveType[] = ['带货', '娱乐互动', '知识内容']

export interface UserProfile {
  nickname: string
  phone: string
  primaryLiveType: LiveType
  experience: string
  defaultCamera: string
  defaultMic: string
  saveRecording: boolean
  recordingVisibleToSelfOnly: boolean
  notifyOnInsight: boolean
}

export interface PracticeRecord {
  id: string
  goal: string
  liveType: LiveType
  mode: PracticeMode
  date: string
  durationMin: number
  score: number | null
  topIssueCount: number
}

export interface Recording {
  id: string
  title: string
  liveType: LiveType
  date: string
  durationMin: number
  size: string
  visibility: string
  trainingId: string
}

export interface ReportIssue {
  id: string
  dimension: string
  timeStart: number
  timeEnd: number
  evidence: string
  problem: string
  suggestion: string
  retrainTarget: string
  triggerBullet?: string
  top: boolean
}

export interface Report {
  id: string
  trainingId: string
  title: string
  liveType: LiveType
  mode: PracticeMode
  date: string
  durationMin: number
  score: number | null
  dimensions: { name: string; score: number }[]
  issues: ReportIssue[]
  aiSuggestion: string
  nextSteps: string[]
}

export interface Bullet {
  id: string
  text: string
  category: BulletCategory
  atSec: number
  scorable: boolean
}

export interface TrendPoint {
  date: string
  label: string
  dimensions: { name: string; value: number }[]
}

// ---------------- 用户 ----------------
export const mockUser: UserProfile = {
  nickname: '小鹿主播',
  phone: '138****6688',
  primaryLiveType: '带货',
  experience: '1–3 个月',
  defaultCamera: 'FaceTime HD 摄像头',
  defaultMic: '内置麦克风',
  saveRecording: true,
  recordingVisibleToSelfOnly: true,
  notifyOnInsight: true,
}

export const CAMERA_OPTIONS = ['FaceTime HD 摄像头', 'Logitech C920', '外接 4K 摄像头']
export const MIC_OPTIONS = ['内置麦克风', 'Blue Yeti', '领夹麦克风']
export const EXPERIENCE_OPTIONS = ['首次开播', '1–3 个月', '3–12 个月', '1 年以上']

// ---------------- 训练记录（首页"最近练习" + 成长记录） ----------------
export const practiceRecords: PracticeRecord[] = [
  { id: 'r6', goal: '开场留住观众', liveType: '带货', mode: 'full', date: '09-21 20:14', durationMin: 12, score: 78, topIssueCount: 2 },
  { id: 'r5', goal: '弹幕应答', liveType: '带货', mode: 'focus', date: '09-20 19:40', durationMin: 6, score: 71, topIssueCount: 1 },
  { id: 'r4', goal: '冷场处理', liveType: '娱乐互动', mode: 'full', date: '09-18 21:02', durationMin: 10, score: 74, topIssueCount: 2 },
  { id: 'r3', goal: '报价表达', liveType: '带货', mode: 'focus', date: '09-16 20:30', durationMin: 5, score: 66, topIssueCount: 2 },
  { id: 'r2', goal: '知识结构', liveType: '知识内容', mode: 'full', date: '09-13 19:18', durationMin: 11, score: 69, topIssueCount: 1 },
  { id: 'r1', goal: '开场留住观众', liveType: '带货', mode: 'full', date: '09-10 20:05', durationMin: 12, score: 58, topIssueCount: 3 },
]

// ---------------- 录像 ----------------
export const recordings: Recording[] = [
  { id: 'v1', title: '开场留住观众 · 完整模拟', liveType: '带货', date: '09-21 20:14', durationMin: 12, size: '86 MB', visibility: '仅自己可见', trainingId: 'r6' },
  { id: 'v2', title: '弹幕应答 · 难点练习', liveType: '带货', date: '09-20 19:40', durationMin: 6, size: '42 MB', visibility: '仅自己可见', trainingId: 'r5' },
  { id: 'v3', title: '冷场处理 · 完整模拟', liveType: '娱乐互动', date: '09-18 21:02', durationMin: 10, size: '71 MB', visibility: '仅自己可见', trainingId: 'r4' },
  { id: 'v4', title: '报价表达 · 难点练习', liveType: '带货', date: '09-16 20:30', durationMin: 5, size: '35 MB', visibility: '仅自己可见', trainingId: 'r3' },
  { id: 'v5', title: '知识结构 · 完整模拟', liveType: '知识内容', date: '09-13 19:18', durationMin: 11, size: '78 MB', visibility: '仅自己可见', trainingId: 'r2' },
]

// ---------------- 训练报告 ----------------
const issue = (
  id: string,
  dimension: string,
  timeStart: number,
  timeEnd: number,
  evidence: string,
  problem: string,
  suggestion: string,
  retrainTarget: string,
  top: boolean,
  triggerBullet?: string,
): ReportIssue => ({ id, dimension, timeStart, timeEnd, evidence, problem, suggestion, retrainTarget, top, triggerBullet })

export const reports: Report[] = [
  {
    id: 'r6',
    trainingId: 'r6',
    title: '开场留住观众',
    liveType: '带货',
    mode: 'full',
    date: '2026-09-21 20:14',
    durationMin: 12,
    score: 78,
    dimensions: [
      { name: '表达清晰度', score: 82 },
      { name: '弹幕应对', score: 74 },
      { name: '内容组织', score: 80 },
      { name: '节奏控制', score: 71 },
    ],
    issues: [
      issue('i1', '开场留人', 18, 42, '开场 30 秒只报了自己叫什么，没有给出商品利益点，弹幕"这播的什么"出现后停顿 6 秒才接话。', '开场信息价值低，观众没有留下理由。', '开场先给一个明确利益点（例如"今晚只讲一个夏季补水面膜怎么挑"），再自我介绍。', '开场留人', true, '这播的什么呀？'),
      issue('i2', '报价表达', 95, 124, '报价时"到手价""叠加券后""限时"三个条件一口气说完，弹幕追问"到底多少钱"后才重复一遍。', '优惠条件一口气带过，关键数字没有停顿。', '报价后停顿 2 秒，分点说清到手价、叠加条件、有效期。', '报价表达', true),
      issue('i3', '节奏控制', 200, 226, '连续 26 秒没有有效表达，画面停留在展示商品细节，无语言引导。', '出现明显冷场，未用话术衔接。', '准备 3 个低门槛话题，沉默 15 秒内自然接上。', '冷场处理', false),
    ],
    aiSuggestion: '本场最值得改进的是开场留人和报价表达：先用利益点抓住观众，再放慢报价节奏。整体表达结构已经稳定，继续练习这两个点即可看到明显进步。',
    nextSteps: ['重练"开场留人"难点', '重练"报价表达"难点', '观看教程《开场前 30 秒怎么留住观众》'],
  },
  {
    id: 'r5',
    trainingId: 'r5',
    title: '弹幕应答',
    liveType: '带货',
    mode: 'focus',
    date: '2026-09-20 19:40',
    durationMin: 6,
    score: 71,
    dimensions: [
      { name: '表达清晰度', score: 75 },
      { name: '弹幕应对', score: 68 },
      { name: '内容组织', score: 72 },
    ],
    issues: [
      issue('i1', '弹幕筛选', 12, 36, '观众连发 4 条弹幕，主播逐条回答，其中 2 条是"主播哪里人"等无关内容。', '未按价值筛选弹幕，被无关弹幕带节奏。', '先回应高价值问题，无关内容一句话带过。', '多弹幕筛选', true),
    ],
    aiSuggestion: '弹幕多时优先回应对购买决策有帮助的问题，其余可合并一句话带过。',
    nextSteps: ['重练"弹幕应答"难点', '观看教程《弹幕提问太多时如何快速筛选》'],
  },
  {
    id: 'r4',
    trainingId: 'r4',
    title: '冷场处理',
    liveType: '娱乐互动',
    mode: 'full',
    date: '2026-09-18 21:02',
    durationMin: 10,
    score: 74,
    dimensions: [
      { name: '表达清晰度', score: 76 },
      { name: '弹幕应对', score: 78 },
      { name: '节奏控制', score: 64 },
    ],
    issues: [
      issue('i1', '冷场处理', 60, 96, '两次超过 15 秒的沉默，期间没有触发救场话术。', '冷场后缺少低门槛话题衔接。', '准备 3 个救场话题，沉默即用。', '冷场处理', true),
    ],
    aiSuggestion: '冷场是当前最明显的问题，建议先练冷场救场话术。',
    nextSteps: ['重练"冷场处理"难点', '观看教程《冷场 15 秒的三种救场话术》'],
  },
  {
    id: 'r3',
    trainingId: 'r3',
    title: '报价表达',
    liveType: '带货',
    mode: 'focus',
    date: '2026-09-16 20:30',
    durationMin: 5,
    score: 66,
    dimensions: [
      { name: '表达清晰度', score: 62 },
      { name: '内容组织', score: 70 },
    ],
    issues: [
      issue('i1', '报价表达', 10, 34, '直接说"全网最低"，未提供可核实依据。', '使用了无法核实的绝对承诺。', '删除绝对承诺，改为可核实的信息和适用条件。', '报价表达', true),
    ],
    aiSuggestion: '避免绝对化表达，用可核实信息替代。',
    nextSteps: ['重练"报价表达"难点', '观看教程《带货报价时如何说清优惠条件》'],
  },
  {
    id: 'r2',
    trainingId: 'r2',
    title: '知识结构',
    liveType: '知识内容',
    mode: 'full',
    date: '2026-09-13 19:18',
    durationMin: 11,
    score: 69,
    dimensions: [
      { name: '表达清晰度', score: 70 },
      { name: '内容组织', score: 66 },
    ],
    issues: [
      issue('i1', '知识结构', 30, 58, '铺垫 28 秒未给出结论，观众追问"所以结论是什么"。', '未采用"先结论再展开"结构。', '先给结论，再补 1–3 个关键点。', '知识结构', true),
    ],
    aiSuggestion: '知识类内容先结论后展开，观众更易跟上。',
    nextSteps: ['重练"知识结构"难点', '观看教程《知识类直播的"先结论再展开"结构》'],
  },
  {
    id: 'r1',
    trainingId: 'r1',
    title: '开场留住观众',
    liveType: '带货',
    mode: 'full',
    date: '2026-09-10 20:05',
    durationMin: 12,
    score: 58,
    dimensions: [
      { name: '表达清晰度', score: 60 },
      { name: '弹幕应对', score: 55 },
      { name: '内容组织', score: 61 },
      { name: '节奏控制', score: 56 },
    ],
    issues: [
      issue('i1', '开场留人', 20, 46, '开场只自我介绍，无利益点，观众流失明显。', '开场无价值锚点。', '开场给利益点 + 悬念。', '开场留人', true),
      issue('i2', '节奏控制', 130, 168, '连续 38 秒无有效表达。', '长时间冷场。', '用救场话题衔接。', '冷场处理', true),
      issue('i3', '报价表达', 210, 240, '优惠条件一次说完，无停顿。', '报价无节奏。', '报价后停顿分点说明。', '报价表达', false),
    ],
    aiSuggestion: '开场、冷场、报价都有较大改进空间，建议从开场留人开始逐个突破。',
    nextSteps: ['重练"开场留人"难点', '重练"冷场处理"难点'],
  },
]

export function getReport(id: string): Report | undefined {
  return reports.find((r) => r.id === id || r.trainingId === id)
}

// 重练前后对比（当前 r6 vs 上次同目标 r1）
export const compareData = {
  current: getReport('r6')!,
  previous: getReport('r1')!,
  deltas: [
    { dimension: '表达清晰度', before: 60, after: 82, delta: '+22' },
    { dimension: '弹幕应对', before: 55, after: 74, delta: '+19' },
    { dimension: '内容组织', before: 61, after: 80, delta: '+19' },
    { dimension: '节奏控制', before: 56, after: 71, delta: '+15' },
  ],
  summary: '开场信息价值明显提升，报价节奏更清晰；冷场衔接仍需继续练习。',
}

// ---------------- 能力趋势（成长记录图表） ----------------
export const trend: TrendPoint[] = [
  { date: '2026-09-10', label: '09-10', dimensions: [{ name: '综合', value: 58 }] },
  { date: '2026-09-13', label: '09-13', dimensions: [{ name: '综合', value: 69 }] },
  { date: '2026-09-16', label: '09-16', dimensions: [{ name: '综合', value: 66 }] },
  { date: '2026-09-18', label: '09-18', dimensions: [{ name: '综合', value: 74 }] },
  { date: '2026-09-20', label: '09-20', dimensions: [{ name: '综合', value: 71 }] },
  { date: '2026-09-21', label: '09-21', dimensions: [{ name: '综合', value: 78 }] },
]

// 分维度趋势（按直播类型/维度筛选时使用）
export const trendByDimension: Record<string, TrendPoint[]> = {
  '表达清晰度': [
    { date: '09-10', label: '09-10', dimensions: [{ name: '表达清晰度', value: 60 }] },
    { date: '09-13', label: '09-13', dimensions: [{ name: '表达清晰度', value: 70 }] },
    { date: '09-16', label: '09-16', dimensions: [{ name: '表达清晰度', value: 62 }] },
    { date: '09-18', label: '09-18', dimensions: [{ name: '表达清晰度', value: 76 }] },
    { date: '09-20', label: '09-20', dimensions: [{ name: '表达清晰度', value: 75 }] },
    { date: '09-21', label: '09-21', dimensions: [{ name: '表达清晰度', value: 82 }] },
  ],
  '弹幕应对': [
    { date: '09-10', label: '09-10', dimensions: [{ name: '弹幕应对', value: 55 }] },
    { date: '09-13', label: '09-13', dimensions: [{ name: '弹幕应对', value: 60 }] },
    { date: '09-16', label: '09-16', dimensions: [{ name: '弹幕应对', value: 58 }] },
    { date: '09-18', label: '09-18', dimensions: [{ name: '弹幕应对', value: 78 }] },
    { date: '09-20', label: '09-20', dimensions: [{ name: '弹幕应对', value: 68 }] },
    { date: '09-21', label: '09-21', dimensions: [{ name: '弹幕应对', value: 74 }] },
  ],
  '内容组织': [
    { date: '09-10', label: '09-10', dimensions: [{ name: '内容组织', value: 61 }] },
    { date: '09-13', label: '09-13', dimensions: [{ name: '内容组织', value: 66 }] },
    { date: '09-16', label: '09-16', dimensions: [{ name: '内容组织', value: 70 }] },
    { date: '09-18', label: '09-18', dimensions: [{ name: '内容组织', value: 72 }] },
    { date: '09-20', label: '09-20', dimensions: [{ name: '内容组织', value: 72 }] },
    { date: '09-21', label: '09-21', dimensions: [{ name: '内容组织', value: 80 }] },
  ],
  '节奏控制': [
    { date: '09-10', label: '09-10', dimensions: [{ name: '节奏控制', value: 56 }] },
    { date: '09-13', label: '09-13', dimensions: [{ name: '节奏控制', value: 60 }] },
    { date: '09-16', label: '09-16', dimensions: [{ name: '节奏控制', value: 62 }] },
    { date: '09-18', label: '09-18', dimensions: [{ name: '节奏控制', value: 64 }] },
    { date: '09-20', label: '09-20', dimensions: [{ name: '节奏控制', value: 66 }] },
    { date: '09-21', label: '09-21', dimensions: [{ name: '节奏控制', value: 71 }] },
  ],
}

// ---------------- AI 建议 ----------------
export const aiAdvice = [
  { id: 'a1', title: '开场留人是当前最值得改进的点', body: '开场先给一个明确利益点，再自我介绍，观众停留意愿会明显提升。' },
  { id: 'a2', title: '报价时放慢节奏', body: '报价后停顿 2 秒，分点说清到手价、叠加条件与有效期。' },
]

// ---------------- 模拟弹幕（完整模拟直播流） ----------------
const b = (id: string, text: string, category: BulletCategory, atSec: number, scorable = false): Bullet => ({
  id,
  text,
  category,
  atSec,
  scorable,
})

export const bulletPool: Bullet[] = [
  b('b1', '主播好，今天讲什么呀？', '路人', 3),
  b('b2', '第一次来，有什么福利吗？', '路人', 8),
  b('b3', '这个商品适合什么肤质？', '追问', 14, true),
  b('b4', '主播说话声音有点小', '无关', 20),
  b('b5', '你们那边今天下雨了吗？', '无关', 27),
  b('b6', '这个价格是到手价吗？', '刁难', 34, true),
  b('b7', '刚进来，讲到哪了？', '路人', 41),
  b('b8', '能不能再说一遍优惠条件', '追问', 48, true),
  b('b9', '背景音乐叫什么？', '无关', 55),
  b('b10', '主播平时几点播？', '路人', 61),
  b('b11', '这个和别家比怎么样？', '刁难', 68, true),
  b('b12', '链接在哪点？', '追问', 75, true),
  b('b13', '今天晚饭吃的什么？', '无关', 82),
  b('b14', '有适合学生党的吗？', '追问', 89, true),
  b('b15', '主播是哪儿人呀？', '路人', 96),
  b('b16', '刚才说的能再讲一遍吗', '追问', 103, true),
  b('b17', '库存还够吗？', '必考', 110, true),
  b('b18', '包不包运费险？', '必考', 118, true),
  b('b19', '这个季节用会不会太油', '追问', 126, true),
  b('b20', '溜了溜了，下次再来', '噪声', 133),
]

// ---------------- 难点练习 ----------------
export interface FocusSession {
  title: string
  goal: string
  question: string
  hints: string[]
  durationHintMin: number
}

export const focusSessions: Record<string, FocusSession> = {
  '开场留人': {
    title: '开场留人',
    goal: '在开场 30 秒内给出明确利益点并留住观众',
    question: '欢迎来到直播间！今天这款夏季补水面膜，你能在 30 秒内告诉我"为什么值得留下来"吗？',
    hints: ['先给一个具体利益点', '再用一个悬念收尾', '控制在 30 秒内'],
    durationHintMin: 3,
  },
  '弹幕应答': {
    title: '弹幕应答',
    goal: '面对多条弹幕，快速筛选并回应高价值问题',
    question: '"这个适合什么肤质？""主播哪里人？""能不能再便宜点？"——你会怎么回应？',
    hints: ['优先回应影响购买的问题', '无关内容一句话带过', '保持节奏不被带偏'],
    durationHintMin: 3,
  },
  '冷场处理': {
    title: '冷场处理',
    goal: '沉默后 15 秒内用低门槛话题重新激活互动',
    question: '直播间突然安静下来，你已经 12 秒没说话了。接下来你会说什么？',
    hints: ['抛一个低门槛问题', '承接刚才的话题', '不要生硬切换'],
    durationHintMin: 3,
  },
  '报价表达': {
    title: '报价表达',
    goal: '报价时停顿分点，说清到手价与优惠条件',
    question: '这款商品到手价 89 元，叠加满 199 减 30。请向观众报价并说清条件。',
    hints: ['先报到手价', '停顿 2 秒', '分点说清优惠条件'],
    durationHintMin: 3,
  },
  '知识结构': {
    title: '知识结构',
    goal: '先给结论，再补 1–3 个关键点',
    question: '"为什么夏季要重点补水而不是美白？"请用"先结论再展开"的方式回答。',
    hints: ['第一句给结论', '补充 1–3 个关键点', '结尾再收束一次'],
    durationHintMin: 3,
  },
  '表达节奏': {
    title: '表达节奏',
    goal: '在重点信息前后留出停顿，让观众能跟上表达',
    question: '请用清楚、自然的节奏介绍一款产品，并在三个重点信息之后各停顿一次。',
    hints: ['一句只说一个重点', '重点后停顿 1–2 秒', '用短句承接下一段'],
    durationHintMin: 3,
  },
  '产品介绍': {
    title: '产品介绍',
    goal: '按对象、特点和适用条件完整介绍产品',
    question: '请向第一次进入直播间的观众介绍这款产品，说明它适合谁、有什么特点以及如何使用。',
    hints: ['先说明适用对象', '提炼两个具体特点', '补充使用条件'],
    durationHintMin: 3,
  },
  '互动号召': {
    title: '互动号召',
    goal: '提出一个观众两秒内就能回应的明确互动问题',
    question: '你刚讲完一个重点，想知道观众接下来更想看演示还是听讲解。请发起一次清楚的互动。',
    hints: ['一次只问一件事', '给出明确回复格式', '说明收到回应后会做什么'],
    durationHintMin: 3,
  },
  '刁难弹幕应答': {
    title: '刁难弹幕应答',
    goal: '确认质疑对象，回答已有依据并交代未知边界',
    question: '弹幕说“你凭什么说这个有效，别又是夸大宣传”。请在不回避问题、不作绝对承诺的情况下回应。',
    hints: ['先确认对方担心什么', '只说现有资料支持的内容', '不知道的部分给出核实方式'],
    durationHintMin: 3,
  },
  '话题承接': {
    title: '话题承接',
    goal: '接住观众的具体信息，再自然转入准备好的新话题',
    question: '观众说“我第一次直播时紧张得说不出话”。请先回应这条弹幕，再转入你的下一个话题。',
    hints: ['接住一个具体信息', '决定展开还是收束', '用连接句进入新话题'],
    durationHintMin: 3,
  },
}

export const FOCUS_TOPICS = Object.keys(focusSessions)

// ---------------- 训练主题（创建练习用） ----------------
export const PRACTICE_TOPICS: Record<LiveType, string[]> = {
  带货: ['开场留人', '弹幕应答', '报价表达', '完整模拟'],
  娱乐互动: ['开场留人', '冷场处理', '弹幕应答', '完整模拟'],
  知识内容: ['知识结构', '开场留人', '弹幕应答', '完整模拟'],
}

// ---------------- 工具 ----------------
export function formatSec(sec: number): string {
  const m = Math.floor(sec / 60)
  const s = Math.floor(sec % 60)
  return `${m}:${String(s).padStart(2, '0')}`
}
