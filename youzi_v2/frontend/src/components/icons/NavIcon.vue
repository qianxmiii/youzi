<script setup lang="ts">
import type { FunctionalComponent } from 'vue'
import { computed } from 'vue'
import {
  BarChart3,
  BookOpen,
  Calculator,
  CircleDollarSign,
  ClipboardCheck,
  Clock,
  FileText,
  Globe,
  Layers,
  LayoutGrid,
  Library,
  MapPin,
  Package,
  Settings,
  Ship,
  Star,
  Truck,
  TriangleAlert,
  Users,
} from 'lucide-vue-next'
import type { LucideProps } from 'lucide-vue-next'
import { ICON_STROKE_NAV } from '@/constants/icons'

const props = defineProps<{ name: string }>()

const ICONS: Record<string, FunctionalComponent<LucideProps>> = {
  'group-workbench': LayoutGrid,
  'group-quote': CircleDollarSign,
  'group-library': Library,
  'group-shipment': Package,
  'group-customer': Users,
  'group-data': BarChart3,
  'group-approval': ClipboardCheck,
  'group-system': Settings,
  grid: LayoutGrid,
  box: Package,
  quote: FileText,
  layers: Layers,
  calc: Calculator,
  book: BookOpen,
  pin: MapPin,
  truck: Truck,
  alert: TriangleAlert,
  ship: Ship,
  chart: BarChart3,
  users: Users,
  approval: ClipboardCheck,
  clock: Clock,
  globe: Globe,
  settings: Settings,
  star: Star,
  wallet: CircleDollarSign,
}

const Icon = computed(() => ICONS[props.name] ?? Star)

const NAV_ICON_SIZE = 18
</script>

<template>
  <component
    :is="Icon"
    class="shrink-0 opacity-90"
    :size="NAV_ICON_SIZE"
    :stroke-width="ICON_STROKE_NAV"
    aria-hidden="true"
  />
</template>
