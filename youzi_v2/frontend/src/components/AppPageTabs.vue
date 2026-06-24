<script setup lang="ts">
import { X } from 'lucide-vue-next'
import { useRouter } from 'vue-router'
import { ICON_STROKE } from '@/constants/icons'
import { usePageTabs } from '@/composables/usePageTabs'

const router = useRouter()
const { tabs, activeKey, activateTab, closeTab, closeAll } = usePageTabs()

function onClose(key: string, event: MouseEvent) {
  event.stopPropagation()
  closeTab(key, router)
}

function onCloseAll() {
  closeAll(router)
}
</script>

<template>
  <div v-if="tabs.length" class="app-page-tabs">
    <div class="app-page-tabs__scroll scrollbar-subtle">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        type="button"
        class="app-page-tab"
        :class="{ 'app-page-tab--active': tab.key === activeKey }"
        @click="activateTab(tab.key, router)"
      >
        <span class="app-page-tab__title">{{ tab.title }}</span>
        <span
          class="app-page-tab__close"
          role="button"
          tabindex="-1"
          aria-label="关闭标签"
          @click="onClose(tab.key, $event)"
        >
          <X :size="14" :stroke-width="ICON_STROKE" aria-hidden="true" />
        </span>
      </button>
    </div>
    <button
      v-if="tabs.length > 1"
      type="button"
      class="app-page-tabs__close-all"
      title="关闭全部标签"
      @click="onCloseAll"
    >
      关闭全部
    </button>
  </div>
</template>
