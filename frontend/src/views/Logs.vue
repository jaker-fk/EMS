<template>
  <el-card>
    <template #header><span>操作日志（只读）</span></template>

    <el-form inline>
      <el-form-item label="操作人">
        <el-input v-model="q.username" placeholder="用户名" clearable style="width: 140px" />
      </el-form-item>
      <el-form-item label="模块">
        <el-select v-model="q.module" placeholder="全部" clearable style="width: 140px">
          <el-option v-for="m in modules" :key="m" :label="m" :value="m" />
        </el-select>
      </el-form-item>
      <el-form-item label="类型">
        <el-select v-model="q.action" placeholder="全部" clearable style="width: 120px">
          <el-option v-for="a in actions" :key="a" :label="a" :value="a" />
        </el-select>
      </el-form-item>
      <el-form-item label="时间">
        <el-date-picker
          v-model="q.range"
          type="datetimerange"
          range-separator="至"
          start-placeholder="开始"
          end-placeholder="结束"
          value-format="YYYY-MM-DD HH:mm:ss"
          style="width: 360px"
        />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="search">查询</el-button>
        <el-button @click="reset">重置</el-button>
      </el-form-item>
    </el-form>

    <el-table :data="list" v-loading="loading" border stripe>
      <el-table-column prop="username" label="操作人" width="120" />
      <el-table-column prop="module" label="模块" width="110" />
      <el-table-column prop="action" label="类型" width="90" />
      <el-table-column prop="method" label="方法" width="80" />
      <el-table-column prop="path" label="请求地址" min-width="180" />
      <el-table-column prop="params" label="请求参数" min-width="140" show-overflow-tooltip />
      <el-table-column prop="ip" label="IP" width="130" />
      <el-table-column label="结果" width="80">
        <template #default="{ row }">
          <el-tag :type="row.result === '成功' ? 'success' : 'danger'" size="small">{{ row.result }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="时间" width="170" />
    </el-table>

    <el-pagination
      v-model:current-page="page"
      :total="total"
      :page-size="size"
      layout="total,prev,pager,next"
      style="margin-top: 12px; justify-content: flex-end"
      @current-change="load"
    />
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import api from '../utils/request'

const modules = ['用户管理', '角色管理', '菜单管理', '数据字典', '个人中心', '业务数据', '文件管理', '登录']
const actions = ['登录', '新增', '修改', '删除', '重置密码', '修改密码', '上传', '导出', '新增字典项', '修改字典项', '删除字典项']

const list = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const loading = ref(false)
const q = reactive<any>({ username: '', module: '', action: '', range: null })

async function load(): Promise<void> {
  loading.value = true
  try {
    const [start, end] = q.range || ['', '']
    const d: any = await api.get('/logs', {
      params: {
        username: q.username,
        module: q.module,
        action: q.action,
        start,
        end,
        page: page.value,
        size: size.value,
      },
    })
    list.value = d.list
    total.value = d.total
  } finally {
    loading.value = false
  }
}

function search(): void {
  page.value = 1
  load()
}

function reset(): void {
  Object.assign(q, { username: '', module: '', action: '', range: null })
  search()
}

onMounted(load)
</script>
