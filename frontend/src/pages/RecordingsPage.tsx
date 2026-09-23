import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Eye, FileAudio, FileVideo, Lock, MoreHorizontal, Play, Search, Trash2, VideoOff } from 'lucide-react'
import { PageHeader } from '../components/PageHeader'
import { Card } from '../components/Card'
import { Button } from '../components/Button'
import { IconButton } from '../components/IconButton'
import { Modal } from '../components/Modal'
import { StatusTag } from '../components/StatusTag'
import { EmptyState } from '../components/EmptyState'
import { useApp } from '../store/AppContext'
import { deleteTraining, listRecordings, type ApiRecording } from '../api/client'

const TYPE_OPTIONS = ['全部', '带货', '娱乐互动', '知识内容'] as const

function formatDate(value: string | null): string {
  if (!value) return '时间未记录'
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

function formatSize(bytes: number | null): string {
  if (bytes === null || bytes === undefined) return '—'
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function formatDuration(sec: number | null): string {
  if (sec === null || sec === undefined) return '—'
  const m = Math.floor(sec / 60)
  const s = Math.floor(sec % 60)
  return `${m}:${String(s).padStart(2, '0')}`
}

export default function RecordingsPage() {
  const navigate = useNavigate()
  const { showToast } = useApp()

  const [records, setRecords] = useState<ApiRecording[]>([])
  const [loading, setLoading] = useState(true)
  const [query, setQuery] = useState('')
  const [type, setType] = useState<(typeof TYPE_OPTIONS)[number]>('全部')
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [menuId, setMenuId] = useState<number | null>(null)
  const [deleteIds, setDeleteIds] = useState<number[] | null>(null)
  const [deleting, setDeleting] = useState(false)

  const reload = () => {
    void listRecordings()
      .then((list) => { setRecords(list) })
      .catch((e) => showToast(e instanceof Error ? e.message : '读取录像列表失败', 'error'))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    reload()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const filtered = useMemo(() => {
    return records.filter((r) => {
      const matchType = type === '全部' || r.live_type === type
      const q = query.trim().toLowerCase()
      const matchQuery = !q || (r.goal ?? '').toLowerCase().includes(q)
      return matchType && matchQuery
    })
  }, [records, query, type])

  const allSelected = filtered.length > 0 && filtered.every((r) => selected.has(r.training_id))

  const toggle = (id: number) => {
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
        filtered.forEach((r) => next.delete(r.training_id))
        return next
      }
      const next = new Set(prev)
      filtered.forEach((r) => next.add(r.training_id))
      return next
    })
  }

  const confirmDelete = async () => {
    if (!deleteIds) return
    const ids = deleteIds
    setDeleting(true)
    try {
      for (const id of ids) {
        await deleteTraining(id)
      }
      setRecords((prev) => prev.filter((r) => !ids.includes(r.training_id)))
      setSelected((prev) => {
        const next = new Set(prev)
        ids.forEach((i) => next.delete(i))
        return next
      })
      showToast(`已删除 ${ids.length} 条录像`, 'success')
    } catch (e) {
      showToast(e instanceof Error ? e.message : '删除失败', 'error')
    } finally {
      setDeleting(false)
      setDeleteIds(null)
    }
  }

  return (
    <div className="page">
      <PageHeader
        title="录像管理"
        subtitle="管理练习录像与可见范围"
        actions={<Button onClick={() => navigate('/practice/new')}><Play size={15} />开始新练习</Button>}
      />

      <div className="recording-privacy frosted">
        <span><Lock size={22} /></span>
        <div><strong>录像默认仅自己可见</strong><small>练习录像只保存在你的账号下，可随时删除</small></div>
      </div>

      <div className="toolbar">
        <div className="search">
          <Search size={16} className="text-tertiary" aria-hidden />
          <input
            className="search__input"
            type="search"
            placeholder="搜索练习目标"
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
        {loading ? (
          <p className="text-sm text-tertiary">正在读取录像列表…</p>
        ) : filtered.length === 0 ? (
          <EmptyState
            icon={<VideoOff size={22} aria-hidden />}
            title="没有录像记录"
            description="完成一次练习后，录像会出现在这里。"
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
                  <th>练习</th>
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
                  <tr key={r.recording_id}>
                    <td>
                      <input
                        type="checkbox"
                        className="checkbox"
                        aria-label={`选择 ${r.goal}`}
                        checked={selected.has(r.training_id)}
                        onChange={() => toggle(r.training_id)}
                      />
                    </td>
                    <td>
                      <div className="recording-title">
                        {r.media_kind === 'audio' ? (
                          <FileAudio size={16} className="text-tertiary" aria-hidden />
                        ) : (
                          <FileVideo size={16} className="text-tertiary" aria-hidden />
                        )}
                        <span className="medium">{r.goal}</span>
                        {!r.exists && <span className="text-xs text-danger">文件缺失</span>}
                      </div>
                    </td>
                    <td>
                      <StatusTag tone="neutral">{r.live_type}</StatusTag>
                    </td>
                    <td className="text-secondary">{formatDate(r.created_at)}</td>
                    <td className="text-secondary">{formatDuration(r.duration_sec)}</td>
                    <td className="text-secondary">{formatSize(r.size_bytes)}</td>
                    <td>
                      <StatusTag tone="brand">
                        <Lock size={12} aria-hidden /> 仅自己可见
                      </StatusTag>
                    </td>
                    <td>
                      <div className="row gap-2">
                        <IconButton
                          label="查看报告"
                          size="sm"
                          bordered
                          onClick={() => navigate(`/reports/${r.training_id}`)}
                        >
                          <Eye size={15} />
                        </IconButton>
                        <div className="dropdown">
                          <IconButton
                            label="更多操作"
                            size="sm"
                            bordered
                            onClick={() => setMenuId(menuId === r.recording_id ? null : r.recording_id)}
                          >
                            <MoreHorizontal size={15} />
                          </IconButton>
                          {menuId === r.recording_id && (
                            <>
                              <div className="dropdown__backdrop" onClick={() => setMenuId(null)} />
                              <div className="dropdown__menu">
                                <button
                                  className="dropdown__item dropdown__item--danger"
                                  onClick={() => {
                                    setDeleteIds([r.training_id])
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
            <Button variant="danger" onClick={confirmDelete} disabled={deleting}>
              {deleting ? '正在删除…' : '确认删除'}
            </Button>
          </>
        }
      >
        {deleteIds && deleteIds.length > 1
          ? `将删除选中的 ${deleteIds.length} 条录像及其训练记录，删除后无法恢复。`
          : '删除后无法恢复，确认删除这条录像吗？'}
      </Modal>
    </div>
  )
}
