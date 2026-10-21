<template>
  <el-container style="height: 100vh">
    <el-aside width="220px" style="background: #001529">
      <div class="logo">企业后台管理</div>
      <el-menu
        router
        background-color="#001529"
        text-color="#c0c4cc"
        active-text-color="#ffffff"
        :default-active="$route.path"
        unique-opened
      >
        <SidebarItem v-for="m in menus" :key="m.id" :item="m" />
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header">
        <div class="breadcrumb">{{ currentTitle }}</div>
        <el-dropdown @command="onCmd">
          <span class="user">{{ nickname }} ▾</span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="profile">个人中心</el-dropdown-item>
              <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </el-header>
      <el-main style="background: #f0f2f5">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../utils/request'
import { setPerms } from '../utils/auth'
import SidebarItem from '../components/SidebarItem.vue'

interface MenuNode { id: number; name: string; path: string; children?: MenuNode[] }

const r = useRouter()
const route = useRoute()
const menus = ref<MenuNode[]>([])
const nickname = ref('')

function findTitle(nodes: MenuNode[], path: string): string {
  for (const n of nodes) {
    if (n.path === path) return n.name
    if (n.children) {
      const t = findTitle(n.children, path)
      if (t) return t
    }
  }
  return ''
}

const currentTitle = computed(() => findTitle(menus.value, route.path) || '后台管理')

async function load(): Promise<void> {
  try {
    const d: any = await api.get('/auth/menus')
    menus.value = d.menus || []
    setPerms(d.perms || [])
    nickname.value = d.user?.nickname || d.user?.username || ''
    localStorage.setItem('nickname', nickname.value)
  } catch {
    menus.value = []
  }
}

async function onCmd(cmd: string): Promise<void> {
  if (cmd === 'profile') {
    r.push('/profile')
    return
  }
  try {
    await api.post('/auth/logout')
  } catch {
    /* 忽略登出接口异常，前端仍然清理登录态 */
  }
  localStorage.removeItem('token')
  localStorage.removeItem('nickname')
  localStorage.removeItem('perms')
  r.push('/login')
}

onMounted(load)
</script>

<style scoped>
.logo {
  height: 56px;
  line-height: 56px;
  text-align: center;
  color: #fff;
  font-weight: 600;
  letter-spacing: 1px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
}
.breadcrumb {
  font-size: 15px;
  font-weight: 500;
}
.user {
  cursor: pointer;
  color: #303133;
  font-size: 14px;
}
</style>
