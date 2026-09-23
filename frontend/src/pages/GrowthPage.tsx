import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeftRight, ChevronRight } from 'lucide-react'
import { PageHeader } from '../components/PageHeader'
import { Card } from '../components/Card'
import { MetricCard } from '../components/MetricCard'
import { FilterBar } from '../components/FilterBar'
import { StatusTag } from '../components/StatusTag'
import { practiceRecords, trend, trendByDimension, type LiveType } from '../data/mock'

const RANGE_OPTIONS = ['近 7 天', '近 30 天', '全部']
const TYPE_OPTIONS: (LiveType | '全部')[] = ['全部', '带货', '娱乐互动', '知识内容']
const DIMENSIONS = ['综合', '表达清晰度', '弹幕应对', '内容组织', '节奏控制']

interface ChartPoint {
  label: string
  value: number
}

interface ChartSeries {
  name: string
  color: string
  points: ChartPoint[]
}

function LineChart({ series }: { series: ChartSeries[] }) {
  const w = 560
  const h = 200
  const padX = 28
  const padY = 24
  const min = 40
  const max = 100
  const points = series[0]?.points ?? []
  const stepX = (w - padX * 2) / Math.max(1, points.length - 1)
  const x = (i: number) => padX + i * stepX
  const y = (v: number) => h - padY - ((v - min) / (max - min)) * (h - padY * 2)

  return (
    <div className="growth-chart-wrap">
    <div className="growth-chart-legend">{series.map((item) => <span key={item.name}><i style={{ background: item.color }} />{item.name}</span>)}</div>
    <svg viewBox={`0 0 ${w} ${h}`} className="chart" role="img" aria-label="能力趋势图">
      {[40, 60, 80, 100].map((g) => (
        <line
          key={g}
          x1={padX}
          x2={w - padX}
          y1={y(g)}
          y2={y(g)}
          stroke="var(--border)"
          strokeWidth="1"
        />
      ))}
      {series.map((item) => {
        const path = item.points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${x(i)} ${y(p.value)}`).join(' ')
        return <path key={item.name} d={path} fill="none" stroke={item.color} strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
      })}
      {series[0]?.points.map((p, i) => (
        <g key={p.label}>
          <circle cx={x(i)} cy={y(p.value)} r="3.6" fill="#fff" stroke={series[0].color} strokeWidth="2" />
          <text x={x(i)} y={h - 6} textAnchor="middle" fontSize="10" fill="var(--text-tertiary)">
            {p.label}
          </text>
        </g>
      ))}
    </svg>
    </div>
  )
}

export default function GrowthPage() {
  const navigate = useNavigate()
  const [range, setRange] = useState('近 30 天')
  const [type, setType] = useState<(typeof TYPE_OPTIONS)[number]>('全部')
  const [dimension, setDimension] = useState('综合')

  const slice = range === '近 7 天' ? 3 : range === '近 30 天' ? 5 : 6

  const chartSeries = useMemo<ChartSeries[]>(() => {
    const toPoints = (source: typeof trend) => source.slice(-slice).map((p) => ({ label: p.label, value: p.dimensions[0].value }))
    if (dimension !== '综合') {
      return [{ name: dimension, color: 'var(--brand)', points: toPoints(trendByDimension[dimension] ?? trend) }]
    }
    return [
      { name: '表达清晰度', color: '#08b8b0', points: toPoints(trendByDimension['表达清晰度']) },
      { name: '弹幕应对', color: '#15171c', points: toPoints(trendByDimension['弹幕应对']) },
      { name: '内容组织', color: '#9aa6b1', points: toPoints(trendByDimension['内容组织']) },
    ]
  }, [dimension, slice])

  const records = useMemo(() => {
    return practiceRecords.filter((r) => type === '全部' || r.liveType === type)
  }, [type])

  const latest = practiceRecords[0].score ?? 0
  const first = practiceRecords[practiceRecords.length - 1].score ?? 0

  return (
    <div className="page">
      <PageHeader title="成长记录" subtitle="看见每一次练习带来的具体进步，而不是只看总分。" />

      <div className="metric-grid">
        <MetricCard label="累计练习" value={practiceRecords.length} unit="场" hint="覆盖三种直播类型" />
        <MetricCard label="最近综合分" value={latest} unit="分" hint="分数仅作辅助参考" brand />
        <MetricCard label="相较首次" value={latest - first >= 0 ? `+${latest - first}` : latest - first} unit="分" hint="持续练习带来的进步" />
      </div>

      <div className="growth-main mt-6">
      <Card>
        <div className="growth-filters">
          <div>
            <span className="filter-label">时间范围</span>
            <FilterBar options={RANGE_OPTIONS} value={range} onChange={setRange} label="时间范围" />
          </div>
          <div>
            <span className="filter-label">直播类型</span>
            <FilterBar options={TYPE_OPTIONS} value={type} onChange={(v) => setType(v as (typeof TYPE_OPTIONS)[number])} label="直播类型" />
          </div>
        </div>

        <div className="growth-chart-head row-between mt-4">
          <span className="medium">能力趋势</span>
          <div className="chip-row">
            {DIMENSIONS.map((d) => (
              <button
                key={d}
                className={dimension === d ? 'chip chip--active chip--sm' : 'chip chip--sm'}
                onClick={() => setDimension(d)}
              >
                {d}
              </button>
            ))}
          </div>
        </div>

        <div className="mt-3">
          <LineChart series={chartSeries} />
        </div>
        <p className="text-xs text-tertiary mt-2">
          趋势显示「{dimension}」在「{range}」内的变化；直播类型筛选用于下方进步证据。
        </p>
      </Card>
      <aside className="growth-insight frosted">
        <span>本月进步</span>
        <strong>弹幕追问应答</strong>
        <small>完整回答比例</small>
        <b>42% <i>→</i> 67%</b>
        <p>先说结论后再补充原因，已经更稳定。</p>
      </aside>
      </div>

      <section className="section mt-6">
        <h2 className="section-title">进步证据</h2>
        <Card>
          <ul className="recent-list">
            {records.map((r) => (
              <li key={r.id}>
                <button className="recent-item" onClick={() => navigate(`/reports/${r.id}`)}>
                  <span className="recent-item__goal">{r.goal}</span>
                  <span className="recent-item__meta">
                    <StatusTag tone="neutral">{r.liveType}</StatusTag>
                    <span className="text-xs text-tertiary">
                      {r.date} · {r.durationMin} 分钟 · 优先问题 {r.topIssueCount} 个
                    </span>
                  </span>
                  <span className="recent-item__score">
                    {r.score ?? '—'}
                    <span className="text-xs text-tertiary"> 分</span>
                  </span>
                  {r.id === 'r6' && (
                    <span
                      className="link-btn"
                      onClick={(e) => {
                        e.stopPropagation()
                        navigate(`/practice/${r.id}/compare`)
                      }}
                    >
                      <ArrowLeftRight size={14} aria-hidden /> 对比
                    </span>
                  )}
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
