import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { initAuthHandlers } from './stores/auth'
import './style.css'

const app = createApp(App)
app.use(createPinia())
app.use(router)

// 初始化认证处理器
initAuthHandlers()

app.mount('#app')
