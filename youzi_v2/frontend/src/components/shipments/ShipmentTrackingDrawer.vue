<script setup lang="ts">
import { NDrawer, NTag } from 'naive-ui'
import { computed } from 'vue'
import ShipmentExceptionHistory from '@/components/shipments/ShipmentExceptionHistory.vue'
import ShipmentLastMileHeader from '@/components/shipments/ShipmentLastMileHeader.vue'
import ShipmentTrackingPanel from '@/components/shipments/ShipmentTrackingPanel.vue'
import LastMileBadge from '@/components/common/LastMileBadge.vue'
import VipStarBadge from '@/components/common/VipStarBadge.vue'
import type { Shipment } from '@/types/shipment'
import { hasLastMileTracking } from '@/utils/lastMileTracking'

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
          <span class="font-mono text-base font-semibold text-[var(--color-fg-emphasis)]">{{ shipment.shipmentNo }}</span>
          <VipStarBadge v-if="shipment.isVip" size="md" />
          <LastMileBadge v-if="hasLastMileTracking(shipment.trackingNumber)" size="md" />
          <NTag
            v-if="shipment.statusCode"
            size="small"
            :bordered="false"
          >
            {{ statusLabel[shipment.statusCode] || shipment.statusCode }}
          </NTag>
        </div>
        <div v-if="shipment.customer" class="mt-1 truncate text-xs text-[var(--color-muted)]">
          {{ shipment.customer }}
          <span v-if="shipment.carrierCode" class="opacity-80"> · {{ shipment.carrierCode }}</span>
        </div>
      </div>
      <span v-else class="text-[var(--color-fg-emphasis)]">{{ title }}</span>
    </template>

    <div v-if="shipment" class="flex min-h-0 flex-col">
      <ShipmentLastMileHeader class="shrink-0" :shipment="shipment" />
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
.shipment-tracking-drawer :deep(.n-drawer-header) {
  padding-bottom: 12px;
}

.shipment-tracking-drawer :deep(.n-drawer-body-content-wrapper) {
  padding: 0 16px 20px;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
</style>
