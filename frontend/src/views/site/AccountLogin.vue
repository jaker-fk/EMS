<template>
  <section class="site-section auth-page">
    <div class="site-container auth-wrap">
      <div class="auth-aside">
        <p class="eyebrow">学员中心</p>
        <h1>登录，随时查看<br />孩子的课程进度</h1>
        <p class="desc">
          报名、试听、课程顾问跟进状态都能在个人中心里查到，
          不用再翻聊天记录找上次约的是哪门课。
        </p>
        <ul class="points">
          <li><el-icon><CircleCheck /></el-icon>「我的报名」汇总官网提交的全部线索</li>
          <li><el-icon><CircleCheck /></el-icon>报名可提前填入手机号，少填一遍</li>
          <li><el-icon><CircleCheck /></el-icon>学员账号与机构后台账号彼此独立</li>
        </ul>
      </div>

      <div class="auth-card">
        <h2>学员登录</h2>
        <p class="tip">还没账号？<RouterLink to="/account/register">立即注册</RouterLink></p>

        <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent="submit">
          <el-form-item label="账号 / 手机号" prop="account">
            <el-input
              v-model.trim="form.account"
              size="large"
              placeholder="注册时填写的账号或手机号"
              :prefix-icon="User"
              clearable
              @keyup.enter="submit"
            />
          </el-form-item>
          <el-form-item label="密码" prop="password">
            <el-input
              v-model="form.password"
              type="password"
              size="large"
              placeholder="请输入登录密码"
              :prefix-icon="Lock"
              show-password
              @keyup.enter="submit"
            />
          </el-form-item>

          <el-button type="primary" size="large" class="submit-btn" :loading="loading" @click="submit">
            登 录
          </el-button>
        </el-form>

        <p class="back-home">
          <RouterLink to="/">← 返回官网首页</RouterLink>
        </p>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { CircleCheck, Lock, User } from '@element-plus/icons-vue'
import { useSiteSessionStore } from '../../stores/siteSession'

const REMEMBER_KEY = 'site-login-account'

const route = useRoute()
const router = useRouter()
const site = useSiteSessionStore()

const formRef = ref()
const loading = ref(false)
const form = reactive({
  account: localStorage.getItem(REMEMBER_KEY) || '',
  password: '',
})

const rules = {
  account: [{ required: true, message: '请输入账号或手机号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

function safeRedirect(): string {
  const raw = String(route.query.redirect || '')
  // 只接受站内路径，避免被构造成跳转到外部站点
  return raw.startsWith('/') && !raw.startsWith('//') ? raw : '/account'
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
    const user = await site.login(form.account, form.password)
    localStorage.setItem(REMEMBER_KEY, form.account)
    ElMessage.success(`欢迎回来，${user.nickname || user.username}`)
    router.replace(safeRedirect())
  } catch {
    form.password = ''
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  if (site.user) router.replace('/account')
})
</script>

<style scoped>
.auth-page {
  background: linear-gradient(180deg, #f4f8ff 0%, #eef3fb 100%);
}

.auth-wrap {
  display: grid;
  grid-template-columns: 1.1fr 0.9fr;
  gap: 48px;
  align-items: center;
  max-width: 980px;
}

.eyebrow {
  margin: 0 0 12px;
  color: #1677ff;
  font-size: 13px;
  letter-spacing: 3px;
  font-weight: 600;
}

.auth-aside h1 {
  margin: 0 0 18px;
  font-size: 30px;
  line-height: 1.45;
  color: #0f1c2e;
}

.auth-aside .desc {
  margin: 0 0 22px;
  color: #5b6675;
  font-size: 14.5px;
  line-height: 1.9;
  max-width: 420px;
}

.points {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.points li {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #4b5563;
  font-size: 13.5px;
}

.points :deep(.el-icon) {
  color: #52c41a;
}

.auth-card {
  background: #fff;
  border: 1px solid #e6ecf6;
  border-radius: 16px;
  padding: 32px 32px 24px;
  box-shadow: 0 16px 40px rgba(15, 28, 46, 0.08);
}

.auth-card h2 {
  margin: 0 0 6px;
  font-size: 22px;
  color: #0f1c2e;
}

.tip {
  margin: 0 0 22px;
  color: #8a919f;
  font-size: 13px;
}

.tip a {
  color: #1677ff;
  text-decoration: none;
}

.submit-btn {
  width: 100%;
  height: 44px;
  letter-spacing: 4px;
  font-weight: 600;
}

.back-home {
  margin: 18px 0 0;
  text-align: center;
}

.back-home a {
  color: #8a919f;
  font-size: 12.5px;
  text-decoration: none;
}

.back-home a:hover {
  color: #1677ff;
}

@media (max-width: 900px) {
  .auth-wrap {
    grid-template-columns: 1fr;
    gap: 28px;
    max-width: 520px;
  }

  .auth-aside h1 {
    font-size: 24px;
  }

  .auth-aside .points {
    display: none;
  }
}
</style>
