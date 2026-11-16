<template>
  <el-card class="page-card" shadow="never">
    <template #header>
      <div class="card-header">
        <div class="toolbar">
          <el-input
            v-model="keyword"
            placeholder="姓名 / 头衔"
            clearable
            style="width: 200px"
            @keyup.enter="search"
            @clear="search"
          />
          <el-button type="primary" plain @click="search">查询</el-button>
        </div>
        <el-button v-if="can('edu:teacher:add')" type="primary" :icon="Plus" @click="openCreate">
          新增教师
        </el-button>
      </div>
    </template>

    <el-table :data="list" v-loading="loading" border stripe>
      <el-table-column label="教师" min-width="200">
        <template #default="{ row }">
          <div class="teacher-cell">
            <img
              v-if="imageUrl(row.avatar)"
              class="avatar avatar--img"
              :src="imageUrl(row.avatar)"
              :alt="row.name"
              loading="lazy"
            />
            <span v-else class="avatar" :style="coverStyle(row.name)">{{ initials(row.name, 1) }}</span>
            <div>
              <strong>{{ row.name }}</strong>
              <small>{{ row.title || '—' }}</small>
            </div>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="years" label="教龄" width="80">
        <template #default="{ row }">{{ row.years ? `${row.years} 年` : '—' }}</template>
      </el-table-column>
      <el-table-column prop="tags" label="标签" min-width="160">
        <template #default="{ row }">
          <span v-for="tag in splitTags(row.tags)" :key="tag" class="tag-pill">{{ tag }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="course_count" label="带课数" width="90" />
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.status ? 'success' : 'info'" size="small">
            {{ row.status ? '正常' : '停用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button v-if="can('edu:teacher:edit')" size="small" link type="primary" @click="openEdit(row)">
            编辑
          </el-button>
          <el-button v-if="can('edu:teacher:remove')" size="small" link type="danger" @click="remove(row)">
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

  <el-dialog v-model="dialogVisible" :title="form.id ? '编辑教师' : '新增教师'" width="560px" destroy-on-close>
    <el-form ref="formRef" :model="form" :rules="rules" label-width="86px">
      <el-form-item label="姓名" prop="name">
        <el-input v-model.trim="form.name" placeholder="如：王思远" />
      </el-form-item>
      <el-form-item label="头衔">
        <el-input v-model.trim="form.title" placeholder="如：少儿编程教研组长" />
      </el-form-item>
      <el-form-item label="教龄 (年)">
        <el-input-number v-model="form.years" :min="0" :max="60" controls-position="right" />
      </el-form-item>
      <el-form-item label="标签">
        <el-input v-model.trim="form.tags" placeholder="逗号分隔，如：信息学奥赛,Python" />
      </el-form-item>
      <el-form-item label="头像地址">
        <div class="avatar-field">
          <div class="avatar-row">
            <el-input v-model.trim="form.avatar" placeholder="选填，支持 https 链接或 /uploads/xxx.png" />
            <span class="avatar-thumb">
              <img v-if="imageUrl(form.avatar)" :src="imageUrl(form.avatar)" alt="头像预览" />
              <em v-else>{{ initials(form.name || '教师', 1) }}</em>
            </span>
          </div>
          <small>留空则用「姓名首字 + 渐变」生成；填好保存后列表和前台立即显示这张图</small>
        </div>
      </el-form-item>
      <el-form-item label="教师简介">
        <el-input v-model="form.intro" type="textarea" :rows="4" maxlength="500" show-word-limit />
      </el-form-item>
      <el-form-item label="排序">
        <el-input-number v-model="form.sort" :min="0" controls-position="right" />
      </el-form-item>
      <el-form-item label="状态">
        <el-switch v-model="form.status" :active-value="1" :inactive-value="0" active-text="正常" />
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
import { coverStyle, imageUrl, initials } from '../utils/site'

interface TeacherRow {
  id: number
  name: string
  title: string
  avatar: string
  intro: string
  tags: string
  years: number
  sort: number
  status: number
  course_count: number
}

const can = hasPerm

const list = ref<TeacherRow[]>([])
const total = ref(0)
const page = ref(1)
const size = 10
const keyword = ref('')
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const formRef = ref()

const emptyForm = () => ({
  id: 0,
  name: '',
  title: '',
  avatar: '',
  intro: '',
  tags: '',
  years: 0,
  sort: 0,
  status: 1,
})
const form = reactive<ReturnType<typeof emptyForm>>(emptyForm())

const rules = {
  name: [
    { required: true, message: '请输入姓名', trigger: 'blur' },
    { max: 64, message: '姓名过长', trigger: 'blur' },
  ],
}

function splitTags(value?: string): string[] {
  return (value || '').split(',').map((item) => item.trim()).filter(Boolean)
}

async function load(): Promise<void> {
  loading.value = true
  try {
    const data = (await api.get('/teachers', {
      params: { keyword: keyword.value, page: page.value, size },
    })) as unknown as { total: number; list: TeacherRow[] }
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

function openEdit(row: TeacherRow): void {
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
      name: form.name,
      title: form.title,
      avatar: form.avatar,
      intro: form.intro,
      tags: form.tags,
      years: form.years,
      sort: form.sort,
      status: form.status,
    }
    if (form.id) await api.put(`/teachers/${form.id}`, payload)
    else await api.post('/teachers', payload)
    ElMessage.success('保存成功')
    dialogVisible.value = false
    load()
  } finally {
    saving.value = false
  }
}

async function remove(row: TeacherRow): Promise<void> {
  try {
    await ElMessageBox.confirm(`确认删除教师「${row.name}」吗？`, '提示', { type: 'warning' })
  } catch {
    return
  }
  await api.delete(`/teachers/${row.id}`)
  ElMessage.success('删除成功')
  load()
}

onMounted(load)
</script>

<style scoped>
.teacher-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.avatar {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-weight: 600;
  flex: none;
  overflow: hidden;
}

.avatar--img {
  object-fit: cover;
  background: #eef2f7;
}

.avatar-field {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.avatar-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.avatar-thumb {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  overflow: hidden;
  flex: none;
  background: #f2f5fa;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #8a919f;
  font-size: 13px;
  font-style: normal;
}

.avatar-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-field small {
  color: #8a919f;
  font-size: 12px;
  line-height: 1.5;
}

.teacher-cell strong {
  display: block;
  font-size: 14px;
  color: #0f1c2e;
}

.teacher-cell small {
  color: #8a919f;
  font-size: 12px;
}
</style>
