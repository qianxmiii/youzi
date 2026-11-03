<script setup lang="ts">
import { NButton, NDatePicker, NInput, NInputNumber, NModal, NRadio, NRadioGroup, NSelect, NSpace } from 'naive-ui'
import { computed, ref, watch } from 'vue'
import {
  createQuoteOpportunity,
  listCustomerQuotedProducts,
  parseQuotePaste,
  updateQuoteContent,
  type CustomerQuotedProduct,
  type QuoteDestination,
  type QuoteLine,
  type QuoteOpportunity,
} from '@/api/quoteOpportunities'
import { DEFAULT_USD_CNY_RATE, formatMoney, formatProfitRate, moneyUnitLabel, priceUnitLabel, quoteProfitMoney, quoteProfitRate, quoteSellingTotal } from '@/constants/quoteFollowup'

const props = defineProps<{
  show: boolean
  customers: { label: string; value: string; raw: { customerName: string } }[]
  quote?: QuoteOpportunity | null
}>()
const emit = defineEmits<{ 'update:show': [value: boolean]; saved: []; manual: [] }>()

const sourceText = ref('')
const parsing = ref(false)
const saving = ref(false)
const errorText = ref('')
const unrecognized = ref<string[]>([])
const destinations = ref<QuoteDestination[]>([])
const summaryCtns = ref<number | null>(null)
const summaryWeightKg = ref<number | null>(null)
const summaryVolumeCbm = ref<number | null>(null)
const pickupFee = ref<number | null>(null)
const pickupCurrency = ref('USD')
const customerSource = ref<'existing' | 'new'>('existing')
const customerId = ref<string | null>(null)
const customerName = ref('')
const productName = ref('')
const inquiryNote = ref('')
const profitAmount = ref<number | null>(null)
const profitUnit = ref('RMB/KG')
const exchangeRate = ref(DEFAULT_USD_CNY_RATE)
const previousProducts = ref<CustomerQuotedProduct[]>([])
const quoteDate = ref<number | null>(Date.now())

const showModel = computed({
  get: () => props.show,
  set: (value: boolean) => emit('update:show', value),
})

const lineCtns = computed(() => sum(destinations.value.map((row) => row.ctns)))
const lineWeight = computed(() => sum(destinations.value.map((row) => row.weightKg)))
const lineVolume = computed(() => sum(destinations.value.map((row) => row.volumeCbm)))
const sellingPreview = computed(() =>
  quoteSellingTotal(destinations.value.flatMap((dest) => dest.channels)),
)
const profitPreview = computed(() => {
  const lines = destinations.value.flatMap((dest) => dest.channels)
  return quoteProfitMoney(
    profitAmount.value,
    profitUnit.value,
    lines,
    sellingPreview.value?.currency,
    exchangeRate.value,
  )
})
const profitRatePreview = computed(() =>
  quoteProfitRate(
    profitPreview.value?.amount,
    profitPreview.value?.currency,
    sellingPreview.value?.amount,
    sellingPreview.value?.currency,
  ),
)
const totalsDiffer = computed(
  () =>
    differs(lineCtns.value, summaryCtns.value) ||
    differs(lineWeight.value, summaryWeightKg.value) ||
    differs(lineVolume.value, summaryVolumeCbm.value),
)

function sum(values: Array<number | null>) {
  const nums = values.filter((value): value is number => value != null && Number.isFinite(value))
  return nums.length ? nums.reduce((total, value) => total + value, 0) : null
}

function differs(left: number | null, right: number | null) {
  if (left == null || right == null) return false
  return Math.abs(left - right) > 0.001
}

function applyDays(channel: QuoteDestination['channels'][number], value: string) {
  const match = value.trim().match(/^(\d+)\s*-\s*(\d+)$/)
  channel.transitDaysMin = match ? Number(match[1]) : null
  channel.transitDaysMax = match ? Number(match[2]) : null
}

function formatNum(value: number | null) {
  return value == null ? '—' : String(Math.round(value * 1000) / 1000)
}

function chargeUnit(channel: QuoteDestination['channels'][number]) {
  return (channel.priceBasis || '').trim().toLowerCase()
}

function ensureChannels(rows: QuoteDestination[]) {
  for (const row of rows) {
    if (row.channels.length) continue
    row.channels.push({
      tradeTerm: '',
      channelName: '',
      unitPrice: null,
      chargeWeightKg: null,
      quotedAmount: null,
      quotedCurrency: '',
      priceBasis: '',
      transitDaysMin: null,
      transitDaysMax: null,
      note: '',
    })
  }
  return rows
}

function linesToDestinations(lines: QuoteLine[]): QuoteDestination[] {
  const rows: QuoteDestination[] = []
  for (const line of lines) {
    const channel = {
      tradeTerm: line.tradeTerm,
      channelName: line.channelName,
      unitPrice: line.unitPrice,
      chargeWeightKg: line.chargeWeightKg,
      quotedAmount: line.quotedAmount,
      quotedCurrency: line.quotedCurrency || 'USD',
      transitDaysMin: line.transitDaysMin,
      transitDaysMax: line.transitDaysMax,
      note: line.note,
      priceBasis: line.priceBasis || '',
    }
    const last = rows[rows.length - 1]
    if (last && last.addressCode === line.addressCode) {
      last.channels.push(channel)
      continue
    }
    rows.push({
      addressCode: line.addressCode,
      ctns: line.ctns,
      weightKg: line.weightKg,
      volumeCbm: line.volumeCbm,
      channels: [channel],
    })
  }
  return rows
}

function dateToTs(value: string | null | undefined) {
  if (!value) return Date.now()
  const [year, month, day] = value.slice(0, 10).split('-').map(Number)
  if (!year || !month || !day) return Date.now()
  return new Date(year, month - 1, day).getTime()
}

function resetForm() {
  sourceText.value = ''
  unrecognized.value = []
  destinations.value = []
  summaryCtns.value = null
  summaryWeightKg.value = null
  summaryVolumeCbm.value = null
  pickupFee.value = null
  pickupCurrency.value = 'USD'
  customerSource.value = 'existing'
  customerId.value = null
  customerName.value = ''
  productName.value = ''
  inquiryNote.value = ''
  profitAmount.value = null
  profitUnit.value = 'RMB/KG'
  exchangeRate.value = DEFAULT_USD_CNY_RATE
  quoteDate.value = Date.now()
  errorText.value = ''
}

function channelsAreBlank(rows: QuoteDestination[]) {
  return rows.every((row) =>
    row.channels.every((channel) => !channel.channelName && channel.unitPrice == null && channel.quotedAmount == null),
  )
}

async function fillFromQuote(quote: QuoteOpportunity) {
  sourceText.value = quote.sourceText || ''
  unrecognized.value = []
  destinations.value = ensureChannels(linesToDestinations(quote.lines || []))
  summaryCtns.value = quote.ctns
  summaryWeightKg.value = quote.weightKg
  summaryVolumeCbm.value = quote.volumeCbm
  pickupFee.value = quote.pickupFee ?? null
  pickupCurrency.value = quote.pickupFeeCurrency || 'USD'
  customerSource.value = quote.customerId ? 'existing' : 'new'
  customerId.value = quote.customerId || null
  customerName.value = quote.customerId ? '' : quote.customerName
  productName.value = quote.productName || ''
  inquiryNote.value = quote.note || ''
  profitAmount.value = quote.currentProfitAmount
  profitUnit.value = quote.profitUnit || 'RMB/KG'
  exchangeRate.value = quote.exchangeRate && quote.exchangeRate > 0 ? quote.exchangeRate : DEFAULT_USD_CNY_RATE
  quoteDate.value = dateToTs(quote.quoteDate)
  errorText.value = ''
  if (!channelsAreBlank(destinations.value) || !quote.sourceText?.trim()) return
  try {
    const parsed = await parseQuotePaste(quote.sourceText)
    if (props.quote?.id !== quote.id || !props.show) return
    const recovered = parsed.destinations.some((row) => row.channels.some((channel) => channel.channelName))
    if (!recovered) return
    destinations.value = ensureChannels(parsed.destinations)
    unrecognized.value = parsed.unrecognized
    if (parsed.summaryCtns != null) summaryCtns.value = parsed.summaryCtns
    if (parsed.summaryWeightKg != null) summaryWeightKg.value = parsed.summaryWeightKg
    if (parsed.summaryVolumeCbm != null) summaryVolumeCbm.value = parsed.summaryVolumeCbm
    if (parsed.pickupFee != null) pickupFee.value = parsed.pickupFee
    if (parsed.pickupFeeCurrency) pickupCurrency.value = parsed.pickupFeeCurrency
  } catch {
    // 原文暂时解析不了时，仍显示已保存的仓点，方便手工补渠道。
  }
}

watch(
  () => props.show,
  (open) => {
    if (!open) return
    if (props.quote) void fillFromQuote(props.quote)
    else resetForm()
  },
)

watch([customerSource, customerId, customerName], async () => {
  previousProducts.value = []
  const id = customerSource.value === 'existing' ? customerId.value || '' : ''
  const name = customerSource.value === 'new' ? customerName.value.trim() : ''
  if (!id && name.length < 2) return
  if (customerSource.value === 'existing' && !id) return
  try {
    const res = await listCustomerQuotedProducts({
      customerId: id || undefined,
      customerName: name || undefined,
    })
    previousProducts.value = res.items
  } catch {
    previousProducts.value = []
  }
})

function dateString(value: number | null) {
  if (!value) return null
  const date = new Date(value)
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${date.getFullYear()}-${month}-${day}`
}

async function parseText() {
  errorText.value = ''
  if (!sourceText.value.trim()) {
    errorText.value = '请先粘贴报价'
    return
  }
  parsing.value = true
  try {
    const parsed = await parseQuotePaste(sourceText.value)
    destinations.value = ensureChannels(parsed.destinations)
    unrecognized.value = parsed.unrecognized
    summaryCtns.value = parsed.summaryCtns
    summaryWeightKg.value = parsed.summaryWeightKg
    summaryVolumeCbm.value = parsed.summaryVolumeCbm
    pickupFee.value = parsed.pickupFee
    pickupCurrency.value = parsed.pickupFeeCurrency || 'USD'
    if (!parsed.destinations.length) errorText.value = '没有识别到仓点，请检查 To 仓码 这一行'
  } catch (error) {
    errorText.value = error instanceof Error ? error.message : '解析失败'
  } finally {
    parsing.value = false
  }
}

async function save() {
  let name = customerName.value.trim()
  let id = ''
  const isNew = customerSource.value === 'new'
  if (!isNew) {
    const found = props.customers.find((item) => item.value === customerId.value)
    if (!found) {
      errorText.value = '请选择客户'
      return
    }
    id = found.value
    name = found.raw.customerName
  } else if (!name) {
    errorText.value = '请输入新客户名称'
    return
  }
  if (!destinations.value.length) {
    errorText.value = '请先解析出仓点'
    return
  }
  saving.value = true
  errorText.value = ''
  try {
    const saved = props.quote
      ? await updateQuoteContent(props.quote.id, {
          customerId: id,
          customerName: name,
          isNewCustomer: isNew,
          quoteDate: dateString(quoteDate.value),
          productName: productName.value.trim(),
          note: inquiryNote.value.trim(),
          profitAmount: profitAmount.value,
          profitCurrency: 'CNY',
          profitUnit: profitUnit.value,
          exchangeRate: exchangeRate.value,
          summaryCtns: summaryCtns.value,
          summaryWeightKg: summaryWeightKg.value,
          summaryVolumeCbm: summaryVolumeCbm.value,
          pickupFee: pickupFee.value,
          pickupFeeCurrency: pickupCurrency.value,
          sourceText: sourceText.value,
          destinations: destinations.value,
        })
      : await createQuoteOpportunity({
          customerId: id,
          customerName: name,
          isNewCustomer: isNew,
          quoteDate: dateString(quoteDate.value),
          productName: productName.value.trim(),
          note: inquiryNote.value.trim(),
          profitAmount: profitAmount.value,
          profitCurrency: 'CNY',
          profitUnit: profitUnit.value,
          exchangeRate: exchangeRate.value,
          nextFollowupDate: dateString(Date.now()),
          summaryCtns: summaryCtns.value,
          summaryWeightKg: summaryWeightKg.value,
          summaryVolumeCbm: summaryVolumeCbm.value,
          pickupFee: pickupFee.value,
          pickupFeeCurrency: pickupCurrency.value,
          sourceText: sourceText.value,
          destinations: destinations.value,
        })
    void saved
    emit('saved')
    showModel.value = false
  } catch (error) {
    errorText.value = error instanceof Error ? error.message : '保存失败'
  } finally {
    saving.value = false
  }
}

function openManual() {
  showModel.value = false
  emit('manual')
}
</script>

<template>
  <NModal v-model:show="showModel" preset="card" :title="quote ? '编辑报价' : '新增报价'" :style="{ width: 'min(1080px, calc(100vw - 2rem))' }" :mask-closable="false">
    <div class="space-y-3 text-sm">
      <NInput v-model:value="sourceText" type="textarea" :autosize="{ minRows: 6, maxRows: 12 }" placeholder="粘贴报价，例如 To 仓码, 12ctns 157kg 0.57cbm" />
      <div class="flex items-center justify-between gap-2">
        <NButton size="small" :loading="parsing" @click="parseText">解析</NButton>
        <NButton v-if="!quote" text size="small" @click="openManual">改为手动填写</NButton>
      </div>
      <p v-if="errorText" class="text-red-600">{{ errorText }}</p>
      <div v-if="unrecognized.length" class="rounded bg-amber-50 px-3 py-2 text-amber-900 dark:bg-amber-950/40 dark:text-amber-100">
        <div class="font-medium">未识别，不会写入明细</div>
        <div v-for="(line, index) in unrecognized" :key="index">{{ line }}</div>
      </div>
      <template v-if="destinations.length">
        <div class="grid grid-cols-2 gap-3">
          <div class="block">客户
            <NRadioGroup v-model:value="customerSource" class="mt-1">
              <NRadio value="existing">已有客户</NRadio>
              <NRadio value="new">新客户</NRadio>
            </NRadioGroup>
            <NSelect v-if="customerSource === 'existing'" v-model:value="customerId" class="mt-1" :options="customers" filterable clearable placeholder="选择客户" />
            <NInput v-else v-model:value="customerName" class="mt-1" placeholder="新客户名称" />
          </div>
          <div class="block">产品
            <NInput v-model:value="productName" class="mt-1" />
            <div v-if="previousProducts.length" class="mt-1 flex flex-wrap gap-1">
              <button
                v-for="item in previousProducts"
                :key="item.productName"
                type="button"
                class="rounded bg-[var(--color-btn-ghost-bg)] px-2 py-0.5 text-xs"
                @click="productName = item.productName"
              >
                {{ item.productName }}
              </button>
            </div>
          </div>
          <div class="block">报价日期
            <NDatePicker v-model:value="quoteDate" type="date" class="mt-1 w-full" />
          </div>
          <div class="block">利润备注
            <div class="mt-1 grid grid-cols-2 gap-2">
              <NInputNumber v-model:value="profitAmount" class="w-full" :show-button="false" placeholder="金额" />
              <NSelect v-model:value="profitUnit" class="w-full" :options="[{ label: 'RMB/KG', value: 'RMB/KG' }, { label: 'RMB/CBM', value: 'RMB/CBM' }]" />
            </div>
            <div class="mt-1 flex items-center gap-2">
              <span class="shrink-0 text-xs text-[var(--color-muted)]">1 USD =</span>
              <NInputNumber v-model:value="exchangeRate" class="w-28" :min="0.0001" :show-button="false" />
              <span class="shrink-0 text-xs text-[var(--color-muted)]">RMB</span>
            </div>
            <p v-if="profitPreview" class="mt-1 text-xs text-[var(--color-muted)]">
              利润合计 {{ formatMoney(profitPreview.amount, profitPreview.currency) }}
              <template v-if="profitRatePreview != null"> · 利润率 {{ formatProfitRate(profitRatePreview) }}</template>
            </p>
          </div>
          <div class="block">提货费
            <div class="quote-unit mt-1" :class="moneyUnitLabel(pickupCurrency) ? '' : 'quote-unit--plain'">
              <NInputNumber v-model:value="pickupFee" class="w-full" :min="0" :show-button="false" />
              <span v-if="moneyUnitLabel(pickupCurrency)" class="quote-unit__tag">{{ moneyUnitLabel(pickupCurrency) }}</span>
            </div>
          </div>
        </div>
        <div class="block">询价备注
          <NInput v-model:value="inquiryNote" class="mt-1" type="textarea" :autosize="{ minRows: 2, maxRows: 4 }" placeholder="整票询价说明" />
        </div>
        <div class="scrollbar-visible max-w-full overflow-x-auto">
          <table class="quote-edit-table">
            <thead>
              <tr>
                <th>仓码</th>
                <th>渠道</th>
                <th class="col-ctns">件数 ctns</th>
                <th>实重 kg</th>
                <th>方数 cbm</th>
                <th class="col-price">单价</th>
                <th>计费</th>
                <th>总价</th>
                <th>days</th>
                <th>备注</th>
              </tr>
            </thead>
            <tbody>
              <template v-for="(dest, destIndex) in destinations" :key="destIndex">
                <tr
                  v-for="(channel, channelIndex) in dest.channels"
                  :key="`${destIndex}-${channelIndex}`"
                  :class="channelIndex === 0 && destIndex > 0 ? 'is-group' : ''"
                >
                  <td v-if="channelIndex === 0" :rowspan="dest.channels.length">
                    <NInput v-model:value="dest.addressCode" size="small" placeholder="" />
                  </td>
                  <td>
                    <NInput v-model:value="channel.channelName" size="small" placeholder="" />
                  </td>
                  <td v-if="channelIndex === 0" class="col-ctns" :rowspan="dest.channels.length">
                    <NInputNumber v-model:value="dest.ctns" size="small" :min="0" :precision="0" :show-button="false" />
                  </td>
                  <td v-if="channelIndex === 0" :rowspan="dest.channels.length">
                    <NInputNumber v-model:value="dest.weightKg" size="small" :min="0" :show-button="false" />
                  </td>
                  <td v-if="channelIndex === 0" :rowspan="dest.channels.length">
                    <NInputNumber v-model:value="dest.volumeCbm" size="small" :min="0" :show-button="false" />
                  </td>
                  <td class="col-price">
                    <div class="quote-unit" :class="priceUnitLabel(channel.quotedCurrency, channel.priceBasis) ? '' : 'quote-unit--plain'">
                      <NInputNumber v-model:value="channel.unitPrice" size="small" :show-button="false" />
                      <span v-if="priceUnitLabel(channel.quotedCurrency, channel.priceBasis)" class="quote-unit__tag">{{ priceUnitLabel(channel.quotedCurrency, channel.priceBasis) }}</span>
                    </div>
                  </td>
                  <td>
                    <div class="quote-unit quote-unit--short" :class="chargeUnit(channel) ? '' : 'quote-unit--plain'">
                      <NInputNumber v-model:value="channel.chargeWeightKg" size="small" :show-button="false" />
                      <span v-if="chargeUnit(channel)" class="quote-unit__tag">{{ chargeUnit(channel) }}</span>
                    </div>
                  </td>
                  <td>
                    <div class="quote-unit quote-unit--short" :class="moneyUnitLabel(channel.quotedCurrency) ? '' : 'quote-unit--plain'">
                      <NInputNumber v-model:value="channel.quotedAmount" size="small" :show-button="false" />
                      <span v-if="moneyUnitLabel(channel.quotedCurrency)" class="quote-unit__tag">{{ moneyUnitLabel(channel.quotedCurrency) }}</span>
                    </div>
                  </td>
                  <td>
                    <NInput :value="channel.transitDaysMin == null ? '' : `${channel.transitDaysMin}-${channel.transitDaysMax ?? ''}`" size="small" placeholder="" @update:value="(value) => applyDays(channel, value)" />
                  </td>
                  <td>
                    <NInput v-model:value="channel.note" size="small" placeholder="" />
                  </td>
                </tr>
              </template>
            </tbody>
          </table>
        </div>
        <div class="rounded px-3 py-2" :class="totalsDiffer ? 'bg-amber-50 text-amber-900 dark:bg-amber-950/40 dark:text-amber-100' : 'text-[var(--color-muted)]'">
          明细合计 {{ formatNum(lineCtns) }} ctns / {{ formatNum(lineWeight) }} kg / {{ formatNum(lineVolume) }} cbm
          · 原文合计 {{ formatNum(summaryCtns) }} ctns / {{ formatNum(summaryWeightKg) }} kg / {{ formatNum(summaryVolumeCbm) }} cbm
          <span v-if="totalsDiffer"> · 不一致，仍可保存</span>
        </div>
      </template>
    </div>
    <template #footer>
      <NSpace justify="end">
        <NButton @click="showModel = false">取消</NButton>
        <NButton type="primary" :loading="saving" :disabled="!destinations.length" @click="save">{{ quote ? '保存修改' : '确认保存' }}</NButton>
      </NSpace>
    </template>
  </NModal>
</template>

<style scoped>
.quote-unit {
  position: relative;
}
.quote-unit__tag {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 11px;
  line-height: 1;
  color: var(--color-muted);
  pointer-events: none;
}
.quote-unit :deep(.n-input__input-el) {
  padding-right: 3.6rem;
}
.quote-unit--short :deep(.n-input__input-el) {
  padding-right: 2.1rem;
}
.quote-unit--plain :deep(.n-input__input-el) {
  padding-right: 0.75rem;
}
.quote-edit-table {
  width: 100%;
  min-width: 920px;
  border-collapse: collapse;
  table-layout: fixed;
}
.quote-edit-table .col-ctns {
  width: 5.25rem;
}
.quote-edit-table .col-price {
  width: 7.5rem;
}
.quote-edit-table .col-price :deep(.n-input__input-el) {
  padding-right: 3.45rem;
}
.quote-edit-table th {
  padding: 0 4px 6px;
  font-size: 12px;
  font-weight: 500;
  text-align: left;
  white-space: nowrap;
  color: var(--color-muted);
  border-bottom: 1px solid var(--color-border);
}
.quote-edit-table td {
  padding: 6px 4px;
  vertical-align: middle;
  border-bottom: 1px solid var(--color-border);
}
.quote-edit-table tr.is-group td {
  border-top: 1px solid var(--color-border);
  padding-top: 10px;
}
.quote-edit-table :deep(.n-input) {
  width: 100%;
}
</style>
