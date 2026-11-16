<template>
  <section class="site-section auth-page">
    <div class="site-container auth-wrap">
      <div class="auth-aside">
        <p class="eyebrow">注册学员账号</p>
        <h1>一个账号，<br />收好所有报名记录</h1>
        <p class="desc">
          注册完全免费，不会影响你浏览课程。提交报名后，课程顾问的跟进状态会同步到
          「个人中心 → 我的报名」。
        </p>
        <ul class="points">
          <li><el-icon><CircleCheck /></el-icon>手机号仅用于课程沟通与报名匹配</li>
          <li><el-icon><CircleCheck /></el-icon>与后台管理账号完全隔离，互不相通</li>
          <li><el-icon><CircleCheck /></el-icon>随时可以在个人中心修改资料与密码</li>
        </ul>
      </div>

      <div class="auth-card">
        <h2>注册账号</h2>
        <p class="tip">已有账号？<RouterLink to="/account/login">直接登录</RouterLink></p>

        <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent="submit">
          <el-form-item label="登录账号" prop="username">
            <el-input
              v-model.trim="form.username"
              size="large"
              placeholder="字母、数字、下划线，3-32 位"
              :prefix-icon="User"
              clearable
            />
          </el-form-item>
          <el-form-item label="昵称 / 家长称呼" prop="nickname">
            <el-input v-model.trim="form.nickname" size="large" placeholder="选填，如 王妈妈" maxlength="64" />
          </el-form-item>
          <el-form-item label="手机号" prop="phone">
            <el-input
              v-model.trim="form.phone"
              size="large"
              placeholder="用于匹配报名记录与课程回电"
              :prefix-icon="Phone"
              maxlength="20"
            />
          </el-form-item>
          <el-form-item label="设置密码" prop="password">
            <el-input
              v-model="form.password"
              type="password"
              size="large"
              placeholder="至少 8 位，含大小写字母 / 数字 / 符号中的两类"
              :prefix-icon="Lock"
              show-password
            />
          </el-form-item>
          <el-form-item label="确认密码" prop="confirm">
            <el-input
              v-model="form.confirm"
              type="password"
              size="large"
              placeholder="请再次输入密码"
              :prefix-icon="Lock"
              show-password
              @keyup.enter="submit"
            />
          </el-form-item>

          <el-button type="primary" size="large" class="submit-btn" :loading="loading" @click="submit">
            注册并登录
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
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { CircleCheck, Lock, Phone, User } from '@element-plus/icons-vue'
import { useSiteSessionStore } from '../../stores/siteSession'

const router = useRouter()
const site = useSiteSessionStore()

const formRef = ref()
const loading = ref(false)
const form = reactive({
  username: '',
  nickname: '',
  phone: '',
  password: '',
  confirm: '',
})

function checkPassword(_rule: unknown, value: string, callback: (error?: Error) => void): void {
  const classes = [/[a-z]/, /[A-Z]/, /\d/, /[^A-Za-z0-9]/].filter((re) => re.test(value || '')).length
  if (!value || value.length < 8) {
    callback(new Error('密码至少 8 位'))
    return
  }
  if (classes < 2) {
    callback(new Error('密码需包含大小写字母、数字、符号中的至少两类'))
    return
  }
  callback()
}

function checkConfirm(_rule: unknown, value: string, callback: (error?: Error) => void): void {
  if (value !== form.password) {
    callback(new Error('两次输入的密码不一致'))
    return
  }
  callback()
}

const rules = {
  username: [
    { required: true, message: '请输入登录账号', trigger: 'blur' },
    {
      pattern: /^[A-Za-z0-9_.-]{3,32}$/,
      message: '账号只能包含字母、数字、下划线、点或短横线，长度 3-32',
      trigger: 'blur',
    },
  ],
  phone: [
    { required: true, message: '请输入手机号', trigger: 'blur' },
    { pattern: /^[0-9+\-\s]{6,20}$/, message: '手机号格式不正确', trigger: 'blur' },
  ],
  password: [{ required: true, validator: checkPassword, trigger: 'blur' }],
  confirm: [{ required: true, validator: checkConfirm, trigger: 'blur' }],
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
    const user = await site.register({
      username: form.username,
      password: form.password,
      nickname: form.nickname,
      phone: form.phone,
    })
    ElMessage.success(`注册成功，欢迎你，${user.nickname || user.username}`)
    router.replace('/account')
  } finally {
    loading.value = false
  }
}
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
  padding: 30px 32px 22px;
  box-shadow: 0 16px 40px rgba(15, 28, 46, 0.08);
}

.auth-card h2 {
  margin: 0 0 6px;
  font-size: 22px;
  color: #0f1c2e;
}

.tip {
  margin: 0 0 20px;
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
  font-weight: 600;
  margin-top: 4px;
}

.back-home {
  margin: 16px 0 0;
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
