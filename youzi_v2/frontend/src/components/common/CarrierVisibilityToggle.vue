<script setup lang="ts">
import { Eye, EyeOff } from 'lucide-vue-next'
import { carrierVisible } from '@/composables/useCarrierPrivacy'
import { ICON_STROKE } from '@/constants/icons'
</script>

<template>
  <button
    type="button"
    class="header-ghost-btn"
    aria-label="显示承运商信息"
    :aria-pressed="carrierVisible"
    :title="carrierVisible ? '隐藏承运商信息' : '显示承运商信息'"
    @click="carrierVisible = !carrierVisible"
  >
    <component :is="carrierVisible ? Eye : EyeOff" class="size-4" :stroke-width="ICON_STROKE" aria-hidden="true" />
  </button>
</template>
