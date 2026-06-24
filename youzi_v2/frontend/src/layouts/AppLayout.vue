<script setup lang="ts">
import AppHeader from '@/components/AppHeader.vue'
import AppPageTabs from '@/components/AppPageTabs.vue'
import AppSidebar from '@/components/AppSidebar.vue'
</script>

<template>
  <div class="flex h-screen overflow-hidden bg-[var(--color-surface)]">
    <AppSidebar />
    <div class="flex min-w-0 flex-1 flex-col">
      <AppHeader />
      <AppPageTabs />
      <main class="flex min-h-0 flex-1 flex-col overflow-hidden p-6">
        <RouterView v-slot="{ Component, route }">
          <KeepAlive :max="15">
            <component :is="Component" :key="route.fullPath" class="flex min-h-0 min-w-0 flex-1 flex-col" />
          </KeepAlive>
        </RouterView>
      </main>
    </div>
  </div>
</template>
