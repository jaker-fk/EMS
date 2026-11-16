<template>
  <el-card class="err-card" shadow="never">
    <el-result icon="info" title="404" sub-title="页面不存在，可能已被移除或地址输入有误">
      <template #extra>
        <el-button type="primary" @click="router.replace('/dashboard')">返回首页</el-button>
        <el-button @click="router.back()">返回上一页</el-button>
      </template>
    </el-result>
    <p class="muted center">当前路径：{{ route.fullPath }}</p>
  </el-card>
</template>

<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
</script>

<style scoped>
.err-card {
  border-radius: var(--app-radius);
}

.center {
  text-align: center;
}
</style>
