<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { createDoc, fetchDoc, updateDoc } from '../services/api'
import EditorVditor from '../components/EditorVditor.vue'
import EditorEditormd from '../components/EditorEditormd.vue'
import EditorLuckysheet from '../components/EditorLuckysheet.vue'
import type { Doc } from '../types/api'

const route = useRoute()
const router = useRouter()

const isEdit = computed(() => Boolean(route.params.id))
const docId = computed(() => route.params.id as string | undefined)
const projectId = computed(() => Number(route.params.projectId || route.query.project_id || 0))

const form = ref<Partial<Doc>>({
  name: '',
  top_doc: projectId.value,
  parent_doc: 0,
  editor_mode: 2,
  status: 1,
})

const editorMode = computed({
  get: () => form.value.editor_mode || 2,
  set: (v) => (form.value.editor_mode = Number(v)),
})

const contentMd = ref('')
const contentSheet = ref<any[]>([
  {
    name: 'Sheet1',
    color: '',
    status: 1,
    order: 0,
    data: [[]],
    column: 20,
    row: 30,
  },
])
const loading = ref(false)
const error = ref('')
const saving = ref(false)
const ready = ref(false)

const loadDoc = async () => {
  if (!isEdit.value || !docId.value) return
  loading.value = true
  try {
    const res = await fetchDoc(docId.value)
    const d = res.data.data
    form.value = {
      ...form.value,
      ...d,
    }
    if (d.editor_mode === 4) {
      try {
        contentSheet.value = JSON.parse(d.pre_content || '[]')
      } catch {
        contentSheet.value = contentSheet.value
      }
    } else {
      contentMd.value = d.pre_content || d.content || ''
    }
    ready.value = true
  } catch (e: any) {
    const status = e?.response?.status
    if (status === 401) {
      router.replace({ name: 'login', query: { redirect: route.fullPath } })
      return
    }
    error.value = e?.response?.data?.msg || '加载失败'
  } finally {
    loading.value = false
  }
}

const buildPayload = () => {
  const payload: Partial<Doc> = {
    name: form.value.name,
    top_doc: form.value.top_doc,
    parent_doc: form.value.parent_doc || 0,
    editor_mode: editorMode.value,
    status: form.value.status,
  }
  if (editorMode.value === 4) {
    payload.pre_content = JSON.stringify(contentSheet.value)
    payload.content = ''
  } else {
    payload.pre_content = contentMd.value
    payload.content = ''
  }
  return payload
}

const save = async () => {
  saving.value = true
  error.value = ''
  try {
    const payload = buildPayload()
    if (isEdit.value && docId.value) {
      await updateDoc(docId.value, payload)
    } else {
      payload.top_doc = payload.top_doc || projectId.value
      const res = await createDoc(payload)
      const newId = res.data.data.id
      router.replace({ name: 'doc', params: { id: newId }, query: { project_id: payload.top_doc } })
      return
    }
    router.push({ name: 'doc', params: { id: docId.value }, query: { project_id: payload.top_doc } })
  } catch (e: any) {
    error.value = e?.response?.data?.msg || '保存失败'
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  if (isEdit.value) {
    await loadDoc()
  } else {
    ready.value = true
  }
})
</script>

<template>
  <div class="stack" style="gap: 16px;">
    <div class="row" style="justify-content: space-between; align-items: center;">
      <div>
        <h1>{{ isEdit ? '编辑文档' : '新建文档' }}</h1>
        <p class="muted">文集 ID: {{ form.top_doc || projectId }}</p>
      </div>
      <div class="row" style="gap: 10px;">
        <button class="btn" @click="router.back()">返回</button>
        <button class="btn primary" :disabled="saving" @click="save">{{ saving ? '保存中...' : '保存' }}</button>
      </div>
    </div>

    <div v-if="error" style="color: #f58f8f">{{ error }}</div>

    <div class="card">
      <div class="row" style="gap: 12px; align-items: center; flex-wrap: wrap;">
        <label class="stack" style="gap: 6px; width: 240px;">
          <span class="muted">标题</span>
          <input class="input" v-model="form.name" placeholder="文档标题" />
        </label>
        <label class="stack" style="gap: 6px; width: 200px;">
          <span class="muted">上级文档 ID</span>
          <input class="input" type="number" v-model.number="form.parent_doc" placeholder="0 为顶级" />
        </label>
        <label class="stack" style="gap: 6px; width: 180px;">
          <span class="muted">编辑器</span>
          <select class="input" v-model.number="editorMode">
            <option :value="2">Vditor</option>
            <option :value="1">Editormd</option>
            <option :value="4">Luckysheet</option>
          </select>
        </label>
        <label class="stack" style="gap: 6px; width: 160px;">
          <span class="muted">状态</span>
          <select class="input" v-model.number="form.status">
            <option :value="1">发布</option>
            <option :value="0">草稿</option>
          </select>
        </label>
      </div>
    </div>

    <div v-if="!ready" class="muted">Loading editor…</div>
    <template v-else>
      <div class="card" v-if="editorMode !== 4">
        <EditorVditor v-if="editorMode === 2" v-model="contentMd" />
        <EditorEditormd v-else v-model="contentMd" />
      </div>

      <div class="card" v-else>
        <EditorLuckysheet v-model="contentSheet" />
      </div>
    </template>
  </div>
</template>
