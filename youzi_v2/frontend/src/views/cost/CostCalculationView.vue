<script setup lang="ts">
import { Copy, Plus, Trash2 } from 'lucide-vue-next'
import {
  NAutoComplete,
  NCheckbox,
  NInput,
  NInputNumber,
  NSelect,
} from 'naive-ui'
import { computed, ref, watch } from 'vue'
import {
  COMMON_PRODUCTS,
  DDP_KG_PRICE_OPTIONS,
  DEFAULT_GOODS_VALUE_USD,
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
  for (const row of ddpRows.value) {
    row.quantity = cargo.quantity
    row.weight = cargo.weight
    row.volume = cargo.volume
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

function addDdpRow() {
  ddpRows.value.push(createDdpRow())
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
</script>

<template>
  <div class="cost-page mx-auto max-w-[1600px] px-4 py-6">
    <header class="mb-6">
      <h1 class="text-xl font-bold text-[var(--color-fg-emphasis)]">成本计算</h1>
      <p class="mt-1 text-sm text-[var(--color-muted)]">
        自税（DDU）与包税（DDP）成本试算；公式与 Legacy costCalTab 一致
      </p>
    </header>

    <!-- 公共参数 -->
    <section class="panel mb-5 p-4">
      <h2 class="mb-4 text-sm font-semibold text-[var(--color-fg-emphasis)]">成本计算参数</h2>
      <div class="grid gap-4 md:grid-cols-2">
        <div class="md:col-span-2">
          <label class="mb-1 block text-xs font-medium text-[var(--color-muted)]">报价识别</label>
          <NInput
            v-model:value="cargoInput"
            placeholder="例如: 21ctns 8.3 kg 2.126 cbm 或 2ctns 10kg 50*40*30cm"
            clearable
          />
          <p class="mt-1 text-xs text-[var(--color-muted)]">支持自动识别箱数、重量、体积、尺寸</p>
        </div>
        <div>
          <label class="mb-1 block text-xs font-medium text-[var(--color-muted)]">常用产品</label>
          <div class="flex gap-2">
            <NSelect
              v-model:value="selectedProduct"
              :options="productOptions"
              placeholder="请选择产品"
              clearable
              class="flex-1"
            />
            <NInput
              :value="productHscode"
              readonly
              placeholder="海关编码"
              class="w-36"
            />
          </div>
        </div>
        <div>
          <label class="mb-1 block text-xs font-medium text-[var(--color-muted)]">重量比</label>
          <NSelect v-model:value="weightRatio" :options="WEIGHT_RATIO_OPTIONS" />
        </div>
      </div>
    </section>

    <!-- 自税 DDU -->
    <section class="panel mb-5 overflow-hidden">
      <div class="border-b border-[var(--color-border)] bg-[var(--color-btn-ghost-bg)] px-4 py-3">
        <h2 class="text-sm font-semibold text-[var(--color-fg-emphasis)]">自税成本计算 (DDU)</h2>
      </div>
      <div class="cost-table-wrap overflow-x-auto">
        <table class="cost-table">
          <thead>
            <tr>
              <th>实重(kg)</th>
              <th>体积(cbm)</th>
              <th>计费方(cbm)</th>
              <th>泡比</th>
              <th>按方表价(RMB)</th>
              <th>按方包税</th>
              <th>货值(USD)</th>
              <th>税率(%)<span class="tax-badge">+20%</span></th>
              <th>派送费(USD)</th>
              <th>头程费(RMB)</th>
              <th>派送费(RMB)</th>
              <th>税金(RMB)</th>
              <th class="col-emphasis">总成本(RMB)</th>
              <th>单价(cbm)</th>
              <th>单价(kg)</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>
                <NInputNumber v-model:value="ddu.weight" :min="0" size="small" class="w-full" />
              </td>
              <td>
                <NInputNumber
                  v-model:value="ddu.volume"
                  :min="0"
                  :precision="2"
                  size="small"
                  class="w-full"
                />
              </td>
              <td class="cell-out">{{ dduResult.chargeVolume }}</td>
              <td class="cell-out">{{ dduResult.volumeRatio }}</td>
              <td>
                <NInputNumber v-model:value="ddu.pricePerCbm" :min="0" size="small" class="w-full" />
              </td>
              <td>
                <div class="flex flex-col gap-1">
                  <NCheckbox v-model:checked="ddu.byVolumeTaxIncluded" size="small">
                    按方包税
                  </NCheckbox>
                  <NInputNumber
                    v-if="ddu.byVolumeTaxIncluded"
                    v-model:value="ddu.byVolumeTaxIncludedValue"
                    :min="0"
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
                  size="small"
                  class="w-full"
                />
              </td>
              <td>
                <NInputNumber
                  v-model:value="ddu.taxRate"
                  :min="0"
                  :precision="1"
                  size="small"
                  class="w-full"
                />
              </td>
              <td>
                <NInputNumber
                  v-model:value="ddu.deliveryFeeUsd"
                  :min="0"
                  size="small"
                  class="w-full"
                />
              </td>
              <td class="cell-out">{{ dduResult.forwardingCost }}</td>
              <td class="cell-out">{{ dduResult.deliveryFeeRmb }}</td>
              <td class="cell-out">{{ dduResult.taxAmount }}</td>
              <td class="cell-out col-emphasis">{{ dduResult.totalCost }}</td>
              <td class="cell-out">{{ dduResult.unitPriceCbm }}</td>
              <td class="cell-out">{{ dduResult.unitPriceKg }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p class="px-4 py-2 text-xs text-[var(--color-muted)]">
        DDU 汇率 {{ 7.1 }}（税金/派送费）；税金按实际体积 cbm 计算，另含基础关税 20%
      </p>
    </section>

    <!-- 包税 DDP -->
    <section class="panel overflow-hidden">
      <div class="border-b border-[var(--color-border)] bg-[var(--color-btn-ghost-bg)] px-4 py-3">
        <h2 class="text-sm font-semibold text-[var(--color-fg-emphasis)]">包税成本计算 (DDP)</h2>
      </div>
      <div class="cost-table-wrap overflow-x-auto">
        <table class="cost-table">
          <thead>
            <tr>
              <th>实重(kg)</th>
              <th>体积(cbm)</th>
              <th>计费重(kg)</th>
              <th>计费方(cbm)</th>
              <th>泡比</th>
              <th>按kg表价</th>
              <th>派送费(USD)</th>
              <th>派送费(RMB输入)</th>
              <th>头程费(RMB)</th>
              <th>派送费合计(RMB)</th>
              <th class="col-emphasis">总成本(RMB)</th>
              <th class="col-emphasis">单价(cbm)</th>
              <th class="col-emphasis">单价(kg)</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, index) in ddpRows" :key="row.key">
              <td>
                <NInputNumber v-model:value="row.weight" :min="0" size="small" class="w-full" />
              </td>
              <td>
                <NInputNumber
                  v-model:value="row.volume"
                  :min="0"
                  :precision="2"
                  size="small"
                  class="w-full"
                />
              </td>
              <td class="cell-out">{{ ddpResults[index]?.chargeWeight }}</td>
              <td class="cell-out">{{ ddpResults[index]?.chargeVolume }}</td>
              <td class="cell-out">{{ ddpResults[index]?.volumeRatio }}</td>
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
                  size="small"
                  class="w-full"
                />
              </td>
              <td>
                <NInputNumber
                  v-model:value="row.deliveryFeeRmb"
                  :min="0"
                  size="small"
                  class="w-full"
                />
              </td>
              <td class="cell-out">{{ ddpResults[index]?.forwardingCost }}</td>
              <td class="cell-out">{{ ddpResults[index]?.deliveryFeeTotal }}</td>
              <td class="cell-out col-emphasis">{{ ddpResults[index]?.totalCost }}</td>
              <td class="cell-out col-emphasis">{{ ddpResults[index]?.unitPriceCbm }}</td>
              <td class="cell-out col-emphasis">{{ ddpResults[index]?.unitPriceKg }}</td>
              <td>
                <div class="flex gap-1">
                  <button
                    type="button"
                    class="cost-row-btn cost-row-btn--add"
                    title="新增行"
                    @click="addDdpRow"
                  >
                    <Plus class="h-3.5 w-3.5" />
                  </button>
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
      <p class="px-4 py-2 text-xs text-[var(--color-muted)]">
        DDP 汇率 {{ 6.8 }}（USD 派送费折算）；计费重 = max(实重, 体积×10⁶/6000)
      </p>
    </section>
  </div>
</template>

<style scoped>
.cost-table {
  width: 100%;
  min-width: 1200px;
  border-collapse: collapse;
  font-size: 13px;
}

.cost-table th,
.cost-table td {
  border: 1px solid var(--color-border);
  padding: 0.5rem 0.375rem;
  text-align: center;
  vertical-align: middle;
  white-space: nowrap;
}

.cost-table th {
  background: var(--color-btn-ghost-bg);
  color: var(--color-fg-secondary);
  font-weight: 600;
  font-size: 12px;
}

.cell-out {
  font-variant-numeric: tabular-nums;
  color: var(--color-fg);
}

.col-emphasis {
  font-weight: 700;
}

.tax-badge {
  display: inline-block;
  margin-left: 0.25rem;
  border-radius: 0.25rem;
  background: var(--color-badge-bg);
  padding: 0 0.25rem;
  font-size: 10px;
  color: var(--color-badge-fg);
}

.cost-row-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 1.75rem;
  width: 1.75rem;
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

.cost-row-btn--add {
  color: rgb(22 163 74);
}

.cost-row-btn--danger {
  color: rgb(220 38 38);
}

.cost-table :deep(.n-input-number),
.cost-table :deep(.n-auto-complete) {
  min-width: 72px;
}
</style>
