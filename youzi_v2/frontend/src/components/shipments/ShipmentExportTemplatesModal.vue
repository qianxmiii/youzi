<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { NButton, NInput, NModal, NSelect, NTabPane, NTabs, useMessage, type SelectInst } from 'naive-ui'
import { ArrowDown, ArrowUp, GripVertical, Link, Lock, LockOpen, X } from 'lucide-vue-next'
import {
  saveShipmentExportTemplate,
  type ShipmentExportChannelMapping,
  type ShipmentExportChannelOption,
  type ShipmentExportColumn,
  type ShipmentExportField,
  type ShipmentExportFormat,
  type ShipmentExportTemplate,
} from '@/api/shipments'
import { apiErrorMessage } from '@/utils/apiError'

const props = defineProps<{
  show: boolean
  fields: ShipmentExportField[]
  templates: ShipmentExportTemplate[]
  channels: ShipmentExportChannelOption[]
  initialTemplateId: string | null
}>()
const emit = defineEmits<{
  'update:show': [value: boolean]
  saved: [template: ShipmentExportTemplate]
}>()
const message = useMessage()
const id = ref<string | null>(null)
const name = ref('')
const columns = ref<ShipmentExportColumn[]>([])
const channelMappings = ref<{ channelCodes: string[]; value: string }[]>([])
const mappingList = ref<HTMLDivElement | null>(null)
const pendingMappingFocus = ref<number | null>(null)
const mappingSelects = new Map<number, SelectInst>()
const tab = ref('columns')
const fieldList = ref<HTMLOListElement | null>(null)
const dragging = ref<string | null>(null)
const dragOffset = ref(0)
let drag: {
  list: HTMLOListElement
  pointerId: number
  field: string
  startIndex: number
  clientY: number
  grabOffset: number
  first: number
  last: number
} | null = null
let dragFrame = 0
const saving = ref(false)
const labels = computed(() => new Map(props.fields.map(({ field, label }) => [field, label])))
const formatLabels: Record<ShipmentExportFormat, string> = {
  country_name: '中文名称',
  country_code: '国家代码',
  date_long: 'YYYY-MM-DD',
  date_short: 'MM-DD',
}
const formatOptions = computed(() => new Map(props.fields.filter(({ formats }) => formats?.length)
  .map(({ field, formats }) => [
    field,
    [{ label: '默认', value: 'default' }, ...formats.map((value) => ({ label: formatLabels[value], value }))],
  ])))
const fieldOptions = computed(() => {
  const pinnedFields = new Set(columns.value.filter(isPinned).map(({ field }) => field))
  return props.fields.map(({ field, label }) => ({ value: field, label, disabled: pinnedFields.has(field) }))
})
const linkedFields = computed(() => new Set(columns.value.flatMap(({ field, linkedTo }) => linkedTo ? [field, linkedTo] : [])))
const templateOptions = computed(() => props.templates.map((template) => ({ value: template.id, label: template.name })))
const hasChannelColumn = computed(() => columns.value.some(({ field }) => field === 'channel_code'))
const mappingCount = computed(() => channelMappings.value.reduce((count, row) => count + row.channelCodes.length, 0))
const incompleteMappings = computed(() => channelMappings.value.some(({ channelCodes, value }) => !channelCodes.length || !value.trim()))
const selectedFields = computed(() => columns.value.filter(({ field }) => !isBlankField(field)).map(({ field }) => field))
const canSave = computed(() => Boolean(name.value.trim()) && columns.value.length > 0
  && !columns.value.some(({ field, label }) => isBlankField(field) && !label.trim())
  && !incompleteMappings.value)

function isBlankField(field: string) {
  return /^blank_[1-9][0-9]*$/.test(field)
}

function isPinned(column: ShipmentExportColumn) {
  return column.locked || linkedFields.value.has(column.field)
}

function linkStart(index: number) {
  return columns.value[index - 1]?.linkedTo === columns.value[index].field ? index - 1 : index
}

function canToggleLink(index: number) {
  const start = linkStart(index)
  const [first, second] = columns.value.slice(start, start + 2)
  if (!second || first.locked || second.locked) return false
  if (first.linkedTo) return true
  return !isBlankField(first.field) && !isBlankField(second.field) && !linkedFields.value.has(second.field)
}

function toggleLink(index: number) {
  if (saving.value || !canToggleLink(index)) return
  finishDrag()
  const start = linkStart(index)
  const first = columns.value[start]
  first.linkedTo = first.linkedTo ? null : columns.value[start + 1].field
}

function fieldLabel(column: ShipmentExportColumn) {
  return isBlankField(column.field) ? '空白列' : labels.value.get(column.field) ?? column.field
}

function groupChannelMappings(entries: ShipmentExportChannelMapping[]) {
  const groups = new Map<string, string[]>()
  for (const { channelCode, value } of entries) {
    const codes = groups.get(value) ?? []
    codes.push(channelCode)
    groups.set(value, codes)
  }
  return Array.from(groups, ([value, channelCodes]) => ({ value, channelCodes }))
}

function channelOptions(index: number) {
  const current = new Set(channelMappings.value[index].channelCodes)
  const used = new Set(channelMappings.value.flatMap(({ channelCodes }, row) => row === index ? [] : channelCodes))
  return props.channels.map(({ code, name }) => ({
    value: code,
    label: name === code ? code : `${name} (${code})`,
    disabled: !current.has(code) && (used.has(code) || mappingCount.value >= 500),
  }))
}

function setMappingSelect(index: number, select: SelectInst | null) {
  if (select) mappingSelects.set(index, select)
  else mappingSelects.delete(index)
}

async function addChannelMapping() {
  if (saving.value || channelMappings.value.length >= 500 || mappingCount.value >= 500) return
  const index = channelMappings.value.length
  channelMappings.value.push({ channelCodes: [], value: '' })
  pendingMappingFocus.value = index
  await nextTick()
  if (pendingMappingFocus.value !== index) return
  mappingList.value?.children[index]?.scrollIntoView({ block: 'nearest', inline: 'nearest' })
  mappingSelects.get(index)?.focus()
  pendingMappingFocus.value = null
}

function edit(templateId: string | null) {
  finishDrag()
  const template = props.templates.find((item) => item.id === templateId)
  id.value = template?.id ?? null
  name.value = template?.name ?? ''
  columns.value = template
    ? template.columns.map((column) => ({ ...column }))
    : props.fields.map(({ field, label }) => ({ field, label }))
  channelMappings.value = groupChannelMappings(template?.channelMappings ?? [])
  if (!hasChannelColumn.value) tab.value = 'columns'
}

watch(() => props.show, (show) => {
  if (!show) return
  edit(props.initialTemplateId)
  tab.value = props.initialTemplateId && hasChannelColumn.value ? 'channels' : 'columns'
})

function copyTemplate() {
  id.value = null
  name.value = ''
  columns.value = columns.value.map((column) => ({ ...column, locked: false }))
}

function selectFields(fields: string[]) {
  if (saving.value) return
  finishDrag()
  const selected = new Set(fields)
  const retained = columns.value.filter((column) => isPinned(column) || isBlankField(column.field) || selected.has(column.field))
  const retainedFields = new Set(retained.map(({ field }) => field))
  const added = fields.filter((field) => !retainedFields.has(field))
    .map((field) => ({ field, label: labels.value.get(field) ?? field }))
  if (retained.length + added.length > 100) {
    message.warning('每个模板最多支持 100 列')
    return
  }
  columns.value = [...retained, ...added]
}

async function addBlankColumn() {
  if (saving.value || columns.value.length >= 100) return
  finishDrag()
  const used = new Set(columns.value.map(({ field }) => field))
  let number = 1
  while (used.has(`blank_${number}`)) number += 1
  columns.value.push({ field: `blank_${number}`, label: '' })
  await nextTick()
  fieldList.value?.lastElementChild?.querySelector('input')?.focus()
}

function canMove(from: number, to: number) {
  return from >= 0 && from < columns.value.length && to >= 0 && to < columns.value.length && from !== to
    && !columns.value.slice(Math.min(from, to), Math.max(from, to) + 1).some(isPinned)
}

function move(from: number, to: number) {
  if (!canMove(from, to)) return
  const [column] = columns.value.splice(from, 1)
  columns.value.splice(to, 0, column)
}

function startDrag(event: PointerEvent, field: string, index: number) {
  const list = fieldList.value
  const row = list?.children[index]
  if (saving.value || drag || !event.isPrimary || event.button !== 0 || !list || !row || isPinned(columns.value[index])) return
  let first = index
  let last = index
  while (first > 0 && !isPinned(columns.value[first - 1])) first -= 1
  while (last < columns.value.length - 1 && !isPinned(columns.value[last + 1])) last += 1
  if (first === last) return
  event.preventDefault()
  list.setPointerCapture(event.pointerId)
  drag = {
    list,
    pointerId: event.pointerId,
    field,
    startIndex: index,
    clientY: event.clientY,
    grabOffset: event.clientY - row.getBoundingClientRect().top,
    first,
    last,
  }
  dragOffset.value = 0
  dragging.value = field
  dragFrame = requestAnimationFrame(updateDrag)
}

function trackPointer(event: PointerEvent) {
  if (drag && event.pointerId === drag.pointerId) drag.clientY = event.clientY
}

function updateDrag() {
  const state = drag
  if (!state) return
  const { list, clientY, field, grabOffset, first, last } = state
  const from = columns.value.findIndex((column) => column.field === field)
  const row = list.children[from] as HTMLElement | undefined
  if (!row) {
    finishDrag()
    return
  }

  const bounds = list.getBoundingClientRect()
  const edge = Math.min(32, list.clientHeight / 4)
  const edgeDistance = Math.min(clientY - bounds.top, bounds.bottom - clientY)
  if (edgeDistance < edge) {
    const direction = clientY < (bounds.top + bounds.bottom) / 2 ? -1 : 1
    list.scrollTop += direction * Math.min(12, Math.ceil((edge - edgeDistance) / 3))
  }
  const firstRow = list.children[first] as HTMLElement
  const lastRow = list.children[last] as HTMLElement
  const maxTop = lastRow.offsetTop + lastRow.offsetHeight - row.offsetHeight
  const draggedTop = Math.max(firstRow.offsetTop, Math.min(maxTop, clientY - bounds.top - list.clientTop + list.scrollTop - grabOffset))
  const center = draggedTop + row.offsetHeight / 2
  const target = Array.from(list.children).filter((child) => {
    const other = child as HTMLElement
    return other !== row && center > other.offsetTop + other.offsetHeight / 2
  }).length
  const to = Math.min(last, Math.max(first, target))

  if (from === to) {
    dragOffset.value = draggedTop - row.offsetTop
  } else {
    move(from, to)
    void nextTick(() => {
      if (drag === state) dragOffset.value = draggedTop - row.offsetTop
    })
  }
  dragFrame = requestAnimationFrame(updateDrag)
}

function dropField(event: PointerEvent) {
  if (!drag || event.pointerId !== drag.pointerId) return
  trackPointer(event)
  cancelAnimationFrame(dragFrame)
  updateDrag()
  finishDrag(event)
}

function finishDrag(event?: PointerEvent) {
  if (!drag || (event && event.pointerId !== drag.pointerId)) return
  const { list, pointerId, field, startIndex } = drag
  drag = null
  cancelAnimationFrame(dragFrame)
  dragging.value = null
  dragOffset.value = 0
  if (list.hasPointerCapture(pointerId)) list.releasePointerCapture(pointerId)
  if (event?.type === 'pointercancel') {
    move(columns.value.findIndex((column) => column.field === field), startIndex)
  }
}

watch([() => props.show, tab], ([show, activeTab]) => {
  if (!show || activeTab !== 'columns') finishDrag()
})
onBeforeUnmount(() => finishDrag())

function toggleFieldLock(column: ShipmentExportColumn) {
  finishDrag()
  column.locked = !column.locked
}

function removeField(index: number) {
  if (saving.value || !columns.value[index] || isPinned(columns.value[index])) return
  finishDrag()
  columns.value.splice(index, 1)
}

async function save() {
  if (saving.value || !canSave.value) return
  saving.value = true
  try {
    const template = await saveShipmentExportTemplate({
      id: id.value ?? undefined,
      name: name.value.trim(),
      columns: columns.value,
      channelMappings: channelMappings.value.flatMap(({ channelCodes, value }) =>
        channelCodes.map((channelCode) => ({ channelCode, value })),
      ),
    })
    id.value = template.id
    name.value = template.name
    columns.value = template.columns.map((column) => ({ ...column }))
    channelMappings.value = groupChannelMappings(template.channelMappings ?? [])
    emit('saved', template)
    message.success('模板已保存')
  } catch (error) {
    message.error(apiErrorMessage(error, '保存导出模板失败'))
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <NModal
    :show="show"
    preset="card"
    title="运单导出模板"
    :style="{ width: 'min(640px, calc(100vw - 2rem))' }"
    :mask-closable="false"
    :closable="!saving"
    :close-on-esc="!saving"
    @update:show="emit('update:show', $event)"
  >
    <div class="flex flex-col gap-3">
      <div class="flex items-center gap-2">
        <NSelect :value="id" :options="templateOptions" :disabled="saving" placeholder="选择已保存的模板" aria-label="选择已保存的模板" @update:value="edit" />
        <NButton :disabled="saving" @click="edit(null)">新建</NButton>
        <NButton :disabled="!id || saving" @click="copyTemplate">复制</NButton>
      </div>
      <NInput v-model:value="name" :disabled="saving" :maxlength="60" placeholder="模板名称" aria-label="模板名称" />
      <NTabs v-model:value="tab" size="small" :animated="false">
        <NTabPane name="columns" tab="导出字段">
          <div class="flex flex-col gap-2">
            <div class="flex items-center gap-2">
              <NSelect
                multiple filterable clearable
                :value="selectedFields"
                :options="fieldOptions"
                :max-tag-count="3"
                :disabled="saving"
                placeholder="选择导出字段"
                aria-label="选择导出字段"
                @update:value="selectFields"
              />
              <NButton class="shrink-0" :disabled="saving || columns.length >= 100" @click="addBlankColumn">添加空白列</NButton>
            </div>
            <ol
              ref="fieldList"
              class="relative max-h-[min(44vh,25rem)] overflow-auto rounded-md border border-[var(--color-border)] [overflow-anchor:none]"
              @pointermove="trackPointer"
              @pointerup="dropField"
              @pointercancel="finishDrag"
              @lostpointercapture="finishDrag"
            >
              <li
                v-for="(column, index) in columns"
                :key="column.field"
                class="flex items-center gap-1.5 border-b border-[var(--color-border)] px-2 py-1 last:border-b-0"
                :class="{
                  'bg-[var(--tag-indigo-bg)]': column.locked,
                  'bg-[var(--tag-teal-bg)]': !column.locked && linkedFields.has(column.field),
                  'relative z-10 bg-[var(--color-panel)] shadow-sm ring-1 ring-inset ring-[var(--color-accent-text)]': dragging === column.field,
                }"
                :style="dragging === column.field ? { transform: `translateY(${dragOffset}px)` } : undefined"
              >
                <span
                  class="shrink-0 select-none"
                  :class="saving || isPinned(column) ? 'text-[var(--color-muted)]' : 'cursor-grab touch-none'"
                  @pointerdown="startDrag($event, column.field, index)"
                >
                  <GripVertical :size="15" aria-hidden="true" />
                </span>
                <span class="w-24 shrink-0 truncate text-xs" :title="fieldLabel(column)">{{ fieldLabel(column) }}</span>
                <NInput
                  v-model:value="column.label" size="small" :readonly="saving || column.locked || linkStart(index) !== index" :maxlength="100"
                  :placeholder="isBlankField(column.field) ? '填写表头' : undefined"
                  :aria-label="`${fieldLabel(column)}的导出表头`"
                />
                <NButton
                  quaternary size="tiny"
                  :type="linkedFields.has(column.field) ? 'primary' : 'default'"
                  :disabled="saving || !canToggleLink(index)"
                  :aria-pressed="linkedFields.has(column.field)"
                  :aria-label="`关联${fieldLabel(column)}`"
                  :title="linkedFields.has(column.field) ? '取消关联' : '与下一列合并'"
                  @click="toggleLink(index)"
                >
                  <Link :size="14" aria-hidden="true" />
                </NButton>
                <NSelect
                  v-if="formatOptions.has(column.field)"
                  size="small"
                  class="shrink-0"
                  style="width: min(9rem, 25vw)"
                  :value="column.format ?? 'default'"
                  :options="formatOptions.get(column.field)"
                  :disabled="saving || column.locked"
                  :aria-label="`${labels.get(column.field)}的导出格式`"
                  @update:value="(value: ShipmentExportFormat | 'default') => column.format = value === 'default' ? null : value"
                />
                <NButton
                  quaternary size="tiny"
                  :type="column.locked ? 'primary' : 'default'"
                  :disabled="saving"
                  :aria-pressed="Boolean(column.locked)"
                  :aria-label="`锁定${fieldLabel(column)}`"
                  :title="column.locked ? '解锁字段' : '锁定字段'"
                  @click="toggleFieldLock(column)"
                >
                  <component :is="column.locked ? Lock : LockOpen" :size="14" aria-hidden="true" />
                </NButton>
                <NButton quaternary size="tiny" :disabled="saving || !canMove(index, index - 1)" aria-label="上移" @click="move(index, index - 1)">
                  <ArrowUp :size="14" aria-hidden="true" />
                </NButton>
                <NButton quaternary size="tiny" :disabled="saving || !canMove(index, index + 1)" aria-label="下移" @click="move(index, index + 1)">
                  <ArrowDown :size="14" aria-hidden="true" />
                </NButton>
                <NButton
                  quaternary size="tiny" type="error" :disabled="saving || isPinned(column)"
                  title="移除字段" :aria-label="`移除${fieldLabel(column)}`"
                  @click="removeField(index)"
                >
                  <X :size="14" aria-hidden="true" />
                </NButton>
              </li>
            </ol>
          </div>
        </NTabPane>
        <NTabPane name="channels" tab="渠道映射" :disabled="!hasChannelColumn">
          <div class="flex flex-col gap-2">
            <div v-if="channelMappings.length" class="grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)_3rem] gap-2 text-xs text-[var(--color-muted)]">
              <span>系统渠道</span>
              <span>客户渠道</span>
            </div>
            <div ref="mappingList" class="max-h-[min(40vh,24rem)] space-y-2 overflow-auto pb-1">
              <div v-for="(mapping, index) in channelMappings" :key="index" class="grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)_3rem] items-center gap-2">
                <NSelect
                  :ref="element => setMappingSelect(index, element as SelectInst | null)"
                  v-model:value="mapping.channelCodes"
                  :options="channelOptions(index)"
                  :disabled="saving"
                  size="small"
                  multiple filterable
                  :show-on-focus="pendingMappingFocus === index"
                  :max-tag-count="2"
                  placeholder="选择系统渠道"
                  aria-label="系统渠道"
                />
                <NInput
                  v-model:value="mapping.value"
                  :disabled="saving"
                  :maxlength="200"
                  size="small"
                  placeholder="填客户渠道"
                  aria-label="客户渠道"
                />
                <NButton quaternary size="small" :disabled="saving" @click="channelMappings.splice(index, 1)">移除</NButton>
              </div>
            </div>
            <NButton class="self-start" size="small" :disabled="saving || channelMappings.length >= 500 || mappingCount >= 500" @click="addChannelMapping">
              添加映射
            </NButton>
          </div>
        </NTabPane>
      </NTabs>
    </div>
    <template #footer>
      <div class="flex justify-end gap-2">
        <NButton :disabled="saving" @click="emit('update:show', false)">关闭</NButton>
        <NButton type="primary" :loading="saving" :disabled="!canSave" @click="save">保存</NButton>
      </div>
    </template>
  </NModal>
</template>
