<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const form = ref({ username: '', password: '' })
const error = ref('')
const loading = ref(false)

const handleSubmit = async () => {
  loading.value = true
  error.value = ''
  try {
    await auth.login(form.value)
    await auth.loadMe()
    const redirect = (route.query.redirect as string) || '/projects'
    router.replace(redirect)
  } catch (e: any) {
    error.value = auth.error || '登录失败'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="stack" style="max-width: 400px; margin: 0 auto;">
    <h1>Login</h1>
    <p class="muted">Use your MrDoc credentials to access the new Vue front-end.</p>
    <div class="stack">
      <label class="stack">
        <span class="muted">Username</span>
        <input class="input" v-model="form.username" placeholder="username" />
      </label>
      <label class="stack">
        <span class="muted">Password</span>
        <input class="input" v-model="form.password" type="password" placeholder="password" />
      </label>
      <button class="btn primary" :disabled="loading" @click="handleSubmit">
        {{ loading ? 'Signing in...' : 'Sign In' }}
      </button>
      <p v-if="error" style="color: #f58f8f">{{ error }}</p>
    </div>
  </div>
</template>
