import { h, type VNodeChild } from 'vue'
import type { SelectOption, SelectRenderLabel } from 'naive-ui'
import ShipmentGroupTypeIcon from '@/components/shipments/ShipmentGroupTypeIcon.vue'

function typeValue(option: SelectOption | null | undefined): string {
  return String(option?.value ?? '')
}

function typeText(option: SelectOption | null | undefined): string {
  return String(option?.label ?? '')
}

/** 选中态与下拉项共用：仅 render-label，避免 render-option 重复渲染图标 */
export const renderShipmentGroupTypeSelectLabel: SelectRenderLabel = (
  option,
): VNodeChild => {
  if (!option?.value) return typeText(option)
  return h(
    'span',
    { class: 'inline-flex min-w-0 max-w-full items-center gap-1.5' },
    [
      h(ShipmentGroupTypeIcon, {
        type: typeValue(option),
        size: 14,
        class: 'shrink-0 text-current',
      }),
      h('span', { class: 'truncate' }, typeText(option)),
    ],
  )
}
