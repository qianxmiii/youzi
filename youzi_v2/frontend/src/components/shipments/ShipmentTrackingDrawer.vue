<script setup lang="ts">
import { NDrawer, NTag } from 'naive-ui'
import { computed } from 'vue'
import ShipmentExceptionHistory from '@/components/shipments/ShipmentExceptionHistory.vue'
import ShipmentTrackingPanel from '@/components/shipments/ShipmentTrackingPanel.vue'
import VipStarBadge from '@/components/common/VipStarBadge.vue'
import type { Shipment } from '@/types/shipment'

const props = defineProps<{
  show: boolean
  shipment: Shipment | null
  initialTab?: 'internal' | 'carrier'
  exceptionLabelByCode?: Record<string, string>
}>()

const emit = defineEmits<{
  'update:show': [value: boolean]
}>()

const showModel = computed({
  get: () => props.show,
  set: (v: boolean) => emit('update:show', v),
})

const statusLabel: Record<string, string> = {
  IN_TRANSIT: '转运中',
  DELIVERED: '已签收',
  INSPECTION: '查验',
  UNKNOWN: '未知',
}

const title = computed(() => props.shipment?.shipmentNo || '运单轨迹')

</script>

<template>
  <NDrawer
    v-model:show="showModel"
    :width="520"
    placement="right"
    :auto-focus="false"
    class="shipment-tracking-drawer"
  >
    <template #header>
      <div v-if="shipment" class="min-w-0 pr-2">
        <div class="flex flex-wrap items-center gap-2">
          <span class="font-mono text-base font-semibold text-white">{{ shipment.shipmentNo }}</span>
          <VipStarBadge v-if="shipment.isVip" size="md" />
          <NTag
            v-if="shipment.statusCode"
            size="small"
            :bordered="false"
          >
            {{ statusLabel[shipment.statusCode] || shipment.statusCode }}
          </NTag>
        </div>
        <div v-if="shipment.customer" class="mt-1 truncate text-xs text-zinc-500">
          {{ shipment.customer }}
          <span v-if="shipment.carrierCode" class="text-zinc-600"> · {{ shipment.carrierCode }}</span>
        </div>
      </div>
      <span v-else class="text-white">{{ title }}</span>
    </template>

    <div v-if="shipment" class="flex min-h-0 flex-col">
      <ShipmentTrackingPanel
        :key="`${shipment.id}-${initialTab || 'internal'}`"
        :shipment-id="shipment.id"
        mode="drawer"
        :initial-tab="initialTab || 'internal'"
      />
      <ShipmentExceptionHistory
        :shipment-id="shipment.id"
        :label-by-code="exceptionLabelByCode"
      />
    </div>
  </NDrawer>
</template>

<style scoped>
.shipment-tracking-drawer :deep(.n-drawer-body-content-wrapper) {
  padding: 0 16px 20px;
}

</style>
