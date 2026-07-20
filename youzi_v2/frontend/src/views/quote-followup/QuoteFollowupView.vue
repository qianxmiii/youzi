<script setup lang="ts">
import {
  NButton,
  NCheckbox,
  NDataTable,
  NDatePicker,
  NDrawer,
  NDrawerContent,
  NForm,
  NFormItem,
  NInput,
  NInputNumber,
  NModal,
  NPagination,
  NRadio,
  NRadioGroup,
  NSelect,
  NSpace,
  NTag,
  useDialog,
  useMessage,
  type DataTableColumns,
} from 'naive-ui'
import { computed, h, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { listCustomers, type Customer } from '@/api/customers'
import {
  cancelQuote,
  createQuoteFollowup,
  createQuoteOpportunity,
  extendQuoteDeadline,
  getQuoteOpportunity,
  listQuoteFollowups,
  listQuoteOpportunities,
  listQuoteVersions,
  markQuoteLost,
  markQuoteWon,
  type QuoteFollowup,
  type QuoteOpportunity,
  type QuoteScope,
  type QuoteVersion,
} from '@/api/quoteOpportunities'
import {
  QUOTE_CHANGE_REASON_OPTIONS,
  QUOTE_CURRENCY_OPTIONS,
  QUOTE_FOLLOWUP_TYPE_OPTIONS,
  QUOTE_LOST_REASON_OPTIONS,
  QUOTE_SCOPE_OPTIONS,
  formatMoney,
  formatProfitRate,
  quoteChangeReasonLabel,
  quoteStatusLabel,
} from '@/constants/quoteFollowup'
import { formatAbsoluteDateTime, formatRelativeTime } from '@/utils/formatDateTime'

const message = useMessage()
const dialog = useDialog()
const route = useRoute()

const loading = ref(false)
const items = ref<QuoteOpportunity[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(50)

const scope = ref<QuoteScope>('todo')
const filterCustomer = ref<string | null>(null)
const filterIsNewCustomer = ref<boolean | null>(null)
const search = ref('')
const customerOptions = ref<{ label: string; value: string }[]>([])

const createShow = ref(false)
const createSubmitting = ref(false)
const createForm = reactive({
  customerSource: 'existing' as 'existing' | 'new',
  customerId: null as string | null,
  customerName: '',
  customerInquiryNo: '',
  quoteDate: null as number | null,
  deadlineDate: null as number | null,
  followupIntervalDays: 1,
  nextFollowupDate: null as number | null,
  owner: '',
  productName: '',
  addressText: '',
  ctns: null as number | null,
  weightKg: null as number | null,
  volumeCbm: null as number | null,
  quotedAmount: null as number | null,
  quotedCurrency: 'USD',
  profitAmount: null as number | null,
  profitCurrency: 'USD',
  profitRate: null as number | null,
  note: '',
})
const customerSelectOptions = ref<{ label: string; value: string; raw: Customer }[]>([])

const followupShow = ref(false)
const followupSubmitting = ref(false)
const followupRow = ref<QuoteOpportunity | null>(null)
const followupForm = reactive({
  followupType: 'wechat' as string,
  note: '',
  nextFollowupDate: null as number | null,
  adjustQuote: false,
  changeReason: 'PRICE_DOWN',
  productName: '',
  addressText: '',
  ctns: null as number | null,
  weightKg: null as number | null,
  volumeCbm: null as number | null,
  quotedAmount: null as number | null,
  quotedCurrency: 'USD',
  profitAmount: null as number | null,
  profitCurrency: 'USD',
  profitRate: null as number | null,
  versionNote: '',
})

const detailShow = ref(false)
const detailLoading = ref(false)
const detailRow = ref<QuoteOpportunity | null>(null)
const detailVersions = ref<QuoteVersion[]>([])
const detailFollowups = ref<QuoteFollowup[]>([])

const lostShow = ref(false)
const lostRow = ref<QuoteOpportunity | null>(null)
const lostReason = ref<string | null>('价格高')
const lostNote = ref('')

const extendShow = ref(false)
const extendRow = ref<QuoteOpportunity | null>(null)
const extendDeadline = ref<number | null>(null)
const extendNextFollowup = ref<number | null>(null)

function tsToDateStr(ts: number | null | undefined): string | null {
  if (ts == null) return null
  const d = new Date(ts)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function dateStrToTs(value: string | null | undefined): number | null {
  const text = (value || '').trim().slice(0, 10)
  if (!/^\d{4}-\d{2}-\d{2}$/.test(text)) return null
  return new Date(`${text}T00:00:00`).getTime()
}

function statusTagType(status: string): 'default' | 'info' | 'success' | 'warning' | 'error' {
  const s = (status || '').toUpperCase()
  if (s === 'WON') return 'success'
  if (s === 'FOLLOWING' || s === 'QUOTED') return 'info'
  if (s === 'LOST' || s === 'CANCELLED') return 'default'
  if (s === 'EXPIRED') return 'error'
  return 'warning'
}

/** 列表/详情展示：丢单原因优先，其次业务备注 */
function reasonOrNoteText(row: QuoteOpportunity): string {
  const lost = (row.lostReason || '').trim()
  const note = (row.note || '').trim()
  const status = (row.displayStatus || row.status || '').toUpperCase()
  if (status === 'LOST') {
    if (lost && note && lost !== note) return `${lost}；${note}`
    return lost || note
  }
  return note || lost
}

async function loadCustomers() {
  try {
    const res = await listCustomers({ limit: 500 })
    customerOptions.value = res.items.map((c) => ({
      label: c.customerName,
      value: c.customerName,
    }))
    customerSelectOptions.value = res.items.map((c) => ({
      label: c.customerName,
      value: c.id,
      raw: c,
    }))
  } catch {
    customerOptions.value = []
  }
}

async function load() {
  loading.value = true
  try {
    const res = await listQuoteOpportunities({
      scope: scope.value,
      customer: filterCustomer.value || undefined,
      isNewCustomer: filterIsNewCustomer.value ?? undefined,
      search: search.value.trim() || undefined,
      limit: pageSize.value,
      offset: (page.value - 1) * pageSize.value,
    })
    items.value = res.items
    total.value = res.total
  } catch (e) {
    message.error(e instanceof Error ? e.message : '加载失败')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  const today = Date.now()
  createForm.customerSource = 'existing'
  createForm.customerId = null
  createForm.customerName = ''
  createForm.customerInquiryNo = ''
  createForm.quoteDate = today
  createForm.deadlineDate = today + 7 * 86400000
  createForm.followupIntervalDays = 1
  createForm.nextFollowupDate = today + 86400000
  createForm.owner = ''
  createForm.productName = ''
  createForm.addressText = ''
  createForm.ctns = null
  createForm.weightKg = null
  createForm.volumeCbm = null
  createForm.quotedAmount = null
  createForm.quotedCurrency = 'USD'
  createForm.profitAmount = null
  createForm.profitCurrency = 'USD'
  createForm.profitRate = null
  createForm.note = ''
  createShow.value = true
}

async function submitCreate() {
  let customerName = createForm.customerName.trim()
  let customerId = ''
  let isNew = createForm.customerSource === 'new'
  if (createForm.customerSource === 'existing') {
    const found = customerSelectOptions.value.find((o) => o.value === createForm.customerId)
    if (!found) {
      message.warning('请选择客户')
      return
    }
    customerId = found.value
    customerName = found.raw.customerName
    isNew = false
  } else if (!customerName) {
    message.warning('请输入新客户名称')
    return
  }
  createSubmitting.value = true
  try {
    await createQuoteOpportunity({
      customerId,
      customerName,
      isNewCustomer: isNew,
      customerInquiryNo: createForm.customerInquiryNo.trim(),
      quoteDate: tsToDateStr(createForm.quoteDate),
      deadlineDate: tsToDateStr(createForm.deadlineDate),
      followupIntervalDays: createForm.followupIntervalDays || 1,
      nextFollowupDate: tsToDateStr(createForm.nextFollowupDate),
      owner: createForm.owner.trim(),
      productName: createForm.productName.trim(),
      addressText: createForm.addressText.trim(),
      ctns: createForm.ctns,
      weightKg: createForm.weightKg,
      volumeCbm: createForm.volumeCbm,
      quotedAmount: createForm.quotedAmount,
      quotedCurrency: createForm.quotedCurrency,
      profitAmount: createForm.profitAmount,
      profitCurrency: createForm.profitCurrency,
      profitRate: createForm.profitRate,
      note: createForm.note.trim(),
    })
    message.success('已创建报价')
    createShow.value = false
    page.value = 1
    await load()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '创建失败')
  } finally {
    createSubmitting.value = false
  }
}

function openFollowup(row: QuoteOpportunity) {
  followupRow.value = row
  followupForm.followupType = 'wechat'
  followupForm.note = ''
  followupForm.nextFollowupDate = dateStrToTs(row.nextFollowupDate) ?? Date.now() + 86400000
  followupForm.adjustQuote = false
  followupForm.changeReason = 'PRICE_DOWN'
  followupForm.productName = row.productName || ''
  followupForm.addressText = row.addressText || ''
  followupForm.ctns = row.ctns
  followupForm.weightKg = row.weightKg
  followupForm.volumeCbm = row.volumeCbm
  followupForm.quotedAmount = row.currentQuotedAmount
  followupForm.quotedCurrency = row.currentQuotedCurrency || 'USD'
  followupForm.profitAmount = row.currentProfitAmount
  followupForm.profitCurrency = row.currentProfitCurrency || 'USD'
  followupForm.profitRate = row.currentProfitRate
  followupForm.versionNote = ''
  followupShow.value = true
}

async function submitFollowup() {
  const row = followupRow.value
  if (!row) return
  followupSubmitting.value = true
  try {
    await createQuoteFollowup(row.id, {
      followupType: followupForm.followupType,
      note: followupForm.note.trim(),
      nextFollowupDate: tsToDateStr(followupForm.nextFollowupDate),
      adjustQuote: followupForm.adjustQuote,
      version: followupForm.adjustQuote
        ? {
            changeReason: followupForm.changeReason,
            productName: followupForm.productName.trim(),
            addressText: followupForm.addressText.trim(),
            ctns: followupForm.ctns,
            weightKg: followupForm.weightKg,
            volumeCbm: followupForm.volumeCbm,
            quotedAmount: followupForm.quotedAmount,
            quotedCurrency: followupForm.quotedCurrency,
            profitAmount: followupForm.profitAmount,
            profitCurrency: followupForm.profitCurrency,
            profitRate: followupForm.profitRate,
            note: followupForm.versionNote.trim(),
          }
        : undefined,
    })
    message.success('已记录跟进')
    followupShow.value = false
    await load()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '跟进失败')
  } finally {
    followupSubmitting.value = false
  }
}

async function openDetail(row: QuoteOpportunity) {
  detailRow.value = row
  detailShow.value = true
  detailLoading.value = true
  try {
    const [fresh, versions, followups] = await Promise.all([
      getQuoteOpportunity(row.id),
      listQuoteVersions(row.id),
      listQuoteFollowups(row.id),
    ])
    detailRow.value = fresh
    detailVersions.value = versions.items
    detailFollowups.value = followups.items
  } catch (e) {
    message.error(e instanceof Error ? e.message : '加载详情失败')
  } finally {
    detailLoading.value = false
  }
}

function confirmWon(row: QuoteOpportunity) {
  dialog.warning({
    title: '标记已成单',
    content: `确认将 ${row.quoteNo} 标记为已成单？`,
    positiveText: '确认',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await markQuoteWon(row.id)
        message.success('已标记成单')
        await load()
      } catch (e) {
        message.error(e instanceof Error ? e.message : '操作失败')
      }
    },
  })
}

function openLost(row: QuoteOpportunity) {
  lostRow.value = row
  lostReason.value = '价格高'
  lostNote.value = ''
  lostShow.value = true
}

async function submitLost() {
  const row = lostRow.value
  if (!row) return
  try {
    await markQuoteLost(row.id, {
      lostReason: lostReason.value || '',
      note: lostNote.value.trim() || undefined,
    })
    message.success('已标记丢单')
    lostShow.value = false
    await load()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '操作失败')
  }
}

function confirmCancel(row: QuoteOpportunity) {
  dialog.warning({
    title: '取消报价',
    content: `确认取消 ${row.quoteNo}？`,
    positiveText: '确认',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await cancelQuote(row.id)
        message.success('已取消')
        await load()
      } catch (e) {
        message.error(e instanceof Error ? e.message : '操作失败')
      }
    },
  })
}

function openExtend(row: QuoteOpportunity) {
  extendRow.value = row
  extendDeadline.value = dateStrToTs(row.deadlineDate) ?? Date.now() + 7 * 86400000
  extendNextFollowup.value = Date.now() + 86400000
  extendShow.value = true
}

async function submitExtend() {
  const row = extendRow.value
  const deadline = tsToDateStr(extendDeadline.value)
  if (!row || !deadline) {
    message.warning('请选择截止日期')
    return
  }
  try {
    await extendQuoteDeadline(row.id, {
      deadlineDate: deadline,
      nextFollowupDate: tsToDateStr(extendNextFollowup.value),
    })
    message.success('已延长有效期')
    extendShow.value = false
    await load()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '操作失败')
  }
}

const columns = computed<DataTableColumns<QuoteOpportunity>>(() => [
  {
    title: '报价编号',
    key: 'quoteNo',
    width: 168,
    render: (row) =>
      h(
        'button',
        {
          type: 'button',
          class: 'text-left text-[var(--color-accent-text)] hover:underline',
          onClick: () => openDetail(row),
        },
        row.quoteNo,
      ),
  },
  {
    title: '客户',
    key: 'customerName',
    width: 140,
    render: (row) =>
      h('span', { class: 'inline-flex items-center gap-1' }, [
        row.customerName || '—',
        row.isNewCustomer
          ? h(NTag, { size: 'tiny', type: 'warning', bordered: false }, () => '新客户')
          : null,
      ]),
  },
  {
    title: '状态',
    key: 'displayStatus',
    width: 88,
    align: 'center',
    render: (row) =>
      h(
        NTag,
        { size: 'small', type: statusTagType(row.displayStatus), bordered: false },
        () => quoteStatusLabel(row.displayStatus),
      ),
  },
  {
    title: '原因/备注',
    key: 'lostReason',
    width: 160,
    ellipsis: { tooltip: true },
    render: (row) => reasonOrNoteText(row) || '—',
  },
  { title: '品名', key: 'productName', width: 120, ellipsis: { tooltip: true }, render: (r) => r.productName || '—' },
  { title: '地址', key: 'addressText', minWidth: 140, ellipsis: { tooltip: true }, render: (r) => r.addressText || '—' },
  {
    title: '当前报价',
    key: 'currentQuotedAmount',
    width: 120,
    render: (r) => formatMoney(r.currentQuotedAmount, r.currentQuotedCurrency),
  },
  {
    title: '利润',
    key: 'currentProfitAmount',
    width: 110,
    render: (r) => formatMoney(r.currentProfitAmount, r.currentProfitCurrency),
  },
  {
    title: '利润率',
    key: 'currentProfitRate',
    width: 80,
    render: (r) => formatProfitRate(r.currentProfitRate),
  },
  { title: '报价日', key: 'quoteDate', width: 104, render: (r) => r.quoteDate || '—' },
  { title: '截止日', key: 'deadlineDate', width: 104, render: (r) => r.deadlineDate || '—' },
  { title: '下次跟进', key: 'nextFollowupDate', width: 104, render: (r) => r.nextFollowupDate || '—' },
  {
    title: '跟进',
    key: 'followupCount',
    width: 72,
    align: 'center',
    render: (r) => String(r.followupCount ?? 0),
  },
  {
    title: '操作',
    key: 'actions',
    width: 280,
    fixed: 'right',
    render: (row) => {
      const active = ['QUOTED', 'FOLLOWING'].includes((row.status || '').toUpperCase())
      return h(NSpace, { size: 4, wrap: false }, () => [
        h(NButton, { size: 'tiny', type: 'warning', disabled: !active, onClick: () => openFollowup(row) }, () => '已跟进'),
        h(NButton, { size: 'tiny', quaternary: true, onClick: () => openDetail(row) }, () => '详情'),
        h(NButton, { size: 'tiny', quaternary: true, disabled: !active, onClick: () => confirmWon(row) }, () => '成单'),
        h(NButton, { size: 'tiny', quaternary: true, disabled: !active, onClick: () => openLost(row) }, () => '丢单'),
        h(NButton, { size: 'tiny', quaternary: true, onClick: () => openExtend(row) }, () => '延期'),
        h(NButton, { size: 'tiny', quaternary: true, disabled: !active, onClick: () => confirmCancel(row) }, () => '取消'),
      ])
    },
  },
])

watch([scope, filterCustomer, filterIsNewCustomer], () => {
  page.value = 1
  void load()
})
watch([page, pageSize], () => void load())

onMounted(() => {
  const qScope = String(route.query.scope || '').trim()
  if (qScope && QUOTE_SCOPE_OPTIONS.some((o) => o.value === qScope)) {
    scope.value = qScope as QuoteScope
  }
  void loadCustomers()
  void load()
})
</script>

<template>
  <div class="flex h-full min-h-0 flex-col gap-3 p-4">
    <div class="flex shrink-0 flex-wrap items-end justify-between gap-3">
      <div>
        <h1 class="page-h2">报价跟进</h1>
        <p class="mt-1 text-sm text-zinc-500">记录报价机会、跟进沟通与报价版本变化</p>
      </div>
      <NButton type="primary" size="small" @click="openCreate">新增报价</NButton>
    </div>

    <div class="quote-followup-filters panel shrink-0 px-3 py-2">
      <div class="quote-followup-filters__row scrollbar-subtle">
        <NSelect
          v-model:value="scope"
          :options="[...QUOTE_SCOPE_OPTIONS]"
          size="small"
          class="quote-followup-filter-select quote-followup-filter-select--wide"
        />
        <NSelect
          v-model:value="filterCustomer"
          :options="customerOptions"
          clearable
          filterable
          placeholder="客户"
          size="small"
          class="quote-followup-filter-select quote-followup-filter-select--wide"
        />
        <NSelect
          v-model:value="filterIsNewCustomer"
          :options="[
            { label: '新客户', value: true },
            { label: '旧客户', value: false },
          ]"
          clearable
          placeholder="客户类型"
          size="small"
          class="quote-followup-filter-select"
        />
        <NInput
          v-model:value="search"
          clearable
          size="small"
          placeholder="搜索报价号 / 询价号 / 客户 / 品名 / 地址"
          class="quote-followup-filter-search"
          @keyup.enter="page = 1; load()"
        />
        <NButton size="small" class="shrink-0" @click="page = 1; load()">查询</NButton>
      </div>
    </div>

    <div class="panel min-h-0 flex-1 overflow-hidden p-0">
      <NDataTable
        :columns="columns"
        :data="items"
        :loading="loading"
        :bordered="false"
        :single-line="false"
        size="small"
        flex-height
        class="h-full"
        :row-key="(row: QuoteOpportunity) => row.id"
      />
    </div>

    <div class="flex shrink-0 justify-end">
      <NPagination
        v-model:page="page"
        v-model:page-size="pageSize"
        :item-count="total"
        :page-sizes="[20, 50, 100]"
        show-size-picker
      />
    </div>

    <NModal
      v-model:show="createShow"
      preset="card"
      title="新增报价"
      class="w-[720px] max-w-[95vw]"
      :mask-closable="false"
    >
      <NForm label-placement="left" label-width="108" size="small">
        <NFormItem label="客户来源">
          <NRadioGroup v-model:value="createForm.customerSource">
            <NRadio value="existing">已有客户</NRadio>
            <NRadio value="new">新客户</NRadio>
          </NRadioGroup>
        </NFormItem>
        <NFormItem v-if="createForm.customerSource === 'existing'" label="客户">
          <NSelect
            v-model:value="createForm.customerId"
            :options="customerSelectOptions"
            filterable
            clearable
            placeholder="选择客户"
          />
        </NFormItem>
        <NFormItem v-else label="新客户名称">
          <NInput v-model:value="createForm.customerName" placeholder="录入新客户名称" />
        </NFormItem>
        <NFormItem label="客户询价编号">
          <NInput v-model:value="createForm.customerInquiryNo" clearable />
        </NFormItem>
        <div class="grid grid-cols-2 gap-x-3">
          <NFormItem label="报价日期">
            <NDatePicker v-model:value="createForm.quoteDate" type="date" class="w-full" />
          </NFormItem>
          <NFormItem label="有效期截止">
            <NDatePicker v-model:value="createForm.deadlineDate" type="date" class="w-full" />
          </NFormItem>
          <NFormItem label="跟进间隔(天)">
            <NInputNumber v-model:value="createForm.followupIntervalDays" :min="1" class="w-full" />
          </NFormItem>
          <NFormItem label="下次跟进">
            <NDatePicker v-model:value="createForm.nextFollowupDate" type="date" class="w-full" />
          </NFormItem>
        </div>
        <NFormItem label="品名">
          <NInput v-model:value="createForm.productName" clearable />
        </NFormItem>
        <NFormItem label="地址">
          <NInput v-model:value="createForm.addressText" type="textarea" :rows="2" />
        </NFormItem>
        <div class="grid grid-cols-3 gap-x-3">
          <NFormItem label="箱数">
            <NInputNumber v-model:value="createForm.ctns" :min="0" class="w-full" />
          </NFormItem>
          <NFormItem label="重量KG">
            <NInputNumber v-model:value="createForm.weightKg" :min="0" class="w-full" />
          </NFormItem>
          <NFormItem label="方数CBM">
            <NInputNumber v-model:value="createForm.volumeCbm" :min="0" class="w-full" />
          </NFormItem>
        </div>
        <div class="grid grid-cols-2 gap-x-3">
          <NFormItem label="报价金额">
            <NInputNumber v-model:value="createForm.quotedAmount" :min="0" class="w-full" />
          </NFormItem>
          <NFormItem label="报价币种">
            <NSelect v-model:value="createForm.quotedCurrency" :options="[...QUOTE_CURRENCY_OPTIONS]" />
          </NFormItem>
          <NFormItem label="利润金额">
            <NInputNumber v-model:value="createForm.profitAmount" class="w-full" />
          </NFormItem>
          <NFormItem label="利润币种">
            <NSelect v-model:value="createForm.profitCurrency" :options="[...QUOTE_CURRENCY_OPTIONS]" />
          </NFormItem>
          <NFormItem label="利润率%">
            <NInputNumber v-model:value="createForm.profitRate" class="w-full" />
          </NFormItem>
          <NFormItem label="负责人">
            <NInput v-model:value="createForm.owner" clearable />
          </NFormItem>
        </div>
        <NFormItem label="备注">
          <NInput v-model:value="createForm.note" type="textarea" :rows="2" />
        </NFormItem>
      </NForm>
      <template #footer>
        <NSpace justify="end">
          <NButton @click="createShow = false">取消</NButton>
          <NButton type="primary" :loading="createSubmitting" @click="submitCreate">保存</NButton>
        </NSpace>
      </template>
    </NModal>

    <NModal
      v-model:show="followupShow"
      preset="card"
      :title="followupRow ? `已跟进 · ${followupRow.quoteNo}` : '已跟进'"
      class="w-[640px] max-w-[95vw]"
      :mask-closable="false"
    >
      <NForm label-placement="left" label-width="108" size="small">
        <NFormItem label="跟进方式">
          <NSelect v-model:value="followupForm.followupType" :options="[...QUOTE_FOLLOWUP_TYPE_OPTIONS]" />
        </NFormItem>
        <NFormItem label="跟进备注">
          <NInput v-model:value="followupForm.note" type="textarea" :rows="3" placeholder="沟通记录" />
        </NFormItem>
        <NFormItem label="下次跟进">
          <NDatePicker v-model:value="followupForm.nextFollowupDate" type="date" class="w-full" />
        </NFormItem>
        <NFormItem label="调整报价">
          <NCheckbox v-model:checked="followupForm.adjustQuote">本次跟进同时调整报价（生成新版本）</NCheckbox>
        </NFormItem>
        <template v-if="followupForm.adjustQuote">
          <NFormItem label="调整原因">
            <NSelect v-model:value="followupForm.changeReason" :options="[...QUOTE_CHANGE_REASON_OPTIONS]" />
          </NFormItem>
          <NFormItem label="品名">
            <NInput v-model:value="followupForm.productName" />
          </NFormItem>
          <NFormItem label="地址">
            <NInput v-model:value="followupForm.addressText" type="textarea" :rows="2" />
          </NFormItem>
          <div class="grid grid-cols-2 gap-x-3">
            <NFormItem label="新报价金额">
              <NInputNumber v-model:value="followupForm.quotedAmount" class="w-full" />
            </NFormItem>
            <NFormItem label="币种">
              <NSelect v-model:value="followupForm.quotedCurrency" :options="[...QUOTE_CURRENCY_OPTIONS]" />
            </NFormItem>
            <NFormItem label="新利润金额">
              <NInputNumber v-model:value="followupForm.profitAmount" class="w-full" />
            </NFormItem>
            <NFormItem label="利润率%">
              <NInputNumber v-model:value="followupForm.profitRate" class="w-full" />
            </NFormItem>
          </div>
          <NFormItem label="版本备注">
            <NInput v-model:value="followupForm.versionNote" type="textarea" :rows="2" />
          </NFormItem>
        </template>
      </NForm>
      <template #footer>
        <NSpace justify="end">
          <NButton @click="followupShow = false">取消</NButton>
          <NButton type="primary" :loading="followupSubmitting" @click="submitFollowup">保存</NButton>
        </NSpace>
      </template>
    </NModal>

    <NModal v-model:show="lostShow" preset="card" title="标记已丢单" class="w-[420px]" :mask-closable="false">
      <NForm label-placement="left" label-width="80" size="small">
        <NFormItem label="丢单原因">
          <NSelect v-model:value="lostReason" :options="[...QUOTE_LOST_REASON_OPTIONS]" />
        </NFormItem>
        <NFormItem label="备注">
          <NInput v-model:value="lostNote" type="textarea" :rows="2" />
        </NFormItem>
      </NForm>
      <template #footer>
        <NSpace justify="end">
          <NButton @click="lostShow = false">取消</NButton>
          <NButton type="primary" @click="submitLost">确认</NButton>
        </NSpace>
      </template>
    </NModal>

    <NModal v-model:show="extendShow" preset="card" title="延长有效期" class="w-[420px]" :mask-closable="false">
      <NForm label-placement="left" label-width="100" size="small">
        <NFormItem label="新截止日期">
          <NDatePicker v-model:value="extendDeadline" type="date" class="w-full" />
        </NFormItem>
        <NFormItem label="下次跟进">
          <NDatePicker v-model:value="extendNextFollowup" type="date" class="w-full" />
        </NFormItem>
      </NForm>
      <template #footer>
        <NSpace justify="end">
          <NButton @click="extendShow = false">取消</NButton>
          <NButton type="primary" @click="submitExtend">确认</NButton>
        </NSpace>
      </template>
    </NModal>

    <NDrawer v-model:show="detailShow" :width="520" placement="right">
      <NDrawerContent :title="detailRow ? `报价详情 · ${detailRow.quoteNo}` : '报价详情'" closable>
        <div v-if="detailRow" class="space-y-4 text-sm">
          <div class="space-y-1 rounded-lg border border-[var(--color-border)] p-3">
            <div class="flex items-center gap-2 font-medium">
              {{ detailRow.customerName }}
              <NTag v-if="detailRow.isNewCustomer" size="tiny" type="warning" :bordered="false">新客户</NTag>
              <NTag size="tiny" :type="statusTagType(detailRow.displayStatus)" :bordered="false">
                {{ quoteStatusLabel(detailRow.displayStatus) }}
              </NTag>
            </div>
            <div class="text-[var(--color-muted)]">
              报价 {{ formatMoney(detailRow.currentQuotedAmount, detailRow.currentQuotedCurrency) }}
              · 利润 {{ formatMoney(detailRow.currentProfitAmount, detailRow.currentProfitCurrency) }}
              · {{ formatProfitRate(detailRow.currentProfitRate) }}
            </div>
            <div class="text-[var(--color-muted)]">
              截止 {{ detailRow.deadlineDate || '—' }} · 下次跟进 {{ detailRow.nextFollowupDate || '—' }}
            </div>
            <div v-if="detailRow.productName || detailRow.addressText" class="text-[var(--color-muted)]">
              {{ detailRow.productName || '—' }} · {{ detailRow.addressText || '—' }}
            </div>
            <div
              v-if="(detailRow.displayStatus || detailRow.status || '').toUpperCase() === 'LOST' && detailRow.lostReason"
              class="mt-1 rounded bg-amber-50 px-2 py-1 text-amber-900 dark:bg-amber-950/40 dark:text-amber-100"
            >
              丢单原因：{{ detailRow.lostReason }}
            </div>
            <div v-if="detailRow.note" class="mt-1 text-[var(--color-fg-secondary)]">
              备注：{{ detailRow.note }}
            </div>
          </div>

          <div>
            <div class="mb-2 font-medium">报价版本</div>
            <div v-if="detailLoading" class="text-[var(--color-muted)]">加载中…</div>
            <div v-else-if="!detailVersions.length" class="text-[var(--color-muted)]">暂无版本</div>
            <ul v-else class="space-y-2">
              <li
                v-for="v in detailVersions"
                :key="v.id"
                class="rounded-md border border-[var(--color-border)] px-3 py-2"
              >
                <div class="font-medium">
                  V{{ v.versionNo }} · {{ quoteChangeReasonLabel(v.changeReason) }}
                </div>
                <div class="text-xs text-[var(--color-muted)]">
                  {{ formatAbsoluteDateTime(v.versionTime) }}
                  · {{ formatMoney(v.quotedAmount, v.quotedCurrency) }}
                  · 利润 {{ formatMoney(v.profitAmount, v.profitCurrency) }}
                </div>
                <div v-if="v.note" class="mt-1 text-xs">{{ v.note }}</div>
              </li>
            </ul>
          </div>

          <div>
            <div class="mb-2 font-medium">跟进记录</div>
            <div v-if="detailLoading" class="text-[var(--color-muted)]">加载中…</div>
            <div v-else-if="!detailFollowups.length" class="text-[var(--color-muted)]">暂无跟进</div>
            <ul v-else class="space-y-2">
              <li
                v-for="f in detailFollowups"
                :key="f.id"
                class="rounded-md border border-[var(--color-border)] px-3 py-2"
              >
                <div class="text-xs text-[var(--color-muted)]">
                  {{ formatRelativeTime(f.followupTime) || formatAbsoluteDateTime(f.followupTime) }}
                  <span v-if="f.followupType"> · {{ f.followupType }}</span>
                </div>
                <div class="mt-0.5">{{ f.note || '（无备注）' }}</div>
              </li>
            </ul>
          </div>
        </div>
      </NDrawerContent>
    </NDrawer>
  </div>
</template>

<style scoped>
.quote-followup-filters {
  min-width: 0;
}

.quote-followup-filters__row {
  display: flex;
  min-width: 0;
  flex-wrap: nowrap;
  align-items: center;
  gap: 0.5rem;
  overflow-x: auto;
  overflow-y: hidden;
}

.quote-followup-filters__row > * {
  flex: 0 0 auto;
}

.quote-followup-filter-select {
  width: 7.25rem;
  min-width: 6.5rem;
}

.quote-followup-filter-select--wide {
  width: 10.5rem;
  min-width: 9rem;
}

.quote-followup-filter-search {
  width: 16rem;
  min-width: 12rem;
}
</style>
