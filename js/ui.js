// 提货费输入控制
function togglePickupFeeInput() {
    const pickupFeeCheckbox = document.getElementById("pickup-fee-checkbox");
    const pickupFeeInputContainer = document.getElementById("pickup-fee-input-container");

    // 根据 checkbox 的状态显示或隐藏提货费输入框
    if (pickupFeeCheckbox.checked) {
        pickupFeeInputContainer.style.display = "block";
    } else {
        pickupFeeInputContainer.style.display = "none";
        document.getElementById("pickup-fee").value = ""; // 清空提货费输入框
    }

    // 触发更新
    updateQuote();
}

// 根据国家显示不同派送方式
function updateDeliveryMethods() {
    // 获取选择的国家
    const countrySelect = document.getElementById("country-select");
    const selectedCountry = countrySelect.value;

    // 获取派送方式下拉菜单
    const deliveryMethodSelect = document.getElementById("delivery-method-select");

    // 清空当前选项
    deliveryMethodSelect.innerHTML = "";

    // 获取当前国家对应的派送方式
    const deliveryMethods = deliveryMethodsByCountry[selectedCountry] || [];

    // 添加新的选项
    deliveryMethods.forEach(method => {
        const option = document.createElement("option");
        option.value = method;
        option.textContent = method;
        deliveryMethodSelect.appendChild(option);
    });

    // 更新报价
    updateQuote();
}

// 添加新的一行
function addRow() {
    let table = document.getElementById('box-table');
    let newRow = document.createElement('tr');
    newRow.classList.add('input-row');
    newRow.innerHTML = `
        <td><input type="number" class="form-control length" placeholder="长 (cm)" oninput="calculate()"></td>
        <td><input type="number" class="form-control width" placeholder="宽 (cm)" oninput="calculate()"></td>
        <td><input type="number" class="form-control height" placeholder="高 (cm)" oninput="calculate()"></td>
        <td><input type="number" class="form-control weight" placeholder="单箱实重 (kg)" oninput="calculate()"></td>
        <td><input type="number" class="form-control quantity" placeholder="箱数" oninput="calculate()"></td>
        <td class="result-cell">0.00 m³</td>
        <td class="result-cell">0 kg</td> <!-- 新增列 -->
        <td class="result-cell">0 kg</td>
        <td class="result-cell">0 kg</td>
        <td class="result-cell">0 cm</td>
        <td>
            <button class="btn btn-success btn-sm" onclick="addRow()">+</button>
            <button class="btn btn-danger btn-sm" onclick="deleteRow(event)">-</button>
        </td>
    `;
    table.appendChild(newRow);
}

// 删除当前行
function deleteRow(event) {
    let rows = document.querySelectorAll('.input-row');

    // 如果只有一行，弹出提示并阻止删除
    if (rows.length <= 1) {
        alert("无法删除最后一行！");
        return; // 不进行删除
    }

    let row = event.target.closest('tr'); // 获取到当前行
    row.remove(); // 删除当前行
    calculate(); // 重新计算总计
}

// 更新邮编
function updatePostcode() {
    const addressInput = document.getElementById("address").value.trim().toUpperCase();
    const postcodeInput = document.getElementById("postcode");

    // 如果地址长度为 4 位，从 JSON 中获取邮编
    if (addressInput.length === 4) {
        const postcode = addressToPostcode[addressInput];
        if (postcode) {
            postcodeInput.value = postcode;
        } else {
            postcodeInput.value = ""; // 如果未找到对应邮编，清空邮编输入框
        }
    } else {
        postcodeInput.value = ""; // 如果地址长度不为 4 位，清空邮编输入框
    }
    // 检查邮编是否为偏远地区
    checkRemoteAddress();
    // 触发更新
    updateQuote();
}



// 检查邮编是否为偏远地区
function checkRemoteAddress() {
    const postcodeInput = document.getElementById("postcode").value.trim();
    const remoteAddressCheckbox = document.getElementById("remote-address");

    // 如果邮编在偏远地区列表中，选中 checkbox
    if (remotePostcodes.includes(postcodeInput)) {
        remoteAddressCheckbox.checked = true;
    } else {
        remoteAddressCheckbox.checked = false;
    }

    // 触发更新
    updateQuote();
}

// 动态生成分类按钮
function renderCategoryButtons() {
    const categoryButtonsContainer = document.getElementById('categoryButtons');
    if (!categoryButtonsContainer) return;

    // 清空现有按钮
    categoryButtonsContainer.innerHTML = '';

    // 添加“全部”按钮
    const allButton = document.createElement('button');
    allButton.className = 'btn btn-outline-primary';
    allButton.textContent = '全部';
    allButton.onclick = () => filterTerms('全部', allButton);
    allButton.id = 'termTotal';
    categoryButtonsContainer.appendChild(allButton);

    // 从 data.js 中获取分类并生成按钮
    const categories = Object.keys(termsByCategory);
    categories.forEach(category => {
        const button = document.createElement('button');
        button.className = 'btn btn-outline-primary';
        button.textContent = category;
        button.onclick = () => filterTerms(category, button);
        categoryButtonsContainer.appendChild(button);
    });
}

// 突出显示对应的单元格
function highlightPriceCell(area, region, weightIndex) {
    // 清除所有表格中之前突出显示的样式
    clearHighlightedCells();

    // 获取当前区域的表格
    const tableId = region === "华南" ? "southChinaPriceTable" : "eastChinaPriceTable";
    const priceTableElement = document.getElementById(tableId).getElementsByTagName("tbody")[0];
    const rows = priceTableElement.getElementsByTagName("tr");

    // 遍历表格，找到对应的区域和价格
    for (let i = 0; i < rows.length; i++) {
        const areaCell = rows[i].getElementsByTagName("td")[0];
        if (areaCell.textContent === area) {
            const priceCell = rows[i].getElementsByTagName("td")[weightIndex + 1]; // 第一列是区域
            priceCell.innerHTML = `<span class="highlight">${priceCell.textContent}</span>`;
            break;
        }
    }
}

// 清除所有表格中之前突出显示的样式
function clearHighlightedCells() {
    const tables = ["southChinaPriceTable", "eastChinaPriceTable"];

    tables.forEach(tableId => {
        const priceTableElement = document.getElementById(tableId).getElementsByTagName("tbody")[0];
        const rows = priceTableElement.getElementsByTagName("tr");

        // 遍历所有行和单元格，清除突出显示样式
        for (let i = 0; i < rows.length; i++) {
            const cells = rows[i].getElementsByTagName("td");
            for (let j = 1; j < cells.length; j++) { // 跳过第一列（区域列）
                if (cells[j].querySelector(".highlight")) {
                    cells[j].innerHTML = cells[j].textContent; // 移除 <span class="highlight">
                }
            }
        }
    });
}

// 显示指定的 Tab
function showTab(tabId) {

    const channel = document.getElementById('delivery-method-select').value;
    if (channel.includes("express")) { //快递派才切换
        // 隐藏所有 Tab
        const tabPanes = document.querySelectorAll(".tab-pane");
        tabPanes.forEach(tabPane => {
            tabPane.classList.remove("show", "active");
        });

        // 移除所有 Tab 导航按钮的激活状态
        const tabButtons = document.querySelectorAll(".nav-link");
        tabButtons.forEach(tabButton => {
            tabButton.classList.remove("active");
        });

        // 显示选中的 Tab
        const selectedTabPane = document.getElementById(tabId);
        if (selectedTabPane) {
            selectedTabPane.classList.add("show", "active");
        }

        // 激活对应的 Tab 导航按钮
        const selectedTabButton = document.querySelector(`[data-bs-target="#${tabId}"]`);
        if (selectedTabButton) {
            selectedTabButton.classList.add("active");
        }
    }
}

function toggleMOQInput() {
    const moqCheckbox = document.getElementById("MOQ");
    const moqInputContainer = document.getElementById("moq-input-container");

    // 根据复选框状态显示或隐藏输入框
    if (moqCheckbox.checked) {
        moqInputContainer.style.display = "block"; // 显示输入框
    } else {
        moqInputContainer.style.display = "none"; // 隐藏输入框
    }

    // 触发报价更新
    updateQuote();
}

/* 复制快捷回复 */
function copyQuickReply(textareaId, btn) {
    let textArea = document.getElementById(textareaId);
    textArea.select();
    document.execCommand("copy");

    // 按钮变色 & 显示“已复制”文字
    btn.textContent = "✅ 已复制";
    btn.classList.add("btn-success");

    // 1.5秒后恢复
    setTimeout(() => {
        btn.textContent = textareaId === "chinese-message" ? "复制" : "Copy";
        btn.classList.remove("btn-success");
    }, 1500);
}