import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      'luckysheet/dist/plugins/plugins.css': path.resolve(__dirname, 'node_modules/luckysheet/dist/plugins/plugins.css'),
      'luckysheet/dist/css/luckysheet.css': path.resolve(__dirname, 'node_modules/luckysheet/dist/css/luckysheet.css'),
      'luckysheet/dist/assets/iconfont/iconfont.css': path.resolve(__dirname, 'node_modules/luckysheet/dist/assets/iconfont/iconfont.css'),
    },
  },
})
