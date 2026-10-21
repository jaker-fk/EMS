<template>
  <el-card>
    <template #header>
      <div class="toolbar">
        <div>
          <el-input v-model="kw" placeholder="角色名称" clearable style="width: 200px" @keyup.enter="search" />
          <el-button style="margin-left: 8px" @click="search">搜索</el-button>
        </div>
        <el-button v-if="can('system:role:add')" type="primary" @click="showEdit()">新增角色</el-button>
      </div>
    </template>

    <el-table :data="list" v-loading="loading" border stripe>
      <el-table-column prop="name" label="角色名称" width="180" />
      <el-table-column prop="code" label="角色标识" width="160" />
      <el-table-column prop="desc" label="描述" min-width="180" />
      <el-table-column prop="user_count" label="绑定用户" width="100" />
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.status ? 'success' : 'info'">{{ row.status ? '启用' : '禁用' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="220" fixed="right">
        <template #default="{ row }">
          <el-button v-if="can('system:role:edit')" size="small" @click="showEdit(row)">编辑</el-button>
          <el-button v-if="can('system:role:assign')" size="small" type="primary" @click="showEdit(row, true)">分配权限</el-button>
          <el-button v-if="can('system:role:remove')" size="small" type="danger" @click="del(row)">删除</el-button>
        </template>
      </el-table-column>
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

  <el-dialog v-model="vis" :title="form.id ? '编辑角色 / 分配权限' : '新增角色'" width="560px">
    <el-form :model="form" label-width="90px">
      <el-form-item label="角色名称">
        <el-input v-model="form.name" :disabled="form.name === 'super_admin'" />
      </el-form-item>
      <el-form-item label="角色标识">
        <el-input v-model="form.code" placeholder="如 ADMIN" />
      </el-form-item>
      <el-form-item label="描述">
        <el-input v-model="form.desc" />
      </el-form-item>
      <el-form-item label="状态">
        <el-switch v-model="form.status" :active-value="1" :inactive-value="0" />
      </el-form-item>
      <el-form-item label="菜单权限">
        <div class="tree-box">
          <el-tree
            ref="treeRef"
            :data="menuTree"
            :props="{ label: 'name', children: 'children' }"
            node-key="id"
            show-checkbox
            check-strictly
            default-expand-all
          />
        </div>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="vis = false">取消</el-button>
      <el-button type="primary" @click="save">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { nextTick, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../utils/request'
import { hasPerm } from '../utils/auth'

const list = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const kw = ref('')
const loading = ref(false)
const vis = ref(false)
const menuTree = ref<any[]>([])
const treeRef = ref()
const form = reactive<any>({ id: 0, name: '', code: '', desc: '', status: 1, menu_ids: [] })

const can = hasPerm

async function load(): Promise<void> {
  loading.value = true
  try {
    const d: any = await api.get('/roles', { params: { keyword: kw.value, page: page.value, size: size.value } })
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

async function ensureMenus(): Promise<void> {
  if (!menuTree.value.length) menuTree.value = (await api.get('/menus/tree')) as any
}

async function showEdit(r?: any, focusAssign = false): Promise<void> {
  await ensureMenus()
  let menuIds: number[] = []
  if (r) {
    menuIds = (await api.get(`/roles/${r.id}/menus`)) as any
    Object.assign(form, { id: r.id, name: r.name, code: r.code, desc: r.desc, status: r.status, menu_ids: menuIds })
  } else {
    Object.assign(form, { id: 0, name: '', code: '', desc: '', status: 1, menu_ids: [] })
  }
  vis.value = true
  await nextTick()
  treeRef.value?.setCheckedKeys(menuIds)
  if (focusAssign) {
    // 仅用于提示用户当前为权限分配操作
    ElMessage.info(`正在为角色【${form.name}】分配菜单权限`)
  }
}

async function save(): Promise<void> {
  const checked: number[] = treeRef.value ? treeRef.value.getCheckedKeys() : form.menu_ids
  const payload = { name: form.name, code: form.code, desc: form.desc, status: form.status, menu_ids: checked }
  if (form.id) await api.put(`/roles/${form.id}`, payload)
  else await api.post('/roles', payload)
  ElMessage.success('保存成功')
  vis.value = false
  load()
}

async function del(r: any): Promise<void> {
  await ElMessageBox.confirm(`确认删除角色【${r.name}】吗？`, '提示', { type: 'warning' })
  await api.delete(`/roles/${r.id}`)
  ElMessage.success('删除成功')
  load()
}

onMounted(load)
</script>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.tree-box {
  width: 100%;
  max-height: 280px;
  overflow: auto;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  padding: 6px;
}
</style>
