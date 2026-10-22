<script setup lang="ts">
import { NButton, NModal, NSelect } from 'naive-ui'
import { computed, ref, watch } from 'vue'
import { listDictByType } from '@/api/dict'
import type { Shipment } from '@/types/shipment'
import {
  MARK_RENAME_COUNTRY_LANG_OPTIONS,
  MARK_RENAME_FIELDS,
  MARK_RENAME_SEPARATORS,
  DEFAULT_MARK_RENAME_COUNTRY_LANG,
  DEFAULT_MARK_RENAME_FIELDS,
  normalizeStoredMarkRenameCountryLang,
  normalizeStoredMarkRenameFields,
  previewMarkRenameFolder,
  previewMarkRenameStem,
  type MarkRenameCountryLabelMap,
  type MarkRenameCountryLang,
  type MarkRenameFieldKey,
} from '@/utils/markRename'

const STORAGE_KEY = 'youzi.markRename.v1'

const props = defineProps<{
  show: boolean
  previewRow: Shipment | null
  count: number
}>()

const emit = defineEmits<{
  'update:show': [value: boolean]
  confirm: [
    payload: {
      fields: MarkRenameFieldKey[]
      separator: string
      folder: string
      countryLang: MarkRenameCountryLang
    },
  ]
}>()

const selected = ref<MarkRenameFieldKey[]>([...DEFAULT_MARK_RENAME_FIELDS])
const separator = ref('-')
const folderField = ref<MarkRenameFieldKey | ''>('')
const countryLang = ref<MarkRenameCountryLang>(DEFAULT_MARK_RENAME_COUNTRY_LANG)
const countryLabels = ref<MarkRenameCountryLabelMap>({})

const labelOf = Object.fromEntries(MARK_RENAME_FIELDS.map((item) => [item.key, item.label]))

const available = computed(() =>
  MARK_RENAME_FIELDS.filter((item) => !selected.value.includes(item.key)),
)

const folderOptions = computed(() => [
  { label: '不使用', value: '' },
  ...MARK_RENAME_FIELDS.map((item) => ({ label: item.label, value: item.key })),
])

const usesCountry = computed(
  () => selected.value.includes('countryCode') || folderField.value === 'countryCode',
)

const resolveOpts = computed(() => ({
  countryLang: countryLang.value,
  countryLabels: countryLabels.value,
}))

const previewName = computed(() => {
  const row = props.previewRow
  if (!row) return ''
  const file = `${previewMarkRenameStem(row, selected.value, separator.value, resolveOpts.value)}.pdf`
  const folder = previewMarkRenameFolder(row, folderField.value, resolveOpts.value)
  return folder ? `${folder}/${file}` : file
})

async function loadCountryLabels() {
  try {
    const res = await listDictByType('country_code')
    const map: MarkRenameCountryLabelMap = {}
    for (const item of res.items) {
      const code = (item.code || '').trim().toUpperCase()
      if (!code) continue
      map[code] = {
        zh: (item.value || '').trim(),
        en: (item.desc || '').trim(),
      }
    }
    countryLabels.value = map
  } catch {
    countryLabels.value = {}
  }
}

function loadStored() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return
    const parsed = JSON.parse(raw) as {
      fields?: unknown
      separator?: unknown
      folder?: unknown
      countryLang?: unknown
    }
    selected.value = normalizeStoredMarkRenameFields(parsed.fields)
    const sep = parsed.separator
    if (sep === '-' || sep === '_' || sep === ' ') separator.value = sep
    const folder = parsed.folder
    folderField.value =
      typeof folder === 'string' && MARK_RENAME_FIELDS.some((item) => item.key === folder)
        ? (folder as MarkRenameFieldKey)
        : ''
    countryLang.value = normalizeStoredMarkRenameCountryLang(parsed.countryLang)
  } catch {
    selected.value = [...DEFAULT_MARK_RENAME_FIELDS]
    separator.value = '-'
    folderField.value = ''
    countryLang.value = DEFAULT_MARK_RENAME_COUNTRY_LANG
  }
}

function persist() {
  localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify({
      fields: selected.value,
      separator: separator.value,
      folder: folderField.value,
      countryLang: countryLang.value,
    }),
  )
}

watch(
  () => props.show,
  (open) => {
    if (open) {
      loadStored()
      void loadCountryLabels()
    }
  },
)

function move(index: number, delta: number) {
  const next = index + delta
  if (next < 0 || next >= selected.value.length) return
  const copy = selected.value.slice()
  const [item] = copy.splice(index, 1)
  if (!item) return
  copy.splice(next, 0, item)
  selected.value = copy
}

function remove(key: MarkRenameFieldKey) {
  selected.value = selected.value.filter((item) => item !== key)
}

function add(key: MarkRenameFieldKey) {
  if (!selected.value.includes(key)) selected.value = [...selected.value, key]
}

function submit() {
  if (!selected.value.length) return
  persist()
  emit('confirm', {
    fields: selected.value.slice(),
    separator: separator.value,
    folder: folderField.value,
    countryLang: countryLang.value,
  })
  emit('update:show', false)
}
</script>

<template>
  <NModal
    :show="show"
    preset="card"
    title="唛头（重命名）"
    :style="{ width: '380px', maxWidth: 'calc(100vw - 2rem)' }"
    :mask-closable="false"
    @update:show="emit('update:show', $event)"
  >
    <p class="text-xs leading-relaxed text-[var(--color-fg-secondary)]">
      按下面的顺序用分隔符拼文件名。空字段会跳过；派送仓库为空时自动用邮编。
      {{
        count > 1
          ? folderField
            ? `已选 ${count} 票，相同${labelOf[folderField]}放进同一个文件夹。`
            : `已选 ${count} 票，将打成一个 zip，包内各票单独命名。`
          : '已选 1 票，直接下载该文件。'
      }}
    </p>

    <ol class="mt-3 space-y-1.5">
      <li
        v-for="(key, index) in selected"
        :key="key"
        class="flex items-center gap-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-elevated)] px-2 py-1.5"
      >
        <span class="w-5 shrink-0 text-center text-xs text-[var(--color-muted)]">{{ index + 1 }}</span>
        <span class="min-w-0 flex-1 text-sm text-[var(--color-fg)]">{{ labelOf[key] }}</span>
        <button
          type="button"
          class="cursor-pointer rounded border border-[var(--color-border)] px-2 py-0.5 text-xs text-[var(--color-fg-secondary)] disabled:cursor-not-allowed disabled:opacity-40"
          :disabled="index === 0"
          @click="move(index, -1)"
        >
          上移
        </button>
        <button
          type="button"
          class="cursor-pointer rounded border border-[var(--color-border)] px-2 py-0.5 text-xs text-[var(--color-fg-secondary)] disabled:cursor-not-allowed disabled:opacity-40"
          :disabled="index === selected.length - 1"
          @click="move(index, 1)"
        >
          下移
        </button>
        <button
          type="button"
          class="cursor-pointer rounded border border-[var(--color-border)] px-2 py-0.5 text-xs text-[var(--color-fg-secondary)]"
          @click="remove(key)"
        >
          移除
        </button>
      </li>
    </ol>
    <p v-if="!selected.length" class="mt-2 text-xs text-[var(--color-muted)]">请至少加入一个字段。</p>

    <div v-if="available.length" class="mt-3 flex flex-wrap gap-1.5">
      <button
        v-for="item in available"
        :key="item.key"
        type="button"
        class="cursor-pointer rounded-full border border-[var(--color-border)] px-2.5 py-1 text-xs text-[var(--color-fg-secondary)] hover:bg-[var(--color-btn-ghost-hover)]"
        @click="add(item.key)"
      >
        + {{ item.label }}
      </button>
    </div>

    <div class="mt-4 space-y-2">
      <label class="flex items-center gap-2">
        <span class="w-14 shrink-0 text-sm text-[var(--color-fg-secondary)]">分隔符</span>
        <NSelect
          v-model:value="separator"
          class="min-w-0 flex-1"
          :options="MARK_RENAME_SEPARATORS.map((item) => ({ label: item.label, value: item.value }))"
        />
      </label>
      <label class="flex items-center gap-2">
        <span class="w-14 shrink-0 text-sm text-[var(--color-fg-secondary)]">文件夹</span>
        <NSelect v-model:value="folderField" class="min-w-0 flex-1" :options="folderOptions" />
      </label>
      <label v-if="usesCountry" class="flex items-center gap-2">
        <span class="w-14 shrink-0 text-sm text-[var(--color-fg-secondary)]">国家</span>
        <NSelect
          v-model:value="countryLang"
          class="min-w-0 flex-1"
          :options="MARK_RENAME_COUNTRY_LANG_OPTIONS.map((item) => ({ label: item.label, value: item.value }))"
        />
      </label>
    </div>

    <p v-if="previewName" class="mt-3 break-all text-sm text-[var(--color-fg)]">
      预览：{{ previewName }}
    </p>

    <template #footer>
      <div class="flex justify-end gap-2">
        <NButton @click="emit('update:show', false)">取消</NButton>
        <NButton type="primary" :disabled="!selected.length" @click="submit">下载</NButton>
      </div>
    </template>
  </NModal>
</template>
