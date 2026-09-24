import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { ArrowRight, BookOpen, CheckCircle2, Clock, Search, SearchX } from 'lucide-react'
import { PageHeader } from '../components/PageHeader'
import { FilterBar } from '../components/FilterBar'
import { Card } from '../components/Card'
import { Button } from '../components/Button'
import { StatusTag } from '../components/StatusTag'
import { EmptyState } from '../components/EmptyState'
import { getTutorials, type ApiTutorial } from '../api/client'
import { tutorialSearchText, TUTORIAL_CATEGORIES } from '../content/tutorials'

export default function TutorialsPage() {
  const [searchParams] = useSearchParams()
  const [category, setCategory] = useState('全部')
  const [query, setQuery] = useState(searchParams.get('q') ?? '')
  const [tutorials, setTutorials] = useState<ApiTutorial[]>([])
  const [completedIds, setCompletedIds] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    setQuery(searchParams.get('q') ?? '')
  }, [searchParams])

  useEffect(() => {
    let cancelled = false
    void getTutorials()
      .then((data) => {
        if (cancelled) return
        setTutorials(data.tutorials)
        setCompletedIds(new Set(data.progress.completed_ids))
        setError('')
      })
      .catch((caught) => {
        if (!cancelled) setError(caught instanceof Error ? caught.message : '教程读取失败')
      })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [])

  const filtered = useMemo(() => tutorials.filter((tutorial) => {
    const matchCategory = category === '全部' || tutorial.category === category
    const normalizedQuery = query.trim().toLowerCase()
    return matchCategory && (!normalizedQuery || tutorialSearchText(tutorial).includes(normalizedQuery))
  }), [category, query, tutorials])

  const completedCount = tutorials.filter((tutorial) => completedIds.has(tutorial.id)).length

  return (
    <div className="page">
      <PageHeader title="教程中心" subtitle="先学一个具体方法，再进入对应练习。教程可以随时跳过。" />

      <section className="tutorial-overview" aria-label="学习进度">
        <div><BookOpen size={20} aria-hidden /><span><strong>{tutorials.length}</strong> 节文字微课</span></div>
        <div className="tutorial-progress">
          <span>已学完 {completedCount} 节</span>
          <div aria-hidden><i style={{ width: `${tutorials.length ? (completedCount / tutorials.length) * 100 : 0}%` }} /></div>
        </div>
      </section>

      <div className="toolbar">
        <div className="search">
          <Search size={16} className="text-tertiary" aria-hidden />
          <input className="search__input" type="search" placeholder="搜索开场、报价、冷场或弹幕应答" aria-label="搜索教程" value={query} onChange={(event) => setQuery(event.target.value)} />
        </div>
      </div>

      <div className="mt-4">
        <FilterBar options={TUTORIAL_CATEGORIES} value={category} onChange={setCategory} label="教程分类" />
      </div>

      <div className="mt-6">
        {loading ? (
          <Card><p className="text-sm text-secondary">正在从后端读取教程…</p></Card>
        ) : error ? (
          <Card><EmptyState icon={<SearchX size={22} aria-hidden />} title="教程暂时无法读取" description={error} /></Card>
        ) : filtered.length === 0 ? (
          <Card>
            <EmptyState icon={<SearchX size={22} aria-hidden />} title="没有找到相关教程" description="换个关键词，或切换到其他分类试试。" action={<Button variant="secondary" onClick={() => { setQuery(''); setCategory('全部') }}>清除筛选</Button>} />
          </Card>
        ) : (
          <div className="tutorial-grid">
            {filtered.map((tutorial) => {
              const completed = completedIds.has(tutorial.id)
              return (
                <Link key={tutorial.id} className="tutorial-card" to={`/tutorials/${tutorial.id}`} aria-label={`查看教程 ${tutorial.title}`}>
                  <span className="tutorial-card__thumb">{completed ? <CheckCircle2 size={22} aria-hidden /> : <BookOpen size={22} aria-hidden />}</span>
                  <span className="tutorial-card__body">
                    <span className="tutorial-card__title">{tutorial.title}</span>
                    <span className="tutorial-card__desc">{tutorial.description}</span>
                    <span className="tutorial-card__meta">
                      <StatusTag tone={completed ? 'success' : 'brand'}>{completed ? '已学完' : tutorial.category}</StatusTag>
                      <span className="text-xs text-tertiary"><Clock size={12} aria-hidden /> {tutorial.durationMin} 分钟 · {tutorial.level}</span>
                    </span>
                  </span>
                  <ArrowRight className="tutorial-card__arrow" size={18} aria-hidden />
                </Link>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
