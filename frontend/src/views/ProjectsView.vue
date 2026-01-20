<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { fetchProjects } from '../services/api'
import type { Project, Pagination } from '../types/api'
import { useAuthStore } from '../stores/auth'
import { useRouter } from 'vue-router'

const projects = ref<Project[]>([])
const meta = ref<Partial<Pagination<Project>>>({})
const errorMsg = ref('')
const query = ref('')
const loading = ref(false)
const auth = useAuthStore()
const router = useRouter()

const load = async (page = 1) => {
  loading.value = true
  errorMsg.value = ''
  try {
    const res = await fetchProjects(page, 10, query.value)
    projects.value = res.data.data.results
    meta.value = res.data.data
  } catch (e: any) {
    errorMsg.value = e?.response?.data?.msg || '加载失败'
  } finally {
    loading.value = false
  }
}

const goProject = (id: number) => router.push({ name: 'project', params: { id } })

onMounted(async () => {
  if (!auth.user) {
    await auth.loadMe()
  }
  load()
})
</script>

<template>
  <div class="stack" style="gap: 18px;">
    <div class="row" style="justify-content: space-between; align-items: flex-start;">
      <div class="stack" style="gap: 6px;">
        <h1>Projects</h1>
        <p class="muted">Browse projects available to your account via /api/v1.</p>
      </div>
      <button class="btn">New Project (coming soon)</button>
    </div>
    <div class="row" style="align-items: center; gap: 10px;">
      <input class="input" v-model="query" placeholder="搜索文集" style="max-width: 240px;" />
      <button class="btn" @click="load(1)">搜索</button>
    </div>
    <div v-if="loading" class="muted">Loading...</div>
    <div v-else class="card-grid">
      <div class="card" v-for="p in projects" :key="p.id">
        <div class="row" style="justify-content: space-between;">
          <strong>{{ p.name }}</strong>
          <span class="pill">Docs: {{ p.doc_count ?? 0 }}</span>
        </div>
        <p class="muted">{{ p.intro || 'No description' }}</p>
        <div class="row" style="justify-content: space-between; align-items: center;">
          <span class="pill">role {{ p.role }}</span>
          <button class="btn" @click="goProject(p.id)">Open</button>
        </div>
      </div>
    </div>
    <p v-if="errorMsg" style="color: #f58f8f">{{ errorMsg }}</p>
  </div>
</template>
