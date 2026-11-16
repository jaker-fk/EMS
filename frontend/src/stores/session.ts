import { defineStore } from 'pinia'
import api from '../utils/request'

export interface MenuNode {
  id: number
  parent_id: number
  name: string
  menu_type: string
  path: string
  component?: string
  perms?: string
  icon?: string
  sort?: number
  visible?: number
  children?: MenuNode[]
}

export interface SessionUser {
  id: number
  username: string
  nickname: string
}

interface MenusPayload {
  menus: MenuNode[]
  perms: string[]
  user: SessionUser
  roles: string[]
}

let inflight: Promise<void> | null = null

/** 会话状态：登录后一次性拉取「菜单树 + 按钮权限 + 角色」，供路由守卫与界面复用 */
export const useSessionStore = defineStore('session', {
  state: () => ({
    loaded: false,
    user: null as SessionUser | null,
    roles: [] as string[],
    perms: [] as string[],
    menus: [] as MenuNode[],
  }),

  getters: {
    nickname: (state): string => state.user?.nickname || state.user?.username || '',
    isSuper: (state): boolean => state.perms.includes('*'),
  },

  actions: {
    async load(force = false): Promise<void> {
      if (inflight) return inflight
      if (this.loaded && !force) return
      inflight = (async () => {
        const data = (await api.get('/auth/menus')) as unknown as MenusPayload
        this.menus = data?.menus || []
        this.perms = data?.perms || []
        this.user = data?.user || null
        this.roles = data?.roles || []
        this.loaded = true
        // 落一份到 localStorage，供 hasPerm() 这类非组件场景同步读取
        localStorage.setItem('perms', JSON.stringify(this.perms))
        localStorage.setItem('nickname', this.nickname)
      })()
      try {
        await inflight
      } finally {
        inflight = null
      }
    },

    reset(): void {
      this.$reset()
    },
  },
})
