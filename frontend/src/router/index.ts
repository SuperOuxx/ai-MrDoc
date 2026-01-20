import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const LoginView = () => import('../views/LoginView.vue')
const ProjectsView = () => import('../views/ProjectsView.vue')
const ProjectDetailView = () => import('../views/ProjectDetailView.vue')
const DocDetailView = () => import('../views/DocDetailView.vue')
const EditorDemoView = () => import('../views/EditorDemoView.vue')
const DocEditView = () => import('../views/DocEditView.vue')

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/projects' },
    { path: '/login', name: 'login', component: LoginView, meta: { public: true, title: 'Login' } },
    { path: '/projects', name: 'projects', component: ProjectsView, meta: { requiresAuth: true, title: 'Projects' } },
    { path: '/projects/:id', name: 'project', component: ProjectDetailView, meta: { requiresAuth: true, title: 'Project' } },
    { path: '/docs/:id', name: 'doc', component: DocDetailView, meta: { requiresAuth: true, title: 'Document' } },
    { path: '/docs/:id/edit', name: 'doc-edit', component: DocEditView, meta: { requiresAuth: true, title: 'Edit Doc' } },
    { path: '/projects/:projectId/docs/new', name: 'doc-create', component: DocEditView, meta: { requiresAuth: true, title: 'New Doc' } },
    { path: '/editor-demo', name: 'editor-demo', component: EditorDemoView, meta: { requiresAuth: true, title: 'Editors' } },
  ],
})

router.beforeEach((to, _from, next) => {
  const auth = useAuthStore()
  if (!auth.initialized) {
    auth.restore()
  }

  if (to.meta.title) {
    document.title = `MrDoc · ${to.meta.title as string}`
  }

  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return next({ name: 'login', query: { redirect: to.fullPath } })
  }
  if (to.meta.public && auth.isAuthenticated) {
    return next({ name: 'projects' })
  }
  return next()
})

export default router
