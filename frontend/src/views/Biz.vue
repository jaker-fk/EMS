<template>
  <el-card class="page-card" shadow="never">
    <template #header>
      <div class="card-header">
        <div class="toolbar">
          <el-input
            v-model="keyword"
            placeholder="按名称搜索"
            clearable
            style="width: 200px"
            @keyup.enter="search"
            @clear="search"
          />
          <el-button type="primary" plain @click="search">查询</el-button>
        </div>
        <div class="toolbar">
          <el-button :icon="Download" :loading="exporting" @click="exportExcel">导出 Excel</el-button>
          <el-button v-if="canEdit" type="primary" :icon="Plus" @click="openCreate">新增</el-button>
          <el-button v-if="canEdit" type="danger" plain :disabled="!selection.length" @click="batchDelete">
            批量删除
          </el-button>
        </div>
      </div>
    </template>

    <el-alert
      class="demo-tip"
      type="info"
      :closable="false"
      show-icon
      title="这是用于演示 CRUD 与 Excel 导出的示例模块，可按需替换为真实业务表。"
    />

    <el-table :data="list" v-loading="loading" border stripe @selection-change="onSelectionChange">
      <el-table-column type="selection" width="46" />
      <el-table-column prop="name" label="名称" min-width="160" show-overflow-tooltip />
      <el-table-column prop="category" label="分类" width="130" />
      <el-table-column label="价格" width="110">
        <template #default="{ row }">￥{{ Number(row.price || 0).toFixed(2) }}</template>
      </el-table-column>
      <el-table-column prop="remark" label="备注" min-width="180" show-overflow-tooltip />
      <el-table-column prop="created_at" label="创建时间" width="170" />
      <el-table-column v-if="canEdit" label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button size="small" link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button size="small" link type="danger" @click="remove(row)">删除</el-button>
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

  <el-dialog v-model="dialogVisible" :title="form.id ? '编辑业务数据' : '新增业务数据'" width="480px">
    <el-form ref="formRef" :model="form" :rules="rules" label-width="70px">
      <el-form-item label="名称" prop="name">
        <el-input v-model.trim="form.name" placeholder="必填" />
      </el-form-item>
      <el-form-item label="分类">
        <el-input v-model.trim="form.category" placeholder="选填" />
      </el-form-item>
      <el-form-item label="价格">
        <el-input-number v-model="form.price" :min="0" :step="1" controls-position="right" />
      </el-form-item>
      <el-form-item label="备注">
        <el-input v-model="form.remark" type="textarea" :rows="2" maxlength="255" show-word-limit />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="save">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Download, Plus } from '@element-plus/icons-vue'
import api, { download } from '../utils/request'
import { hasPerm } from '../utils/auth'

interface BizRow {
  id: number
  name: string
  category: string
  price: number
  remark: string
  created_at: string
}

const canEdit = computed(() => hasPerm('biz:list'))

const list = ref<BizRow[]>([])
const selection = ref<BizRow[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const keyword = ref('')
const loading = ref(false)
const exporting = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const formRef = ref()
const form = reactive({ id: 0, name: '', category: '', price: 0, remark: '' })

const rules = {
  name: [
    { required: true, message: '请输入名称', trigger: 'blur' },
    { max: 128, message: '名称过长', trigger: 'blur' },
  ],
}

async function load(): Promise<void> {
  loading.value = true
  try {
    const data = (await api.get('/biz', {
      params: { keyword: keyword.value, page: page.value, size: size.value },
    })) as unknown as { total: number; list: BizRow[] }
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

function onSizeChange(): void {
  page.value = 1
  load()
}

function onSelectionChange(rows: BizRow[]): void {
  selection.value = rows
}

function openCreate(): void {
  Object.assign(form, { id: 0, name: '', category: '', price: 0, remark: '' })
  dialogVisible.value = true
}

function openEdit(row: BizRow): void {
  Object.assign(form, { ...row })
  dialogVisible.value = true
}

async function save(): Promise<void> {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }
  saving.value = true
  try {
    const payload = { name: form.name, category: form.category, price: form.price, remark: form.remark }
    if (form.id) await api.put(`/biz/${form.id}`, payload)
    else await api.post('/biz', payload)
    ElMessage.success('保存成功')
    dialogVisible.value = false
    load()
  } finally {
    saving.value = false
  }
}

async function remove(row: BizRow): Promise<void> {
  try {
    await ElMessageBox.confirm(`确认删除「${row.name}」吗？`, '提示', { type: 'warning' })
  } catch {
    return
  }
  await api.delete('/biz', { params: { ids: String(row.id) } })
  ElMessage.success('删除成功')
  load()
}

async function batchDelete(): Promise<void> {
  const ids = selection.value.map((item) => item.id)
  if (!ids.length) return
  try {
    await ElMessageBox.confirm(`确认删除选中的 ${ids.length} 条记录吗？`, '提示', { type: 'warning' })
  } catch {
    return
  }
  await api.delete('/biz', { params: { ids: ids.join(',') } })
  ElMessage.success('删除成功')
  load()
}

async function exportExcel(): Promise<void> {
  exporting.value = true
  try {
    await download('/biz/export', { keyword: keyword.value }, 'biz.xlsx')
    ElMessage.success('导出完成')
  } finally {
    exporting.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.demo-tip {
  margin-bottom: 12px;
}
</style>
