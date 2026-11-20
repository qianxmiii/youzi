<script setup lang="ts">
import { ref, onMounted, onDeactivated, onUnmounted } from 'vue'
import { NInput, NButton, NTag, NSpace, useMessage } from 'naive-ui'
import { getOrderFlowAuthorization, saveAndRefreshOrderFlow } from '@/api/orderFlow'

const message = useMessage()
const authorization = ref('')
const configured = ref(false)
const loaded = ref(false)
const running = ref(false)
const result = ref('')
async function load() {
  try {
    configured.value = (await getOrderFlowAuthorization()).configured
    loaded.value = true
  } catch {
    result.value = '订单流转授权状态读取失败，请重试'
  }
}
async function saveAndSync() {
  running.value = true
  result.value = '正在验证授权并刷新订单流转…'
  try {
    const data = await saveAndRefreshOrderFlow(authorization.value)
    if (data.skipped) {
      result.value = '订单流转正在同步，本次未保存新授权，请稍后重试'
      message.warning(result.value)
      return
    }
    authorization.value = ''
    configured.value = true
    result.value = `${data.authorizationSaved ? '授权已保存；' : ''}订单流转已刷新：远端 ${data.remote ?? 0}，新增 ${data.created ?? 0}，状态变化 ${data.changed ?? 0}，结束 ${data.ended ?? 0}`
    message.success('订单流转同步完成')
  } catch (e) {
    const detail = (e as {data?: {detail?: unknown}}).data?.detail
    result.value = typeof detail === 'string' ? detail : '同步结果未确认，请先在订单流转页核对，避免重复提交'
    message.error(result.value)
  } finally {
    running.value = false
  }
}
onMounted(load)
onDeactivated(() => { authorization.value = '' })
onUnmounted(() => { authorization.value = '' })
</script>

<template>
  <section class="w-full max-w-3xl rounded-lg border border-[var(--color-border)] p-3 space-y-3" aria-label="订单流转授权与同步">
    <div class="flex items-center justify-between gap-2">
      <strong class="text-sm">订单流转</strong>
      <NTag size="small" :bordered="false">{{ configured ? '订单流转授权已配置' : '尚未配置订单流转授权' }}</NTag>
    </div>
    <NInput v-model:value="authorization" type="password" show-password-on="click" :maxlength="16384"
      :disabled="running" autocomplete="off" :placeholder="configured ? '粘贴新订单流转 Authorization；留空沿用已保存授权' : '粘贴订单流转 Authorization'" />
    <NSpace align="center" wrap>
      <NButton type="primary" :loading="running" :disabled="!loaded || (!configured && !authorization.trim())" @click="saveAndSync">保存并同步订单流转</NButton>
      <NButton v-if="!loaded" size="small" @click="load">重试读取状态</NButton>
    </NSpace>
    <p role="status" aria-live="polite" class="text-xs break-all">{{ result }}</p>
    <p class="text-xs text-[var(--color-muted)]">仅保存订单流转授权，并执行订单流转页的手动刷新。与六步每日同步独立，原手动刷新按钮保留。</p>
  </section>
</template>
