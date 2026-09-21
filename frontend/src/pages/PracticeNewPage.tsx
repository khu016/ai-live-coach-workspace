import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Camera, CameraOff, Mic, MicOff, Play, RefreshCw } from 'lucide-react'
import { PageHeader } from '../components/PageHeader'
import { Card } from '../components/Card'
import { Button } from '../components/Button'
import { Toggle } from '../components/Toggle'
import { StatusTag } from '../components/StatusTag'
import { VideoPreview } from '../components/VideoPreview'
import { useApp } from '../store/AppContext'
import {
  FOCUS_TOPICS,
  LIVE_TYPES,
  type LiveType,
  type PracticeMode,
} from '../data/mock'

const FULL_TOPICS = ['综合练习', '开场留人', '弹幕应答', '冷场处理', '报价表达']

export default function PracticeNewPage() {
  const navigate = useNavigate()
  const { setDraft, showToast } = useApp()
  const [searchParams] = useSearchParams()

  const [mode, setMode] = useState<PracticeMode>(
    searchParams.get('mode') === 'focus' ? 'focus' : 'full',
  )
  const [liveType, setLiveType] = useState<LiveType>('带货')
  const [topic, setTopic] = useState(mode === 'focus' ? '开场留人' : '综合练习')
  const [cameraOn, setCameraOn] = useState(true)
  const [micOn, setMicOn] = useState(true)
  const [checking, setChecking] = useState(false)
  const [checked, setChecked] = useState(false)

  const topics = mode === 'focus' ? FOCUS_TOPICS : FULL_TOPICS

  const switchMode = (next: PracticeMode) => {
    setMode(next)
    setTopic(next === 'focus' ? '开场留人' : '综合练习')
  }

  const detect = () => {
    setChecking(true)
    setChecked(false)
    window.setTimeout(() => {
      setChecking(false)
      setChecked(true)
      showToast('设备检测完成：摄像头与麦克风可用', 'success')
    }, 900)
  }

  const start = () => {
    const goal = mode === 'full' ? (topic === '综合练习' ? '完整模拟直播' : topic) : topic
    setDraft({ mode, liveType, topic, goal })
    navigate(mode === 'full' ? '/practice/live' : '/practice/focus')
  }

  const canStart = topic.length > 0 && cameraOn && micOn

  return (
    <div className="page page--narrow">
      <PageHeader title="创建练习" subtitle="选择练习方式与主题，确认设备后即可开始。" />

      <section className="section">
        <h2 className="section-title">练习方式</h2>
        <div className="mode-grid">
          <button
            className={mode === 'full' ? 'mode-card mode-card--active' : 'mode-card'}
            onClick={() => switchMode('full')}
          >
            <span className="mode-card__title">完整模拟直播</span>
            <span className="mode-card__desc">完整走一遍开播流程，练表达与互动</span>
          </button>
          <button
            className={mode === 'focus' ? 'mode-card mode-card--active' : 'mode-card'}
            onClick={() => switchMode('focus')}
          >
            <span className="mode-card__title">难点练习</span>
            <span className="mode-card__desc">针对单一难点短练，快速反复</span>
          </button>
        </div>
      </section>

      <section className="section">
        <h2 className="section-title">直播类型</h2>
        <div className="chip-row">
          {LIVE_TYPES.map((t) => (
            <button
              key={t}
              className={liveType === t ? 'chip chip--active' : 'chip'}
              onClick={() => setLiveType(t)}
            >
              {t}
            </button>
          ))}
        </div>
      </section>

      <section className="section">
        <h2 className="section-title">训练主题</h2>
        <div className="chip-row">
          {topics.map((t) => (
            <button
              key={t}
              className={topic === t ? 'chip chip--active' : 'chip'}
              onClick={() => setTopic(t)}
            >
              {t}
            </button>
          ))}
        </div>
      </section>

      <section className="section">
        <h2 className="section-title">设备检测</h2>
        <Card>
          <div className="device-grid">
            <VideoPreview label="摄像头预览" className="device-preview" />
            <div className="device-panel">
              <div className="device-row">
                <span className="device-row__icon">
                  {cameraOn ? <Camera size={18} aria-hidden /> : <CameraOff size={18} aria-hidden />}
                </span>
                <span className="device-row__text">
                  <span className="medium">摄像头</span>
                  <span className="text-xs text-tertiary">FaceTime HD 摄像头</span>
                </span>
                <Toggle
                  checked={cameraOn}
                  onChange={setCameraOn}
                  label="摄像头"
                  id="dev-camera"
                />
              </div>
              <div className="device-row">
                <span className="device-row__icon">
                  {micOn ? <Mic size={18} aria-hidden /> : <MicOff size={18} aria-hidden />}
                </span>
                <span className="device-row__text">
                  <span className="medium">麦克风</span>
                  <span className="text-xs text-tertiary">内置麦克风</span>
                </span>
                <Toggle checked={micOn} onChange={setMicOn} label="麦克风" id="dev-mic" />
              </div>
              <div className="device-row device-row--check">
                <span className="text-sm text-secondary">
                  {checking
                    ? '正在检测设备…'
                    : checked
                      ? '设备就绪，可以开始练习'
                      : '开始前建议先检测一次设备'}
                </span>
                {checked && <StatusTag tone="success">就绪</StatusTag>}
                <Button variant="secondary" size="sm" onClick={detect} disabled={checking}>
                  <RefreshCw size={14} aria-hidden className={checking ? 'spin' : ''} />
                  {checking ? '检测中' : '检测设备'}
                </Button>
              </div>
            </div>
          </div>
        </Card>
      </section>

      <div className="section">
        <Button size="lg" block onClick={start} disabled={!canStart}>
          <Play size={16} aria-hidden />
          开始练习
        </Button>
        {!cameraOn || !micOn ? (
          <p className="text-xs text-tertiary mt-2" style={{ textAlign: 'center' }}>
            请先开启摄像头和麦克风
          </p>
        ) : null}
      </div>
    </div>
  )
}
