(() => {
  'use strict';
  if (globalThis.YouziOrderModel) return;
  const fields = [
    ['sales', '销售', '基本信息', 'choice', true],
    ['customer', '大客户', '基本信息', 'choice', true],
    ['subCustomer', '小客户', '基本信息', 'choice'],
    ['channel', '渠道名称', '基本信息', 'choice', true],
    ['insurance', '是否需要保险', '基本信息', 'boolean', true],
    ['dpsCustoms', '是否需要DPS清关', '基本信息', 'boolean'],
    ['packageType', '包装类型', '基本信息', 'choice'],
    ['taxNumber', '税号', '基本信息', 'text'],
    ['customerOrderNo', '客户单号', '基本信息', 'text', false, true],
    ['referenceNo', '关联单号', '基本信息', 'text', false, true],
    ['supplier', '公司名称', '供应商信息', 'choice', true],
    ['supplierContact', '联系人名称', '供应商信息', 'text'],
    ['supplierPhone', '联系方式', '供应商信息', 'text'],
    ['supplierEmail', '邮箱', '供应商信息', 'text'],
    ['supplierAddress', '地址', '供应商信息', 'text'],
    ['importer', '名称', '进口商信息', 'choice'],
    ['importerCountry', '国家', '进口商信息', 'choice'],
    ['eori', 'EORI', '进口商信息', 'text'],
    ['vat', 'VAT', '进口商信息', 'text'],
    ['importerAddress', '地址', '进口商信息', 'text'],
    ['customsType', '报关类型', '清关信息', 'radio', true],
    ['refundCopies', '退税份数', '清关信息', 'text'],
    ['deliveryWarehouse', '交货仓库', '交付信息', 'choice', false, true],
    ['deliveryAddressType', '派送地址类型', '交付信息', 'radio'],
    ['deliveryAddress', '派送地址', '交付信息', 'choice', false, true],
    ['deliveryContact', '派送联系人', '其它派送地址', 'choice', false, true],
    ['deliveryCompany', '公司名称', '其它派送地址', 'text', false, true],
    ['deliveryPhone', '派送手机号', '其它派送地址', 'text', false, true],
    ['deliveryCountry', '国家', '其它派送地址', 'choice', false, true],
    ['deliveryProvince', '省份', '其它派送地址', 'choice', false, true],
    ['deliveryCity', '城市', '其它派送地址', 'choice', false, true],
    ['deliveryPostcode', '派送地址邮编', '交付信息', 'text', false, true],
    ['deliveryStreet', '派送详细地址', '其它派送地址', 'text', false, true],
    ['shipmentId', 'Shipment ID', '派送信息', 'text', false, true],
    ['referenceId', 'Reference ID', '派送信息', 'text', false, true],
    ['ctns', '箱数(CTN)', '派送信息', 'text', false, true],
    ['weight', '毛重(KG)', '派送信息', 'text', false, true],
    ['volume', '体积(CBM)', '派送信息', 'text', false, true],
    ['productName', '产品品名', '产品信息', 'text', false, true],
  ].map(([key, label, group, kind, required = false, perOrder = false]) => ({key, label, group, kind, required, perOrder}));
  const otherAddressKeys=['deliveryContact','deliveryCompany','deliveryPhone','deliveryCountry','deliveryProvince','deliveryCity','deliveryStreet'];
  const radioChoices={customsType:['买单','退税','买单+退税'],deliveryAddressType:['FBA地址','其它地址']};
  function allowed(url) {
    const page = globalThis.YouziOrderPage;
    if (!page || typeof page.origin !== 'string' || typeof page.pathname !== 'string') return false;
    try {
      const value = new URL(url);
      const path = page.pathname.replace(/\/$/, '');
      return value.origin === page.origin && !value.search && !value.hash && value.pathname.replace(/\/$/, '') === path;
    } catch { return false; }
  }
  function clean(data, template = false) {
    const result = {};
    for (const field of fields) {
      if (template && field.perOrder) continue;
      if (typeof data?.[field.key] === 'string') result[field.key] = data[field.key].trim();
    }
    if(result.deliveryAddressType==='其他地址')result.deliveryAddressType='其它地址';
    return result;
  }
  const defaults = {insurance:'否',dpsCustoms:'否'};
  function withDefaults(data) {
    const result = clean(data);
    for (const [key,value] of Object.entries(defaults)) if (!result[key]) result[key] = value;
    if(!result.deliveryAddressType){
      if(otherAddressKeys.some(key=>result[key]))result.deliveryAddressType='其它地址';
      else if(result.deliveryAddress)result.deliveryAddressType='FBA地址';
    }
    if(result.deliveryAddressType==='其它地址'&&!result.deliveryContact)result.deliveryContact='待定(000000)';
    return result;
  }
  function customerNumber(data,sameAsShipment=false){
    const result=clean(data);
    if(sameAsShipment&&result.shipmentId)result.customerOrderNo=result.shipmentId;
    return result;
  }
  function selectedValues(data,enabledFields){
    const cleanData=clean(data),keys=new Set(enabledFields);
    return Object.fromEntries(Object.entries(cleanData).filter(([key])=>keys.has(key)));
  }
  // 使用模板中的完整名称；只应用本人手工保存的对照，没有仓库特例。
  const defaultAliases = {};
  const aliasKey = (value) => String(value || '').normalize('NFKC').trim().toUpperCase();
  function aliasEntries(key, saved = {}) {
    const field = fields.find((field) => field.key === key);
    if (!field || !['choice','auto'].includes(field.kind)) return [];
    const entries = new Map();
    for (const [short, full] of Object.entries(defaultAliases[key] || {})) entries.set(aliasKey(short), {short, full, builtin:true});
    const custom = new Map();
    for (const [short, full] of Object.entries(saved[key] || {})) {
      if (typeof full !== 'string' || !short.trim() || !full.trim() || short.length > 1000 || full.length > 1000) throw new Error('简称对照格式不正确，请重新保存。');
      const normalized = aliasKey(short);
      if (custom.has(normalized) && custom.get(normalized).full !== full.trim()) throw new Error('同一简称存在多个映射，请先统一简称对照。');
      custom.set(normalized, {short:short.trim(),full:full.trim(),builtin:false});
    }
    for (const [short, entry] of custom) entries.set(short, entry);
    return [...entries.values()];
  }
  function resolveAlias(key, value, saved = {}) {
    const original = String(value || '').trim();
    const entry = aliasEntries(key, saved).find((entry) => aliasKey(entry.short) === aliasKey(original));
    return {value:entry ? entry.full : original, used:Boolean(entry && entry.full !== original)};
  }
  function validate(data, partial = false) {
    const errors = [];
    for (const field of fields) {
      const value = data[field.key] || '';
      if (!partial && field.required && !value) errors.push(`${field.group} · ${field.label}未填写`);
      if (value.length > 1000) errors.push(`${field.label}内容过长`);
      if (field.kind === 'boolean' && value && !['是', '否'].includes(value)) errors.push(`${field.label}只能选择是或否`);
    }
    if (data.customsType && !['买单', '退税', '买单+退税'].includes(data.customsType)) errors.push('报关类型必须明确选择');
    if(data.deliveryAddressType&&!radioChoices.deliveryAddressType.includes(data.deliveryAddressType))errors.push('派送地址类型只能选择FBA地址或其它地址');
    if(data.deliveryAddressType==='其它地址'&&data.deliveryAddress)errors.push('其它地址请填写国家、邮编和派送详细地址，不要填写FBA派送地址列');
    if(data.deliveryAddressType==='FBA地址'&&otherAddressKeys.some(key=>data[key]))errors.push('FBA地址不能同时填写其它地址专用字段');
    if (data.refundCopies && !/^[1-9]\d*$/.test(data.refundCopies)) errors.push('退税份数应为正整数，请按实际业务填写');
    if (data.supplierEmail && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(data.supplierEmail)) errors.push('供应商邮箱格式需核对');
    if(data.ctns&&(!/^[1-9]\d*$/.test(data.ctns)||!Number.isSafeInteger(Number(data.ctns))))errors.push('箱数必须为可表示的正整数');
    for(const key of ['weight','volume'])if(data[key]&&(!/^\d+(?:\.\d+)?$/.test(data[key])||!Number.isFinite(Number(data[key]))||Number(data[key])<=0))errors.push((key==='weight'?'毛重':'体积')+'必须为正数');
    return errors;
  }
  globalThis.YouziOrderModel = {version:'0.4.1', fields, defaults, radioChoices, otherAddressKeys, selectedValues, customerNumber, withDefaults, allowed, clean, validate, aliasKey, aliasEntries, resolveAlias};
  if (typeof module !== 'undefined') module.exports = globalThis.YouziOrderModel;
})();
