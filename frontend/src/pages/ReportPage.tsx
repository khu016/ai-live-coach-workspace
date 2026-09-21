import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ArrowLeftRight, RotateCcw, VideoOff } from 'lucide-react'
import { PageHeader } from '../components/PageHeader'
import { Card } from '../components/Card'
import { Button } from '../components/Button'
import { StatusTag } from '../components/StatusTag'
import { ProgressBar } from '../components/ProgressBar'
import { FrostedInsightCard } from '../components/FrostedInsightCard'
import { VideoPreview } from '../components/VideoPreview'
import { EmptyState } from '../components/EmptyState'
import { formatSec, getReport } from '../data/mock'

export default function ReportPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const report = getReport(id ?? '')

  const [selectedId, setSelectedId] = useState<string | null>(null)

  if (!report) {
    return (
      <div className="page">
        <Card>
          <EmptyState
            icon={<VideoOff size={22} aria-hidden />}
            title="未找到该训练报告"
            description="报告可能已被删除，或链接有误。"
            action={<Button onClick={() => navigate('/')}>返回首页</Button>}
          />
        </Card>
      </div>
    )
  }

  const durationSec = report.durationMin * 60
  const selected =
    report.issues.find((i) => i.id === selectedId) ?? report.issues[0] ?? null

  const modeLabel = report.mode === 'full' ? '完整模拟' : '难点练习'

  return (
    <div className="page">
      <PageHeader
        title={report.title}
        subtitle={`${report.date} · ${report.liveType} · ${modeLabel} · ${report.durationMin} 分钟`}
        actions={
          <>
            <Button variant="secondary" onClick={() => navigate(`/practice/${report.id}/compare`)}>
              <ArrowLeftRight size={16} aria-hidden /> 查看重练对比
            </Button>
            <Button onClick={() => navigate('/practice/focus')}>
              <RotateCcw size={16} aria-hidden /> 再次练习
            </Button>
          </>
        }
      />

      <div className="report-grid">
        <div className="report-main">
          <VideoPreview label="本次录像回看" />
          <div className="report-timeline-wrap mt-4">
            <div className="timeline" role="group" aria-label="问题标记时间轴">
              <div
                className="timeline__fill"
                style={{ width: `${Math.min(100, (selected?.timeEnd ?? 0) / durationSec) * 100}%` }}
              />
              {report.issues.map((i) => (
                <button
                  key={i.id}
                  className={
                    i.id === selected?.id
                      ? 'timeline__marker timeline__marker--active'
                      : 'timeline__marker'
                  }
                  style={{ left: `${(i.timeStart / durationSec) * 100}%` }}
                  aria-label={`${i.dimension} ${formatSec(i.timeStart)}`}
                  title={`${i.dimension} · ${formatSec(i.timeStart)}`}
                  onClick={() => setSelectedId(i.id)}
                />
              ))}
            </div>
            <div className="row-between mt-2">
              <span className="text-xs text-tertiary">0:00</span>
              <span className="text-xs text-tertiary">点击时间轴标记查看对应证据</span>
              <span className="text-xs text-tertiary">{formatSec(durationSec)}</span>
            </div>
          </div>

          <Card className="mt-4">
            <h3 className="text-lg semibold mb-4">能力维度</h3>
            <div className="dimension-list">
              {report.dimensions.map((d) => (
                <div key={d.name} className="dimension-row">
                  <div className="row-between">
                    <span className="text-sm">{d.name}</span>
                    <span className="text-sm semibold text-brand">{d.score}</span>
                  </div>
                  <ProgressBar value={d.score} />
                </div>
              ))}
            </div>
          </Card>
        </div>

        <div className="report-side">
          {selected && (
            <FrostedInsightCard title="AI 反馈 · 证据片段">
              <p className="mb-2">
                <span className="medium">时间：</span>
                {formatSec(selected.timeStart)}–{formatSec(selected.timeEnd)}
              </p>
              {selected.triggerBullet && (
                <p className="mb-2">
                  <span className="medium">触发弹幕：</span>“{selected.triggerBullet}”
                </p>
              )}
              <p className="mb-2">
                <span className="medium">问题：</span>
                {selected.problem}
              </p>
              <p>
                <span className="medium">建议：</span>
                {selected.suggestion}
              </p>
            </FrostedInsightCard>
          )}

          <div className="mt-4">
            <h3 className="text-lg semibold mb-3">本次发现的问题</h3>
            <div className="issue-list">
              {report.issues.map((i) => (
                <button
                  key={i.id}
                  className={i.id === selected?.id ? 'issue-item issue-item--active' : 'issue-item'}
                  onClick={() => setSelectedId(i.id)}
                >
                  <div className="row-between">
                    <StatusTag tone={i.top ? 'warning' : 'neutral'}>
                      {i.dimension}
                      {i.top ? ' · 优先' : ''}
                    </StatusTag>
                    <span className="text-xs text-tertiary">
                      {formatSec(i.timeStart)}–{formatSec(i.timeEnd)}
                    </span>
                  </div>
                  <p className="issue-item__text">{i.problem}</p>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
