<template>
  <el-container class="layout">
    <el-aside :width="collapsed ? '64px' : '220px'" class="aside">
      <div class="logo">
        <el-icon :size="20" color="#4d9bff"><Platform /></el-icon>
        <span v-show="!collapsed" class="logo-text">启明学堂 · 后台</span>
      </div>
      <el-scrollbar class="menu-scroll">
        <el-menu
          :default-active="activeMenu"
          :collapse="collapsed"
          :collapse-transition="false"
          router
          unique-opened
          background-color="transparent"
          text-color="#c7ccd6"
          active-text-color="#ffffff"
        >
          <SidebarItem v-for="item in session.menus" :key="item.id" :item="item" />
        </el-menu>
      </el-scrollbar>
      <div v-show="!collapsed" class="aside-foot">
        <a href="/" target="_blank" rel="noopener">查看前台官网 ↗</a>
      </div>
    </el-aside>

    <el-container>
      <el-header class="header">
        <div class="header-left">
          <el-icon class="icon-btn" :size="18" @click="toggleCollapse">
            <Expand v-if="collapsed" />
            <Fold v-else />
          </el-icon>
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/admin/dashboard' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item v-if="currentTitle">{{ currentTitle }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>

        <div class="header-right">
          <el-tooltip content="刷新菜单与数据" placement="bottom">
            <el-icon class="icon-btn" :size="17" @click="refreshAll"><Refresh /></el-icon>
          </el-tooltip>
          <el-dropdown trigger="click" @command="onCommand">
            <span class="user-trigger">
              <el-avatar :size="28" class="avatar">{{ avatarText }}</el-avatar>
              <span class="user-name">{{ session.nickname || '未登录' }}</span>
              <el-icon :size="12"><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item disabled>
                  {{ session.roles.length ? session.roles.join(' / ') : '无角色' }}
                </el-dropdown-item>
                <el-dropdown-item command="profile" divided>个人中心</el-dropdown-item>
                <el-dropdown-item command="site">前往前台官网</el-dropdown-item>
                <el-dropdown-item command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="main">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" :key="`${route.path}-${viewKey}`" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowDown, Expand, Fold, Platform, Refresh } from '@element-plus/icons-vue'
import api from '../utils/request'
import { useSessionStore } from '../stores/session'
import SidebarItem from '../components/SidebarItem.vue'

const route = useRoute()
const router = useRouter()
const session = useSessionStore()

const COLLAPSE_KEY = 'sidebar-collapsed'
const collapsed = ref(localStorage.getItem(COLLAPSE_KEY) === '1')
const viewKey = ref(0)

const activeMenu = computed(() => route.path)
const avatarText = computed(() => (session.nickname || 'U').slice(0, 1).toUpperCase())

function findTitle(nodes: typeof session.menus, path: string): string {
  for (const node of nodes) {
    if (node.path === path) return node.name
    if (node.children?.length) {
      const found = findTitle(node.children, path)
      if (found) return found
    }
  }
  return ''
}

const currentTitle = computed(
  () => findTitle(session.menus, route.path) || String(route.meta.title || ''),
)

function toggleCollapse(): void {
  collapsed.value = !collapsed.value
  localStorage.setItem(COLLAPSE_KEY, collapsed.value ? '1' : '0')
}

async function refreshAll(): Promise<void> {
  try {
    await session.load(true)
    viewKey.value += 1
    ElMessage.success('已刷新')
  } catch {
    /* 错误提示由请求拦截器统一处理 */
  }
}

async function onCommand(command: string): Promise<void> {
  if (command === 'profile') {
    router.push('/admin/profile')
    return
  }
  if (command === 'site') {
    window.open('/', '_blank')
    return
  }
  if (command !== 'logout') return
  try {
    await ElMessageBox.confirm('确认退出当前账号吗？', '提示', { type: 'warning' })
  } catch {
    return
  }
  try {
    await api.post('/auth/logout')
  } catch {
    /* 登出接口异常也要清理本地登录态 */
  }
  localStorage.removeItem('token')
  localStorage.removeItem('perms')
  localStorage.removeItem('nickname')
  session.reset()
  router.push('/admin/login')
}

onMounted(async () => {
  if (!session.loaded) {
    try {
      await session.load()
    } catch {
      /* 守卫已处理跳转 */
    }
  }
})
</script>

<style scoped>
.layout {
  height: 100vh;
}

.aside {
  display: flex;
  flex-direction: column;
  background: var(--app-aside-bg);
  transition: width 0.2s ease;
  overflow: hidden;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 56px;
  padding: 0 18px;
  color: #fff;
  font-weight: 600;
  letter-spacing: 1px;
  white-space: nowrap;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.logo-text {
  font-size: 15px;
}

.menu-scroll {
  flex: 1;
}

.aside-foot {
  padding: 12px 18px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  font-size: 12px;
}

.aside-foot a {
  color: #8aa4c8;
  text-decoration: none;
}

.aside-foot a:hover {
  color: #fff;
}

.aside :deep(.el-menu) {
  border-right: none;
}

.aside :deep(.el-menu-item:hover),
.aside :deep(.el-sub-menu__title:hover) {
  background-color: rgba(255, 255, 255, 0.08) !important;
}

.aside :deep(.el-menu-item.is-active) {
  background: linear-gradient(90deg, #1677ff, #3d8bff) !important;
  border-radius: 6px;
  margin: 2px 8px;
}

.aside :deep(.el-menu--collapse .el-menu-item),
.aside :deep(.el-menu--collapse .el-sub-menu__title) {
  margin: 2px 4px;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 56px;
  padding: 0 18px;
  background: #fff;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
  z-index: 10;
}

.header-left,
.header-right {
  display: flex;
  align-items: center;
  gap: 14px;
}

.icon-btn {
  cursor: pointer;
  color: #5c6270;
  transition: color 0.15s ease;
}

.icon-btn:hover {
  color: #1677ff;
}

.user-trigger {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  outline: none;
}

.avatar {
  background: linear-gradient(135deg, #1677ff, #4aa3ff);
  font-size: 13px;
}

.user-name {
  font-size: 14px;
  color: #303133;
}

.main {
  padding: 14px;
  background: var(--app-page-bg);
  overflow: auto;
}
</style>
