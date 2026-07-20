<script setup lang="ts">
import { ChevronDown, ChevronLeft } from 'lucide-vue-next'
import { NTooltip } from 'naive-ui'
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import NavIcon from '@/components/icons/NavIcon.vue'
import { ICON_STROKE, ICON_STROKE_NAV } from '@/constants/icons'
import { navGroups } from '@/constants/navigation'
import { useNavGroupsExpanded } from '@/composables/useNavGroupsExpanded'
import { usePendingPaymentReminderCount } from '@/composables/usePendingPaymentReminderCount'
import { usePendingShipmentSlaAlertCount } from '@/composables/usePendingShipmentSlaAlertCount'
import { usePendingTrackingTimeReviewCount } from '@/composables/usePendingTrackingTimeReviewCount'
import { useSidebarCollapsed } from '@/composables/useSidebarCollapsed'

const route = useRoute()
const { collapsed, toggle } = useSidebarCollapsed()
const { isGroupExpanded, toggleGroup } = useNavGroupsExpanded()
const { pendingTrackingTimeReviewCount, refreshPendingTrackingTimeReviewCount } =
  usePendingTrackingTimeReviewCount()
const { pendingShipmentSlaAlertCount, refreshPendingShipmentSlaAlertCount } =
  usePendingShipmentSlaAlertCount()
const { pendingPaymentReminderCount, refreshPendingPaymentReminderCount } =
  usePendingPaymentReminderCount()

onMounted(() => {
  void refreshPendingTrackingTimeReviewCount()
  void refreshPendingShipmentSlaAlertCount()
  void refreshPendingPaymentReminderCount()
})

const flatItems = computed(() => navGroups.flatMap((g) => g.items))

function navPathMatchesRoute(navPath: string, currentPath: string) {
  if (navPath === '/') return currentPath === '/'
  return currentPath === navPath || currentPath.startsWith(`${navPath}/`)
}

function isActive(path: string) {
  const currentPath = route.path
  const bestMatch = flatItems.value
    .filter((item) => navPathMatchesRoute(item.to, currentPath))
    .sort((a, b) => b.to.length - a.to.length)[0]
  return bestMatch?.to === path
}

function groupHasActiveItem(groupLabel: string) {
  const group = navGroups.find((g) => g.label === groupLabel)
  return group?.items.some((item) => isActive(item.to)) ?? false
}

function groupExpanded(label: string) {
  return isGroupExpanded(label, groupHasActiveItem(label))
}

function onToggleGroup(label: string) {
  toggleGroup(label, groupHasActiveItem(label))
}

function itemLabel(groupLabel: string, name: string, badge?: string) {
  const text = `${groupLabel} · ${name}`
  return badge ? `${text}（${badge}）` : text
}

function pendingNavCount(path: string) {
  if (path === '/approvals/tracking-time') return pendingTrackingTimeReviewCount.value
  if (path === '/shipment-exceptions') return pendingShipmentSlaAlertCount.value
  if (path === '/shipments/payment-reminders') return pendingPaymentReminderCount.value
  return 0
}

function pendingNavHint(path: string, count: number) {
  if (path === '/approvals/tracking-time') return `${count} 待审`
  if (path === '/shipment-exceptions') return `${count} 待办`
  if (path === '/shipments/payment-reminders') return `${count} 待催`
  return `${count}`
}

function formatNavPendingCount(count: number) {
  if (count <= 0) return ''
  return count > 99 ? '99+' : String(count)
}

function groupPendingCount(groupLabel: string) {
  if (groupLabel === '审批管理') return pendingTrackingTimeReviewCount.value
  if (groupLabel === '运单中心') {
    return pendingShipmentSlaAlertCount.value + pendingPaymentReminderCount.value
  }
  return 0
}
</script>

<template>
  <aside
    class="flex h-full shrink-0 flex-col border-r border-[var(--color-border)] bg-[var(--color-panel)] transition-[width] duration-200 ease-out"
    :class="collapsed ? 'w-14' : 'w-[240px]'"
  >
    <div
      class="flex h-14 shrink-0 items-center border-b border-[var(--color-border)]"
      :class="collapsed ? 'justify-center px-0' : 'gap-2.5 px-4'"
    >
      <img
        src="/youzi-app-icon.png"
        alt="Youzi"
        class="h-7 w-7 shrink-0 rounded-lg object-cover shadow-lg shadow-violet-500/20"
      />
      <div v-if="!collapsed" class="min-w-0">
        <div class="truncate text-sm font-semibold tracking-tight text-[var(--color-fg-emphasis)]">
          Youzi
        </div>
        <div class="text-[11px] text-[var(--color-muted)]">v2 · 迁移中</div>
      </div>
    </div>

    <nav
      class="scrollbar-subtle flex-1 overflow-x-hidden overflow-y-auto py-3"
      :class="collapsed ? 'px-1.5' : 'px-2'"
    >
      <div
        v-for="(group, gi) in navGroups"
        :key="group.label"
        class="nav-group"
        :class="[gi > 0 ? 'mt-2' : '']"
      >
        <!-- 展开：一级分组 + 二级菜单 -->
        <template v-if="!collapsed">
          <button
            type="button"
            class="nav-group-header"
            :class="{
              'nav-group-header--active': groupHasActiveItem(group.label),
              'nav-group-header--pinned': groupHasActiveItem(group.label),
            }"
            :aria-expanded="groupExpanded(group.label)"
            @click="onToggleGroup(group.label)"
          >
            <NavIcon :name="group.icon" />
            <span class="min-w-0 flex-1 truncate text-left">{{ group.label }}</span>
            <span
              v-if="groupPendingCount(group.label) > 0"
              class="nav-pending-badge shrink-0 rounded-full px-1.5 py-0.5 text-[10px] font-bold tabular-nums"
            >
              {{
                groupPendingCount(group.label) > 99 ? '99+' : groupPendingCount(group.label)
              }}
            </span>
            <ChevronDown
              class="nav-group-chevron shrink-0"
              :class="{ 'nav-group-chevron--folded': !groupExpanded(group.label) }"
              :size="16"
              :stroke-width="ICON_STROKE"
              aria-hidden="true"
            />
          </button>

          <div v-show="groupExpanded(group.label)" class="nav-group-children">
            <RouterLink
              v-for="item in group.items"
              :key="item.to"
              :to="item.to"
              class="nav-item nav-item--child"
              :class="{ 'nav-item-active': isActive(item.to) }"
            >
              <span class="flex-1 truncate">{{ item.name }}</span>
              <span
                v-if="pendingNavCount(item.to) > 0"
                class="nav-pending-badge shrink-0 rounded-full px-1.5 py-0.5 text-[10px] font-bold tabular-nums"
              >
                {{ pendingNavCount(item.to) > 99 ? '99+' : pendingNavCount(item.to) }}
              </span>
              <span
                v-else-if="item.badge"
                class="rounded-md px-1.5 py-0.5 text-[10px] font-medium"
                style="background: var(--color-badge-bg); color: var(--color-badge-fg)"
              >
                {{ item.badge }}
              </span>
            </RouterLink>
          </div>
        </template>

        <!-- 收起：仍展示全部叶子入口 -->
        <template v-else>
          <div
            v-if="gi > 0"
            class="mx-1.5 mb-1.5 border-t border-[var(--color-border)] pt-1.5"
          />
          <NTooltip
            v-for="item in group.items"
            :key="item.to"
            placement="right"
            :show-arrow="false"
          >
            <template #trigger>
              <RouterLink
                :to="item.to"
                class="nav-item mb-0.5 justify-center px-0 py-2.5"
                :class="{ 'nav-item-active': isActive(item.to) }"
                :aria-label="item.name"
              >
                <span class="relative inline-flex">
                  <NavIcon :name="item.icon" />
                  <span
                    v-if="pendingNavCount(item.to) > 0"
                    class="nav-pending-count"
                    :aria-label="pendingNavHint(item.to, pendingNavCount(item.to))"
                  >
                    {{ formatNavPendingCount(pendingNavCount(item.to)) }}
                  </span>
                </span>
              </RouterLink>
            </template>
            {{
              pendingNavCount(item.to) > 0
                ? `${itemLabel(group.label, item.name)}（${pendingNavHint(item.to, pendingNavCount(item.to))}）`
                : itemLabel(group.label, item.name, item.badge)
            }}
          </NTooltip>
        </template>
      </div>
    </nav>

    <div class="shrink-0 border-t border-[var(--color-border)] p-2">
      <NTooltip :disabled="!collapsed" placement="right" :show-arrow="false">
        <template #trigger>
          <a
            href="http://127.0.0.1:3001/"
            target="_blank"
            rel="noopener"
            class="nav-item w-full"
            :class="collapsed ? 'justify-center px-0 py-2.5' : ''"
            aria-label="旧版后台"
          >
            <NavIcon name="settings" />
            <span v-if="!collapsed">旧版后台</span>
          </a>
        </template>
        旧版后台
      </NTooltip>

      <button
        type="button"
        class="nav-item mt-1 w-full"
        :class="collapsed ? 'justify-center px-0 py-2.5' : ''"
        :aria-label="collapsed ? '展开侧栏' : '收起侧栏'"
        @click="toggle"
      >
        <ChevronLeft
          class="shrink-0 transition-transform duration-200"
          :class="collapsed ? 'rotate-180' : ''"
          :size="20"
          :stroke-width="ICON_STROKE_NAV"
          aria-hidden="true"
        />
        <span v-if="!collapsed" class="text-xs">收起侧栏</span>
      </button>

      <div v-if="!collapsed" class="mt-2 px-2.5 text-[10px] leading-relaxed text-[var(--color-muted)]">
        {{ flatItems.length }} 个模块 · {{ navGroups.length }} 个中心
      </div>
    </div>
  </aside>
</template>

<style scoped>
.nav-group-header {
  display: flex;
  width: 100%;
  align-items: center;
  gap: 0.625rem;
  border: none;
  border-radius: 0.5rem;
  padding: 0.5rem 0.625rem;
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--color-fg-secondary);
  background: transparent;
  cursor: pointer;
  transition:
    background-color 0.15s ease,
    color 0.15s ease;
}

.nav-group-header:hover {
  background: var(--color-nav-hover);
  color: var(--color-nav-fg-hover);
}

.nav-group-header--active {
  color: var(--color-nav-fg-active);
}

.nav-group-header--pinned {
  cursor: default;
}

.nav-group-header--pinned:hover {
  background: transparent;
  color: var(--color-nav-fg-active);
}

.nav-group-chevron {
  color: var(--color-muted);
  transition: transform 0.2s ease;
}

.nav-group-chevron--folded {
  transform: rotate(-90deg);
}

.nav-group-children {
  margin-top: 0.125rem;
  margin-bottom: 0.25rem;
  padding-left: 0.75rem;
  border-left: 1px solid var(--color-border-subtle);
  margin-left: 1.125rem;
}

.nav-item--child {
  margin-bottom: 0.125rem;
  padding: 0.4375rem 0.625rem;
  font-size: 0.8125rem;
}

.nav-pending-badge {
  background: rgb(254 243 199);
  color: rgb(180 83 9);
  border: 1px solid rgb(251 191 36 / 0.55);
}

[data-theme='dark'] .nav-pending-badge {
  background: rgb(120 53 15 / 0.45);
  color: rgb(253 230 138);
  border-color: rgb(245 158 11 / 0.35);
}

.nav-pending-count {
  position: absolute;
  top: -0.375rem;
  right: -0.5rem;
  min-width: 1rem;
  height: 1rem;
  padding: 0 0.1875rem;
  border-radius: 9999px;
  border: 1px solid rgb(251 191 36 / 0.55);
  background: rgb(254 243 199);
  color: rgb(180 83 9);
  font-size: 9px;
  font-weight: 700;
  line-height: 0.875rem;
  text-align: center;
  box-shadow: 0 0 0 1px var(--color-panel);
}

[data-theme='dark'] .nav-pending-count {
  background: rgb(120 53 15 / 0.92);
  color: rgb(253 230 138);
  border-color: rgb(245 158 11 / 0.35);
}
</style>
