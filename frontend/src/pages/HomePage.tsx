import { useNavigate } from 'react-router-dom'
import { ArrowRight, BookOpen, ChevronRight, PlayCircle, Target } from 'lucide-react'
import { PageHeader } from '../components/PageHeader'
import { Card } from '../components/Card'
import { MetricCard } from '../components/MetricCard'
import { FrostedInsightCard } from '../components/FrostedInsightCard'
import { StatusTag } from '../components/StatusTag'
import { useApp } from '../store/AppContext'
import { aiAdvice, practiceRecords } from '../data/mock'

const MODE_LABEL: Record<string, string> = { full: '完整模拟', focus: '难点练习' }

export default function HomePage() {
  const navigate = useNavigate()
  const { user } = useApp()

  const hour = new Date().getHours()
  const greeting = hour < 6 ? '夜深了' : hour < 12 ? '早上好' : hour < 18 ? '下午好' : '晚上好'

  const total = practiceRecords.length
  const recentScore = practiceRecords[0].score ?? 0
  const firstScore = practiceRecords[practiceRecords.length - 1].score ?? 0
  const improved = recentScore - firstScore

  return (
    <div className="page">
      <PageHeader
        title={`${greeting}，${user.nickname}`}
        subtitle="在模拟直播间里练表达、练互动，练后得到有依据的反馈。"
      />

      <div className="metric-grid">
        <MetricCard label="累计练习" value={total} unit="场" hint="覆盖三种直播类型" />
        <MetricCard label="最近综合分" value={recentScore} unit="分" hint="分数仅作辅助参考" brand />
        <MetricCard label="相较首次" value={improved >= 0 ? `+${improved}` : improved} unit="分" hint="持续练习带来的进步" />
      </div>

      <div className="mt-6">
        <FrostedInsightCard title="AI 训练洞察">
          {aiAdvice[0].title}：{aiAdvice[0].body} 建议从「难点练习」进入，直接针对性地练一次。
        </FrostedInsightCard>
      </div>

      <section className="section">
        <h2 className="section-title">开始练习</h2>
        <div className="quick-grid">
          <button className="quick-card" onClick={() => navigate('/practice/new?mode=full')}>
            <span className="quick-card__icon">
              <PlayCircle size={24} aria-hidden />
            </span>
            <span className="quick-card__title">完整模拟直播</span>
            <span className="quick-card__desc">完整走一遍开播流程，练表达与互动</span>
            <span className="quick-card__arrow">
              <ArrowRight size={16} aria-hidden />
            </span>
          </button>

          <button className="quick-card" onClick={() => navigate('/practice/new?mode=focus')}>
            <span className="quick-card__icon">
              <Target size={24} aria-hidden />
            </span>
            <span className="quick-card__title">难点练习</span>
            <span className="quick-card__desc">针对开场、弹幕、冷场等单项反复练</span>
            <span className="quick-card__arrow">
              <ArrowRight size={16} aria-hidden />
            </span>
          </button>

          <button className="quick-card" onClick={() => navigate('/tutorials')}>
            <span className="quick-card__icon">
              <BookOpen size={24} aria-hidden />
            </span>
            <span className="quick-card__title">看教程</span>
            <span className="quick-card__desc">先学方法，再进入练习</span>
            <span className="quick-card__arrow">
              <ArrowRight size={16} aria-hidden />
            </span>
          </button>
        </div>
      </section>

      <section className="section">
        <div className="section-head">
          <h2 className="section-title">最近练习</h2>
          <button className="link-btn" onClick={() => navigate('/growth')}>
            查看全部 <ChevronRight size={14} aria-hidden />
          </button>
        </div>
        <Card className="recent-card">
          <ul className="recent-list">
            {practiceRecords.slice(0, 5).map((r) => (
              <li key={r.id}>
                <button className="recent-item" onClick={() => navigate(`/reports/${r.id}`)}>
                  <span className="recent-item__goal">{r.goal}</span>
                  <span className="recent-item__meta">
                    <StatusTag tone="neutral">{r.liveType}</StatusTag>
                    <StatusTag tone="ink">{MODE_LABEL[r.mode]}</StatusTag>
                    <span className="text-xs text-tertiary">
                      {r.date} · {r.durationMin} 分钟
                    </span>
                  </span>
                  <span className="recent-item__score">
                    {r.score ?? '—'}
                    <span className="text-xs text-tertiary"> 分</span>
                  </span>
                  <ChevronRight size={16} className="text-tertiary" aria-hidden />
                </button>
              </li>
            ))}
          </ul>
        </Card>
      </section>
    </div>
  )
}
