<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { NButton, NCheckbox, NConfigProvider, NInput, NInputNumber, NSelect, type GlobalThemeOverrides } from 'naive-ui'
import { ClipboardPaste, Copy, Eraser, Pin, PinOff, SlidersHorizontal } from 'lucide-vue-next'
import { parseCargoText } from '@/domain/costCalculation/parseCargoText'
import { createWarehouseSearch, exactWarehouseMatch, type WarehouseMatch, type WarehouseSearchResult } from './warehouseLookup'
import { calculateQuickQuote, DEFAULT_EXCHANGE_RATE, defaultVisibleFields, emptyQuote, publicQuoteText, quoteFields, restoreVisibleFields, singleResultCopyText, type QuoteFieldKey, type QuickQuoteInput } from './calculator'

interface Preferences { visibleFields: string[]; onTop: boolean; exchangeRate: number; fieldLayoutVersion: number; showRecognition: boolean; copyLanguage: 'zh' | 'en' }
interface DesktopApi {
  get_preferences(): Promise<Preferences>
  save_preferences(value: Preferences): Promise<Preferences>
  set_on_top(value: boolean): Promise<boolean>
  find_warehouses(query: string): Promise<WarehouseSearchResult>
}
const desktop = () => (window as unknown as { pywebview?: { api?: DesktopApi } }).pywebview?.api
const input = reactive(emptyQuote())
const cargo = ref('')
const visible = ref<string[]>([...defaultVisibleFields])
const settingsOpen = ref(false)
const compactTheme: GlobalThemeOverrides = {
  common: { primaryColor: '#2563eb', primaryColorHover: '#1d4ed8', borderRadius: '6px', fontFamily: 'Segoe UI, Microsoft YaHei, sans-serif', fontSize: '12px', fontSizeSmall: '11px', fontSizeMedium: '12px' },
  Input: { heightSmall: '24px', fontSizeSmall: '12px', paddingSmall: '0 6px' },
  Button: { heightSmall: '24px', heightMedium: '26px', fontSizeSmall: '11px', fontSizeMedium: '12px', paddingSmall: '0 7px', paddingMedium: '0 9px' },
  Select: { peers: { InternalSelection: { heightSmall: '24px', fontSizeSmall: '12px' } } },
  Checkbox: { fontSizeMedium: '11px', sizeMedium: '14px', labelPadding: '0 5px' },
}
const showRecognition = ref(true)
const copyLanguage = ref<'zh' | 'en'>('en')
const exchangeRate = ref(DEFAULT_EXCHANGE_RATE)
const onTop = ref(true)
const nativeReady = ref(false)
const pinBusy = ref(false)
const notice = ref('输入金额即可核价，数据仅本次保留。')
const warehouseCandidates = ref<WarehouseMatch[]>([])
const warehouseMessage = ref('')
let autoPostcode: string | null = null
let postcodeRevision = 0
let warehouseTimer: ReturnType<typeof setTimeout> | undefined
const warehouseSearch = createWarehouseSearch(async query => {
  const api = desktop()
  if (!api?.find_warehouses) return { status: 'unavailable', items: [], hasMore: false }
  return api.find_warehouses(query)
})
const calculation = computed(() => calculateQuickQuote(input, exchangeRate.value))
const fields = computed(() => quoteFields.filter(field => visible.value.includes(field.key)))
const fieldRowStarts = computed(() => [
  ['cost', 'profit', 'extraFee'],
  ['margin', 'unitPrice', 'unitPriceUsd'],
  ['totalUnitPrice', 'total'],
].map(group => fields.value.find(field => group.includes(field.key))?.key))
const methods = ['Sea truck', 'Sea express', 'Fast sea express', 'Air express', 'Rail truck', 'Air truck'].map(value => ({ label: value, value }))
const read = (key: QuoteFieldKey) => key in calculation.value ? calculation.value[key as keyof typeof calculation.value] : input[key as keyof QuickQuoteInput]
const setText = (key: QuoteFieldKey, value: string) => {
  if (key === 'postcode') {
    postcodeRevision++
    autoPostcode = null
    warehouseMessage.value = value ? '邮编已手动填写。' : ''
  }
  (input as unknown as Record<string, unknown>)[key] = value
}
const setNumber = (key: QuoteFieldKey, value: number | null) => { (input as unknown as Record<string, unknown>)[key] = value ?? 0 }
function setExchangeRate(value: number | null) {
  if (value !== null && Number.isFinite(value) && value > 0) exchangeRate.value = value
}
function selectWarehouse(match: WarehouseMatch) {
  input.address = match.warehouseCode
  clearTimeout(warehouseTimer)
  warehouseSearch.invalidate()
  input.postcode = match.postalCode
  autoPostcode = match.postalCode
  warehouseCandidates.value = []
  warehouseMessage.value = match.postalCode ? `已匹配 ${match.warehouseCode} · 邮编 ${match.postalCode}` : '该仓库未维护邮编，请手动填写。'
}
watch(() => [input.address, nativeReady.value], () => {
  clearTimeout(warehouseTimer)
  warehouseSearch.invalidate()
  if (autoPostcode !== null && input.postcode === autoPostcode) input.postcode = ''
  autoPostcode = null
  warehouseCandidates.value = []
  warehouseMessage.value = ''
  const query = input.address.trim()
  if (!/^[A-Za-z]/.test(query)) return
  warehouseMessage.value = '正在检索仓库…'
  const initialPostcodeRevision = postcodeRevision
  warehouseTimer = setTimeout(async () => {
    const result = await warehouseSearch.run(query)
    if (!result) return
    if (result.status === 'unavailable') {
      warehouseMessage.value = '仓库查询不可用，请重开桌面小窗并确认本地地址库存在；邮编可手动填写。'
      return
    }
    warehouseCandidates.value = result.items
    const match = exactWarehouseMatch(query, result)
    if (match && initialPostcodeRevision === postcodeRevision) {
      selectWarehouse(match)
      return
    }
    warehouseMessage.value = result.items.length
      ? match ? '已找到仓库，保留查询期间手动填写的邮编；点击候选可替换。'
        : result.hasMore ? '匹配较多，请继续输入完整仓码或选择候选。' : '请选择仓库以带出邮编；同码多条记录需核对。'
      : '未找到匹配仓库，邮编可手动填写。'
  }, 250)
}, { flush: 'sync' })
function recognize() {
  if (!cargo.value.trim()) { notice.value = '请先粘贴货况。'; return }
  const result = parseCargoText(cargo.value)
  if (!result.quantity && !result.weight && !result.volume) { notice.value = '未识别到箱数、重量或体积，请检查单位或手动填写。'; return }
  // Recognition replaces cargo metrics, not customer information or manually entered prices.
  Object.assign(input, { quantity: result.quantity, weight: result.weight, volume: result.volume })
  notice.value = '已识别。重量按总重处理；尺寸缺少单位时按厘米，结果可直接修改。'
}
async function paste() {
  try { cargo.value = await navigator.clipboard.readText(); recognize() }
  catch { notice.value = '无法读取剪贴板，请在输入框内按 Ctrl+V 粘贴。' }
}
async function copy() {
  const text = publicQuoteText(input, exchangeRate.value)
  try { await navigator.clipboard.writeText(text); notice.value = '已复制美元报价。' }
  catch { notice.value = '复制失败，请检查窗口焦点或剪贴板权限。' }
}
async function copyResult(key: QuoteFieldKey) {
  const text = singleResultCopyText(key, calculation.value)
  if (text === null) return
  try { await navigator.clipboard.writeText(text); notice.value = `已复制：${text}` }
  catch { notice.value = '复制失败，请检查窗口焦点或剪贴板权限。' }
}
function clear() {
  cargo.value = ''
  Object.assign(input, emptyQuote())
  notice.value = '本次输入已清空，字段偏好与汇率保持不变。'
}
async function togglePin() {
  if (!desktop() || pinBusy.value) return
  pinBusy.value = true
  try { onTop.value = await desktop()!.set_on_top(!onTop.value) }
  catch { notice.value = '置顶切换失败，请重新打开桌面小窗。' }
  finally { pinBusy.value = false }
}
let loaded = false
let saving = Promise.resolve()
watch([visible, exchangeRate, showRecognition, copyLanguage], () => {
  if (!loaded) return
  const preferences = { visibleFields: [...visible.value], onTop: onTop.value, exchangeRate: exchangeRate.value, fieldLayoutVersion: 1, showRecognition: showRecognition.value, copyLanguage: copyLanguage.value }
  saving = saving.then(async () => {
    if (desktop()) await desktop()!.save_preferences(preferences)
    else {
      localStorage.setItem('youzi.quoteWidget.fields', JSON.stringify(preferences.visibleFields))
      localStorage.setItem('youzi.quoteWidget.exchangeRate', String(preferences.exchangeRate))
      localStorage.setItem('youzi.quoteWidget.fieldLayoutVersion', '1')
      localStorage.setItem('youzi.quoteWidget.showRecognition', JSON.stringify(preferences.showRecognition))
      localStorage.setItem('youzi.quoteWidget.copyLanguage', preferences.copyLanguage)
    }
  }).catch(() => { notice.value = '字段偏好保存失败，本次窗口仍可正常使用。' })
}, { deep: true })
async function initialize() {
  try {
    const api = desktop()
    if (api) {
      const preferences = await api.get_preferences()
      visible.value = restoreVisibleFields(preferences.visibleFields, preferences.fieldLayoutVersion ?? 0)
      onTop.value = preferences.onTop
      setExchangeRate(preferences.exchangeRate ?? DEFAULT_EXCHANGE_RATE)
      showRecognition.value = preferences.showRecognition !== false
      copyLanguage.value = preferences.copyLanguage === 'zh' ? 'zh' : 'en'
      nativeReady.value = true
    } else {
      const saved = JSON.parse(localStorage.getItem('youzi.quoteWidget.fields') || 'null')
      if (Array.isArray(saved)) visible.value = restoreVisibleFields(saved, Number(localStorage.getItem('youzi.quoteWidget.fieldLayoutVersion')))
      setExchangeRate(Number(localStorage.getItem('youzi.quoteWidget.exchangeRate')))
      showRecognition.value = localStorage.getItem('youzi.quoteWidget.showRecognition') !== 'false'
      copyLanguage.value = localStorage.getItem('youzi.quoteWidget.copyLanguage') === 'zh' ? 'zh' : 'en'
    }
  } catch { notice.value = '使用默认字段设置。' }
  loaded = true
}
onMounted(() => {
  void initialize()
  window.addEventListener('pywebviewready', initialize)
})
onBeforeUnmount(() => {
  window.removeEventListener('pywebviewready', initialize)
  clearTimeout(warehouseTimer)
  warehouseSearch.invalidate()
})
</script>

<template>
  <NConfigProvider :theme-overrides="compactTheme">
    <main class="quote-widget">
      <header>
        <h1>报价小窗</h1>
        <div class="toolbar">
          <NButton size="small" :type="onTop && nativeReady ? 'primary' : 'default'" :disabled="!nativeReady" :loading="pinBusy" :title="nativeReady ? '切换窗口置顶' : '网页预览无法置顶，请使用桌面启动器'" @click="togglePin"><template #icon><Pin v-if="onTop" :size="12" /><PinOff v-else :size="12" /></template>{{ onTop && nativeReady ? '已置顶' : '置顶' }}</NButton>
          <NButton size="small" :aria-expanded="settingsOpen" @click="settingsOpen = !settingsOpen"><template #icon><SlidersHorizontal :size="12" /></template>字段／汇率</NButton>
        </div>
      </header>
      <section v-if="settingsOpen" class="settings" aria-label="字段显示设置">
        <div class="rate-setting"><label for="quote-exchange-rate">汇率：1 USD =</label><NInputNumber id="quote-exchange-rate" :value="exchangeRate" :min="0.0001" :precision="4" :step="0.01" :clearable="false" :show-button="false" size="small" @update:value="setExchangeRate" /><span>RMB</span></div>
        <p>手动设置，修改后自动记住；美元单价 = 人民币单价 ÷ 汇率。</p>
        <div class="settings-heading"><strong>选择显示字段</strong><NButton text size="small" @click="visible = quoteFields.map(field => field.key); showRecognition = true">全选</NButton><NButton text size="small" @click="visible = [...defaultVisibleFields]; showRecognition = true">恢复默认</NButton></div>
        <div class="checks"><NCheckbox v-model:checked="showRecognition">显示报价识别</NCheckbox></div>
        <div class="checks"><NCheckbox v-for="field in quoteFields" :key="field.key" :checked="visible.includes(field.key)" @update:checked="checked => visible = checked ? [...visible, field.key] : visible.filter(key => key !== field.key)">{{ field.label }}</NCheckbox></div>
        <p>隐藏仅影响显示，已填值仍参与计算。复制报价按地址、货况及美元报价的固定格式生成。</p>
      </section>
      <section v-show="showRecognition" class="recognition" aria-label="报价识别">
        <label for="cargo-input">报价识别</label>
        <NInput id="cargo-input" v-model:value="cargo" type="textarea" size="small" :autosize="{ minRows: 1, maxRows: 3 }" placeholder="21ctns 8.3kg 2.126cbm 或 45*45*50cm 10kg 21箱" @keydown.ctrl.enter.prevent="recognize" />
        <div class="recognition-actions"><span>总重 · Ctrl+Enter 识别</span><NButton size="small" @click="paste"><template #icon><ClipboardPaste :size="12" /></template>粘贴识别</NButton><NButton size="small" type="primary" @click="recognize">识别</NButton></div>
      </section>
      <section class="field-grid" aria-label="货况与报价字段">
        <div v-for="field in fields" :key="field.key" :class="['field-card', { metric: field.type === 'result', confidential: 'private' in field, 'row-start': fieldRowStarts.includes(field.key) }]">
          <label :for="`quote-${field.key}`">{{ field.label }}<span v-if="'private' in field" class="internal">内部</span></label>
          <NSelect v-if="field.type === 'channel'" :value="String(read(field.key))" :options="methods" filterable tag size="small" @update:value="setText(field.key, $event)" />
          <NInput v-else-if="field.type === 'text'" :id="`quote-${field.key}`" :value="String(read(field.key))" size="small" :placeholder="field.key === 'postcode' ? '保留前导零' : '选填'" @update:value="setText(field.key, $event)" />
          <NInputNumber v-else-if="field.type === 'number'" :id="`quote-${field.key}`" :value="Number(read(field.key))" :min="0" :precision="field.key === 'quantity' ? 0 : 3" :show-button="false" size="small" @update:value="setNumber(field.key, $event)" />
          <button v-else-if="singleResultCopyText(field.key, calculation) !== null" :id="`quote-${field.key}`" type="button" class="copy-result" :aria-label="`${field.label}，点击复制 ${singleResultCopyText(field.key, calculation)}`" :title="`点击复制 ${singleResultCopyText(field.key, calculation)}`" @click="copyResult(field.key)">{{ read(field.key) }}<Copy :size="11" aria-hidden="true" /></button>
          <output v-else :id="`quote-${field.key}`">{{ read(field.key) }}</output>
          <div v-if="field.key === 'address'" class="warehouse-search" aria-live="polite">
            <p v-if="warehouseMessage">{{ warehouseMessage }}</p>
            <div v-if="warehouseCandidates.length" class="warehouse-options">
              <NButton v-for="(match, index) in warehouseCandidates" :key="index" size="tiny" @click="selectWarehouse(match)">{{ match.warehouseCode }} · {{ match.countryCode || '国家未填' }} · {{ match.postalCode || '邮编未填' }}</NButton>
            </div>
          </div>
        </div>
      </section>
      <p v-if="!fields.length" class="empty">字段已全部隐藏，可通过右上角“字段”重新选择。</p>
      <p class="notice" role="status">{{ notice }}</p>
      <footer><NButton size="small" @click="clear"><template #icon><Eraser :size="12" /></template>清空本次</NButton><div class="copy-actions"><NSelect v-model:value="copyLanguage" class="copy-language" size="small" aria-label="报价复制语言" :options="[{ label: '中文', value: 'zh' }, { label: 'English', value: 'en' }]" /><NButton type="primary" size="small" @click="copy"><template #icon><Copy :size="12" /></template>复制报价</NButton></div></footer>
      <details class="footnote"><summary>1 USD = {{ exchangeRate }} RMB · 计算说明</summary><p>成本、利润、附加费均按 RMB/kg 输入，无需货况即可核价。人民币单价 = 成本＋利润＋附加费；美元单价 = 人民币单价 ÷ 汇率；毛利率 =（利润＋附加费）÷ 人民币单价。总报价需有计费重。计费方按 363kg/cbm，不自动查价或判偏远。</p></details>
    </main>
  </NConfigProvider>
</template>

<style>
* { box-sizing: border-box; }
body { margin: 0; background: #f4f7fc; color: #172b45; font: 12px 'Segoe UI', 'Microsoft YaHei', sans-serif; }
.quote-widget { padding: 8px; max-width: 1100px; margin: auto; }
header, .toolbar, .settings-heading, .recognition-actions, footer { display: flex; align-items: center; gap: 4px; }
header { justify-content: space-between; margin-bottom: 6px; padding-bottom: 2px; position: sticky; top: 0; z-index: 5; background: #f4f7fc; }
h1 { font-size: 14px; margin: 0; white-space: nowrap; }
.recognition, .settings { background: #fff; border: 1px solid #dfe7f2; border-radius: 7px; padding: 7px; margin-bottom: 6px; }
.recognition > label { display: block; font-weight: 600; margin-bottom: 4px; font-size: 11px; }
.recognition-actions { margin-top: 4px; flex-wrap: wrap; }
.recognition-actions > span { font-size: 10px; color: #53647b; flex: 1; }
.field-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 4px; }
.field-card { background: white; border: 1px solid #e2e8f2; border-radius: 6px; padding: 6px; min-width: 0; }
.field-card.row-start { grid-column-start: 1; }
.field-card > label { display: flex; flex-wrap: wrap; gap: 3px; align-items: center; margin-bottom: 3px; font-size: 11px; line-height: 1.35; color: #53647b; }
.internal { border-radius: 4px; color: #8a5a19; background: #fff3d9; font-size: 9px; padding: 1px 4px; }
.metric { background: #eef4ff; border-color: #dce7ff; }
output, .copy-result { display: block; font-size: 18px; line-height: 24px; font-weight: 650; font-variant-numeric: tabular-nums; color: #1f53ba; overflow-wrap: anywhere; }
.copy-result { position: relative; width: 100%; border: 0; border-radius: 3px; padding: 0 14px 0 0; background: transparent; text-align: left; font-family: inherit; cursor: pointer; }
.copy-result svg { position: absolute; right: 0; top: 6px; color: #53647b; }
.copy-result:hover { background: #dce7ff; }
.copy-result:active { background: #cbdcff; }
.copy-result:focus-visible { outline: 2px solid #2563eb; outline-offset: 2px; }
.checks { margin-top: 7px; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 6px; }
.settings p, .notice, .footnote, .empty { font-size: 10px; color: #53647b; line-height: 1.45; }
.settings-heading { flex-wrap: wrap; }
.rate-setting { display: flex; align-items: center; gap: 5px; flex-wrap: wrap; font-size: 11px; }
.rate-setting .n-input-number { width: 90px; }
.warehouse-search { font-size: 11px; color: #53647b; line-height: 1.5; overflow-wrap: anywhere; }
.warehouse-search p { margin: 6px 0 0; }
.warehouse-options { display: flex; flex-direction: column; align-items: flex-start; gap: 6px; margin-top: 6px; max-height: 170px; overflow: auto; }
.warehouse-options .n-button { max-width: 100%; height: auto; min-height: 28px; white-space: normal; text-align: left; }
.notice { margin: 6px 0; }
.footnote { margin: 5px 0 0; }
.footnote summary { cursor: pointer; }
.footnote summary:focus-visible { outline: 2px solid #2563eb; outline-offset: 2px; }
.footnote p { margin: 5px 0 0; }
footer { justify-content: space-between; position: sticky; bottom: 0; z-index: 5; background: #f4f7fc; padding-top: 3px; }
.copy-actions { display: flex; align-items: center; gap: 4px; }
.copy-language { width: 78px; }
@media (max-width: 340px) { .field-grid { grid-template-columns: repeat(2, minmax(0,1fr)); } .checks { grid-template-columns: 1fr; } }
@media (prefers-reduced-motion: reduce) { *, *::before, *::after { transition: none !important; animation: none !important; } }
</style>
