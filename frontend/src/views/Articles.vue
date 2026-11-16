<template>
  <el-card class="page-card" shadow="never">
    <template #header>
      <div class="card-header">
        <div class="toolbar">
          <el-input
            v-model="keyword"
            placeholder="标题关键字"
            clearable
            style="width: 200px"
            @keyup.enter="search"
            @clear="search"
          />
          <el-button type="primary" plain @click="search">查询</el-button>
        </div>
        <el-button v-if="can('edu:article:add')" type="primary" :icon="Plus" @click="openCreate">
          发布资讯
        </el-button>
      </div>
    </template>

    <el-table :data="list" v-loading="loading" border stripe>
      <el-table-column label="标题" min-width="280">
        <template #default="{ row }">
          <div class="title-cell">
            <strong>{{ row.title }}</strong>
            <small>{{ row.summary || '—' }}</small>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="category" label="栏目" width="120">
        <template #default="{ row }">
          <el-tag size="small" type="info">{{ row.category }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.status ? 'success' : 'info'" size="small">
            {{ row.status ? '已发布' : '已隐藏' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="published_at" label="发布时间" width="170" />
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button v-if="can('edu:article:edit')" size="small" link type="primary" @click="openEdit(row)">
            编辑
          </el-button>
          <el-button v-if="can('edu:article:remove')" size="small" link type="danger" @click="remove(row)">
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pager">
      <el-pagination
        v-model:current-page="page"
        :page-size="size"
        :total="total"
        layout="total, prev, pager, next"
        background
        @current-change="load"
      />
    </div>
  </el-card>

  <el-dialog v-model="dialogVisible" :title="form.id ? '编辑资讯' : '发布资讯'" width="720px" top="6vh" destroy-on-close>
    <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
      <el-form-item label="标题" prop="title">
        <el-input v-model.trim="form.title" placeholder="如：2026 春季班课表发布" />
      </el-form-item>
      <el-form-item label="栏目">
        <el-select v-model="form.category" allow-create filterable placeholder="选择或输入栏目" style="width: 100%">
          <el-option v-for="item in categories" :key="item" :label="item" :value="item" />
        </el-select>
      </el-form-item>
      <el-form-item label="摘要">
        <el-input v-model.trim="form.summary" type="textarea" :rows="2" maxlength="200" show-word-limit />
      </el-form-item>
      <el-form-item label="正文" prop="content">
        <el-input
          v-model="form.content"
          type="textarea"
          :rows="10"
          placeholder="支持换行，前台按段落展示"
        />
      </el-form-item>
      <el-form-item label="状态">
        <el-switch v-model="form.status" :active-value="1" :inactive-value="0" active-text="发布" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="save">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import api from '../utils/request'
import { hasPerm } from '../utils/auth'

interface ArticleRow {
  id: number
  title: string
  category: string
  summary: string
  content: string
  status: number
  published_at: string
}

const can = hasPerm
const categories = ['机构动态', '荣誉成果', '家庭教育', '课程安排']

const list = ref<ArticleRow[]>([])
const total = ref(0)
const page = ref(1)
const size = 10
const keyword = ref('')
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const formRef = ref()

const emptyForm = () => ({ id: 0, title: '', category: '机构动态', summary: '', content: '', status: 1 })
const form = reactive<ReturnType<typeof emptyForm>>(emptyForm())

const rules = {
  title: [
    { required: true, message: '请输入标题', trigger: 'blur' },
    { max: 128, message: '标题过长', trigger: 'blur' },
  ],
  content: [{ required: true, message: '请输入正文内容', trigger: 'blur' }],
}

async function load(): Promise<void> {
  loading.value = true
  try {
    const data = (await api.get('/articles', {
      params: { keyword: keyword.value, page: page.value, size },
    })) as unknown as { total: number; list: ArticleRow[] }
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

function openCreate(): void {
  Object.assign(form, emptyForm())
  dialogVisible.value = true
}

function openEdit(row: ArticleRow): void {
  Object.assign(form, { ...emptyForm(), ...row })
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
    const payload = {
      title: form.title,
      category: form.category,
      summary: form.summary,
      content: form.content,
      status: form.status,
    }
    if (form.id) await api.put(`/articles/${form.id}`, payload)
    else await api.post('/articles', payload)
    ElMessage.success('保存成功')
    dialogVisible.value = false
    load()
  } finally {
    saving.value = false
  }
}

async function remove(row: ArticleRow): Promise<void> {
  try {
    await ElMessageBox.confirm(`确认删除资讯「${row.title}」吗？`, '提示', { type: 'warning' })
  } catch {
    return
  }
  await api.delete(`/articles/${row.id}`)
  ElMessage.success('删除成功')
  load()
}

onMounted(load)
</script>

<style scoped>
.title-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.title-cell strong {
  font-size: 14px;
  color: #0f1c2e;
}

.title-cell small {
  color: #8a919f;
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
