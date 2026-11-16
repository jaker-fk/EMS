<template>
  <div class="page" v-loading="loading">
    <div class="stat-grid">
      <div v-for="card in statCards" :key="card.label" class="stat-card">
        <div class="stat-label">{{ card.label }}</div>
        <div class="stat-value">{{ card.value }}</div>
        <div class="stat-foot">{{ card.foot }}</div>
        <div class="stat-icon" :style="{ background: card.bg, color: card.color }">
          <el-icon :size="20"><component :is="card.icon" /></el-icon>
        </div>
      </div>
    </div>

    <el-row :gutter="12">
      <el-col :xs="24" :lg="15">
        <el-card class="page-card" shadow="never">
          <template #header>
            <div class="card-header">
              <span class="card-title">近 7 天操作趋势</span>
              <span class="muted">共 {{ weekTotal }} 次操作</span>
            </div>
          </template>
          <svg class="trend-svg" :viewBox="`0 0 ${chart.w} ${chart.h}`" role="img" aria-label="近七天操作趋势">
            <line
              v-for="tick in chart.ticks"
              :key="`grid-${tick.value}`"
              :x1="chart.padL"
              :x2="chart.w - 16"
              :y1="tick.y"
              :y2="tick.y"
              stroke="#eef1f6"
              stroke-width="1"
            />
            <text
              v-for="tick in chart.ticks"
              :key="`label-${tick.value}`"
              :x="chart.padL - 8"
              :y="tick.y + 4"
              text-anchor="end"
              class="axis-text"
            >{{ tick.value }}</text>
            <path v-if="chart.area" :d="chart.area" fill="url(#trendGradient)" />
            <path v-if="chart.line" :d="chart.line" fill="none" stroke="#1677ff" stroke-width="2" />
            <g v-for="point in chart.points" :key="point.date">
              <circle :cx="point.x" :cy="point.y" r="4" fill="#fff" stroke="#1677ff" stroke-width="2" />
              <text :x="point.x" :y="chart.h - 8" text-anchor="middle" class="axis-text">
                {{ point.date }}
              </text>
              <title>{{ point.date }}：{{ point.count }} 次</title>
            </g>
            <defs>
              <linearGradient id="trendGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color="#1677ff" stop-opacity="0.22" />
                <stop offset="100%" stop-color="#1677ff" stop-opacity="0" />
              </linearGradient>
            </defs>
          </svg>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="9">
        <el-card class="page-card" shadow="never">
          <template #header>
            <div class="card-header">
              <span class="card-title">操作模块分布</span>
              <span class="muted">累计</span>
            </div>
          </template>
          <el-empty v-if="!modules.length" description="暂无操作记录" :image-size="70" />
          <ul v-else class="module-list">
            <li v-for="item in modules" :key="item.name" class="module-item">
              <div class="module-head">
                <span>{{ item.name }}</span>
                <span class="muted">{{ item.value }}</span>
              </div>
              <el-progress
                :percentage="modulePercent(item.value)"
                :show-text="false"
                :stroke-width="8"
                color="#1677ff"
              />
            </li>
          </ul>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="12">
      <el-col :xs="24" :lg="15">
        <el-card class="page-card" shadow="never">
          <template #header>
            <div class="card-header">
              <span class="card-title">最近操作</span>
              <el-button v-if="canViewLogs" link type="primary" @click="router.push('/logs')">
                查看全部
              </el-button>
            </div>
          </template>
          <el-table :data="recent" size="small" border>
            <el-table-column prop="username" label="操作人" width="110" />
            <el-table-column prop="module" label="模块" width="110" />
            <el-table-column prop="action" label="类型" width="90" />
            <el-table-column prop="path" label="请求地址" min-width="170" show-overflow-tooltip />
            <el-table-column label="结果" width="80">
              <template #default="{ row }">
                <el-tag :type="row.result === '成功' ? 'success' : 'danger'" size="small">
                  {{ row.result }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="时间" width="165" />
          </el-table>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="9">
        <el-card class="page-card" shadow="never">
          <template #header>
            <div class="card-header">
              <span class="card-title">系统信息</span>
              <el-tag size="small" type="success">运行中</el-tag>
            </div>
          </template>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="应用名称">{{ system.app || '-' }}</el-descriptions-item>
            <el-descriptions-item label="版本">{{ system.version || '-' }}</el-descriptions-item>
            <el-descriptions-item label="数据库">{{ system.database || '-' }}</el-descriptions-item>
            <el-descriptions-item label="缓存">
              <el-tag size="small" :type="system.cache === 'redis' ? 'success' : 'info'">
                {{ system.cache === 'redis' ? 'Redis' : '进程内存（降级）' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="验证码">
              {{ system.captcha ? '已开启' : '已关闭' }}
            </el-descriptions-item>
            <el-descriptions-item label="Python">{{ system.python || '-' }}</el-descriptions-item>
            <el-descriptions-item label="已运行">{{ uptimeText }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  Avatar,
  TrendCharts,
  User,
  WarningFilled,
} from '@element-plus/icons-vue'
import api from '../utils/request'
import { hasPerm } from '../utils/auth'

interface TrendPoint {
  date: string
  count: number
}

interface LogRow {
  id: number
  username: string
  module: string
  action: string
  path: string
  result: string
  created_at: string
}

interface Overview {
  cards: Record<string, number>
  todayLogs: number
  failLogs: number
  newUsers: number
  trend: TrendPoint[]
  modules: { name: string; value: number }[]
  recent: LogRow[]
  system: {
    app: string
    version: string
    python: string
    database: string
    cache: string
    captcha: boolean
    uptime: number
  }
}

const router = useRouter()
const loading = ref(false)
const data = ref<Overview | null>(null)

const canViewLogs = computed(() => hasPerm('system:log:list'))

const cards = computed(() => data.value?.cards || {})
const trend = computed(() => data.value?.trend || [])
const modules = computed(() => data.value?.modules || [])
const recent = computed(() => data.value?.recent || [])
const system = computed(() => data.value?.system || ({} as Overview['system']))

const weekTotal = computed(() => trend.value.reduce((sum, item) => sum + item.count, 0))

const statCards = computed(() => [
  {
    label: '用户总数',
    value: cards.value.users ?? 0,
    foot: `近 7 天新增 ${data.value?.newUsers ?? 0} 人`,
    icon: User,
    bg: 'rgba(22, 119, 255, 0.12)',
    color: '#1677ff',
  },
  {
    label: '角色数量',
    value: cards.value.roles ?? 0,
    foot: `菜单 ${cards.value.menus ?? 0} 项`,
    icon: Avatar,
    bg: 'rgba(103, 194, 58, 0.14)',
    color: '#67c23a',
  },
  {
    label: '今日操作',
    value: data.value?.todayLogs ?? 0,
    foot: `累计 ${cards.value.logs ?? 0} 条日志`,
    icon: TrendCharts,
    bg: 'rgba(230, 162, 60, 0.16)',
    color: '#e6a23c',
  },
  {
    label: '异常操作',
    value: data.value?.failLogs ?? 0,
    foot: '失败 / 越权访问次数',
    icon: WarningFilled,
    bg: 'rgba(245, 108, 108, 0.14)',
    color: '#f56c6c',
  },
])

const chart = computed(() => {
  const points = trend.value
  const w = 720
  const h = 220
  const padL = 40
  const padR = 16
  const padT = 18
  const padB = 30
  const innerW = w - padL - padR
  const innerH = h - padT - padB
  const max = Math.max(1, ...points.map((p) => p.count))
  const step = points.length > 1 ? innerW / (points.length - 1) : 0

  const coords = points.map((point, index) => ({
    ...point,
    x: padL + index * step,
    y: padT + innerH - (point.count / max) * innerH,
  }))
  const line = coords
    .map((point, index) => `${index === 0 ? 'M' : 'L'}${point.x.toFixed(1)} ${point.y.toFixed(1)}`)
    .join(' ')
  const baseY = (padT + innerH).toFixed(1)
  const area = coords.length
    ? `${line} L${coords[coords.length - 1].x.toFixed(1)} ${baseY} L${coords[0].x.toFixed(1)} ${baseY} Z`
    : ''
  const ticks = [0, 0.5, 1].map((ratio) => ({
    y: padT + innerH - ratio * innerH,
    value: Math.round(max * ratio),
  }))

  return { w, h, padL, points: coords, line, area, ticks }
})

const moduleMax = computed(() => Math.max(1, ...modules.value.map((item) => item.value)))

function modulePercent(value: number): number {
  return Math.round((value / moduleMax.value) * 100)
}

const uptimeText = computed(() => {
  const seconds = Number(system.value.uptime || 0)
  if (!seconds) return '-'
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  if (days) return `${days} 天 ${hours} 小时`
  if (hours) return `${hours} 小时 ${minutes} 分`
  return `${minutes} 分钟`
})

async function load(): Promise<void> {
  loading.value = true
  try {
    data.value = (await api.get('/dashboard/overview')) as unknown as Overview
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.trend-svg {
  width: 100%;
  height: 220px;
  display: block;
}

.axis-text {
  font-size: 11px;
  fill: #98a1b0;
}

.module-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.module-head {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  margin-bottom: 6px;
  color: #4b5563;
}
</style>
