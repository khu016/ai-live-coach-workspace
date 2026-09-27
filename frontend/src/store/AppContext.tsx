import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { mockUser, type LiveType, type PracticeMode, type UserProfile } from '../data/mock'
import { getCurrentUser, loginWithInvite, logoutSession } from '../api/client'

export interface ToastItem {
  id: number
  message: string
  kind: 'default' | 'success' | 'error'
}

export interface PracticeDraft {
  mode: PracticeMode
  liveType: LiveType
  topic: string
  goal: string
}

interface AppContextValue {
  user: UserProfile
  authStatus: 'loading' | 'authenticated' | 'anonymous'
  login: (nickname: string, inviteCode: string) => Promise<void>
  logout: () => Promise<void>
  updateUser: (patch: Partial<UserProfile>) => void
  toasts: ToastItem[]
  showToast: (message: string, kind?: ToastItem['kind']) => void
  dismissToast: (id: number) => void
  draft: PracticeDraft
  setDraft: (draft: PracticeDraft) => void
}

const AppContext = createContext<AppContextValue | null>(null)

let toastSeq = 0

export function AppProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserProfile>(mockUser)
  const [authStatus, setAuthStatus] = useState<AppContextValue['authStatus']>('loading')
  const [toasts, setToasts] = useState<ToastItem[]>([])
  const [draft, setDraft] = useState<PracticeDraft>({
    mode: 'full',
    liveType: '带货',
    topic: '开场留人',
    goal: '练习开场留住观众',
  })

  const dismissToast = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const showToast = useCallback(
    (message: string, kind: ToastItem['kind'] = 'default') => {
      const id = ++toastSeq
      setToasts((prev) => [...prev, { id, message, kind }])
      window.setTimeout(() => dismissToast(id), 2800)
    },
    [dismissToast],
  )

  const updateUser = useCallback((patch: Partial<UserProfile>) => {
    setUser((prev) => ({ ...prev, ...patch }))
  }, [])

  useEffect(() => {
    let active = true
    const sessionExpired = () => setAuthStatus('anonymous')
    window.addEventListener('nivi:session-expired', sessionExpired)
    getCurrentUser()
      .then(({ user: current }) => {
        if (!active) return
        setUser((prev) => ({ ...prev, nickname: current.nickname, phone: '' }))
        setAuthStatus('authenticated')
      })
      .catch(() => {
        if (active) setAuthStatus('anonymous')
      })
    return () => {
      active = false
      window.removeEventListener('nivi:session-expired', sessionExpired)
    }
  }, [])

  const login = useCallback(async (nickname: string, inviteCode: string) => {
    const { user: current } = await loginWithInvite(nickname, inviteCode)
    setUser((prev) => ({ ...prev, nickname: current.nickname, phone: '' }))
    setAuthStatus('authenticated')
  }, [])

  const logout = useCallback(async () => {
    try {
      await logoutSession()
    } finally {
      setAuthStatus('anonymous')
    }
  }, [])

  const value = useMemo<AppContextValue>(
    () => ({ user, authStatus, login, logout, updateUser, toasts, showToast, dismissToast, draft, setDraft }),
    [user, authStatus, login, logout, updateUser, toasts, showToast, dismissToast, draft],
  )

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>
}

export function useApp(): AppContextValue {
  const ctx = useContext(AppContext)
  if (!ctx) throw new Error('useApp must be used within AppProvider')
  return ctx
}
