<script setup lang="ts">
import { NButton, NSpin, useMessage } from 'naive-ui'
import { computed, onMounted, ref, watch } from 'vue'
import { getShipmentExceptionEvents } from '@/api/shipments'
import type { Shipment, ShipmentExceptionEvent } from '@/types/shipment'

const props = withDefaults(
  defineProps<{
    shipmentId: string
    shipment?: Shipment | null
    labelByCode?: Record<string, string>
    mode?: 'default' | 'drawer'
  }>(),
  { mode: 'default' },
)

const message = useMessage()

function codeLabel(code: string) {
  return props.labelByCode?.[code] || code
}

const loading = ref(false)
const items = ref<ShipmentExceptionEvent[]>([])

const openException = computed(() => {
  const code = props.shipment?.exceptionCode?.trim()
  if (!code) return null
  const openEvent = items.value.find((ev) => ev.exceptionCode === code && !ev.closedTime)
  return {
    code,
    label: codeLabel(code),
    note: openEvent?.note || null,
    openedTime: props.shipment?.exceptionOpenedTime || openEvent?.openedTime || null,
  }
})

async function load() {
  loading.value = true
  try {
    const res = await getShipmentExceptionEvents(props.shipmentId, { limit: 30 })
    items.value = res.items
  } finally {
    loading.value = false
  }
}

function buildContactCopyText(): string {
  const s = props.shipment
  const ex = openException.value
  if (!s) return ''
  const lines: string[] = ['运单号：' + s.shipmentNo]
  if (s.customer) lines.push('客户：' + s.customer)
  if (s.customerNo) lines.push('客户订单号：' + s.customerNo)
  if (ex) lines.push('异常：' + ex.label)
  if (ex?.note) lines.push('备注：' + ex.note)
  return lines.join('\n')
}

async function contactSender() {
  const text = buildContactCopyText()
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
    message.success('已复制联系信息，可粘贴至邮件或 IM')
  } catch {
    message.error('复制失败')
  }
}

onMounted(load)
watch(() => props.shipmentId, load)
</script>

<template>
  <!-- Drawer：设计稿异常卡片 -->
  <div v-if="mode === 'drawer' && openException" class="abnormal-section">
    <h3 class="section-label">
      Abnormal Status <span class="section-label-zh">（异常信息）</span>
    </h3>
    <NSpin :show="loading">
      <div class="abnormal-card">
        <div class="flex gap-3">
          <div class="abnormal-icon shrink-0" aria-hidden="true">
            <svg viewBox="0 0 20 20" fill="none" class="h-5 w-5">
              <path
                d="M10 3.5 17.5 16.5H2.5L10 3.5Z"
                stroke="currentColor"
                stroke-width="1.25"
                stroke-linejoin="round"
              />
              <path d="M10 8v4M10 14.5v.5" stroke="currentColor" stroke-width="1.25" stroke-linecap="round" />
            </svg>
          </div>
          <div class="min-w-0 flex-1">
            <div class="abnormal-title">
              Issue: {{ openException.label }}
            </div>
            <p v-if="openException.note" class="abnormal-desc">
              {{ openException.note }}
            </p>
            <p v-else class="abnormal-desc">
              The shipment has an open exception. Please follow up with the sender.
            </p>
          </div>
        </div>
        <NButton quaternary class="abnormal-action mt-4 w-full" @click="contactSender">
          <span class="inline-flex items-center justify-center gap-2">
            <svg viewBox="0 0 16 16" fill="none" class="h-4 w-4" aria-hidden="true">
              <rect x="2" y="3.5" width="12" height="9" rx="1" stroke="currentColor" stroke-width="1.25" />
              <path d="M2.5 4.5 8 8.5l5.5-4" stroke="currentColor" stroke-width="1.25" stroke-linejoin="round" />
            </svg>
            Contact Sender
          </span>
        </NButton>
      </div>
    </NSpin>
  </div>

  <!-- Default：历史列表 -->
  <div v-else-if="mode === 'default'" class="exception-history-default">
    <div class="mb-2 text-xs font-medium text-secondary">异常记录</div>
    <NSpin :show="loading">
      <div v-if="!loading && items.length === 0" class="text-xs text-muted">暂无异常事件</div>
      <ul v-else class="space-y-2">
        <li
          v-for="ev in items"
          :key="ev.id"
          class="exception-history-item"
        >
          <div class="flex flex-wrap items-center gap-2 text-fg">
            <span class="font-medium">{{ codeLabel(ev.exceptionCode) }}</span>
            <span class="text-muted">{{ ev.durationLabel }}</span>
            <span v-if="!ev.closedTime" class="exception-open-badge rounded px-1.5 py-0.5">进行中</span>
          </div>
          <div class="mt-0.5 text-muted">
            {{ ev.openedTime }}
            <template v-if="ev.closedTime"> → {{ ev.closedTime }}</template>
          </div>
          <div v-if="ev.note" class="mt-0.5 text-secondary">{{ ev.note }}</div>
        </li>
      </ul>
    </NSpin>
  </div>
</template>

<style scoped>
.abnormal-section {
  border-top: 1px solid var(--color-border);
  padding-top: 1.125rem;
  margin-top: 0;
}

.section-label {
  margin-bottom: 0.75rem;
  font-size: 0.6875rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--color-muted);
}

.section-label-zh {
  text-transform: none;
  letter-spacing: normal;
  font-weight: 600;
}

.abnormal-card {
  border-radius: 0.625rem;
  border: 1px solid rgb(191 219 254);
  background: rgb(240 247 255);
  padding: 1rem 1rem 0.875rem;
}

[data-theme='dark'] .abnormal-card {
  border-color: rgb(30 58 138 / 0.55);
  background: rgb(30 58 138 / 0.2);
}

.abnormal-icon {
  color: rgb(220 38 38);
}

.abnormal-title {
  font-size: 0.875rem;
  font-weight: 600;
  line-height: 1.35;
  color: var(--color-fg-emphasis);
}

.abnormal-desc {
  margin-top: 0.375rem;
  font-size: 0.8125rem;
  line-height: 1.55;
  color: var(--color-fg-secondary);
}

.abnormal-action {
  height: 2.5rem !important;
  border: 1px solid rgb(147 197 253) !important;
  border-radius: 0.5rem !important;
  background: rgb(240 247 255) !important;
  color: rgb(37 99 235) !important;
}

.abnormal-action:hover {
  background: rgb(224 242 254) !important;
}

[data-theme='dark'] .abnormal-action {
  border-color: rgb(59 130 246 / 0.45) !important;
  background: rgb(30 58 138 / 0.35) !important;
  color: rgb(147 197 253) !important;
}

[data-theme='dark'] .abnormal-action:hover {
  background: rgb(30 58 138 / 0.5) !important;
}

.exception-open-badge {
  background: var(--tracking-ahead-badge-bg);
  color: var(--tracking-ahead-badge-fg);
}

.exception-history-default {
  margin-top: 0.75rem;
  border-top: 1px solid var(--color-border);
  padding-top: 0.75rem;
}

.text-secondary {
  color: var(--color-fg-secondary);
}

.text-muted {
  color: var(--color-muted);
}

.text-fg {
  color: var(--color-fg);
}

.exception-history-item {
  border-radius: 0.25rem;
  border: 1px solid var(--color-border);
  background: var(--color-btn-ghost-bg);
  padding: 0.375rem 0.5rem;
  font-size: 0.75rem;
}
</style>
