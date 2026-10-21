<template>
  <el-row :gutter="12">
    <el-col :span="8">
      <el-card header="个人信息">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="账号">{{ info.username }}</el-descriptions-item>
          <el-descriptions-item label="昵称">{{ info.nickname || '-' }}</el-descriptions-item>
          <el-descriptions-item label="手机号">{{ info.phone || '-' }}</el-descriptions-item>
          <el-descriptions-item label="角色">
            <el-tag v-for="r in roles" :key="r" size="small" style="margin-right: 4px">{{ r }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="info.status ? 'success' : 'danger'">{{ info.status ? '启用' : '禁用' }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ info.created_at }}</el-descriptions-item>
        </el-descriptions>
      </el-card>

      <el-card header="修改密码" style="margin-top: 12px">
        <el-form ref="pwdRef" :model="pwd" :rules="rules" label-width="90px">
          <el-form-item label="原密码" prop="old_password">
            <el-input v-model="pwd.old_password" type="password" show-password />
          </el-form-item>
          <el-form-item label="新密码" prop="new_password">
            <el-input v-model="pwd.new_password" type="password" show-password />
          </el-form-item>
          <el-form-item label="确认密码" prop="confirm">
            <el-input v-model="pwd.confirm" type="password" show-password />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="changePwd">保存</el-button>
          </el-form-item>
        </el-form>
      </el-card>
    </el-col>

    <el-col :span="16">
      <el-card header="我的操作日志">
        <el-table :data="logs" size="small" border>
          <el-table-column prop="module" label="模块" width="110" />
          <el-table-column prop="action" label="类型" width="100" />
          <el-table-column prop="path" label="请求地址" min-width="160" />
          <el-table-column prop="ip" label="IP" width="130" />
          <el-table-column label="结果" width="80">
            <template #default="{ row }">
              <el-tag :type="row.result === '成功' ? 'success' : 'danger'" size="small">{{ row.result }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="时间" width="170" />
        </el-table>
        <el-pagination
          v-model:current-page="page"
          :total="total"
          :page-size="10"
          layout="total,prev,pager,next"
          small
          style="margin-top: 8px; justify-content: flex-end"
          @current-change="loadLogs"
        />
      </el-card>
    </el-col>
  </el-row>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../utils/request'

const info = ref<any>({})
const roles = ref<string[]>([])
const logs = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pwdRef = ref()
const pwd = reactive({ old_password: '', new_password: '', confirm: '' })

const rules = {
  old_password: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  new_password: [{ required: true, min: 6, message: '新密码至少 6 位', trigger: 'blur' }],
  confirm: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    {
      validator: (_r: any, v: string, cb: any) => (v === pwd.new_password ? cb() : cb(new Error('两次密码不一致'))),
      trigger: 'blur',
    },
  ],
}

async function loadInfo(): Promise<void> {
  const d: any = await api.get('/profile')
  info.value = d.user
  roles.value = d.roles
}

async function loadLogs(): Promise<void> {
  const d: any = await api.get('/profile/logs', { params: { page: page.value, size: 10 } })
  logs.value = d.list
  total.value = d.total
}

async function changePwd(): Promise<void> {
  await pwdRef.value?.validate()
  await api.put('/profile/password', { old_password: pwd.old_password, new_password: pwd.new_password })
  ElMessage.success('密码修改成功，请重新登录')
  localStorage.clear()
  location.href = '/login'
}

onMounted(async () => {
  await loadInfo()
  await loadLogs()
})
</script>
