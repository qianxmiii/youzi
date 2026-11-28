import { ref } from 'vue'

export const carrierVisible = ref(false)

export function displayCarrier(value: string | null | undefined): string {
  return carrierVisible.value ? value?.trim() || '—' : '***'
}
