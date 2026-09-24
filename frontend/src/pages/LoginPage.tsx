import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { ShieldCheck } from 'lucide-react'
import { Button } from '../components/Button'
import { FormField } from '../components/FormField'
import { useApp } from '../store/AppContext'

export default function LoginPage() {
  const navigate = useNavigate()
  const { showToast } = useApp()

  const [phone, setPhone] = useState('')
  const [code, setCode] = useState('')
  const [phoneError, setPhoneError] = useState('')
  const [codeError, setCodeError] = useState('')
  const [countdown, setCountdown] = useState(0)

  const sendCode = () => {
    const ok = /^1\d{10}$/.test(phone)
    if (!ok) {
      setPhoneError('请输入 11 位手机号')
      return
    }
    setPhoneError('')
    showToast('验证码已发送（模拟）', 'success')
    setCountdown(60)
    window.setTimeout(() => setCountdown(0), 60000)
  }

  const submit = (e: FormEvent) => {
    e.preventDefault()
    let valid = true
    if (!/^1\d{10}$/.test(phone)) {
      setPhoneError('请输入 11 位手机号')
      valid = false
    } else {
      setPhoneError('')
    }
    if (!/^\d{6}$/.test(code)) {
      setCodeError('请输入 6 位验证码')
      valid = false
    } else {
      setCodeError('')
    }
    if (!valid) return
    showToast('登录成功', 'success')
    navigate('/')
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
          <FormField label="手机号" htmlFor="login-phone" error={phoneError}>
            <input
              id="login-phone"
              className="field__input"
              type="tel"
              inputMode="numeric"
              maxLength={11}
              placeholder="请输入手机号"
              value={phone}
              onChange={(e) => setPhone(e.target.value.replace(/\D/g, ''))}
            />
          </FormField>

          <FormField label="验证码" htmlFor="login-code" error={codeError}>
            <div className="login-code-row">
              <input
                id="login-code"
                className="field__input"
                type="text"
                inputMode="numeric"
                maxLength={6}
                placeholder="6 位验证码"
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
              />
              <Button type="button" variant="secondary" onClick={sendCode} disabled={countdown > 0}>
                {countdown > 0 ? `${countdown}s 后重发` : '获取验证码'}
              </Button>
            </div>
          </FormField>

          <Button type="submit" block size="lg">
            登录
          </Button>
        </form>

        <div className="login-note">
          <ShieldCheck size={14} aria-hidden />
          <span>登录与验证码均为本地模拟，不会连接真实接口</span>
        </div>
      </div>
    </div>
  )
}
