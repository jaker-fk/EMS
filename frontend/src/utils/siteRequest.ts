import axios from 'axios'
import { ElMessage } from 'element-plus'

/** 前台学员 Token 的存储键，与后台管理员的 token 完全分开 */
export const SITE_TOKEN_KEY = 'site_token'

/**
 * 前台学员专用请求实例。
 *
 * 与后台的 `api` 实例相互独立：
 * - 只带前台学员 Token，不会把后台 Token 发到学员接口；
 * - 401 时只清理学员登录态，不会把页面跳去后台登录页。
 */
const siteApi = axios.create({ baseURL: '/api', timeout: 15000 })

siteApi.interceptors.request.use((config) => {
  const token = localStorage.getItem(SITE_TOKEN_KEY)
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

siteApi.interceptors.response.use(
  (response) => {
    const body = response.data
    if (body && typeof body.code !== 'undefined') {
      if (body.code === 200) return body.data
      if (body.code === 401) {
        // 学员 Token 失效：清掉本地状态，由页面 / 守卫决定跳转，不做整页刷新
        localStorage.removeItem(SITE_TOKEN_KEY)
        return Promise.reject(new Error(body.msg || '登录已过期，请重新登录'))
      }
      ElMessage.error(body.msg || '请求失败')
      return Promise.reject(new Error(body.msg || '请求失败'))
    }
    return body
  },
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem(SITE_TOKEN_KEY)
    } else if (error.code === 'ECONNABORTED') {
      ElMessage.error('请求超时：请稍后重试')
    } else {
      ElMessage.error('网络错误，请稍后重试')
    }
    return Promise.reject(error)
  },
)

export default siteApi
