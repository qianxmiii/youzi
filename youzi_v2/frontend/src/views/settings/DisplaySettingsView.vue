<script setup lang="ts">
import {
  NButton,
  NForm,
  NFormItem,
  NSelect,
  NSpace,
  NSwitch,
  useMessage,
} from 'naive-ui'
import { computed, onMounted, ref } from 'vue'
import {
  getWorldClocksSettings,
  updateWorldClocksSettings,
  type WorldClockZone,
  type WorldClocksSettings,
} from '@/api/worldClocks'
import { apiErrorMessage } from '@/utils/apiError'
import { setWorldClocksCache } from '@/composables/useWorldClocks'
import {
  MAX_WORLD_CLOCK_ZONES,
  WORLD_CLOCK_PRESETS,
} from '@/constants/worldClockPresets'

const message = useMessage()
const loading = ref(false)
const saving = ref(false)

const enabled = ref(true)
const use24h = ref(true)
const zones = ref<WorldClockZone[]>([])

const addPick = ref<string | null>(null)

const addOptions = computed(() =>
  WORLD_CLOCK_PRESETS.filter((p) => !zones.value.some((z) => z.tz === p.tz)).map((p) => ({
    label: `${p.label} (${p.tz})`,
    value: p.tz,
  })),
)

async function load() {
  loading.value = true
  try {
    const res = await getWorldClocksSettings()
    apply(res)
  } catch (e) {
    message.error(e instanceof Error ? e.message : '加载失败')
  } finally {
    loading.value = false
  }
}

function apply(res: WorldClocksSettings) {
  enabled.value = res.enabled
  use24h.value = res.use24h
  zones.value = res.zones.map((z) => ({ ...z }))
}

function addZone() {
  const tz = addPick.value
  if (!tz) return
  if (zones.value.length >= MAX_WORLD_CLOCK_ZONES) {
    message.warning(`最多 ${MAX_WORLD_CLOCK_ZONES} 个时区`)
    return
  }
  const preset = WORLD_CLOCK_PRESETS.find((p) => p.tz === tz)
  if (!preset) return
  zones.value.push({ tz: preset.tz, label: preset.label })
  addPick.value = null
}

function removeZone(index: number) {
  zones.value.splice(index, 1)
}

function moveZone(index: number, delta: number) {
  const next = index + delta
  if (next < 0 || next >= zones.value.length) return
  const copy = [...zones.value]
  const tmp = copy[index]
  copy[index] = copy[next]
  copy[next] = tmp
  zones.value = copy
}

async function save() {
  if (enabled.value && zones.value.length === 0) {
    message.warning('请至少保留一个时区，或关闭世界时间显示')
    return
  }
  saving.value = true
  try {
    const res = await updateWorldClocksSettings({
      enabled: enabled.value,
      use24h: use24h.value,
      zones: zones.value,
    })
    apply(res)
    setWorldClocksCache(res)
    message.success('显示设置已保存')
  } catch (e) {
    message.error(apiErrorMessage(e, '保存失败'))
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="mx-auto max-w-2xl space-y-6">
    <div>
      <h2 class="page-h2">显示设置</h2>
      <p class="page-subtitle">顶栏世界时间全员一致，保存后所有人刷新即可生效。</p>
    </div>

    <section class="panel space-y-4 p-5">
      <h3 class="text-sm font-medium text-[var(--color-fg-emphasis)]">世界时间</h3>

      <NForm label-placement="left" label-width="120" :disabled="loading || saving">
        <NFormItem label="顶栏显示">
          <NSwitch v-model:value="enabled" />
        </NFormItem>
        <NFormItem label="24 小时制">
          <NSwitch v-model:value="use24h" />
        </NFormItem>
      </NForm>

      <div class="space-y-2">
        <p class="text-xs text-[var(--color-muted)]">
          时区列表（最多 {{ MAX_WORLD_CLOCK_ZONES }} 个，从上到下为顶栏从左到右顺序）
        </p>
        <ul class="space-y-2">
          <li
            v-for="(z, idx) in zones"
            :key="z.tz"
            class="flex flex-wrap items-center gap-2 rounded-lg border border-[var(--color-border)] px-3 py-2"
          >
            <span class="min-w-0 flex-1 text-sm">
              <span class="font-medium text-[var(--color-fg-emphasis)]">{{ z.label }}</span>
              <span class="ml-2 text-xs text-[var(--color-muted)]">{{ z.tz }}</span>
            </span>
            <NSpace size="small">
              <NButton size="tiny" quaternary :disabled="idx === 0" @click="moveZone(idx, -1)">
                上移
              </NButton>
              <NButton
                size="tiny"
                quaternary
                :disabled="idx === zones.length - 1"
                @click="moveZone(idx, 1)"
              >
                下移
              </NButton>
              <NButton size="tiny" quaternary type="error" @click="removeZone(idx)">移除</NButton>
            </NSpace>
          </li>
        </ul>
        <p v-if="!zones.length" class="text-xs text-[var(--color-muted)]">暂无时区，请下方添加。</p>
      </div>

      <div class="flex flex-wrap items-end gap-2">
        <NSelect
          v-model:value="addPick"
          class="min-w-[16rem] flex-1"
          :options="addOptions"
          filterable
          clearable
          placeholder="添加时区"
          :disabled="zones.length >= MAX_WORLD_CLOCK_ZONES"
        />
        <NButton :disabled="!addPick" @click="addZone">添加</NButton>
      </div>

      <div class="flex justify-end border-t border-[var(--color-border)] pt-4">
        <NButton type="primary" :loading="saving" @click="save">保存</NButton>
      </div>
    </section>
  </div>
</template>
