<template>
  <div>
    <section class="page-head">
      <div class="site-container">
        <h1>机构动态</h1>
        <p>班课安排、学员成绩与家庭教育分享</p>
      </div>
    </section>

    <section class="site-section">
      <div class="site-container">
        <div v-loading="loading">
          <div v-if="list.length" class="news-wrap">
            <article
              v-for="item in list"
              :key="item.id"
              class="news-card site-card"
              @click="openDetail(item.id)"
            >
              <div class="news-side">
                <span class="news-cat">{{ item.category }}</span>
                <span class="news-date">{{ item.published_at }}</span>
              </div>
              <div class="news-body">
                <h3>{{ item.title }}</h3>
                <p>{{ item.summary }}</p>
                <span class="read-more">阅读全文 →</span>
              </div>
            </article>
          </div>
          <el-empty v-else description="暂无动态" />

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

    <el-dialog v-model="visible" :title="detail?.title" width="720px" class="news-dialog">
      <div v-if="detail" class="dialog-body">
        <div class="dialog-meta">
          <span class="news-cat">{{ detail.category }}</span>
          <span class="news-date">{{ detail.published_at }}</span>
        </div>
        <div class="content">{{ detail.content }}</div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../../utils/request'
import type { SiteArticle } from '../../utils/site'

const route = useRoute()
const router = useRouter()

const list = ref<SiteArticle[]>([])
const total = ref(0)
const page = ref(1)
const size = 8
const loading = ref(false)
const visible = ref(false)
const detail = ref<SiteArticle | null>(null)

async function load(): Promise<void> {
  loading.value = true
  try {
    const data = (await api.get('/site/articles', {
      params: { page: page.value, size },
    })) as unknown as { total: number; list: SiteArticle[] }
    list.value = data.list
    total.value = data.total
  } finally {
    loading.value = false
  }
}

async function openDetail(id: number): Promise<void> {
  try {
    detail.value = (await api.get(`/site/articles/${id}`)) as unknown as SiteArticle
    visible.value = true
    router.replace({ path: '/news', query: {} })
  } catch {
    /* 提示已由拦截器处理 */
  }
}

onMounted(async () => {
  await load()
  const id = Number(route.query.id)
  if (id) await openDetail(id)
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

.news-wrap {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 900px;
  margin: 0 auto;
}

.news-card {
  display: flex;
  gap: 22px;
  padding: 24px 26px;
  cursor: pointer;
}

.news-side {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 88px;
  align-items: flex-start;
}

.news-cat {
  padding: 2px 10px;
  border-radius: 999px;
  background: #eef4ff;
  color: #1677ff;
  font-size: 12px;
  white-space: nowrap;
}

.news-date {
  color: #9aa3b2;
  font-size: 12px;
}

.news-body h3 {
  margin: 0 0 8px;
  font-size: 17px;
  color: #0f1c2e;
}

.news-body p {
  margin: 0 0 10px;
  color: #6b7280;
  font-size: 13.5px;
  line-height: 1.8;
}

.read-more {
  color: #1677ff;
  font-size: 13px;
}

.pagination {
  display: flex;
  justify-content: center;
  margin-top: 30px;
}

.dialog-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 18px;
}

.content {
  white-space: pre-wrap;
  color: #33415c;
  font-size: 14.5px;
  line-height: 2;
  max-height: 62vh;
  overflow: auto;
}
</style>
