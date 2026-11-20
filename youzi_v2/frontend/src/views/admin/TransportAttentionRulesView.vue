<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { NButton, NInputNumber, NSpin, useMessage } from 'naive-ui'
import { api } from '@/api/client'

const message = useMessage()
const busy = ref(false)
const rules = ref<Record<string, [number, number]>>({})
const labels: Record<string, string> = {
  WAREHOUSE_NO_DEPARTURE: '入库后未安排开船',
  ARRIVAL_NO_DELIVERY: '到港后未送仓',
  DEST_WAREHOUSE_NO_DISPATCH: '到中转仓后未派送',
  INTERNAL_TRACKING_STALE: '内部轨迹未更新',
}
onMounted(async () => {
  busy.value = true
  try { rules.value = await api('/api/v1/shipment-sla-alerts/attention-rules') }
  catch (e) { message.error(e instanceof Error ? e.message : '加载失败') }
  finally { busy.value = false }
})
async function save() {
  if (Object.keys(rules.value).length !== 4) return
  if (Object.values(rules.value).some(([minor, major]) => minor == null || major == null || minor >= major)) {
    message.warning('主要关注天数须大于次要关注'); return
  }
  busy.value = true
  try {
    const result = await api<{ scan: { skipped: boolean } }>('/api/v1/shipment-sla-alerts/attention-rules', { method: 'PUT', body: rules.value })
    message.success(result.scan.skipped ? '规则已保存，当前扫描正在运行，请稍后在异常跟踪中重新扫描' : '已保存并重新计算运输关注')
  } catch (e) { message.error(e instanceof Error ? e.message : '保存失败') }
  finally { busy.value = false }
}
</script>

<template>
  <div class="p-5 space-y-5">
    <div class="flex items-center justify-between">
      <h1 class="page-h2">后台管理 · 时效规则</h1>
      <NButton type="primary" :loading="busy" @click="save">保存并重新计算</NButton>
    </div>
    <p class="text-sm text-secondary">统一按自然日计算，超过阈值才进入对应等级。主要关注覆盖次要关注；有未关闭人工异常的运单不进入运输关注。</p>
    <NSpin :show="busy">
      <div class="panel p-4 space-y-4">
        <div class="grid grid-cols-3 gap-4 text-sm font-medium"><span>关注规则</span><span>次要关注：超过天数</span><span>主要关注：超过天数</span></div>
        <div v-for="(pair, key) in rules" :key="key" class="grid grid-cols-3 items-center gap-4">
          <span>{{ labels[key] || key }}</span>
          <NInputNumber v-model:value="pair[0]" :min="0" :max="364" :precision="0" :disabled="busy" />
          <NInputNumber v-model:value="pair[1]" :min="1" :max="365" :precision="0" :disabled="busy" />
        </div>
      </div>
    </NSpin>
    <p class="text-sm text-secondary">缺少起算时间时不推测时长。内部轨迹只看记录时间，不看承运商轨迹或同步时间。全程运输时效继续在渠道的时效设置中维护。</p>
  </div>
</template>
