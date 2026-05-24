<script setup lang="ts">
defineProps<{ name: string }>()
</script>

<template>
  <svg
    class="h-4 w-4 shrink-0 opacity-80"
    viewBox="0 0 16 16"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden="true"
  >
    <template v-if="name === 'grid'">
      <rect x="2" y="2" width="5" height="5" rx="1" stroke="currentColor" stroke-width="1.25" />
      <rect x="9" y="2" width="5" height="5" rx="1" stroke="currentColor" stroke-width="1.25" />
      <rect x="2" y="9" width="5" height="5" rx="1" stroke="currentColor" stroke-width="1.25" />
      <rect x="9" y="9" width="5" height="5" rx="1" stroke="currentColor" stroke-width="1.25" />
    </template>
    <template v-else-if="name === 'box'">
      <path
        d="M2.5 5.5 8 2.5l5.5 3v5L8 13.5l-5.5-3v-5Z"
        stroke="currentColor"
        stroke-width="1.25"
        stroke-linejoin="round"
      />
      <path d="M8 8v5.5M2.5 5.5 8 8l5.5-2.5" stroke="currentColor" stroke-width="1.25" />
    </template>
    <template v-else-if="name === 'quote'">
      <path
        d="M3 4.5h10M3 8h6M3 11.5h8"
        stroke="currentColor"
        stroke-width="1.25"
        stroke-linecap="round"
      />
    </template>
    <template v-else-if="name === 'layers'">
      <path d="M2.5 6 8 3.5 13.5 6 8 8.5 2.5 6Z" stroke="currentColor" stroke-width="1.25" />
      <path d="M2.5 10 8 12.5 13.5 10" stroke="currentColor" stroke-width="1.25" />
    </template>
    <template v-else-if="name === 'calc'">
      <rect x="3" y="2.5" width="10" height="11" rx="1.5" stroke="currentColor" stroke-width="1.25" />
      <path d="M5.5 6h5M5.5 8.5h3" stroke="currentColor" stroke-width="1.25" stroke-linecap="round" />
    </template>
    <template v-else-if="name === 'book'">
      <path
        d="M3 3.5h4.5a1.5 1.5 0 0 1 1.5 1.5V13L5.5 11 3 13V3.5Z"
        stroke="currentColor"
        stroke-width="1.25"
        stroke-linejoin="round"
      />
      <path
        d="M8.5 3.5H13a1 1 0 0 1 1 1V13l-3-2-3 2V4.5a1 1 0 0 1 1-1Z"
        stroke="currentColor"
        stroke-width="1.25"
        stroke-linejoin="round"
      />
    </template>
    <template v-else-if="name === 'pin'">
      <path
        d="M8 2.5v9M5.5 12.5h5"
        stroke="currentColor"
        stroke-width="1.25"
        stroke-linecap="round"
      />
      <circle cx="8" cy="5.5" r="2" stroke="currentColor" stroke-width="1.25" />
    </template>
    <template v-else-if="name === 'users'">
      <circle cx="5.5" cy="5.5" r="2" stroke="currentColor" stroke-width="1.25" />
      <circle cx="10.5" cy="5.5" r="2" stroke="currentColor" stroke-width="1.25" />
      <path
        d="M2.5 13c0-1.66 1.34-3 3-3h1c.55 0 1.05.15 1.5.4.45-.25.95-.4 1.5-.4h1c1.66 0 3 1.34 3 3"
        stroke="currentColor"
        stroke-width="1.25"
        stroke-linecap="round"
      />
    </template>
    <template v-else-if="name === 'star'">
      <path
        d="M8 2.8 9.55 6.2l3.7.55-2.68 2.6.63 3.65L8 11.1l-3.2 1.9.63-3.65-2.68-2.6 3.7-.55L8 2.8Z"
        stroke="currentColor"
        stroke-width="1.1"
        stroke-linejoin="round"
      />
    </template>
    <template v-else-if="name === 'chart'">
      <path
        d="M3 12.5v2.5h2.5M3 8v1.5h5M3 3.5v1.5h7.5M12 3.5v9l3 2 4.5-7"
        stroke="currentColor"
        stroke-width="1.25"
        stroke-linecap="round"
        stroke-linejoin="round"
      />
    </template>
    <template v-else-if="name === 'clock'">
      <circle cx="8" cy="8" r="5.25" stroke="currentColor" stroke-width="1.25" />
      <path
        d="M8 5v3.2l2.2 1.3"
        stroke="currentColor"
        stroke-width="1.25"
        stroke-linecap="round"
        stroke-linejoin="round"
      />
    </template>
    <template v-else-if="name === 'truck'">
      <path
        d="M2.5 11V6.5h6V11M8.5 6.5 11 4.5h2.5V11"
        stroke="currentColor"
        stroke-width="1.25"
        stroke-linejoin="round"
      />
      <circle cx="4.5" cy="11.5" r="1" fill="currentColor" />
      <circle cx="11.5" cy="11.5" r="1" fill="currentColor" />
    </template>
    <template v-else>
      <circle cx="8" cy="8" r="2.5" stroke="currentColor" stroke-width="1.25" />
      <path
        d="M8 2.5v1M8 12.5v1M2.5 8h1M12.5 8h1"
        stroke="currentColor"
        stroke-width="1.25"
        stroke-linecap="round"
      />
    </template>
  </svg>
</template>
