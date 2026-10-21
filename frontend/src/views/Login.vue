<template>
  <div class="login-page">
    <el-card class="login-card" header="企业后台管理系统">
      <el-form :model="f" @submit.prevent="login">
        <el-form-item>
          <el-input v-model="f.username" placeholder="账号" size="large" />
        </el-form-item>
        <el-form-item>
          <el-input
            v-model="f.password"
            type="password"
            placeholder="密码"
            size="large"
            show-password
            @keyup.enter="login"
          />
        </el-form-item>
        <el-form-item>
          <div class="captcha-row">
            <el-input
              v-model="f.captcha_code"
              placeholder="验证码"
              size="large"
              @keyup.enter="login"
            />
            <img v-if="captchaImg" :src="captchaImg" class="captcha-img" title="点击刷新" @click="loadCaptcha" />
          </div>
        </el-form-item>
        <el-button type="primary" size="large" style="width: 100%" :loading="loading" @click="login">
          登 录
        </el-button>
        <p class="tip">默认账号 admin / 123456</p>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '../utils/request'

const f = reactive({ username: 'admin', password: '123456', captcha_key: '', captcha_code: '' })
const r = useRouter()
const loading = ref(false)
const captchaImg = ref('')

async function loadCaptcha(): Promise<void> {
  try {
    const d: any = await api.get('/auth/captcha')
    f.captcha_key = d.key
    captchaImg.value = d.image
    f.captcha_code = ''
  } catch {
    captchaImg.value = ''
  }
}

async function login(): Promise<void> {
  if (!f.username || !f.password) return
  loading.value = true
  try {
    const d: any = await api.post('/auth/login', f)
    localStorage.setItem('token', d.token)
    localStorage.setItem('nickname', d.user?.nickname || d.user?.username || '')
    r.push('/')
  } catch {
    loadCaptcha()
  } finally {
    loading.value = false
  }
}

onMounted(loadCaptcha)
</script>

<style scoped>
.login-page {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #001529 0%, #003a70 100%);
}
.login-card {
  width: 380px;
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
  border-radius: 4px;
  background: #f2f5fa;
}
.tip {
  margin-top: 12px;
  text-align: center;
  color: #909399;
  font-size: 12px;
}
</style>
