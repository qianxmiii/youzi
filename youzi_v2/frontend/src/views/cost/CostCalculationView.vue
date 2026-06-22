<script setup lang="ts">
import { Copy, Plus, Trash2 } from 'lucide-vue-next'
import {
  NAutoComplete,
  NButton,
  NCheckbox,
  NInput,
  NInputNumber,
  NSelect,
} from 'naive-ui'
import { computed, ref, watch } from 'vue'
import {
  COMMON_PRODUCTS,
  COST_EXCHANGE_RATE,
  DDP_KG_PRICE_OPTIONS,
  DEFAULT_GOODS_VALUE_USD,
  EXCHANGE_RATE,
  WEIGHT_RATIO_OPTIONS,
  type WeightRatio,
} from '@/constants/costCalculation'
import {
  calculateDdpRow,
  calculateDdu,
  parseCargoText,
} from '@/domain/costCalculation'

let rowSeq = 1

function createDdpRow() {
  return {
    key: rowSeq++,
    quantity: 0,
    weight: 0,
    volume: 0,
    pricePerKg: 0,
    deliveryFeeUsd: 0,
    deliveryFeeRmb: 0,
  }
}

const cargoInput = ref('')
const weightRatio = ref<WeightRatio>('363')
const selectedProduct = ref<string | null>(null)
const productHscode = ref('')

const ddu = ref({
  quantity: 0,
  weight: 0,
  volume: 0,
  pricePerCbm: 0,
  byVolumeTaxIncluded: false,
  byVolumeTaxIncludedValue: 0,
  goodsValue: DEFAULT_GOODS_VALUE_USD,
  taxRate: 0,
  deliveryFeeUsd: 0,
})

const ddpRows = ref([createDdpRow()])

const productOptions = COMMON_PRODUCTS.map((p) => ({
  label: p.name,
  value: p.name,
}))

const kgPriceOptions = DDP_KG_PRICE_OPTIONS.map((o) => ({
  label: `${o.label} (${o.price})`,
  value: `${o.label} (${o.price})`,
}))

function resolveKgPrice(value: string): number {
  const preset = DDP_KG_PRICE_OPTIONS.find(
    (o) => value === String(o.price) || value.startsWith(o.label),
  )
  if (preset) return preset.price
  const price = Number.parseFloat(value)
  return Number.isFinite(price) ? price : 0
}

function applyCargoToForms(cargo: ReturnType<typeof parseCargoText>) {
  ddu.value.quantity = cargo.quantity
  ddu.value.weight = cargo.weight
  ddu.value.volume = cargo.volume
  syncCargoToDdpRows()
}

function syncCargoToDdpRows() {
  const { quantity, weight, volume } = ddu.value
  for (const row of ddpRows.value) {
    row.quantity = quantity
    row.weight = weight
    row.volume = volume
  }
}

function clearCargoFromForms() {
  applyCargoToForms({ quantity: 0, weight: 0, volume: 0 })
}

watch(cargoInput, (text) => {
  if (!text.trim()) {
    clearCargoFromForms()
    return
  }
  applyCargoToForms(parseCargoText(text))
})

watch(
  () => [ddu.value.weight, ddu.value.volume, ddu.value.quantity] as const,
  () => syncCargoToDdpRows(),
)

watch(selectedProduct, (name) => {
  if (!name) {
    productHscode.value = ''
    ddu.value.taxRate = 0
    return
  }
  const product = COMMON_PRODUCTS.find((p) => p.name === name)
  if (!product) return
  productHscode.value = product.hscode
  ddu.value.taxRate = Number.parseFloat(product.taxrate) || 0
})

watch(
  () => ddu.value.byVolumeTaxIncluded,
  (enabled, wasEnabled) => {
    if (enabled) {
      ddu.value.goodsValue = 0
      return
    }
    if (wasEnabled && (ddu.value.goodsValue === 0 || ddu.value.goodsValue === null)) {
      ddu.value.goodsValue = DEFAULT_GOODS_VALUE_USD
    }
  },
)

const dduResult = computed(() =>
  calculateDdu({
    ...ddu.value,
    weightRatio: weightRatio.value,
  }),
)

const ddpResults = computed(() =>
  ddpRows.value.map((row) =>
    calculateDdpRow({
      quantity: row.quantity,
      weight: row.weight,
      volume: row.volume,
      pricePerKg: row.pricePerKg,
      deliveryFeeUsd: row.deliveryFeeUsd,
      deliveryFeeRmb: row.deliveryFeeRmb,
      weightRatio: weightRatio.value,
    }),
  ),
)

const sharedDdpMetrics = computed(() =>
  calculateDdpRow({
    quantity: ddu.value.quantity,
    weight: ddu.value.weight,
    volume: ddu.value.volume,
    pricePerKg: 0,
    deliveryFeeUsd: 0,
    deliveryFeeRmb: 0,
    weightRatio: weightRatio.value,
  }),
)

const cargoParsed = computed(() => Boolean(cargoInput.value.trim()))

function addDdpRow() {
  const row = createDdpRow()
  row.quantity = ddu.value.quantity
  row.weight = ddu.value.weight
  row.volume = ddu.value.volume
  ddpRows.value.push(row)
}

function copyDdpRow(index: number) {
  const source = ddpRows.value[index]
  if (!source) return
  ddpRows.value.push({
    ...createDdpRow(),
    quantity: source.quantity,
    weight: source.weight,
    volume: source.volume,
    pricePerKg: source.pricePerKg,
    deliveryFeeUsd: source.deliveryFeeUsd,
    deliveryFeeRmb: source.deliveryFeeRmb,
  })
}

function deleteDdpRow(index: number) {
  if (ddpRows.value.length <= 1) return
  ddpRows.value.splice(index, 1)
}

function onKgPriceInput(index: number, value: string) {
  ddpRows.value[index].pricePerKg = resolveKgPrice(value)
}

function displayQty(value: number): string {
  return value > 0 ? String(value) : '—'
}
</script>

<template>
  <div class="cost-page mx-auto max-w-[1600px] px-4 py-6">
    <header class="mb-5">
      <h1 class="text-xl font-bold text-[var(--color-fg-emphasis)]">成本计算</h1>
      <p class="mt-1 text-sm text-[var(--color-muted)]">
        粘贴报价识别货况，对比自税（DDU）与包税（DDP）方案
      </p>
    </header>

    <!-- 货况 + 公共参数 -->
    <section class="panel mb-5 p-4">
      <div class="mb-4">
        <label class="mb-1.5 block text-xs font-medium text-[var(--color-muted)]">报价识别</label>
        <NInput
          v-model:value="cargoInput"
          placeholder="例如: 21ctns 8.3 kg 2.126 cbm 或 2ctns 10kg 50*40*30cm"
          clearable
        />
        <p class="mt-1 text-xs text-[var(--color-muted)]">支持自动识别箱数、重量、体积、尺寸</p>
      </div>

      <div class="cost-cargo-strip">
        <div class="cost-cargo-strip__title">货况</div>
        <div class="cost-cargo-metrics">
          <div class="cost-metric">
            <span class="cost-metric__label">箱数</span>
            <span class="cost-metric__value" :class="{ 'is-empty': !ddu.quantity }">
              {{ displayQty(ddu.quantity) }}
            </span>
          </div>
          <div class="cost-metric cost-metric--input">
            <span class="cost-metric__label">实重 (kg)</span>
            <NInputNumber
              v-model:value="ddu.weight"
              :min="0"
              :show-button="false"
              size="small"
              class="cost-metric__input"
            />
          </div>
          <div class="cost-metric cost-metric--input">
            <span class="cost-metric__label">体积 (cbm)</span>
            <NInputNumber
              v-model:value="ddu.volume"
              :min="0"
              :precision="2"
              :show-button="false"
              size="small"
              class="cost-metric__input"
            />
          </div>
          <div class="cost-metric">
            <span class="cost-metric__label">计费方 (cbm)</span>
            <span class="cost-metric__value cost-metric__value--computed">{{ dduResult.chargeVolume }}</span>
          </div>
          <div class="cost-metric">
            <span class="cost-metric__label">泡比</span>
            <span class="cost-metric__value cost-metric__value--computed">{{ dduResult.volumeRatio }}</span>
          </div>
        </div>
        <p
          v-if="cargoParsed && !ddu.weight && !ddu.volume"
          class="cost-cargo-strip__hint cost-cargo-strip__hint--warn"
        >
          未能识别重量或体积，请检查报价格式或手动填写
        </p>
      </div>

      <div class="mt-4 grid gap-4 md:grid-cols-2">
        <div>
          <label class="mb-1.5 block text-xs font-medium text-[var(--color-muted)]">常用产品</label>
          <div class="flex gap-2">
            <NSelect
              v-model:value="selectedProduct"
              :options="productOptions"
              placeholder="请选择产品"
              clearable
              class="flex-1"
            />
            <NInput :value="productHscode" readonly placeholder="海关编码" class="w-36" />
          </div>
        </div>
        <div>
          <label class="mb-1.5 block text-xs font-medium text-[var(--color-muted)]">重量比</label>
          <NSelect v-model:value="weightRatio" :options="WEIGHT_RATIO_OPTIONS" />
        </div>
      </div>
    </section>

    <!-- DDU / DDP 计算器卡片 -->
    <div class="cost-schemes">
      <!-- 自税 DDU -->
      <section class="cost-card panel">
        <header class="cost-card__header cost-card__header--ddu">
          <div class="min-w-0">
            <h2 class="cost-card__title">自税 (DDU)</h2>
            <p class="cost-card__subtitle">
              汇率 {{ COST_EXCHANGE_RATE }} · 计费方 {{ dduResult.chargeVolume }} cbm · 泡比
              {{ dduResult.volumeRatio }} · 税金按实际体积 · 含基础关税 20%
            </p>
          </div>
        </header>

        <div class="cost-card__body cost-card__body--table">
          <div class="cost-scheme-table-wrap">
            <table class="cost-scheme-table">
              <thead>
                <tr>
                  <th>按方表价</th>
                  <th>按方包税</th>
                  <th>货值 (USD)</th>
                  <th>税率 (%)<span class="cost-tax-badge">+20%</span></th>
                  <th>派送 (USD)</th>
                  <th>头程费</th>
                  <th>派送费</th>
                  <th>税金</th>
                  <th class="col-result">总成本</th>
                  <th>单价/cbm</th>
                  <th>单价/kg</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>
                    <NInputNumber
                      v-model:value="ddu.pricePerCbm"
                      :min="0"
                      :show-button="false"
                      size="small"
                      class="w-full"
                    />
                  </td>
                  <td>
                    <div class="cost-cell-stack">
                      <NCheckbox v-model:checked="ddu.byVolumeTaxIncluded" size="small">
                        按方包税
                      </NCheckbox>
                      <NInputNumber
                        v-if="ddu.byVolumeTaxIncluded"
                        v-model:value="ddu.byVolumeTaxIncludedValue"
                        :min="0"
                        :show-button="false"
                        size="small"
                        class="w-full"
                        placeholder="附加值"
                      />
                    </div>
                  </td>
                  <td>
                    <NInputNumber
                      v-model:value="ddu.goodsValue"
                      :min="0"
                      :disabled="ddu.byVolumeTaxIncluded"
                      :show-button="false"
                      size="small"
                      class="w-full"
                    />
                  </td>
                  <td>
                    <NInputNumber
                      v-model:value="ddu.taxRate"
                      :min="0"
                      :precision="1"
                      :show-button="false"
                      size="small"
                      class="w-full"
                    />
                  </td>
                  <td>
                    <NInputNumber
                      v-model:value="ddu.deliveryFeeUsd"
                      :min="0"
                      :show-button="false"
                      size="small"
                      class="w-full"
                    />
                  </td>
                  <td class="cell-out">¥{{ dduResult.forwardingCost }}</td>
                  <td class="cell-out">¥{{ dduResult.deliveryFeeRmb }}</td>
                  <td class="cell-out">¥{{ dduResult.taxAmount }}</td>
                  <td class="cell-out col-result">¥{{ dduResult.totalCost }}</td>
                  <td class="cell-out">¥{{ dduResult.unitPriceCbm }}</td>
                  <td class="cell-out">¥{{ dduResult.unitPriceKg }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <!-- 包税 DDP -->
      <section class="cost-card panel">
        <header class="cost-card__header cost-card__header--ddp">
          <div class="min-w-0">
            <h2 class="cost-card__title">包税 (DDP)</h2>
            <p class="cost-card__subtitle">
              汇率 {{ EXCHANGE_RATE }} · 计费重 {{ sharedDdpMetrics.chargeWeight }} kg · 计费方
              {{ sharedDdpMetrics.chargeVolume }} cbm · 泡比 {{ sharedDdpMetrics.volumeRatio }}
            </p>
          </div>
          <NButton size="small" type="primary" @click="addDdpRow">
            <template #icon>
              <Plus class="h-3.5 w-3.5" />
            </template>
            添加比价行
          </NButton>
        </header>

        <div class="cost-card__body cost-card__body--table">
          <div class="cost-scheme-table-wrap">
            <table class="cost-scheme-table">
              <thead>
                <tr>
                  <th>按 kg 表价</th>
                  <th>派送 (USD)</th>
                  <th>派送 (RMB)</th>
                  <th>头程费</th>
                  <th>派送合计</th>
                  <th class="col-result">总成本</th>
                  <th>单价/cbm</th>
                  <th>单价/kg</th>
                  <th class="col-actions">操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, index) in ddpRows" :key="row.key">
                  <td>
                    <NAutoComplete
                      :value="row.pricePerKg ? String(row.pricePerKg) : ''"
                      :options="kgPriceOptions"
                      placeholder="手输或选择"
                      size="small"
                      @update:value="(v) => onKgPriceInput(index, v)"
                    />
                  </td>
                  <td>
                    <NInputNumber
                      v-model:value="row.deliveryFeeUsd"
                      :min="0"
                      :show-button="false"
                      size="small"
                      class="w-full"
                    />
                  </td>
                  <td>
                    <NInputNumber
                      v-model:value="row.deliveryFeeRmb"
                      :min="0"
                      :show-button="false"
                      size="small"
                      class="w-full"
                    />
                  </td>
                  <td class="cell-out">{{ ddpResults[index]?.forwardingCost }}</td>
                  <td class="cell-out">{{ ddpResults[index]?.deliveryFeeTotal }}</td>
                  <td class="cell-out col-result">¥{{ ddpResults[index]?.totalCost }}</td>
                  <td class="cell-out">¥{{ ddpResults[index]?.unitPriceCbm }}</td>
                  <td class="cell-out">¥{{ ddpResults[index]?.unitPriceKg }}</td>
                  <td class="col-actions">
                    <div class="flex justify-center gap-1">
                      <button
                        type="button"
                        class="cost-row-btn"
                        title="复制行"
                        @click="copyDdpRow(index)"
                      >
                        <Copy class="h-3.5 w-3.5" />
                      </button>
                      <button
                        type="button"
                        class="cost-row-btn cost-row-btn--danger"
                        title="删除行"
                        :disabled="ddpRows.length <= 1"
                        @click="deleteDdpRow(index)"
                      >
                        <Trash2 class="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <p class="cost-scheme-footnote">
            计费重 = max(实重, 体积×10⁶/6000)；多行用于对比不同 kg 表价方案
          </p>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.cost-cargo-strip {
  border-radius: 0.625rem;
  border: 1px solid var(--color-border);
  background: var(--color-btn-ghost-bg);
  padding: 0.75rem 1rem;
}

.cost-cargo-strip__title {
  margin-bottom: 0.625rem;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--color-muted);
}

.cost-cargo-metrics {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem 1.25rem;
  align-items: flex-end;
}

.cost-metric {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  min-width: 4.5rem;
}

.cost-metric--input {
  min-width: 6.5rem;
}

.cost-metric__label {
  font-size: 11px;
  color: var(--color-muted);
}

.cost-metric__value {
  font-size: 0.9375rem;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  color: var(--color-fg-emphasis);
}

.cost-metric__value.is-empty {
  color: var(--color-muted);
  font-weight: 500;
}

.cost-metric__value--computed {
  color: var(--color-fg);
}

.cost-metric__input {
  width: 6.5rem;
}

.cost-cargo-strip__hint {
  margin-top: 0.625rem;
  font-size: 11px;
  color: var(--color-muted);
}

.cost-cargo-strip__hint--warn {
  color: rgb(234 88 12);
}

.cost-schemes {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.cost-card {
  overflow: hidden;
}

.cost-card__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
  border-bottom: 1px solid var(--color-border);
  padding: 0.875rem 1rem;
}

.cost-card__header--ddu {
  background: linear-gradient(
    135deg,
    rgb(59 130 246 / 0.08) 0%,
    transparent 60%
  );
}

.cost-card__header--ddp {
  background: linear-gradient(
    135deg,
    rgb(34 197 94 / 0.08) 0%,
    transparent 60%
  );
}

.cost-card__title {
  font-size: 0.9375rem;
  font-weight: 700;
  color: var(--color-fg-emphasis);
}

.cost-card__subtitle {
  margin-top: 0.125rem;
  font-size: 11px;
  color: var(--color-muted);
  line-height: 1.4;
}

.cost-card__body--table {
  padding: 0;
}

.cost-tax-badge {
  display: inline-block;
  margin-left: 0.25rem;
  border-radius: 0.25rem;
  background: var(--color-badge-bg);
  padding: 0 0.3rem;
  font-size: 10px;
  font-weight: 500;
  color: var(--color-badge-fg);
  vertical-align: middle;
}

.cost-cell-stack {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.375rem;
  min-width: 5.5rem;
}

.cost-scheme-table-wrap {
  overflow-x: auto;
}

.cost-scheme-table {
  width: 100%;
  min-width: 720px;
  border-collapse: collapse;
  font-size: 12px;
}

.cost-scheme-table th,
.cost-scheme-table td {
  border-bottom: 1px solid var(--color-border);
  padding: 0.5rem 0.5rem;
  text-align: center;
  vertical-align: middle;
}

.cost-scheme-table th {
  background: var(--color-btn-ghost-bg);
  color: var(--color-fg-secondary);
  font-weight: 600;
  font-size: 11px;
  white-space: nowrap;
}

.cost-scheme-table tbody tr:last-child td {
  border-bottom: none;
}

.cost-scheme-table tbody tr:hover {
  background: var(--color-btn-ghost-bg);
}

.cell-out {
  font-variant-numeric: tabular-nums;
  color: var(--color-fg);
  white-space: nowrap;
}

.col-result {
  font-weight: 700;
  color: var(--color-fg-emphasis);
}

.col-actions {
  width: 4.5rem;
}

.cost-scheme-footnote {
  padding: 0.625rem 1rem;
  font-size: 11px;
  color: var(--color-muted);
  border-top: 1px solid var(--color-border);
}

.cost-row-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 1.625rem;
  width: 1.625rem;
  border-radius: 0.375rem;
  border: 1px solid var(--color-border);
  background: var(--color-panel);
  color: var(--color-fg-secondary);
  cursor: pointer;
}

.cost-row-btn:hover:not(:disabled) {
  background: var(--color-btn-ghost-hover);
}

.cost-row-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.cost-row-btn--danger {
  color: rgb(220 38 38);
}

.cost-scheme-table :deep(.n-input-number),
.cost-scheme-table :deep(.n-auto-complete) {
  min-width: 4.5rem;
}
</style>
