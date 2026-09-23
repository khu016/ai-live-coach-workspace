import { useEffect, useRef, useState, type ReactNode } from 'react'
import { Pause, Play, Video } from 'lucide-react'

export interface VideoPreviewProps {
  label?: string
  badge?: ReactNode
  live?: boolean
  className?: string
  stream?: MediaStream | null
  src?: string
  controls?: boolean
  autoPlay?: boolean
  muted?: boolean
}

export function VideoPreview({
  label,
  badge,
  live = false,
  className = '',
  stream = null,
  src,
  controls = false,
  autoPlay = false,
  muted = false,
}: VideoPreviewProps) {
  const [playing, setPlaying] = useState(false)
  const videoRef = useRef<HTMLVideoElement>(null)
  const hasVideo = Boolean(stream || src)

  useEffect(() => {
    if (!videoRef.current) return
    videoRef.current.srcObject = stream
    return () => {
      if (videoRef.current) videoRef.current.srcObject = null
    }
  }, [stream])

  const togglePlayback = () => {
    const video = videoRef.current
    if (!video) return
    if (video.paused) void video.play()
    else video.pause()
  }

  return (
    <div className={`video-preview ${className}`}>
      {live && (
        <div className="video-preview__live">
          <span className="video-preview__live-dot" />
          直播中
        </div>
      )}
      {badge && <div className="video-preview__badge">{badge}</div>}
      {hasVideo ? (
        <video
          ref={videoRef}
          src={src}
          controls={controls}
          autoPlay={autoPlay}
          muted={muted}
          playsInline
          onPlay={() => setPlaying(true)}
          onPause={() => setPlaying(false)}
        />
      ) : (
        <div className="video-preview__placeholder">
          <Video size={30} strokeWidth={1.4} />
          <span>{label ?? '录像预览'}</span>
        </div>
      )}
      {hasVideo && !controls && !stream ? (
        <div className="video-preview__overlay">
          <button
            className="video-preview__play"
            onClick={togglePlayback}
            aria-label={playing ? '暂停播放' : '开始播放'}
          >
            {playing ? <Pause size={22} /> : <Play size={22} style={{ marginLeft: 2 }} />}
          </button>
        </div>
      ) : null}
    </div>
  )
}
