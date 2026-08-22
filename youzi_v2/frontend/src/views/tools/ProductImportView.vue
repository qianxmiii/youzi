<script setup lang="ts">
import { NButton, useMessage } from 'naive-ui'
import { ArrowLeft, Download, Upload } from 'lucide-vue-next'
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { convertProductImport, downloadProductImport } from '@/api/tools'
import { ICON_STROKE } from '@/constants/icons'
import { apiErrorMessage } from '@/utils/apiError'

const message = useMessage()
const router = useRouter()
const fileInputRef = ref<HTMLInputElement | null>(null)
const selectedFile = ref<File | null>(null)
const loading = ref(false)
const taskId = ref<string | null>(null)
const resultFilename = ref('产品导入模版.xls')

function pickFile() {
  fileInputRef.value?.click()
}

function onFileSelected(e: Event) {
  const input = e.target as HTMLInputElement
  selectedFile.value = input.files?.[0] || null
  taskId.value = null
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

async function handleConvert() {
  const file = selectedFile.value
  if (!file) {
    message.warning('请先选择箱单文件（.xls / .xlsx）')
    return
  }
  loading.value = true
  taskId.value = null
  try {
    const res = await convertProductImport(file)
    taskId.value = res.id
    resultFilename.value = res.filename || '产品导入模版.xls'
    message.success('转换成功，可下载产品导入模版')
  } catch (e) {
    message.error(apiErrorMessage(e, '转换失败'))
  } finally {
    loading.value = false
  }
}

async function handleDownload() {
  if (!taskId.value) {
    message.warning('请先完成转换')
    return
  }
  loading.value = true
  try {
    const { blob, filename } = await downloadProductImport(taskId.value)
    downloadBlob(blob, filename || resultFilename.value)
    message.success('已开始下载')
  } catch (e) {
    message.error(apiErrorMessage(e, '下载失败'))
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
      <h1 class="page-h2">箱单转产品导入</h1>
      <p class="page-subtitle mt-1">
        上传客户箱单发票（.xls / .xlsx），按系统产品导入模板字段映射生成可导入的 .xls
      </p>
    </div>

    <section class="panel max-w-2xl space-y-5 p-4">
      <div>
        <h2 class="mb-2 text-sm font-semibold text-[var(--color-fg-emphasis)]">输入</h2>
        <div class="mb-1.5 text-sm text-[var(--color-fg-secondary)]">箱单文件</div>
        <div class="flex flex-wrap items-center gap-2">
          <NButton size="small" class="cursor-pointer" :disabled="loading" @click="pickFile">
            <template #icon>
              <Upload class="h-3.5 w-3.5" :stroke-width="ICON_STROKE" />
            </template>
            选择箱单
          </NButton>
          <span class="text-sm text-[var(--color-fg-secondary)]">
            {{ selectedFile?.name || '未选择（.xls / .xlsx，≤30MB）' }}
          </span>
        </div>
        <input
          ref="fileInputRef"
          type="file"
          class="hidden"
          accept=".xls,.xlsx,.xlsm"
          @change="onFileSelected"
        />
      </div>

      <div class="flex flex-wrap items-center gap-2">
        <NButton
          type="primary"
          size="small"
          class="cursor-pointer"
          :loading="loading"
          :disabled="!selectedFile || loading"
          @click="handleConvert"
        >
          上传并转换
        </NButton>
        <NButton
          size="small"
          class="cursor-pointer"
          :disabled="!taskId || loading"
          @click="handleDownload"
        >
          <template #icon>
            <Download class="h-3.5 w-3.5" :stroke-width="ICON_STROKE" />
          </template>
          下载产品导入模版
        </NButton>
      </div>

      <p v-if="taskId" class="text-sm text-[var(--color-fg-secondary)]">
        已生成：{{ resultFilename }}
      </p>
    </section>

    <section class="panel max-w-2xl space-y-2 p-4 text-sm text-[var(--color-fg-secondary)]">
      <h2 class="text-sm font-semibold text-[var(--color-fg-emphasis)]">说明</h2>
      <ul class="list-disc space-y-1 pl-5">
        <li>箱单需含：英文品名、中文品名、件数、申报总数量、单价、材质、用途、海关编码、长宽高、毛重等</li>
        <li>件数支持 <code>24CTNS</code> 写法；单箱数量 / 单箱重按申报总数量÷件数、毛重÷件数计算</li>
        <li>产品导入模板取自 <code>tools/product_import/samples</code>；字段映射见 <code>field_mapping.json</code></li>
      </ul>
    </section>
  </div>
</template>
