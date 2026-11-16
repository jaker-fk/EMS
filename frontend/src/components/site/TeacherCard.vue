<template>
  <article class="teacher-card site-card">
    <div class="head">
      <div class="avatar" :style="coverStyle(teacher.name)">
        <span>{{ initials(teacher.name, 1) }}</span>
      </div>
      <div class="who">
        <h3>{{ teacher.name }}</h3>
        <p class="title">{{ teacher.title }}</p>
      </div>
      <span v-if="teacher.years" class="years">{{ teacher.years }} 年教龄</span>
    </div>

    <p class="intro">{{ teacher.intro }}</p>

    <div v-if="teacher.tags?.length" class="tags">
      <span v-for="tag in teacher.tags.slice(0, 3)" :key="tag" class="tag-pill">{{ tag }}</span>
    </div>
  </article>
</template>

<script setup lang="ts">
import { coverStyle, initials, type SiteTeacher } from '../../utils/site'

defineProps<{ teacher: SiteTeacher }>()
</script>

<style scoped>
.teacher-card {
  padding: 22px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.head {
  display: flex;
  align-items: center;
  gap: 14px;
}

.avatar {
  width: 54px;
  height: 54px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 20px;
  font-weight: 600;
  flex: none;
}

.who h3 {
  margin: 0 0 4px;
  font-size: 16px;
  color: #0f1c2e;
}

.who .title {
  margin: 0;
  font-size: 12px;
  color: #1677ff;
}

.years {
  margin-left: auto;
  font-size: 12px;
  color: #8a919f;
  white-space: nowrap;
}

.intro {
  margin: 0;
  color: #5c6675;
  font-size: 13px;
  line-height: 1.8;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.tags {
  margin-top: auto;
}
</style>
