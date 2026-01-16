<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { fetchDoc, fetchDocTags, updateDocTags, fetchTags, fetchDocShare, updateDocShare } from '../services/api'
import type { Doc, DocShare } from '../types/api'
import AccessCodeModal from '../components/AccessCodeModal.vue'

const route = useRoute()
const router = useRouter()
const doc = ref<Doc | null>(null)
const loading = ref(false)
const error = ref('')
const showAccess = ref(false)
const pendingProjectId = ref<number | null>(null)
const tags = ref<Array<{ id: number; name: string }>>([])
const newTag = ref('')
const tagSuggest = ref<Array<{ id: number; name: string }>>([])
const share = ref<DocShare | null>(null)
const shareType = ref(0)
const shareValue = ref('')
const shareEnabled = ref(true)

const setAccessCodeCookie = (projectId: number, code: string) => {
  const name = `viewcode-${projectId}`
  document.cookie = `${name}=${code};path=/;max-age=${60 * 60 * 24 * 30}`
}

const load = async () => {
  loading.value = true
  error.value = ''
  try {
    const res = await fetchDoc(route.params.id as string)
    doc.value = res.data.data
    pendingProjectId.value = doc.value.top_doc
    const tagRes = await fetchDocTags(doc.value.id)
    tags.value = tagRes.data.data
    const shareRes = await fetchDocShare(doc.value.id)
    share.value = shareRes.data.data
    shareType.value = share.value?.share_type ?? 0
    shareValue.value = share.value?.share_value || ''
    shareEnabled.value = share.value?.is_enable ?? true
  } catch (e: any) {
    const status = e?.response?.status
    if (status === 403) {
      // require access code
      const pid = doc.value?.top_doc || Number(route.query.project_id) || null
      pendingProjectId.value = pid
      showAccess.value = true
      error.value = '需要访问码'
    } else {
      error.value = e?.response?.data?.msg || '加载失败'
    }
  } finally {
    loading.value = false
  }
}

const handleAccessSubmit = async (code: string) => {
  if (!pendingProjectId.value) return
  setAccessCodeCookie(pendingProjectId.value, code)
  showAccess.value = false
  await load()
}

const addTag = async () => {
  if (!doc.value) return
  const trimmed = newTag.value.trim()
  if (!trimmed) return
  const res = await updateDocTags(doc.value.id, [...tags.value.map((t) => t.name), trimmed])
  tags.value = res.data.data
  newTag.value = ''
  tagSuggest.value = []
}

const removeTag = async (name: string) => {
  if (!doc.value) return
  const remaining = tags.value.filter((t) => t.name !== name).map((t) => t.name)
  const res = await updateDocTags(doc.value.id, remaining)
  tags.value = res.data.data
}

const querySuggest = async () => {
  if (!newTag.value.trim()) {
    tagSuggest.value = []
    return
  }
  const res = await fetchTags(newTag.value.trim())
  tagSuggest.value = res.data.data
}

const useSuggest = (name: string) => {
  newTag.value = name
  tagSuggest.value = []
}

const saveShare = async () => {
  if (!doc.value) return
  const res = await updateDocShare(doc.value.id, {
    share_type: shareType.value,
    share_value: shareValue.value || null,
    is_enable: shareEnabled.value,
  })
  share.value = res.data.data
}

const createDoc = () => {
  if (!doc.value) return
  router.push({ name: 'doc-create', params: { projectId: doc.value.top_doc } })
}

onMounted(load)
</script>

<template>
  <div class="stack" style="gap: 16px;">
    <div class="row" style="justify-content: space-between; align-items: center;">
      <div>
        <h1>Document</h1>
        <p class="muted">Doc ID: {{ route.params.id }}</p>
      </div>
      <div class="row" style="gap: 10px;">
        <RouterLink v-if="doc" class="btn" :to="{ name: 'project', params: { id: doc.top_doc } }">
          返回文集
        </RouterLink>
        <button v-if="doc" class="btn primary" @click="createDoc">
          + 新建文档
        </button>
        <RouterLink v-if="doc" class="btn" :to="{ name: 'doc-edit', params: { id: doc.id }, query: { project_id: doc.top_doc } }">
          编辑
        </RouterLink>
      </div>
    </div>
    <div v-if="loading" class="muted">Loading...</div>
    <div v-else-if="error" style="color: #f58f8f">{{ error }}</div>
    <div v-else-if="doc" class="stack" style="gap: 10px;">
      <div class="card">
        <div class="row" style="justify-content: space-between;">
          <strong>{{ doc.name }}</strong>
          <span class="pill">Mode: {{ doc.editor_mode }}</span>
        </div>
        <p class="muted">Status: {{ doc.status }} · Top project: {{ doc.top_doc }}</p>
        <div class="stack">
          <span class="muted">Content preview:</span>
          <div class="card" style="background: rgba(255,255,255,0.02); border-style: dashed;">
            <pre style="margin: 0; white-space: pre-wrap;">{{ doc.pre_content || doc.content || 'No content' }}</pre>
          </div>
        </div>
      </div>
      <div class="card">
        <div class="row" style="justify-content: space-between; align-items: center;">
          <h3>Tags</h3>
          <div class="row">
            <input class="input" v-model="newTag" placeholder="添加标签" style="width: 160px;" />
            <button class="btn" @click="querySuggest">搜索</button>
            <button class="btn" @click="addTag">添加</button>
          </div>
        </div>
        <div class="row" style="gap: 8px; flex-wrap: wrap;" v-if="tagSuggest.length">
          <span class="pill" v-for="s in tagSuggest" :key="s.id" @click="useSuggest(s.name)" style="cursor: pointer;">
            {{ s.name }}
          </span>
        </div>
        <div class="row" style="gap: 8px; flex-wrap: wrap;">
          <span class="pill" v-for="t in tags" :key="t.id">
            {{ t.name }}
            <button class="btn" style="padding: 4px 6px;" @click="removeTag(t.name)">x</button>
          </span>
        </div>
      </div>
      <div class="card">
        <h3>Share</h3>
        <div class="stack">
          <div class="row" style="gap: 12px;">
            <label class="row" style="gap: 6px;">
              <input type="radio" value="0" v-model="shareType" /> 公开
            </label>
            <label class="row" style="gap: 6px;">
              <input type="radio" value="1" v-model="shareType" /> 私密（分享码）
            </label>
            <label class="row" style="gap: 6px;">
              <input type="checkbox" v-model="shareEnabled" /> 启用
            </label>
          </div>
          <div class="row" v-if="shareType === 1" style="gap: 8px; align-items: center;">
            <span class="muted">分享码：</span>
            <input class="input" v-model="shareValue" placeholder="share code" style="width: 160px;" />
          </div>
          <button class="btn primary" @click="saveShare">保存分享设置</button>
          <div class="muted">
            Token: {{ share?.token || '未生成' }} · 启用: {{ shareEnabled ? '是' : '否' }}
          </div>
        </div>
      </div>
    </div>
    <AccessCodeModal
      :show="showAccess"
      :project-id="pendingProjectId"
      @submit="handleAccessSubmit"
      @close="showAccess = false"
    />
  </div>
</template>
