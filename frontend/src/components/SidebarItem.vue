<template>
  <el-sub-menu v-if="item.children && item.children.length" :index="item.path || String(item.id)">
    <template #title>{{ item.name }}</template>
    <SidebarItem v-for="c in item.children" :key="c.id" :item="c" />
  </el-sub-menu>
  <el-menu-item v-else :index="item.path">{{ item.name }}</el-menu-item>
</template>

<script setup lang="ts">
defineOptions({ name: 'SidebarItem' })
defineProps<{ item: { id: number; name: string; path: string; children?: any[] } }>()
</script>
