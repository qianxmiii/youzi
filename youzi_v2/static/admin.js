const views = {
  dashboard: document.getElementById("view-dashboard"),
  quote: document.getElementById("view-quote"),
  addresses: document.getElementById("view-addresses"),
  "product-import": document.getElementById("view-product-import"),
};
const menuItems = Array.from(document.querySelectorAll(".menu-item[data-view]"));

const quoteTbody = document.getElementById("quote-tbody");
const addrTbody = document.getElementById("addr-tbody");
const quoteCountEl = document.getElementById("metric-quote-count");
const addrCountEl = document.getElementById("metric-address-count");
const healthEl = document.getElementById("metric-health");

const btnRefresh = document.getElementById("btn-refresh");
const btnNew = document.getElementById("btn-new");
const btnClear = document.getElementById("btn-clear");
const addrBtnRefresh = document.getElementById("addr-btn-refresh");
const addrBtnNew = document.getElementById("addr-btn-new");

const dialog = document.getElementById("quote-dialog");
const form = document.getElementById("quote-form");
const formTitle = document.getElementById("dialog-title");
const customerInput = document.getElementById("form-customer");
const productNameInput = document.getElementById("form-product-name");
const countryInput = document.getElementById("form-country");
const addressInput = document.getElementById("form-address");
const channelInput = document.getElementById("form-channel");
const amountInput = document.getElementById("form-amount");
const noteInput = document.getElementById("form-note");
const quoteCancel = document.getElementById("quote-cancel");

const addrDialog = document.getElementById("address-dialog");
const addrForm = document.getElementById("address-form");
const addrDialogTitle = document.getElementById("addr-dialog-title");
const addrCancel = document.getElementById("addr-cancel");
const acCust = document.getElementById("addr-form-customer");
const acProd = document.getElementById("addr-form-product");
const acCtry = document.getElementById("addr-form-country");
const acAddr = document.getElementById("addr-form-address");
const acPost = document.getElementById("addr-form-postcode");
const acComp = document.getElementById("addr-form-company");
const acContact = document.getElementById("addr-form-contact");
const acPhone = document.getElementById("addr-form-phone");
const acComm = document.getElementById("addr-form-commercial");
const acRemote = document.getElementById("addr-form-remote");

let editingId = null;
let editingAddrId = null;

const piFile = document.getElementById("pi-file");
const piUploadBtn = document.getElementById("pi-upload");
const piDownload = document.getElementById("pi-download");
const piMsg = document.getElementById("pi-msg");

function escapeHtml(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/** 表格数字展示 */
function fmtNum(v, decimals) {
  if (v === null || v === undefined || v === "") return "";
  const n = Number(v);
  if (Number.isNaN(n)) return escapeHtml(String(v));
  return decimals === 0 ? String(Math.round(n)) : n.toFixed(decimals);
}

/** 与 index 报价历史一致的偏远/住宅/带电/DDU/USD 及提货/超尺寸/超重/MOQ badge */
function quoteAdminBadgeCell(item) {
  const status = [];
  if (item.isRemote) status.push('<span class="b b-dark">偏远</span>');
  if (item.hasResidential) status.push('<span class="b b-dark">住宅</span>');
  if (item.hasBattery) status.push('<span class="b b-green">带电</span>');
  if (item.isDDU) status.push('<span class="b b-blue">DDU</span>');
  if (item.isUSD) status.push('<span class="b b-amber">USD</span>');

  const fees = [];
  const pRmb = Number(item.pickupFeeRmb) || 0;
  const pUsd = Number(item.pickupFeeUsd) || 0;
  if (item.hasPickupFee && (pRmb > 0 || pUsd > 0)) {
    const bits = [];
    if (pRmb > 0) bits.push(`¥${pRmb}`);
    if (pUsd > 0) bits.push(`$${pUsd}`);
    fees.push(`<span class="b b-info">提货 ${bits.join(" / ")}</span>`);
  }
  if (item.isOversize && Number(item.oversizeFee) > 0) {
    fees.push(
      `<span class="b b-warn">超尺寸 ¥${item.oversizeFee}/箱</span>`
    );
  }
  if (item.isOverweight && Number(item.overweightFee) > 0) {
    fees.push(
      `<span class="b b-danger">超重 ¥${item.overweightFee}/箱</span>`
    );
  }
  if (item.isMOQ && Number(item.moqValue) > 0) {
    fees.push(`<span class="b b-muted">MOQ ${fmtNum(item.moqValue, 2)}</span>`);
  }

  const line1 = status.length ? status.join("") : '<span class="text-muted">—</span>';
  const line2 = fees.length ? fees.join("") : '<span class="text-muted">—</span>';
  return `<div class="badge-stack"><div class="badge-line">${line1}</div><div class="badge-line">${line2}</div></div>`;
}

function switchView(name) {
  Object.entries(views).forEach(([k, el]) => {
    el.classList.toggle("active", k === name);
  });
  menuItems.forEach((item) => item.classList.toggle("active", item.dataset.view === name));
}

menuItems.forEach((item) => {
  item.addEventListener("click", () => switchView(item.dataset.view));
});

async function checkHealth() {
  try {
    const res = await fetch("/api/health");
    const data = await res.json();
    healthEl.textContent = data.ok ? "正常" : "异常";
  } catch (e) {
    healthEl.textContent = "不可用";
  }
}

function quotePayload() {
  let cust = customerInput.value.trim();
  let pn = productNameInput.value.trim();
  if (!cust) cust = "00";
  if (!pn) pn = "00";
  return {
    customer: cust,
    productName: pn,
    country: countryInput.value.trim(),
    address: addressInput.value.trim(),
    channel: channelInput.value.trim(),
    amount: Number(amountInput.value || 0),
    note: noteInput.value.trim(),
    extra: {},
  };
}

function openCreateQuoteDialog() {
  editingId = null;
  formTitle.textContent = "新增报价";
  customerInput.value = "00";
  productNameInput.value = "00";
  countryInput.value = "";
  addressInput.value = "";
  channelInput.value = "";
  amountInput.value = "";
  noteInput.value = "";
  dialog.showModal();
}

function openEditQuoteDialog(item) {
  editingId = item.id;
  formTitle.textContent = "编辑报价";
  customerInput.value = item.customer != null && item.customer !== "" ? item.customer : "00";
  productNameInput.value =
    item.productName != null && item.productName !== "" ? item.productName : "00";
  countryInput.value = item.country || "";
  addressInput.value = item.address || "";
  channelInput.value = item.channel || "";
  amountInput.value = item.amount ?? 0;
  noteInput.value = item.note || item.notes || "";
  dialog.showModal();
}

async function saveQuoteDialog() {
  const payload = quotePayload();
  if (!payload.channel) {
    alert("渠道不能为空");
    return;
  }
  const url = editingId
    ? `/api/quote-history/${encodeURIComponent(editingId)}`
    : "/api/quote-history";
  const method = editingId ? "PUT" : "POST";
  const res = await fetch(url, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    alert(err.detail || "保存失败");
    return;
  }
  dialog.close();
  await loadQuotes();
}

async function deleteQuoteItem(id) {
  if (!confirm("确认删除该记录？")) return;
  await fetch(`/api/quote-history/${encodeURIComponent(id)}`, { method: "DELETE" });
  await loadQuotes();
}

async function clearAllQuotes() {
  if (!confirm("确认清空全部报价历史？")) return;
  await fetch("/api/quote-history", { method: "DELETE" });
  await loadQuotes();
}

const QUOTE_TABLE_COLS = 29;

async function loadQuotes() {
  const res = await fetch("/api/quote-history");
  const items = await res.json();
  quoteCountEl.textContent = String(items.length);

  if (!items.length) {
    quoteTbody.innerHTML = `<tr><td colspan="${QUOTE_TABLE_COLS}" class="empty">暂无数据</td></tr>`;
    return;
  }

  quoteTbody.innerHTML = "";
  items.forEach((item) => {
    const ch = item.channel || item.deliveryMethod || "";
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td class="cell-mono cell-id" title="${escapeHtml(item.id)}">${escapeHtml(item.id)}</td>
      <td>${escapeHtml(item.source)}</td>
      <td class="cell-time">${escapeHtml(item.created_at)}</td>
      <td class="cell-time">${escapeHtml(item.updated_at)}</td>
      <td class="cell-time">${escapeHtml(item.timestamp)}</td>
      <td>${escapeHtml(item.customer)}</td>
      <td>${escapeHtml(item.productName)}</td>
      <td>${escapeHtml(item.country)}</td>
      <td class="cell-mono">${escapeHtml(item.postcode)}</td>
      <td class="cell-mono">${escapeHtml(item.address)}</td>
      <td>${escapeHtml(item.origin)}</td>
      <td>${escapeHtml(ch)}</td>
      <td class="cell-num">${fmtNum(item.quantity, 2)}</td>
      <td class="cell-num">${fmtNum(item.weight, 3)}</td>
      <td class="cell-num">${fmtNum(item.volume, 4)}</td>
      <td class="cell-num">${fmtNum(item.costRmb, 2)}</td>
      <td class="cell-num">${fmtNum(item.profitRmb, 2)}</td>
      <td class="cell-num">${fmtNum(item.priceRmb, 2)}</td>
      <td class="cell-num">${fmtNum(item.priceUsd, 2)}</td>
      <td class="cell-num">${fmtNum(item.chargeWeight, 3)}</td>
      <td class="cell-num">${fmtNum(item.chargeCBM, 4)}</td>
      <td class="cell-num">${fmtNum(item.volumeRatio, 3)}</td>
      <td class="cell-num">${fmtNum(item.totalPriceUsd, 2)}</td>
      <td class="cell-num">${fmtNum(item.totalPriceRmb, 2)}</td>
      <td class="cell-num">${fmtNum(item.unitPriceRmb, 2)}</td>
      <td>${escapeHtml(item.quoteType)}</td>
      <td class="cell-note">${escapeHtml(item.notes != null ? item.notes : item.note)}</td>
      <td>${quoteAdminBadgeCell(item)}</td>
      <td>
        <button type="button" data-edit=${JSON.stringify(item.id)}>编辑</button>
        <button type="button" data-del=${JSON.stringify(item.id)} class="danger">删除</button>
      </td>
    `;
    quoteTbody.appendChild(tr);
  });

  quoteTbody.querySelectorAll("[data-edit]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = btn.getAttribute("data-edit");
      const found = items.find((x) => x.id === id);
      if (found) openEditQuoteDialog(found);
    });
  });
  quoteTbody.querySelectorAll("[data-del]").forEach((btn) => {
    btn.addEventListener("click", () => deleteQuoteItem(btn.getAttribute("data-del")));
  });
}

function addrPayload() {
  let c = acCust.value.trim();
  let p = acProd.value.trim();
  if (!c) c = "00";
  if (!p) p = "00";
  return {
    customer: c,
    productName: p,
    country: acCtry.value.trim(),
    address: acAddr.value.trim(),
    postalCode: acPost.value.trim(),
    company: acComp.value.trim(),
    contact: acContact.value.trim(),
    phone: acPhone.value.trim(),
    isCommercial: acComm.checked,
    isRemote: acRemote.checked,
  };
}

function openCreateAddrDialog() {
  editingAddrId = null;
  addrDialogTitle.textContent = "新增地址";
  acCust.value = "00";
  acProd.value = "00";
  acCtry.value = "";
  acAddr.value = "";
  acPost.value = "";
  acComp.value = "";
  acContact.value = "";
  acPhone.value = "";
  acComm.checked = true;
  acRemote.checked = false;
  addrDialog.showModal();
}

function openEditAddrDialog(row) {
  editingAddrId = row.id;
  addrDialogTitle.textContent = "编辑地址";
  acCust.value = row.customer != null && row.customer !== "" ? row.customer : "00";
  acProd.value = row.productName != null && row.productName !== "" ? row.productName : "00";
  acCtry.value = row.country || "";
  acAddr.value = row.address || "";
  acPost.value = row.postalCode || "";
  acComp.value = row.company || "";
  acContact.value = row.contact || "";
  acPhone.value = row.phone || "";
  acComm.checked = !!row.isCommercial;
  acRemote.checked = !!row.isRemote;
  addrDialog.showModal();
}

async function saveAddrDialog(e) {
  e.preventDefault();
  const payload = addrPayload();
  const url = editingAddrId
    ? `/api/addresses/${encodeURIComponent(editingAddrId)}`
    : "/api/addresses";
  const method = editingAddrId ? "PUT" : "POST";
  const res = await fetch(url, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    alert(err.detail || "保存失败");
    return;
  }
  addrDialog.close();
  await loadAddresses();
}

async function deleteAddrItem(id) {
  if (!confirm("确认删除该地址？")) return;
  await fetch(`/api/addresses/${encodeURIComponent(id)}`, { method: "DELETE" });
  await loadAddresses();
}

async function loadAddresses() {
  const res = await fetch("/api/addresses");
  const rows = await res.json();
  if (addrCountEl) addrCountEl.textContent = String(rows.length);

  if (!rows.length) {
    addrTbody.innerHTML = `<tr><td colspan="11" class="empty">暂无数据</td></tr>`;
    return;
  }

  addrTbody.innerHTML = "";
  rows.forEach((row) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${escapeHtml(row.customer)}</td>
      <td>${escapeHtml(row.productName)}</td>
      <td>${escapeHtml(row.country)}</td>
      <td class="cell-mono">${escapeHtml(row.address)}</td>
      <td>${escapeHtml(row.postalCode)}</td>
      <td>${escapeHtml(row.company)}</td>
      <td>${escapeHtml(row.contact)}</td>
      <td>${escapeHtml(row.phone)}</td>
      <td>${
        row.isCommercial
          ? '<span class="b b-blue">商业</span>'
          : '<span class="b b-green">住宅</span>'
      }</td>
      <td>${
        row.isRemote
          ? '<span class="b b-dark">偏远</span>'
          : '<span class="b b-green">非偏远</span>'
      }</td>
      <td>
        <button type="button" data-a-edit=${JSON.stringify(row.id)}>编辑</button>
        <button type="button" data-a-del=${JSON.stringify(row.id)} class="danger">删除</button>
      </td>
    `;
    addrTbody.appendChild(tr);
  });

  addrTbody.querySelectorAll("[data-a-edit]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = btn.getAttribute("data-a-edit");
      const row = rows.find((r) => r.id === id);
      if (row) openEditAddrDialog(row);
    });
  });
  addrTbody.querySelectorAll("[data-a-del]").forEach((btn) => {
    btn.addEventListener("click", () => deleteAddrItem(btn.getAttribute("data-a-del")));
  });
}

quoteCancel.addEventListener("click", () => dialog.close());
addrCancel.addEventListener("click", () => addrDialog.close());

btnNew.addEventListener("click", openCreateQuoteDialog);
btnRefresh.addEventListener("click", loadQuotes);
btnClear.addEventListener("click", clearAllQuotes);
form.addEventListener("submit", async (e) => {
  e.preventDefault();
  await saveQuoteDialog();
});

addrBtnNew.addEventListener("click", openCreateAddrDialog);
addrBtnRefresh.addEventListener("click", loadAddresses);
addrForm.addEventListener("submit", saveAddrDialog);

const chargeWCustomer = document.getElementById("charge-w-customer");
const chargeWActual = document.getElementById("charge-w-actual");
const chargeWRate = document.getElementById("charge-w-rate");

function updateChargeWeightDiff() {
  if (!chargeWRate) return;
  const cRaw = chargeWCustomer && chargeWCustomer.value != null ? chargeWCustomer.value.trim() : "";
  const aRaw = chargeWActual && chargeWActual.value != null ? chargeWActual.value.trim() : "";
  if (!cRaw || !aRaw) {
    chargeWRate.textContent = "—";
    chargeWRate.classList.remove("charge-diff-over");
    return;
  }
  const c = Number(cRaw);
  const a = Number(aRaw);
  if (!(c > 0) || Number.isNaN(c) || Number.isNaN(a)) {
    chargeWRate.textContent = "—";
    chargeWRate.classList.remove("charge-diff-over");
    return;
  }
  const signedPct = ((a - c) / c) * 100;
  const sign = signedPct > 0 ? "+" : "";
  chargeWRate.textContent = `${sign}${signedPct.toFixed(2)}%`;
  chargeWRate.classList.toggle("charge-diff-over", Math.abs(signedPct) > 3);
}

if (chargeWCustomer && chargeWActual) {
  chargeWCustomer.addEventListener("input", updateChargeWeightDiff);
  chargeWActual.addEventListener("input", updateChargeWeightDiff);
}

switchView("dashboard");
checkHealth();
loadQuotes();
loadAddresses();

function resetProductImportDownload() {
  piDownload.classList.add("disabled");
  piDownload.href = "#";
}

async function uploadAndConvertProductImport() {
  const file = piFile.files && piFile.files[0];
  if (!file) {
    piMsg.textContent = "请先选择箱单文件。";
    return;
  }

  const formData = new FormData();
  formData.append("invoice", file);
  piUploadBtn.disabled = true;
  piMsg.textContent = "上传并转换中...";
  resetProductImportDownload();
  try {
    const res = await fetch("/api/product-import", { method: "POST", body: formData });
    const data = await res.json();
    if (!res.ok) {
      piMsg.textContent = data.detail || "转换失败，请检查文件格式。";
      return;
    }
    piDownload.href = `/api/product-import/download/${encodeURIComponent(data.id)}`;
    piDownload.classList.remove("disabled");
    piMsg.textContent = "转换完成，请点击下载。";
  } catch (_e) {
    piMsg.textContent = "请求失败，请确认服务正常。";
  } finally {
    piUploadBtn.disabled = false;
  }
}

piUploadBtn.addEventListener("click", uploadAndConvertProductImport);
