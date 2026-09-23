import { Navigate } from 'react-router-dom'

/**
 * 难点练习已复用完整模拟直播的真实训练链路（创建真实训练 → 实时转写 → 录制 →
 * 真实报告）。直接访问本路由时引导用户先创建练习，避免再走模拟报告。
 */
export default function FocusPracticePage() {
  return <Navigate to="/practice/new?mode=focus" replace />
}
