<script setup lang="ts">
import { BellDot, Route, SquarePen, Trash2 } from 'lucide-vue-next'
import BellCheckIcon from '@/components/icons/BellCheckIcon.vue'
import { ICON_STROKE } from '@/constants/icons'

withDefaults(
  defineProps<{
    kind: 'view' | 'edit' | 'delete' | 'subscribe'
    title: string
    /** 订阅图标：已订阅高亮 */
    active?: boolean
    loading?: boolean
  }>(),
  { active: false, loading: false },
)

defineEmits<{
  click: []
}>()
</script>

<template>
  <button
    type="button"
    class="table-action-icon"
    :class="[
      'table-action-icon--' + kind,
      kind === 'subscribe' && active ? 'table-action-icon--subscribe-active' : '',
    ]"
    :aria-label="title"
    :disabled="loading"
    @click.stop="$emit('click')"
  >
    <Route v-if="kind === 'view'" class="table-action-icon__svg" :stroke-width="ICON_STROKE" aria-hidden="true" />
    <SquarePen v-else-if="kind === 'edit'" class="table-action-icon__svg" :stroke-width="ICON_STROKE" aria-hidden="true" />
    <BellCheckIcon
      v-else-if="kind === 'subscribe' && active"
      class="table-action-icon__svg"
      :stroke-width="ICON_STROKE"
    />
    <BellDot
      v-else-if="kind === 'subscribe'"
      class="table-action-icon__svg"
      :stroke-width="ICON_STROKE"
      aria-hidden="true"
    />
    <Trash2 v-else class="table-action-icon__svg" :stroke-width="ICON_STROKE" aria-hidden="true" />
  </button>
</template>

<style scoped>
.table-action-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.75rem;
  height: 1.75rem;
  border: none;
  border-radius: 0.375rem;
  padding: 0;
  background: transparent;
  cursor: pointer;
  transition:
    background-color 0.15s ease,
    color 0.15s ease,
    box-shadow 0.15s ease;
}

.table-action-icon__svg {
  width: 1.125rem;
  height: 1.125rem;
}

.table-action-icon--view {
  color: rgb(37 99 235);
}

.table-action-icon--view:hover {
  background: rgb(239 246 255);
}

.table-action-icon--edit {
  color: rgb(82 82 91);
}

.table-action-icon--edit:hover {
  background: rgb(244 244 245);
  color: rgb(39 39 42);
}

.table-action-icon--delete {
  color: rgb(220 38 38);
}

.table-action-icon--delete:hover {
  background: rgb(254 242 242);
}

.table-action-icon--subscribe {
  color: rgb(161 161 170);
}

.table-action-icon--subscribe:hover:not(:disabled) {
  background: rgb(244 244 245);
  color: rgb(113 113 122);
}

.table-action-icon--subscribe-active {
  color: rgb(124 58 237);
}

.table-action-icon--subscribe-active:hover:not(:disabled) {
  background: rgb(237 233 254);
  color: rgb(109 40 217);
}

.table-action-icon:disabled {
  cursor: wait;
  opacity: 0.55;
}

[data-theme='dark'] .table-action-icon--view {
  color: rgb(96 165 250);
}

[data-theme='dark'] .table-action-icon--view:hover {
  background: rgb(30 58 138 / 0.35);
}

[data-theme='dark'] .table-action-icon--edit {
  color: rgb(161 161 170);
}

[data-theme='dark'] .table-action-icon--edit:hover {
  background: rgb(63 63 70 / 0.5);
  color: rgb(228 228 231);
}

[data-theme='dark'] .table-action-icon--delete {
  color: rgb(248 113 113);
}

[data-theme='dark'] .table-action-icon--delete:hover {
  background: rgb(127 29 29 / 0.35);
}

[data-theme='dark'] .table-action-icon--subscribe {
  color: rgb(113 113 122);
}

[data-theme='dark'] .table-action-icon--subscribe:hover:not(:disabled) {
  background: rgb(63 63 70 / 0.5);
  color: rgb(161 161 170);
}

[data-theme='dark'] .table-action-icon--subscribe-active {
  color: rgb(167 139 250);
}

[data-theme='dark'] .table-action-icon--subscribe-active:hover:not(:disabled) {
  background: rgb(91 33 182 / 0.35);
  color: rgb(196 181 253);
}
</style>
