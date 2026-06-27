<script setup lang="ts">
import { AlertTriangle } from 'lucide-vue-next'
import { NButton, NDatePicker, NSpace, NSpin, useMessage } from 'naive-ui'
import { computed, ref, watch } from 'vue'
import {
  getShipment,
  getShipmentTrackingTimeCandidates,
  reviewTrackingTimeCandidate,
} from '@/api/shipments'
import type { Shipment } from '@/types/shipment'
import type { TrackingTimeCandidate, TrackingTimeReviewAction } from '@/types/trackingTimeWriteback'
import { formatSignedTimeReviewQuestion } from '@/types/trackingTimeWriteback'
import { formatAbsoluteDateTime } from '@/utils/formatDateTime'

const props = defineProps<{
  shipment: Shipment
}>()

const emit = defineEmits<{
  updated: [shipment: Shipment]
}>()

const message = useMessage()
const loading = ref(false)
const reviewing = ref(false)
const manualOpen = ref(false)
const manualAt = ref<number | null>(null)
const candidates = ref<TrackingTimeCandidate[]>([])

const pendingSigned = computed(() =>
  candidates.value.find(
    (item) => item.fieldName === 'signed_time' && item.reviewStatus === 'pending_review',
  ),
)

const reviewQuestion = computed(() =>
  pendingSigned.value
    ? formatSignedTimeReviewQuestion(pendingSigned.value.candidateValue)
    : '',
)

function formatTime(value: string | null | undefined) {
  const text = (value || '').trim()
  if (!text) return '—'
  return formatAbsoluteDateTime(text) || text
}

async function load() {
  loading.value = true
  try {
    const res = await getShipmentTrackingTimeCandidates(props.shipment.id)
    candidates.value = res.items
  } finally {
    loading.value = false
  }
}

async function review(action: TrackingTimeReviewAction, manualValue?: string) {
  const item = pendingSigned.value
  if (!item) return
  reviewing.value = true
  try {
    await reviewTrackingTimeCandidate(item.id, { action, manualValue })
    const labels: Record<string, string> = {
      use_expected_delivery: '已采用预计送仓时间',
      use_signed_track: '已采用签收节点时间',
      manual: '已写入手动签收时间',
      reject: '已暂不处理',
    }
    message.success(labels[action] || '已处理')
    manualOpen.value = false
    manualAt.value = null
    await load()
    emit('updated', await getShipment(props.shipment.id))
  } catch (e) {
    message.error(e instanceof Error ? e.message : '审批失败')
  } finally {
    reviewing.value = false
  }
}

function submitManual() {
  if (manualAt.value == null) {
    message.warning('请选择签收时间')
    return
  }
  const d = new Date(manualAt.value)
  const pad = (n: number) => String(n).padStart(2, '0')
  const manualValue = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
  void review('manual', manualValue)
}

watch(
  () => props.shipment.id,
  () => {
    void load()
  },
  { immediate: true },
)
</script>

<template>
  <section v-if="loading || pendingSigned" class="tracking-time-review">
    <NSpin v-if="loading" size="small" />
    <template v-else-if="pendingSigned">
      <div class="tracking-time-review__head">
        <AlertTriangle class="tracking-time-review__icon" aria-hidden="true" />
        <div>
          <h3 class="tracking-time-review__title">签收时间待确认</h3>
          <p class="tracking-time-review__question">{{ reviewQuestion }}</p>
          <p class="tracking-time-review__reason">{{ pendingSigned.reviewReason }}</p>
        </div>
      </div>
      <dl class="tracking-time-review__meta">
        <div>
          <dt>推荐（预计送仓）</dt>
          <dd>{{ formatTime(pendingSigned.candidateValue) }}</dd>
        </div>
        <div>
          <dt>对照（签收节点）</dt>
          <dd>{{ formatTime(pendingSigned.compareValue) }}</dd>
        </div>
        <div>
          <dt>当前签收时间</dt>
          <dd>{{ formatTime(shipment.deliveredTime) }}</dd>
        </div>
        <div class="tracking-time-review__source">
          <dt>预计送仓轨迹</dt>
          <dd>{{ pendingSigned.sourceTrackDesc || '—' }}</dd>
        </div>
        <div class="tracking-time-review__source">
          <dt>签收轨迹</dt>
          <dd>{{ pendingSigned.compareSourceTrackDesc || '—' }}</dd>
        </div>
      </dl>
      <NSpace vertical :size="12">
        <NSpace wrap>
          <NButton
            type="primary"
            size="small"
            :loading="reviewing"
            @click="review('use_expected_delivery')"
          >
            采用预计送仓
          </NButton>
          <NButton size="small" :loading="reviewing" @click="review('use_signed_track')">
            使用签收节点
          </NButton>
          <NButton size="small" :loading="reviewing" @click="manualOpen = !manualOpen">
            手动填写
          </NButton>
          <NButton size="small" :loading="reviewing" @click="review('reject')">暂不处理</NButton>
        </NSpace>
        <div v-if="manualOpen" class="tracking-time-review__manual">
          <NDatePicker
            v-model:value="manualAt"
            type="datetime"
            clearable
            class="w-full max-w-xs"
            format="yyyy-MM-dd HH:mm:ss"
          />
          <NButton size="small" type="primary" class="mt-2" :loading="reviewing" @click="submitManual">
            确认写入
          </NButton>
        </div>
      </NSpace>
    </template>
  </section>
</template>

<style scoped>
.tracking-time-review {
  margin-bottom: 1rem;
  border: 1px solid rgb(254 215 170);
  border-radius: 0.75rem;
  background: rgb(255 247 237 / 0.65);
  padding: 0.875rem 1rem;
}

[data-theme='dark'] .tracking-time-review {
  border-color: rgb(120 53 15 / 0.55);
  background: rgb(120 53 15 / 0.18);
}

.tracking-time-review__head {
  display: flex;
  gap: 0.625rem;
  align-items: flex-start;
}

.tracking-time-review__icon {
  width: 1.125rem;
  height: 1.125rem;
  flex-shrink: 0;
  margin-top: 0.125rem;
  color: rgb(234 88 12);
}

.tracking-time-review__title {
  margin: 0;
  font-size: 0.875rem;
  font-weight: 700;
  color: var(--color-fg-emphasis);
}

.tracking-time-review__question {
  margin: 0.25rem 0 0;
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--color-fg-emphasis);
}

.tracking-time-review__reason {
  margin: 0.25rem 0 0;
  font-size: 0.8125rem;
  color: var(--color-muted);
}

.tracking-time-review__meta {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.75rem 1rem;
  margin: 0.875rem 0;
}

.tracking-time-review__meta dt {
  font-size: 0.6875rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--color-muted);
}

.tracking-time-review__meta dd {
  margin: 0.25rem 0 0;
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--color-fg-emphasis);
}

.tracking-time-review__source {
  grid-column: 1 / -1;
}

.tracking-time-review__source dd {
  font-weight: 500;
  line-height: 1.45;
}

.tracking-time-review__manual {
  padding-top: 0.25rem;
}
</style>
