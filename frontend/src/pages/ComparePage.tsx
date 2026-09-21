import { useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, ArrowLeftRight, RotateCcw } from 'lucide-react'
import { PageHeader } from '../components/PageHeader'
import { Card } from '../components/Card'
import { Button } from '../components/Button'
import { StatusTag } from '../components/StatusTag'
import { FrostedInsightCard } from '../components/FrostedInsightCard'
import { VideoPreview } from '../components/VideoPreview'
import { getReport } from '../data/mock'

export default function ComparePage() {
  const { id } = useParams()
  const navigate = useNavigate()

  const current = getReport(id ?? '') ?? getReport('r6')!
  const previous = getReport('r1')!

  const deltas = current.dimensions.map((d) => {
    const before = previous.dimensions.find((p) => p.name === d.name)?.score ?? 0
    const delta = d.score - before
    return { name: d.name, before, after: d.score, delta }
  })

  return (
    <div className="page">
      <PageHeader
        title="重练前后对比"
        subtitle={`同一任务「${current.title}」的两次表现对比`}
        actions={
          <>
            <Button variant="secondary" onClick={() => navigate(`/reports/${current.id}`)}>
              <ArrowLeft size={16} aria-hidden /> 返回训练报告
            </Button>
            <Button onClick={() => navigate('/practice/focus')}>
              <RotateCcw size={16} aria-hidden /> 再次重练
            </Button>
          </>
        }
      />

      <div className="compare-videos">
        <div className="compare-video">
          <div className="compare-video__label">
            <StatusTag tone="neutral">上次</StatusTag>
            <span className="text-xs text-tertiary">{previous.date}</span>
          </div>
          <VideoPreview label="上次录像" />
        </div>
        <div className="compare-video">
          <div className="compare-video__label">
            <StatusTag tone="brand">本次</StatusTag>
            <span className="text-xs text-tertiary">{current.date}</span>
          </div>
          <VideoPreview label="本次录像" />
        </div>
      </div>

      <Card className="mt-6">
        <h3 className="text-lg semibold mb-4">变化对比</h3>
        <table className="table">
          <thead>
            <tr>
              <th>能力维度</th>
              <th>上次</th>
              <th>本次</th>
              <th>变化</th>
            </tr>
          </thead>
          <tbody>
            {deltas.map((d) => (
              <tr key={d.name}>
                <td className="medium">{d.name}</td>
                <td>{d.before}</td>
                <td className="semibold text-brand">{d.after}</td>
                <td>
                  <StatusTag tone={d.delta >= 0 ? 'success' : 'danger'}>
                    {d.delta >= 0 ? `+${d.delta}` : d.delta}
                  </StatusTag>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <div className="mt-4">
        <FrostedInsightCard title="进步小结">
          本次在表达结构上明显更清晰：开场给出了利益点，报价节奏更从容。冷场衔接仍可继续练习。
        </FrostedInsightCard>
      </div>

      <div className="row gap-3 mt-6">
        <Button variant="secondary" onClick={() => navigate(`/reports/${current.id}`)}>
          <ArrowLeftRight size={16} aria-hidden /> 查看本次完整报告
        </Button>
      </div>
    </div>
  )
}
