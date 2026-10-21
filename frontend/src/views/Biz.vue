<template>
  <el-card header="业务数据">
    <el-input v-model="kw" placeholder="搜索名称" style="width: 200px" @keyup.enter="load" />
    <el-button @click="load">搜索</el-button>
    <el-button type="primary" @click="showEdit()">新增</el-button>
    <el-button @click="exportXlsx">导出Excel</el-button>
    <el-button type="danger" :disabled="!sel.length" @click="batchDel">批量删除</el-button>
    <el-table :data="list" @selection-change="onSel">
      <el-table-column type="selection" width="50" />
      <el-table-column prop="name" label="名称" />
      <el-table-column prop="category" label="分类" />
      <el-table-column prop="price" label="价格" />
      <el-table-column prop="remark" label="备注" />
      <el-table-column label="操作">
        <template #default="s">
          <el-button size="small" @click="showEdit(s.row)">编辑</el-button>
          <el-button size="small" type="danger" @click="del(s.row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination
      v-model:current-page="page"
      :total="total"
      :page-size="size"
      layout="total,prev,pager,next"
      @current-change="load"
    />
  </el-card>
  <el-dialog v-model="vis" title="业务记录">
    <el-form :model="form" label-width="80px">
      <el-form-item label="名称">
        <el-input v-model="form.name" />
      </el-form-item>
      <el-form-item label="分类">
        <el-input v-model="form.category" />
      </el-form-item>
      <el-form-item label="价格">
        <el-input-number v-model="form.price" :min="0" />
      </el-form-item>
      <el-form-item label="备注">
        <el-input v-model="form.remark" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="vis = false">取消</el-button>
      <el-button type="primary" @click="save">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import api from '../utils/request';

const list = ref([]);
const sel = ref<any[]>([]);
const total = ref(0);
const page = ref(1);
const size = ref(10);
const kw = ref('');
const vis = ref(false);
const form = reactive<any>({ id: 0, name: '', category: '', price: 0, remark: '' });

async function load(): Promise<void> {
  const d: any = await api.get('/biz', { params: { keyword: kw.value, page: page.value, size: size.value } });
  list.value = d.list;
  total.value = d.total;
}

function onSel(rows: any[]): void {
  sel.value = rows;
}

function showEdit(r?: any): void {
  if (r) {
    Object.assign(form, { ...r });
  } else {
    Object.assign(form, { id: 0, name: '', category: '', price: 0, remark: '' });
  }
  vis.value = true;
}

async function save(): Promise<void> {
  const payload = { name: form.name, category: form.category, price: form.price, remark: form.remark };
  if (form.id) {
    await api.put(`/biz/${form.id}`, payload);
  } else {
    await api.post('/biz', payload);
  }
  vis.value = false;
  load();
}

async function del(id: number): Promise<void> {
  await api.delete('/biz', { params: { ids: String(id) } });
  load();
}

async function batchDel(): Promise<void> {
  const ids = sel.value.map((x) => x.id).join(',');
  await api.delete('/biz', { params: { ids } });
  load();
}

async function exportXlsx(): Promise<void> {
  const t = localStorage.getItem('token');
  const res = await fetch(`/api/biz/export?keyword=${encodeURIComponent(kw.value)}`, {
    headers: { Authorization: 'Bearer ' + t },
  });
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'biz.xlsx';
  a.click();
  URL.revokeObjectURL(url);
}

onMounted(load);
</script>
