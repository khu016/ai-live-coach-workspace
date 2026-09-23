import { useEffect, useState } from 'react'
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
import { createTraining, saveTrainingScript } from '../api/client'

const FULL_TOPICS = ['综合练习', '开场留人', '弹幕应答', '冷场处理', '报价表达']

export default function PracticeNewPage() {
  const navigate = useNavigate()
  const { setDraft, showToast } = useApp()
  const [searchParams] = useSearchParams()

  const [mode, setMode] = useState<PracticeMode>(
    searchParams.get('mode') === 'focus' ? 'focus' : 'full',
  )
  const [liveType, setLiveType] = useState<LiveType>('带货')
  const requestedTopic = searchParams.get('topic')
  const [topic, setTopic] = useState(
    mode === 'focus' && requestedTopic && FOCUS_TOPICS.includes(requestedTopic)
      ? requestedTopic
      : mode === 'focus'
        ? '开场留人'
        : '综合练习',
  )
  // 摄像头可选，默认开启；麦克风必需，默认开启
  const [cameraOn, setCameraOn] = useState(true)
  const [micOn, setMicOn] = useState(true)
  const [checking, setChecking] = useState(false)
  const [checked, setChecked] = useState(false)
  const [starting, setStarting] = useState(false)
  const [previewStream, setPreviewStream] = useState<MediaStream | null>(null)

  const topics = mode === 'focus' ? FOCUS_TOPICS : FULL_TOPICS

  const switchMode = (next: PracticeMode) => {
    setMode(next)
    setTopic(next === 'focus' ? '开场留人' : '综合练习')
  }

  useEffect(() => {
    return () => previewStream?.getTracks().forEach((track) => track.stop())
  }, [previewStream])

  const resetPreview = () => {
    previewStream?.getTracks().forEach((track) => track.stop())
    setPreviewStream(null)
    setChecked(false)
  }

  const detect = async () => {
    setChecking(true)
    setChecked(false)
    previewStream?.getTracks().forEach((track) => track.stop())
    try {
      if (!navigator.mediaDevices?.getUserMedia) throw new Error('当前浏览器不支持设备检测')
      if (!micOn) throw new Error('麦克风是语音训练必需设备，请先开启麦克风')
      // 麦克风必需：先单独申请音频轨道
      const audioStream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const combined = audioStream
      // 摄像头可选：开启时再申请视频轨道，失败则降级为仅音频
      if (cameraOn) {
        try {
          const videoStream = await navigator.mediaDevices.getUserMedia({ video: true })
          videoStream.getTracks().forEach((track) => combined.addTrack(track))
        } catch {
          setCameraOn(false)
          showToast('摄像头不可用，本次将只保存音频', 'error')
        }
      }
      setPreviewStream(combined)
      setChecked(true)
      showToast(cameraOn ? '设备检测完成：摄像头与麦克风可用' : '设备检测完成：仅音频训练', 'success')
    } catch (error) {
      const message = error instanceof Error ? error.message : '无法访问麦克风'
      showToast(`${message}，请在浏览器设置中允许访问麦克风`, 'error')
      setPreviewStream(null)
    } finally {
      setChecking(false)
    }
  }

  const start = async () => {
    const goal = mode === 'full' ? (topic === '综合练习' ? '完整模拟直播' : topic) : topic
    const mediaKind: 'video' | 'audio' = cameraOn ? 'video' : 'audio'
    setDraft({ mode, liveType, topic, goal })
    setStarting(true)
    try {
      // 难点练习与完整模拟共用真实训练链路，仅 practice_mode 不同
      const result = await createTraining({
        live_type: liveType,
        goal,
        topic,
        practice_mode: mode,
        media_kind: mediaKind,
      })
      saveTrainingScript(result.training.id, result.script)
      resetPreview()
      const query = `trainingId=${result.training.id}`
        + (mode === 'focus' ? `&mode=focus&topic=${encodeURIComponent(topic)}` : '')
      navigate(`/practice/live?${query}`)
    } catch (error) {
      showToast(error instanceof Error ? error.message : '创建练习失败', 'error')
      setStarting(false)
    }
  }

  // 麦克风必需；摄像头可选
  const canStart = topic.length > 0 && micOn && checked && !starting

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
            {cameraOn ? (
              <VideoPreview
                label="检测后显示摄像头画面"
                className="device-preview"
                stream={previewStream}
                autoPlay
                muted
              />
            ) : (
              <div className="device-preview device-preview--audio">
                <Mic size={30} strokeWidth={1.4} />
                <span>仅音频训练，不显示摄像头画面</span>
              </div>
            )}
            <div className="device-panel">
              <div className="device-row">
                <span className="device-row__icon">
                  {cameraOn ? <Camera size={18} aria-hidden /> : <CameraOff size={18} aria-hidden />}
                </span>
                <span className="device-row__text">
                  <span className="medium">摄像头</span>
                  <span className="text-xs text-tertiary">可选 · 关闭后仅保存音频</span>
                </span>
                <Toggle
                  checked={cameraOn}
                  onChange={(next) => {
                    setCameraOn(next)
                    resetPreview()
                  }}
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
                  <span className="text-xs text-tertiary">语音训练必需</span>
                </span>
                <Toggle
                  checked={micOn}
                  onChange={(next) => {
                    setMicOn(next)
                    resetPreview()
                  }}
                  label="麦克风"
                  id="dev-mic"
                />
              </div>
              <div className="device-row device-row--check">
                <span className="text-sm text-secondary">
                  {checking
                    ? '正在检测设备…'
                    : checked
                      ? '设备就绪，可以开始练习'
                      : '开始前请先检测一次设备'}
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
          {starting ? '正在创建练习…' : '开始练习'}
        </Button>
        {!micOn ? (
          <p className="text-xs text-tertiary mt-2" style={{ textAlign: 'center' }}>
            麦克风是语音训练必需设备，请先开启麦克风
          </p>
        ) : !checked ? (
          <p className="text-xs text-tertiary mt-2" style={{ textAlign: 'center' }}>
            请先完成设备检测
          </p>
        ) : null}
      </div>
    </div>
  )
}
