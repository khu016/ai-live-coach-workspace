import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ArrowRight,
  BarChart3,
  BookOpen,
  Bot,
  ChevronRight,
  CircleCheck,
  FileText,
  MessageCircle,
  MoreHorizontal,
  Play,
  Radio,
  Sparkles,
  Target,
  TrendingUp,
} from 'lucide-react'
const weekBars = [22, 34, 45, 48, 63, 78, 94]
const adviceCards = [
  {
    title: '弹幕追问应对',
    description: '上次训练有 3 次回答缺少关键信息',
    cta: '开始 5 分钟难点练习',
    topic: '弹幕应答',
    Icon: Sparkles,
  },
  {
    title: '表达节奏',
    description: '连续表达时有 2 处节奏变化过快',
    cta: '开始节奏专项练习',
    topic: '表达节奏',
    Icon: BarChart3,
  },
  {
    title: '产品介绍',
    description: '核心卖点还可以表达得更有层次',
    cta: '开始产品介绍练习',
    topic: '产品介绍',
    Icon: Target,
  },
]

export default function HomePage() {
  const navigate = useNavigate()
  const [activeAdvice, setActiveAdvice] = useState(0)

  const selectAdvice = (index: number) => {
    if (index === activeAdvice) {
      navigate(`/practice/new?mode=focus&topic=${encodeURIComponent(adviceCards[index].topic)}`)
      return
    }
    setActiveAdvice(index)
  }

  return (
    <div className="page home-dashboard">
      <section className="home-hero" aria-labelledby="home-title">
        <div className="home-hero__copy">
          <p className="home-hero__eyebrow">开播前训练</p>
          <h1 id="home-title">今天想怎么练？</h1>
          <p>选择一种方式，开始你的开播前训练</p>
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
              >
                <span className="advice-card__content">
                  <span className="advice-card__label"><CardIcon size={18} /> 今日训练建议</span>
                  <strong>{card.title}</strong>
                  <span className="advice-card__description">{card.description}</span>
                  <span className="advice-card__cta">{card.cta} <ArrowRight size={17} /></span>
                </span>
                <span className="advice-card__peek" aria-hidden><CardIcon size={27} /><b>{card.title}</b></span>
              </button>
            )
          })}
        </div>
      </section>

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

      <section className="home-workspace" aria-label="训练数据总览">
        <article className="home-panel weekly-panel">
          <header><span><BarChart3 size={19} /> 本周训练</span></header>
          <div className="weekly-summary">
            <strong>5<small>次</small></strong>
            <button onClick={() => navigate('/reports/r6')}><span>待改进</span><b>2<small>项</small></b><ChevronRight size={18} /></button>
          </div>
          <div className="week-bars" aria-label="本周训练次数柱状图">
            {weekBars.map((height, index) => (
              <div key={index} className="week-bars__item">
                <i style={{ height: `${height}%` }} />
                <span>{['周一', '周二', '周三', '周四', '周五', '周六', '周日'][index]}</span>
              </div>
            ))}
          </div>
          <div className="completeness">
            <h3>应答完整度</h3>
            <div className="completeness__bar"><i /><i /><i /></div>
            <div className="completeness__legend">
              <span><i className="dot dot--strong" />完整回答 <b>67%</b></span>
              <span><i className="dot dot--soft" />部分完整 <b>24%</b></span>
              <span><i className="dot dot--muted" />缺少信息 <b>9%</b></span>
            </div>
          </div>
        </article>

        <div className="home-middle-stack">
          <article className="home-panel rhythm-panel">
            <header><span><CircleCheck size={19} /> 互动节奏</span><small className="rhythm-range">最近 7 天</small></header>
            <div className="rhythm-summary">
              <div><strong>82%</strong><span>本周平均连贯度</span></div>
              <span className="rhythm-change"><TrendingUp size={14} /> 较上周 +8%</span>
            </div>
            <div className="rhythm-chart" role="img" aria-label="最近七天互动连贯度从百分之五十八提升到百分之八十二，目标为百分之七十五">
              <svg viewBox="0 0 330 112" preserveAspectRatio="none" aria-hidden>
                <defs>
                  <linearGradient id="rhythmArea" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#16bcb3" stopOpacity="0.24" />
                    <stop offset="100%" stopColor="#16bcb3" stopOpacity="0" />
                  </linearGradient>
                </defs>
                <g className="rhythm-grid">
                  <line x1="12" y1="25" x2="318" y2="25" />
                  <line x1="12" y1="57" x2="318" y2="57" />
                  <line x1="12" y1="89" x2="318" y2="89" />
                </g>
                <line className="rhythm-target" x1="12" y1="46" x2="318" y2="46" />
                <text className="rhythm-target-label" x="316" y="40" textAnchor="end">目标 75%</text>
                <path className="rhythm-area" d="M18 91 C42 86 52 77 67 76 S101 86 116 82 S148 63 165 62 S198 52 214 48 S247 40 263 36 S296 26 312 22 L312 103 L18 103 Z" />
                <path className="rhythm-line" d="M18 91 C42 86 52 77 67 76 S101 86 116 82 S148 63 165 62 S198 52 214 48 S247 40 263 36 S296 26 312 22" />
                <g className="rhythm-points">
                  <circle cx="18" cy="91" r="3" /><circle cx="67" cy="76" r="3" />
                  <circle cx="116" cy="82" r="3" /><circle cx="165" cy="62" r="3" />
                  <circle cx="214" cy="48" r="3" /><circle cx="263" cy="36" r="3" />
                  <circle className="rhythm-point--latest" cx="312" cy="22" r="5" />
                </g>
              </svg>
            </div>
            <div className="rhythm-days" aria-hidden>{['周一', '周二', '周三', '周四', '周五', '周六', '周日'].map((day) => <span key={day}>{day}</span>)}</div>
          </article>

          <article className="home-panel progress-panel">
            <header><span><TrendingUp size={19} /> 本周进步</span><ChevronRight size={18} /></header>
            {[
              ['表达流畅度', 82, '+67%'],
              ['互动能力', 62, '+52%'],
              ['产品介绍', 42, '+38%'],
            ].map(([label, value, change]) => (
              <div className="progress-row" key={String(label)}>
                <span>{label}</span><div><i style={{ width: `${value}%` }} /></div><b>{change}</b>
              </div>
            ))}
          </article>
        </div>

        <article className="home-panel coach-panel">
          <header><span><Sparkles size={20} /> AI 陪练</span><button aria-label="展开"><ArrowRight size={18} /></button></header>
          <div className="coach-advice">
            <span className="coach-bot"><Bot size={28} /></span>
            <p>建议先练习弹幕追问，<br />回答时补全对象、原因和结果。</p>
          </div>
          <div className="coach-recent-head"><strong>最近练习</strong><button onClick={() => navigate('/growth')}>查看全部 <ChevronRight size={14} /></button></div>
          <button className="coach-record" onClick={() => navigate('/reports/r6')}>
            <span className="record-icon"><MessageCircle size={18} /></span><span><b>直播互动话术练习</b><small>昨天</small></span><em>已完成</em><MoreHorizontal size={18} />
          </button>
          <button className="coach-record" onClick={() => navigate('/reports/r5')}>
            <span className="record-icon"><FileText size={18} /></span><span><b>带货产品介绍模拟</b><small>3 天前</small></span><em className="is-training">练习中</em><MoreHorizontal size={18} />
          </button>
          <div className="coach-actions">
            <button onClick={() => navigate('/reports/r6')}><FileText size={17} /> 查看依据</button>
            <button className="primary" onClick={() => navigate('/practice/new?mode=focus&topic=弹幕应答')}><Play size={17} fill="currentColor" /> 开始练习</button>
          </div>
          <button className="coach-input" onClick={() => navigate('/practice/new?mode=focus&topic=弹幕应答')}><MessageCircle size={17} /> 问问 AI 陪练 <ArrowRight size={17} /></button>
        </article>
      </section>
    </div>
  )
}
