import { Navigate, Outlet, Route, Routes } from 'react-router-dom'
import { AppShell } from './components/AppShell'
import LoginPage from './pages/LoginPage'
import HomePage from './pages/HomePage'
import TutorialsPage from './pages/TutorialsPage'
import TutorialDetailPage from './pages/TutorialDetailPage'
import PracticeNewPage from './pages/PracticeNewPage'
import LivePracticePage from './pages/LivePracticeRealPage'
import FocusPracticePage from './pages/FocusPracticePage'
import ReportPage from './pages/ReportConnectedPage'
import ComparePage from './pages/CompareConnectedPage'
import GrowthPage from './pages/GrowthPage'
import RecordingsPage from './pages/RecordingsPage'
import ProfilePage from './pages/ProfilePage'
import AdminAnalyticsPage from './pages/AdminAnalyticsPage'
import { useApp } from './store/AppContext'

function ProtectedLayout() {
  const { authStatus } = useApp()
  if (authStatus === 'loading') return <div className="auth-loading">正在确认登录状态…</div>
  if (authStatus === 'anonymous') return <Navigate to="/login" replace />
  return <AppShell><Outlet /></AppShell>
}

function LoginRoute() {
  const { authStatus } = useApp()
  if (authStatus === 'loading') return <div className="auth-loading">正在确认登录状态…</div>
  if (authStatus === 'authenticated') return <Navigate to="/" replace />
  return <LoginPage />
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginRoute />} />
      <Route path="/admin/analytics" element={<AdminAnalyticsPage />} />
      <Route element={<ProtectedLayout />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/tutorials" element={<TutorialsPage />} />
        <Route path="/tutorials/:id" element={<TutorialDetailPage />} />
        <Route path="/practice/new" element={<PracticeNewPage />} />
        <Route path="/practice/live" element={<LivePracticePage />} />
        <Route path="/practice/focus" element={<FocusPracticePage />} />
        <Route path="/reports/:id" element={<ReportPage />} />
        <Route path="/practice/:id/compare" element={<ComparePage />} />
        <Route path="/growth" element={<GrowthPage />} />
        <Route path="/recordings" element={<RecordingsPage />} />
        <Route path="/profile" element={<ProfilePage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
