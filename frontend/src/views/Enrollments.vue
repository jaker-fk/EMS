<template>
  <el-card class="page-card" shadow="never">
    <template #header>
      <div class="card-header">
        <div class="toolbar">
          <el-input
            v-model="keyword"
            placeholder="姓名 / 手机号 / 课程"
            clearable
            style="width: 220px"
            @keyup.enter="search"
            @clear="search"
          />
          <el-select v-model="status" placeholder="全部状态" clearable style="width: 130px" @change="search">
            <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
          <el-button type="primary" plain @click="search">查询</el-button>
          <el-button @click="reset">重置</el-button>
        </div>
        <div class="toolbar">
          <el-button :icon="Download" :loading="exporting" @click="exportExcel">导出 Excel</el-button>
          <el-button
            v-if="can('edu:enrollment:remove')"
            type="danger"
            plain
            :disabled="!selection.length"
            @click="batchDelete"
          >批量删除</el-button>
        </div>
      </div>
    </template>

    <el-alert
      class="tip"
      type="info"
      :closable="false"
      show-icon
      title="这里汇总官网「预约试听 / 报名」提交的线索，状态变更会记入操作日志。"
    />

    <el-table :data="list" v-loading="loading" border stripe @selection-change="onSelectionChange">
      <el-table-column type="selection" width="46" />
      <el-table-column prop="name" label="姓名" width="110" />
      <el-table-column prop="phone" label="手机号" width="140" />
      <el-table-column prop="course_title" label="意向课程" min-width="200" show-overflow-tooltip>
        <template #default="{ row }">{{ row.course_title || '未指定课程' }}</template>
      </el-table-column>
      <el-table-column prop="age" label="年龄/年级" width="100">
        <template #default="{ row }">{{ row.age || '—' }}</template>
      </el-table-column>
      <el-table-column prop="source" label="来源" width="90" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusTag(row.status)" size="small">{{ row.status_text }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="remark" label="备注" min-width="160" show-overflow-tooltip>
        <template #default="{ row }">{{ row.remark || '—' }}</template>
      </el-table-column>
      <el-table-column prop="created_at" label="提交时间" width="170" />
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button v-if="can('edu:enrollment:edit')" size="small" link type="primary" @click="openFollow(row)">
            跟进
          </el-button>
          <el-button v-if="can('edu:enrollment:remove')" size="small" link type="danger" @click="remove(row)">
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pager">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="size"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        background
        @current-change="load"
        @size-change="onSizeChange"
      />
    </div>
  </el-card>

  <el-dialog v-model="dialogVisible" title="跟进报名" width="480px" destroy-on-close>
    <el-descriptions v-if="current" :column="1" border size="small" class="follow-info">
      <el-descriptions-item label="姓名">{{ current.name }}</el-descriptions-item>
      <el-descriptions-item label="手机号">{{ current.phone }}</el-descriptions-item>
      <el-descriptions-item label="意向课程">{{ current.course_title || '未指定' }}</el-descriptions-item>
      <el-descriptions-item label="提交时间">{{ current.created_at }}</el-descriptions-item>
    </el-descriptions>

    <el-form label-width="80px" class="follow-form">
      <el-form-item label="跟进状态">
        <el-select v-model="followForm.status" style="width: 100%">
          <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
      </el-form-item>
      <el-form-item label="跟进备注">
        <el-input
          v-model="followForm.remark"
          type="textarea"
          :rows="3"
          maxlength="200"
          show-word-limit
          placeholder="如：已电话沟通，约定周六到校测评"
        />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="saveFollow">保存跟进</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Download } from '@element-plus/icons-vue'
import api, { download } from '../utils/request'
import { hasPerm } from '../utils/auth'

interface EnrollmentRow {
  id: number
  course_id: number
  course_title: string
  name: string
  phone: string
  age: string
  source: string
  status: number
  status_text: string
  remark: string
  created_at: string
}

const can = hasPerm
const statusOptions = [
  { label: '待跟进', value: 0 },
  { label: '已联系', value: 1 },
  { label: '已成交', value: 2 },
  { label: '已失效', value: 3 },
]

const list = ref<EnrollmentRow[]>([])
const selection = ref<EnrollmentRow[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const keyword = ref('')
const status = ref<number | undefined>(undefined)
const loading = ref(false)
const exporting = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const current = ref<EnrollmentRow | null>(null)
const followForm = reactive({ status: 0, remark: '' })

function statusTag(value: number): 'info' | 'warning' | 'success' | 'danger' {
  if (value === 2) return 'success'
  if (value === 1) return 'warning'
  if (value === 3) return 'danger'
  return 'info'
}

async function load(): Promise<void> {
  loading.value = true
  try {
    const data = (await api.get('/enrollments', {
      params: {
        keyword: keyword.value,
        status: status.value,
        page: page.value,
        size: size.value,
      },
    })) as unknown as { total: number; list: EnrollmentRow[] }
    list.value = data.list
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function search(): void {
  page.value = 1
  load()
}

function reset(): void {
  keyword.value = ''
  status.value = undefined
  search()
}

function onSizeChange(): void {
  page.value = 1
  load()
}

function onSelectionChange(rows: EnrollmentRow[]): void {
  selection.value = rows
}

function openFollow(row: EnrollmentRow): void {
  current.value = row
  followForm.status = row.status
  followForm.remark = row.remark || ''
  dialogVisible.value = true
}

async function saveFollow(): Promise<void> {
  if (!current.value) return
  saving.value = true
  try {
    await api.put(`/enrollments/${current.value.id}`, {
      status: followForm.status,
      remark: followForm.remark,
    })
    ElMessage.success('跟进状态已更新')
    dialogVisible.value = false
    load()
  } finally {
    saving.value = false
  }
}

async function remove(row: EnrollmentRow): Promise<void> {
  try {
    await ElMessageBox.confirm(`确认删除「${row.name}」的报名记录吗？`, '提示', { type: 'warning' })
  } catch {
    return
  }
  await api.delete('/enrollments', { params: { ids: String(row.id) } })
  ElMessage.success('删除成功')
  load()
}

async function batchDelete(): Promise<void> {
  const ids = selection.value.map((item) => item.id)
  if (!ids.length) return
  try {
    await ElMessageBox.confirm(`确认删除选中的 ${ids.length} 条报名记录吗？`, '提示', { type: 'warning' })
  } catch {
    return
  }
  await api.delete('/enrollments', { params: { ids: ids.join(',') } })
  ElMessage.success('删除成功')
  load()
}

async function exportExcel(): Promise<void> {
  exporting.value = true
  try {
    await download(
      '/enrollments/export',
      { keyword: keyword.value, status: status.value },
      'enrollments.xlsx',
    )
    ElMessage.success('导出完成')
  } finally {
    exporting.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.tip {
  margin-bottom: 12px;
}

.follow-info {
  margin-bottom: 16px;
}

.follow-form {
  margin-top: 4px;
}
</style>
