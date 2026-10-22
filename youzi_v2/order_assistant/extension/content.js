(() => {
  'use strict';
  const version = '0.4.1';
  if (globalThis.YouziOrderBridge) {
    if (globalThis.YouziOrderBridge.version !== version) throw new Error('DPS 页面仍在运行旧版填表脚本。请先保留未提交内容，刷新 DPS 页面，再打开新版助手。');
    return;
  }
  const model = globalThis.YouziOrderModel;
  if (model.version !== version) throw new Error('DPS 页面仍保留旧版字段配置。请先保留未提交内容并刷新 DPS 页面。');
  const wrapperSelector = '.el-form-item,.ant-form-item,.layui-form-item,.form-group,.form-item';
  const labelSelector = 'label,.el-form-item__label,.ant-form-item-label';
  const controlSelector = 'input:not([type=hidden]):not([type=password]):not([type=file]),textarea,select,[role=combobox]';
  const optionSelector = '[role=option],.el-select-dropdown__item,.ant-select-item-option,.ivu-select-item,.el-autocomplete-suggestion li';
  let busy = false, cancelBinding;
  let activeBatchRow='';
  const verifiedChoices = new Map();
  const normalize = (value) => String(value || '').normalize('NFKC').replace(/[\s*：:]/g, '').trim();
  const canonical = (field, value) => ['text','auto'].includes(field.kind) ? String(value || '').trim() : normalize(value);
  const visible = (element) => Boolean(element && element.getClientRects().length && getComputedStyle(element).visibility !== 'hidden');
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  function guard() { if (!model.allowed(location.href)) throw new Error('页面地址已变化，已停止操作。'); }
  function labelOf(root) { return normalize(root?.querySelector(labelSelector)?.textContent || ''); }
  function contextOf(control, field) {
    let parent = (control.closest(wrapperSelector) || control.parentElement)?.parentElement;
    for (let depth = 0; parent && depth < 6; depth++, parent = parent.parentElement) {
      const labels = [...parent.querySelectorAll(labelSelector)].map((label) => normalize(label.textContent));
      if (labels.length < 2 || labels.length > 12) continue;
      if (field.group === '供应商信息' && (!labels.includes('公司名称') || labels.includes('EORI') || labels.includes('派送联系人'))) continue;
      if (field.group === '进口商信息' && (!labels.includes('EORI') || labels.includes('公司名称'))) continue;
      if (field.group === '其它派送地址' && (!labels.includes('派送联系人') || !labels.includes('派送详细地址'))) continue;
      if (field.group === '派送信息' && (!labels.includes('ShipmentID') || !labels.includes('ReferenceID'))) continue;
      if (field.group === '派送信息' && ['箱数(CTN)','毛重(KG)','体积(CBM)'].some((name) => labels.filter((label) => label === normalize(name)).length > 1)) continue;
      return labels.join('|');
    }
    return '';
  }
  function eligible(control) {
    return visible(control) && !control.disabled && !['hidden', 'password', 'file', 'submit', 'button', 'reset', 'checkbox'].includes(control.type);
  }
  function refreshTarget(target) {
    if (target.refresh) Object.assign(target, target.refresh());
    return target.control;
  }
  function resolve(field, bindings) {
    const bound = bindings[field.key];
    if (bound) {
      const matches = document.querySelectorAll(bound.selector);
      if (matches.length !== 1 || !eligible(matches[0])) throw new Error('已定位字段发生变化，请重新定位');
      const control = matches[0]; const root = control.closest(wrapperSelector) || control.parentElement;
      if (labelOf(root) !== bound.label) throw new Error('字段标签已变化，请重新定位');
      if (bound.context !== contextOf(control, field)) throw new Error('字段所属区域已变化，请重新定位');
      return {root, control, refresh: () => resolve(field, bindings)};
    }
    const candidates = [];
    for (const label of document.querySelectorAll(labelSelector)) {
      if (!visible(label) || normalize(label.textContent) !== normalize(field.label)) continue;
      const linked = label.control || (label.htmlFor && document.getElementById(label.htmlFor));
      const root = label.closest(wrapperSelector) || linked?.parentElement;
      if (!root) continue;
      const controls = linked ? [linked] : [...root.querySelectorAll(controlSelector)].filter(eligible);
      if (!controls.length || !eligible(controls[0]) || (!['radio'].includes(field.kind) && controls.length !== 1)) continue;
      if ((['派送信息','其它派送地址'].includes(field.group)||['supplier','importerCountry'].includes(field.key)) && !contextOf(controls[0], field)) continue;
      if (!candidates.some((candidate) => candidate.root === root)) candidates.push({root, control: controls[0]});
    }
    if (candidates.length !== 1) throw new Error(candidates.length ? '存在同名字段，请先定位字段' : '未识别到唯一控件，请先定位字段');
    return {...candidates[0], refresh: () => resolve(field, bindings)};
  }
  function read(target, field) {
    if (field.kind === 'text' || (field.kind === 'auto' && target.control.tagName !== 'SELECT')) return canonical(field, target.control.value);
    if (field.kind === 'radio') {
      const selected = [...target.root.querySelectorAll('input[type=radio]')].filter((input) => input.checked);
      return selected.length === 1 ? normalize(selected[0].closest('label')?.textContent) : '';
    }
    if (target.control.tagName === 'SELECT') return normalize(target.control.selectedOptions[0]?.textContent);
    return normalize(target.control.value || target.root.querySelector('.el-select__selected-item,.ant-select-selection-item')?.textContent || target.control.getAttribute('placeholder') || '');
  }
  function inputValue(control, value, commit = true) {
    if (!['INPUT', 'TEXTAREA'].includes(control.tagName) || control.readOnly || !eligible(control)) throw new Error('输入框不可编辑，请人工填写');
    const prototype = control.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    Object.getOwnPropertyDescriptor(prototype, 'value').set.call(control, value);
    control.dispatchEvent(new Event('input', {bubbles: true}));
    if (commit) {
      control.dispatchEvent(new Event('change', {bubbles: true}));
      control.dispatchEvent(new Event('blur', {bubbles: true}));
    }
  }
  function postalControl() {
    for (const label of ['派送地址邮编','派送邮编']) {
      try { return resolve({key:'deliveryPostcode',label,kind:'text'},{}).control; } catch { /* 未知结构不能猜测其他邮编字段。 */ }
    }
    return null;
  }
  async function verifyChoice(target, option, value, field) {
    const zip = field?.key === 'deliveryAddress'&&target.verifyPostcode!==false ? /\[([^\[\]]+)\]\s*$/.exec(value)?.[1]?.trim() : null;
    let selected = false, postalMissing = false;
    for (let attempt = 0; attempt < 20; attempt++) {
      guard();
      refreshTarget(target);
      selected = option.getAttribute('aria-selected') === 'true' || option.classList.contains('selected') || option.classList.contains('is-selected') || !visible(option);
      const displayed = read(target, field || {kind:'choice'});
      const postal = zip ? postalControl() : null;
      postalMissing = Boolean(postal && String(postal.value || '').trim() !== zip);
      if (selected && displayed === normalize(value) && !postalMissing) return;
      await sleep(100);
    }
    throw new Error(postalMissing ? '已点击地址选项，但派送地址邮编未联动为目标邮编，请人工核对' : '搜索文字一致，但未能确认下拉选项真正选中，请人工核对');
  }
  async function choose(target, value, field) {
    let control = refreshTarget(target);
    if (control.tagName === 'SELECT') {
      const matches = [...control.options].filter((option) => !option.disabled && normalize(option.textContent) === normalize(value));
      if (matches.length !== 1) throw new Error('没有找到唯一的同名选项，未猜测选择');
      control.value = matches[0].value; control.dispatchEvent(new Event('change', {bubbles: true})); return;
    }
    // 只点击当前字段和精确匹配的选项，不点击保存、提交或任意通用按钮。
    control.focus?.();
    if (control.getAttribute('aria-expanded') !== 'true') control.click();
    await sleep(100);
    control = refreshTarget(target);
    const editable = !control.readOnly && control.tagName === 'INPUT';
    const originalQuery = control.value;
    let queries = [value];
    // 搜索键可能只有仓库代码，展示文字则包含国家和邮编。仅放宽搜索词，不放宽最终选项匹配。
    if (editable && ['deliveryAddress','deliveryWarehouse'].includes(field?.key)) {
      const withoutZip = value.normalize('NFKC').replace(/\[[^\[\]]+\]\s*$/, '').trim();
      queries = /^[A-Za-z]{2}-.+/.test(withoutZip) ? [withoutZip.slice(3),withoutZip,value] : [withoutZip,value];
    }
    let loaded = 0, available = 0, owned = false;
    const searches = editable ? [...new Set(queries)] : [value];
    let lastQuery = originalQuery;
    for (const query of searches) {
      control = refreshTarget(target);
      if (!control.readOnly && control.tagName === 'INPUT' && eligible(control)) {
        inputValue(control, query, false); lastQuery = query;
      }
      // 给组件防抖搜索和远端结果一次加载时间，不把尚未更新的列表当成最终结果。
      await sleep(350);
      const deadline = Date.now() + (searches.length > 1 ? 2500 : 5000);
      while (Date.now() < deadline) {
        guard();
        control = refreshTarget(target);
        const owner = control.getAttribute('aria-controls') || control.getAttribute('aria-owns');
        let panel = owner ? document.getElementById(owner) : null;
        if (!panel) {
          const panels = [...document.querySelectorAll('.el-select-dropdown,.ant-select-dropdown,.ivu-select-dropdown,.el-autocomplete-suggestion')].filter((item) => typeof item.querySelectorAll === 'function' && visible(item));
          if (panels.length > 1) throw new Error('同时展开了多个下拉列表，请先收起其他列表再重试');
          if (panels.length === 1) panel = panels[0];
        }
        owned = Boolean(panel);
        const items = [...((panel || document).querySelectorAll(optionSelector) || [])];
        const enabled = items.filter((option) => visible(option) && option.getAttribute('aria-disabled') !== 'true' && !option.classList.contains('is-disabled'));
        loaded = items.length; available = enabled.length;
        const matches = enabled.filter((option) => normalize(option.innerText || option.textContent) === normalize(value));
        if (matches.length > 1) throw new Error('出现多个同名选项，请人工选择');
        if (matches.length === 1) { matches[0].click(); await verifyChoice(target, matches[0], value, field); return; }
        await sleep(150);
      }
    }
    control = refreshTarget(target);
    if (!control.readOnly && eligible(control) && control.tagName === 'INPUT' && control.value === lastQuery) inputValue(control, originalQuery, false);
    throw new Error(`未找到可确认的同名选项。控件${control.readOnly ? '只读，未输入搜索词' : '可编辑'}；已尝试 ${searches.length} 种搜索词；已加载 ${loaded} 项，可用 ${available} 项；${owned ? '已关联列表' : '未关联专属列表'}。请将本条完整核对信息反馈排查。`);
  }
  async function fillField(field, target, value, replace) {
    const current = read(target, field);
    // 可搜索下拉的 input.value 可能只是搜索词，相同文字也必须点选真实选项。
    const customChoice = ['choice','boolean','auto'].includes(field.kind) && target.control.tagName !== 'SELECT';
    if (sameValue(field,current,value) && !customChoice) return;
    if (current && current !== canonical(field, value) && !['请选择', '请输入'].includes(current) && !replace) throw new Error('网页已有不同内容，已保留；需要替换时请明确勾选');
    if (field.kind === 'radio') {
      const options = [...target.root.querySelectorAll('label')].filter((label) => visible(label) && normalize(label.textContent) === normalize(value) && label.querySelector('input[type=radio]'));
      if (options.length !== 1 || options[0].querySelector('input').disabled) throw new Error('未识别到唯一'+field.label+'选项');
      options[0].click();
    } else if (['choice', 'boolean'].includes(field.kind) || (field.kind === 'auto' && (target.control.tagName === 'SELECT' || target.control.readOnly || target.control.getAttribute('role') === 'combobox' || target.control.closest('.el-select,.ant-select,.el-autocomplete')))) await choose(target, value, field);
    else inputValue(target.control, value);
    await sleep(250);
    if (['choice','boolean'].includes(field.kind)) verifiedChoices.set(field.key,{control:target.control,value:canonical(field,value)});
  }
  function displayValue(target, field) {
    if (field.kind === 'radio') return [...target.root.querySelectorAll('input[type=radio]')].filter(input=>input.checked).map(input=>input.closest('label')?.textContent.trim()||'').join(' / ');
    if (target.control.tagName === 'SELECT') return target.control.selectedOptions[0]?.value === '' ? '' : String(target.control.selectedOptions[0]?.textContent||'').trim();
    const text = String(target.control.value || target.root.querySelector('.el-select__selected-item,.ant-select-selection-item')?.textContent || (field.kind === 'choice'||field.kind==='boolean'?target.control.getAttribute('placeholder'):'') || '').trim();
    return ['请选择','请输入'].includes(text) ? '' : text;
  }
  function sameValue(field, actual, expected) {
    if (['ctns','weight','volume'].includes(field.key)) return /^\d+(?:\.\d+)?$/.test(actual) && /^\d+(?:\.\d+)?$/.test(expected) && Number(actual) === Number(expected);
    return canonical(field,actual) === canonical(field,expected);
  }
  function choiceConfirmed(target, field, actual) {
    if (!['choice','boolean'].includes(field.kind) || target.control.tagName === 'SELECT') return true;
    if (target.control.getAttribute('aria-expanded') === 'true') return false;
    const proof = verifiedChoices.get(field.key);
    if (proof?.control === target.control && proof.value === canonical(field,actual)) return true;
    const selectedText = target.root.querySelector('.el-select__selected-item,.ant-select-selection-item')?.textContent;
    if (selectedText && normalize(selectedText) === normalize(actual)) return true;
    const owner = target.control.getAttribute('aria-controls') || target.control.getAttribute('aria-owns');
    const panel = owner ? document.getElementById(owner) : null;
    const selected = [...(panel?.querySelectorAll(optionSelector)||[])].filter(option=>option.getAttribute('aria-selected')==='true'||option.classList.contains('selected')||option.classList.contains('is-selected'));
    return selected.length === 1 && normalize(selected[0].innerText||selected[0].textContent) === normalize(actual);
  }
  function buildSummary(values, bindings, aliases, enabledFields) {
    const scoped=Array.isArray(enabledFields);
    const clean = scoped?model.selectedValues(values,enabledFields):model.withDefaults(values);
    const keys = scoped?new Set(enabledFields):new Set(['sales','customer','supplier','channel','insurance','dpsCustoms','customerOrderNo','referenceNo','customsType','deliveryWarehouse','deliveryAddress','shipmentId','referenceId','ctns','weight','volume','productName',...Object.keys(clean)]);
    if(!scoped){keys.add('deliveryAddressType');keys.add('deliveryPostcode');}
    let addressType=clean.deliveryAddressType;
    if(!addressType)try{addressType=displayValue(resolve(model.fields.find(field=>field.key==='deliveryAddressType'),bindings),model.fields.find(field=>field.key==='deliveryAddressType'));}catch{ /* 无法确认时保留人工核对。 */ }
    if(!scoped){
      if(addressType==='其它地址'&&!clean.deliveryContact)clean.deliveryContact='待定(000000)';
      if(addressType==='其它地址'){keys.delete('deliveryAddress');for(const key of model.otherAddressKeys)keys.add(key);}
      else for(const key of model.otherAddressKeys)if(!clean[key])keys.delete(key);
    }
    return model.fields.filter(field=>keys.has(field.key)).map(field=>{
      const original = clean[field.key]||'';
      const row = {key:field.key,label:field.label,group:field.group,expected:original,actual:'',status:'unreadable',message:''};
      if(scoped&&!original){row.status='notProvided';row.message='空白，跳过，不修改网页';return row;}
      try {
        const expected = original ? model.resolveAlias(field.key,original,aliases).value : '';
        row.expected=expected;
        guard(); const target = resolve(field,bindings);row.actual = displayValue(target,field);
        if (!expected) {row.status='notProvided';row.message=field.key==='productName'?'未提供，跳过填写':'未提供目标值，请人工核对';}
        else if (!row.actual) {row.status='missing';row.message='网页未填';}
        else if (!sameValue(field,row.actual,expected)) {row.status='mismatch';row.message='不一致';}
        else if (!choiceConfirmed(target,field,row.actual)) {row.status='unconfirmed';row.message='文字一致，选中状态需核对';}
        else {row.status='match';row.message='一致';}
        if (row.status==='match'&&field.key==='deliveryAddress') {
          const zip=/\[([^\[\]]+)\]\s*$/.exec(expected)?.[1]?.trim(),postal=zip&&(!scoped||keys.has('deliveryPostcode'))?postalControl():null;
          if(postal&&String(postal.value||'').trim()!==zip){row.status='mismatch';row.message='地址文字一致，但联动邮编不一致';}
        }
      } catch(error) {row.message='无法读取：'+error.message;}
      return row;
    });
  }
  async function compare(values,enabledFields) {
    guard();if(busy)throw new Error('有填写或定位正在进行，请稍后核对');busy=true;
    try {
      const {orderBindings={},orderAliases={}}=await chrome.storage.local.get(['orderBindings','orderAliases']);
      return {summary:buildSummary(values,orderBindings,orderAliases,enabledFields),message:'已重新读取本次启用字段核对；未修改、保存或提交订单。'};
    } finally {busy=false;}
  }
  async function run(values, replace, scan = false, batch = false, batchRow = '',customerNoFromShipment=false,enabledFields) {
    guard();
    if (busy) throw new Error('上一轮填写或定位仍在进行，请等待');
    const scoped=Array.isArray(enabledFields);
    const clean = scoped?model.selectedValues(values,enabledFields):scan ? model.clean(values) : model.withDefaults(model.customerNumber(values,customerNoFromShipment));
    if (!scan&&!scoped) { const errors = model.validate(clean,true); if (errors.length) throw new Error(errors.join('\n')); }
    busy = true;
    try {
      const {orderBindings = {}, orderAliases = {}} = await chrome.storage.local.get(['orderBindings','orderAliases']);
      if(!scoped&&!scan&&!clean.deliveryAddressType){
        try{
          const field=model.fields.find(field=>field.key==='deliveryAddressType');
          if(read(resolve(field,orderBindings),field)===normalize('其它地址')){
            clean.deliveryAddressType='其它地址';
            if(!clean.deliveryContact)clean.deliveryContact='待定(000000)';
          }
        }catch{ /* 未确认地址类型时，不填写其它地址联系人。 */ }
      }
      const mapped = new Set(), mappingErrors = new Map();
      let allowCustomerNoCopy=false;
      const copyTarget=clean.shipmentId||(customerNoFromShipment?clean.customerOrderNo:'');
      if(customerNoFromShipment&&copyTarget)try{allowCustomerNoCopy=read(resolve(model.fields.find(field=>field.key==='shipmentId'),orderBindings),model.fields.find(field=>field.key==='shipmentId'))===copyTarget;}catch{ /* 无法确认同一Shipment时保留原客户单号。 */ }
      if (!scan) for (const field of model.fields) {
        if (!clean[field.key]) continue;
        try {
          const alias = model.resolveAlias(field.key, clean[field.key], orderAliases);
          clean[field.key] = alias.value;
          if (alias.used) mapped.add(field.key);
        } catch(error) { mappingErrors.set(field.key,error.message); }
      }
      if (batch && !scan) {
        if(batchRow&&activeBatchRow&&batchRow!==activeBatchRow){
          for(const field of model.fields.filter(field=>field.perOrder)){
            let current='';try{current=displayValue(resolve(field,orderBindings),field);}catch{ /* 其他可识别的每单字段仍继续检查。 */ }
            if(current)throw new Error('上一条订单仍在当前页面。请先确认下单结果，再打开空白新建页填写下一条。');
          }
        }
        for (const field of model.fields.filter((field) => field.perOrder && clean[field.key]&&!['deliveryAddress','deliveryPostcode',...model.otherAddressKeys].includes(field.key))) {
          if(scoped)continue;
          if(field.key==='customerOrderNo'&&allowCustomerNoCopy)continue;
          const current = read(resolve(field, orderBindings), field);
          if (sameValue(field,current,clean[field.key])) continue;
          if (current && !['请选择','请输入'].includes(current)) throw new Error('每单字段已有内容。请先确认上一单是否已下单，再打开空白新建页，避免覆盖或重复填写。');
        }
        if(batchRow)activeBatchRow=batchRow;
      }
      const rows = [];
      for (const field of model.fields) {
        if(scoped&&!enabledFields.includes(field.key))continue;
        guard(); const value = clean[field.key];
        const row = {label: `${field.group} · ${field.label}`, ok: false, key: field.key}; rows.push(row);
        if (!scan && !value) { row.message = '未提供，保留网页原值并人工核对'; continue; }
        if(!scan&&field.key==='deliveryAddress'&&clean.deliveryAddressType==='其它地址'){row.message='其它地址模式，跳过FBA地址';continue;}
        if(!scan&&model.otherAddressKeys.includes(field.key)&&clean.deliveryAddressType==='FBA地址'){row.message='FBA地址模式，跳过其它地址字段';continue;}
        try {
          if(mappingErrors.has(field.key))throw new Error(mappingErrors.get(field.key));
          const target = resolve(field, orderBindings);
          target.verifyPostcode=!scoped||enabledFields.includes('deliveryPostcode');
          if (scan) { row.ok = true; row.message = '已识别控件；选项是否存在需填写时确认'; continue; }
          const replaceDefault = (batch && ['sales','customer','subCustomer','supplier','channel'].includes(field.key)) || ['insurance','dpsCustoms','customsType','deliveryAddressType'].includes(field.key)||(field.key==='customerOrderNo'&&allowCustomerNoCopy);
          if(scoped){const errors=model.validate({[field.key]:value},true);if(errors.length)throw new Error(errors.join('；'));}
          await fillField(field, target, value, replace === true || replaceDefault);
          if (!sameValue(field,read(resolve(field, orderBindings), field),value)) throw new Error('填写后未能确认选中结果，请人工核对');
          row.ok = true; row.message = mapped.has(field.key) ? '已按简称对照填写完整名称并复核，请提交前核对' : '填写后显示值一致，提交前仍需核对';
        } catch (error) { row.message = error.message; }
      }
      // 父级选择可能清空已填字段，结束时再核验一次，避免保留早先的成功标记。
      if (!scan) for (const row of rows.filter((row) => row.ok)) {
        try {
          const field = model.fields.find((item) => item.key === row.key);
          if (!sameValue(field,read(resolve(field, orderBindings), field),clean[row.key])) throw new Error('字段被页面联动改变，请人工核对');
        } catch (error) { row.ok = false; row.message = error.message; }
      }
      const report = rows.map(({label, ok, message}) => ({label, ok, message}));
      if (!scan) await chrome.storage.local.set({orderLastReport: report});
      return {rows: report, ...(!scan?{summary:buildSummary(scoped?clean:model.customerNumber(values,customerNoFromShipment),orderBindings,orderAliases,enabledFields)}:{}), message: scan ? '检查只识别已启用字段位置，没有修改表单。' : '本次字段填写结束。隐藏字段未操作，空白项已跳过；请核对结果。未保存或提交订单。'};
    } finally { busy = false; }
  }
  function selectorFor(element) {
    if (element.id && document.querySelectorAll('#' + CSS.escape(element.id)).length === 1) return '#' + CSS.escape(element.id);
    const parts = [];
    for (let current = element; current && current !== document.documentElement; current = current.parentElement) {
      const index = [...current.parentElement.children].indexOf(current) + 1;
      parts.unshift(current.tagName.toLowerCase() + ':nth-child(' + index + ')');
    }
    return 'html > ' + parts.join(' > ');
  }
  function bind(key) {
    guard(); if (busy) throw new Error('有操作正在进行，请稍后再定位');
    const field = model.fields.find((item) => item.key === key); if (!field) throw new Error('无效字段');
    busy = true;
    const banner = document.createElement('div');
    banner.textContent = `柚子：请点击「${field.group} · ${field.label}」输入框；按 Esc 取消。30 秒后自动退出。`;
    banner.setAttribute('style', 'position:fixed;top:10px;left:10px;right:10px;z-index:2147483647;padding:16px;background:#eaf2ff;color:#23477d;border:1px solid #6798ed;font:14px sans-serif;');
    document.body.append(banner);
    let timer;
    function stop() { clearTimeout(timer); document.removeEventListener('click', pick, true); document.removeEventListener('keydown', escape, true); banner.remove(); busy = false; cancelBinding = null; }
    function escape(event) { if (event.key === 'Escape') stop(); }
    async function pick(event) {
      if (banner.contains(event.target)) return;
      event.preventDefault(); event.stopImmediatePropagation();
      try {
        guard();
        const control = event.target.closest(controlSelector);
        const root = control?.closest(wrapperSelector) || control?.parentElement;
        if (!control || !eligible(control) || labelOf(root) !== normalize(field.label)) { banner.textContent = '未选中对应标签的输入框，请重新点击；Esc 取消。'; return; }
        const context = contextOf(control, field);
        if ((field.label === '地址' || field.group === '派送信息') && !context) { banner.textContent = '未能确认所属区域，请按 Esc 退出，暂时手工填写。'; return; }
        const {orderBindings = {}} = await chrome.storage.local.get('orderBindings');
        await chrome.storage.local.set({orderBindings: {...orderBindings, [key]: {selector: selectorFor(control), label: labelOf(root), context}}});
        stop();
      } catch { banner.textContent = '定位未完成，请按 Esc 退出后重试。'; }
    }
    document.addEventListener('click', pick, true); document.addEventListener('keydown', escape, true);
    timer = setTimeout(stop, 30000); cancelBinding = stop;
    return {message: '请关闭助手弹窗，在网页点击对应输入框；然后重新打开助手检查。'};
  }
  async function retry(key, value,enabledFields) {
    guard(); if (busy) throw new Error('有操作正在进行，请稍后再试');
    const field = model.fields.find((item) => item.key === key);
    if (!field || !['choice','boolean','radio'].includes(field.kind)) throw new Error('仅支持单独重试下拉字段或报关类型');
    const clean = model.clean({[key]:value});
    if (!clean[key]) throw new Error('当前订单或公共模板未提供该字段，请先填写目标完整名称');
    busy = true;
    try {
      const {orderBindings = {}, orderAliases = {}} = await chrome.storage.local.get(['orderBindings','orderAliases']);
      const targetValue = model.resolveAlias(key, clean[key], orderAliases).value;
      const row = {label:`${field.group} · ${field.label}`,ok:false,message:''};
      try {
        const target=resolve(field,orderBindings);target.verifyPostcode=!Array.isArray(enabledFields)||enabledFields.includes('deliveryPostcode');
        await fillField(field, target, targetValue, ['insurance','dpsCustoms','customsType','deliveryAddressType'].includes(key));
        if (read(resolve(field,orderBindings),field) !== canonical(field,targetValue)) throw new Error('填写后显示值不一致，请人工核对');
        row.ok = true; row.message = '本项已选择并复核；请核对关联字段';
      } catch(error) { row.message = error.message; }
      return {rows:[row],message:`脚本 ${version}：仅重试了所选项目，未重新填写其他字段，未保存或提交。`};
    } finally { busy = false; }
  }
  function orderButton() {
    const matches=[...document.querySelectorAll('button,input[type=submit],input[type=button]')].filter(button=>visible(button)&&String(button.tagName==='INPUT'?button.value:button.textContent).replace(/\s/g,'')==='下单');
    if(matches.length!==1)throw new Error('未找到唯一可见的“下单”按钮，未点击');
    const button=matches[0];
    if(button.disabled||button.getAttribute('aria-disabled')==='true'||button.classList.contains('is-disabled')||button.classList.contains('is-loading'))throw new Error('DPS 下单按钮不可用或正在处理，请先核对页面结果');
    return button;
  }
  function requiredForSubmit(key,addressType) {
    return model.fields.find(field=>field.key===key)?.required||['customerOrderNo','shipmentId','referenceId','deliveryWarehouse','deliveryAddressType','deliveryPostcode','ctns','weight','volume',...(addressType==='其它地址'?['deliveryCountry','deliveryStreet']:['deliveryAddress'])].includes(key);
  }
  const summaryAddressType=summary=>summary.find(row=>row.key==='deliveryAddressType')?.actual||'';
  function submitBlockers(summary) {
    return summary.filter(row=>row.expected?row.status!=='match':requiredForSubmit(row.key,summaryAddressType(summary))&&(!row.actual||['missing','mismatch','unreadable','unconfirmed'].includes(row.status)));
  }
  function submissionSummary(values,bindings,aliases) {
    const summary=buildSummary(values,bindings,aliases);
    for(const row of summary.filter(row=>!row.expected&&requiredForSubmit(row.key,summaryAddressType(summary)))){
      const field=model.fields.find(field=>field.key===row.key);
      if(!row.actual){row.status='missing';row.message='下单前需补齐';}
      else if(!choiceConfirmed(resolve(field,bindings),field,row.actual)){row.status='unconfirmed';row.message='沿用网页值，但无法确认已选中';}
      else if(['ctns','weight','volume'].includes(row.key)&&model.validate({[row.key]:row.actual},true).length){row.status='mismatch';row.message='网页数值格式或范围不正确';}
    }
    return summary;
  }
  async function submitOrder(values,customerNoFromShipment=false,enabledFields) {
    guard();if(busy)throw new Error('有填写、核对或下单正在进行，请等待');
    if(!globalThis.navigator?.locks||!globalThis.crypto?.subtle)throw new Error('当前浏览器无法建立防重复下单锁，请在 DPS 页面手工下单');
    busy=true;
    try {
      return await navigator.locks.request('youzi-order-submit',{mode:'exclusive'},async()=>{
        guard();
        const {orderSubmitAttempts={},orderBindings={},orderAliases={}}=await chrome.storage.local.get(['orderSubmitAttempts','orderBindings','orderAliases']);
        const scoped=Array.isArray(enabledFields);
        if(scoped)values=model.selectedValues(values,enabledFields);
        const summary=scoped?buildSummary(values,orderBindings,orderAliases,enabledFields):submissionSummary(values,orderBindings,orderAliases);
        const identity=['customerOrderNo','shipmentId','referenceId'].map(key=>{
          let actual=summary.find(row=>row.key===key)?.actual||'';
          if(scoped&&!actual)try{const field=model.fields.find(field=>field.key===key);actual=displayValue(resolve(field,orderBindings),field);}catch{ /* 无编号时以本次字段快照建立防重记录。 */ }
          return String(values?.[key]||actual||'').trim();
        });
        if(!scoped&&identity.some(value=>!value))throw new Error('下单前必须提供或在网页补齐客户单号、Shipment ID 和 Reference ID，避免下错单');
        if(customerNoFromShipment&&(!scoped||enabledFields.includes('customerOrderNo')&&enabledFields.includes('shipmentId'))&&identity[0]!==identity[1]){
          const row=summary.find(row=>row.key==='customerOrderNo');row.expected=identity[1];row.status='mismatch';row.message='客户单号需与Shipment ID一致';
          return {summary,submitAttempted:false,message:'未点击下单：已勾选客户单号与Shipment ID一致，请先修正客户单号。'};
        }
        const duplicateKey=identity.some(Boolean)?identity:['fields',...summary.filter(row=>row.expected).map(row=>[row.key,row.expected])];
        const digest=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(JSON.stringify(duplicateKey)));
        const fingerprint=Array.from(new Uint8Array(digest),byte=>byte.toString(16).padStart(2,'0')).join('');
        if(Object.hasOwn(orderSubmitAttempts,fingerprint))throw new Error('该订单已尝试点击下单。请先核对 DPS 是否成功，助手不会重复点击；不要直接重试或重导入');
        const blockers=scoped?summary.filter(row=>row.expected&&row.status!=='match'):submitBlockers(summary);
        if(blockers.length)return {summary,submitAttempted:false,message:'未点击下单：'+blockers.map(row=>row.label+'（'+row.message+'）').join('、')+'。请修正并核对后再次点击。'};
        orderButton();
        // 点击前先持久记录。网页跳转、消息丢失或点击异常时都不能自动重试。
        await chrome.storage.local.set({orderSubmitAttempts:{...orderSubmitAttempts,[fingerprint]:{state:'attempting',at:Date.now()}}});
        guard();
        const manual=Object.fromEntries(summary.filter(row=>!row.expected&&row.actual&&requiredForSubmit(row.key,summaryAddressType(summary))).map(row=>[row.key,row.actual]));
        const fresh=scoped?buildSummary(values,orderBindings,orderAliases,enabledFields):submissionSummary({...values,...manual},orderBindings,orderAliases);
        if((scoped?fresh.filter(row=>row.expected&&row.status!=='match'):submitBlockers(fresh)).length)throw new Error('核对后网页内容发生变化，已停止下单。请人工核对 DPS；防重复记录已保留');
        const button=orderButton();
        button.click();
        return {summary,submitAttempted:true,message:'已点击一次 DPS“下单”，尚未确认成功。请查看网页成功提示或运单记录；确认成功后再勾选并记录下一条。'};
      });
    } finally {busy=false;}
  }
  globalThis.YouziOrderBridge = {version, run, resolve, normalize, options, retry, compare, submitOrder};
  async function options(key) {
    guard(); if (busy) throw new Error('有填写或定位正在进行');
    const field = model.fields.find((item) => item.key === key);
    if (!field || !['choice','auto','boolean'].includes(field.kind)) throw new Error('请选择一个下拉字段');
    busy = true;
    try {
      const {orderBindings = {}} = await chrome.storage.local.get('orderBindings');
      const {control} = resolve(field, orderBindings);
      if (control.tagName === 'SELECT') return {options: [...control.options].filter((option) => !option.disabled && option.value !== '').map((option) => option.textContent.trim()), message: '已读取原生下拉选项，未改变选择。'};
      control.click();
      for (let attempt = 0; attempt < 20; attempt++) {
        guard();
        const owner = control.getAttribute('aria-controls') || control.getAttribute('aria-owns');
        const panel = owner ? document.getElementById(owner) : document;
        const list = [...(panel?.querySelectorAll(optionSelector) || [])].filter(visible).map((option) => option.textContent.trim());
        if (list.length) return {options: [...new Set(list)], message: '已读取当前加载的可见选项；搜索型或滚动列表可能还有其他项。未选择任何选项。'};
        await sleep(150);
      }
      throw new Error('没有读到可见选项，请手动展开该下拉后再试。');
    } finally { busy = false; }
  }
  chrome.runtime.onMessage.addListener((message, sender, respond) => {
    if (sender.id !== chrome.runtime.id || !['YOUZI_ORDER_SCAN', 'YOUZI_ORDER_FILL', 'YOUZI_ORDER_BIND','YOUZI_ORDER_OPTIONS','YOUZI_ORDER_RETRY','YOUZI_ORDER_COMPARE','YOUZI_ORDER_SUBMIT'].includes(message.type)) return;
    const enabled=Array.isArray(message.enabledFields)?message.enabledFields.filter(key=>model.fields.some(field=>field.key===key)):[];
    if(enabled&&message.field&&!enabled.includes(message.field)){respond({error:'该字段已隐藏，本次不操作'});return;}
    Promise.resolve().then(() => message.type === 'YOUZI_ORDER_SUBMIT' ? submitOrder(message.values,message.customerNoFromShipment===true,enabled) : message.type === 'YOUZI_ORDER_COMPARE' ? compare(message.values,enabled) : message.type === 'YOUZI_ORDER_RETRY' ? retry(message.field,message.value,enabled) : message.type === 'YOUZI_ORDER_BIND' ? bind(message.field) : message.type === 'YOUZI_ORDER_OPTIONS' ? options(message.field) : run(message.values, message.replace, message.type === 'YOUZI_ORDER_SCAN', message.batch === true,typeof message.batchRow==='string'?message.batchRow:'',message.customerNoFromShipment===true,enabled)).then(respond, (error) => respond({error: error.message}));
    return true;
  });
  window.addEventListener('pagehide', () => { cancelBinding?.(); });
  function invalidateChoiceProof(event) {
    for(const [key,proof] of verifiedChoices)if(proof.control===event.target)verifiedChoices.delete(key);
  }
  document.addEventListener('input',invalidateChoiceProof,true);
  document.addEventListener('change',invalidateChoiceProof,true);
})();
