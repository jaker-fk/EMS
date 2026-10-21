import axios from 'axios'
import { ElMessage } from 'element-plus'

// 10s 超时：代理或断网导致请求挂起时快速失败，页面可降级展示而不是无限空白
const api = axios.create({ baseURL: '/api', timeout: 10000 })

api.interceptors.request.use((c) => {
  const t = localStorage.getItem('token')
  if (t) c.headers.Authorization = `Bearer ${t}`
  return c
})

function toLogin(): void {
  localStorage.removeItem('token')
  localStorage.removeItem('perms')
  if (location.pathname !== '/login') location.href = '/login'
}

api.interceptors.response.use(
  (r) => {
    const d = r.data
    if (d && typeof d.code !== 'undefined') {
      if (d.code === 200) return d.data
      if (d.code === 401) {
        ElMessage.error(d.msg || '登录已过期')
        toLogin()
        return Promise.reject(new Error(d.msg))
      }
      ElMessage.error(d.msg || '请求失败')
      return Promise.reject(new Error(d.msg))
    }
    return d
  },
  (e) => {
    if (e.response?.status === 401) toLogin()
    else if (e.code === 'ECONNABORTED')
      ElMessage.error('请求超时：请检查后端是否启动，或浏览器代理是否绕过了 localhost')
    else ElMessage.error('网络错误')
    return Promise.reject(e)
  },
)

export default api
