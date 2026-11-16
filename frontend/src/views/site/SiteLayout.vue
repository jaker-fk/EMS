<template>
  <div class="site">
    <header class="topbar">
      <div class="site-container topbar-inner">
        <RouterLink to="/" class="brand">
          <span class="brand-mark">启</span>
          <span class="brand-text">
            <strong>启明学堂</strong>
            <small>中小学辅导 · 少儿编程</small>
          </span>
        </RouterLink>

        <nav class="nav">
          <RouterLink v-for="item in navs" :key="item.path" :to="item.path" class="nav-link">
            {{ item.name }}
          </RouterLink>
        </nav>

        <div class="actions">
          <a class="phone" href="tel:4008601234">
            <el-icon><Phone /></el-icon>
            <span>400-860-1234</span>
          </a>

          <template v-if="site.user">
            <el-dropdown trigger="click" @command="onAccountCommand">
              <span class="account-trigger">
                <el-avatar :size="28" class="account-avatar">{{ avatarText }}</el-avatar>
                <span class="account-name">{{ site.displayName }}</span>
                <el-icon :size="12"><ArrowDown /></el-icon>
              </span>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="account">个人中心</el-dropdown-item>
                  <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
          <template v-else>
            <RouterLink to="/account/login" class="login-link">学员登录</RouterLink>
            <RouterLink to="/account/register" class="register-link">注册</RouterLink>
          </template>
        </div>

        <el-icon class="menu-toggle" :size="20" @click="open = !open">
          <Close v-if="open" />
          <Menu v-else />
        </el-icon>
      </div>

      <div v-show="open" class="mobile-nav">
        <RouterLink
          v-for="item in navs"
          :key="item.path"
          :to="item.path"
          class="mobile-link"
          @click="open = false"
        >{{ item.name }}</RouterLink>

        <template v-if="site.user">
          <RouterLink to="/account" class="mobile-link" @click="open = false">
            个人中心（{{ site.displayName }}）
          </RouterLink>
          <a class="mobile-link" @click="doLogout">退出登录</a>
        </template>
        <template v-else>
          <RouterLink to="/account/login" class="mobile-link" @click="open = false">学员登录</RouterLink>
          <RouterLink to="/account/register" class="mobile-link" @click="open = false">注册账号</RouterLink>
        </template>
      </div>
    </header>

    <main class="site-main">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>

    <footer class="footer">
      <div class="site-container footer-inner">
        <div class="footer-about">
          <div class="footer-brand">
            <span class="brand-mark">启</span>
            <strong>启明学堂</strong>
          </div>
          <p>
            专注中小学学科辅导与少儿编程，坚持小班教学与双师课堂，
            已累计服务 1200+ 组家庭。
          </p>
        </div>

        <div class="footer-col">
          <h4>课程体系</h4>
          <RouterLink to="/courses">少儿编程</RouterLink>
          <RouterLink to="/courses">学科辅导</RouterLink>
          <RouterLink to="/courses">语言培训</RouterLink>
          <RouterLink to="/courses">艺术素养</RouterLink>
        </div>

        <div class="footer-col">
          <h4>关于我们</h4>
          <RouterLink to="/about">机构介绍</RouterLink>
          <RouterLink to="/teachers">师资团队</RouterLink>
          <RouterLink to="/news">机构动态</RouterLink>
          <RouterLink to="/account">学员中心</RouterLink>
        </div>

        <div class="footer-col footer-contact">
          <h4>联系我们</h4>
          <p>咨询电话：400-860-1234</p>
          <p>校区地址：北京市海淀区知春路 66 号 3 层</p>
          <p>工作时间：09:00 - 20:30（周一至周日）</p>
        </div>
      </div>

      <div class="footer-bottom">
        © {{ year }} 启明学堂 · 民办学校办学许可证：教民 1101087000xxx 号 · 京 ICP 备 00000000 号
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowDown, Close, Menu, Phone } from '@element-plus/icons-vue'
import { useSiteSessionStore } from '../../stores/siteSession'
import { SITE_TOKEN_KEY } from '../../utils/siteRequest'

const router = useRouter()
const site = useSiteSessionStore()

const year = new Date().getFullYear()
const open = ref(false)
const avatarText = computed(() => (site.displayName || '学').slice(0, 1).toUpperCase())

const navs = [
  { name: '首页', path: '/' },
  { name: '课程中心', path: '/courses' },
  { name: '师资团队', path: '/teachers' },
  { name: '机构动态', path: '/news' },
  { name: '关于我们', path: '/about' },
]

async function doLogout(): Promise<void> {
  try {
    await ElMessageBox.confirm('确认退出当前学员账号吗？', '提示', { type: 'warning' })
  } catch {
    return
  }
  await site.logout()
  open.value = false
  ElMessage.success('已退出登录')
  if (router.currentRoute.value.path.startsWith('/account')) router.replace('/')
}

async function onAccountCommand(command: string): Promise<void> {
  if (command === 'account') {
    router.push('/account')
    return
  }
  if (command === 'logout') await doLogout()
}

onMounted(() => {
  // 刷新页面后恢复学员登录态；Token 失效时静默清理，不打断浏览
  if (localStorage.getItem(SITE_TOKEN_KEY) && !site.loaded) {
    site.load().catch(() => undefined)
  }
})
</script>

<style scoped>
.site {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: #fff;
}

.topbar {
  position: sticky;
  top: 0;
  z-index: 50;
  background: rgba(255, 255, 255, 0.94);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid #eef1f6;
}

.topbar-inner {
  display: flex;
  align-items: center;
  gap: 28px;
  height: 72px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
  color: #0f1c2e;
}

.brand-mark {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-weight: 700;
  font-size: 18px;
  background: linear-gradient(135deg, #1677ff, #4aa3ff);
}

.brand-text {
  display: flex;
  flex-direction: column;
  line-height: 1.25;
}

.brand-text strong {
  font-size: 17px;
  letter-spacing: 1px;
}

.brand-text small {
  color: #8a919f;
  font-size: 11px;
}

.nav {
  display: flex;
  gap: 26px;
  margin-left: 12px;
  flex: 1;
}

.nav-link {
  color: #33415c;
  font-size: 15px;
  text-decoration: none;
  padding: 6px 0;
  border-bottom: 2px solid transparent;
  transition: color 0.15s ease, border-color 0.15s ease;
}

.nav-link:hover {
  color: #1677ff;
}

.nav-link.router-link-active {
  color: #1677ff;
  border-bottom-color: #1677ff;
  font-weight: 600;
}

.actions {
  display: flex;
  align-items: center;
  gap: 14px;
}

.phone {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #f5222d;
  font-weight: 600;
  font-size: 15px;
  text-decoration: none;
}

.account-trigger {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  outline: none;
}

.account-avatar {
  background: linear-gradient(135deg, #1677ff, #4aa3ff);
  font-size: 13px;
  font-weight: 600;
}

.account-name {
  max-width: 88px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #33415c;
  font-size: 14px;
}

.login-link {
  color: #33415c;
  font-size: 14px;
  text-decoration: none;
}

.login-link:hover {
  color: #1677ff;
}

.register-link {
  padding: 8px 16px;
  border-radius: 999px;
  background: #1677ff;
  color: #fff;
  font-size: 13px;
  text-decoration: none;
  transition: background 0.15s ease;
}

.register-link:hover {
  background: #0d5fd6;
}

.menu-toggle {
  display: none;
  cursor: pointer;
  color: #33415c;
}

.mobile-nav {
  display: none;
  flex-direction: column;
  padding: 8px 20px 16px;
  border-top: 1px solid #eef1f6;
  background: #fff;
}

.mobile-link {
  padding: 12px 0;
  color: #33415c;
  text-decoration: none;
  border-bottom: 1px dashed #eef1f6;
  cursor: pointer;
}

.site-main {
  flex: 1;
}

.footer {
  background: #0b1729;
  color: #93a3bb;
  font-size: 13px;
}

.footer-inner {
  display: grid;
  grid-template-columns: 1.6fr 1fr 1fr 1.4fr;
  gap: 32px;
  padding: 48px 20px 32px;
}

.footer-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #fff;
  font-size: 16px;
  margin-bottom: 12px;
}

.footer-about p {
  margin: 0;
  line-height: 1.9;
  max-width: 300px;
}

.footer-col h4 {
  margin: 0 0 14px;
  color: #fff;
  font-size: 14px;
  font-weight: 600;
}

.footer-col a,
.footer-col p {
  display: block;
  margin: 0 0 10px;
  color: #93a3bb;
  text-decoration: none;
  line-height: 1.8;
}

.footer-col a:hover {
  color: #fff;
}

.footer-bottom {
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  padding: 16px 20px;
  text-align: center;
  color: #64748b;
  font-size: 12px;
}

@media (max-width: 900px) {
  .nav,
  .actions {
    display: none;
  }

  .menu-toggle {
    display: block;
    margin-left: auto;
  }

  .mobile-nav {
    display: flex;
  }

  .footer-inner {
    grid-template-columns: 1fr;
    gap: 24px;
    padding: 32px 20px;
  }
}
</style>
