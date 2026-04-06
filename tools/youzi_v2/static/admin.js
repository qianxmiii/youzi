const views = {
  dashboard: document.getElementById("view-dashboard"),
  quote: document.getElementById("view-quote"),
  "product-import": document.getElementById("view-product-import"),
};
const menuItems = Array.from(document.querySelectorAll(".menu-item[data-view]"));

const quoteTbody = document.getElementById("quote-tbody");
const quoteCountEl = document.getElementById("metric-quote-count");
const healthEl = document.getElementById("metric-health");

const btnRefresh = document.getElementById("btn-refresh");
const btnNew = document.getElementById("btn-new");
const btnClear = document.getElementById("btn-clear");

const dialog = document.getElementById("quote-dialog");
const form = document.getElementById("quote-form");
const formTitle = document.getElementById("dialog-title");
const customerInput = document.getElementById("form-customer");
const channelInput = document.getElementById("form-channel");
const amountInput = document.getElementById("form-amount");
const noteInput = document.getElementById("form-note");

let editingId = null;

const piFile = document.getElementById("pi-file");
const piUploadBtn = document.getElementById("pi-upload");
const piDownload = document.getElementById("pi-download");
const piMsg = document.getElementById("pi-msg");

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

function formPayload() {
  return {
    customer: customerInput.value.trim(),
    channel: channelInput.value.trim(),
    amount: Number(amountInput.value || 0),
    note: noteInput.value.trim(),
    extra: {},
  };
}

function openCreateDialog() {
  editingId = null;
  formTitle.textContent = "新增报价";
  customerInput.value = "";
  channelInput.value = "";
  amountInput.value = "";
  noteInput.value = "";
  dialog.showModal();
}

function openEditDialog(item) {
  editingId = item.id;
  formTitle.textContent = "编辑报价";
  customerInput.value = item.customer || "";
  channelInput.value = item.channel || "";
  amountInput.value = item.amount ?? 0;
  noteInput.value = item.note || "";
  dialog.showModal();
}

async function saveDialog() {
  const payload = formPayload();
  if (!payload.customer || !payload.channel) {
    alert("客户和渠道不能为空");
    return;
  }
  const url = editingId ? `/api/quote-history/${encodeURIComponent(editingId)}` : "/api/quote-history";
  const method = editingId ? "PUT" : "POST";
  await fetch(url, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  dialog.close();
  await loadQuotes();
}

async function deleteItem(id) {
  if (!confirm("确认删除该记录？")) return;
  await fetch(`/api/quote-history/${encodeURIComponent(id)}`, { method: "DELETE" });
  await loadQuotes();
}

async function clearAll() {
  if (!confirm("确认清空全部报价历史？")) return;
  await fetch("/api/quote-history", { method: "DELETE" });
  await loadQuotes();
}

async function loadQuotes() {
  const res = await fetch("/api/quote-history");
  const items = await res.json();
  quoteCountEl.textContent = String(items.length);

  if (!items.length) {
    quoteTbody.innerHTML = `<tr><td colspan="6" class="empty">暂无数据</td></tr>`;
    return;
  }

  quoteTbody.innerHTML = "";
  items.forEach((item) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${item.customer || ""}</td>
      <td>${item.channel || ""}</td>
      <td>${Number(item.amount || 0).toFixed(2)}</td>
      <td>${item.note || ""}</td>
      <td>${item.updated_at || ""}</td>
      <td>
        <button data-edit="${item.id}">编辑</button>
        <button data-del="${item.id}" class="danger">删除</button>
      </td>
    `;
    quoteTbody.appendChild(tr);
  });

  quoteTbody.querySelectorAll("[data-edit]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = btn.getAttribute("data-edit");
      const item = items.find((x) => x.id === id);
      if (item) openEditDialog(item);
    });
  });
  quoteTbody.querySelectorAll("[data-del]").forEach((btn) => {
    btn.addEventListener("click", () => deleteItem(btn.getAttribute("data-del")));
  });
}

btnNew.addEventListener("click", openCreateDialog);
btnRefresh.addEventListener("click", loadQuotes);
btnClear.addEventListener("click", clearAll);
form.addEventListener("submit", async (e) => {
  e.preventDefault();
  await saveDialog();
});

switchView("dashboard");
checkHealth();
loadQuotes();

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
