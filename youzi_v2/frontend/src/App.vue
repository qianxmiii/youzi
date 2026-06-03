<script setup lang="ts">
import { computed } from 'vue'
import { NConfigProvider, NDialogProvider, NMessageProvider, darkTheme, lightTheme } from 'naive-ui'
import type { GlobalThemeOverrides } from 'naive-ui'
import { useTheme } from '@/composables/useTheme'

const { theme } = useTheme()

const naiveTheme = computed(() => (theme.value === 'dark' ? darkTheme : lightTheme))

const themeOverrides = computed<GlobalThemeOverrides>(() =>
  theme.value === 'dark'
    ? {
        common: {
          primaryColor: '#8b5cf6',
          primaryColorHover: '#a78bfa',
          primaryColorPressed: '#7c3aed',
          borderRadius: '8px',
          fontFamily: '"Inter", "Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif',
          bodyColor: '#09090b',
          cardColor: '#18181b',
          modalColor: '#18181b',
          popoverColor: '#18181b',
          tableColor: '#18181b',
        },
      }
    : {
        common: {
          primaryColor: '#8b5cf6',
          primaryColorHover: '#7c3aed',
          primaryColorPressed: '#6d28d9',
          borderRadius: '8px',
          fontFamily: '"Inter", "Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif',
          bodyColor: '#f4f4f5',
          cardColor: '#ffffff',
          modalColor: '#ffffff',
          popoverColor: '#ffffff',
          tableColor: '#ffffff',
          textColor1: '#18181b',
          textColor2: '#3f3f46',
          textColor3: '#71717a',
          borderColor: '#e4e4e7',
          dividerColor: '#e4e4e7',
          hoverColor: 'rgb(24 24 27 / 0.04)',
          pressedColor: 'rgb(24 24 27 / 0.08)',
        },
      },
)
</script>

<template>
  <NConfigProvider :theme="naiveTheme" :theme-overrides="themeOverrides">
    <NMessageProvider>
      <NDialogProvider>
        <RouterView />
      </NDialogProvider>
    </NMessageProvider>
  </NConfigProvider>
</template>
