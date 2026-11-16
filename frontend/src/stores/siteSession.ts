import { defineStore } from 'pinia'
import siteApi, { SITE_TOKEN_KEY } from '../utils/siteRequest'

export interface SiteUser {
  id: number
  username: string
  nickname: string
  phone: string
  created_at?: string
}

interface MePayload {
  user: SiteUser
}

interface AuthPayload {
  token: string
  user: SiteUser
}

export interface RegisterPayload {
  username: string
  password: string
  nickname: string
  phone: string
}

let inflight: Promise<void> | null = null

/**
 * 前台学员会话：与后台 `session` store 完全独立。
 * 登录态存在 site_token，页面刷新后由 SiteLayout / 路由守卫按需拉取 /site/me。
 */
export const useSiteSessionStore = defineStore('siteSession', {
  state: () => ({
    loaded: false,
    user: null as SiteUser | null,
  }),

  getters: {
    isLogin: (state): boolean => Boolean(state.user),
    displayName: (state): string => state.user?.nickname || state.user?.username || '',
  },

  actions: {
    async load(force = false): Promise<void> {
      if (inflight) return inflight
      if (this.loaded && !force) return
      if (!localStorage.getItem(SITE_TOKEN_KEY)) {
        this.user = null
        this.loaded = true
        return
      }
      inflight = (async () => {
        const data = (await siteApi.get('/site/me')) as unknown as MePayload
        this.user = data?.user || null
        this.loaded = true
      })()
      try {
        await inflight
      } finally {
        inflight = null
      }
    },

    async login(account: string, password: string): Promise<SiteUser> {
      const data = (await siteApi.post('/site/auth/login', {
        account,
        password,
      })) as unknown as AuthPayload
      this._applyAuth(data)
      return data.user
    },

    async register(payload: RegisterPayload): Promise<SiteUser> {
      const data = (await siteApi.post(
        '/site/auth/register',
        payload,
      )) as unknown as AuthPayload
      this._applyAuth(data)
      return data.user
    },

    _applyAuth(data: AuthPayload): void {
      localStorage.setItem(SITE_TOKEN_KEY, data.token)
      this.user = data.user
      this.loaded = true
    },

    async logout(): Promise<void> {
      try {
        await siteApi.post('/site/auth/logout')
      } catch {
        /* 接口异常也要清理本地登录态 */
      }
      localStorage.removeItem(SITE_TOKEN_KEY)
      this.$reset()
    },

    reset(): void {
      this.$reset()
    },
  },
})
