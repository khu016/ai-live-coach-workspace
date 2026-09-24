import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, ArrowRight, BookOpen, Check, CheckCircle2, CircleAlert, Clock, Play } from 'lucide-react'
import { Button } from '../components/Button'
import { Card } from '../components/Card'
import { EmptyState } from '../components/EmptyState'
import { StatusTag } from '../components/StatusTag'
import { getTutorial, getTutorials, updateTutorialProgress, type ApiTutorial } from '../api/client'
import { useApp } from '../store/AppContext'

export default function TutorialDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { showToast } = useApp()
  const [tutorials, setTutorials] = useState<ApiTutorial[]>([])
  const [tutorial, setTutorial] = useState<ApiTutorial | null>(null)
  const [completed, setCompleted] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!id) return
    let cancelled = false
    setLoading(true)
    void Promise.all([getTutorial(id), getTutorials()])
      .then(([detail, catalog]) => {
        if (cancelled) return
        setTutorial(detail.tutorial)
        setCompleted(detail.completed)
        setTutorials(catalog.tutorials)
        setError('')
      })
      .catch((caught) => {
        if (!cancelled) setError(caught instanceof Error ? caught.message : '教程读取失败')
      })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [id])

  const tutorialIndex = tutorials.findIndex((item) => item.id === tutorial?.id)
  const previous = tutorialIndex > 0 ? tutorials[tutorialIndex - 1] : null
  const next = tutorialIndex >= 0 && tutorialIndex < tutorials.length - 1 ? tutorials[tutorialIndex + 1] : null
  const progress = useMemo(() => tutorials.length ? ((tutorialIndex + 1) / tutorials.length) * 100 : 0, [tutorialIndex, tutorials.length])

  const toggleCompleted = async () => {
    if (!tutorial) return
    const nextCompleted = !completed
    setSaving(true)
    try {
      await updateTutorialProgress(tutorial.id, nextCompleted)
      setCompleted(nextCompleted)
      showToast(nextCompleted ? '学习进度已保存' : '已取消完成标记', 'success')
    } catch (caught) {
      showToast(caught instanceof Error ? caught.message : '保存学习进度失败', 'error')
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <div className="page page--narrow"><Card><p className="text-sm text-secondary">正在从后端读取教程…</p></Card></div>
  if (error || !tutorial) {
    return <div className="page page--narrow"><Card><EmptyState title="教程暂时无法读取" description={error || '教程不存在'} action={<Button onClick={() => navigate('/tutorials')}>返回教程中心</Button>} /></Card></div>
  }

  return (
    <div className="page tutorial-reader">
      <Link className="tutorial-reader__back" to="/tutorials"><ArrowLeft size={17} aria-hidden /> 返回教程中心</Link>
      <div className="tutorial-reader__progress" aria-label={`第 ${tutorialIndex + 1} 节，共 ${tutorials.length} 节`}><i style={{ width: `${progress}%` }} /></div>

      <header className="tutorial-reader__hero">
        <div className="tutorial-reader__meta">
          <StatusTag tone="brand">{tutorial.category}</StatusTag>
          <span><Clock size={14} aria-hidden /> {tutorial.durationMin} 分钟</span>
          <span>{tutorial.level}</span>
          <StatusTag tone="warning">待老师复核</StatusTag>
        </div>
        <h1>{tutorial.title}</h1>
        <p>{tutorial.description}</p>
      </header>

      <main className="tutorial-reader__content">
        <section className="lesson-block lesson-block--objective"><span className="lesson-block__icon"><BookOpen size={20} aria-hidden /></span><div><h2>学完以后</h2><p>{tutorial.objective}</p></div></section>
        <section className="lesson-block"><h2>什么时候使用</h2><ul className="lesson-list">{tutorial.whenToUse.map((item) => <li key={item}><Check size={16} aria-hidden /> {item}</li>)}</ul></section>
        <section className="lesson-block"><h2>跟着这三步练</h2><ol className="lesson-steps">{tutorial.steps.map((step, index) => <li key={step.title}><span>{index + 1}</span><div><h3>{step.title}</h3><p>{step.detail}</p></div></li>)}</ol></section>
        <section className="lesson-block"><h2>说法对比</h2><div className="lesson-examples"><article className="lesson-example lesson-example--bad"><span><CircleAlert size={17} aria-hidden /> 容易出问题的说法</span><p>“{tutorial.badExample}”</p></article><article className="lesson-example lesson-example--good"><span><CheckCircle2 size={17} aria-hidden /> 更清楚的说法</span><p>“{tutorial.goodExample}”</p></article></div></section>
        <section className="lesson-block lesson-two-column"><div><h2>常见问题</h2><ul className="lesson-list lesson-list--plain">{tutorial.mistakes.map((item) => <li key={item}>{item}</li>)}</ul></div><div><h2>练习前检查</h2><ul className="lesson-list">{tutorial.checklist.map((item) => <li key={item}><Check size={16} aria-hidden /> {item}</li>)}</ul></div></section>
        <section className="lesson-source"><strong>内容状态</strong><p>本节依据项目教学规则卡 {tutorial.ruleRefs.join('、')} 整理。当前为内部训练初稿，等待有直播经验的老师复核后再标记为已验证内容。</p></section>
      </main>

      <section className="tutorial-reader__actions" aria-label="教程操作">
        <div>
          <Button variant={completed ? 'secondary' : 'brand'} onClick={toggleCompleted} disabled={saving}><CheckCircle2 size={17} aria-hidden /> {saving ? '正在保存…' : completed ? '已学完' : '标记为已学完'}</Button>
          <Button onClick={() => navigate(`/practice/new?mode=focus&topic=${encodeURIComponent(tutorial.practiceTopic)}`)}><Play size={17} fill="currentColor" aria-hidden /> 立即练习</Button>
        </div>
        <p>练习主题将自动设为“{tutorial.practiceTopic}”</p>
      </section>

      <nav className="tutorial-reader__nav" aria-label="教程翻页">
        {previous ? <Link to={`/tutorials/${previous.id}`}><ArrowLeft size={16} aria-hidden /><span><small>上一篇</small>{previous.title}</span></Link> : <span />}
        {next ? <Link to={`/tutorials/${next.id}`}><span><small>下一篇</small>{next.title}</span><ArrowRight size={16} aria-hidden /></Link> : <span />}
      </nav>
    </div>
  )
}
