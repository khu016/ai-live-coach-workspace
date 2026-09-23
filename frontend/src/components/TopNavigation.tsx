import { useState, type FormEvent } from 'react'
import { Bell, HelpCircle, Search, Settings } from 'lucide-react'
import { NavLink, useNavigate } from 'react-router-dom'
import { useApp } from '../store/AppContext'

const NAV = [
  { to: '/', label: '首页', end: true },
  { to: '/tutorials', label: '教程', end: false },
  { to: '/recordings', label: '练习记录', end: false },
  { to: '/growth', label: '成长记录', end: false },
]

export function TopNavigation() {
  const { user, showToast } = useApp()
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const search = (event: FormEvent) => {
    event.preventDefault()
    const value = query.trim()
    navigate(value ? `/tutorials?q=${encodeURIComponent(value)}` : '/tutorials')
  }

  return (
    <header className="topnav">
      <div className="topnav__inner">
        <NavLink to="/" className="topnav__brand" aria-label="AI 主播陪练首页">
          <img
            className="topnav__logo"
            src="/assets/ai-coach-logo.png"
            width="50"
            height="35"
            alt=""
            aria-hidden="true"
            draggable="false"
          />
          <span className="topnav__brand-name">AI 主播陪练</span>
        </NavLink>
        <nav className="topnav__nav" aria-label="主导航">
          {NAV.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.end} className={({ isActive }) => isActive ? 'topnav__link topnav__link--active' : 'topnav__link'}>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="topnav__actions">
          <form className="topnav__search" role="search" onSubmit={search}><Search size={17} /><input aria-label="搜索训练或教程" placeholder="搜索训练或教程" value={query} onChange={(event) => setQuery(event.target.value)} /></form>
          <button className="topnav__utility" aria-label="通知" onClick={() => showToast('目前没有新的训练提醒', 'success')}><Bell size={18} /><i /></button>
          <button className="topnav__utility" aria-label="设置" onClick={() => navigate('/profile')}><Settings size={18} /></button>
          <button className="topnav__utility" aria-label="帮助" onClick={() => navigate('/tutorials')}><HelpCircle size={19} /></button>
          <button className="avatar topnav__avatar" onClick={() => navigate('/profile')} aria-label="个人中心">{user.nickname.slice(0, 1)}</button>
        </div>
      </div>
    </header>
  )
}
