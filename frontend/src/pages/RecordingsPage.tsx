import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Download, Eye, FileVideo, Lock, MoreHorizontal, Search, Trash2, VideoOff } from 'lucide-react'
import { PageHeader } from '../components/PageHeader'
import { Card } from '../components/Card'
import { Button } from '../components/Button'
import { IconButton } from '../components/IconButton'
import { Modal } from '../components/Modal'
import { StatusTag } from '../components/StatusTag'
import { EmptyState } from '../components/EmptyState'
import { useApp } from '../store/AppContext'
import { recordings as initialRecordings, type LiveType, type Recording } from '../data/mock'

const TYPE_OPTIONS: (LiveType | '全部')[] = ['全部', '带货', '娱乐互动', '知识内容']

export default function RecordingsPage() {
  const navigate = useNavigate()
  const { showToast } = useApp()

  const [records, setRecords] = useState<Recording[]>(initialRecordings)
  const [query, setQuery] = useState('')
  const [type, setType] = useState<(typeof TYPE_OPTIONS)[number]>('全部')
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [menuId, setMenuId] = useState<string | null>(null)
  const [deleteIds, setDeleteIds] = useState<string[] | null>(null)

  const filtered = useMemo(() => {
    return records.filter((r) => {
      const matchType = type === '全部' || r.liveType === type
      const q = query.trim().toLowerCase()
      const matchQuery = !q || r.title.toLowerCase().includes(q)
      return matchType && matchQuery
    })
  }, [records, query, type])

  const allSelected = filtered.length > 0 && filtered.every((r) => selected.has(r.id))

  const toggle = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const toggleAll = () => {
    setSelected((prev) => {
      if (allSelected) {
        const next = new Set(prev)
        filtered.forEach((r) => next.delete(r.id))
        return next
      }
      const next = new Set(prev)
      filtered.forEach((r) => next.add(r.id))
      return next
    })
  }

  const download = (r: Recording) => {
    showToast(`已开始下载：${r.title}（模拟）`, 'success')
  }

  const confirmDelete = () => {
    if (!deleteIds) return
    const ids = deleteIds
    setRecords((prev) => prev.filter((r) => !ids.includes(r.id)))
    setSelected((prev) => {
      const next = new Set(prev)
      ids.forEach((i) => next.delete(i))
      return next
    })
    setDeleteIds(null)
    showToast(`已删除 ${ids.length} 条录像`, 'success')
  }

  return (
    <div className="page">
      <PageHeader
        title="录像管理"
        subtitle="练习录像默认仅自己可见，可回看、下载或删除。"
      />

      <div className="toolbar">
        <div className="search">
          <Search size={16} className="text-tertiary" aria-hidden />
          <input
            className="search__input"
            type="search"
            placeholder="搜索录像标题"
            aria-label="搜索录像"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
        <div className="chip-row">
          {TYPE_OPTIONS.map((t) => (
            <button
              key={t}
              className={type === t ? 'chip chip--active' : 'chip'}
              onClick={() => setType(t)}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {selected.size > 0 && (
        <div className="batch-bar mt-4">
          <span className="text-sm text-secondary">已选 {selected.size} 项</span>
          <Button variant="danger" size="sm" onClick={() => setDeleteIds(Array.from(selected))}>
            <Trash2 size={14} aria-hidden /> 批量删除
          </Button>
        </div>
      )}

      <Card className="mt-4">
        {filtered.length === 0 ? (
          <EmptyState
            icon={<VideoOff size={22} aria-hidden />}
            title="没有找到录像"
            description="换个关键词或筛选类型试试。"
          />
        ) : (
          <div className="table-scroll">
            <table className="table">
              <thead>
                <tr>
                  <th style={{ width: 36 }}>
                    <input
                      type="checkbox"
                      className="checkbox"
                      aria-label="全选"
                      checked={allSelected}
                      onChange={toggleAll}
                    />
                  </th>
                  <th>录像</th>
                  <th>类型</th>
                  <th>日期</th>
                  <th>时长</th>
                  <th>大小</th>
                  <th>可见范围</th>
                  <th style={{ width: 120 }} />
                </tr>
              </thead>
              <tbody>
                {filtered.map((r) => (
                  <tr key={r.id}>
                    <td>
                      <input
                        type="checkbox"
                        className="checkbox"
                        aria-label={`选择 ${r.title}`}
                        checked={selected.has(r.id)}
                        onChange={() => toggle(r.id)}
                      />
                    </td>
                    <td>
                      <div className="recording-title">
                        <FileVideo size={16} className="text-tertiary" aria-hidden />
                        <span className="medium">{r.title}</span>
                      </div>
                    </td>
                    <td>
                      <StatusTag tone="neutral">{r.liveType}</StatusTag>
                    </td>
                    <td className="text-secondary">{r.date}</td>
                    <td className="text-secondary">{r.durationMin} 分钟</td>
                    <td className="text-secondary">{r.size}</td>
                    <td>
                      <StatusTag tone="brand">
                        <Lock size={12} aria-hidden /> {r.visibility}
                      </StatusTag>
                    </td>
                    <td>
                      <div className="row gap-2">
                        <IconButton
                          label="查看录像"
                          size="sm"
                          bordered
                          onClick={() => navigate(`/reports/${r.trainingId}`)}
                        >
                          <Eye size={15} />
                        </IconButton>
                        <div className="dropdown">
                          <IconButton
                            label="更多操作"
                            size="sm"
                            bordered
                            onClick={() => setMenuId(menuId === r.id ? null : r.id)}
                          >
                            <MoreHorizontal size={15} />
                          </IconButton>
                          {menuId === r.id && (
                            <>
                              <div className="dropdown__backdrop" onClick={() => setMenuId(null)} />
                              <div className="dropdown__menu">
                                <button
                                  className="dropdown__item"
                                  onClick={() => {
                                    download(r)
                                    setMenuId(null)
                                  }}
                                >
                                  <Download size={14} aria-hidden /> 下载
                                </button>
                                <button
                                  className="dropdown__item dropdown__item--danger"
                                  onClick={() => {
                                    setDeleteIds([r.id])
                                    setMenuId(null)
                                  }}
                                >
                                  <Trash2 size={14} aria-hidden /> 删除
                                </button>
                              </div>
                            </>
                          )}
                        </div>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Modal
        open={deleteIds !== null}
        title={deleteIds && deleteIds.length > 1 ? '批量删除录像？' : '删除这条录像？'}
        onClose={() => setDeleteIds(null)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setDeleteIds(null)}>
              取消
            </Button>
            <Button variant="danger" onClick={confirmDelete}>
              确认删除
            </Button>
          </>
        }
      >
        {deleteIds && deleteIds.length > 1
          ? `将删除选中的 ${deleteIds.length} 条录像，删除后无法恢复。`
          : '删除后无法恢复，确认删除这条录像吗？'}
      </Modal>
    </div>
  )
}
