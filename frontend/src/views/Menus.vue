<template>
  <el-card>
    <template #header>
      <div class="toolbar">
        <span>菜单管理（目录 / 页面 / 按钮）</span>
        <el-button v-if="can('system:menu:add')" type="primary" @click="showEdit()">新增菜单</el-button>
      </div>
    </template>

    <el-table
      :data="tree"
      row-key="id"
      border
      default-expand-all
      v-loading="loading"
      :tree-props="{ children: 'children' }"
    >
      <el-table-column prop="name" label="菜单名称" min-width="160" />
      <el-table-column label="类型" width="90">
        <template #default="{ row }">
          <el-tag :type="typeTag(row.menu_type)" size="small">{{ typeLabel(row.menu_type) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="path" label="路由地址" width="140" />
      <el-table-column prop="component" label="组件路径" min-width="160" />
      <el-table-column prop="perms" label="权限标识" min-width="170" />
      <el-table-column prop="sort" label="排序" width="70" />
      <el-table-column label="可见" width="70">
        <template #default="{ row }">{{ row.visible ? '是' : '否' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="170" fixed="right">
        <template #default="{ row }">
          <el-button v-if="can('system:menu:edit')" size="small" @click="showEdit(row)">编辑</el-button>
          <el-button v-if="can('system:menu:remove')" size="small" type="danger" @click="del(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>

  <el-dialog v-model="vis" :title="form.id ? '编辑菜单' : '新增菜单'" width="560px">
    <el-form :model="form" label-width="90px">
      <el-form-item label="上级菜单">
        <el-select v-model="form.parent_id" style="width: 100%">
          <el-option :value="0" label="顶级菜单" />
          <el-option v-for="m in parentOptions" :key="m.id" :value="m.id" :label="m.name" />
        </el-select>
      </el-form-item>
      <el-form-item label="菜单类型">
        <el-radio-group v-model="form.menu_type">
          <el-radio value="M">目录</el-radio>
          <el-radio value="C">页面</el-radio>
          <el-radio value="F">按钮</el-radio>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="菜单名称">
        <el-input v-model="form.name" />
      </el-form-item>
      <el-form-item v-if="form.menu_type !== 'F'" label="路由地址">
        <el-input v-model="form.path" placeholder="/users" />
      </el-form-item>
      <el-form-item v-if="form.menu_type === 'C'" label="组件路径">
        <el-input v-model="form.component" placeholder="views/Users.vue" />
      </el-form-item>
      <el-form-item label="权限标识">
        <el-input v-model="form.perms" placeholder="system:user:list" />
      </el-form-item>
      <el-form-item v-if="form.menu_type !== 'F'" label="图标">
        <el-input v-model="form.icon" placeholder="Element Plus 图标名" />
      </el-form-item>
      <el-form-item label="排序">
        <el-input-number v-model="form.sort" :min="0" />
      </el-form-item>
      <el-form-item v-if="form.menu_type !== 'F'" label="是否可见">
        <el-switch v-model="form.visible" :active-value="1" :inactive-value="0" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="vis = false">取消</el-button>
      <el-button type="primary" @click="save">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../utils/request'
import { hasPerm } from '../utils/auth'

const tree = ref<any[]>([])
const flat = ref<any[]>([])
const loading = ref(false)
const vis = ref(false)
const form = reactive<any>({
  id: 0,
  parent_id: 0,
  name: '',
  menu_type: 'C',
  path: '',
  component: '',
  perms: '',
  icon: '',
  sort: 0,
  visible: 1,
})

const can = hasPerm

const parentOptions = computed(() => flat.value.filter((m) => m.menu_type !== 'F' && m.id !== form.id))

function typeLabel(t: string): string {
  return t === 'M' ? '目录' : t === 'F' ? '按钮' : '页面'
}
function typeTag(t: string): 'success' | 'warning' | 'info' {
  return t === 'M' ? 'warning' : t === 'F' ? 'info' : 'success'
}

async function load(): Promise<void> {
  loading.value = true
  try {
    tree.value = (await api.get('/menus/tree')) as any
    flat.value = (await api.get('/menus')) as any
  } finally {
    loading.value = false
  }
}

function showEdit(r?: any): void {
  if (r) Object.assign(form, { ...r })
  else
    Object.assign(form, {
      id: 0, parent_id: 0, name: '', menu_type: 'C', path: '', component: '', perms: '', icon: '', sort: 0, visible: 1,
    })
  vis.value = true
}

async function save(): Promise<void> {
  if (!form.name) {
    ElMessage.warning('请输入菜单名称')
    return
  }
  const payload = { ...form }
  delete payload.id
  delete payload.children
  if (form.id) await api.put(`/menus/${form.id}`, payload)
  else await api.post('/menus', payload)
  ElMessage.success('保存成功')
  vis.value = false
  load()
}

async function del(r: any): Promise<void> {
  await ElMessageBox.confirm(`确认删除菜单【${r.name}】吗？`, '提示', { type: 'warning' })
  await api.delete(`/menus/${r.id}`)
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
</style>
