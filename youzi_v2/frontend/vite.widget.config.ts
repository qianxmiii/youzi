import { fileURLToPath, URL } from 'node:url'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

export default defineConfig({
  base: './',
  plugins: [vue()],
  resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
  build: {
    outDir: '../desktop_quote/build',
    emptyOutDir: false,
    rollupOptions: { input: fileURLToPath(new URL('./quote-widget.html', import.meta.url)) },
  },
})
