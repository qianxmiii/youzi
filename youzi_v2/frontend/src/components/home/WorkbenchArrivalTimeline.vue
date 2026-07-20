<script setup lang="ts">
import { NButton } from 'naive-ui'
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import type { WorkbenchArrivalDayGroup, WorkbenchArrivalItem } from '@/api/workbench'

const props = defineProps<{
  items: WorkbenchArrivalItem[]
  loading?: boolean
  error?: string | null
  available?: boolean
}>()

const emit = defineEmits<{
  retry: []
}>()

const router = useRouter()

const GROUP_LABEL: Record<WorkbenchArrivalDayGroup, string> = {
  today: '今天',
  tomorrow: '明天',
  later: '后天及以后',
}

const grouped = computed(() => {
  const order: WorkbenchArrivalDayGroup[] = ['today', 'tomorrow', 'later']
  return order
    .map((key) => ({
      key,
      label: GROUP_LABEL[key],
      items: props.items.filter((item) => item.dayGroup === key),
    }))
    .filter((g) => g.items.length > 0)
})

function formatEta(eta: string | null) {
  const raw = (eta || '').trim()
  if (!raw) return '—'
  // MM-DD HH:mm
  const m = raw.match(/(\d{2})-(\d{2})[ T](\d{2}:\d{2})/)
  if (m) return `${m[1]}-${m[2]} ${m[3]}`
  return raw.slice(5, 16)
}

function openItem(item: WorkbenchArrivalItem) {
  if (item.href) {
    void router.push(item.href)
    return
  }
  void router.push({ path: '/vessel-schedules', query: { maritimeStatus: 'arriving_soon' } })
}

function openAll() {
  void router.push({ path: '/vessel-schedules', query: { maritimeStatus: 'arriving_soon' } })
}
</script>

<template>
  <section class="panel arrival-panel">
    <div class="arrival-panel__head">
      <h2 class="arrival-panel__title">近期到港</h2>
      <NButton text size="tiny" type="primary" @click="openAll">查看全部</NButton>
    </div>

    <div v-if="error && available === false" class="arrival-panel__error">
      <span>{{ error }}</span>
      <button type="button" @click="emit('retry')">重试</button>
    </div>

    <div v-if="loading && !items.length" class="arrival-empty">加载中…</div>
    <div v-else-if="!items.length" class="arrival-empty">未来三天暂无到港</div>
    <div v-else class="arrival-groups">
      <div v-for="group in grouped" :key="group.key" class="arrival-group">
        <h3 class="arrival-group__label">{{ group.label }}</h3>
        <ul>
          <li v-for="(item, idx) in group.items" :key="`${item.vesselVoyage}-${item.eta}-${idx}`">
            <button type="button" class="arrival-row" @click="openItem(item)">
              <div class="arrival-row__voyage">{{ item.vesselVoyage || '—' }}</div>
              <div class="arrival-row__meta">
                <span>{{ item.destinationPortCode || '目的港待定' }}</span>
                <span v-if="item.isSubscribedPort" class="arrival-row__tag">订阅港</span>
                <span>· ETA {{ formatEta(item.eta) }}</span>
                <span>· {{ item.shipmentCount }} 票</span>
              </div>
            </button>
          </li>
        </ul>
      </div>
    </div>
  </section>
</template>

<style scoped>
.arrival-panel {
  padding: 0.9rem 1rem 0.75rem;
  min-height: 16rem;
}

.arrival-panel__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.65rem;
}

.arrival-panel__title {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 600;
}

.arrival-panel__error {
  display: flex;
  justify-content: space-between;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
  font-size: 0.8rem;
  color: #e11d48;
}

.arrival-panel__error button {
  border: 0;
  background: transparent;
  color: var(--yz-primary, #2563eb);
  cursor: pointer;
}

.arrival-group {
  margin-bottom: 0.75rem;
}

.arrival-group__label {
  margin: 0 0 0.35rem;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--yz-muted, #6b7280);
  text-transform: none;
}

.arrival-group ul {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.arrival-row {
  width: 100%;
  border: 0;
  border-radius: 0.45rem;
  background: transparent;
  padding: 0.4rem 0.25rem;
  text-align: left;
  cursor: pointer;
}

.arrival-row:hover {
  background: color-mix(in srgb, var(--yz-bg, #f8fafc) 90%, #fff);
}

.arrival-row__voyage {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--yz-text, #111827);
}

.arrival-row__meta {
  margin-top: 0.15rem;
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
  font-size: 0.75rem;
  color: var(--yz-muted, #6b7280);
}

.arrival-row__tag {
  color: #0284c7;
  font-weight: 600;
}

.arrival-empty {
  padding: 1.75rem 0.5rem;
  text-align: center;
  font-size: 0.85rem;
  color: var(--yz-muted, #9ca3af);
}
</style>
