import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { trackAnalyticsEvent } from '../api/client'

export function AnalyticsTracker() {
  const location = useLocation()

  useEffect(() => {
    const route = location.pathname
    void trackAnalyticsEvent('page_view', { route }).catch(() => {})
    if (/^\/reports\/\d+$/.test(route)) {
      const trainingId = route.split('/').pop()
      void trackAnalyticsEvent('report_viewed', {
        route,
        entityType: 'training',
        entityId: trainingId,
      }).catch(() => {})
    }
  }, [location.pathname])

  return null
}
