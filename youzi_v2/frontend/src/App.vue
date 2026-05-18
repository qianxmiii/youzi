<script setup lang="ts">
import { NConfigProvider, NMessageProvider, darkTheme } from 'naive-ui'
import type { GlobalThemeOverrides } from 'naive-ui'

const themeOverrides: GlobalThemeOverrides = {
  common: {
    primaryColor: '#8b5cf6',
    primaryColorHover: '#a78bfa',
    primaryColorPressed: '#7c3aed',
    borderRadius: '8px',
    fontFamily: 'Inter, ui-sans-serif, system-ui, sans-serif',
    bodyColor: '#09090b',
    cardColor: '#18181b',
    modalColor: '#18181b',
    popoverColor: '#18181b',
    tableColor: '#18181b',
  },
}
</script>

<template>
  <NConfigProvider :theme="darkTheme" :theme-overrides="themeOverrides">
    <NMessageProvider>
      <RouterView />
    </NMessageProvider>
  </NConfigProvider>
</template>
