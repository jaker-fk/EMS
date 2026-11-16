<template>
  <el-card class="page-card" shadow="never">
    <template #header>
      <div class="card-header">
        <div class="toolbar">
          <el-input
            v-model="keyword"
            placeholder="课程名称 / 标签"
            clearable
            style="width: 200px"
            @keyup.enter="search"
            @clear="search"
          />
          <el-select v-model="categoryId" placeholder="全部分类" clearable style="width: 140px" @change="search">
            <el-option v-for="cat in categories" :key="cat.id" :label="cat.name" :value="cat.id" />
          </el-select>
          <el-select v-model="status" placeholder="全部状态" clearable style="width: 130px" @change="search">
            <el-option label="已上架" :value="1" />
            <el-option label="未上架" :value="0" />
          </el-select>
          <el-button type="primary" plain @click="search">查询</el-button>
          <el-button @click="reset">重置</el-button>
        </div>
        <el-button v-if="can('edu:course:add')" type="primary" :icon="Plus" @click="openCreate">
          新增课程
        </el-button>
      </div>
    </template>

    <el-alert
      class="tip"
      type="info"
      :closable="false"
      show-icon
      title="课程「上架」后才会出现在官网课程中心；下架后前台立即不可见，已产生的报名记录不受影响。"
    />

    <el-table :data="list" v-loading="loading" border stripe>
      <el-table-column label="课程" min-width="260">
        <template #default="{ row }">
          <div class="course-cell">
            <span class="thumb" :style="coverStyle(row.title)">{{ initials(row.title) }}</span>
            <div class="course-info">
              <strong>{{ row.title }}</strong>
              <small>{{ row.subtitle || row.summary || '—' }}</small>
            </div>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="category_name" label="分类" width="110">
        <template #default="{ row }">{{ row.category_name || '未分类' }}</template>
      </el-table-column>
      <el-table-column prop="teacher_name" label="讲师" width="100">
        <template #default="{ row }">{{ row.teacher_name || '未指定' }}</template>
      </el-table-column>
      <el-table-column label="价格" width="120">
        <template #default="{ row }">
          <span class="price">¥{{ row.price }}</span>
          <small v-if="row.original_price > row.price" class="old-price">¥{{ row.original_price }}</small>
        </template>
      </el-table-column>
      <el-table-column prop="lessons" label="课时" width="70" />
      <el-table-column label="上架" width="90">
        <template #default="{ row }">
          <el-switch
            :model-value="row.status === 1"
            :disabled="!can('edu:course:publish')"
            @change="(value: boolean) => toggleStatus(row, value)"
          />
        </template>
      </el-table-column>
      <el-table-column label="推荐" width="70">
        <template #default="{ row }">
          <el-tag v-if="row.is_recommend" type="warning" size="small">推荐</el-tag>
          <span v-else class="muted">—</span>
        </template>
      </el-table-column>
      <el-table-column prop="view_count" label="浏览" width="70" />
      <el-table-column label="操作" width="130" fixed="right">
        <template #default="{ row }">
          <el-button v-if="can('edu:course:edit')" size="small" link type="primary" @click="openEdit(row)">
            编辑
          </el-button>
          <el-button v-if="can('edu:course:remove')" size="small" link type="danger" @click="remove(row)">
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

  <el-dialog
    v-model="dialogVisible"
    :title="form.id ? '编辑课程' : '新增课程'"
    width="760px"
    top="6vh"
    destroy-on-close
  >
    <el-form ref="formRef" :model="form" :rules="rules" label-width="96px">
      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item label="课程名称" prop="title">
            <el-input v-model.trim="form.title" placeholder="如：少儿编程 · Scratch 启蒙班" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="一句话卖点">
            <el-input v-model.trim="form.subtitle" placeholder="展示在详情页标题下" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="课程分类">
            <el-select v-model="form.category_id" placeholder="请选择" clearable style="width: 100%">
              <el-option v-for="cat in categories" :key="cat.id" :label="cat.name" :value="cat.id" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="授课教师">
            <el-select v-model="form.teacher_id" placeholder="请选择" clearable style="width: 100%">
              <el-option v-for="t in teachers" :key="t.id" :label="`${t.name}（${t.title}）`" :value="t.id" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="现价 (元)">
            <el-input-number v-model="form.price" :min="0" :step="100" controls-position="right" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="原价 (元)">
            <el-input-number v-model="form.original_price" :min="0" :step="100" controls-position="right" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="课时数">
            <el-input-number v-model="form.lessons" :min="0" controls-position="right" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="上课周期">
            <el-input v-model.trim="form.duration" placeholder="如：12 周 / 每周 2 次" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="适合阶段">
            <el-select v-model="form.level" placeholder="请选择" clearable allow-create filterable style="width: 100%">
              <el-option v-for="item in levelOptions" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="24">
          <el-form-item label="适合人群">
            <el-input v-model.trim="form.suitable" placeholder="如：6-9 岁零基础" />
          </el-form-item>
        </el-col>
        <el-col :span="24">
          <el-form-item label="标签">
            <el-input v-model.trim="form.tags" placeholder="逗号分隔，如：小班课,零基础,作品结课" />
          </el-form-item>
        </el-col>
        <el-col :span="24">
          <el-form-item label="列表摘要">
            <el-input v-model.trim="form.summary" type="textarea" :rows="2" maxlength="200" show-word-limit />
          </el-form-item>
        </el-col>
        <el-col :span="24">
          <el-form-item label="课程详情">
            <el-input
              v-model="form.description"
              type="textarea"
              :rows="7"
              placeholder="支持换行，建议写：课程亮点 / 适合人群 / 课程大纲"
            />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="上架状态">
            <el-switch v-model="form.status" :active-value="1" :inactive-value="0" active-text="上架" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="首页推荐">
            <el-switch v-model="form.is_recommend" :active-value="1" :inactive-value="0" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="排序">
            <el-input-number v-model="form.sort" :min="0" controls-position="right" style="width: 100%" />
          </el-form-item>
        </el-col>
      </el-row>
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
import { coverStyle, initials } from '../utils/site'

interface CourseRow {
  id: number
  title: string
  subtitle: string
  summary: string
  description: string
  category_id: number
  category_name: string
  teacher_id: number
  teacher_name: string
  price: number
  original_price: number
  lessons: number
  duration: string
  level: string
  suitable: string
  tags: string
  status: number
  is_recommend: number
  sort: number
  view_count: number
}

const can = hasPerm
const levelOptions = ['启蒙', '入门', '进阶', '竞赛', '冲刺', '同步']

const list = ref<CourseRow[]>([])
const categories = ref<{ id: number; name: string }[]>([])
const teachers = ref<{ id: number; name: string; title: string }[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const keyword = ref('')
const categoryId = ref<number | undefined>(undefined)
const status = ref<number | undefined>(undefined)
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const formRef = ref()

const emptyForm = () => ({
  id: 0,
  title: '',
  subtitle: '',
  summary: '',
  description: '',
  category_id: 0,
  teacher_id: 0,
  price: 0,
  original_price: 0,
  lessons: 0,
  duration: '',
  level: '',
  suitable: '',
  tags: '',
  status: 0,
  is_recommend: 0,
  sort: 0,
})

const form = reactive<ReturnType<typeof emptyForm>>(emptyForm())

const rules = {
  title: [
    { required: true, message: '请输入课程名称', trigger: 'blur' },
    { max: 128, message: '名称过长', trigger: 'blur' },
  ],
}

async function loadOptions(): Promise<void> {
  categories.value = (await api.get('/course-categories')) as unknown as { id: number; name: string }[]
  const data = (await api.get('/teachers', { params: { page: 1, size: 100 } })) as unknown as {
    list: { id: number; name: string; title: string }[]
  }
  teachers.value = data.list
}

async function load(): Promise<void> {
  loading.value = true
  try {
    const data = (await api.get('/courses', {
      params: {
        keyword: keyword.value,
        category_id: categoryId.value || 0,
        status: status.value,
        page: page.value,
        size: size.value,
      },
    })) as unknown as { total: number; list: CourseRow[] }
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
  categoryId.value = undefined
  status.value = undefined
  search()
}

function onSizeChange(): void {
  page.value = 1
  load()
}

function openCreate(): void {
  Object.assign(form, emptyForm())
  dialogVisible.value = true
}

function openEdit(row: CourseRow): void {
  Object.assign(form, {
    ...emptyForm(),
    ...row,
    description: row.description || '',
  })
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
    const payload = { ...form }
    delete (payload as Record<string, unknown>).id
    delete (payload as Record<string, unknown>).category_name
    delete (payload as Record<string, unknown>).teacher_name
    delete (payload as Record<string, unknown>).view_count
    delete (payload as Record<string, unknown>).created_at
    delete (payload as Record<string, unknown>).updated_at
    if (form.id) await api.put(`/courses/${form.id}`, payload)
    else await api.post('/courses', payload)
    ElMessage.success('保存成功')
    dialogVisible.value = false
    await load()
  } finally {
    saving.value = false
  }
}

async function toggleStatus(row: CourseRow, value: boolean): Promise<void> {
  const next = value ? 1 : 0
  try {
    await api.put(`/courses/${row.id}/status`, { status: next })
    row.status = next
    ElMessage.success(next ? '课程已上架，官网可见' : '课程已下架')
  } catch {
    /* 失败时保持原状态 */
  }
}

async function remove(row: CourseRow): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `确认删除课程「${row.title}」吗？删除后前台不可见，历史报名记录保留。`,
      '提示',
      { type: 'warning' },
    )
  } catch {
    return
  }
  await api.delete('/courses', { params: { ids: String(row.id) } })
  ElMessage.success('删除成功')
  load()
}

onMounted(async () => {
  await loadOptions()
  await load()
})
</script>

<style scoped>
.tip {
  margin-bottom: 12px;
}

.course-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.thumb {
  width: 46px;
  height: 46px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  flex: none;
}

.course-info {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}

.course-info strong {
  font-size: 14px;
  color: #0f1c2e;
}

.course-info small {
  color: #8a919f;
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.price {
  color: #f5222d;
  font-weight: 600;
}

.old-price {
  margin-left: 6px;
  color: #a8b0bd;
  text-decoration: line-through;
}
</style>
