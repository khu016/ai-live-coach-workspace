import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, ArrowLeftRight, RotateCcw } from 'lucide-react'
import { PageHeader } from '../components/PageHeader'
import { Card } from '../components/Card'
import { Button } from '../components/Button'
import { StatusTag } from '../components/StatusTag'
import { FrostedInsightCard } from '../components/FrostedInsightCard'
import { VideoPreview } from '../components/VideoPreview'
import { EmptyState } from '../components/EmptyState'
import {
  getComparison,
  recordingUrl,
  retrain,
  saveTrainingScript,
  type CompareResponse,
} from '../api/client'
import { useApp } from '../store/AppContext'
import LegacyComparePage from './ComparePage'

export default function CompareConnectedPage() {
  const { id } = useParams()
  const numericId = Number(id)
  const navigate = useNavigate()
  const { showToast } = useApp()
  const [comparison, setComparison] = useState<CompareResponse | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const isBackendComparison = Number.isInteger(numericId) && numericId > 0

  useEffect(() => {
    if (!isBackendComparison) return
    getComparison(numericId)
      .then(setComparison)
      .catch((caught) => setError(caught instanceof Error ? caught.message : '读取重练对比失败'))
  }, [isBackendComparison, numericId])

  const rows = useMemo(() => {
    if (!comparison) return []
    const dimensions = new Set([
      ...comparison.previous.issues.map((issue) => issue.dimension),
      ...comparison.current.issues.map((issue) => issue.dimension),
    ])
    return Array.from(dimensions).map((dimension) => {
      const before = comparison.previous.issues.filter((issue) => issue.dimension === dimension).length
      const after = comparison.current.issues.filter((issue) => issue.dimension === dimension).length
      return { dimension, before, after, delta: after - before }
    })
  }, [comparison])

  if (!isBackendComparison) return <LegacyComparePage />

  const startRetrain = async () => {
    if (!comparison) return
    setBusy(true)
    try {
      const result = await retrain(comparison.current.training.id)
      saveTrainingScript(result.training.id, result.script)
      navigate(`/practice/live?trainingId=${result.training.id}`)
    } catch (caught) {
      showToast(caught instanceof Error ? caught.message : '创建重练失败', 'error')
      setBusy(false)
    }
  }

  if (error) {
    return (
      <div className="page">
        <Card>
          <EmptyState
            title="暂时无法生成前后对比"
            description={error}
            action={<Button onClick={() => navigate(`/reports/${numericId}`)}>返回训练报告</Button>}
          />
        </Card>
      </div>
    )
  }

  if (!comparison) {
    return (
      <div className="page page--narrow">
        <Card className="report-processing">
          <span className="report-processing__spinner" aria-hidden />
          <div>
            <h1 className="text-xl semibold">正在读取重练记录</h1>
            <p className="text-sm text-secondary mt-2">系统正在对齐两次训练的录像和问题证据。</p>
          </div>
        </Card>
      </div>
    )
  }

  const current = comparison.current
  const previous = comparison.previous
  const beforeTop = previous.top_issue_ids.length
  const afterTop = current.top_issue_ids.length

  return (
    <div className="page">
      <PageHeader
        title="重练前后对比"
        subtitle={`同一任务「${current.training.goal}」的两次真实训练记录`}
        actions={
          <>
            <Button variant="secondary" onClick={() => navigate(`/reports/${current.training.id}`)}>
              <ArrowLeft size={16} aria-hidden /> 返回训练报告
            </Button>
            <Button onClick={startRetrain} disabled={busy}>
              <RotateCcw size={16} aria-hidden /> {busy ? '正在创建…' : '再次重练'}
            </Button>
          </>
        }
      />

      <div className="compare-videos">
        <div className="compare-video">
          <div className="compare-video__label">
            <StatusTag tone="neutral">上次</StatusTag>
            <span className="text-xs text-tertiary">训练 #{previous.training.id}</span>
          </div>
          <VideoPreview label="上次录像" src={recordingUrl(previous.training.id)} controls />
        </div>
        <div className="compare-video">
          <div className="compare-video__label">
            <StatusTag tone="brand">本次</StatusTag>
            <span className="text-xs text-tertiary">训练 #{current.training.id}</span>
          </div>
          <VideoPreview label="本次录像" src={recordingUrl(current.training.id)} controls />
        </div>
      </div>

      <Card className="mt-6">
        <h3 className="text-lg semibold mb-2">问题证据变化</h3>
        <p className="text-sm text-secondary mb-4">这里比较两次报告中形成证据的问题数量，不把数量换算成虚构分数。</p>
        {rows.length === 0 ? (
          <p className="text-sm text-tertiary">两次训练均未形成可比较的问题证据。</p>
        ) : (
          <table className="table">
            <thead>
              <tr><th>反馈维度</th><th>上次问题数</th><th>本次问题数</th><th>变化</th></tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.dimension}>
                  <td className="medium">{row.dimension}</td>
                  <td>{row.before}</td>
                  <td className="semibold text-brand">{row.after}</td>
                  <td>
                    <StatusTag tone={row.delta <= 0 ? 'success' : 'warning'}>
                      {row.delta > 0 ? `+${row.delta}` : row.delta}
                    </StatusTag>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      <div className="mt-4">
        <FrostedInsightCard title="对比说明">
          上次有 {beforeTop} 个优先问题，本次有 {afterTop} 个。请结合两侧录像和具体证据判断变化，AI 不自动给出上播结论。
        </FrostedInsightCard>
      </div>

      <div className="row gap-3 mt-6">
        <Button variant="secondary" onClick={() => navigate(`/reports/${current.training.id}`)}>
          <ArrowLeftRight size={16} aria-hidden /> 查看本次完整报告
        </Button>
      </div>
    </div>
  )
}
