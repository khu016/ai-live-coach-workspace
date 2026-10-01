import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  ArrowRight,
  BarChart3,
  BookOpen,
  Bot,
  ChevronRight,
  CircleCheck,
  FileText,
  MessageCircle,
  Mic2,
  Play,
  Radio,
  ShieldCheck,
  Sparkles,
  Target,
  TrendingUp,
} from 'lucide-react'
import { getWeekStats, listTrainings, type ApiTraining, type WeekStats } from '../api/client'

const adviceCards = [
  { title: '弹幕追问应对', description: '回答时补全对象、原因和结果', cue: '“这个适合什么肤质？”', cta: '开始弹幕应答练习', topic: '弹幕应答', Icon: Sparkles },
  { title: '表达节奏', description: '在重点信息前后留出停顿', cue: '重点前停一拍，让观众听清', cta: '开始节奏专项练习', topic: '表达节奏', Icon: BarChart3 },
  { title: '产品介绍', description: '先说适用对象，再讲具体特点', cue: '对象 → 特点 → 使用结果', cta: '开始产品介绍练习', topic: '产品介绍', Icon: Target },
]

function minutesOf(sec: number): string {
  if (sec < 60) return `${Math.round(sec)} 秒`
  return `${Math.round(sec / 60)} 分钟`
}

function rateText(rate: number | null): string {
  if (rate === null || rate === undefined) return '—'
  return `${Math.round(rate * 100)}%`
}

export default function HomePage() {
  const navigate = useNavigate()
  const [activeAdvice, setActiveAdvice] = useState(0)
  const [stats, setStats] = useState<WeekStats | null>(null)
  const [recent, setRecent] = useState<ApiTraining[]>([])

  useEffect(() => {
    let cancelled = false
    void getWeekStats()
      .then((s) => { if (!cancelled) setStats(s) })
      .catch(() => {})
    void listTrainings()
      .then((list) => { if (!cancelled) setRecent(list.slice(0, 3)) })
      .catch(() => {})
    return () => { cancelled = true }
  }, [])

  const selectAdvice = (index: number) => {
    if (index === activeAdvice) {
      navigate(`/practice/new?mode=focus&topic=${encodeURIComponent(adviceCards[index].topic)}`)
      return
    }
    setActiveAdvice(index)
  }

  const week = stats?.week
  const weekCount = week?.training_count ?? 0
  const weekDuration = week?.total_duration_sec ?? 0
  const requiredBullets = week?.required_response_bullets ?? 0
  const respondedBullets = week?.responded_bullets ?? 0
  const responseRate = week?.response_rate ?? null
  const sampleSufficient = week?.sample_sufficient ?? false
  const sampleCount = week?.sample_count ?? 0

  return (
    <div className="page home-dashboard">
      <section className="home-hero" aria-labelledby="home-title">
        <div className="home-hero__copy">
          <p className="home-hero__eyebrow"><Sparkles size={16} /> NIVI 开播排练室</p>
          <h1 id="home-title">今天想怎么练？</h1>
          <p className="home-hero__lead">先看教程、练一个难点，或者直接模拟直播。路径由你决定。</p>
          <div className="home-hero__trust" aria-label="训练说明">
            <span><ShieldCheck size={16} /> 不会真实开播</span>
            <span><Mic2 size={16} /> 可以只使用麦克风</span>
          </div>
        </div>

        <div className="advice-stage" aria-label="今日训练建议">
          <div className="advice-glow" aria-hidden />
          {adviceCards.map((card, index) => {
            const layer = (index - activeAdvice + adviceCards.length) % adviceCards.length
            const CardIcon = card.Icon
            return (
              <button
                key={card.topic}
                className={`advice-card advice-card--deck advice-card--layer-${layer}`}
                onClick={() => selectAdvice(index)}
                aria-label={layer === 0 ? `${card.title}，${card.cta}` : `切换到${card.title}`}
                aria-current={layer === 0 ? 'true' : undefined}
                tabIndex={layer === 0 ? 0 : -1}
              >
                <span className="advice-card__content">
                  <span className="advice-card__label"><CardIcon size={18} /> 今日训练建议</span>
                  <strong>{card.title}</strong>
                  <span className="advice-card__description">{card.description}</span>
                  <span className="advice-card__cue" aria-hidden>
                    <MessageCircle size={15} /> {card.cue}
                  </span>
                  <span className="advice-card__cta">{card.cta} <ArrowRight size={17} /></span>
                </span>
                <span className="advice-card__peek" aria-hidden><CardIcon size={27} /><b>{card.title}</b></span>
              </button>
            )
          })}
        </div>
      </section>

      <div className="home-section-heading">
        <div><span>选择训练方式</span><strong>从你现在最需要的地方开始</strong></div>
        <p>三种方式可以随时切换，没有固定顺序。</p>
      </div>

      <section className="home-entry-grid" aria-label="训练入口">
        <button className="home-entry" onClick={() => navigate('/practice/new?mode=full')}>
          <span className="home-entry__icon"><Radio /></span>
          <span><strong>完整模拟直播</strong><small>进入有实时弹幕的完整训练</small></span>
          <ChevronRight size={22} />
        </button>
        <button className="home-entry" onClick={() => navigate('/practice/new?mode=focus')}>
          <span className="home-entry__icon"><Target /></span>
          <span><strong>难点练习</strong><small>针对冷场、应答等问题练习</small></span>
          <ChevronRight size={22} />
        </button>
        <button className="home-entry" onClick={() => navigate('/tutorials')}>
          <span className="home-entry__icon"><BookOpen /></span>
          <span><strong>看教程</strong><small>学习开场、互动与表达技巧</small></span>
          <ChevronRight size={22} />
        </button>
      </section>

      <div className="home-section-heading home-section-heading--compact">
        <div><span>你的训练状态</span><strong>只展示真实练习数据</strong></div>
      </div>

      <section className="home-workspace" aria-label="训练数据总览">
        <Link
          to="/growth"
          className="home-panel home-panel--interactive weekly-panel"
          aria-label="查看本周训练详情"
        >
          <header><span><BarChart3 size={19} /> 本周训练</span></header>
          <div className="weekly-summary">
            <strong>{weekCount}<small>次</small></strong>
            <span className="text-sm text-secondary">累计 {minutesOf(weekDuration)}</span>
          </div>
          <div className="weekly-metrics">
            <div className="weekly-metric">
              <span className="weekly-metric__label">需回应弹幕</span>
              <strong>{requiredBullets}</strong>
            </div>
            <div className="weekly-metric">
              <span className="weekly-metric__label">已回应</span>
              <strong>{respondedBullets}</strong>
            </div>
          </div>
          <p className="text-xs text-tertiary">数据来自已保存的真实训练记录，不包含演示值。</p>
        </Link>

        <div className="home-middle-stack">
          <Link
            to="/growth"
            className="home-panel home-panel--interactive rhythm-panel"
            aria-label="查看互动节奏详情"
          >
            <header><span><CircleCheck size={19} /> 互动节奏</span><small className="rhythm-range">本周</small></header>
            <div className="rhythm-summary">
              {sampleSufficient ? (
                <div><strong>{rateText(responseRate)}</strong><span>回应及时率</span></div>
              ) : (
                <div><strong>数据不足</strong><span>已有样本 {sampleCount} 条</span></div>
              )}
              <span className="rhythm-change"><TrendingUp size={14} /> 需回应弹幕 {requiredBullets} 条</span>
            </div>
            <p className="text-xs text-tertiary">
              {sampleSufficient
                ? `回应窗口内已关联有效转写片段的弹幕占比，样本 ${sampleCount} 条。`
                : '可评分且需回应的弹幕少于 3 条，暂不显示百分比。'}
            </p>
          </Link>

          <Link
            to="/growth"
            className="home-panel home-panel--interactive progress-panel"
            aria-label="查看本周进步详情"
          >
            <header><span><TrendingUp size={19} /> 本周进步</span><ChevronRight size={18} /></header>
            <div className="progress-row">
              <span>训练次数</span><div><i style={{ width: '100%' }} /></div><b>{weekCount} 场</b>
            </div>
            <div className="progress-row">
              <span>训练时长</span><div><i style={{ width: '100%' }} /></div><b>{minutesOf(weekDuration)}</b>
            </div>
            <p className="text-xs text-tertiary mt-3">
              表达流畅度、互动能力等评分口径尚在积累样本，暂不展示百分比趋势。
            </p>
          </Link>
        </div>

        <article className="home-panel home-panel--animated coach-panel">
          <header><span><Sparkles size={20} /> AI 陪练</span><button onClick={() => navigate('/practice/new?mode=focus&topic=弹幕应答')} aria-label="开始 AI 陪练"><ArrowRight size={18} /></button></header>
          <div className="coach-advice">
            <span className="coach-bot"><Bot size={28} /></span>
            <p>建议先练习弹幕追问，<br />回答时补全对象、原因和结果。</p>
          </div>
          <div className="coach-recent-head"><strong>最近练习</strong><button onClick={() => navigate('/growth')}>查看全部 <ChevronRight size={14} /></button></div>
          {recent.length === 0 ? (
            <p className="text-sm text-tertiary coach-empty">还没有已完成的练习，先开始一场吧。</p>
          ) : recent.map((t) => (
            <button
              className="coach-record"
              key={t.id}
              onClick={() => navigate(`/reports/${t.id}`)}
              aria-label={`查看训练报告：${t.goal}`}
            >
              <span className="record-icon"><MessageCircle size={18} /></span>
              <span><b>{t.goal}</b><small>{t.live_type} · {t.practice_mode === 'focus' ? '难点练习' : '完整模拟'}</small></span>
              <em>已完成</em>
              <ChevronRight className="coach-record__arrow" size={17} aria-hidden />
            </button>
          ))}
          <div className="coach-actions">
            <button onClick={() => navigate('/recordings')}><FileText size={17} /> 查看录像</button>
            <button className="primary" onClick={() => navigate('/practice/new?mode=focus&topic=弹幕应答')}><Play size={17} fill="currentColor" /> 开始练习</button>
          </div>
        </article>
      </section>
    </div>
  )
}
