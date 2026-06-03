<script setup lang="ts">
import BellIcon from '@/components/common/BellIcon.vue'

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
    <!-- 查看 -->
    <svg
      v-if="kind === 'view'"
      viewBox="0 0 20 20"
      fill="none"
      class="table-action-icon__svg"
      aria-hidden="true"
    >
      <path
        d="M10 4.5c-3.2 0-5.9 2-7.2 5 1.3 3 4 5 7.2 5s5.9-2 7.2-5c-1.3-3-4-5-7.2-5Z"
        stroke="currentColor"
        stroke-width="1.35"
        stroke-linejoin="round"
      />
      <circle cx="10" cy="9.5" r="2.25" stroke="currentColor" stroke-width="1.35" />
    </svg>
    <!-- 编辑 -->
    <svg
      v-else-if="kind === 'edit'"
      viewBox="0 0 20 20"
      fill="none"
      class="table-action-icon__svg"
      aria-hidden="true"
    >
      <path
        d="M12.2 3.5 16.5 7.8 6.8 17.5H2.5v-4.3L12.2 3.5Z"
        stroke="currentColor"
        stroke-width="1.35"
        stroke-linejoin="round"
      />
      <path d="M11 5.3 14.7 9" stroke="currentColor" stroke-width="1.35" stroke-linecap="round" />
    </svg>
    <BellIcon v-else-if="kind === 'subscribe'" :filled="active" />
    <!-- 删除 -->
    <svg
      v-else
      viewBox="0 0 20 20"
      fill="none"
      class="table-action-icon__svg"
      aria-hidden="true"
    >
      <path
        d="M4.5 6h11M7.5 6V4.8c0-.7.6-1.3 1.3-1.3h2.4c.7 0 1.3.6 1.3 1.3V6m1.2 0v9.2c0 .7-.6 1.3-1.3 1.3H7.6c-.7 0-1.3-.6-1.3-1.3V6"
        stroke="currentColor"
        stroke-width="1.35"
        stroke-linecap="round"
        stroke-linejoin="round"
      />
      <path d="M8.2 8.5v5M11.8 8.5v5" stroke="currentColor" stroke-width="1.35" stroke-linecap="round" />
    </svg>
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
