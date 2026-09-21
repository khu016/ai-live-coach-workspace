import { useState, type ReactNode } from 'react'
import { Pause, Play, Video } from 'lucide-react'

export interface VideoPreviewProps {
  label?: string
  badge?: ReactNode
  live?: boolean
  className?: string
}

export function VideoPreview({ label, badge, live = false, className = '' }: VideoPreviewProps) {
  const [playing, setPlaying] = useState(false)
  return (
    <div className={`video-preview ${className}`}>
      {live && (
        <div className="video-preview__live">
          <span className="video-preview__live-dot" />
          直播中
        </div>
      )}
      {badge && <div className="video-preview__badge">{badge}</div>}
      <div className="video-preview__placeholder">
        <Video size={30} strokeWidth={1.4} />
        <span>{playing ? '正在播放预览…' : label ?? '模拟录像预览'}</span>
      </div>
      <div className="video-preview__overlay">
        <button
          className="video-preview__play"
          onClick={() => setPlaying((p) => !p)}
          aria-label={playing ? '暂停播放' : '开始播放'}
        >
          {playing ? <Pause size={22} /> : <Play size={22} style={{ marginLeft: 2 }} />}
        </button>
      </div>
    </div>
  )
}
