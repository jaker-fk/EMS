<template>
  <div class="login-page">
    <section class="brand">
      <div class="brand-inner">
        <RouterLink to="/" class="brand-back">← 返回官网首页</RouterLink>
        <h1>启明学堂 · 管理后台</h1>
        <p class="brand-sub">课程上架 · 师资管理 · 报名线索 · 权限与审计</p>
        <ul class="brand-points">
          <li>前台官网提交的报名，实时进入后台线索池</li>
          <li>课程上下架与前台展示自动同步</li>
          <li>RBAC 权限 + 操作日志，改动可追溯</li>
        </ul>
      </div>
    </section>

    <section class="form-side">
      <el-card class="login-card" shadow="never">
        <h2 class="login-title">管理员登录</h2>
        <p class="login-tip">仅供机构内部管理员使用，学员请前往<RouterLink to="/account/login">学员中心</RouterLink>登录</p>

        <el-form ref="formRef" :model="form" :rules="rules" @submit.prevent="submit">
          <el-form-item prop="username">
            <el-input
              v-model.trim="form.username"
              placeholder="请输入账号"
              size="large"
              :prefix-icon="User"
              clearable
              @keyup.enter="submit"
            />
          </el-form-item>

          <el-form-item prop="password">
            <el-input
              v-model="form.password"
              type="password"
              placeholder="请输入密码"
              size="large"
              :prefix-icon="Lock"
              show-password
              @keyup.enter="submit"
            />
          </el-form-item>

          <el-form-item v-if="captchaEnabled" prop="captcha_code">
            <div class="captcha-row">
              <el-input
                v-model.trim="form.captcha_code"
                placeholder="请输入验证码"
                size="large"
                :prefix-icon="Key"
                @keyup.enter="submit"
              />
              <img
                v-if="captchaImg"
                :src="captchaImg"
                class="captcha-img"
                title="点击刷新验证码"
                alt="验证码"
                @click="loadCaptcha"
              />
              <div v-else class="captcha-img placeholder" @click="loadCaptcha">点击获取</div>
            </div>
          </el-form-item>

          <div class="login-options">
            <el-checkbox v-model="remember">记住账号</el-checkbox>
            <span class="muted">默认 admin / 123456</span>
          </div>

          <el-button type="primary" size="large" class="login-btn" :loading="loading" @click="submit">
            登 录
          </el-button>
        </el-form>
      </el-card>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Key, Lock, User } from '@element-plus/icons-vue'
import api from '../utils/request'
import { useSessionStore } from '../stores/session'

const REMEMBER_KEY = 'login-username'

const route = useRoute()
const router = useRouter()
const session = useSessionStore()

const formRef = ref()
const loading = ref(false)
const remember = ref(true)
const captchaEnabled = ref(false)
const captchaImg = ref('')

const form = reactive({
  username: localStorage.getItem(REMEMBER_KEY) || 'admin',
  password: '',
  captcha_key: '',
  captcha_code: '',
})

const rules = {
  username: [{ required: true, message: '请输入账号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  captcha_code: [{ required: true, message: '请输入验证码', trigger: 'blur' }],
}

async function loadCaptcha(): Promise<void> {
  try {
    const data = (await api.get('/auth/captcha')) as unknown as {
      enabled: boolean
      key?: string
      image?: string
    }
    captchaEnabled.value = Boolean(data?.enabled)
    if (captchaEnabled.value) {
      form.captcha_key = data.key || ''
      captchaImg.value = data.image || ''
      form.captcha_code = ''
    }
  } catch {
    captchaEnabled.value = false
    captchaImg.value = ''
  }
}

async function submit(): Promise<void> {
  if (loading.value) return
  try {
    await formRef.value?.validate()
  } catch {
    return
  }
  loading.value = true
  try {
    const data = (await api.post('/auth/login', { ...form })) as unknown as {
      token: string
      user: { username: string; nickname: string }
    }
    localStorage.setItem('token', data.token)
    localStorage.setItem('nickname', data.user?.nickname || data.user?.username || '')
    if (remember.value) localStorage.setItem(REMEMBER_KEY, form.username)
    else localStorage.removeItem(REMEMBER_KEY)

    session.reset()
    ElMessage.success(`欢迎回来，${data.user?.nickname || data.user?.username || ''}`)
    const redirect = String(route.query.redirect || '')
    router.replace(redirect.startsWith('/') ? redirect : '/admin/dashboard')
  } catch {
    form.password = ''
    if (captchaEnabled.value) await loadCaptcha()
  } finally {
    loading.value = false
  }
}

onMounted(loadCaptcha)
</script>

<style scoped>
.login-page {
  display: flex;
  min-height: 100vh;
  background: #f0f2f5;
}

.brand {
  flex: 1.1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px;
  color: #fff;
  background: radial-gradient(circle at 20% 20%, #1b4f9c 0%, #001529 65%);
}

.brand-inner {
  max-width: 440px;
}

.brand-back {
  display: inline-block;
  margin-bottom: 22px;
  color: #9fb6d4;
  font-size: 13px;
  text-decoration: none;
}

.brand-back:hover {
  color: #fff;
}

.brand h1 {
  margin: 0 0 14px;
  font-size: 30px;
  letter-spacing: 1px;
}

.brand-sub {
  margin: 0 0 26px;
  color: #9fb6d4;
  font-size: 14px;
}

.brand-points {
  margin: 0;
  padding-left: 18px;
  color: #c7d6ea;
  font-size: 14px;
  line-height: 2.1;
}

.form-side {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px;
}

.login-card {
  width: 380px;
  border-radius: 14px;
  padding: 10px 6px;
  border: 1px solid #ebeef5;
  box-shadow: 0 12px 32px rgba(0, 21, 41, 0.08);
}

.login-title {
  margin: 6px 0 6px;
  font-size: 22px;
}

.login-tip {
  margin: 0 0 22px;
  color: #8a919f;
  font-size: 13px;
}

.login-tip a {
  color: #1677ff;
  text-decoration: none;
}

.login-tip a:hover {
  text-decoration: underline;
}

.captcha-row {
  display: flex;
  gap: 10px;
  width: 100%;
}

.captcha-img {
  width: 120px;
  height: 40px;
  cursor: pointer;
  border-radius: 6px;
  background: #f2f5fa;
  object-fit: cover;
  flex: none;
}

.captcha-img.placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: #8a919f;
}

.login-options {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.login-btn {
  width: 100%;
  letter-spacing: 4px;
}

@media (max-width: 900px) {
  .brand {
    display: none;
  }
}
</style>
