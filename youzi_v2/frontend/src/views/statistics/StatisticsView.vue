<script setup lang="ts">
import { NButton, NSpin, NTag } from 'naive-ui'
import { computed, onMounted, ref } from 'vue'
import DistributionBars from '@/components/statistics/DistributionBars.vue'
import {
  getShipmentStatisticsOverview,
  type ShipmentStatisticsOverview,
} from '@/api/statistics'

const loading = ref(false)
const data = ref<ShipmentStatisticsOverview | null>(null)
const error = ref('')

function statusTagType(key: string): 'default' | 'info' | 'warning' | 'error' {
  if (key === 'EXCEPTION') return 'warning'
  if (key === 'IN_TRANSIT') return 'info'
  return 'default'
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    data.value = await getShipmentStatisticsOverview()
  } catch (e) {
    data.value = null
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

const baselineSummary = computed(() => {
  const b = data.value?.transitBaseline
  if (!b?.available) return '需运单同时填写 ATD 与 ATA 后自动计算'
  const parts = [`样本 ${b.sampleCount} 单`, `均值 ${b.avgDays} 天`]
  if (b.stdDevDays != null) parts.push(`标准差 ${b.stdDevDays} 天`)
  if (b.minDays != null && b.maxDays != null) {
    parts.push(`区间 ${b.minDays}–${b.maxDays} 天`)
  }
  return parts.join(' · ')
})

onMounted(load)
</script>

<template>
  <div class="scrollbar-subtle flex h-full min-h-0 w-full flex-col gap-4 overflow-y-auto">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 class="page-h2">统计管理</h2>
        <p class="mt-1 text-xs text-zinc-500">
          基于当前库内全部运单聚合；状态分类互斥（异常 → 无轨迹 → 转运中 → 其它）。
        </p>
      </div>
      <NButton size="small" :loading="loading" @click="load">刷新</NButton>
    </div>

    <NSpin :show="loading">
      <div v-if="error" class="panel px-4 py-6 text-sm text-red-400">{{ error }}</div>
      <template v-else-if="data">
        <div
          class="grid gap-3 grid-cols-2 md:grid-cols-3 lg:grid-cols-5"
        >
          <article class="panel p-4">
            <p class="text-xs text-zinc-500">运单总数</p>
            <p class="mt-1 text-2xl font-semibold tabular-nums text-white">{{ data.total }}</p>
          </article>
          <article
            v-for="item in data.statusDistribution"
            :key="item.key"
            class="panel p-4"
          >
            <p class="text-xs text-zinc-500">{{ item.label }}</p>
            <p class="mt-1 text-2xl font-semibold tabular-nums text-white">
              {{ (item.ratio * 100).toFixed(1) }}%
            </p>
            <p class="mt-0.5 text-xs text-zinc-600">{{ item.count }} 单</p>
          </article>
        </div>

        <article class="panel p-4">
          <p class="text-xs text-zinc-500">时效基准线（预览）</p>
          <p class="mt-1 text-sm text-zinc-200">{{ baselineSummary }}</p>
          <p class="mt-1 text-[10px] text-zinc-600">{{ data.transitBaseline.description }}</p>
        </article>

        <div class="grid min-h-0 flex-1 gap-4 xl:grid-cols-2">
        <section class="panel p-4">
          <h3 class="mb-3 text-sm font-medium text-white">运单状态分布</h3>
          <div class="mb-4 flex flex-wrap gap-2">
            <NTag
              v-for="item in data.statusDistribution"
              :key="item.key"
              size="small"
              :bordered="false"
              :type="statusTagType(item.key)"
            >
              {{ item.label }} {{ (item.ratio * 100).toFixed(1) }}%（{{ item.count }}）
            </NTag>
          </div>
          <DistributionBars :items="data.statusDistribution" :total="data.total" />
        </section>

        <section class="grid gap-4">
          <article class="panel p-4">
            <h3 class="mb-1 text-sm font-medium text-white">海运渠道占比</h3>
            <p class="mb-3 text-[10px] text-zinc-600">
              渠道名含 Sea / Truck 的运单，共 {{ data.seaChannelTotal }} 单
            </p>
            <DistributionBars
              :items="data.seaChannelDistribution"
              :total="data.seaChannelTotal"
              empty-text="暂无海运渠道数据"
            />
          </article>
          <article class="panel p-4">
            <h3 class="mb-1 text-sm font-medium text-white">承运商占比</h3>
            <p class="mb-3 text-[10px] text-zinc-600">按运单 carrier_code 聚合</p>
            <DistributionBars
              :items="data.carrierDistribution"
              :total="data.total"
              empty-text="暂无承运商数据"
            />
          </article>
        </section>
        </div>

        <section class="panel p-4">
          <h3 class="mb-1 text-sm font-medium text-white">全部渠道占比</h3>
          <p class="mb-3 text-[10px] text-zinc-600">含空运、快递等所有 channel_code</p>
          <DistributionBars
            :items="data.channelDistribution"
            :total="data.total"
            empty-text="暂无渠道数据"
          />
        </section>

        <section class="panel border-dashed p-4">
          <h3 class="text-sm font-medium text-zinc-300">规划中</h3>
          <ul class="mt-2 list-disc space-y-1 pl-5 text-xs text-zinc-500">
            <li>按时间段、客户、国家筛选统计</li>
            <li>时效基准线分渠道/承运商拆分与趋势图</li>
            <li>异常类型、停滞天数分布</li>
          </ul>
        </section>
      </template>
    </NSpin>
  </div>
</template>
