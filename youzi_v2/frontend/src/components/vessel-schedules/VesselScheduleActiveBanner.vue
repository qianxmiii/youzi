<script setup lang="ts">
import { Ship } from 'lucide-vue-next'
import { ICON_STROKE } from '@/constants/icons'
import { computed } from 'vue'
import type { VoyagePortCall } from '@/types/vesselSchedule'
import { formatDateYmd } from '@/utils/formatDateTime'
import { formatPortDisplay } from '@/utils/portDisplay'

const props = defineProps<{
  vesselName: string
  voyageNo: string
  shippingCompany: string | null
  portCalls: VoyagePortCall[]
}>()

function carrierInitials(company: string | null): string {
  const raw = (company || '').trim()
  if (!raw) return '—'
  const words = raw.split(/\s+/).filter(Boolean)
  if (words.length >= 2) {
    return (words[0][0] + words[1][0]).toUpperCase()
  }
  return raw.slice(0, 2).toUpperCase()
}

const nextPort = computed(() => {
  const calls = [...props.portCalls].sort((a, b) => a.sequence - b.sequence)
  if (!calls.length) return null
  const upcoming = calls.find(
    (pc) =>
      !pc.ata &&
      (pc.status === 'arriving_soon' ||
        pc.status === 'departing_soon' ||
        pc.status === 'planned' ||
        pc.status === 'in_transit' ||
        pc.status === 'unknown'),
  )
  if (upcoming) return upcoming
  const withoutAta = calls.find((pc) => !pc.ata)
  return withoutAta ?? calls[calls.length - 1]
})

const nextEta = computed(() => nextPort.value?.eta ?? nextPort.value?.etd ?? null)
</script>

<template>
  <section class="vessel-banner" aria-label="当前船舶">
    <div class="vessel-banner__ship-deco" aria-hidden="true">
      <Ship class="vessel-banner__ship-svg" :stroke-width="ICON_STROKE" aria-hidden="true" />
    </div>
    <div class="vessel-banner__grid">
      <div class="vessel-banner__cell">
        <p class="vessel-banner__label">ACTIVE VESSEL</p>
        <p class="vessel-banner__value vessel-banner__value--lg">{{ vesselName || '—' }}</p>
      </div>
      <div class="vessel-banner__cell vessel-banner__cell--divider">
        <p class="vessel-banner__label">VOYAGE ID</p>
        <p class="vessel-banner__value vessel-banner__value--lg">{{ voyageNo || '—' }}</p>
      </div>
      <div class="vessel-banner__cell vessel-banner__cell--divider">
        <p class="vessel-banner__label">CARRIER</p>
        <div class="vessel-banner__carrier">
          <span class="vessel-banner__carrier-logo" aria-hidden="true">{{ carrierInitials(shippingCompany) }}</span>
          <span class="vessel-banner__value vessel-banner__value--wrap">{{ shippingCompany || '—' }}</span>
        </div>
      </div>
      <div class="vessel-banner__cell vessel-banner__cell--next vessel-banner__cell--divider">
        <p class="vessel-banner__label">Next Destination</p>
        <p class="vessel-banner__value vessel-banner__value--lg">
          {{ nextPort ? formatPortDisplay(nextPort) : '—' }}
        </p>
        <p class="vessel-banner__eta">ETA: {{ formatDateYmd(nextEta) }}</p>
      </div>
    </div>
  </section>
</template>

<style scoped>
.vessel-banner {
  position: relative;
  overflow: visible;
  border-radius: 0.75rem;
  background: linear-gradient(135deg, rgb(70 72 212) 0%, rgb(88 90 220) 48%, rgb(70 72 212) 100%);
  min-height: 7.5rem;
  padding: 1.5rem 11rem 1.5rem 2rem;
  color: #fff;
  transition:
    transform 0.15s ease,
    box-shadow 0.15s ease;
}

.vessel-banner:hover {
  transform: translateY(-2px);
  box-shadow:
    0 4px 8px rgb(70 72 212 / 0.2),
    0 12px 28px rgb(70 72 212 / 0.28);
}

.vessel-banner__ship-deco {
  position: absolute;
  right: 2rem;
  top: 50%;
  transform: translateY(-50%);
  opacity: 0.12;
  pointer-events: none;
}

.vessel-banner__ship-svg {
  width: 8.5rem;
  height: 3.25rem;
  color: #fff;
}

.vessel-banner__grid {
  position: relative;
  z-index: 1;
  display: grid;
  gap: 1.25rem 2rem;
  align-items: start;
}

@media (min-width: 900px) {
  .vessel-banner__grid {
    grid-template-columns: minmax(10rem, 1.15fr) minmax(8rem, 0.95fr) minmax(10rem, 1.1fr) minmax(12rem, 1.35fr);
  }
}

@media (max-width: 899px) {
  .vessel-banner {
    padding-right: 2rem;
  }
}

.vessel-banner__cell--divider {
  border-left: 1px solid rgb(255 255 255 / 0.22);
  padding-left: 2rem;
}

@media (max-width: 899px) {
  .vessel-banner__cell--divider {
    border-left: none;
    padding-left: 0;
    border-top: 1px solid rgb(255 255 255 / 0.22);
    padding-top: 1.25rem;
  }
}

.vessel-banner__cell--next {
  min-width: 0;
}

@media (min-width: 900px) {
  .vessel-banner__cell--next {
    text-align: right;
  }
}

.vessel-banner__label {
  margin: 0;
  font-size: 0.625rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  opacity: 0.85;
}

.vessel-banner__value {
  margin: 0.375rem 0 0;
  font-size: 0.9375rem;
  font-weight: 600;
  line-height: 1.4;
}

.vessel-banner__value--lg {
  font-size: 1.5rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  word-break: break-word;
}

.vessel-banner__value--wrap {
  word-break: break-word;
}

.vessel-banner__carrier {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  margin-top: 0.375rem;
}

.vessel-banner__carrier-logo {
  display: inline-flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 1.75rem;
  height: 1.75rem;
  border-radius: 0.375rem;
  background: rgb(255 255 255 / 0.2);
  font-size: 0.6875rem;
  font-weight: 700;
}

.vessel-banner__eta {
  margin: 0.375rem 0 0;
  font-size: 0.8125rem;
  opacity: 0.9;
}
</style>
