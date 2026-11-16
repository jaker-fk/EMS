<template>
  <article class="course-card site-card">
    <RouterLink :to="`/courses/${course.id}`" class="cover cover-thumb" :style="coverStyle(course.title)">
      <span>{{ initials(course.title) }}</span>
      <em v-if="course.level" class="level">{{ course.level }}</em>
      <em v-if="course.view_count" class="views">{{ course.view_count }} 人浏览</em>
    </RouterLink>

    <div class="body">
      <div class="meta">
        <span class="cat">{{ course.category_name || '全部课程' }}</span>
        <span class="lessons">{{ course.lessons }} 课时</span>
      </div>

      <h3 class="title">
        <RouterLink :to="`/courses/${course.id}`">{{ course.title }}</RouterLink>
      </h3>
      <p class="summary">{{ course.summary || course.subtitle }}</p>

      <div v-if="course.tags?.length" class="tags">
        <span v-for="tag in course.tags.slice(0, 3)" :key="tag" class="tag-pill">{{ tag }}</span>
      </div>

      <div class="teacher" v-if="course.teacher_name">
        <span class="avatar-dot">{{ initials(course.teacher_name, 1) }}</span>
        授课：{{ course.teacher_name }}
        <em v-if="course.teacher_title">· {{ course.teacher_title }}</em>
      </div>

      <div class="foot">
        <div class="price">
          <span class="price-now">{{ priceText(course.price) }}</span>
          <span v-if="course.original_price && course.original_price > course.price" class="price-old">
            {{ priceText(course.original_price) }}
          </span>
        </div>
        <RouterLink :to="`/courses/${course.id}`" class="detail-btn">查看详情</RouterLink>
      </div>
    </div>
  </article>
</template>

<script setup lang="ts">
import { coverStyle, initials, priceText, type SiteCourse } from '../../utils/site'

defineProps<{ course: SiteCourse }>()
</script>

<style scoped>
.course-card {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.cover {
  height: 148px;
  text-decoration: none;
}

.cover .level,
.cover .views {
  position: absolute;
  z-index: 1;
  font-size: 11px;
  font-style: normal;
  padding: 3px 9px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.22);
  backdrop-filter: blur(4px);
}

.cover .level {
  top: 12px;
  left: 12px;
}

.cover .views {
  right: 12px;
  bottom: 12px;
}

.body {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 16px 18px 18px;
  flex: 1;
}

.meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #8a919f;
}

.cat {
  color: #1677ff;
  background: #eef4ff;
  padding: 2px 9px;
  border-radius: 999px;
}

.title {
  margin: 2px 0 0;
  font-size: 16px;
  line-height: 1.45;
  font-weight: 600;
}

.title a {
  color: #0f1c2e;
  text-decoration: none;
}

.title a:hover {
  color: #1677ff;
}

.summary {
  margin: 0;
  color: #6b7280;
  font-size: 13px;
  line-height: 1.7;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.teacher {
  font-size: 12px;
  color: #6b7280;
  display: flex;
  align-items: center;
  gap: 6px;
}

.teacher em {
  font-style: normal;
  color: #9aa3b2;
}

.avatar-dot {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: linear-gradient(135deg, #1677ff, #4aa3ff);
  color: #fff;
  font-size: 11px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.foot {
  margin-top: auto;
  padding-top: 12px;
  border-top: 1px dashed #eef1f6;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.detail-btn {
  padding: 7px 16px;
  border-radius: 999px;
  border: 1px solid #1677ff;
  color: #1677ff;
  font-size: 13px;
  text-decoration: none;
  transition: all 0.15s ease;
}

.detail-btn:hover {
  background: #1677ff;
  color: #fff;
}
</style>
