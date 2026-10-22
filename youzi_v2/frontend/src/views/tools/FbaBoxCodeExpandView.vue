<script setup lang="ts">
import { NButton, NInput, NInputNumber, useMessage } from 'naive-ui'
import { ArrowLeft, Copy, Download } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ICON_STROKE } from '@/constants/icons'
import { buildFbaBoxCodesXlsx } from '@/utils/fbaBoxCodeExcel'
import { generateFbaBoxCodes } from '@/utils/fbaBoxCodeGenerate'

const message = useMessage()
const router = useRouter()

const prefixLines = ref(`FBA19QH6N50R 3
FBA19QH6NKF8 1
FBA19QH6NVN2 2`)
const namingChar = ref('U')
const suffixDigits = ref(6)

const result = computed(() =>
  generateFbaBoxCodes(prefixLines.value, namingChar.value, suffixDigits.value ?? 6),
)

const outputText = computed(() => result.value.codes.join('\n'))

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

function exportExcel() {
  const codes = result.value.codes
  if (!codes.length) {
    message.warning(result.value.errors[0] || '无可导出内容')
    return
  }
  const bytes = buildFbaBoxCodesXlsx(codes)
  const stamp = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  const name = `FBA箱号展开_${stamp.getFullYear()}${pad(stamp.getMonth() + 1)}${pad(stamp.getDate())}${pad(stamp.getHours())}${pad(stamp.getMinutes())}${pad(stamp.getSeconds())}.xlsx`
  downloadBlob(
    new Blob([bytes], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    }),
    name,
  )
  message.success(`已导出 ${codes.length} 行`)
}

async function copyOutput() {
  const text = outputText.value.trim()
  if (!text) {
    message.warning(result.value.errors[0] || '无可复制内容')
    return
  }
  try {
    await navigator.clipboard.writeText(text)
    message.success(`已复制 ${result.value.codes.length} 行`)
  } catch {
    message.error('复制失败，请检查浏览器权限')
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
      <h1 class="page-h2">FBA 箱号展开</h1>
      <p class="page-subtitle mt-1">
        按「前缀 + 箱数」批量生成
        <code class="text-[var(--color-muted)]">前缀 + 命名符 + 序号</code>
        （如
        <code class="text-[var(--color-muted)]">FBA19QH6N50RU000001</code>
        ）
      </p>
    </div>

    <div class="grid min-h-0 flex-1 gap-4 lg:grid-cols-2">
      <section class="panel flex min-h-0 flex-col gap-3 p-4">
        <h2 class="text-sm font-semibold text-[var(--color-fg-emphasis)]">输入</h2>

        <div>
          <div class="mb-1.5 text-sm text-[var(--color-fg-secondary)]">前缀与箱数（每行一条）</div>
          <NInput
            v-model:value="prefixLines"
            type="textarea"
            :rows="10"
            placeholder="FBA19QH6N50R 3&#10;FBA19QH6NKF8 1"
            class="font-mono text-sm"
          />
        </div>

        <div class="flex flex-wrap gap-3">
          <div class="min-w-[8rem] flex-1">
            <div class="mb-1.5 text-sm text-[var(--color-fg-secondary)]">命名符</div>
            <NInput v-model:value="namingChar" maxlength="8" placeholder="U" />
          </div>
          <div class="min-w-[8rem] flex-1">
            <div class="mb-1.5 text-sm text-[var(--color-fg-secondary)]">箱号尾数（位数）</div>
            <NInputNumber
              v-model:value="suffixDigits"
              :min="1"
              :max="12"
              :show-button="true"
              class="w-full"
            />
          </div>
        </div>

        <p class="text-xs text-[var(--color-muted)]">
          规则：
          <code>前缀</code>
          +
          <code>命名符</code>
          +
          从 1 起、按尾数位数零填充的序号。修改输入后右侧即时更新。
        </p>
      </section>

      <section class="panel flex min-h-0 flex-col gap-3 p-4">
        <div class="flex items-center justify-between gap-2">
          <h2 class="text-sm font-semibold text-[var(--color-fg-emphasis)]">
            生成结果
            <span v-if="result.codes.length" class="font-normal text-[var(--color-muted)]">
              · {{ result.codes.length }} 行
            </span>
          </h2>
          <div class="flex items-center gap-2">
            <NButton size="small" :disabled="!result.codes.length" @click="exportExcel">
              <template #icon>
                <Download class="h-3.5 w-3.5" :stroke-width="ICON_STROKE" />
              </template>
              导出 Excel
            </NButton>
            <NButton size="small" type="primary" :disabled="!result.codes.length" @click="copyOutput">
              <template #icon>
                <Copy class="h-3.5 w-3.5" :stroke-width="ICON_STROKE" />
              </template>
              复制
            </NButton>
          </div>
        </div>

        <ul v-if="result.errors.length" class="space-y-1 text-xs text-amber-700">
          <li v-for="(err, i) in result.errors" :key="i">{{ err }}</li>
        </ul>

        <NInput
          :value="outputText"
          type="textarea"
          :rows="14"
          readonly
          placeholder="生成的箱号将显示在这里"
          class="font-mono text-sm"
        />
      </section>
    </div>
  </div>
</template>
