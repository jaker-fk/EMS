import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000',
      // 上传文件的静态访问也走代理，开发时可直接预览
      '/uploads': 'http://localhost:8000',
    },
  },
  build: {
    // Element Plus 目前是整体引入（体积集中在 element chunk，可长期缓存），
    // 后续若改成按需引入，可把这里调回 500
    chunkSizeWarningLimit: 1200,
    rollupOptions: {
      output: {
        // 把体积较大的三方库拆出来，业务 chunk 更小、缓存命中率更高
        manualChunks: {
          vue: ['vue', 'vue-router', 'pinia'],
          element: ['element-plus', '@element-plus/icons-vue'],
        },
      },
    },
  },
})
