<template>
  <el-row :gutter="12">
    <el-col :span="9">
      <el-card>
        <template #header>
          <div class="toolbar">
            <span>字典类型</span>
            <el-button v-if="can('system:dict:add')" type="primary" size="small" @click="showType()">新增</el-button>
          </div>
        </template>
        <div class="filter">
          <el-input v-model="typeKw" placeholder="类型名称 / 编码" clearable size="small" @keyup.enter="loadTypes" />
          <el-button size="small" @click="loadTypes">搜索</el-button>
        </div>
        <el-table
          :data="types"
          size="small"
          highlight-current-row
          :current-row-key="currentType"
          row-key="id"
          @current-change="onSelectType"
        >
          <el-table-column prop="name" label="名称" />
          <el-table-column prop="dict_type" label="编码" width="110" />
          <el-table-column prop="item_count" label="项" width="50" />
          <el-table-column label="操作" width="130">
            <template #default="{ row }">
              <el-button v-if="can('system:dict:edit')" link type="primary" @click.stop="showType(row)">编辑</el-button>
              <el-button v-if="can('system:dict:remove')" link type="danger" @click.stop="delType(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-pagination
          v-model:current-page="typePage"
          :total="typeTotal"
          :page-size="10"
          layout="prev,pager,next"
          small
          style="margin-top: 8px; justify-content: flex-end"
          @current-change="loadTypes"
        />
      </el-card>
    </el-col>

    <el-col :span="15">
      <el-card>
        <template #header>
          <div class="toolbar">
            <span>字典项{{ currentType ? `（${currentType}）` : '' }}</span>
            <el-button
              v-if="can('system:dict:add')"
              type="primary"
              size="small"
              :disabled="!currentType"
              @click="showItem()"
            >新增字典项</el-button>
          </div>
        </template>
        <el-empty v-if="!currentType" description="请选择左侧字典类型" />
        <template v-else>
          <el-table :data="items" size="small" border>
            <el-table-column prop="label" label="标签" width="120" />
            <el-table-column prop="value" label="值" width="120" />
            <el-table-column prop="sort" label="排序" width="70" />
            <el-table-column label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="row.status ? 'success' : 'info'" size="small">{{ row.status ? '启用' : '禁用' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="remark" label="备注" min-width="120" />
            <el-table-column label="操作" width="130">
              <template #default="{ row }">
                <el-button v-if="can('system:dict:edit')" link type="primary" @click="showItem(row)">编辑</el-button>
                <el-button v-if="can('system:dict:remove')" link type="danger" @click="delItem(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-pagination
            v-model:current-page="itemPage"
            :total="itemTotal"
            :page-size="10"
            layout="prev,pager,next"
            small
            style="margin-top: 8px; justify-content: flex-end"
            @current-change="loadItems"
          />
        </template>
      </el-card>
    </el-col>
  </el-row>

  <el-dialog v-model="typeVis" :title="typeForm.id ? '编辑字典类型' : '新增字典类型'" width="480px">
    <el-form :model="typeForm" label-width="90px">
      <el-form-item label="类型编码">
        <el-input v-model="typeForm.dict_type" placeholder="如 user_status" />
      </el-form-item>
      <el-form-item label="类型名称">
        <el-input v-model="typeForm.name" placeholder="如 用户状态" />
      </el-form-item>
      <el-form-item label="状态">
        <el-switch v-model="typeForm.status" :active-value="1" :inactive-value="0" />
      </el-form-item>
      <el-form-item label="备注">
        <el-input v-model="typeForm.remark" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="typeVis = false">取消</el-button>
      <el-button type="primary" @click="saveType">保存</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="itemVis" :title="itemForm.id ? '编辑字典项' : '新增字典项'" width="480px">
    <el-form :model="itemForm" label-width="80px">
      <el-form-item label="标签">
        <el-input v-model="itemForm.label" />
      </el-form-item>
      <el-form-item label="值">
        <el-input v-model="itemForm.value" />
      </el-form-item>
      <el-form-item label="排序">
        <el-input-number v-model="itemForm.sort" :min="0" />
      </el-form-item>
      <el-form-item label="状态">
        <el-switch v-model="itemForm.status" :active-value="1" :inactive-value="0" />
      </el-form-item>
      <el-form-item label="备注">
        <el-input v-model="itemForm.remark" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="itemVis = false">取消</el-button>
      <el-button type="primary" @click="saveItem">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../utils/request'
import { hasPerm } from '../utils/auth'

const types = ref<any[]>([])
const typeTotal = ref(0)
const typePage = ref(1)
const typeKw = ref('')
const currentType = ref('')

const items = ref<any[]>([])
const itemTotal = ref(0)
const itemPage = ref(1)

const typeVis = ref(false)
const itemVis = ref(false)
const typeForm = reactive<any>({ id: 0, dict_type: '', name: '', status: 1, remark: '' })
const itemForm = reactive<any>({ id: 0, dict_type: '', label: '', value: '', sort: 0, status: 1, remark: '' })

const can = hasPerm

async function loadTypes(): Promise<void> {
  const d: any = await api.get('/dict/types', {
    params: { keyword: typeKw.value, page: typePage.value, size: 10 },
  })
  types.value = d.list
  typeTotal.value = d.total
  if (!currentType.value && d.list.length) {
    onSelectType(d.list[0])
  }
}

function onSelectType(row: any): void {
  if (!row) return
  currentType.value = row.dict_type
  itemPage.value = 1
  loadItems()
}

async function loadItems(): Promise<void> {
  if (!currentType.value) return
  const d: any = await api.get('/dict/items', {
    params: { dict_type: currentType.value, page: itemPage.value, size: 10 },
  })
  items.value = d.list
  itemTotal.value = d.total
}

function showType(r?: any): void {
  if (r) Object.assign(typeForm, { ...r })
  else Object.assign(typeForm, { id: 0, dict_type: '', name: '', status: 1, remark: '' })
  typeVis.value = true
}

async function saveType(): Promise<void> {
  const payload = {
    dict_type: typeForm.dict_type,
    name: typeForm.name,
    status: typeForm.status,
    remark: typeForm.remark,
  }
  if (typeForm.id) await api.put(`/dict/types/${typeForm.id}`, payload)
  else await api.post('/dict/types', payload)
  ElMessage.success('保存成功')
  typeVis.value = false
  loadTypes()
}

async function delType(r: any): Promise<void> {
  await ElMessageBox.confirm(`确认删除字典类型【${r.name}】及其字典项吗？`, '提示', { type: 'warning' })
  await api.delete(`/dict/types/${r.id}`)
  ElMessage.success('删除成功')
  if (currentType.value === r.dict_type) {
    currentType.value = ''
    items.value = []
  }
  loadTypes()
}

function showItem(r?: any): void {
  if (r) Object.assign(itemForm, { ...r })
  else Object.assign(itemForm, { id: 0, dict_type: currentType.value, label: '', value: '', sort: 0, status: 1, remark: '' })
  itemVis.value = true
}

async function saveItem(): Promise<void> {
  if (!itemForm.label || itemForm.value === '') {
    ElMessage.warning('标签和值不能为空')
    return
  }
  const payload = {
    dict_type: currentType.value,
    label: itemForm.label,
    value: itemForm.value,
    sort: itemForm.sort,
    status: itemForm.status,
    remark: itemForm.remark,
  }
  if (itemForm.id) await api.put(`/dict/items/${itemForm.id}`, payload)
  else await api.post('/dict/items', payload)
  ElMessage.success('保存成功')
  itemVis.value = false
  loadItems()
  loadTypes()
}

async function delItem(r: any): Promise<void> {
  await ElMessageBox.confirm(`确认删除字典项【${r.label}】吗？`, '提示', { type: 'warning' })
  await api.delete(`/dict/items/${r.id}`)
  ElMessage.success('删除成功')
  loadItems()
  loadTypes()
}

onMounted(loadTypes)
</script>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.filter {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}
</style>
