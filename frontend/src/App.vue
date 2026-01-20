<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
import { useAuthStore } from './stores/auth'

const auth = useAuthStore()
</script>

<template>
  <div class="app-shell">
    <header class="app-header">
      <div class="brand">
        MrDoc
        <span class="brand-badge">v1 API</span>
      </div>
      <nav class="nav">
        <RouterLink to="/projects">Projects</RouterLink>
      </nav>
      <div class="user-chip" v-if="auth.isAuthenticated">
        <span>{{ auth.user?.username || 'User' }}</span>
        <button @click="auth.logout">Logout</button>
      </div>
      <div class="user-chip" v-else>
        <RouterLink to="/login">Login</RouterLink>
      </div>
    </header>
    <main class="page">
      <RouterView />
    </main>
  </div>
</template>
