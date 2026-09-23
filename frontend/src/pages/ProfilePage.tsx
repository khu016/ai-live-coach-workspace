import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Bell, Check, LogOut, ShieldCheck, Sparkles, Trash2, UserRound, Video } from 'lucide-react'
import { PageHeader } from '../components/PageHeader'
import { Card } from '../components/Card'
import { Button } from '../components/Button'
import { FormField } from '../components/FormField'
import { Toggle } from '../components/Toggle'
import { Modal } from '../components/Modal'
import { useApp } from '../store/AppContext'
import {
  CAMERA_OPTIONS,
  EXPERIENCE_OPTIONS,
  LIVE_TYPES,
  MIC_OPTIONS,
  type LiveType,
} from '../data/mock'

export default function ProfilePage() {
  const navigate = useNavigate()
  const { user, updateUser, showToast } = useApp()

  const [nickname, setNickname] = useState(user.nickname)
  const [liveType, setLiveType] = useState<LiveType>(user.primaryLiveType)
  const [experience, setExperience] = useState(user.experience)
  const [camera, setCamera] = useState(user.defaultCamera)
  const [mic, setMic] = useState(user.defaultMic)
  const [saveRecording, setSaveRecording] = useState(user.saveRecording)
  const [selfOnly, setSelfOnly] = useState(user.recordingVisibleToSelfOnly)
  const [notify, setNotify] = useState(user.notifyOnInsight)
  const [confirmLogout, setConfirmLogout] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)

  const save = () => {
    updateUser({
      nickname: nickname.trim() || user.nickname,
      primaryLiveType: liveType,
      experience,
      defaultCamera: camera,
      defaultMic: mic,
      saveRecording,
      recordingVisibleToSelfOnly: selfOnly,
      notifyOnInsight: notify,
    })
    showToast('已保存个人设置', 'success')
  }
  const scrollTo = (id: string) => document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })

  return (
    <div className="page profile-page">
      <PageHeader title="个人中心" subtitle="管理账号、设备与录像偏好" />

      <div className="profile-layout">
        <aside className="profile-sidebar" aria-label="个人中心设置分类">
          <button className="is-active" onClick={() => scrollTo('profile-account')}><UserRound size={19} />账号资料</button>
          <button onClick={() => scrollTo('profile-devices')}><Video size={19} />设备偏好</button>
          <button onClick={() => scrollTo('profile-privacy')}><ShieldCheck size={19} />隐私与录像</button>
          <button onClick={() => scrollTo('profile-notify')}><Bell size={19} />通知设置</button>
          <div className="profile-preference frosted">
            <Sparkles size={20} />
            <span>当前训练重点</span>
            <strong>弹幕追问应答</strong>
            <small>系统会优先推荐相关难点练习</small>
          </div>
        </aside>
        <div className="profile-content">

      <Card className="section" id="profile-account">
        <h3 className="text-lg semibold mb-4">账号资料</h3>
        <div className="profile-avatar-row">
          <span className="profile-avatar">{nickname.slice(0, 1)}</span>
          <div><strong>{nickname}</strong><small>个人主播账号</small></div>
          <Button variant="secondary" size="sm" onClick={() => showToast('头像上传功能将在账号服务接入后开放', 'success')}>更换头像</Button>
        </div>
        <div className="form-grid">
          <FormField label="昵称" htmlFor="profile-nickname">
            <input
              id="profile-nickname"
              className="field__input"
              value={nickname}
              onChange={(e) => setNickname(e.target.value)}
            />
          </FormField>
          <FormField label="主要直播类型" htmlFor="profile-livetype">
            <select
              id="profile-livetype"
              className="field__select"
              value={liveType}
              onChange={(e) => setLiveType(e.target.value as LiveType)}
            >
              {LIVE_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </FormField>
          <FormField label="直播经验" htmlFor="profile-exp">
            <select
              id="profile-exp"
              className="field__select"
              value={experience}
              onChange={(e) => setExperience(e.target.value)}
            >
              {EXPERIENCE_OPTIONS.map((o) => (
                <option key={o} value={o}>
                  {o}
                </option>
              ))}
            </select>
          </FormField>
        </div>
      </Card>

      <Card className="section" id="profile-devices">
        <h3 className="text-lg semibold mb-4">默认设备</h3>
        <div className="form-grid">
          <FormField label="默认摄像头" htmlFor="profile-camera">
            <select
              id="profile-camera"
              className="field__select"
              value={camera}
              onChange={(e) => setCamera(e.target.value)}
            >
              {CAMERA_OPTIONS.map((o) => (
                <option key={o} value={o}>
                  {o}
                </option>
              ))}
            </select>
          </FormField>
          <FormField label="默认麦克风" htmlFor="profile-mic">
            <select
              id="profile-mic"
              className="field__select"
              value={mic}
              onChange={(e) => setMic(e.target.value)}
            >
              {MIC_OPTIONS.map((o) => (
                <option key={o} value={o}>
                  {o}
                </option>
              ))}
            </select>
          </FormField>
        </div>
      </Card>

      <Card className="section" id="profile-privacy">
        <h3 className="text-lg semibold mb-4">隐私与录像</h3>
        <div className="setting-list">
          <div className="setting-row">
            <div>
              <div className="medium">自动保存练习录像</div>
              <div className="text-xs text-tertiary">练习结束后自动保存，方便回看与对比</div>
            </div>
            <Toggle checked={saveRecording} onChange={setSaveRecording} label="自动保存录像" id="set-save" />
          </div>
          <div className="setting-row">
            <div>
              <div className="medium">录像仅自己可见</div>
              <div className="text-xs text-tertiary">默认不向任何人展示你的练习录像</div>
            </div>
            <Toggle checked={selfOnly} onChange={setSelfOnly} label="录像仅自己可见" id="set-self" />
          </div>
          <div className="setting-row" id="profile-notify">
            <div>
              <div className="medium">训练洞察提醒</div>
              <div className="text-xs text-tertiary">有新反馈或进步提醒时通知你</div>
            </div>
            <Toggle checked={notify} onChange={setNotify} label="训练洞察提醒" id="set-notify" />
          </div>
        </div>
      </Card>

      <div className="section row gap-3">
        <Button onClick={save}>
          <Check size={16} aria-hidden /> 保存设置
        </Button>
        <Button variant="secondary" onClick={() => setConfirmLogout(true)}>
          <LogOut size={16} aria-hidden /> 退出登录
        </Button>
      </div>

      <div className="section">
        <button className="link-danger" onClick={() => setConfirmDelete(true)}>
          <Trash2 size={14} aria-hidden /> 注销账号
        </button>
      </div>
        </div>
      </div>

      <Modal
        open={confirmLogout}
        title="退出登录？"
        onClose={() => setConfirmLogout(false)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setConfirmLogout(false)}>
              取消
            </Button>
            <Button
              onClick={() => {
                setConfirmLogout(false)
                navigate('/login')
              }}
            >
              退出登录
            </Button>
          </>
        }
      >
        退出后需要重新登录才能继续练习。
      </Modal>

      <Modal
        open={confirmDelete}
        title="注销账号？"
        onClose={() => setConfirmDelete(false)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setConfirmDelete(false)}>
              取消
            </Button>
            <Button
              variant="danger"
              onClick={() => {
                setConfirmDelete(false)
                showToast('已提交注销申请（模拟，未真实执行）', 'success')
              }}
            >
              确认注销
            </Button>
          </>
        }
      >
        注销后账号数据将被清理。本演示环境不会真实执行注销。
      </Modal>
    </div>
  )
}
