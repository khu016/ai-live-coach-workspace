import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react'
import {
  Activity,
  ArrowLeft,
  BarChart3,
  BookOpenCheck,
  Bot,
  CheckCircle2,
  Clock3,
  LogOut,
  Radio,
  RefreshCw,
  ShieldCheck,
  Users,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import {
  getAdminAnalytics,
  getAdminSession,
  loginAdmin,
  logoutAdmin,
  type AdminAnalyticsSummary,
} from '../api/client'

const EVENT_LABELS: Record<string, string> = {
  page_view: '浏览页面',
  login_success: '登录成功',
  login_failed: '登录失败',
  training_created: '创建练习',
  training_started: '开始练习',
  training_completed: '完成练习',
  report_viewed: '查看报告',
  retrain_started: '发起重练',
  tutorial_viewed: '查看教程',
  tutorial_completed: '完成教程',
  asr_started: '语音识别启动',
  asr_failed: '语音识别失败',
}

function percent(value: number | null): string {
  return value == null ? '数据不足' : `${Math.round(value * 100)}%`
}

function localTime(value: string | null): string {
  if (!value) return '—'
  return new Date(`${value}Z`).toLocaleString('zh-CN', {
    month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit',
  })
}

export default function AdminAnalyticsPage() {
  const [status, setStatus] = useState<'checking' | 'locked' | 'ready'>('checking')
  const [code, setCode] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [days, setDays] = useState<7 | 30>(7)
  const [data, setData] = useState<AdminAnalyticsSummary | null>(null)
  const [loading, setLoading] = useState(false)

  const load = useCallback(async (range: 7 | 30) => {
    setLoading(true)
    try {
      const next = await getAdminAnalytics(range)
      setData(next)
      setStatus('ready')
      setError('')
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : '数据加载失败'
      if (message.includes('管理员') || message.includes('身份') || message.includes('会话')) {
        setStatus('locked')
      }
      setError(message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    let active = true
    getAdminSession()
      .then(() => { if (active) void load(days) })
      .catch(() => { if (active) setStatus('locked') })
    return () => { active = false }
  }, [load])

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (code.trim().length < 8) {
      setError('请输入管理员口令')
      return
    }
    setSubmitting(true)
    try {
      await loginAdmin(code.trim())
      setCode('')
      await load(days)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : '验证失败')
    } finally {
      setSubmitting(false)
    }
  }

  const changeDays = (next: 7 | 30) => {
    setDays(next)
    void load(next)
  }

  const signOut = async () => {
    await logoutAdmin().catch(() => {})
    setData(null)
    setStatus('locked')
  }

  const chartMax = useMemo(() => {
    if (!data?.daily.length) return 1
    return Math.max(1, ...data.daily.map((day) => Math.max(day.page_views, day.trainings)))
  }, [data])

  if (status === 'checking') {
    return <div className="admin-state">正在验证管理员身份…</div>
  }

  if (status === 'locked') {
    return (
      <main className="admin-login">
        <section className="admin-login__panel" aria-labelledby="admin-login-title">
          <Link to="/" className="admin-back"><ArrowLeft size={16} /> 返回 NIVI</Link>
          <img src="/assets/ai-coach-logo.png" width="58" height="41" alt="" />
          <h1 id="admin-login-title">训练数据看板</h1>
          <p>仅用于 NIVI 邀请测试运营。主播账号与管理员权限相互独立。</p>
          <form onSubmit={submit}>
            <label htmlFor="admin-code">管理员口令</label>
            <input
              id="admin-code"
              type="password"
              autoComplete="current-password"
              value={code}
              onChange={(event) => setCode(event.target.value)}
              placeholder="输入服务端配置的管理员口令"
            />
            {error && <span className="admin-login__error" role="alert">{error}</span>}
            <button type="submit" disabled={submitting}>
              <ShieldCheck size={18} />{submitting ? '正在验证…' : '进入数据看板'}
            </button>
          </form>
        </section>
      </main>
    )
  }

  const metrics = data?.metrics
  return (
    <main className="analytics-page">
      <header className="analytics-header">
        <div className="analytics-brand">
          <Link to="/" aria-label="返回 NIVI 首页"><img src="/assets/ai-coach-logo.png" width="48" height="34" alt="" /></Link>
          <div><strong>NIVI</strong><span>邀请测试数据看板</span></div>
        </div>
        <div className="analytics-actions">
          <div className="analytics-range" aria-label="统计周期">
            <button className={days === 7 ? 'is-active' : ''} onClick={() => changeDays(7)}>近 7 天</button>
            <button className={days === 30 ? 'is-active' : ''} onClick={() => changeDays(30)}>近 30 天</button>
          </div>
          <button className="analytics-icon-action" onClick={() => void load(days)} aria-label="刷新数据"><RefreshCw size={17} className={loading ? 'is-spinning' : ''} /></button>
          <button className="analytics-logout" onClick={() => void signOut()}><LogOut size={16} />退出</button>
        </div>
      </header>

      <div className="analytics-content">
        <section className="analytics-title">
          <div><h1>真实使用情况</h1><p>只统计实际产生的数据，当前周期为近 {days} 天。</p></div>
          <span>{data ? `更新于 ${localTime(data.generated_at)}` : '正在读取'}</span>
        </section>

        {error && <div className="analytics-error" role="alert">{error}</div>}

        <section className="analytics-primary" aria-label="关键指标">
          <article><Users /><span>活跃主播</span><strong>{metrics?.active_users ?? 0}</strong><small>累计用户 {metrics?.total_users ?? 0} 人</small></article>
          <article><Radio /><span>创建练习</span><strong>{metrics?.training_created ?? 0}</strong><small>完成 {metrics?.training_completed ?? 0} 场</small></article>
          <article><CheckCircle2 /><span>练习完成率</span><strong>{percent(metrics?.completion_rate ?? null)}</strong><small>从创建到生成反馈</small></article>
          <article><Clock3 /><span>累计训练时长</span><strong>{metrics?.practice_minutes ?? 0}<em>分钟</em></strong><small>来自已保存的真实媒体</small></article>
        </section>

        <div className="analytics-grid">
          <section className="analytics-panel analytics-panel--activity">
            <header><div><h2>使用趋势</h2><p>页面访问与训练创建情况</p></div><Activity size={20} /></header>
            <div className="analytics-chart" role="img" aria-label={`近 ${days} 天页面访问与训练趋势`}>
              {data?.daily.map((day, index) => (
                <div className="analytics-chart__day" key={day.date} title={`${day.date}：访问 ${day.page_views}，训练 ${day.trainings}`}>
                  <div className="analytics-chart__bars">
                    <i style={{ height: `${Math.max(3, day.page_views / chartMax * 100)}%` }} />
                    <b style={{ height: `${Math.max(3, day.trainings / chartMax * 100)}%` }} />
                  </div>
                  {(days === 7 || index % 5 === 0 || index === data.daily.length - 1) && <span>{day.label}</span>}
                </div>
              ))}
            </div>
            <div className="analytics-legend"><span><i />页面访问</span><span><b />训练创建</span></div>
          </section>

          <section className="analytics-panel analytics-panel--funnel">
            <header><div><h2>训练转化</h2><p>按去重用户计算</p></div><BarChart3 size={20} /></header>
            <div className="analytics-funnel">
              {data?.funnel.map((step) => {
                const base = Math.max(1, data.funnel[0]?.users ?? 1)
                return <div key={step.key}><span>{step.label}</span><div><i style={{ width: `${Math.max(4, step.users / base * 100)}%` }} /></div><strong>{step.users}</strong></div>
              })}
            </div>
          </section>

          <section className="analytics-panel analytics-panel--quality">
            <header><div><h2>AI 链路</h2><p>实时训练关键运行数据</p></div><Bot size={20} /></header>
            <dl className="analytics-quality">
              <div><dt>语音识别启动</dt><dd>{metrics?.asr_started ?? 0}</dd></div>
              <div><dt>语音识别失败</dt><dd className={(metrics?.asr_failed ?? 0) > 0 ? 'is-warning' : ''}>{metrics?.asr_failed ?? 0}</dd></div>
              <div><dt>动态弹幕</dt><dd>{metrics?.dynamic_bullets ?? 0}</dd></div>
              <div><dt>报告查看</dt><dd>{metrics?.report_views ?? 0}</dd></div>
            </dl>
          </section>

          <section className="analytics-panel analytics-panel--learning">
            <header><div><h2>教程与重练</h2><p>学习内容是否回到训练</p></div><BookOpenCheck size={20} /></header>
            <div className="analytics-learning">
              <div><strong>{metrics?.tutorial_views ?? 0}</strong><span>教程查看</span></div>
              <div><strong>{metrics?.tutorial_completed ?? 0}</strong><span>教程完成</span></div>
              <div><strong>{metrics?.retrain_count ?? 0}</strong><span>发起重练</span></div>
            </div>
          </section>
        </div>

        <section className="analytics-panel analytics-events">
          <header><div><h2>最近事件</h2><p>不记录邀请码、音频、转写原文或 API Key</p></div></header>
          {data?.recent_events.length ? (
            <div className="analytics-table-wrap"><table><thead><tr><th>时间</th><th>事件</th><th>用户</th><th>页面 / 对象</th></tr></thead><tbody>
              {data.recent_events.map((event) => <tr key={event.id}><td>{localTime(event.created_at)}</td><td><span className="analytics-event-tag">{EVENT_LABELS[event.event_name] ?? event.event_name}</span></td><td>{event.user_id ? `用户 ${event.user_id}` : '匿名'}</td><td>{event.route ?? (event.entity_id ? `${event.entity_type ?? '对象'} ${event.entity_id}` : '—')}</td></tr>)}
            </tbody></table></div>
          ) : <div className="analytics-empty">当前周期还没有埋点记录。完成登录或训练后，这里会出现真实数据。</div>}
        </section>
      </div>
    </main>
  )
}
