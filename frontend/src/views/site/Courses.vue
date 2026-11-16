<template>
  <div>
    <section class="page-head">
      <div class="site-container">
        <h1>课程中心</h1>
        <p>按课程体系、阶段筛选，找到最适合孩子的那一门</p>
      </div>
    </section>

    <section class="site-section">
      <div class="site-container">
        <div class="filters">
          <el-input
            v-model="keyword"
            size="large"
            placeholder="搜索课程名称、标签"
            :prefix-icon="Search"
            clearable
            class="search"
            @keyup.enter="search"
            @clear="search"
          />

          <div class="filter-row">
            <span class="filter-label">课程体系</span>
            <div class="chips">
              <button
                class="chip"
                :class="{ active: !categoryId }"
                @click="pickCategory(0)"
              >全部</button>
              <button
                v-for="cat in categories"
                :key="cat.id"
                class="chip"
                :class="{ active: categoryId === cat.id }"
                @click="pickCategory(cat.id)"
              >{{ cat.name }}</button>
            </div>
          </div>

          <div class="filter-row">
            <span class="filter-label">适合阶段</span>
            <div class="chips">
              <button
                v-for="level in levels"
                :key="level"
                class="chip"
                :class="{ active: activeLevel === level }"
                @click="pickLevel(level)"
              >{{ level || '全部' }}</button>
            </div>
          </div>
        </div>

        <div v-loading="loading" class="result">
          <div class="result-head">
            <span>共 {{ total }} 门课程</span>
            <el-button link type="primary" @click="reset">重置筛选</el-button>
          </div>

          <div v-if="list.length" class="site-grid site-grid--3">
            <CourseCard v-for="course in list" :key="course.id" :course="course" />
          </div>
          <el-empty v-else description="没有找到符合条件的课程，换个关键词试试" />

          <div v-if="total > size" class="pagination">
            <el-pagination
              v-model:current-page="page"
              :page-size="size"
              :total="total"
              layout="prev, pager, next"
              background
              @current-change="load"
            />
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Search } from '@element-plus/icons-vue'
import api from '../../utils/request'
import type { SiteCourse } from '../../utils/site'
import CourseCard from '../../components/site/CourseCard.vue'

const route = useRoute()
const router = useRouter()

const levels = ['', '启蒙', '入门', '进阶', '竞赛', '冲刺', '同步']

const keyword = ref(String(route.query.keyword || ''))
const categoryId = ref(Number(route.query.category || 0))
const activeLevel = ref(String(route.query.level || ''))
const categories = ref<{ id: number; name: string }[]>([])
const list = ref<SiteCourse[]>([])
const total = ref(0)
const page = ref(1)
const size = 9
const loading = ref(false)

function syncQuery(): void {
  router.replace({
    path: '/courses',
    query: {
      ...(keyword.value ? { keyword: keyword.value } : {}),
      ...(categoryId.value ? { category: String(categoryId.value) } : {}),
      ...(activeLevel.value ? { level: activeLevel.value } : {}),
    },
  })
}

async function load(): Promise<void> {
  loading.value = true
  try {
    const data = (await api.get('/site/courses', {
      params: {
        keyword: keyword.value,
        category_id: categoryId.value,
        level: activeLevel.value,
        page: page.value,
        size,
      },
    })) as unknown as { total: number; list: SiteCourse[] }
    list.value = data.list
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function search(): void {
  page.value = 1
  syncQuery()
  load()
}

function pickCategory(id: number): void {
  categoryId.value = id
  search()
}

function pickLevel(level: string): void {
  activeLevel.value = level
  search()
}

function reset(): void {
  keyword.value = ''
  categoryId.value = 0
  activeLevel.value = ''
  search()
}

onMounted(async () => {
  categories.value = (await api.get('/site/categories')) as unknown as { id: number; name: string }[]
  await load()
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

.filters {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 22px 24px;
  border-radius: 14px;
  background: #fff;
  border: 1px solid #eaeef6;
}

.search {
  max-width: 420px;
}

.filter-row {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
}

.filter-label {
  color: #8a919f;
  font-size: 13px;
  min-width: 60px;
}

.chips {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.chip {
  padding: 6px 16px;
  border-radius: 999px;
  border: 1px solid #e6ebf3;
  background: #fff;
  color: #4b5563;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.chip:hover {
  border-color: #1677ff;
  color: #1677ff;
}

.chip.active {
  background: #1677ff;
  border-color: #1677ff;
  color: #fff;
}

.result {
  margin-top: 28px;
}

.result-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: #8a919f;
  font-size: 13px;
  margin-bottom: 18px;
}

.pagination {
  display: flex;
  justify-content: center;
  margin-top: 34px;
}
</style>
