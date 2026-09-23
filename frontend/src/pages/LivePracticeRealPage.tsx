import { useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Camera, CameraOff, Mic, MicOff, Pause, Play, Square } from 'lucide-react'
import { Button } from '../components/Button'
import { Card } from '../components/Card'
import { IconButton } from '../components/IconButton'
import { Modal } from '../components/Modal'
import { StatusTag } from '../components/StatusTag'
import { VideoPreview } from '../components/VideoPreview'
import { useApp } from '../store/AppContext'
import { formatSec, type Bullet, type BulletCategory } from '../data/mock'
import {
  finishTraining,
  getTraining,
  trainingSocketUrl,
  type ApiTraining,
} from '../api/client'
import { PcmStreamer, recordingMimeType } from '../media/pcm'

type LiveStatus = 'idle' | 'connecting' | 'running' | 'paused' | 'saving' | 'ended' | 'error'

interface TranscriptLine {
  id: string
  text: string
}

interface SocketMessage {
  type: 'transcript' | 'bullet' | 'asr_error' | 'error'
  kind?: 'partial' | 'final' | string
  text?: string
  start_sec?: number
  at_sec?: number
  bullet_category?: string | null
  scorable?: boolean | null
  message?: string
}

const CATEGORY_MAP: Record<string, BulletCategory> = {
  must_cover: '必考',
  adversarial: '刁难',
  unrelated: '无关',
  ambient_unrelated: '无关',
  bystander: '路人',
  ambient_bystander: '路人',
  noise: '噪声',
  ambient_noise: '噪声',
  related: '追问',
  dynamic: '追问',
  engagement: '话题',
}

function categoryOf(value?: string | null): BulletCategory {
  return CATEGORY_MAP[value ?? ''] ?? '话题'
}

function audioMimeType(): string | null {
  const candidates = ['audio/webm;codecs=opus', 'audio/webm']
  return candidates.find((type) => MediaRecorder.isTypeSupported(type)) ?? null
}

function connectRealtime(
  id: number,
  onMessage: (message: SocketMessage) => void,
): Promise<WebSocket> {
  return new Promise((resolve, reject) => {
    const socket = new WebSocket(trainingSocketUrl(id))
    const timeout = window.setTimeout(() => {
      socket.close()
      reject(new Error('实时识别连接超时，请检查后端服务'))
    }, 10_000)
    socket.onmessage = (event) => {
      try {
        onMessage(JSON.parse(event.data) as SocketMessage)
      } catch {
        // 忽略无法识别的服务端消息，保持训练不中断。
      }
    }
    socket.onopen = () => {
      window.clearTimeout(timeout)
      resolve(socket)
    }
    socket.onerror = () => {
      window.clearTimeout(timeout)
      reject(new Error('无法连接实时识别服务'))
    }
  })
}

export default function LivePracticeRealPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { draft, showToast } = useApp()
  const trainingId = Number(searchParams.get('trainingId'))
  const mode = searchParams.get('mode') === 'focus' ? 'focus' : 'full'

  const [training, setTraining] = useState<ApiTraining | null>(null)
  const [status, setStatus] = useState<LiveStatus>('idle')
  const [elapsed, setElapsed] = useState(0)
  const [bullets, setBullets] = useState<Bullet[]>([])
  const [transcripts, setTranscripts] = useState<TranscriptLine[]>([])
  const [partialTranscript, setPartialTranscript] = useState('')
  const [cameraOn, setCameraOn] = useState(true)
  const [micOn, setMicOn] = useState(true)
  const [confirmEnd, setConfirmEnd] = useState(false)
  const [videoStream, setVideoStream] = useState<MediaStream | null>(null)
  const [loadError, setLoadError] = useState('')
  const [asrMessage, setAsrMessage] = useState('')

  const elapsedRef = useRef(0)
  const statusRef = useRef<LiveStatus>('idle')
  const micOnRef = useRef(true)
  const streamRef = useRef<MediaStream | null>(null)
  const socketRef = useRef<WebSocket | null>(null)
  const recorderRef = useRef<MediaRecorder | null>(null)
  const recorderChunksRef = useRef<Blob[]>([])
  const pcmRef = useRef<PcmStreamer | null>(null)
  const mediaKindRef = useRef<'video' | 'audio'>('video')

  useEffect(() => {
    statusRef.current = status
  }, [status])

  useEffect(() => {
    micOnRef.current = micOn
  }, [micOn])

  useEffect(() => {
    if (!Number.isInteger(trainingId) || trainingId <= 0) {
      setLoadError('缺少有效的练习编号，请重新创建练习')
      return
    }
    getTraining(trainingId)
      .then((t) => {
        setTraining(t)
        // 摄像头默认按创建练习时的 media_kind：audio 训练不请求视频轨道
        setCameraOn(t.media_kind === 'video')
        mediaKindRef.current = t.media_kind === 'audio' ? 'audio' : 'video'
      })
      .catch((error) => setLoadError(error instanceof Error ? error.message : '读取练习失败'))
  }, [trainingId])

  useEffect(() => {
    if (status !== 'running') return
    const timer = window.setInterval(() => {
      elapsedRef.current += 1
      setElapsed(elapsedRef.current)
    }, 1000)
    return () => window.clearInterval(timer)
  }, [status])

  useEffect(() => {
    return () => {
      socketRef.current?.close()
      const recorder = recorderRef.current
      if (recorder && recorder.state !== 'inactive') recorder.stop()
      streamRef.current?.getTracks().forEach((track) => track.stop())
      void pcmRef.current?.stop()
    }
  }, [])

  const handleSocketMessage = (message: SocketMessage) => {
    if (message.type === 'transcript' && message.text) {
      if (message.kind === 'final') {
        setTranscripts((previous) => [
          ...previous,
          { id: `transcript-${Date.now()}-${previous.length}`, text: message.text ?? '' },
        ])
        setPartialTranscript('')
      } else {
        setPartialTranscript(message.text)
      }
      return
    }
    if (message.type === 'bullet' && message.text) {
      setBullets((previous) => [
        ...previous,
        {
          id: `bullet-${Date.now()}-${previous.length}`,
          text: message.text ?? '',
          category: categoryOf(message.bullet_category),
          atSec: message.at_sec ?? elapsedRef.current,
          scorable: message.scorable ?? true,
        },
      ])
      return
    }
    if (message.type === 'asr_error' || message.type === 'error') {
      setAsrMessage(message.message ?? '实时识别暂时不可用')
    }
  }

  const start = async () => {
    if (!training) return
    setStatus('connecting')
    setLoadError('')
    setAsrMessage('')
    try {
      if (!navigator.mediaDevices?.getUserMedia) throw new Error('当前浏览器不支持摄像头和麦克风')
      // 麦克风必需、摄像头可选：关闭摄像头时只申请音频轨道，不创建黑色视频轨道
      const mediaKind: 'video' | 'audio' = cameraOn ? 'video' : 'audio'
      const mimeType = mediaKind === 'video' ? recordingMimeType() : audioMimeType()
      if (!mimeType) throw new Error('当前浏览器不支持 WebM 录制，请使用最新版 Chrome 或 Edge')
      const stream = await navigator.mediaDevices.getUserMedia({
        video: mediaKind === 'video',
        audio: true,
      })
      if (!stream.getAudioTracks().length) throw new Error('未获取到麦克风，请允许浏览器访问麦克风')
      streamRef.current = stream
      setVideoStream(mediaKind === 'video' ? stream : null)
      mediaKindRef.current = mediaKind
      const socket = await connectRealtime(training.id, handleSocketMessage)
      socketRef.current = socket
      const recorder = new MediaRecorder(stream, { mimeType })
      recorderChunksRef.current = []
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) recorderChunksRef.current.push(event.data)
      }
      recorderRef.current = recorder
      const pcm = new PcmStreamer()
      pcmRef.current = pcm
      statusRef.current = 'running'
      setStatus('running')
      recorder.start(1000)
      await pcm.start(stream, (chunk) => {
        if (micOnRef.current && statusRef.current === 'running' && socket.readyState === WebSocket.OPEN) {
          socket.send(chunk)
        }
      })
      elapsedRef.current = 0
      setElapsed(0)
      setBullets([])
      setTranscripts([])
      setPartialTranscript('')
    } catch (error) {
      socketRef.current?.close()
      streamRef.current?.getTracks().forEach((track) => track.stop())
      streamRef.current = null
      setVideoStream(null)
      setStatus('error')
      const message = error instanceof Error ? error.message : '无法开始练习'
      setLoadError(message)
      showToast(message, 'error')
    }
  }

  const pause = async () => {
    if (recorderRef.current?.state === 'recording') recorderRef.current.pause()
    await pcmRef.current?.pause()
    statusRef.current = 'paused'
    setStatus('paused')
  }

  const resume = async () => {
    if (recorderRef.current?.state === 'paused') recorderRef.current.resume()
    await pcmRef.current?.resume()
    statusRef.current = 'running'
    setStatus('running')
  }

  const requestEnd = () => {
    if (status === 'running') void pause()
    if (status === 'running' || status === 'paused') setConfirmEnd(true)
  }

  const stopRecorder = (): Promise<Blob> => {
    const recorder = recorderRef.current
    if (!recorder) return Promise.reject(new Error('没有可保存的录像'))
    return new Promise((resolve, reject) => {
      recorder.addEventListener(
        'stop',
        () => {
          const kind = mediaKindRef.current
          const blob = new Blob(recorderChunksRef.current, {
            type: kind === 'audio' ? 'audio/webm' : 'video/webm',
          })
          if (blob.size === 0) reject(new Error('录像为空，请重新练习'))
          else resolve(blob)
        },
        { once: true },
      )
      if (recorder.state === 'paused') recorder.resume()
      recorder.stop()
    })
  }

  const closeRealtime = async () => {
    const socket = socketRef.current
    if (!socket || socket.readyState >= WebSocket.CLOSING) return
    await new Promise<void>((resolve) => {
      const timeout = window.setTimeout(resolve, 3500)
      socket.addEventListener('close', () => {
        window.clearTimeout(timeout)
        resolve()
      }, { once: true })
      socket.send(JSON.stringify({ type: 'end' }))
    })
    if (socket.readyState < WebSocket.CLOSING) socket.close()
  }

  const finish = async () => {
    if (!training) return
    setConfirmEnd(false)
    statusRef.current = 'saving'
    setStatus('saving')
    try {
      const recordingPromise = stopRecorder()
      await pcmRef.current?.stop()
      await closeRealtime()
      const recording = await recordingPromise
      streamRef.current?.getTracks().forEach((track) => track.stop())
      streamRef.current = null
      setVideoStream(null)
      await finishTraining(training.id, recording, elapsedRef.current, mediaKindRef.current)
      setStatus('ended')
      showToast('已保存，正在生成训练反馈', 'success')
      navigate(`/reports/${training.id}`)
    } catch (error) {
      const message = error instanceof Error ? error.message : '保存训练失败'
      setLoadError(message)
      setStatus('error')
      showToast(message, 'error')
    }
  }

  const toggleCamera = () => {
    const next = !cameraOn
    // 仅开始前允许切换（开始后不改变媒体模式，避免录制中出现黑色视频轨）
    if (status !== 'idle' && status !== 'error') return
    setCameraOn(next)
    mediaKindRef.current = next ? 'video' : 'audio'
  }

  const toggleMic = () => {
    const next = !micOn
    streamRef.current?.getAudioTracks().forEach((track) => { track.enabled = next })
    micOnRef.current = next
    setMicOn(next)
  }

  const isRunning = status === 'running'
  const isIdle = status === 'idle' || status === 'error'
  const isBusy = status === 'connecting' || status === 'saving'
  const statusLabel = isRunning
    ? '训练中'
    : status === 'paused'
      ? '已暂停'
      : status === 'connecting'
        ? '正在连接'
        : status === 'saving'
          ? '正在保存'
          : '未开始'

  if (loadError && !training) {
    return (
      <div className="page page--narrow">
        <Card>
          <h1 className="text-xl semibold">无法进入完整模拟直播</h1>
          <p className="text-sm text-secondary mt-3">{loadError}</p>
          <Button className="mt-4" onClick={() => navigate('/practice/new')}>返回创建练习</Button>
        </Card>
      </div>
    )
  }

  return (
    <div className="page live-page">
      <div className="live-header">
        <div>
          <h1 className="text-xl semibold">{mode === 'focus' ? '难点练习' : '完整模拟直播'}</h1>
          <p className="text-sm text-secondary">
            {training?.live_type ?? draft.liveType} · {training?.goal ?? draft.goal} · 模拟观众，不会真实开播
          </p>
        </div>
        <div className="row gap-3">
          <StatusTag tone={isRunning ? 'danger' : 'neutral'}>{statusLabel}</StatusTag>
          <span className="live-timer">{formatSec(elapsed)}</span>
        </div>
      </div>

      {loadError && training ? <p className="live-error mb-4">{loadError}</p> : null}

      <div className="live-grid">
        <div className="live-stage">
          {cameraOn ? (
            <VideoPreview
              live={isRunning}
              label={status === 'connecting' ? '正在连接摄像头…' : '点击开始后显示摄像头画面'}
              stream={videoStream}
              autoPlay
              muted
            />
          ) : (
            <div className="video-preview video-preview--audio">
              <Mic size={30} strokeWidth={1.4} />
              <span>仅音频训练，不显示摄像头画面</span>
            </div>
          )}
          <div className="live-controls">
            <div className="row gap-3">
              <IconButton label={cameraOn ? '关闭摄像头' : '开启摄像头'} bordered onClick={toggleCamera} disabled={isBusy || isRunning || status === 'paused'}>
                {cameraOn ? <Camera size={18} /> : <CameraOff size={18} />}
              </IconButton>
              <IconButton label={micOn ? '关闭麦克风' : '开启麦克风'} bordered onClick={toggleMic} disabled={!videoStream || isBusy}>
                {micOn ? <Mic size={18} /> : <MicOff size={18} />}
              </IconButton>
            </div>
            <div className="row gap-3">
              {isIdle ? (
                <Button onClick={start} disabled={!training || isBusy}>
                  <Play size={16} aria-hidden /> {status === 'error' ? '重新开始' : '开始'}
                </Button>
              ) : null}
              {isRunning ? (
                <Button variant="secondary" onClick={pause}><Pause size={16} aria-hidden /> 暂停</Button>
              ) : null}
              {status === 'paused' ? (
                <Button onClick={resume}><Play size={16} aria-hidden /> 继续</Button>
              ) : null}
              {isRunning || status === 'paused' ? (
                <Button variant="danger" onClick={requestEnd}><Square size={16} aria-hidden /> 结束</Button>
              ) : null}
              {isBusy ? <Button disabled>{statusLabel}…</Button> : null}
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
                <p className="text-sm text-tertiary">开始后，模拟观众会根据你的表达陆续发来弹幕。</p>
              ) : bullets.map((bullet) => (
                <div key={bullet.id} className="bullet">
                  <span className="bullet__meta">
                    <span className="text-xs text-tertiary">模拟观众 · {formatSec(bullet.atSec)}</span>
                  </span>
                  <span>{bullet.text}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="live-panel">
            <div className="live-panel__head">
              <span className="medium">实时转写</span>
              <StatusTag tone={isRunning && micOn ? 'success' : 'neutral'}>
                {isRunning && micOn ? '识别中' : micOn ? statusLabel : '已静音'}
              </StatusTag>
            </div>
            <div className="live-panel__body" aria-live="polite">
              {asrMessage ? <p className="text-sm text-danger">{asrMessage}</p> : null}
              {transcripts.length === 0 && !partialTranscript ? (
                <p className="text-sm text-tertiary">开始后，你说的话会通过后端实时转写。</p>
              ) : (
                <div className="transcript-lines">
                  {transcripts.map((line) => <p className="transcript-line" key={line.id}>{line.text}</p>)}
                  {partialTranscript ? <p className="transcript-line transcript-line--partial">{partialTranscript}</p> : null}
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
            <Button variant="secondary" onClick={() => setConfirmEnd(false)}>继续练习</Button>
            <Button variant="danger" onClick={finish}>确认结束</Button>
          </>
        }
      >
        结束后将保存本次录像，并由后端生成带时间点证据的练习反馈。
      </Modal>
    </div>
  )
}
