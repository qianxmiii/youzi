<script setup lang="ts">
import { NButton, NDataTable, useDialog, useMessage, type DataTableColumns } from 'naive-ui'
import { ArrowLeft, FolderOpen, Upload } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { parseShipmentFileRenameExcel, type ShipmentFileRenameParseResult } from '@/api/tools'
import { ICON_STROKE } from '@/constants/icons'
import { apiErrorMessage } from '@/utils/apiError'
import {
  applyRenamePlans,
  buildRenamePlans,
  listDirectoryFiles,
  supportsDirectoryPicker,
  type RenamePlanItem,
} from '@/utils/shipmentFileRename'

const message = useMessage()
const dialog = useDialog()
const router = useRouter()

const excelInputRef = ref<HTMLInputElement | null>(null)
const excelFile = ref<File | null>(null)
const parseResult = ref<ShipmentFileRenameParseResult | null>(null)
const dirHandle = ref<FileSystemDirectoryHandle | null>(null)
const dirLabel = ref('')
const plans = ref<RenamePlanItem[]>([])
const unmatchedExcel = ref<string[]>([])
const parsing = ref(false)
const renaming = ref(false)
const lastSummary = ref<{ ok: number; failed: number } | null>(null)

const fsSupported = supportsDirectoryPicker()

const readyCount = computed(() => plans.value.filter((p) => p.status === 'ready').length)

const statusLabel: Record<RenamePlanItem['status'], string> = {
  ready: '将处理',
  'skip-same': '已是目标名',
  conflict: '目标名冲突',
  'missing-excel': 'Excel 无此单',
}

const columns: DataTableColumns<RenamePlanItem> = [
  { title: '当前路径', key: 'sourcePath', ellipsis: { tooltip: true } },
  {
    title: '目标目录',
    key: 'folderName',
    width: 120,
    ellipsis: { tooltip: true },
    render: (row) => row.folderName || '（根目录）',
  },
  { title: '目标路径', key: 'targetPath', ellipsis: { tooltip: true } },
  {
    title: '状态',
    key: 'status',
    width: 110,
    render: (row) => statusLabel[row.status],
  },
]

function pickExcel() {
  excelInputRef.value?.click()
}

async function onExcelSelected(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0] || null
  input.value = ''
  excelFile.value = file
  parseResult.value = null
  plans.value = []
  unmatchedExcel.value = []
  lastSummary.value = null
  if (!file) return
  parsing.value = true
  try {
    parseResult.value = await parseShipmentFileRenameExcel(file)
    if (parseResult.value.errors?.length) {
      message.warning(`已解析 ${parseResult.value.total} 条，有 ${parseResult.value.errors.length} 条提示`)
    } else {
      message.success(`已解析 ${parseResult.value.total} 条运单`)
    }
    await rebuildPlans()
  } catch (err) {
    message.error(apiErrorMessage(err, '解析 Excel 失败'))
  } finally {
    parsing.value = false
  }
}

async function pickFolder() {
  if (!fsSupported) {
    message.error('当前浏览器不支持选择文件夹，请使用 Chrome / Edge')
    return
  }
  try {
    const picker = (
      window as unknown as Window & {
        showDirectoryPicker: (opts?: { mode?: 'read' | 'readwrite' }) => Promise<FileSystemDirectoryHandle>
      }
    ).showDirectoryPicker
    const handle = await picker({ mode: 'readwrite' })
    dirHandle.value = handle
    dirLabel.value = handle.name
    lastSummary.value = null
    await rebuildPlans()
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') return
    message.error(err instanceof Error ? err.message : '选择文件夹失败')
  }
}

async function rebuildPlans() {
  if (!dirHandle.value || !parseResult.value) {
    plans.value = []
    unmatchedExcel.value = []
    return
  }
  const files = await listDirectoryFiles(dirHandle.value)
  const built = buildRenamePlans(files, parseResult.value.items)
  plans.value = built.plans
  unmatchedExcel.value = built.unmatchedExcel
}

function confirmRename() {
  if (!dirHandle.value) {
    message.warning('请先选择文件夹')
    return
  }
  if (!readyCount.value) {
    message.warning('没有可重命名的文件')
    return
  }
  dialog.warning({
    title: '确认重命名',
            content: `将处理 ${readyCount.value} 个文件（含全部子文件夹；可按 Excel 文件夹名归入子目录），且不可撤销。是否继续？`,
            positiveText: '确认',
    negativeText: '取消',
    onPositiveClick: () => {
      void doRename()
    },
  })
}

async function doRename() {
  if (!dirHandle.value) return
  renaming.value = true
  try {
    const result = await applyRenamePlans(dirHandle.value, plans.value)
    lastSummary.value = { ok: result.ok, failed: result.failed.length }
    if (result.failed.length) {
      message.warning(`成功 ${result.ok}，失败 ${result.failed.length}`)
    } else {
      message.success(`已重命名 ${result.ok} 个文件`)
    }
    await rebuildPlans()
  } catch (err) {
    message.error(err instanceof Error ? err.message : '重命名失败')
  } finally {
    renaming.value = false
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
      <h1 class="page-h2">运单文件重命名</h1>
      <p class="page-subtitle mt-1">
        导入含运单号/国家/仓库代码（无则邮编）/件数的 Excel，递归扫描所选文件夹及子文件夹，
        将以运单号命名的文件改为「运单号-国家-仓库代码或邮编-件数」
      </p>
    </div>

    <section class="panel max-w-3xl space-y-5 p-4">
      <div>
        <h2 class="mb-2 text-sm font-semibold text-[var(--color-fg-emphasis)]">输入</h2>
        <div class="space-y-3">
          <div>
            <div class="mb-1.5 text-sm text-[var(--color-fg-secondary)]">Excel 文件</div>
            <div class="flex flex-wrap items-center gap-2">
              <NButton size="small" class="cursor-pointer" :disabled="parsing || renaming" @click="pickExcel">
                <template #icon>
                  <Upload class="h-3.5 w-3.5" :stroke-width="ICON_STROKE" />
                </template>
                选择 Excel
              </NButton>
              <span class="text-sm text-[var(--color-fg-secondary)]">
                {{ excelFile?.name || '未选择（需含：运单号、国家、仓库代码或邮编、件数；可选文件夹名）' }}
              </span>
            </div>
            <input
              ref="excelInputRef"
              type="file"
              class="hidden"
              accept=".xls,.xlsx,.xlsm"
              @change="onExcelSelected"
            />
          </div>
          <div>
            <div class="mb-1.5 text-sm text-[var(--color-fg-secondary)]">目标文件夹</div>
            <div class="flex flex-wrap items-center gap-2">
              <NButton
                size="small"
                class="cursor-pointer"
                :disabled="!fsSupported || parsing || renaming"
                @click="pickFolder"
              >
                <template #icon>
                  <FolderOpen class="h-3.5 w-3.5" :stroke-width="ICON_STROKE" />
                </template>
                选择文件夹
              </NButton>
              <span class="text-sm text-[var(--color-fg-secondary)]">
                {{ dirLabel || (fsSupported ? '未选择' : '当前浏览器不支持（请用 Chrome / Edge）') }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <div class="flex flex-wrap items-center gap-3">
        <NButton
          type="primary"
          size="small"
          class="cursor-pointer"
          :loading="renaming"
          :disabled="!readyCount || renaming"
          @click="confirmRename"
        >
          开始处理（{{ readyCount }}）
        </NButton>
        <span v-if="parseResult" class="text-sm text-[var(--color-fg-secondary)]">
          Excel {{ parseResult.total }} 条
          <template v-if="unmatchedExcel.length"> · 文件夹缺 {{ unmatchedExcel.length }} 单</template>
        </span>
        <span v-if="lastSummary" class="text-sm text-[var(--color-fg-secondary)]">
          上次：成功 {{ lastSummary.ok }}，失败 {{ lastSummary.failed }}
        </span>
      </div>
    </section>

    <section v-if="plans.length" class="panel min-h-0 flex-1 p-4">
      <h2 class="mb-3 text-sm font-semibold text-[var(--color-fg-emphasis)]">预览</h2>
      <NDataTable
        :columns="columns"
        :data="plans"
        size="small"
        :bordered="false"
        :max-height="420"
        :row-key="(row: RenamePlanItem) => row.sourcePath"
      />
      <ul
        v-if="parseResult?.errors?.length"
        class="mt-3 list-disc space-y-1 pl-5 text-xs text-[var(--color-fg-secondary)]"
      >
        <li v-for="(err, i) in parseResult.errors.slice(0, 8)" :key="i">{{ err }}</li>
      </ul>
    </section>

    <section class="panel max-w-3xl space-y-2 p-4 text-sm text-[var(--color-fg-secondary)]">
      <h2 class="text-sm font-semibold text-[var(--color-fg-emphasis)]">说明</h2>
      <ul class="list-disc space-y-1 pl-5">
        <li>会遍历所选文件夹下的<strong>全部子文件夹</strong>；原文件名（去掉扩展名）须等于 Excel「运单号」</li>
        <li>新文件名格式：<code>运单号-国家-仓库代码-件数.pdf</code>（无仓库代码时用邮编）</li>
        <li>可选列「文件夹名」：有值时归入该子目录；无则在原目录原地改名</li>
        <li>需在 Chrome / Edge 中授权文件夹读写；操作在浏览器本地完成，不上传 PDF</li>
        <li>处理前请先预览；冲突或 Excel 无匹配的文件会跳过</li>
      </ul>
    </section>
  </div>
</template>
