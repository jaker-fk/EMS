<template>
  <el-sub-menu v-if="item.children && item.children.length" :index="item.path || String(item.id)">
    <template #title>
      <el-icon v-if="iconComp"><component :is="iconComp" /></el-icon>
      <span>{{ item.name }}</span>
    </template>
    <SidebarItem v-for="child in item.children" :key="child.id" :item="child" />
  </el-sub-menu>

  <el-menu-item v-else :index="item.path || String(item.id)">
    <el-icon v-if="iconComp"><component :is="iconComp" /></el-icon>
    <template #title>{{ item.name }}</template>
  </el-menu-item>
</template>

<script setup lang="ts">
import { computed, type Component } from 'vue'
import * as Icons from '@element-plus/icons-vue'
import type { MenuNode } from '../stores/session'

defineOptions({ name: 'SidebarItem' })

const props = defineProps<{ item: MenuNode }>()

const iconComp = computed<Component | null>(() => {
  const name = props.item.icon
  if (!name) return null
  return (Icons as unknown as Record<string, Component>)[name] ?? null
})
</script>
