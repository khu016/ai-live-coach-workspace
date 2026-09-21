import { NavLink, useNavigate } from 'react-router-dom'
import { useApp } from '../store/AppContext'
import { Button } from './Button'

const NAV = [
  { to: '/', label: '首页', end: true },
  { to: '/tutorials', label: '教程中心', end: false },
  { to: '/growth', label: '成长记录', end: false },
  { to: '/recordings', label: '录像管理', end: false },
  { to: '/profile', label: '个人中心', end: false },
]

export function TopNavigation() {
  const { user } = useApp()
  const navigate = useNavigate()

  return (
    <header className="topnav">
      <div className="topnav__inner">
        <NavLink to="/" className="topnav__brand">
          <span className="topnav__logo" aria-hidden>
            播
          </span>
          <span className="topnav__brand-name">AI 主播陪练</span>
        </NavLink>

        <nav className="topnav__nav" aria-label="主导航">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                isActive ? 'topnav__link topnav__link--active' : 'topnav__link'
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="topnav__actions">
          <Button onClick={() => navigate('/practice/new?mode=full')}>开始练习</Button>
          <button
            className="avatar topnav__avatar"
            onClick={() => navigate('/profile')}
            aria-label="个人中心"
          >
            {user.nickname.slice(0, 1)}
          </button>
        </div>
      </div>
    </header>
  )
}
