import { fileURLToPath, URL } from 'node:url'
import tailwindcss from '@tailwindcss/vite'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    // 允许用本机局域网 IP 访问（如 http://192.168.x.x:5173），不仅限 localhost
    host: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:3001',
        changeOrigin: true,
        // DPS 同步等长请求；与前端 ofetch timeout 对齐，避免代理先断连导致 Failed to fetch
        timeout: 600_000,
        proxyTimeout: 600_000,
      },
      '/legacy': {
        target: 'http://127.0.0.1:3001',
        changeOrigin: true,
        timeout: 600_000,
        proxyTimeout: 600_000,
      },
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
})
