import type { ApiTutorial } from '../api/client'

export const TUTORIAL_CATEGORIES = [
  '全部',
  '开场留人',
  '冷场处理',
  '弹幕应答',
  '互动引导',
  '节奏控制',
  '带货表达',
  '娱乐互动',
  '知识内容',
]

export function tutorialSearchText(tutorial: ApiTutorial): string {
  return [
    tutorial.title,
    tutorial.description,
    tutorial.category,
    tutorial.tags.join(' '),
    tutorial.objective,
    tutorial.steps.map((step) => `${step.title} ${step.detail}`).join(' '),
    tutorial.badExample,
    tutorial.goodExample,
  ].join(' ').toLowerCase()
}
