<script setup lang="ts">
import { NButton, NInput, NProgress, useMessage } from 'naive-ui'
import { ArrowLeft, Download, Upload } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { exportImageLinkZip, type ImageZipJob } from '@/api/tools'
import { ICON_STROKE } from '@/constants/icons'

const message = useMessage()
const router = useRouter()
const fileInputRef = ref<HTMLInputElement | null>(null)
const selectedFile = ref<File | null>(null)
const column = ref('P')
const loading = ref(false)
const progress = ref<ImageZipJob | null>(null)
const lastStats = ref<{ total: number; downloaded: number; failed: number } | null>(null)

const progressPercent = computed(() => {
  const p = progress.value
  if (!p || !p.total) return 0
  return Math.min(100, Math.round((p.done / p.total) * 100))
})

const progressText = computed(() => {
  const p = progress.value
  if (!p) return ''
  if (p.status === 'pending') return `已解析 ${p.total} 条链接，准备下载…`
  if (p.status === 'running') {
    return `正在下载 ${p.done}/${p.total}${p.failed ? `（失败 ${p.failed}）` : ''}…`
  }
  if (p.status === 'done') return '打包完成，正在保存…'
  return p.error || '失败'
})

function pickFile() {
  fileInputRef.value?.click()
}

function onFileSelected(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0] || null
  selectedFile.value = file
  lastStats.value = null
  progress.value = null
  input.value = ''
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

async function handleExport() {
  const file = selectedFile.value
  if (!file) {
    message.warning('请先选择 Excel 文件（.xls / .xlsx）')
    return
  }
  const col = column.value.trim().toUpperCase() || 'P'
  if (!/^[A-Z]+$/.test(col)) {
    message.warning('列字母无效，请填写如 P')
    return
  }
  loading.value = true
  lastStats.value = null
  progress.value = null
  try {
    const result = await exportImageLinkZip(file, col, (job) => {
      progress.value = job
    })
    downloadBlob(result.blob, result.filename)
    lastStats.value = {
      total: result.total,
      downloaded: result.downloaded,
      failed: result.failed,
    }
    if (result.failed > 0) {
      message.warning(
        `已打包 ${result.downloaded}/${result.total} 张，失败 ${result.failed} 张`,
      )
    } else {
      message.success(`已打包 ${result.downloaded} 张图片`)
    }
  } catch (e) {
    message.error(e instanceof Error ? e.message : '打包失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="flex h-full min-h-0 w-full flex-col gap-4 overflow-y-auto scrollbar-subtle">
    <div>
      <button
        type="button"
        class="mb-2 inline-flex cursor-pointer items-center gap-1 border-0 bg-transparent p-0 text-xs text-[var(--color-accent-text)] hover:underline"
        @click="router.push('/tools')"
      >
        <ArrowLeft class="h-3.5 w-3.5" :stroke-width="ICON_STROKE" aria-hidden="true" />
        返回工具中心
      </button>
      <h1 class="page-h2">标签图片打包</h1>
      <p class="page-subtitle mt-1">
        上传 Excel，读取指定列图片链接，批量下载并打成 ZIP（不修改业务库数据）
      </p>
    </div>

    <section class="panel max-w-2xl space-y-5 p-4">
      <div>
        <h2 class="mb-2 text-sm font-semibold text-[var(--color-fg-emphasis)]">输入</h2>
        <div class="space-y-3">
          <div>
            <div class="mb-1.5 text-sm text-[var(--color-fg-secondary)]">Excel 文件</div>
            <div class="flex flex-wrap items-center gap-2">
              <NButton size="small" class="cursor-pointer" :disabled="loading" @click="pickFile">
                <template #icon>
                  <Upload class="h-4 w-4" :stroke-width="ICON_STROKE" />
                </template>
                选择文件
              </NButton>
              <span class="text-sm text-[var(--color-muted)]">
                {{ selectedFile?.name || '未选择（.xls / .xlsx，≤30MB）' }}
              </span>
              <input
                ref="fileInputRef"
                type="file"
                accept=".xls,.xlsx,.xlsm"
                class="hidden"
                @change="onFileSelected"
              />
            </div>
          </div>
          <div class="max-w-[8rem]">
            <div class="mb-1.5 text-sm text-[var(--color-fg-secondary)]">链接所在列</div>
            <NInput
              v-model:value="column"
              size="small"
              placeholder="P"
              maxlength="3"
              :disabled="loading"
            />
          </div>
        </div>
      </div>

      <div>
        <h2 class="mb-2 text-sm font-semibold text-[var(--color-fg-emphasis)]">执行</h2>
        <div class="flex flex-wrap items-center gap-3">
          <NButton
            type="primary"
            size="small"
            class="cursor-pointer"
            :loading="loading"
            :disabled="!selectedFile || loading"
            @click="handleExport"
          >
            <template #icon>
              <Download class="h-4 w-4" :stroke-width="ICON_STROKE" />
            </template>
            下载并打包
          </NButton>
        </div>
        <div
          v-if="loading || progress"
          class="mt-3 space-y-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-btn-ghost-bg)] px-3 py-3"
        >
          <div class="text-sm text-[var(--color-fg-secondary)]">{{ progressText || '处理中…' }}</div>
          <NProgress
            type="line"
            :percentage="progressPercent"
            :processing="loading && progressPercent < 100"
            indicator-placement="inside"
            :height="18"
          />
          <p class="text-xs text-[var(--color-muted)]">
            单张约 1～3MB，外网较慢时整批可能需要数分钟，请勿关闭页面。
          </p>
        </div>
      </div>

      <div v-if="lastStats && !loading">
        <h2 class="mb-2 text-sm font-semibold text-[var(--color-fg-emphasis)]">结果</h2>
        <p class="text-sm text-[var(--color-fg-secondary)]">
          共 {{ lastStats.total }} 条链接 · 成功 {{ lastStats.downloaded }} · 失败
          {{ lastStats.failed }}（ZIP 已开始下载）
        </p>
      </div>

      <div>
        <h2 class="mb-2 text-sm font-semibold text-[var(--color-fg-emphasis)]">使用说明</h2>
        <ul class="list-disc space-y-1 pl-5 text-xs text-[var(--color-muted)]">
          <li>默认读取 <strong>P</strong> 列，跳过表头与空单元格；仅识别 http/https 链接</li>
          <li>单次最多 500 条；上传文件上限 30MB；单图上限 20MB</li>
          <li>同名文件自动加后缀；结果文件名含生成时间</li>
          <li>本工具只下载外链图片，不写入运单等业务数据</li>
        </ul>
      </div>
    </section>
  </div>
</template>
