<template>
  <el-card class="err-card" shadow="never">
    <el-result icon="warning" title="403" sub-title="抱歉，当前账号没有访问该页面的权限">
      <template #extra>
        <el-button type="primary" @click="router.replace('/dashboard')">返回首页</el-button>
        <el-button @click="router.back()">返回上一页</el-button>
      </template>
    </el-result>
    <p v-if="fromPath" class="muted center">受限路径：{{ fromPath }}</p>
  </el-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const fromPath = computed(() => String(route.query.from || ''))
</script>

<style scoped>
.err-card {
  border-radius: var(--app-radius);
}

.center {
  text-align: center;
}
</style>
