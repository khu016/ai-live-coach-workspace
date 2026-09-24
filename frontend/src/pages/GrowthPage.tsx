import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ChevronRight } from 'lucide-react'
import { PageHeader } from '../components/PageHeader'
import { Card } from '../components/Card'
import { MetricCard } from '../components/MetricCard'
import { StatusTag } from '../components/StatusTag'
import { getTutorials, listTrainings, type ApiTraining, type TutorialProgressSummary } from '../api/client'

const TYPE_OPTIONS = ['全部', '带货', '娱乐互动', '知识内容'] as const

function formatDate(value: string | null): string {
  if (!value) return '时间未记录'
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

function minutesOf(sec: number | null): string {
  if (sec === null || sec === undefined) return '—'
  return `${Math.round(sec / 60)} 分钟`
}

export default function GrowthPage() {
  const navigate = useNavigate()
  const [records, setRecords] = useState<ApiTraining[]>([])
  const [tutorialProgress, setTutorialProgress] = useState<TutorialProgressSummary>({ completed_ids: [], completed_count: 0, total: 0 })
  const [type, setType] = useState<(typeof TYPE_OPTIONS)[number]>('全部')

  useEffect(() => {
    let cancelled = false
    void Promise.all([listTrainings(), getTutorials()])
      .then(([list, catalog]) => {
        if (!cancelled) {
          setRecords(list)
          setTutorialProgress(catalog.progress)
        }
      })
      .catch(() => {})
    return () => { cancelled = true }
  }, [])

  const filtered = useMemo(() => {
    return records.filter((t) => type === '全部' || t.live_type === type)
  }, [records, type])

  const totalCount = records.length
  const totalDuration = records.reduce((sum, t) => sum + (t.media?.duration_sec ?? 0), 0)

  return (
    <div className="page">
      <PageHeader title="成长记录" subtitle="看见每一次练习带来的具体进步，而不是只看总分。" />

      <div className="metric-grid">
        <MetricCard label="累计练习" value={totalCount} unit="场" hint="来自真实训练记录" />
        <MetricCard label="累计时长" value={Math.round(totalDuration / 60)} unit="分钟" hint="已保存媒体时长之和" brand />
        <MetricCard label="教程进度" value={tutorialProgress.completed_count} unit={`/ ${tutorialProgress.total} 节`} hint="后端保存的学习记录" />
      </div>

      <div className="growth-main mt-6">
        <Card>
          <div className="growth-filters">
            <div>
              <span className="filter-label">直播类型</span>
              <div className="chip-row">
                {TYPE_OPTIONS.map((t) => (
                  <button
                    key={t}
                    className={type === t ? 'chip chip--active chip--sm' : 'chip chip--sm'}
                    onClick={() => setType(t)}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="mt-4">
            <p className="text-sm text-secondary">
              表达流畅度、互动能力等评分口径尚在积累样本，暂不展示百分比趋势；下方只列出可核验的真实练习记录。
            </p>
          </div>
        </Card>
        <aside className="growth-insight frosted">
          <span>真实统计</span>
          <strong>本周训练</strong>
          <small>累计已完成</small>
          <b>{totalCount} <i>场</i></b>
          <p>练习记录与时长均来自后端持久化训练，不使用演示数字。</p>
          <button className="text-link mt-3" onClick={() => navigate('/tutorials')}>继续学习教程 <ChevronRight size={14} aria-hidden /></button>
        </aside>
      </div>

      <section className="section mt-6">
        <h2 className="section-title">练习记录</h2>
        <Card>
          {filtered.length === 0 ? (
            <p className="text-sm text-tertiary">还没有已完成的练习，先开始一场吧。</p>
          ) : (
            <ul className="recent-list">
              {filtered.map((t) => (
                <li key={t.id}>
                  <button className="recent-item" onClick={() => navigate(`/reports/${t.id}`)}>
                    <span className="recent-item__goal">{t.goal}</span>
                    <span className="recent-item__meta">
                      <StatusTag tone="neutral">{t.live_type}</StatusTag>
                      <span className="text-xs text-tertiary">
                        {formatDate(t.finished_at ?? t.created_at)} · {minutesOf(t.media?.duration_sec ?? null)} · {t.practice_mode === 'focus' ? '难点练习' : '完整模拟'}
                      </span>
                    </span>
                    <ChevronRight size={16} className="text-tertiary" aria-hidden />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </section>
    </div>
  )
}
