<template>
  <div v-loading="loading">
    <template v-if="course">
      <section class="detail-head" :style="coverStyle(course.title)">
        <div class="site-container">
          <el-breadcrumb separator="/" class="crumb">
            <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item :to="{ path: '/courses' }">课程中心</el-breadcrumb-item>
            <el-breadcrumb-item>{{ course.category_name || '课程详情' }}</el-breadcrumb-item>
          </el-breadcrumb>

          <h1>{{ course.title }}</h1>
          <p class="subtitle">{{ course.subtitle || course.summary }}</p>

          <div class="meta">
            <span v-if="course.category_name">{{ course.category_name }}</span>
            <span v-if="course.lessons">{{ course.lessons }} 课时</span>
            <span v-if="course.duration">{{ course.duration }}</span>
            <span v-if="course.level">{{ course.level }}</span>
            <span v-if="course.view_count">{{ course.view_count }} 人浏览</span>
          </div>

          <div v-if="course.tags?.length" class="tags">
            <span v-for="tag in course.tags" :key="tag" class="tag-pill">{{ tag }}</span>
          </div>
        </div>
      </section>

      <section class="site-section">
        <div class="site-container layout">
          <div class="main">
            <div class="panel">
              <h2>课程介绍</h2>
              <div class="desc">{{ course.description || course.summary }}</div>
            </div>

            <div v-if="course.suitable" class="panel">
              <h2>适合人群</h2>
              <p class="plain">{{ course.suitable }}</p>
            </div>

            <div v-if="course.teacher_name" class="panel">
              <h2>授课教师</h2>
              <div class="teacher">
                <img
                  v-if="teacherAvatar"
                  class="avatar avatar--img"
                  :src="teacherAvatar"
                  :alt="course.teacher_name"
                />
                <div v-else class="avatar" :style="coverStyle(course.teacher_name)">
                  {{ initials(course.teacher_name, 1) }}
                </div>
                <div>
                  <strong>{{ course.teacher_name }}</strong>
                  <p>{{ course.teacher_title || '启明学堂讲师' }}</p>
                </div>
                <RouterLink to="/teachers" class="link">查看全部教师 →</RouterLink>
              </div>
            </div>

            <div v-if="course.related?.length" class="panel">
              <h2>同类课程</h2>
              <div class="site-grid site-grid--3">
                <CourseCard v-for="item in course.related" :key="item.id" :course="item" />
              </div>
            </div>
          </div>

          <aside class="side">
            <div class="enroll-card site-card">
              <div class="price-row">
                <span class="price-now">{{ priceText(course.price) }}</span>
                <span v-if="course.original_price > course.price" class="price-old">
                  {{ priceText(course.original_price) }}
                </span>
              </div>

              <ul class="perks">
                <li><el-icon><CircleCheck /></el-icon> 免费试听 1 节课</li>
                <li><el-icon><CircleCheck /></el-icon> 前 3 次课不满意可退费</li>
                <li><el-icon><CircleCheck /></el-icon> 6 人小班 · 双师课堂</li>
                <li><el-icon><CircleCheck /></el-icon> 每月一份学情报告</li>
              </ul>

              <p v-if="site.user" class="account-hint">
                已登录 <strong>{{ site.displayName }}</strong>，报名记录可在
                <RouterLink to="/account">个人中心</RouterLink> 查看进度。
              </p>
              <p v-else class="account-hint">
                登录学员账号后可随时查看报名进度：
                <RouterLink :to="{ path: '/account/login', query: { redirect: route.fullPath } }">
                  立即登录
                </RouterLink>
                或
                <RouterLink :to="{ path: '/account/register', query: { redirect: route.fullPath } }">
                  免费注册
                </RouterLink>
              </p>

              <el-alert
                v-if="submitted"
                type="success"
                :closable="false"
                show-icon
                title="报名已提交"
                description="课程顾问会在 24 小时内与你联系，请保持手机畅通。"
                class="done-alert"
              />
              <el-button v-if="submitted" class="full-btn" @click="resetForm">再约一门课</el-button>

              <el-form v-else ref="formRef" :model="form" :rules="rules" label-position="top">
                <el-form-item label="家长 / 学生姓名" prop="name">
                  <el-input v-model.trim="form.name" placeholder="请输入姓名" />
                </el-form-item>
                <el-form-item label="联系手机号" prop="phone">
                  <el-input v-model.trim="form.phone" placeholder="用于回电确认" maxlength="20" />
                </el-form-item>
                <el-form-item label="孩子年龄 / 年级">
                  <el-input v-model.trim="form.age" placeholder="选填，如 8 岁 / 三年级" />
                </el-form-item>
                <el-form-item label="想了解什么">
                  <el-input
                    v-model.trim="form.remark"
                    type="textarea"
                    :rows="2"
                    maxlength="200"
                    placeholder="选填，如希望周末上课"
                  />
                </el-form-item>
                <el-button type="primary" class="full-btn" :loading="submitting" @click="submit">
                  预约试听 / 报名
                </el-button>
                <p class="privacy">提交即表示同意我们通过电话与你联系，信息仅用于课程咨询。</p>
              </el-form>
            </div>
          </aside>
        </div>
      </section>
    </template>

    <el-empty v-else-if="notFound" description="课程不存在或已下架">
      <el-button type="primary" @click="router.push('/courses')">返回课程中心</el-button>
    </el-empty>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { CircleCheck } from '@element-plus/icons-vue'
import api from '../../utils/request'
import siteApi, { SITE_TOKEN_KEY } from '../../utils/siteRequest'
import { useSiteSessionStore } from '../../stores/siteSession'
import { coverStyle, imageUrl, initials, priceText, type SiteCourse } from '../../utils/site'
import CourseCard from '../../components/site/CourseCard.vue'

const route = useRoute()
const router = useRouter()
const site = useSiteSessionStore()

const loading = ref(false)
const notFound = ref(false)
const course = ref<SiteCourse | null>(null)
const teacherAvatar = computed(() => imageUrl(course.value?.teacher_avatar))
const formRef = ref()
const submitting = ref(false)
const submitted = ref(false)

const form = reactive({ name: '', phone: '', age: '', remark: '' })

const rules = {
  name: [
    { required: true, message: '请输入姓名', trigger: 'blur' },
    { max: 32, message: '姓名过长', trigger: 'blur' },
  ],
  phone: [
    { required: true, message: '请输入手机号', trigger: 'blur' },
    { pattern: /^[0-9+\-\s]{6,20}$/, message: '手机号格式不正确', trigger: 'blur' },
  ],
}

async function load(): Promise<void> {
  const id = Number(route.params.id)
  if (!id) {
    notFound.value = true
    return
  }
  loading.value = true
  notFound.value = false
  try {
    course.value = (await api.get(`/site/courses/${id}`)) as unknown as SiteCourse
  } catch {
    course.value = null
    notFound.value = true
  } finally {
    loading.value = false
  }
}

async function submit(): Promise<void> {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }
  if (!course.value) return
  submitting.value = true
  try {
    // 已登录时后端会把线索归属到学员账号，个人中心即可查看进度
    await siteApi.post('/site/enroll', {
      course_id: course.value.id,
      name: form.name,
      phone: form.phone,
      age: form.age,
      source: '官网',
      remark: form.remark,
    })
    submitted.value = true
  } finally {
    submitting.value = false
  }
}

function resetForm(): void {
  submitted.value = false
  form.name = ''
  form.phone = ''
  form.age = ''
  form.remark = ''
}

// 登录学员打开报名表单时自动带入昵称与手机号，减少重复填写
watch(
  () => site.user,
  (user) => {
    if (!user) return
    if (!form.name) form.name = user.nickname || user.username
    if (!form.phone) form.phone = user.phone
  },
  { immediate: true },
)

watch(
  () => route.params.id,
  () => {
    submitted.value = false
    if (route.name === 'site-course-detail') load()
  },
)

onMounted(() => {
  if (!site.loaded && localStorage.getItem(SITE_TOKEN_KEY)) {
    site.load().catch(() => undefined)
  }
  load()
})
</script>

<style scoped>
.detail-head {
  padding: 40px 0 44px;
  color: #fff;
  position: relative;
}

.detail-head::after {
  content: '';
  position: absolute;
  inset: 0;
  background: rgba(6, 18, 38, 0.42);
}

.detail-head .site-container {
  position: relative;
  z-index: 1;
}

.crumb :deep(.el-breadcrumb__inner),
.crumb :deep(.el-breadcrumb__separator) {
  color: rgba(255, 255, 255, 0.8);
}

.crumb :deep(.el-breadcrumb__inner.is-link:hover) {
  color: #fff;
}

.detail-head h1 {
  margin: 16px 0 10px;
  font-size: 32px;
  line-height: 1.35;
}

.subtitle {
  margin: 0 0 18px;
  color: rgba(255, 255, 255, 0.88);
  font-size: 15px;
  max-width: 720px;
  line-height: 1.8;
}

.meta {
  display: flex;
  gap: 18px;
  flex-wrap: wrap;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.9);
  margin-bottom: 14px;
}

.meta span {
  padding: 4px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.18);
}

.tags :deep(.tag-pill) {
  background: rgba(255, 255, 255, 0.18);
  color: #fff;
}

.layout {
  display: grid;
  grid-template-columns: 1fr 360px;
  gap: 28px;
  align-items: start;
}

.main {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.panel {
  background: #fff;
  border: 1px solid #eaeef6;
  border-radius: 14px;
  padding: 26px 28px;
}

.panel h2 {
  margin: 0 0 16px;
  font-size: 19px;
  color: #0f1c2e;
  position: relative;
  padding-left: 12px;
}

.panel h2::before {
  content: '';
  position: absolute;
  left: 0;
  top: 4px;
  bottom: 4px;
  width: 4px;
  border-radius: 4px;
  background: linear-gradient(180deg, #1677ff, #63b3ff);
}

.desc {
  white-space: pre-wrap;
  color: #4b5563;
  font-size: 14.5px;
  line-height: 2;
}

.plain {
  margin: 0;
  color: #4b5563;
  font-size: 14px;
  line-height: 1.9;
}

.teacher {
  display: flex;
  align-items: center;
  gap: 16px;
}

.teacher .avatar {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 20px;
  font-weight: 600;
}

.teacher .avatar--img {
  object-fit: cover;
  background: #eef2f7;
}

.teacher strong {
  display: block;
  font-size: 16px;
  color: #0f1c2e;
}

.teacher p {
  margin: 4px 0 0;
  color: #8a919f;
  font-size: 13px;
}

.teacher .link {
  margin-left: auto;
  color: #1677ff;
  font-size: 13px;
  text-decoration: none;
}

.side {
  position: sticky;
  top: 92px;
}

.enroll-card {
  padding: 24px;
}

.price-row {
  display: flex;
  align-items: baseline;
  margin-bottom: 16px;
}

.perks {
  list-style: none;
  margin: 0 0 20px;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 9px;
}

.perks li {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #4b5563;
  font-size: 13px;
}

.perks :deep(.el-icon) {
  color: #52c41a;
}

.full-btn {
  width: 100%;
  height: 44px;
  font-weight: 600;
}

.privacy {
  margin: 12px 0 0;
  color: #9aa3b2;
  font-size: 11px;
  line-height: 1.6;
}

.done-alert {
  margin-bottom: 12px;
}

.account-hint {
  margin: 0 0 16px;
  padding: 10px 12px;
  border-radius: 10px;
  background: #f3f8ff;
  color: #5b6675;
  font-size: 12.5px;
  line-height: 1.7;
}

.account-hint a {
  color: #1677ff;
  text-decoration: none;
}

.account-hint a:hover {
  text-decoration: underline;
}

@media (max-width: 900px) {
  .layout {
    grid-template-columns: 1fr;
  }

  .side {
    position: static;
  }

  .detail-head h1 {
    font-size: 24px;
  }
}
</style>
