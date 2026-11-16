import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { hasPerm } from './utils/auth'
import { useSessionStore } from './stores/session'
import { useSiteSessionStore } from './stores/siteSession'
import { SITE_TOKEN_KEY } from './utils/siteRequest'

/**
 * 路由分为三棵树，账号体系也严格分离：
 * - 根路径 /      → 前台官网（公开内容）
 * - /account/*    → 前台学员账号（登录 / 注册 / 个人中心，使用 site_token）
 * - /admin/*      → 管理后台（后台管理员 token + 按钮级权限）
 *
 * 前台官网不提供任何进入管理后台的入口；后台登录页固定在 /admin/login，
 * 学员账号与管理员账号的 Token 互相不可用（后端按 scope 校验）。
 */
const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: () => import('./views/site/SiteLayout.vue'),
    children: [
      {
        path: '',
        name: 'site-home',
        component: () => import('./views/site/Home.vue'),
        meta: { public: true, title: '首页' },
      },
      {
        path: 'courses',
        name: 'site-courses',
        component: () => import('./views/site/Courses.vue'),
        meta: { public: true, title: '课程中心' },
      },
      {
        path: 'courses/:id',
        name: 'site-course-detail',
        component: () => import('./views/site/CourseDetail.vue'),
        meta: { public: true, title: '课程详情' },
      },
      {
        path: 'teachers',
        name: 'site-teachers',
        component: () => import('./views/site/Teachers.vue'),
        meta: { public: true, title: '师资团队' },
      },
      {
        path: 'news',
        name: 'site-news',
        component: () => import('./views/site/News.vue'),
        meta: { public: true, title: '机构动态' },
      },
      {
        path: 'about',
        name: 'site-about',
        component: () => import('./views/site/About.vue'),
        meta: { public: true, title: '关于我们' },
      },
      {
        path: 'account',
        name: 'site-account',
        component: () => import('./views/site/Account.vue'),
        meta: { title: '个人中心', siteAuth: true },
      },
      {
        path: 'account/login',
        name: 'site-login',
        component: () => import('./views/site/AccountLogin.vue'),
        meta: { public: true, title: '学员登录' },
      },
      {
        path: 'account/register',
        name: 'site-register',
        component: () => import('./views/site/AccountRegister.vue'),
        meta: { public: true, title: '注册账号' },
      },
    ],
  },
  {
    // 管理后台登录页：不在前台官网中露出入口，只能通过地址直接访问
    path: '/admin/login',
    name: 'admin-login',
    component: () => import('./views/Login.vue'),
    meta: { public: true, title: '管理员登录', adminLogin: true },
  },
  {
    // 兼容旧书签：原来的 /login 统一收敛到后台登录路径
    path: '/login',
    redirect: '/admin/login',
  },
  {
    path: '/admin',
    component: () => import('./views/Layout.vue'),
    redirect: '/admin/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'dashboard',
        component: () => import('./views/Dashboard.vue'),
        meta: { title: '首页看板' },
      },
      {
        path: 'users',
        name: 'users',
        component: () => import('./views/Users.vue'),
        meta: { title: '用户管理', perm: 'system:user:list' },
      },
      {
        path: 'roles',
        name: 'roles',
        component: () => import('./views/Roles.vue'),
        meta: { title: '角色管理', perm: 'system:role:list' },
      },
      {
        path: 'menus',
        name: 'menus',
        component: () => import('./views/Menus.vue'),
        meta: { title: '菜单管理', perm: 'system:menu:list' },
      },
      {
        path: 'dicts',
        name: 'dicts',
        component: () => import('./views/Dicts.vue'),
        meta: { title: '数据字典', perm: 'system:dict:list' },
      },
      {
        path: 'logs',
        name: 'logs',
        component: () => import('./views/Logs.vue'),
        meta: { title: '操作日志', perm: 'system:log:list' },
      },
      {
        path: 'files',
        name: 'files',
        component: () => import('./views/Files.vue'),
        meta: { title: '文件管理', perm: 'file:list' },
      },
      {
        path: 'courses',
        name: 'admin-courses',
        component: () => import('./views/Courses.vue'),
        meta: { title: '课程管理', perm: 'edu:course:list' },
      },
      {
        path: 'categories',
        name: 'admin-categories',
        component: () => import('./views/Categories.vue'),
        meta: { title: '课程分类', perm: 'edu:category:list' },
      },
      {
        path: 'teachers',
        name: 'admin-teachers',
        component: () => import('./views/Teachers.vue'),
        meta: { title: '师资团队', perm: 'edu:teacher:list' },
      },
      {
        path: 'enrollments',
        name: 'admin-enrollments',
        component: () => import('./views/Enrollments.vue'),
        meta: { title: '报名线索', perm: 'edu:enrollment:list' },
      },
      {
        path: 'articles',
        name: 'admin-articles',
        component: () => import('./views/Articles.vue'),
        meta: { title: '资讯管理', perm: 'edu:article:list' },
      },
      {
        path: 'profile',
        name: 'profile',
        component: () => import('./views/Profile.vue'),
        meta: { title: '个人中心' },
      },
      {
        path: 'biz',
        name: 'biz',
        component: () => import('./views/Biz.vue'),
        meta: { title: '业务数据', perm: 'biz:list' },
      },
      {
        path: '403',
        name: 'forbidden',
        component: () => import('./views/Forbidden.vue'),
        meta: { title: '无访问权限' },
      },
      {
        path: ':pathMatch(.*)*',
        name: 'admin-not-found',
        component: () => import('./views/NotFound.vue'),
        meta: { title: '页面不存在' },
      },
    ],
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('./views/NotFound.vue'),
    meta: { public: true, title: '页面不存在' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

const APP_TITLE = '启明学堂 · 中小学辅导与少儿编程'

router.beforeEach(async (to) => {
  const adminToken = localStorage.getItem('token')
  const siteToken = localStorage.getItem(SITE_TOKEN_KEY)

  // 管理后台登录页：已登录直接进后台
  if (to.meta.adminLogin) {
    if (adminToken) return { path: '/admin/dashboard' }
    document.title = `管理员登录 - ${APP_TITLE}`
    return true
  }

  // 前台公开页面（官网内容 + 学员登录 / 注册）
  if (to.meta.public) {
    if (siteToken && (to.name === 'site-login' || to.name === 'site-register')) {
      const site = useSiteSessionStore()
      if (!site.loaded) {
        try {
          await site.load()
        } catch {
          /* Token 失效：留在登录页 */
        }
      }
      if (site.user) return { path: '/account' }
    }
    const title = String(to.meta.title || '')
    document.title = title ? `${title} - ${APP_TITLE}` : APP_TITLE
    return true
  }

  // 前台个人中心：只认学员账号；后台管理员不会被当作学员
  if (to.meta.siteAuth) {
    if (!siteToken) {
      return { path: '/account/login', query: { redirect: to.fullPath } }
    }
    const site = useSiteSessionStore()
    if (!site.loaded) {
      try {
        await site.load()
      } catch {
        return { path: '/account/login', query: { redirect: to.fullPath } }
      }
    }
    document.title = `${String(to.meta.title || '')} - ${APP_TITLE}`
    return true
  }

  // 管理后台：只认管理员账号
  if (!adminToken) {
    return { path: '/admin/login', query: { redirect: to.fullPath } }
  }

  const session = useSessionStore()
  if (!session.loaded) {
    try {
      await session.load()
    } catch {
      return { path: '/admin/login' }
    }
  }

  const perm = to.meta.perm as string | undefined
  if (perm && !hasPerm(perm)) {
    return { path: '/admin/403', query: { from: to.fullPath } }
  }

  document.title = `${String(to.meta.title || '')} - 管理后台`
  return true
})

// 发版后旧页面引用已删除的 chunk 时，整页刷新即可恢复
router.onError((error) => {
  const message = String((error as Error)?.message || '')
  if (/Failed to fetch dynamically imported module|Importing a module script failed/.test(message)) {
    window.location.reload()
  }
})

export default router
