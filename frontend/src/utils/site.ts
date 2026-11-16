/** 前台展示用的轻量工具：无图片资源时用渐变 + 首字生成好看的占位。 */

const GRADIENTS: [string, string][] = [
  ['#1677ff', '#4aa3ff'],
  ['#7c5cff', '#a78bfa'],
  ['#ff7a45', '#ffb26b'],
  ['#13c2c2', '#5cdbd3'],
  ['#eb2f96', '#ff85c0'],
  ['#52c41a', '#95de64'],
  ['#f5a623', '#ffd666'],
  ['#597ef7', '#8fb0ff'],
]

function hash(seed: string): number {
  let h = 0
  for (let i = 0; i < seed.length; i += 1) {
    h = (h * 31 + seed.charCodeAt(i)) % 99991
  }
  return h
}

/** 根据标题生成稳定的渐变背景，同一课程每次渲染颜色一致 */
export function coverStyle(seed: string): Record<string, string> {
  const value = hash(seed || 'course')
  const [from, to] = GRADIENTS[value % GRADIENTS.length]
  return { background: `linear-gradient(135deg, ${from} 0%, ${to} 100%)` }
}

/** 图片地址归一化：站内路径原样返回，裸域名补 https，// 开头补协议 */
export function imageUrl(url?: string): string {
  const value = (url || '').trim()
  if (!value) return ''
  if (value.startsWith('//')) return `https:${value}`
  if (value.startsWith('/') || value.startsWith('data:')) return value
  if (/^[a-z][a-z0-9+.-]*:/i.test(value)) return value
  return `https://${value}`
}

/** 取标题前两个有效字符作为占位文字 */
export function initials(text: string, length = 2): string {
  const cleaned = (text || '').replace(/[^\u4e00-\u9fa5A-Za-z0-9]/g, '')
  return cleaned.slice(0, length) || '启明'
}

/** 价格展示：整数不带小数，保留「面议」场景 */
export function priceText(value?: number): string {
  const price = Number(value || 0)
  return price > 0 ? `¥${price}` : '面议'
}

/** 秒数转「x 天 x 小时」 */
export function uptimeText(seconds: number): string {
  if (!seconds) return '-'
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  if (days) return `${days} 天 ${hours} 小时`
  if (hours) return `${hours} 小时 ${minutes} 分`
  return `${minutes} 分钟`
}

/* ---------------------------------------------------------------- 类型 */
export interface SiteCourse {
  id: number
  title: string
  subtitle?: string
  summary?: string
  price: number
  original_price: number
  lessons: number
  duration?: string
  level?: string
  tags: string[]
  category_id?: number
  category_name?: string
  teacher_id?: number
  teacher_name?: string
  teacher_title?: string
  teacher_avatar?: string
  is_recommend?: number
  view_count?: number
  description?: string
  suitable?: string
  related?: SiteCourse[]
}

export interface SiteTeacher {
  id: number
  name: string
  title: string
  avatar?: string
  intro?: string
  tags: string[]
  years: number
}

export interface SiteArticle {
  id: number
  title: string
  category: string
  cover?: string
  summary?: string
  published_at: string
  content?: string
}

export interface SiteHomeData {
  stats: { courses: number; teachers: number; categories: number; enrollments: number }
  categories: { id: number; name: string; desc: string; icon: string }[]
  recommend: SiteCourse[]
  hot: SiteCourse[]
  teachers: SiteTeacher[]
  articles: SiteArticle[]
}

