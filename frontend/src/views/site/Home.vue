<template>
  <div v-loading="loading">
    <!-- Hero -->
    <section class="hero">
      <div class="site-container hero-inner">
        <div class="hero-copy">
          <span class="hero-badge">2026 春季班火热报名中 · 前 50 名享早鸟价</span>
          <h1>让每一次进步<br /><span>都被看见</span></h1>
          <p class="hero-sub">
            中小学学科辅导 + 少儿编程，小班制教学、双师课堂、每月学情报告。
            先试听，再决定。
          </p>

          <div class="hero-search">
            <el-input
              v-model="keyword"
              size="large"
              placeholder="搜索课程，如「少儿编程」「中考冲刺」"
              :prefix-icon="Search"
              clearable
              @keyup.enter="goCourses"
            />
            <el-button type="primary" size="large" @click="goCourses">查找课程</el-button>
          </div>

          <div class="hero-stats">
            <div v-for="item in statItems" :key="item.label" class="hero-stat">
              <strong>{{ item.value }}</strong>
              <span>{{ item.label }}</span>
            </div>
          </div>
        </div>

        <div class="hero-visual">
          <div class="visual-card visual-card--main">
            <div class="vc-title">本月学情报告</div>
            <div class="vc-row"><span>知识点掌握</span><b>92%</b></div>
            <div class="vc-bar"><i style="width: 92%" /></div>
            <div class="vc-row"><span>作业完成率</span><b>100%</b></div>
            <div class="vc-bar"><i style="width: 100%" /></div>
            <div class="vc-row"><span>课堂参与度</span><b>88%</b></div>
            <div class="vc-bar"><i style="width: 88%" /></div>
          </div>
          <div class="visual-card visual-card--float">
            <el-icon :size="18" color="#1677ff"><Trophy /></el-icon>
            <div>
              <strong>12</strong>
              <span>CSP-J 一等奖</span>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 分类 -->
    <section class="site-section">
      <div class="site-container">
        <div class="section-head">
          <div class="section-eyebrow">COURSE SYSTEM</div>
          <h2 class="section-title">四大课程体系</h2>
          <p class="section-sub">按年龄与目标分层设计，报名前可先预约免费试听</p>
        </div>

        <div class="site-grid site-grid--4">
          <RouterLink
            v-for="cat in data.categories"
            :key="cat.id"
            :to="{ path: '/courses', query: { category: cat.id } }"
            class="category-card site-card"
          >
            <span class="cat-icon">
              <el-icon :size="22"><component :is="iconOf(cat.icon)" /></el-icon>
            </span>
            <h3>{{ cat.name }}</h3>
            <p>{{ cat.desc }}</p>
            <span class="cat-more">查看课程 →</span>
          </RouterLink>
        </div>
      </div>
    </section>

    <!-- 推荐课程 -->
    <section class="site-section site-section--muted">
      <div class="site-container">
        <div class="section-head">
          <div class="section-eyebrow">POPULAR COURSES</div>
          <h2 class="section-title">推荐课程</h2>
          <p class="section-sub">教研团队每学期评估一次，只保留真正有效的课程</p>
        </div>

        <div v-if="data.recommend.length" class="site-grid site-grid--3">
          <CourseCard v-for="course in data.recommend" :key="course.id" :course="course" />
        </div>
        <el-empty v-else description="课程正在上新中" />

        <div class="more-wrap">
          <RouterLink to="/courses" class="more-btn">查看全部 {{ data.stats.courses }} 门课程</RouterLink>
        </div>
      </div>
    </section>

    <!-- 为什么选择 -->
    <section class="site-section">
      <div class="site-container">
        <div class="section-head">
          <div class="section-eyebrow">WHY US</div>
          <h2 class="section-title">为什么选择启明学堂</h2>
        </div>

        <div class="site-grid site-grid--4">
          <div v-for="item in reasons" :key="item.title" class="reason site-card">
            <span class="reason-icon">
              <el-icon :size="20"><component :is="item.icon" /></el-icon>
            </span>
            <h3>{{ item.title }}</h3>
            <p>{{ item.desc }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- 师资 -->
    <section class="site-section site-section--muted">
      <div class="site-container">
        <div class="section-head">
          <div class="section-eyebrow">TEACHERS</div>
          <h2 class="section-title">授课教师</h2>
          <p class="section-sub">平均教龄 7 年以上，试听即见真人</p>
        </div>

        <div class="site-grid site-grid--4">
          <TeacherCard v-for="teacher in data.teachers" :key="teacher.id" :teacher="teacher" />
        </div>

        <div class="more-wrap">
          <RouterLink to="/teachers" class="more-btn more-btn--ghost">认识全部老师</RouterLink>
        </div>
      </div>
    </section>

    <!-- 动态 -->
    <section class="site-section">
      <div class="site-container">
        <div class="section-head">
          <div class="section-eyebrow">NEWS</div>
          <h2 class="section-title">机构动态</h2>
        </div>

        <div v-if="data.articles.length" class="news-list">
          <RouterLink
            v-for="article in data.articles"
            :key="article.id"
            :to="{ path: '/news', query: { id: article.id } }"
            class="news-item"
          >
            <span class="news-date">{{ article.published_at }}</span>
            <span class="news-cat">{{ article.category }}</span>
            <span class="news-title">{{ article.title }}</span>
            <span class="news-arrow">→</span>
          </RouterLink>
        </div>
        <el-empty v-else description="暂无动态" />
      </div>
    </section>

    <!-- CTA -->
    <section class="cta">
      <div class="site-container cta-inner">
        <div>
          <h2>先上一节试听课，再做决定</h2>
          <p>填写手机号即可预约，课程顾问会在 24 小时内与你联系，不推销、不留作业。</p>
        </div>
        <el-button type="primary" size="large" class="cta-btn" @click="router.push('/courses')">
          立即预约试听
        </el-button>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, type Component } from 'vue'
import { useRouter } from 'vue-router'
import {
  ChatDotRound,
  Monitor,
  Reading,
  Search,
  Star,
  Timer,
  Trophy,
  UserFilled,
  Brush,
  Files,
  Notebook,
  Collection,
} from '@element-plus/icons-vue'
import api from '../../utils/request'
import type { SiteHomeData } from '../../utils/site'
import CourseCard from '../../components/site/CourseCard.vue'
import TeacherCard from '../../components/site/TeacherCard.vue'

const router = useRouter()
const loading = ref(false)
const keyword = ref('')
const data = ref<SiteHomeData>({
  stats: { courses: 0, teachers: 0, categories: 0, enrollments: 0 },
  categories: [],
  recommend: [],
  hot: [],
  teachers: [],
  articles: [],
})

const statItems = computed(() => [
  { label: '在售课程', value: `${data.value.stats.courses}` },
  { label: '授课教师', value: `${data.value.stats.teachers}` },
  { label: '课程体系', value: `${data.value.stats.categories}` },
  { label: '累计报名', value: `${data.value.stats.enrollments}` },
])

const reasons = [
  { icon: UserFilled, title: '6 人小班', desc: '主讲 + 助教双师，每个孩子每节课都有发言机会。' },
  { icon: Notebook, title: '每月学情报告', desc: '知识掌握、作业完成、课堂参与三维记录，家长看得懂。' },
  { icon: Trophy, title: '竞赛成果可查', desc: '近三年 CSP-J 累计 12 个一等奖，成绩单公开可核。' },
  { icon: Timer, title: '不满意随时退', desc: '前 3 次课不满意可全额退费，不设附加条件。' },
]

const ICON_MAP: Record<string, Component> = {
  Monitor,
  Reading,
  ChatDotRound,
  Brush,
  Files,
  Notebook,
  Collection,
  Star,
}

function iconOf(name?: string): Component {
  return (name && ICON_MAP[name]) || Collection
}

function goCourses(): void {
  router.push({ path: '/courses', query: keyword.value ? { keyword: keyword.value } : {} })
}

async function load(): Promise<void> {
  loading.value = true
  try {
    data.value = (await api.get('/site/home')) as unknown as SiteHomeData
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.hero {
  background: radial-gradient(circle at 82% 12%, #dbe9ff 0%, #f5f8ff 45%, #ffffff 100%);
  padding: 72px 0 64px;
  overflow: hidden;
}

.hero-inner {
  display: grid;
  grid-template-columns: 1.15fr 0.85fr;
  gap: 48px;
  align-items: center;
}

.hero-badge {
  display: inline-block;
  padding: 6px 14px;
  border-radius: 999px;
  background: #e8f1ff;
  color: #1677ff;
  font-size: 12px;
  font-weight: 600;
}

.hero h1 {
  margin: 18px 0 16px;
  font-size: 44px;
  line-height: 1.25;
  color: #0f1c2e;
  letter-spacing: 1px;
}

.hero h1 span {
  background: linear-gradient(135deg, #1677ff, #4aa3ff);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.hero-sub {
  margin: 0 0 26px;
  max-width: 460px;
  color: #5c6675;
  font-size: 15px;
  line-height: 1.9;
}

.hero-search {
  display: flex;
  gap: 10px;
  max-width: 520px;
  padding: 8px;
  background: #fff;
  border-radius: 14px;
  box-shadow: 0 10px 28px rgba(15, 28, 46, 0.08);
}

.hero-search :deep(.el-input__wrapper) {
  box-shadow: none;
}

.hero-stats {
  display: flex;
  gap: 38px;
  margin-top: 34px;
}

.hero-stat strong {
  display: block;
  font-size: 26px;
  color: #0f1c2e;
}

.hero-stat span {
  font-size: 12px;
  color: #8a919f;
}

.hero-visual {
  position: relative;
  min-height: 300px;
}

.visual-card {
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 18px 44px rgba(15, 28, 46, 0.1);
}

.visual-card--main {
  padding: 24px;
}

.vc-title {
  font-weight: 600;
  color: #0f1c2e;
  margin-bottom: 16px;
}

.vc-row {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  color: #5c6675;
  margin-bottom: 8px;
}

.vc-row b {
  color: #1677ff;
}

.vc-bar {
  height: 8px;
  border-radius: 999px;
  background: #eef2f8;
  overflow: hidden;
  margin-bottom: 16px;
}

.vc-bar i {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, #1677ff, #63b3ff);
}

.visual-card--float {
  position: absolute;
  right: -6px;
  bottom: 6px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 18px;
}

.visual-card--float strong {
  display: block;
  font-size: 18px;
  color: #0f1c2e;
}

.visual-card--float span {
  font-size: 11px;
  color: #8a919f;
}

.category-card {
  padding: 24px 20px;
  text-decoration: none;
  color: inherit;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.cat-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #eef4ff;
  color: #1677ff;
}

.category-card h3 {
  margin: 0;
  font-size: 17px;
  color: #0f1c2e;
}

.category-card p {
  margin: 0;
  font-size: 13px;
  color: #6b7280;
  line-height: 1.7;
  min-height: 44px;
}

.cat-more {
  font-size: 13px;
  color: #1677ff;
}

.more-wrap {
  text-align: center;
  margin-top: 32px;
}

.more-btn {
  display: inline-block;
  padding: 12px 28px;
  border-radius: 999px;
  background: #1677ff;
  color: #fff;
  text-decoration: none;
  font-size: 14px;
  transition: background 0.15s ease;
}

.more-btn:hover {
  background: #0d5fd6;
}

.more-btn--ghost {
  background: #fff;
  color: #1677ff;
  border: 1px solid #1677ff;
}

.reason {
  padding: 24px 20px;
}

.reason-icon {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #e8f1ff, #f2f7ff);
  color: #1677ff;
  margin-bottom: 14px;
}

.reason h3 {
  margin: 0 0 8px;
  font-size: 16px;
  color: #0f1c2e;
}

.reason p {
  margin: 0;
  font-size: 13px;
  color: #6b7280;
  line-height: 1.75;
}

.news-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-width: 900px;
  margin: 0 auto;
}

.news-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 18px 20px;
  border-radius: 12px;
  text-decoration: none;
  color: inherit;
  transition: background 0.15s ease;
}

.news-item:hover {
  background: #f4f8ff;
}

.news-date {
  color: #8a919f;
  font-size: 13px;
  white-space: nowrap;
}

.news-cat {
  padding: 2px 9px;
  border-radius: 999px;
  background: #eef4ff;
  color: #1677ff;
  font-size: 12px;
  white-space: nowrap;
}

.news-title {
  flex: 1;
  color: #0f1c2e;
  font-size: 15px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.news-arrow {
  color: #b6c0cf;
}

.cta {
  background: linear-gradient(135deg, #0f3d8f, #1677ff);
  color: #fff;
  padding: 48px 0;
}

.cta-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  flex-wrap: wrap;
}

.cta h2 {
  margin: 0 0 8px;
  font-size: 26px;
}

.cta p {
  margin: 0;
  color: #cfe0ff;
  font-size: 14px;
}

.cta-btn {
  background: #fff;
  color: #1677ff;
  border-color: #fff;
  padding: 0 30px;
  height: 48px;
  font-weight: 600;
}

@media (max-width: 900px) {
  .hero-inner {
    grid-template-columns: 1fr;
  }

  .hero h1 {
    font-size: 32px;
  }

  .hero-visual {
    display: none;
  }

  .hero-stats {
    gap: 24px;
    flex-wrap: wrap;
  }
}
</style>
