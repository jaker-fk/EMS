import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/login', component: () => import('./views/Login.vue') },
  {
    path: '/',
    component: () => import('./views/Layout.vue'),
    redirect: '/users',
    children: [
      { path: 'users', component: () => import('./views/Users.vue') },
      { path: 'roles', component: () => import('./views/Roles.vue') },
      { path: 'menus', component: () => import('./views/Menus.vue') },
      { path: 'dicts', component: () => import('./views/Dicts.vue') },
      { path: 'logs', component: () => import('./views/Logs.vue') },
      { path: 'profile', component: () => import('./views/Profile.vue') },
      { path: 'biz', component: () => import('./views/Biz.vue') },
      { path: 'files', component: () => import('./views/Files.vue') },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach((to) => {
  if (to.path !== '/login' && !localStorage.getItem('token')) return '/login'
  if (to.path === '/login' && localStorage.getItem('token')) return '/'
})

export default router
