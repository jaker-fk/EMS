<template>
  <el-card>
    <template #header>
      <div class="toolbar">
        <div>
          <el-input v-model="kw" placeholder="账号 / 昵称" clearable style="width: 200px" @keyup.enter="search" />
          <el-select v-model="status" placeholder="状态" clearable style="width: 120px; margin-left: 8px" @change="search">
            <el-option label="启用" :value="1" />
            <el-option label="禁用" :value="0" />
          </el-select>
          <el-button style="margin-left: 8px" @click="search">搜索</el-button>
        </div>
        <el-button v-if="can('system:user:add')" type="primary" @click="showEdit()">新增用户</el-button>
      </div>
    </template>

    <el-table :data="list" v-loading="loading" border stripe>
      <el-table-column prop="username" label="账号" width="140" />
      <el-table-column prop="nickname" label="昵称" width="140" />
      <el-table-column prop="phone" label="手机号" width="150" />
      <el-table-column label="角色" min-width="180">
        <template #default="{ row }">
          <el-tag v-for="n in row.role_names" :key="n" size="small" style="margin-right: 4px">{{ n }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.status ? 'success' : 'danger'">{{ row.status ? '启用' : '禁用' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="180" />
      <el-table-column label="操作" width="240" fixed="right">
        <template #default="{ row }">
          <el-button v-if="can('system:user:edit')" size="small" @click="showEdit(row)">编辑</el-button>
          <el-button v-if="can('system:user:reset')" size="small" type="warning" @click="resetPwd(row)">重置密码</el-button>
          <el-button v-if="can('system:user:remove')" size="small" type="danger" @click="del(row)">删除</el-button>
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

  <el-dialog v-model="vis" :title="form.id ? '编辑用户' : '新增用户'" width="520px">
    <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
      <el-form-item label="账号" prop="username">
        <el-input v-model="form.username" :disabled="!!form.id" />
      </el-form-item>
      <el-form-item v-if="!form.id" label="密码" prop="password">
        <el-input v-model="form.password" type="password" show-password placeholder="至少 6 位" />
      </el-form-item>
      <el-form-item label="昵称">
        <el-input v-model="form.nickname" />
      </el-form-item>
      <el-form-item label="手机号">
        <el-input v-model="form.phone" />
      </el-form-item>
      <el-form-item label="角色">
        <el-select v-model="form.role_ids" multiple placeholder="请选择角色" style="width: 100%">
          <el-option v-for="r in roles" :key="r.id" :label="r.name" :value="r.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="状态">
        <el-switch v-model="form.status" :active-value="1" :inactive-value="0" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="vis = false">取消</el-button>
      <el-button type="primary" @click="save">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../utils/request'
import { hasPerm } from '../utils/auth'

const list = ref<any[]>([])
const roles = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const kw = ref('')
const status = ref<number | undefined>(undefined)
const loading = ref(false)
const vis = ref(false)
const formRef = ref()
const form = reactive<any>({ id: 0, username: '', password: '', nickname: '', phone: '', status: 1, role_ids: [] })

const rules = {
  username: [{ required: true, message: '请输入账号', trigger: 'blur' }],
  password: [{ required: true, min: 6, message: '密码至少 6 位', trigger: 'blur' }],
}

const can = hasPerm

async function loadRoles(): Promise<void> {
  roles.value = (await api.get('/roles/all')) as any
}

async function load(): Promise<void> {
  loading.value = true
  try {
    const d: any = await api.get('/users', {
      params: { keyword: kw.value, status: status.value, page: page.value, size: size.value },
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

function showEdit(r?: any): void {
  if (r) Object.assign(form, { ...r, password: '', role_ids: r.role_ids || [] })
  else Object.assign(form, { id: 0, username: '', password: '', nickname: '', phone: '', status: 1, role_ids: [] })
  vis.value = true
}

async function save(): Promise<void> {
  await formRef.value?.validate()
  const payload: any = {
    nickname: form.nickname,
    phone: form.phone,
    status: form.status,
    role_ids: form.role_ids,
  }
  if (form.id) {
    await api.put(`/users/${form.id}`, payload)
  } else {
    await api.post('/users', { ...payload, username: form.username, password: form.password })
  }
  ElMessage.success('保存成功')
  vis.value = false
  load()
}

async function resetPwd(r: any): Promise<void> {
  const { value } = await ElMessageBox.prompt(`请输入 ${r.username} 的新密码`, '重置密码', {
    inputType: 'password',
    inputPattern: /.{6,}/,
    inputErrorMessage: '密码至少 6 位',
  })
  await api.put(`/users/${r.id}/password`, { password: value })
  ElMessage.success('密码已重置')
}

async function del(r: any): Promise<void> {
  await ElMessageBox.confirm(`确认删除用户【${r.username}】吗？`, '提示', { type: 'warning' })
  await api.delete('/users', { params: { ids: String(r.id) } })
  ElMessage.success('删除成功')
  load()
}

onMounted(async () => {
  await loadRoles()
  await load()
})
</script>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
</style>
