import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Camera, CameraOff, Mic, MicOff, Pause, Play, Square } from 'lucide-react'
import { Button } from '../components/Button'
import { IconButton } from '../components/IconButton'
import { Modal } from '../components/Modal'
import { StatusTag } from '../components/StatusTag'
import { VideoPreview } from '../components/VideoPreview'
import { useApp } from '../store/AppContext'
import { bulletPool, formatSec, type Bullet } from '../data/mock'

type LiveStatus = 'idle' | 'running' | 'paused' | 'ended'

const BULLET_TONE: Record<Bullet['category'], 'brand' | 'neutral' | 'warning'> = {
  必考: 'brand',
  刁难: 'warning',
  追问: 'brand',
  无关: 'neutral',
  路人: 'neutral',
  噪声: 'neutral',
  话题: 'brand',
}

export default function LivePracticePage() {
  const navigate = useNavigate()
  const { draft, showToast } = useApp()

  const [status, setStatus] = useState<LiveStatus>('idle')
  const [elapsed, setElapsed] = useState(0)
  const [bullets, setBullets] = useState<Bullet[]>([])
  const [cameraOn, setCameraOn] = useState(true)
  const [micOn, setMicOn] = useState(true)
  const [confirmEnd, setConfirmEnd] = useState(false)
  const elapsedRef = useRef(0)

  useEffect(() => {
    if (status !== 'running') return
    const timer = window.setInterval(() => {
      elapsedRef.current += 1
      setElapsed(elapsedRef.current)
    }, 1000)
    const bulletTimer = window.setInterval(() => {
      setBullets((prev) => {
        if (prev.length >= bulletPool.length) return prev
        const next = bulletPool[prev.length]
        return [...prev, { ...next, atSec: elapsedRef.current }]
      })
    }, 3000)
    return () => {
      window.clearInterval(timer)
      window.clearInterval(bulletTimer)
    }
  }, [status])

  const start = () => {
    elapsedRef.current = 0
    setElapsed(0)
    setBullets([bulletPool[0]])
    setStatus('running')
  }

  const pause = () => setStatus('paused')
  const resume = () => setStatus('running')

  const requestEnd = () => {
    if (status === 'running' || status === 'paused') {
      setStatus('paused')
      setConfirmEnd(true)
    }
  }

  const finish = () => {
    setConfirmEnd(false)
    setStatus('ended')
    showToast('本次训练已保存', 'success')
    navigate('/reports/r6')
  }

  const isRunning = status === 'running'
  const isIdle = status === 'idle'

  return (
    <div className="page live-page">
      <div className="live-header">
        <div>
          <h1 className="text-xl semibold">完整模拟直播</h1>
          <p className="text-sm text-secondary">
            {draft.liveType} · {draft.goal} · 模拟观众，不会真实开播
          </p>
        </div>
        <div className="row gap-3">
          <StatusTag tone={isRunning ? 'danger' : 'neutral'}>
            {isRunning ? '直播中' : isIdle ? '未开始' : '已暂停'}
          </StatusTag>
          <span className="live-timer">{formatSec(elapsed)}</span>
        </div>
      </div>

      <div className="live-grid">
        <div className="live-stage">
          <VideoPreview live={isRunning} label={isRunning ? '直播进行中' : '待开始'} />
          <div className="live-controls">
            <div className="row gap-3">
              <IconButton
                label={cameraOn ? '关闭摄像头' : '开启摄像头'}
                bordered
                onClick={() => setCameraOn((v) => !v)}
              >
                {cameraOn ? <Camera size={18} /> : <CameraOff size={18} />}
              </IconButton>
              <IconButton
                label={micOn ? '关闭麦克风' : '开启麦克风'}
                bordered
                onClick={() => setMicOn((v) => !v)}
              >
                {micOn ? <Mic size={18} /> : <MicOff size={18} />}
              </IconButton>
            </div>
            <div className="row gap-3">
              {isIdle && (
                <Button onClick={start}>
                  <Play size={16} aria-hidden /> 开始
                </Button>
              )}
              {isRunning && (
                <Button variant="secondary" onClick={pause}>
                  <Pause size={16} aria-hidden /> 暂停
                </Button>
              )}
              {status === 'paused' && (
                <Button onClick={resume}>
                  <Play size={16} aria-hidden /> 继续
                </Button>
              )}
              {!isIdle && (
                <Button variant="danger" onClick={requestEnd}>
                  <Square size={16} aria-hidden /> 结束
                </Button>
              )}
            </div>
          </div>
        </div>

        <div className="live-side">
          <div className="live-panel">
            <div className="live-panel__head">
              <span className="medium">模拟观众弹幕</span>
              <span className="text-xs text-tertiary">{bullets.length} 条</span>
            </div>
            <div className="live-panel__body" aria-live="polite">
              {bullets.length === 0 ? (
                <p className="text-sm text-tertiary">开始后，模拟观众会陆续发来弹幕…</p>
              ) : (
                bullets.map((b) => (
                  <div key={b.id} className="bullet">
                    <span className="bullet__meta">
                      <StatusTag tone={BULLET_TONE[b.category]}>{b.category}</StatusTag>
                      <span className="text-xs text-tertiary">{formatSec(b.atSec)}</span>
                    </span>
                    <span>{b.text}</span>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="live-panel">
            <div className="live-panel__head">
              <span className="medium">实时转写</span>
              <StatusTag tone={micOn ? 'success' : 'neutral'}>
                {micOn ? '识别中' : '已静音'}
              </StatusTag>
            </div>
            <div className="live-panel__body">
              {isIdle ? (
                <p className="text-sm text-tertiary">开始后，你说的话会实时转写成文字。</p>
              ) : (
                <div className="transcript-lines">
                  <p className="transcript-line">大家好，欢迎来到我的直播间…</p>
                  <p className="transcript-line">今天主要想和大家聊一下夏季护肤…</p>
                  <p className="transcript-line transcript-line--partial">
                    这款产品其实最关键的是…
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      <Modal
        open={confirmEnd}
        title="结束本次训练？"
        onClose={() => setConfirmEnd(false)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setConfirmEnd(false)}>
              继续练习
            </Button>
            <Button variant="danger" onClick={finish}>
              确认结束
            </Button>
          </>
        }
      >
        结束后将保存本次录像，并生成带时间点证据的练习反馈。
      </Modal>
    </div>
  )
}
