import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { ShieldCheck } from 'lucide-react'
import { Button } from '../components/Button'
import { FormField } from '../components/FormField'
import { useApp } from '../store/AppContext'

export default function LoginPage() {
  const navigate = useNavigate()
  const { login, showToast } = useApp()

  const [nickname, setNickname] = useState('')
  const [code, setCode] = useState('')
  const [nicknameError, setNicknameError] = useState('')
  const [codeError, setCodeError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    let valid = true
    if (!nickname.trim()) {
      setNicknameError('请输入你的主播昵称')
      valid = false
    } else {
      setNicknameError('')
    }
    if (code.trim().length < 4) {
      setCodeError('请输入有效邀请码')
      valid = false
    } else {
      setCodeError('')
    }
    if (!valid) return
    setSubmitting(true)
    try {
      await login(nickname.trim(), code.trim())
      showToast('欢迎进入 NIVI 测试版', 'success')
      navigate('/')
    } catch (error) {
      setCodeError(error instanceof Error ? error.message : '登录失败，请检查邀请码')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-brand">
          <span className="login-brand__logo" aria-hidden>
            N
          </span>
          <div>
            <h1 className="login-brand__title">NIVI</h1>
            <p className="login-brand__subtitle">AI 主播陪练 · 在开播前练习表达与互动</p>
          </div>
        </div>

        <form onSubmit={submit} className="login-form" noValidate>
          <FormField label="主播昵称" htmlFor="login-nickname" error={nicknameError}>
            <input
              id="login-nickname"
              className="field__input"
              type="text"
              maxLength={40}
              placeholder="例如：小鹿主播"
              value={nickname}
              onChange={(e) => setNickname(e.target.value)}
            />
          </FormField>

          <FormField label="邀请码" htmlFor="login-code" error={codeError}>
            <input
              id="login-code"
              className="field__input"
              type="password"
              autoComplete="current-password"
              maxLength={128}
              placeholder="请输入测试邀请码"
              value={code}
              onChange={(e) => setCode(e.target.value)}
            />
          </FormField>

          <Button type="submit" block size="lg" disabled={submitting}>
            {submitting ? '正在进入…' : '进入测试版'}
          </Button>
        </form>

        <div className="login-note">
          <ShieldCheck size={14} aria-hidden />
          <span>每个邀请码绑定一个独立账号，训练录像默认仅本人可见</span>
        </div>
      </div>
    </div>
  )
}
