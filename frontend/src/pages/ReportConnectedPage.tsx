import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ArrowLeftRight, Mic, RefreshCw, RotateCcw, VideoOff } from 'lucide-react'
import { PageHeader } from '../components/PageHeader'
import { Card } from '../components/Card'
import { Button } from '../components/Button'
import { StatusTag } from '../components/StatusTag'
import { FrostedInsightCard } from '../components/FrostedInsightCard'
import { VideoPreview } from '../components/VideoPreview'
import { EmptyState } from '../components/EmptyState'
import { formatSec } from '../data/mock'
import {
  getFeedback,
  getTraining,
  recordingUrl,
  retrain,
  retryTraining,
  saveTrainingScript,
  type ApiIssue,
  type ApiTraining,
} from '../api/client'
import { useApp } from '../store/AppContext'
import LegacyReportPage from './ReportPage'

interface LoadedReport {
  training: ApiTraining
  issues: ApiIssue[]
  topIssueIds: number[]
}

function formatDate(value: string | null): string {
  if (!value) return '时间未记录'
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

function ReportMedia({ training }: { training: ApiTraining }) {
  const media = training.media
  if (media?.exists && media.media_kind === 'video') {
    return <VideoPreview label="本次录像回看" src={recordingUrl(training.id)} controls />
  }
  if (media?.exists && media.media_kind === 'audio') {
    return (
      <div className="video-preview video-preview--audio">
        <div className="video-preview__head">
          <Mic size={18} /> 音频回放
        </div>
        <audio controls src={recordingUrl(training.id)} preload="metadata" style={{ width: '100%' }} />
      </div>
    )
  }
  return (
    <div className="video-preview">
      <div className="video-preview__placeholder">
        <VideoOff size={30} strokeWidth={1.4} />
        <span>本次练习没有可回放的媒体</span>
      </div>
    </div>
  )
}

export default function ReportConnectedPage() {
  const { id } = useParams()
  const numericId = Number(id)
  const navigate = useNavigate()
  const { showToast } = useApp()
  const [report, setReport] = useState<LoadedReport | null>(null)
  const [status, setStatus] = useState<ApiTraining['status'] | 'loading'>('loading')
  const [error, setError] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [actionBusy, setActionBusy] = useState(false)

  const isBackendReport = Number.isInteger(numericId) && numericId > 0

  useEffect(() => {
    if (!isBackendReport) return
    let cancelled = false
    let timer = 0
    const load = async () => {
      try {
        const [training, feedback] = await Promise.all([
          getTraining(numericId),
          getFeedback(numericId),
        ])
        if (cancelled) return
        setStatus(feedback.status)
        if (feedback.status === 'feedback_ready' && feedback.feedback) {
          setReport({
            training,
            issues: feedback.feedback.issues,
            topIssueIds: feedback.feedback.top_issue_ids,
          })
          setError('')
          return
        }
        if (feedback.status === 'failed') {
          setError('训练反馈生成失败，可以重新生成。录像已经安全保存。')
          return
        }
        timer = window.setTimeout(load, 1600)
      } catch (caught) {
        if (!cancelled) setError(caught instanceof Error ? caught.message : '读取训练报告失败')
      }
    }
    void load()
    return () => {
      cancelled = true
      window.clearTimeout(timer)
    }
  }, [isBackendReport, numericId])

  const selected = report?.issues[selectedIndex] ?? null
  const durationSec = useMemo(
    () => Math.max(60, ...(report?.issues.map((issue) => issue.end_sec) ?? [60])),
    [report],
  )

  if (!isBackendReport) return <LegacyReportPage />

  const regenerate = async () => {
    setActionBusy(true)
    try {
      await retryTraining(numericId)
      setError('')
      setStatus('analyzing')
      window.location.reload()
    } catch (caught) {
      showToast(caught instanceof Error ? caught.message : '重新生成失败', 'error')
    } finally {
      setActionBusy(false)
    }
  }

  const startRetrain = async () => {
    if (!report) return
    setActionBusy(true)
    try {
      const result = await retrain(report.training.id)
      saveTrainingScript(result.training.id, result.script)
      navigate(`/practice/live?trainingId=${result.training.id}`)
    } catch (caught) {
      showToast(caught instanceof Error ? caught.message : '创建重练失败', 'error')
      setActionBusy(false)
    }
  }

  if (error && status !== 'failed') {
    return (
      <div className="page">
        <Card>
          <EmptyState
            icon={<VideoOff size={22} aria-hidden />}
            title="暂时无法读取训练报告"
            description={error}
            action={<Button onClick={() => navigate('/')}>返回首页</Button>}
          />
        </Card>
      </div>
    )
  }

  if (status === 'failed') {
    return (
      <div className="page page--narrow">
        <Card>
          <h1 className="text-xl semibold">反馈生成失败</h1>
          <p className="text-sm text-secondary mt-3">{error}</p>
          <div className="row gap-3 mt-4">
            <Button onClick={regenerate} disabled={actionBusy}>
              <RefreshCw size={16} aria-hidden /> {actionBusy ? '正在重试…' : '重新生成反馈'}
            </Button>
            <Button variant="secondary" onClick={() => navigate('/')}>返回首页</Button>
          </div>
        </Card>
      </div>
    )
  }

  if (!report) {
    return (
      <div className="page page--narrow">
        <Card className="report-processing">
          <span className="report-processing__spinner" aria-hidden />
          <div>
            <h1 className="text-xl semibold">正在生成训练反馈</h1>
            <p className="text-sm text-secondary mt-2">录像已保存，AI 正在整理转写证据和优先改进项。</p>
          </div>
        </Card>
      </div>
    )
  }

  return (
    <div className="page">
      <PageHeader
        title={report.training.goal}
        subtitle={`${formatDate(report.training.finished_at ?? report.training.created_at)} · ${report.training.live_type} · ${report.training.practice_mode === 'focus' ? '难点练习' : '完整模拟'}`}
        actions={
          <>
            {report.training.prev_training_id ? (
              <Button variant="secondary" onClick={() => navigate(`/practice/${report.training.id}/compare`)}>
                <ArrowLeftRight size={16} aria-hidden /> 查看重练对比
              </Button>
            ) : null}
            <Button onClick={startRetrain} disabled={actionBusy}>
              <RotateCcw size={16} aria-hidden /> {actionBusy ? '正在创建…' : '按同一任务重练'}
            </Button>
          </>
        }
      />

      <div className="report-grid">
        <div className="report-main">
          <ReportMedia training={report.training} />
          {report.issues.length > 0 ? (
            <div className="report-timeline-wrap mt-4">
              <div className="timeline" role="group" aria-label="问题标记时间轴">
                <div className="timeline__fill" style={{ width: `${Math.min(100, ((selected?.end_sec ?? 0) / durationSec) * 100)}%` }} />
                {report.issues.map((issue, index) => (
                  <button
                    key={`${issue.dimension}-${issue.start_sec}-${index}`}
                    className={index === selectedIndex ? 'timeline__marker timeline__marker--active' : 'timeline__marker'}
                    style={{ left: `${Math.min(100, (issue.start_sec / durationSec) * 100)}%` }}
                    aria-label={`${issue.dimension} ${formatSec(issue.start_sec)}`}
                    title={`${issue.dimension} · ${formatSec(issue.start_sec)}`}
                    onClick={() => setSelectedIndex(index)}
                  />
                ))}
              </div>
              <div className="row-between mt-2">
                <span className="text-xs text-tertiary">0:00</span>
                <span className="text-xs text-tertiary">点击时间点查看对应证据</span>
                <span className="text-xs text-tertiary">{formatSec(durationSec)}</span>
              </div>
            </div>
          ) : null}

          <Card className="mt-4">
            <h3 className="text-lg semibold mb-3">报告说明</h3>
            <p className="text-sm text-secondary">
              当前报告直接展示可追溯的问题证据和改进建议，不根据演示数据生成综合分数。
            </p>
          </Card>
        </div>

        <div className="report-side">
          {selected ? (
            <FrostedInsightCard title="AI 反馈 · 证据片段">
              <p className="mb-2"><span className="medium">时间：</span>{formatSec(selected.start_sec)}–{formatSec(selected.end_sec)}</p>
              {selected.trigger_bullet ? <p className="mb-2"><span className="medium">触发弹幕：</span>“{selected.trigger_bullet}”</p> : null}
              <p className="mb-2"><span className="medium">证据：</span>{selected.evidence || '本条反馈未引用可展示的逐字稿。'}</p>
              <p className="mb-2"><span className="medium">问题：</span>{selected.problem}</p>
              <p><span className="medium">建议：</span>{selected.suggestion}</p>
            </FrostedInsightCard>
          ) : (
            <FrostedInsightCard title="本次训练已完成">
              当前转写证据不足以形成明确问题，系统没有为了填满报告而编造结论。
            </FrostedInsightCard>
          )}

          <div className="mt-4">
            <h3 className="text-lg semibold mb-3">本次发现的问题</h3>
            {report.issues.length === 0 ? (
              <p className="text-sm text-tertiary">没有形成可追溯的问题记录。</p>
            ) : (
              <div className="issue-list">
                {report.issues.map((issue, index) => (
                  <button
                    key={`${issue.dimension}-${issue.start_sec}-${index}`}
                    className={index === selectedIndex ? 'issue-item issue-item--active' : 'issue-item'}
                    onClick={() => setSelectedIndex(index)}
                  >
                    <div className="row-between">
                      <StatusTag tone={report.topIssueIds.includes(index) ? 'warning' : 'neutral'}>
                        {issue.dimension}{report.topIssueIds.includes(index) ? ' · 优先' : ''}
                      </StatusTag>
                      <span className="text-xs text-tertiary">{formatSec(issue.start_sec)}–{formatSec(issue.end_sec)}</span>
                    </div>
                    <p className="issue-item__text">{issue.problem}</p>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
