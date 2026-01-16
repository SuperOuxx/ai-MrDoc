<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { fetchCollaborators, fetchProjectDocs, fetchProjectTree, fetchProjects } from '../services/api'
import type { Doc, Project, DocNode } from '../types/api'
import DocTreeNode from '../components/DocTreeNode.vue'

const route = useRoute()
const router = useRouter()
const project = ref<Project | null>(null)
const docs = ref<Doc[]>([])
const tree = ref<DocNode[]>([])
const collaborators = ref<Array<{ id: number; username: string; role: number }>>([])
const loading = ref(false)
const error = ref('')
const uploadInfo = ref('暂未接入，预留为后端 /api/v1/uploads/* 或 OSS 签名直传。')
const docQuery = ref('')

const load = async () => {
  loading.value = true
  error.value = ''
  try {
    const pid = Number(route.params.id)
    const pRes = await fetchProjects(1, 1) // quick fetch to ensure token; real data via list already sorted
    // Try to find project from list; if not, skip
    project.value =
      pRes.data.data.results.find((p) => p.id === pid) || { id: pid, name: `Project ${pid}`, intro: '', role: 0, role_value: null, is_top: false }
    const [docRes, collaRes, treeRes] = await Promise.all([
      fetchProjectDocs(pid, docQuery.value),
      fetchCollaborators(pid),
      fetchProjectTree(pid),
    ])
    docs.value = docRes.data.data
    collaborators.value = collaRes.data.data
    tree.value = treeRes.data.data
  } catch (e: any) {
    error.value = e?.response?.data?.msg || '加载失败'
  } finally {
    loading.value = false
  }
}

const openDoc = (doc: Doc) => router.push({ name: 'doc', params: { id: doc.id }, query: { project_id: doc.top_doc } })
const openDocById = (id: number) => router.push({ name: 'doc', params: { id }, query: { project_id: route.params.id } })
const createDoc = () => router.push({ name: 'doc-create', params: { projectId: route.params.id } })

onMounted(load)
</script>

<template>
  <div class="stack" style="gap: 18px;">
    <div class="row" style="justify-content: space-between; align-items: center;">
      <div>
        <h1>{{ project?.name || 'Project' }}</h1>
        <p class="muted">文集 ID: {{ route.params.id }}</p>
      </div>
      <div class="row" style="gap: 10px; align-items: center;">
        <span class="pill">协作者：{{ collaborators.length }}</span>
        <button class="btn primary" @click="createDoc">+ 新建文档</button>
      </div>
    </div>

    <div v-if="loading" class="muted">Loading...</div>
    <div v-else-if="error" style="color: #f58f8f">{{ error }}</div>
    <div v-else class="stack" style="gap: 16px;">
      <div class="card">
        <div class="row" style="justify-content: space-between; align-items: center;">
          <h3>文档目录树</h3>
          <div class="row" style="gap: 8px;">
            <input class="input" v-model="docQuery" placeholder="搜索文档" style="width: 200px;" />
            <button class="btn" @click="load">刷新</button>
            <button class="btn primary" @click="createDoc">+ 新建</button>
          </div>
        </div>
        <div v-if="tree.length === 0" class="muted">暂无目录</div>
        <div v-else class="stack" style="gap: 8px;">
          <DocTreeNode v-for="node in tree" :key="node.id" :node="node" @open="openDocById" />
        </div>
      </div>

      <div class="card">
        <div class="row" style="justify-content: space-between; align-items: center;">
          <h3>文档列表</h3>
          <button class="btn primary" @click="createDoc">+ 新建文档</button>
        </div>
        <div v-if="docs.length === 0" class="muted">暂无文档，点击上方按钮创建第一个文档</div>
        <div class="stack" v-else>
          <div class="card" v-for="d in docs" :key="d.id" style="background: rgba(255,255,255,0.03);">
            <div class="row" style="justify-content: space-between; align-items: center;">
              <div class="stack" style="gap: 4px;">
                <strong>{{ d.name }}</strong>
                <span class="muted">Status: {{ d.status }} · Parent: {{ d.parent_doc }}</span>
              </div>
            <button class="btn" @click="openDoc(d)">查看</button>
          </div>
        </div>
      </div>
      </div>

      <div class="card">
        <h3>Collaborators</h3>
        <div v-if="collaborators.length === 0" class="muted">暂无协作者</div>
        <div class="stack" v-else>
          <div class="row" v-for="c in collaborators" :key="c.id" style="justify-content: space-between;">
            <span>{{ c.username }}</span>
            <span class="pill">role {{ c.role }}</span>
          </div>
        </div>
      </div>

      <div class="card">
        <h3>Uploads (占位)</h3>
        <p class="muted">{{ uploadInfo }}</p>
        <div class="row" style="gap: 8px; flex-wrap: wrap;">
          <button class="btn" disabled>上传图片（待接入）</button>
          <button class="btn" disabled>上传附件（待接入）</button>
        </div>
      </div>
    </div>
  </div>
</template>
