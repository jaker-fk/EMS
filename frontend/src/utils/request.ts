import axios from 'axios'
import { ElMessage } from 'element-plus'

// 15s 超时：代理或断网导致请求挂起时快速失败，页面可降级展示而不是无限空白
const api = axios.create({ baseURL: '/api', timeout: 15000 })

let redirecting = false

/** 清理登录态并跳转后台登录页；带上 redirect 便于登录后回到原页面 */
export function toLogin(message = ''): void {
  localStorage.removeItem('token')
  localStorage.removeItem('perms')
  localStorage.removeItem('nickname')
  if (redirecting) return
  redirecting = true
  if (message) ElMessage.error(message)
  if (location.pathname === '/admin/login') {
    redirecting = false
    return
  }
  const redirect = encodeURIComponent(location.pathname + location.search)
  location.href = `/admin/login?redirect=${redirect}`
}

api.interceptors.request.use((c) => {
  const t = localStorage.getItem('token')
  if (t) c.headers.Authorization = `Bearer ${t}`
  return c
})

api.interceptors.response.use(
  (r) => {
    const d = r.data
    if (d && typeof d.code !== 'undefined') {
      if (d.code === 200) return d.data
      if (d.code === 401) {
        toLogin(d.msg || '登录已过期，请重新登录')
        return Promise.reject(new Error(d.msg || '未登录'))
      }
      ElMessage.error(d.msg || '请求失败')
      return Promise.reject(new Error(d.msg || '请求失败'))
    }
    return d
  },
  (e) => {
    if (e.response?.status === 401) {
      toLogin(e.response?.data?.msg || '登录已过期，请重新登录')
    } else if (e.code === 'ECONNABORTED') {
      ElMessage.error('请求超时：请检查后端是否启动，或浏览器代理是否绕过了 localhost')
    } else if (e.response?.status === 413) {
      ElMessage.error('上传内容过大')
    } else {
      ElMessage.error('网络错误，请稍后重试')
    }
    return Promise.reject(e)
  },
)

/** 下载接口返回的文件（Excel 导出等），统一带上 Token 与错误提示 */
export async function download(
  url: string,
  params: Record<string, unknown> = {},
  fallbackName = 'export.xlsx',
): Promise<void> {
  const res = await axios.get(`/api${url}`, {
    params,
    responseType: 'blob',
    timeout: 60000,
    headers: { Authorization: `Bearer ${localStorage.getItem('token') || ''}` },
  })
  const blob = res.data as Blob
  // 后端出错时会返回 JSON 而不是文件，这里解析出来给出提示
  if (blob.type.includes('application/json')) {
    const text = await blob.text()
    try {
      ElMessage.error(JSON.parse(text).msg || '导出失败')
    } catch {
      ElMessage.error('导出失败')
    }
    return
  }
  const disposition = String(res.headers['content-disposition'] || '')
  const matched = /filename="?([^";]+)"?/.exec(disposition)
  const filename = matched?.[1] || fallbackName
  const href = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = href
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(href)
}

export default api
