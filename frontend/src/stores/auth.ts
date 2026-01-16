import { defineStore } from 'pinia'
import { login as loginApi, fetchMe, setAuthHandlers } from '../services/api'
import type { LoginPayload, LoginResult } from '../types/api'

type Tokens = { access?: string; refresh?: string }

const TOKEN_KEY = 'mrdoc_tokens'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null as LoginResult['user'] | null,
    tokens: {} as Tokens,
    initialized: false,
    loading: false,
    error: '' as string | null,
  }),
  getters: {
    isAuthenticated: (state) => Boolean(state.tokens.access),
  },
  actions: {
    restore() {
      const saved = localStorage.getItem(TOKEN_KEY)
      if (saved) {
        this.tokens = JSON.parse(saved)
      }
      this.initialized = true
    },
    persistTokens(tokens: Tokens) {
      this.tokens = { ...this.tokens, ...tokens }
      localStorage.setItem(TOKEN_KEY, JSON.stringify(this.tokens))
    },
    async login(payload: LoginPayload) {
      this.loading = true
      this.error = null
      try {
        const res = await loginApi(payload)
        this.user = res.data.data.user
        this.persistTokens({ access: res.data.data.access, refresh: res.data.data.refresh })
      } catch (e: any) {
        this.error = e?.response?.data?.msg || '登录失败'
        throw e
      } finally {
        this.loading = false
      }
    },
    async loadMe() {
      if (!this.tokens.access) return
      try {
        const res = await fetchMe()
        this.user = res.data.data
      } catch (e) {
        // ignore
      }
    },
    logout() {
      this.user = null
      this.tokens = {}
      localStorage.removeItem(TOKEN_KEY)
    },
  },
})

// 延迟初始化，避免在 Pinia 未就绪时调用
export function initAuthHandlers() {
  const store = useAuthStore()
  setAuthHandlers(
    () => store.tokens,
    (tokens) => store.persistTokens(tokens),
    () => store.logout()
  )
  store.restore()
}
