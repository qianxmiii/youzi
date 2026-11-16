<script setup lang="ts">
import { ref, watch } from 'vue'
import { NModal,NSelect,NButton,NPopconfirm,useMessage } from 'naive-ui'
import { api } from '@/api/client'
import { trackTask } from '@/composables/useRunningTasks'
const props=defineProps<{show:boolean; ids:string[]}>()
const emit=defineEmits<{close:[]; updated:[]}>()
const message=useMessage()
const action=ref(0)
const marks=ref<string[]>([])
const options=ref<{id:string;name:string;color:string}[]>([])
const busy=ref(false)
const loading=ref(false)
const error=ref('')
watch(() => props.show,async open => {
  if (!open) return
  marks.value=[]; action.value=0; loading.value=true; error.value=''
  try { options.value=(await api<{items:typeof options.value}>('/api/v1/commerce-marks/options')).items }
  catch { error.value='标识配置读取失败，请检查配置后重新打开' }
  finally { loading.value=false }
})
async function submit() {
  if (busy.value || !props.ids.length || props.ids.length>200 || (action.value!==2 && !marks.value.length)) return
  busy.value=true
  const ids=[...props.ids], markIds=[...marks.value], type=action.value
  try {
    const result=await trackTask('标识管理 · '+['增加','移除','编辑'][type],taskId => api<{updated:number}>('/api/v1/commerce-marks',{method:'POST',headers:{'X-Youzi-Task-Id':taskId},body:{ids,markIds,type},timeout:60000,retry:0}))
    message.success(`已更新 ${result.updated} 票标识`); emit('updated'); emit('close')
  } catch(e) { message.error((e as {data?:{detail?:string}})?.data?.detail || '操作失败，请核对远端结果后再试') }
  finally { busy.value=false }
}
</script>
<template>
  <NModal :show="show" preset="card" title="港前运单 · 标识管理" :style="{width:'480px',maxWidth:'95vw'}" :closable="!busy" :mask-closable="!busy" @update:show="v => { if (!v && !busy) emit('close') }">
    <p class="mb-4 text-sm">已选择 {{ ids.length }} 票运单，远端成功后更新本地显示。</p>
    <p v-if="error" class="mb-3 text-amber-600">{{ error }}</p>
    <label class="mb-2 block text-sm">操作类型</label><NSelect v-model:value="action" :disabled="busy" :options="[{label:'增加标识（保留其他标识）',value:0},{label:'移除所选标识',value:1},{label:'编辑标识（替换全部）',value:2}]" />
    <label class="mb-2 mt-4 block text-sm">标识</label><NSelect v-model:value="marks" multiple filterable :loading="loading" :disabled="busy || loading" :options="options.map(x => ({label:x.name,value:x.id}))" placeholder="选择配置中的标识" />
    <p v-if="!loading && !options.length" class="mt-3 text-xs text-amber-600">尚无可用标识，请到「后台管理 → 码表 → 港前运单标识」新增并启用。</p>
    <p v-if="action===2" class="mt-3 text-xs text-amber-600">编辑会用所选标识替换全部现有标识；不选标识表示清空。</p>
    <div class="mt-5 flex justify-end gap-2"><NButton :disabled="busy" @click="emit('close')">取消</NButton><NPopconfirm @positive-click="submit"><template #trigger><NButton type="primary" :loading="busy" :disabled="busy || loading || !!error || !ids.length || ids.length>200 || (action!==2 && !marks.length)">确认{{ ['增加','移除','编辑'][action] }}</NButton></template>将对 {{ ids.length }} 票执行{{ ['增加所选标识','移除所选标识',marks.length ? '替换全部标识' : '清空全部标识'][action] }}，确定继续？</NPopconfirm></div>
  </NModal>
</template>
