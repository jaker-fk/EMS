<template>
  <div>
    <section class="page-head">
      <div class="site-container">
        <h1>师资团队</h1>
        <p>所有授课老师均通过试讲考核，平均教龄 7 年以上，可指定试听</p>
      </div>
    </section>

    <section class="site-section">
      <div class="site-container">
        <div v-loading="loading">
          <div v-if="teachers.length" class="site-grid site-grid--4">
            <TeacherCard v-for="teacher in teachers" :key="teacher.id" :teacher="teacher" />
          </div>
          <el-empty v-else description="师资信息更新中" />
        </div>
      </div>
    </section>

    <section class="site-section site-section--muted">
      <div class="site-container">
        <div class="section-head">
          <div class="section-eyebrow">TEACHING BELIEF</div>
          <h2 class="section-title">我们的教学原则</h2>
        </div>
        <div class="site-grid site-grid--3">
          <div v-for="item in beliefs" :key="item.title" class="belief site-card">
            <h3>{{ item.title }}</h3>
            <p>{{ item.desc }}</p>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import api from '../../utils/request'
import type { SiteTeacher } from '../../utils/site'
import TeacherCard from '../../components/site/TeacherCard.vue'

const teachers = ref<SiteTeacher[]>([])
const loading = ref(false)

const beliefs = [
  {
    title: '先诊断，再上课',
    desc: '每位新学员入学前做一次摸底测评，按薄弱点排课，不做无差别刷题。',
  },
  {
    title: '讲清楚「为什么」',
    desc: '不只教解法，更讲清楚思路从哪来，让孩子遇到新题也能迁移。',
  },
  {
    title: '把反馈交给家长',
    desc: '每月一份学情报告，记录掌握度、课堂表现与下阶段建议，家长可随时约谈。',
  },
]

onMounted(async () => {
  loading.value = true
  try {
    teachers.value = (await api.get('/site/teachers')) as unknown as SiteTeacher[]
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.page-head {
  padding: 52px 0 40px;
  background: radial-gradient(circle at 20% 10%, #e2eeff 0%, #f7faff 60%, #fff 100%);
}

.page-head h1 {
  margin: 0 0 10px;
  font-size: 32px;
  color: #0f1c2e;
}

.page-head p {
  margin: 0;
  color: #6b7280;
  font-size: 14px;
}

.belief {
  padding: 26px 24px;
}

.belief h3 {
  margin: 0 0 10px;
  font-size: 17px;
  color: #0f1c2e;
}

.belief p {
  margin: 0;
  color: #5c6675;
  font-size: 13.5px;
  line-height: 1.85;
}
</style>
