import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { CheckCircle2, Lightbulb, Pause, Play, Square } from 'lucide-react'
import { Button } from '../components/Button'
import { Modal } from '../components/Modal'
import { StatusTag } from '../components/StatusTag'
import { useApp } from '../store/AppContext'
import { focusSessions, formatSec } from '../data/mock'

type FocusStatus = 'idle' | 'answering' | 'paused' | 'done'

const TOPIC_REPORT: Record<string, string> = {
  开场留人: 'r6',
  弹幕应答: 'r5',
  冷场处理: 'r4',
  报价表达: 'r3',
  知识结构: 'r2',
}

export default function FocusPracticePage() {
  const navigate = useNavigate()
  const { draft, showToast } = useApp()

  const session = focusSessions[draft.topic] ?? focusSessions['开场留人']
  const [status, setStatus] = useState<FocusStatus>('idle')
  const [elapsed, setElapsed] = useState(0)
  const [hintIndex, setHintIndex] = useState(0)
  const [confirmDone, setConfirmDone] = useState(false)
  const elapsedRef = useRef(0)

  useEffect(() => {
    if (status !== 'answering') return
    const timer = window.setInterval(() => {
      elapsedRef.current += 1
      setElapsed(elapsedRef.current)
    }, 1000)
    const hintTimer = window.setInterval(() => {
      setHintIndex((i) => (i + 1) % session.hints.length)
    }, 8000)
    return () => {
      window.clearInterval(timer)
      window.clearInterval(hintTimer)
    }
  }, [status, session.hints.length])

  const start = () => {
    elapsedRef.current = 0
    setElapsed(0)
    setHintIndex(0)
    setStatus('answering')
  }
  const pause = () => setStatus('paused')
  const resume = () => setStatus('answering')
  const requestDone = () => {
    setStatus('paused')
    setConfirmDone(true)
  }
  const finish = () => {
    setConfirmDone(false)
    setStatus('done')
    showToast('本次难点练习已保存', 'success')
    navigate(`/reports/${TOPIC_REPORT[draft.topic] ?? 'r6'}`)
  }

  const isIdle = status === 'idle'
  const isAnswering = status === 'answering'

  return (
    <div className="page page--narrow">
      <div className="focus-head">
        <div>
          <h1 className="text-xl semibold">难点练习 · {session.title}</h1>
          <p className="text-sm text-secondary">
            {draft.liveType} · 目标：{session.goal}
          </p>
        </div>
        <div className="row gap-3">
          <StatusTag tone={isAnswering ? 'brand' : 'neutral'}>
            {isIdle ? '未开始' : isAnswering ? '回答中' : '已暂停'}
          </StatusTag>
          <span className="live-timer">{formatSec(elapsed)}</span>
        </div>
      </div>

      <div className="focus-card">
        <div className="focus-question">
          <span className="focus-question__label">模拟问题</span>
          <p className="focus-question__text">{session.question}</p>
        </div>

        <div className="focus-hints">
          {session.hints.map((h, i) => (
            <span
              key={h}
              className={
                i === hintIndex && isAnswering
                  ? 'focus-hint focus-hint--active'
                  : 'focus-hint'
              }
            >
              {i === hintIndex && isAnswering && (
                <Lightbulb size={12} aria-hidden className="focus-hint__icon" />
              )}
              {h}
            </span>
          ))}
        </div>

        <p className="text-xs text-tertiary">
          提示仅在练习中轻量出现，不打断你的表达节奏。
        </p>
      </div>

      <div className="focus-controls">
        {isIdle && (
          <Button size="lg" onClick={start}>
            <Play size={16} aria-hidden /> 开始回答
          </Button>
        )}
        {isAnswering && (
          <Button variant="secondary" size="lg" onClick={pause}>
            <Pause size={16} aria-hidden /> 暂停
          </Button>
        )}
        {status === 'paused' && (
          <Button size="lg" onClick={resume}>
            <Play size={16} aria-hidden /> 继续
          </Button>
        )}
        {!isIdle && (
          <Button variant="danger" size="lg" onClick={requestDone}>
            <Square size={16} aria-hidden /> 完成回答
          </Button>
        )}
      </div>

      <Modal
        open={confirmDone}
        title="完成本次难点练习？"
        onClose={() => setConfirmDone(false)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setConfirmDone(false)}>
              再练一会儿
            </Button>
            <Button onClick={finish}>
              <CheckCircle2 size={16} aria-hidden /> 完成并查看反馈
            </Button>
          </>
        }
      >
        完成后将基于本次回答生成反馈与下一步练习建议。
      </Modal>
    </div>
  )
}
