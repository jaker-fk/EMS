<template>
  <section class="site-section account-page">
    <div class="site-container">
      <div v-if="site.user" class="account-shell">
        <div class="account-head">
          <el-avatar :size="60" class="avatar">{{ avatarText }}</el-avatar>
          <div class="who">
            <h1>{{ site.displayName }}</h1>
            <p class="meta">
              账号 {{ site.user.username }}
              <span class="dot">·</span> 手机 {{ site.user.phone || '未填写' }}
              <span v-if="site.user.created_at" class="dot">·</span>
              <span v-if="site.user.created_at">注册于 {{ site.user.created_at }}</span>
            </p>
          </div>
          <div class="head-actions">
            <RouterLink to="/courses" class="continue-link">继续选课 →</RouterLink>
            <el-button text @click="logout">退出登录</el-button>
          </div>
        </div>

        <el-tabs v-model="tab" class="account-tabs">
          <el-tab-pane label="我的报名" name="enrollments">
            <div v-loading="loadingEnroll" class="tab-body">
              <div v-if="enrollments.length" class="enroll-list">
                <div v-for="item in enrollments" :key="item.id" class="enroll-item">
                  <div class="enroll-main">
                    <strong>{{ item.course_title || '课程咨询' }}</strong>
                    <p class="muted">
                      {{ item.name }} · {{ item.phone }}
                      <span v-if="item.age"> · {{ item.age }}</span>
                      · 提交于 {{ item.created_at }}
                    </p>
                    <p v-if="item.remark" class="remark">备注：{{ item.remark }}</p>
                  </div>
                  <el-tag :type="statusType(item.status)" effect="light">
                    {{ item.status_text }}
                  </el-tag>
                </div>
                <div v-if="total > size" class="pager">
                  <el-pagination
                    v-model:current-page="page"
                    :page-size="size"
                    :total="total"
                    layout="prev, pager, next"
                    background
                    @current-change="loadEnrollments"
                  />
                </div>
              </div>
              <el-empty v-else-if="!loadingEnroll" description="还没有报名记录">
                <el-button type="primary" @click="router.push('/courses')">去看看课程</el-button>
              </el-empty>
            </div>
          </el-tab-pane>

          <el-tab-pane label="账号资料" name="profile">
            <div class="tab-body">
              <p class="hint">手机号用于匹配你在官网提交过的报名线索，修改后「我的报名」会同步刷新。</p>
              <el-form
                ref="profileRef"
                :model="profileForm"
                :rules="profileRules"
                label-width="88px"
                class="narrow-form"
              >
                <el-form-item label="登录账号">
                  <el-input :model-value="site.user.username" disabled />
                </el-form-item>
                <el-form-item label="昵称" prop="nickname">
                  <el-input v-model.trim="profileForm.nickname" maxlength="64" placeholder="家长称呼，如 王妈妈" />
                </el-form-item>
                <el-form-item label="手机号" prop="phone">
                  <el-input v-model.trim="profileForm.phone" maxlength="20" placeholder="用于课程沟通" />
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" :loading="savingProfile" @click="saveProfile">保存资料</el-button>
                </el-form-item>
              </el-form>
            </div>
          </el-tab-pane>

          <el-tab-pane label="修改密码" name="password">
            <div class="tab-body">
              <el-form
                ref="pwdRef"
                :model="pwdForm"
                :rules="pwdRules"
                label-width="88px"
                class="narrow-form"
              >
                <el-form-item label="原密码" prop="old_password">
                  <el-input v-model="pwdForm.old_password" type="password" show-password placeholder="请输入当前密码" />
                </el-form-item>
                <el-form-item label="新密码" prop="new_password">
                  <el-input
                    v-model="pwdForm.new_password"
                    type="password"
                    show-password
                    placeholder="至少 8 位，含两类字符"
                  />
                </el-form-item>
                <el-form-item label="确认密码" prop="confirm">
                  <el-input v-model="pwdForm.confirm" type="password" show-password placeholder="请再次输入新密码" />
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" :loading="savingPwd" @click="changePassword">修改密码</el-button>
                </el-form-item>
              </el-form>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import siteApi from '../../utils/siteRequest'
import { useSiteSessionStore, type SiteUser } from '../../stores/siteSession'

interface SiteEnrollment {
  id: number
  course_id: number
  course_title: string
  name: string
  phone: string
  age: string
  source: string
  status: number
  status_text: string
  remark: string
  created_at: string
}

interface EnrollmentPage {
  total: number
  list: SiteEnrollment[]
}

const site = useSiteSessionStore()
const router = useRouter()

const tab = ref('enrollments')
const loadingEnroll = ref(false)
const enrollments = ref<SiteEnrollment[]>([])
const total = ref(0)
const page = ref(1)
const size = 8

const avatarText = computed(() => (site.displayName || '学').slice(0, 1).toUpperCase())

const profileRef = ref()
const savingProfile = ref(false)
const profileForm = reactive({ nickname: '', phone: '' })
const profileRules = {
  nickname: [{ max: 64, message: '昵称过长', trigger: 'blur' }],
  phone: [{ pattern: /^[0-9+\-\s]{6,20}$/, message: '手机号格式不正确', trigger: 'blur' }],
}

const pwdRef = ref()
const savingPwd = ref(false)
const pwdForm = reactive({ old_password: '', new_password: '', confirm: '' })

function checkNewPassword(_rule: unknown, value: string, callback: (error?: Error) => void): void {
  const classes = [/[a-z]/, /[A-Z]/, /\d/, /[^A-Za-z0-9]/].filter((re) => re.test(value || '')).length
  if (!value || value.length < 8) {
    callback(new Error('新密码至少 8 位'))
    return
  }
  if (classes < 2) {
    callback(new Error('新密码需包含大小写字母、数字、符号中的至少两类'))
    return
  }
  callback()
}

function checkConfirm(_rule: unknown, value: string, callback: (error?: Error) => void): void {
  if (value !== pwdForm.new_password) {
    callback(new Error('两次输入的新密码不一致'))
    return
  }
  callback()
}

const pwdRules = {
  old_password: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  new_password: [{ required: true, validator: checkNewPassword, trigger: 'blur' }],
  confirm: [{ required: true, validator: checkConfirm, trigger: 'blur' }],
}

function statusType(status: number): 'warning' | 'primary' | 'success' | 'info' {
  if (status === 1) return 'primary'
  if (status === 2) return 'success'
  if (status === 3) return 'info'
  return 'warning'
}

async function loadEnrollments(): Promise<void> {
  loadingEnroll.value = true
  try {
    const data = (await siteApi.get('/site/me/enrollments', {
      params: { page: page.value, size },
    })) as unknown as EnrollmentPage
    enrollments.value = data?.list || []
    total.value = data?.total || 0
  } finally {
    loadingEnroll.value = false
  }
}

async function saveProfile(): Promise<void> {
  try {
    await profileRef.value?.validate()
  } catch {
    return
  }
  savingProfile.value = true
  try {
    const user = (await siteApi.put('/site/me', {
      nickname: profileForm.nickname,
      phone: profileForm.phone,
    })) as unknown as SiteUser
    if (site.user) site.user = { ...site.user, ...user }
    ElMessage.success('资料已保存')
    // 手机号可能变化，重新拉一次报名归属
    page.value = 1
    await loadEnrollments()
  } finally {
    savingProfile.value = false
  }
}

async function changePassword(): Promise<void> {
  try {
    await pwdRef.value?.validate()
  } catch {
    return
  }
  savingPwd.value = true
  try {
    await siteApi.put('/site/me/password', {
      old_password: pwdForm.old_password,
      new_password: pwdForm.new_password,
    })
    ElMessage.success('密码已修改，请牢记新密码')
    pwdForm.old_password = ''
    pwdForm.new_password = ''
    pwdForm.confirm = ''
    pwdRef.value?.clearValidate()
  } finally {
    savingPwd.value = false
  }
}

async function logout(): Promise<void> {
  try {
    await ElMessageBox.confirm('确认退出当前学员账号吗？', '提示', { type: 'warning' })
  } catch {
    return
  }
  await site.logout()
  ElMessage.success('已退出登录')
  router.replace('/')
}

function goLogin(): void {
  router.replace({ path: '/account/login', query: { redirect: '/account' } })
}

onMounted(async () => {
  if (!site.loaded) {
    try {
      await site.load()
    } catch {
      goLogin()
      return
    }
  }
  if (!site.user) {
    goLogin()
    return
  }
  profileForm.nickname = site.user.nickname || ''
  profileForm.phone = site.user.phone || ''
  await loadEnrollments()
})
</script>

<style scoped>
.account-page {
  background: linear-gradient(180deg, #f6f9ff 0%, #eef3fb 100%);
  min-height: calc(100vh - 420px);
}

.account-shell {
  max-width: 900px;
  margin: 0 auto;
}

.account-head {
  display: flex;
  align-items: center;
  gap: 18px;
  flex-wrap: wrap;
  padding: 26px 28px;
  background: #fff;
  border: 1px solid #e6ecf6;
  border-radius: 16px;
  box-shadow: 0 12px 30px rgba(15, 28, 46, 0.06);
}

.avatar {
  background: linear-gradient(135deg, #1677ff, #4aa3ff);
  font-size: 22px;
  font-weight: 600;
}

.who h1 {
  margin: 0 0 6px;
  font-size: 22px;
  color: #0f1c2e;
}

.who .meta {
  margin: 0;
  color: #8a919f;
  font-size: 13px;
}

.dot {
  margin: 0 6px;
}

.head-actions {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 10px;
}

.continue-link {
  color: #1677ff;
  font-size: 13.5px;
  text-decoration: none;
}

.continue-link:hover {
  text-decoration: underline;
}

.account-tabs {
  margin-top: 18px;
  padding: 8px 28px 28px;
  background: #fff;
  border: 1px solid #e6ecf6;
  border-radius: 16px;
}

.tab-body {
  min-height: 180px;
  padding-top: 6px;
}

.hint {
  margin: 0 0 18px;
  color: #8a919f;
  font-size: 13px;
}

.enroll-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.enroll-item {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 18px;
  border: 1px solid #eef2f9;
  border-radius: 12px;
  background: #fbfcff;
}

.enroll-main strong {
  display: block;
  margin-bottom: 6px;
  color: #0f1c2e;
  font-size: 15px;
}

.enroll-main .muted {
  margin: 0;
  color: #8a919f;
  font-size: 12.5px;
  line-height: 1.7;
}

.enroll-main .remark {
  margin: 6px 0 0;
  color: #5b6675;
  font-size: 12.5px;
}

.narrow-form {
  max-width: 460px;
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 6px;
}

@media (max-width: 768px) {
  .account-head {
    padding: 20px;
  }

  .head-actions {
    margin-left: 0;
    width: 100%;
    justify-content: space-between;
  }

  .account-tabs {
    padding: 4px 16px 20px;
  }
}
</style>
