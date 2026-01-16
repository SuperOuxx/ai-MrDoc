import axios, { type AxiosError, type AxiosInstance, type AxiosRequestConfig } from 'axios'
import type { ApiResponse, LoginPayload, LoginResult, Pagination, Project, Doc, DocNode } from '../types/api'

type TokenBundle = { access?: string; refresh?: string }
type TokenGetter = () => TokenBundle
type TokenUpdater = (tokens: TokenBundle) => void
type Logout = () => void

const API_BASE = import.meta.env.VITE_API_BASE || '/api/v1'
const API_VERSION = '1.0'

let getTokens: TokenGetter = () => ({})
let updateTokens: TokenUpdater = () => {}
let logout: Logout = () => {}
let isRefreshing = false
let pendingQueue: Array<(token?: string) => void> = []

const api: AxiosInstance = axios.create({
  baseURL: API_BASE,
  timeout: 15000,
})

export const setAuthHandlers = (getter: TokenGetter, updater: TokenUpdater, onLogout: Logout) => {
  getTokens = getter
  updateTokens = updater
  logout = onLogout
}

api.interceptors.request.use((config) => {
  const { access } = getTokens()
  if (access) {
    config.headers = config.headers || {}
    config.headers.Authorization = `Bearer ${access}`
  }
  config.headers = config.headers || {}
  config.headers['API-Version'] = API_VERSION
  return config
})

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const status = error.response?.status
    const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean }

    if (status === 401 && !originalRequest._retry) {
      const { refresh } = getTokens()
      if (!refresh) {
        logout()
        return Promise.reject(error)
      }

      if (isRefreshing) {
        return new Promise((resolve) => {
          pendingQueue.push((token) => {
            if (token && originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${token}`
            }
            resolve(api(originalRequest))
          })
        })
      }

      originalRequest._retry = true
      isRefreshing = true
      try {
        const res = await api.post<ApiResponse<{ access: string }>>('/auth/refresh/', { refresh })
        const newAccess = res.data.data.access
        updateTokens({ access: newAccess })
        pendingQueue.forEach((cb) => cb(newAccess))
        pendingQueue = []
        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${newAccess}`
        }
        return api(originalRequest)
      } catch (refreshErr) {
        logout()
        pendingQueue = []
        return Promise.reject(refreshErr)
      } finally {
        isRefreshing = false
      }
    }
    return Promise.reject(error)
  }
)

export const login = (payload: LoginPayload) => api.post<ApiResponse<LoginResult>>('/auth/login/', payload)
export const fetchMe = () => api.get<ApiResponse<LoginResult['user']>>('/users/me/')
export const fetchProjects = (page = 1, page_size = 10, q = '') =>
  api.get<ApiResponse<Pagination<Project>>>('/projects/', { params: { page, page_size, q } })
export const fetchProjectDocs = (projectId: number, q = '') =>
  api.get<ApiResponse<Doc[]>>(`/projects/${projectId}/docs/`, { params: { q } })
export const fetchCollaborators = (projectId: number) =>
  api.get<ApiResponse<Array<{ id: number; username: string; role: number }>>>(`/projects/${projectId}/collaborators/`)
export const fetchDoc = (id: string | number) => api.get<ApiResponse<Doc>>(`/docs/${id}/`)
export const fetchProjectTree = (projectId: number) => api.get<ApiResponse<DocNode[]>>(`/projects/${projectId}/tree/`)
export const updateProjectTree = (projectId: number, tree: DocNode[]) =>
  api.put<ApiResponse<null>>(`/projects/${projectId}/tree/`, { tree })
export const fetchDocTags = (docId: number | string) => api.get<ApiResponse<Array<{ id: number; name: string }>>>(`/docs/${docId}/tags/`)
export const updateDocTags = (docId: number | string, tags: string[]) =>
  api.post<ApiResponse<Array<{ id: number; name: string }>>>(`/docs/${docId}/tags/`, { tags })
export const fetchTags = (q = '') => api.get<ApiResponse<Array<{ id: number; name: string }>>>('/tags/', { params: { q } })
export const fetchDocShare = (docId: number | string) => api.get<ApiResponse<any>>(`/docs/${docId}/share/`)
export const updateDocShare = (
  docId: number | string,
  payload: { share_type?: number; share_value?: string | null; is_enable?: boolean }
) => api.post<ApiResponse<any>>(`/docs/${docId}/share/`, payload)
export const createDoc = (payload: Partial<Doc>) => api.post<ApiResponse<Doc>>('/docs/', payload)
export const updateDoc = (id: number | string, payload: Partial<Doc>) => api.put<ApiResponse<Doc>>(`/docs/${id}/`, payload)

export default api
