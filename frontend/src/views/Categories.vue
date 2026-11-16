<template>
  <el-card class="page-card" shadow="never">
    <template #header>
      <div class="card-header">
        <span class="card-title">课程分类</span>
        <el-button v-if="can('edu:category:add')" type="primary" :icon="Plus" @click="openCreate">
          新增分类
        </el-button>
      </div>
    </template>

    <el-table :data="list" v-loading="loading" border stripe>
      <el-table-column label="分类" min-width="200">
        <template #default="{ row }">
          <div class="cat-cell">
            <span class="cat-icon">
              <el-icon :size="17"><component :is="iconOf(row.icon)" /></el-icon>
            </span>
            <div>
              <strong>{{ row.name }}</strong>
              <small>{{ row.desc || '—' }}</small>
            </div>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="course_count" label="课程数" width="90" />
      <el-table-column prop="sort" label="排序" width="80" />
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.status ? 'success' : 'info'" size="small">
            {{ row.status ? '启用' : '停用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button v-if="can('edu:category:edit')" size="small" link type="primary" @click="openEdit(row)">
            编辑
          </el-button>
          <el-button v-if="can('edu:category:remove')" size="small" link type="danger" @click="remove(row)">
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-alert
      class="tip"
      type="info"
      :closable="false"
      show-icon
      title="停用或删除分类不会影响已上架课程，但前台筛选入口将不再显示该分类。"
    />
  </el-card>

  <el-dialog v-model="dialogVisible" :title="form.id ? '编辑分类' : '新增分类'" width="486px" destroy-on-close>
    <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
      <el-form-item label="分类名称" prop="name">
        <el-input v-model.trim="form.name" placeholder="如：少儿编程" />
      </el-form-item>
      <el-form-item label="分类说明">
        <el-input v-model.trim="form.desc" placeholder="展示在前台分类卡片上" />
      </el-form-item>
      <el-form-item label="图标">
        <el-select v-model="form.icon" placeholder="选择图标" clearable style="width: 100%">
          <el-option v-for="name in iconNames" :key="name" :label="name" :value="name">
            <span class="icon-option">
              <el-icon><component :is="iconMap[name]" /></el-icon>
              {{ name }}
            </span>
          </el-option>
        </el-select>
      </el-form-item>
      <el-form-item label="排序">
        <el-input-number v-model="form.sort" :min="0" controls-position="right" />
      </el-form-item>
      <el-form-item label="状态">
        <el-switch v-model="form.status" :active-value="1" :inactive-value="0" active-text="启用" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="save">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, type Component } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Plus,
  Monitor,
  Reading,
  ChatDotRound,
  Brush,
  Files,
  Notebook,
  Collection,
  Trophy,
  Microphone,
  EditPen,
} from '@element-plus/icons-vue'
import api from '../utils/request'
import { hasPerm } from '../utils/auth'

interface CategoryRow {
  id: number
  name: string
  desc: string
  icon: string
  sort: number
  status: number
  course_count: number
}

const can = hasPerm

const iconMap: Record<string, Component> = {
  Monitor,
  Reading,
  ChatDotRound,
  Brush,
  Files,
  Notebook,
  Collection,
  Trophy,
  Microphone,
  EditPen,
}
const iconNames = Object.keys(iconMap)

function iconOf(name?: string): Component {
  return (name && iconMap[name]) || Collection
}

const list = ref<CategoryRow[]>([])
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const formRef = ref()
const form = reactive({ id: 0, name: '', desc: '', icon: 'Collection', sort: 0, status: 1 })

const rules = {
  name: [
    { required: true, message: '请输入分类名称', trigger: 'blur' },
    { max: 64, message: '名称过长', trigger: 'blur' },
  ],
}

async function load(): Promise<void> {
  loading.value = true
  try {
    list.value = (await api.get('/course-categories')) as unknown as CategoryRow[]
  } finally {
    loading.value = false
  }
}

function openCreate(): void {
  Object.assign(form, { id: 0, name: '', desc: '', icon: 'Collection', sort: 0, status: 1 })
  dialogVisible.value = true
}

function openEdit(row: CategoryRow): void {
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
    const payload = { name: form.name, desc: form.desc, icon: form.icon, sort: form.sort, status: form.status }
    if (form.id) await api.put(`/course-categories/${form.id}`, payload)
    else await api.post('/course-categories', payload)
    ElMessage.success('保存成功')
    dialogVisible.value = false
    load()
  } finally {
    saving.value = false
  }
}

async function remove(row: CategoryRow): Promise<void> {
  try {
    await ElMessageBox.confirm(`确认删除分类「${row.name}」吗？`, '提示', { type: 'warning' })
  } catch {
    return
  }
  await api.delete(`/course-categories/${row.id}`)
  ElMessage.success('删除成功')
  load()
}

onMounted(load)
</script>

<style scoped>
.cat-cell {
  display: flex;
  align-items: center;
  gap: 12px;
}

.cat-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #eef4ff;
  color: #1677ff;
  flex: none;
}

.cat-cell strong {
  display: block;
  font-size: 14px;
  color: #0f1c2e;
}

.cat-cell small {
  color: #8a919f;
  font-size: 12px;
}

.icon-option {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.tip {
  margin-top: 12px;
}
</style>
