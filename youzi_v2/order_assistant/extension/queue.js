(() => {
  'use strict';
  function advance(queue, confirmedByUser) {
    const row=queue?.rows[queue.index];
    if(!row || row.status!=='review' || !confirmedByUser) throw new Error('请先填写、核对并在 DPS 下单成功，再勾选确认。');
    const rows=queue.rows.map((item,index)=>index===queue.index?{...item,status:'confirmed'}:{...item});
    let index=queue.index+1;
    while(rows[index]?.status==='confirmed')index++;
    return {...queue,rows,index};
  }
  const api={advance}; globalThis.YouziOrderQueue=api;
  if(typeof module!=='undefined')module.exports=api;
})();
