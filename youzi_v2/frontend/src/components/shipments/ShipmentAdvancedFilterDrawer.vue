<script setup lang="ts">
import {
  NButton,
  NCheckbox,
  NDatePicker,
  NDrawer,
  NDrawerContent,
  NInput,
  NSelect,
  NSpace,
} from 'naive-ui'
import type { ShipmentFilterOptions } from '@/api/shipments'
import type { ShipmentAdvancedTimeRanges } from '@/constants/shipmentListFilterMeta'

const show = defineModel<boolean>('show', { default: false })

const filterCarrier = defineModel<string | null>('filterCarrier', { default: null })
const filterCountry = defineModel<string | null>('filterCountry', { default: null })
const filterChannelNameZh = defineModel<string | null>('filterChannelNameZh', { default: null })
const filterChannelCategory = defineModel<string | null>('filterChannelCategory', { default: null })
const filterCustomerNo = defineModel<string>('filterCustomerNo', { default: '' })
const advExactShipmentNo = defineModel<string>('advExactShipmentNo', { default: '' })
const advContainerNos = defineModel<string>('advContainerNos', { default: '' })
const advBillNos = defineModel<string>('advBillNos', { default: '' })
const advCustomerShipmentIds = defineModel<string>('advCustomerShipmentIds', { default: '' })
const searchKeyword = defineModel<string>('searchKeyword', { default: '' })
const filterDestinationPort = defineModel<string | null>('filterDestinationPort', { default: null })
const filterAddressKeyword = defineModel<string | null>('filterAddressKeyword', { default: null })
const filterVesselVoyage = defineModel<string | null>('filterVesselVoyage', { default: null })
const filterVipOnly = defineModel<boolean>('filterVipOnly', { default: false })
const filterException = defineModel<string | null>('filterException', { default: null })
const hasAta = defineModel<boolean>('hasAta', { default: false })
const filterHasException = defineModel<boolean | null>('filterHasException', { default: null })
const filterStaleDays = defineModel<number | null>('filterStaleDays', { default: null })
const filterNoInternalTracking = defineModel<boolean>('filterNoInternalTracking', { default: false })
const filterNoCarrierTracking = defineModel<boolean>('filterNoCarrierTracking', { default: false })
const filterNoZipcode = defineModel<boolean>('filterNoZipcode', { default: false })
const filterHasTrackingNumber = defineModel<boolean>('filterHasTrackingNumber', { default: false })
const filterGroupId = defineModel<string | null>('filterGroupId', { default: null })
const filterGroupNo = defineModel<string | null>('filterGroupNo', { default: null })
const filterRuleType = defineModel<string | null>('filterRuleType', { default: null })
const filterHasGroup = defineModel<boolean | null>('filterHasGroup', { default: null })
const filterPendingTrackingTimeReview = defineModel<boolean>('filterPendingTrackingTimeReview', {
  default: false,
})
const missingEtd = defineModel<boolean>('missingEtd', { default: false })
const missingAtd = defineModel<boolean>('missingAtd', { default: false })
const missingEta = defineModel<boolean>('missingEta', { default: false })
const missingAta = defineModel<boolean>('missingAta', { default: false })
const missingExpectedDelivery = defineModel<boolean>('missingExpectedDelivery', { default: false })
const missingDelivered = defineModel<boolean>('missingDelivered', { default: false })
const notDelivered = defineModel<boolean>('notDelivered', { default: false })
const deliveryRisk = defineModel<string | null>('deliveryRisk', { default: null })
const advancedTimes = defineModel<ShipmentAdvancedTimeRanges>('advancedTimes', { required: true })

defineProps<{
  filterOptions: ShipmentFilterOptions
  carrierOptions: { label: string; value: string }[]
  countryOptions: { label: string; value: string }[]
  channelNameZhOptions: { label: string; value: string }[]
  channelCategoryOptions: { label: string; value: string }[]
  exceptionFilterOptions: { label: string; value: string }[]
  hasExceptionFilterOptions: { label: string; value: string }[]
  staleOptions: { label: string; value: number }[]
  hasGroupFilterOptions: { label: string; value: string }[]
  groupFilterOptions: { label: string; value: string }[]
  ruleTypeFilterOptions: { label: string; value: string }[]
}>()

const emit = defineEmits<{ apply: [] }>()

const deliveryRiskOptions = [
  { label: '即将超时', value: 'warning_soon' },
  { label: '已超时', value: 'overdue' },
  { label: '严重超时', value: 'severe_overdue' },
]

function onHasExceptionChange(val: string | null) {
  filterHasException.value = val === 'yes' ? true : val === 'no' ? false : null
}

function onHasGroupChange(val: string | null) {
  filterHasGroup.value = val === 'yes' ? true : val === 'no' ? false : null
  if (filterHasGroup.value != null) filterGroupId.value = null
}

function onGroupIdChange(val: string | null) {
  filterGroupId.value = val
  if (val) filterHasGroup.value = null
}

function apply() {
  emit('apply')
  show.value = false
}
</script>

<template>
  <NDrawer v-model:show="show" :width="420" placement="right">
    <NDrawerContent title="高级筛选" closable>
      <div class="space-y-5 text-sm">
        <section>
          <p class="mb-2 text-xs font-medium text-[var(--color-muted)]">基础信息</p>
          <NSpace vertical :size="10">
            <NInput
              v-model:value="advExactShipmentNo"
              type="textarea"
              placeholder="运单号（多个用逗号、空格或换行分隔）"
              :autosize="{ minRows: 1, maxRows: 3 }"
              clearable
              size="small"
            />
            <NInput
              v-model:value="advContainerNos"
              type="textarea"
              placeholder="柜号（多个精确匹配）"
              :autosize="{ minRows: 1, maxRows: 3 }"
              clearable
              size="small"
            />
            <NInput
              v-model:value="advBillNos"
              type="textarea"
              placeholder="提单号（多个精确匹配）"
              :autosize="{ minRows: 1, maxRows: 3 }"
              clearable
              size="small"
            />
            <NInput
              v-model:value="advCustomerShipmentIds"
              type="textarea"
              placeholder="货件号（多个精确匹配）"
              :autosize="{ minRows: 1, maxRows: 3 }"
              clearable
              size="small"
            />
            <NInput
              v-model:value="filterCustomerNo"
              type="textarea"
              placeholder="客户编号（多个精确匹配）"
              :autosize="{ minRows: 1, maxRows: 3 }"
              clearable
              size="small"
            />
            <NInput v-model:value="searchKeyword" placeholder="关键词：供应商、品名、地址等" clearable size="small" />
            <NSelect v-model:value="filterCountry" :options="countryOptions" placeholder="国家/地区" clearable filterable size="small" />
            <NInput v-model:value="filterDestinationPort" placeholder="目的港" clearable size="small" />
            <NInput v-model:value="filterAddressKeyword" placeholder="仓库 / 地址关键词" clearable size="small" />
            <NSelect v-model:value="filterChannelNameZh" :options="channelNameZhOptions" placeholder="渠道（中文名）" clearable filterable size="small" />
            <NSelect v-model:value="filterChannelCategory" :options="channelCategoryOptions" placeholder="渠道大类" clearable size="small" />
            <NSelect v-model:value="filterCarrier" :options="carrierOptions" placeholder="承运商" clearable filterable size="small" />
            <NInput v-model:value="filterVesselVoyage" placeholder="船名航次" clearable size="small" />
            <NCheckbox v-model:checked="filterVipOnly" size="small">仅 VIP</NCheckbox>
          </NSpace>
        </section>

        <section>
          <p class="mb-2 text-xs font-medium text-[var(--color-muted)]">时间节点</p>
          <NSpace vertical :size="10">
            <div v-for="item in [
              { label: 'ETD', key: 'etd' },
              { label: 'ATD', key: 'atd' },
              { label: 'ETA', key: 'eta' },
              { label: 'ATA', key: 'ata' },
              { label: '预计送仓', key: 'expectedDelivery' },
              { label: '签收', key: 'delivered' },
              { label: '创建', key: 'created' },
              { label: '更新', key: 'updated' },
            ]" :key="item.key">
              <p class="mb-1 text-[10px] text-[var(--color-muted)]">{{ item.label }}</p>
              <NDatePicker
                v-model:value="advancedTimes[item.key as keyof ShipmentAdvancedTimeRanges]"
                type="daterange"
                clearable
                size="small"
                class="w-full"
              />
            </div>
          </NSpace>
        </section>

        <section>
          <p class="mb-2 text-xs font-medium text-[var(--color-muted)]">轨迹与状态</p>
          <NSpace vertical :size="10">
            <NSelect v-model:value="filterStaleDays" :options="staleOptions" :disabled="filterNoInternalTracking" placeholder="内部轨迹停滞" clearable size="small" />
            <NCheckbox v-model:checked="filterNoInternalTracking" size="small">内部无轨迹</NCheckbox>
            <NCheckbox v-model:checked="filterNoCarrierTracking" size="small">承运商无轨迹</NCheckbox>
            <NCheckbox v-model:checked="hasAta" size="small">已到港</NCheckbox>
            <NCheckbox v-model:checked="notDelivered" size="small">未签收</NCheckbox>
            <NCheckbox v-model:checked="missingEtd" size="small">缺 ETD</NCheckbox>
            <NCheckbox v-model:checked="missingAtd" size="small">缺 ATD</NCheckbox>
            <NCheckbox v-model:checked="missingEta" size="small">缺 ETA</NCheckbox>
            <NCheckbox v-model:checked="missingAta" size="small">缺 ATA</NCheckbox>
            <NCheckbox v-model:checked="missingExpectedDelivery" size="small">缺预计送仓</NCheckbox>
            <NCheckbox v-model:checked="missingDelivered" size="small">缺签收时间</NCheckbox>
            <NCheckbox v-model:checked="filterNoZipcode" size="small">无邮编</NCheckbox>
            <NCheckbox v-model:checked="filterHasTrackingNumber" size="small">有转单号（快递派）</NCheckbox>
          </NSpace>
        </section>

        <section>
          <p class="mb-2 text-xs font-medium text-[var(--color-muted)]">异常与审批</p>
          <NSpace vertical :size="10">
            <NSelect v-model:value="deliveryRisk" :options="deliveryRiskOptions" placeholder="送仓时效风险" clearable size="small" />
            <NSelect
              :value="filterHasException === true ? 'yes' : filterHasException === false ? 'no' : null"
              :options="hasExceptionFilterOptions"
              placeholder="是否有异常"
              clearable
              size="small"
              @update:value="onHasExceptionChange"
            />
            <NSelect v-model:value="filterException" :options="exceptionFilterOptions" placeholder="异常类型" clearable size="small" />
            <NCheckbox v-model:checked="filterPendingTrackingTimeReview" size="small">待签收时间审批</NCheckbox>
          </NSpace>
        </section>

        <section>
          <p class="mb-2 text-xs font-medium text-[var(--color-muted)]">分组与业务</p>
          <NSpace vertical :size="10">
            <NSelect
              :value="filterHasGroup === true ? 'yes' : filterHasGroup === false ? 'no' : null"
              :options="hasGroupFilterOptions"
              placeholder="是否已分组"
              clearable
              size="small"
              @update:value="onHasGroupChange"
            />
            <NInput v-model:value="filterGroupNo" placeholder="分组编号" clearable size="small" />
            <NSelect
              :value="filterGroupId"
              :options="groupFilterOptions"
              placeholder="指定分组"
              clearable
              filterable
              size="small"
              @update:value="onGroupIdChange"
            />
            <NSelect v-model:value="filterRuleType" :options="ruleTypeFilterOptions" placeholder="分组规则" clearable size="small" />
          </NSpace>
        </section>
      </div>
      <template #footer>
        <NSpace justify="end">
          <NButton size="small" type="primary" @click="apply">应用筛选</NButton>
        </NSpace>
      </template>
    </NDrawerContent>
  </NDrawer>
</template>
