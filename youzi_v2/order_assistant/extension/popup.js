(() => {
  'use strict';
  const model = globalThis.YouziOrderModel;
  const $ = (id) => document.getElementById(id);
  let templates = {}, busy = false, queue = null, history = [], aliases = {};
  const imported = globalThis.YouziOrderImport;
  const boundTab = Number(new URL(location.href).searchParams.get('tab'));
  let summaryRevision=0,summaryOrder=null;
  const commonFields=['sales','customer','supplier','channel','customsType'];
  const fieldBoxes=new Map(),groupBoxes=new Map();
  let visibleFields=new Set(commonFields);
  $('assistant-version').textContent = '助手 ' + model.version;
  function node(tag, text) { const element = document.createElement(tag); if (text) element.textContent = text; return element; }
  for (const group of new Set(model.fields.map((field) => field.group))) {
    const fieldset = node('fieldset'); fieldset.append(node('legend', group)); const grid = node('div'); grid.className = 'grid';
    groupBoxes.set(group,fieldset);
    for (const field of model.fields.filter((field) => field.group === group)) {
      const box = node('div'); const label = node('label', field.label); label.htmlFor = field.key;
      const input = node(field.kind === 'boolean' || field.kind === 'radio' ? 'select' : 'input'); input.id = field.key;
      if (input.tagName === 'SELECT') {
        for (const value of ['', ...(field.kind === 'boolean' ? ['否', '是'] : model.radioChoices[field.key])]) {
          const option = node('option', value || '请选择'); option.value = value; input.append(option);
        }
      } else { input.type = 'text'; input.maxLength = 1000; input.autocomplete = 'off'; }
      box.append(label, input); grid.append(box);fieldBoxes.set(field.key,box);
      if (model.defaults[field.key]) input.value = model.defaults[field.key];
      const option = node('option', `${field.group} · ${field.label}`); option.value = field.key; $('bind-field').append(option);
    }
    fieldset.append(grid); $('fields').append(fieldset);
  }
  function applyFieldVisibility(){
    for(const field of model.fields){
      fieldBoxes.get(field.key).hidden=!visibleFields.has(field.key);
      $('visible-'+field.key).checked=visibleFields.has(field.key);
    }
    for(const [group,box] of groupBoxes)box.hidden=!model.fields.some(field=>field.group===group&&visibleFields.has(field.key));
    $('field-visibility-status').textContent=`本次启用 ${visibleFields.size} / ${model.fields.length} 个字段。只填显示且有值的字段；隐藏字段完全不动，空白字段跳过。`;
    $('customer-no-rule').hidden=!visibleFields.has('customerOrderNo');
    $('delivery-mode-rule').hidden=!visibleFields.has('deliveryAddressType');
  }
  async function saveFieldVisibility(){
    await chrome.storage.local.set({orderVisibleFields:[...visibleFields]});applyFieldVisibility();refreshQueueErrors();clearSummary();renderQueue();
  }
  for(const group of groupBoxes.keys()){
    const box=node('fieldset');box.append(node('legend',group));const grid=node('div');grid.className='visibility-grid';
    for(const field of model.fields.filter(field=>field.group===group)){
      const label=node('label');label.className='visibility-choice';
      const input=node('input');input.type='checkbox';input.id='visible-'+field.key;
      input.addEventListener('change',()=>{void action(async()=>{
        if(input.checked)visibleFields.add(field.key);else visibleFields.delete(field.key);
        await saveFieldVisibility();
      });});
      label.append(input,node('span',field.label));grid.append(label);
    }
    box.append(grid);$('field-visibility').append(box);
  }
  $('show-all-fields').addEventListener('click',()=>{void action(async()=>{visibleFields=new Set(model.fields.map(field=>field.key));await saveFieldVisibility();});});
  $('common-fields-only').addEventListener('click',()=>{void action(async()=>{visibleFields=new Set(commonFields);await saveFieldVisibility();});});
  applyFieldVisibility();
  function rawData(){return Object.fromEntries(model.fields.map(field=>[field.key,$(field.key).value]));}
  function data() { return model.selectedValues(model.customerNumber(rawData(),$('customer-no-from-shipment').checked),visibleFields); }
  $('delivery-address-mode').addEventListener('change',()=>{
    $('deliveryAddressType').value=$('delivery-address-mode').value;clearSummary();
  });
  $('deliveryAddressType').addEventListener('change',()=>{$('delivery-address-mode').value=$('deliveryAddressType').value;});
  $('customer-no-from-shipment').addEventListener('change',()=>{void action(async()=>{
    await chrome.storage.local.set({orderCustomerNoFromShipment:$('customer-no-from-shipment').checked});
    clearSummary();renderQueue();$('notice').textContent='客户单号规则已更新；网页尚未修改，请点击填写或重新核对。';
  });});
  for (const field of model.fields.filter((field) => ['choice','auto'].includes(field.kind))) {
    const option = node('option', field.group + ' · ' + field.label); option.value = field.key; $('alias-field').append(option);
  }
  $('alias-field').value = 'deliveryAddress';
  function renderAliases() {
    $('alias-list').replaceChildren();
    for (const entry of model.aliasEntries($('alias-field').value, aliases)) $('alias-list').append(node('li', `${entry.short} → ${entry.full}${entry.builtin ? '（已确认示例）' : ''}`));
  }
  $('alias-field').addEventListener('change', () => { $('alias-targets').replaceChildren(); renderAliases(); });
  $('save-alias').addEventListener('click', () => { void action(async () => {
    const field = $('alias-field').value, short = $('alias-short').value.trim(), full = $('alias-full').value.trim();
    if (!short || !full) throw new Error('请填写简称和系统完整名称。');
    const entries = Object.fromEntries(model.aliasEntries(field, aliases).filter((entry) => !entry.builtin && model.aliasKey(entry.short) !== model.aliasKey(short)).map((entry) => [entry.short,entry.full]));
    const next = {...aliases, [field]: {...entries, [short]: full}};
    model.aliasEntries(field, next);
    await chrome.storage.local.set({orderAliases:next}); aliases = next; renderAliases(); renderQueue();
    clearSummary();
    $('notice').textContent = '简称对照已保存，后续填写会用完整名称精确选中并复核。';
  }); });
  function showRows(rows) {
    $('results').replaceChildren();
    for (const row of rows) { const item = node('li', `${row.label}：${row.message}`); item.className = row.ok ? 'result-ok' : 'result-review'; $('results').append(item); }
  }
  function orderContext(){return queue?.rows[queue.index]?JSON.stringify([queue.index,imported.fingerprint(queue.rows[queue.index].data)]):'manual';}
  function clearSummary(){
    summaryRevision++;summaryOrder=null;$('summary-body').replaceChildren();
    $('summary-table').hidden=true;$('summary-status').textContent='尚未核对。填写后自动生成，也可读取当前网页重新核对。';
  }
  function showSummary(rows){
    $('summary-body').replaceChildren();summaryOrder=orderContext();
    const priority={mismatch:0,missing:1,unreadable:2,unconfirmed:3,notProvided:4,match:5};
    for(const row of [...rows].sort((a,b)=>priority[a.status]-priority[b.status])){
      const tr=node('tr');tr.className='summary-'+row.status;
      for(const value of [row.label,row.expected||'未提供',row.actual||'—',row.message])tr.append(node('td',value));
      $('summary-body').append(tr);
    }
    const matches=rows.filter(row=>row.status==='match').length;
    const review=rows.filter(row=>!['match','notProvided'].includes(row.status)).length;
    const omitted=rows.filter(row=>row.status==='notProvided').length;
    $('summary-status').textContent=`${new Date().toLocaleTimeString('zh-CN')} 读取 · ${matches} 项一致 · ${review} 项需核对 · ${omitted} 项未提供目标值`;
    $('summary-table').hidden=false;
  }
  function currentValues(){
    const row=queue?.rows[queue.index];
    return row?model.selectedValues(model.customerNumber({...model.clean(rawData()),...Object.fromEntries(Object.entries(row.data).filter(([,value])=>value!==''))},$('customer-no-from-shipment').checked),visibleFields):data();
  }
  function checkEffectiveIdentity(values){
    if(![values.customerOrderNo,values.shipmentId,values.referenceId].every(Boolean))return;
    const fingerprint=imported.fingerprint(values);
    if(history.includes(fingerprint))throw new Error('按当前客户单号规则，该编号组合曾由本人确认下单，请先核对避免重复');
    const earlier=queue?.rows.slice(0,queue.index)||[];
    if(earlier.some(row=>imported.fingerprint(model.customerNumber(row.data,$('customer-no-from-shipment').checked))===fingerprint))throw new Error('按当前客户单号规则，与本批前面的订单编号组合重复，请先核对');
  }
  function structuralErrors(row){return row.errors.filter(error=>error.includes('列数与表头不一致'));}
  function refreshQueueErrors(){
    for(const row of queue?.rows||[]){
      if(row.status==='confirmed')continue;
      const values=model.selectedValues(model.customerNumber(row.data,$('customer-no-from-shipment').checked),visibleFields);
      const errors=[...structuralErrors(row),...Object.entries(values).flatMap(([key,value])=>model.validate({[key]:value},true))];
      for(const key of ['customerOrderNo','referenceNo','shipmentId','referenceId'])if(values[key]&&/^[+-]?\d+(?:\.\d+)?e[+-]?\d+$/i.test(values[key]))errors.push('编号疑似科学计数法：'+key);
      row.errors=errors;
      if(row.status==='invalid'&&!errors.length)row.status='pending';
      if(row.status==='pending'&&errors.length)row.status='invalid';
    }
  }
  function updateSubmitButton(){
    const row=queue?.rows[queue.index];
    $('submit-order').disabled=busy||!row||row.status!=='review'||Boolean(structuralErrors(row).length)||Boolean(row.submitAttempted);
    $('submit-order').textContent=row?.submitAttempted?'已点击，待确认 DPS 结果':'录入完成，点击下单';
  }
  async function action(callback) {
    if (busy) return; busy = true; $('notice').textContent = '';
    $('customer-no-from-shipment').disabled=true;
    $('delivery-address-mode').disabled=true;
    document.querySelectorAll('button').forEach((button) => { button.disabled = true; });
    try { await callback(); } catch (error) { $('notice').textContent = error.message || '操作未完成，请重新打开助手检查。'; }
    finally { busy = false; $('customer-no-from-shipment').disabled=false;$('delivery-address-mode').disabled=false;document.querySelectorAll('button').forEach((button) => { button.disabled = false; }); updateSubmitButton(); }
  }
  async function targetTab() {
    if (boundTab) return chrome.tabs.get(boundTab);
    return (await chrome.tabs.query({active: true, currentWindow: true}))[0];
  }
  async function send(type, extra = {}) {
    const customerNoFromShipment=visibleFields.has('customerOrderNo')&&$('customer-no-from-shipment').checked;
    if(extra.field&&!visibleFields.has(extra.field))throw new Error('该字段已隐藏，本次不操作；需要时请先勾选显示');
    clearSummary();const revision=summaryRevision;
    const tab = await targetTab();
    if (!tab || !model.allowed(tab.url)) throw new Error('请切换到已登录的 DPS 新建运单页，再打开助手。');
    await chrome.scripting.executeScript({target: {tabId: tab.id}, files: ['allowed-page.local.js', 'model.js', 'content.js']});
    const result = await chrome.tabs.sendMessage(tab.id, {type, ...extra,customerNoFromShipment,enabledFields:[...visibleFields]});
    if (result.error) throw new Error(result.error);
    if (result.rows) showRows(result.rows);
    if (result.summary && revision===summaryRevision) showSummary(result.summary);
    if (result.options) {
      showRows(result.options.map((option) => ({label:'下拉选项',message:option,ok:true})));
      const field = extra.field;
      if (model.fields.some((item) => item.key === field && ['choice','auto'].includes(item.kind))) {
        $('alias-field').value = field; renderAliases(); $('alias-targets').replaceChildren();
        for (const value of result.options) { const option = node('option'); option.value = value; $('alias-targets').append(option); }
      }
    }
    if (result.message) $('notice').textContent = result.message;
    return result;
  }
  function renderTemplates(selected = '') {
    $('template').replaceChildren(); const blank = node('option', '新模板'); blank.value = ''; $('template').append(blank);
    for (const name of Object.keys(templates).sort()) { const option = node('option', name); option.value = name; $('template').append(option); }
    $('template').value = selected;
  }
  $('save-template').addEventListener('click', () => { void action(async () => {
    const name = $('template-name').value.trim(); if (!name) throw new Error('请先填写模板名称。');
    if (!templates[name] && Object.keys(templates).length >= 100) throw new Error('模板数量已达上限。');
    const next = {...templates, [name]: model.clean(data(), true)};
    await chrome.storage.local.set({orderTemplates: next}); templates = next; renderTemplates(name);
    $('notice').textContent = '模板已保存在当前浏览器；每单编号未保存。';
  }); });
  $('template').addEventListener('change', () => {
    clearSummary();
    const values = model.withDefaults(templates[$('template').value] || {});
    for (const field of model.fields) $(field.key).value = values[field.key] || '';
    $('delivery-address-mode').value=$('deliveryAddressType').value;
    $('template-name').value = $('template').value; $('results').replaceChildren();
  });
  $('scan').addEventListener('click', () => { void action(() => send('YOUZI_ORDER_SCAN')); });
  $('bind').addEventListener('click', () => { void action(() => send('YOUZI_ORDER_BIND', {field: $('bind-field').value})); });
  $('read-options').addEventListener('click', () => { void action(() => send('YOUZI_ORDER_OPTIONS', {field: $('bind-field').value})); });
  $('retry-choice').addEventListener('click', () => { void action(async () => {
    const key = $('bind-field').value;
    if(!visibleFields.has(key))throw new Error('该字段已隐藏，本次不操作；需要时请先勾选显示');
    const row = queue?.rows[queue.index];
    if (row?.status === 'confirmed') throw new Error('当前订单已确认下单，不再填写');
    const value = currentValues()[key];
    if(!value){$('notice').textContent='该字段为空，本次跳过，不修改网页。';return;}
    await send('YOUZI_ORDER_RETRY', {field:key,value});
    await send('YOUZI_ORDER_COMPARE',{values:currentValues()});
  }); });
  $('compare-order').addEventListener('click',()=>{void action(()=>send('YOUZI_ORDER_COMPARE',{values:currentValues()}));});
  $('order-form').addEventListener('input',clearSummary);
  $('order-form').addEventListener('change',clearSummary);
  async function saveQueue() { await chrome.storage.local.set({orderQueue:queue,orderHistory:history}); renderQueue(); }
  function renderQueue() {
    if(summaryOrder!==null&&summaryOrder!==orderContext())clearSummary();
    $('queue-row').replaceChildren(); $('submitted').checked=false;
    updateSubmitButton();
    if (!queue) { $('queue-status').textContent='尚未导入订单'; $('queue-preview').textContent=''; return; }
    const labels={pending:'待填',invalid:'需修改',filling:'填写中/请检查页面',review:'待核对',confirmed:'本人已确认下单'};
    queue.rows.forEach((row,index)=>{const option=node('option',`${index+1}. ${row.data.customerOrderNo || '无客户单号'} · ${labels[row.status] || row.status}`);option.value=String(index);$('queue-row').append(option);});
    $('queue-row').value=String(queue.index);
    const row=queue.rows[queue.index];
    const done=queue.rows.filter(row=>row.status==='confirmed').length;
    $('queue-status').textContent=`共 ${queue.rows.length} 单 · 已确认 ${done} 单 · 需修改 ${queue.rows.filter(row=>row.errors.length).length} 单`;
    $('queue-preview').textContent=row ? (row.errors.length?'本行问题：'+row.errors.join('；')+'\n':'')+imported.columns.filter(([key])=>visibleFields.has(key)).map(([key,label])=>{
      const original=currentValues()[key]; if(!original)return `${label}：空白，跳过`;
      const mapped=model.resolveAlias(key,original,aliases);
      return `${label}：${original}${mapped.used?' → '+mapped.value:''}`;
    }).join('\n') : '本批已处理完毕';
  }
  async function fillCurrent() {
    if (!queue || !queue.rows[queue.index]) throw new Error('请先导入并选择一条订单。');
    const row=queue.rows[queue.index];
    if (structuralErrors(row).length) throw new Error('当前行列数与表头不一致，请修改原表格后重新导入。');
    if (row.status==='confirmed') throw new Error('这条已由本人确认下单，不再填写。');
    if (row.submitAttempted) throw new Error('这条已尝试下单，请先核对 DPS 结果并确认，勿重新填写');
    const values=currentValues();
    checkEffectiveIdentity(values);
    row.filledFingerprint=imported.fingerprint(values);
    if(!row.fillToken)row.fillToken=String(Date.now())+'-'+Math.random().toString(36).slice(2);
    row.status='filling';await saveQueue();
    try { await send('YOUZI_ORDER_FILL',{values,replace:$('replace-existing').checked,batch:true,batchRow:row.fillToken}); }
    finally { row.status='review'; await saveQueue(); }
  }
  $('import-orders').addEventListener('click',()=>{void action(async()=>{
    if (queue && queue.rows.some(row=>row.status!=='confirmed') && !window.confirm('当前队列仍有未确认订单，是否用新表格替换？原网页不会被清空。')) return;
    const rows=imported.parse($('import-text').value,history,[...visibleFields]);
    clearSummary();
    queue={rows,index:0};refreshQueueErrors(); await saveQueue(); $('import-text').value='';
  });});
  async function readImportFile() {
    const file=$('import-file').files[0];if(!file)return;
    $('import-text').value='';
    if(file.size>2_000_000)throw new Error('文件请控制在 2 MB 以内。');
    const decoded=imported.decode(await file.arrayBuffer(),$('import-encoding').value);
    $('import-text').value=decoded.text;
    $('notice').textContent=`已按 ${decoded.encoding.toUpperCase()} 读取原文件，请确认中文显示正常后点击导入并检查。`;
  }
  $('import-file').addEventListener('change',()=>{void action(readImportFile);});
  $('import-encoding').addEventListener('change',()=>{void action(readImportFile);});
  $('queue-row').addEventListener('change',()=>{void action(async()=>{queue.index=Number($('queue-row').value);await saveQueue();});});
  $('fill-row').addEventListener('click',()=>{void action(fillCurrent);});
  $('submit-order').addEventListener('click',()=>{void action(async()=>{
    const row=queue?.rows[queue.index];
    if(!row||row.status!=='review'||structuralErrors(row).length)throw new Error('请先填写当前订单并核对完整页面，再点击下单');
    if(row.submitAttempted)throw new Error('本条已尝试点击下单，请核对 DPS 结果，勿重复提交');
    try {
      const values=currentValues();
      checkEffectiveIdentity(values);
      const result=await send('YOUZI_ORDER_SUBMIT',{values});
      if(result.submitAttempted){row.submitAttempted=true;row.submittedFingerprint=imported.fingerprint(values);await saveQueue();}
    } catch(error){throw new Error(error.message+'；如页面已发生变化，请先检查 DPS 结果，勿直接重复下单。');}
  });});
  $('confirm-next').addEventListener('click',()=>{void action(async()=>{
    const row=queue?.rows[queue.index];
    const next=globalThis.YouziOrderQueue.advance(queue,$('submitted').checked);
    history=[...new Set([...history,row.submittedFingerprint||row.filledFingerprint||imported.fingerprint(currentValues())])].slice(-1000);
    queue=next;
    await saveQueue();
    if(queue.rows[queue.index])await fillCurrent();else $('notice').textContent='本批均已由本人确认处理。';
  });});
  $('download-template').addEventListener('click',()=>{
    const url=URL.createObjectURL(new Blob([imported.template()],{type:'text/csv;charset=utf-8'}));
    const link=node('a');link.href=url;link.download='柚子批量填单模板.csv';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  });
  $('desk').addEventListener('click',()=>{void action(async()=>{
    const tab=await targetTab();if(!tab||!model.allowed(tab.url))throw new Error('请先从 DPS 新建页打开助手。');
    await chrome.windows.create({url:chrome.runtime.getURL('popup.html?tab='+tab.id),type:'popup',width:480,height:900});
  });});
  $('order-form').addEventListener('submit', (event) => { event.preventDefault(); void action(async () => {
    const values = data();
    await send('YOUZI_ORDER_FILL', {values, replace: $('replace-existing').checked});
  }); });
  void action(async () => {
    const saved = await chrome.storage.local.get(['orderTemplates', 'orderLastReport','orderQueue','orderHistory','orderAliases','orderVisibleFields','orderCustomerNoFromShipment']);
    $('customer-no-from-shipment').checked=saved.orderCustomerNoFromShipment===true;
    if(Array.isArray(saved.orderVisibleFields))visibleFields=new Set(saved.orderVisibleFields.filter(key=>model.fields.some(field=>field.key===key)));
    applyFieldVisibility();
    templates = saved.orderTemplates || {}; renderTemplates();
    aliases=saved.orderAliases||{}; renderAliases();
    queue=saved.orderQueue||null;history=saved.orderHistory||[];refreshQueueErrors();renderQueue();
    if (saved.orderLastReport) { showRows(saved.orderLastReport); $('notice').textContent = '下方为上一次填写核对表；请先检查当前页面，再进行新一轮填写。'; }
  });
})();
