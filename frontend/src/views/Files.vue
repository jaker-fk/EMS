<template>
  <el-card header="文件管理">
    <el-upload
      action="/api/upload"
      name="f"
      :headers="headers"
      :on-success="onSuccess"
      :on-error="onError"
      :show-file-list="false"
    >
      <el-button type="primary">上传文件</el-button>
    </el-upload>
    <el-table :data="list" style="margin-top: 12px" border>
      <el-table-column prop="filename" label="文件名" />
      <el-table-column prop="url" label="访问URL" />
      <el-table-column prop="size" label="大小(字节)" width="120" />
      <el-table-column prop="uploader" label="上传人" width="120" />
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
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../utils/request'

const list = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const headers = { Authorization: 'Bearer ' + localStorage.getItem('token') }

async function load(): Promise<void> {
  const d: any = await api.get('/files', { params: { page: page.value, size: size.value } })
  list.value = d.list
  total.value = d.total
}

function onSuccess(res: any): void {
  if (res?.code === 200) ElMessage.success('上传成功')
  else ElMessage.error(res?.msg || '上传失败')
  load()
}

function onError(): void {
  ElMessage.error('上传失败')
}

onMounted(load)
</script>
