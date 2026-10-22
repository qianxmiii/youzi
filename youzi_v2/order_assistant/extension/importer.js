(() => {
  'use strict';
  if (globalThis.YouziOrderImport) return;
  const columns = [
    ['sales','销售',[],true], ['customer','客户',['大客户'],true], ['supplier','公司名称',['供应商','供应商名称'],true],
    ['channel','渠道名称',['渠道']], ['customerOrderNo','客户单号',[]], ['referenceNo','关联单号',[]],
    ['customsType','报关类型',[],true],
    ['deliveryWarehouse','交货仓库',[]], ['deliveryAddress','派送地址',[]],
    ['shipmentId','Shipment ID',[]], ['referenceId','Reference ID',[]],
    ['ctns','箱数(CTN)',['箱数','CTN']], ['weight','毛重(KG)',['毛重','KG']], ['volume','体积(CBM)',['体积','CBM']],
    ['productName','产品品名',['产品名称'],true],
    ['deliveryAddressType','派送地址类型',['地址类型'],true],
    ['deliveryContact','派送联系人',[],true],['deliveryCompany','派送公司名称',[],true],['deliveryPhone','派送手机号',[],true],
    ['deliveryCountry','派送国家',[],true],['deliveryProvince','派送省份',[],true],['deliveryCity','派送城市',[],true],
    ['deliveryPostcode','派送地址邮编',['派送邮编'],true],['deliveryStreet','派送详细地址',[],true],
  ];
  const norm = (value) => String(value).normalize('NFKC').replace(/[\s_()]/g,'').toLowerCase();
  const aliases = new Map(columns.flatMap(([key,label,extra])=>[key,label,...extra].map(name=>[norm(name),key])));
  const fingerprint = (data) => JSON.stringify([data.customerOrderNo||'',data.shipmentId||'',data.referenceId||'']);
  function decode(buffer, encoding = 'auto') {
    const bytes = buffer instanceof Uint8Array ? buffer : new Uint8Array(buffer);
    if (bytes.byteLength > 2_000_000) throw new Error('文件请控制在 2 MB 以内。');
    if (bytes[0] === 0x50 && bytes[1] === 0x4b) throw new Error('这可能是 Excel .xlsx 文件，请另存为 CSV，或直接复制 Excel 表格粘贴。');
    if (!['auto','utf-8','gb18030','utf-16le','utf-16be'].includes(encoding)) throw new Error('不支持的文件编码。');
    let selected = encoding, text;
    try {
      if (selected === 'auto') {
        if (bytes[0] === 0xff && bytes[1] === 0xfe) selected = 'utf-16le';
        else if (bytes[0] === 0xfe && bytes[1] === 0xff) selected = 'utf-16be';
        else if (bytes[0] === 0xef && bytes[1] === 0xbb && bytes[2] === 0xbf) selected = 'utf-8';
        else {
          try { text = new TextDecoder('utf-8', {fatal:true}).decode(bytes); selected = 'utf-8'; }
          catch { selected = 'gb18030'; }
        }
      }
      if (text === undefined) text = new TextDecoder(selected, {fatal:true}).decode(bytes);
    } catch { throw new Error('无法按所选编码读取文件。请切换 CSV 编码，或另存为 CSV UTF-8 后重新选择原文件。'); }
    if (text.includes('\uFFFD')) throw new Error('文件文字中已经含有乱码替代符（�），无法恢复原文。请重新从 Excel 导出原始 CSV，或直接复制表格粘贴。');
    return {text:text.replace(/^\uFEFF/,''), encoding:selected};
  }
  function parse(text, history = [], enabledFields) {
    if (typeof text !== 'string' || text.length > 2_000_000) throw new Error('请导入不超过 2 MB 的 CSV/TSV 文本。');
    text=text.replace(/^\uFEFF/,'');
    if (text.includes('\uFFFD')) throw new Error('当前文字已出现乱码（�）。请重新选择原 CSV 文件，或从 Excel 重新复制；不要继续导入这段乱码。');
    const delimiter=text.split(/\r?\n/,1)[0].includes('\t')?'\t':',';
    const rows=[]; let row=[],cell='',quoted=false,closed=false;
    function pushCell(){ row.push(cell);cell='';closed=false; }
    function pushRow(){ pushCell();if(row.some(value=>value.trim()))rows.push(row);row=[]; }
    for(let index=0;index<text.length;index++) {
      const char=text[index];
      if(quoted) { if(char==='"') { if(text[index+1]==='"'){cell+='"';index++;}else{quoted=false;closed=true;} }else cell+=char; continue; }
      if(char==='"') { if(cell||closed) throw new Error('引号格式错误，请重新导出 CSV。');quoted=true; }
      else if(char===delimiter)pushCell();
      else if(char==='\n'||char==='\r'){if(char==='\r'&&text[index+1]==='\n')index++;pushRow();}
      else {if(closed)throw new Error('闭合引号后存在额外字符。');cell+=char;}
    }
    if(quoted)throw new Error('存在未闭合的引号。');
    if(cell||row.length||closed)pushRow();
    if(rows.length<2)throw new Error('需要表头和至少一行订单数据。');
    if(rows.length>501)throw new Error('每批最多 500 单，请拆分导入。');
    const originalHeaders=rows.shift();
    const headers=originalHeaders.map(value=>aliases.get(norm(value)));
    const unknown=originalHeaders.flatMap((value,index)=>headers[index]?[]:[`第 ${index+1} 列「${value.slice(0,80)||'空表头'}」`]);
    if(unknown.length)throw new Error('无法识别表头：'+unknown.slice(0,5).join('、')+'。请核对列名；如果中文显示不正常，请切换 CSV 编码并重新读取文件。');
    if(new Set(headers).size!==headers.length)throw new Error('存在重复列名。');
    const missing=columns.filter(([key,_label,_aliases,optional])=>!optional&&!headers.includes(key));
    if(missing.length&&!Array.isArray(enabledFields))throw new Error('缺少列：'+missing.map(([,label])=>label).join('、'));
    const seen=new Set(), previous=new Set(history);
    return rows.map((cells,index)=>{
      const errors=[];
      if(cells.length!==headers.length)errors.push('列数与表头不一致');
      const data=Object.fromEntries(headers.map((key,column)=>[key,(cells[column]||'').trim()]));
      if(data.deliveryAddressType==='其他地址')data.deliveryAddressType='其它地址';
      for(const [key,label] of columns) {
        if((data[key]||'').length>1000)errors.push(label+'过长');
      }
      if(data.customsType&&!['买单','退税','买单+退税'].includes(data.customsType))errors.push('报关类型只能填写买单、退税或买单+退税');
      if(data.deliveryAddressType&&!['FBA地址','其它地址'].includes(data.deliveryAddressType))errors.push('派送地址类型只能填写FBA地址或其它地址');
      for(const key of ['customerOrderNo','referenceNo','shipmentId','referenceId']) if(/^[+-]?\d+(?:\.\d+)?e[+-]?\d+$/i.test(data[key]))errors.push('编号疑似科学计数法：'+key+'，请在 Excel 中设置为文本后重新导出');
      if(data.ctns&&(!/^[1-9]\d*$/.test(data.ctns)||!Number.isSafeInteger(Number(data.ctns))))errors.push('箱数必须为可表示的正整数');
      for(const key of ['weight','volume'])if(data[key]&&(!/^(?:\d+)(?:\.\d+)?$/.test(data[key])||!Number.isFinite(Number(data[key]))||Number(data[key])<=0))errors.push((key==='weight'?'毛重':'体积')+'必须为正数，单元格不要带单位');
      const identity=fingerprint(data);
      if([data.customerOrderNo,data.shipmentId,data.referenceId].every(Boolean)){
        if(seen.has(identity))errors.push('与本批前面的订单编号组合重复');seen.add(identity);
        if(previous.has(identity))errors.push('该编号组合曾由本人确认下单，请核对避免重复');
      }
      return {line:index+2,data,errors,status:errors.length?'invalid':'pending'};
    });
  }
  const api={parse,decode,columns,fingerprint,template:()=> '\uFEFF'+columns.map(([,label])=>label).join(',')+'\r\n'};
  globalThis.YouziOrderImport=api;
  if(typeof module!=='undefined')module.exports=api;
})();
