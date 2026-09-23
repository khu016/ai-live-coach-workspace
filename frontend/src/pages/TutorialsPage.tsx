import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { BookOpen, Clock, Search, SearchX } from 'lucide-react'
import { PageHeader } from '../components/PageHeader'
import { FilterBar } from '../components/FilterBar'
import { Card } from '../components/Card'
import { Button } from '../components/Button'
import { StatusTag } from '../components/StatusTag'
import { EmptyState } from '../components/EmptyState'
import { Modal } from '../components/Modal'
import { useApp } from '../store/AppContext'
import { tutorials, TUTORIAL_CATEGORIES, type Tutorial } from '../data/mock'

export default function TutorialsPage() {
  const { showToast } = useApp()
  const [searchParams] = useSearchParams()
  const [category, setCategory] = useState('全部')
  const [query, setQuery] = useState(searchParams.get('q') ?? '')
  const [active, setActive] = useState<Tutorial | null>(null)
  const [learning, setLearning] = useState(false)

  useEffect(() => {
    setQuery(searchParams.get('q') ?? '')
  }, [searchParams])

  const filtered = useMemo(() => {
    return tutorials.filter((t) => {
      const matchCategory = category === '全部' || t.category === category
      const q = query.trim().toLowerCase()
      const matchQuery =
        !q || t.title.toLowerCase().includes(q) || t.description.toLowerCase().includes(q)
      return matchCategory && matchQuery
    })
  }, [category, query])

  const openDetail = (t: Tutorial) => {
    setActive(t)
    setLearning(false)
  }

  return (
    <div className="page">
      <PageHeader title="教程中心" subtitle="先学方法，再进入练习；教程不强制、可随时跳过。" />

      <div className="toolbar">
        <div className="search">
          <Search size={16} className="text-tertiary" aria-hidden />
          <input
            className="search__input"
            type="search"
            placeholder="搜索教程，例如：开场、报价、冷场"
            aria-label="搜索教程"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
      </div>

      <div className="mt-4">
        <FilterBar
          options={TUTORIAL_CATEGORIES}
          value={category}
          onChange={setCategory}
          label="教程分类"
        />
      </div>

      <div className="mt-6">
        {filtered.length === 0 ? (
          <Card>
            <EmptyState
              icon={<SearchX size={22} aria-hidden />}
              title="没有找到相关教程"
              description="换个关键词，或切换到其他分类试试。"
              action={
                <Button
                  variant="secondary"
                  onClick={() => {
                    setQuery('')
                    setCategory('全部')
                  }}
                >
                  清除筛选
                </Button>
              }
            />
          </Card>
        ) : (
          <div className="tutorial-grid">
            {filtered.map((t) => (
              <button key={t.id} className="tutorial-card" onClick={() => openDetail(t)}>
                <span className="tutorial-card__thumb">
                  <BookOpen size={22} aria-hidden />
                </span>
                <span className="tutorial-card__body">
                  <span className="tutorial-card__title">{t.title}</span>
                  <span className="tutorial-card__desc">{t.description}</span>
                  <span className="tutorial-card__meta">
                    <StatusTag tone="brand">{t.category}</StatusTag>
                    <span className="text-xs text-tertiary">
                      <Clock size={12} aria-hidden /> {t.durationMin} 分钟 · {t.level}
                    </span>
                  </span>
                </span>
              </button>
            ))}
          </div>
        )}
      </div>

      <Modal
        open={active !== null}
        title={active?.title}
        onClose={() => setActive(null)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setActive(null)}>
              关闭
            </Button>
            <Button
              onClick={() => {
                setLearning(true)
                showToast('开始学习：' + active?.title, 'success')
              }}
            >
              {learning ? '学习中…' : '开始学习'}
            </Button>
          </>
        }
      >
        {active && (
          <div className="tutorial-detail">
            <p>{active.description}</p>
            <div className="row gap-3 wrap mt-3">
              <StatusTag tone="brand">{active.category}</StatusTag>
              <StatusTag tone="neutral">{active.level}</StatusTag>
              <StatusTag tone="neutral">{active.durationMin} 分钟</StatusTag>
              <StatusTag tone="neutral">{active.views} 次学习</StatusTag>
            </div>
            <div className="row gap-2 wrap mt-3">
              {active.tags.map((tag) => (
                <span key={tag} className="tag-pill">
                  #{tag}
                </span>
              ))}
            </div>
            {learning && (
              <p className="mt-3 text-brand text-sm">已进入学习状态（模拟），可随时返回继续练习。</p>
            )}
          </div>
        )}
      </Modal>
    </div>
  )
}
