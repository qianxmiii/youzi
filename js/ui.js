/**
 * ui.js UI相关功能
 */

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
    
    // 更新分泡比例显示
    if (typeof toggleVolumeRatioVisibility === 'function') {
        toggleVolumeRatioVisibility();
    }
    
    // 更新特别提示
    updateQuoteTips();
}

/**
 * 根据选择的运输方式和国家更新特别提示（Badge样式）
 */
function updateQuoteTips() {
    // 获取选择的运输方式
    const deliveryMethodSelect = document.getElementById("delivery-method-select");
    const selectedDeliveryMethod = deliveryMethodSelect ? deliveryMethodSelect.value : "";
    
    // 获取选择的国家
    const countrySelect = document.getElementById("country-select");
    const selectedCountry = countrySelect ? countrySelect.value : "";
    
    // 获取统一容器
    const tipsContainer = document.getElementById("quote-tips-container");
    
    if (!tipsContainer) return;
    
    // 清空容器
    tipsContainer.innerHTML = "";
    
    // 从独立配置中获取提示信息
    let deliveryTipsArray = [];
    let countryTipsArray = [];
    
    if (typeof window.logisticsData !== 'undefined' && window.logisticsData.quoteTipsConfig) {
        const config = window.logisticsData.quoteTipsConfig;
        
        // 获取运输方式提示
        if (config.deliveryMethod && config.deliveryMethod[selectedDeliveryMethod]) {
            deliveryTipsArray = config.deliveryMethod[selectedDeliveryMethod];
        }
        
        // 获取国家提示
        if (config.country && config.country[selectedCountry]) {
            countryTipsArray = config.country[selectedCountry];
        }
    }
    
    // 统一颜色：运输方式用蓝色，国家用绿色
    const deliveryColor = '#005be2';
    const countryColor = '#00c16e'; 
    const originColor = '#2164f4'; 
    
    // 先渲染运输方式提示（蓝色）
    deliveryTipsArray.forEach((tip, index) => {
        createTipBadge(tip, tipsContainer, 'delivery', deliveryColor, index);
    });
    
    // 再渲染国家提示（绿色）
    countryTipsArray.forEach((tip, index) => {
        createTipBadge(tip, tipsContainer, 'country', countryColor, deliveryTipsArray.length + index);
    });
    
    // 显示或隐藏容器
    if (deliveryTipsArray.length > 0 || countryTipsArray.length > 0) {
        tipsContainer.style.display = "flex";
        
        // 初始化Bootstrap tooltips
        setTimeout(() => {
            // 销毁旧的tooltip实例
            const existingTooltips = tipsContainer.querySelectorAll('[data-bs-toggle="tooltip"]');
            existingTooltips.forEach(el => {
                if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
                    const tooltipInstance = bootstrap.Tooltip.getInstance(el);
                    if (tooltipInstance) {
                        tooltipInstance.dispose();
                    }
                }
            });
            
            // 初始化新的tooltip
            const tooltipTriggerList = tipsContainer.querySelectorAll('[data-bs-toggle="tooltip"]');
            tooltipTriggerList.forEach(tooltipTriggerEl => {
                if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
                    new bootstrap.Tooltip(tooltipTriggerEl, {
                        placement: 'top',
                        html: true,
                        trigger: 'hover focus'
                    });
                }
            });
        }, 100);
    } else {
        tipsContainer.style.display = "none";
    }
}

/**
 * 创建提示Badge
 * @param {Object} tip - 提示对象
 * @param {HTMLElement} container - 容器元素
 * @param {string} type - 类型（'delivery' 或 'country'）
 * @param {string} textColor - 文字颜色
 * @param {number} index - 索引
 */
function createTipBadge(tip, container, type, textColor, index) {
    const badge = document.createElement('span');
    badge.className = `badge quote-tip-badge quote-tip-${type}`;
    
    // 使用简洁样式：白底，统一颜色文字
    badge.style.cssText = `
        cursor: help; 
        font-size: 0.9rem; 
        font-weight: 600;
        padding: 0.35rem 0.7rem; 
        margin: 0.25rem 0.35rem 0.25rem 0; 
        transition: all 0.15s ease;
        border-radius: 0.2rem;
        background-color: #ffffff;
        color: ${textColor};
        border: 1px solid #dee2e6;
        box-shadow: none;
        display: inline-flex;
        align-items: center;
        white-space: nowrap;
        line-height: 1.4;
    `;
    badge.setAttribute('data-bs-toggle', 'tooltip');
    badge.setAttribute('data-bs-placement', 'top');
    badge.setAttribute('data-bs-html', 'true');
    badge.setAttribute('title', tip.quoteTipDetail || '');
    badge.textContent = `#${tip.quoteTip}`;
    
    // 添加悬停效果
    badge.addEventListener('mouseenter', function() {
        this.style.backgroundColor = '#f8f9fa';
        this.style.borderColor = textColor;
    });
    badge.addEventListener('mouseleave', function() {
        this.style.backgroundColor = '#ffffff';
        this.style.borderColor = '#dee2e6';
    });
    
    // 添加唯一ID用于初始化tooltip
    badge.id = `quote-tip-${type}-${index}`;
    
    container.appendChild(badge);
}

// 添加新的一行
function addRow() {
    let table = document.getElementById('box-table');
    let newRow = document.createElement('tr');
    newRow.classList.add('input-row');

    // 获取当前行数，用于生成编号
    let rowCount = table.getElementsByClassName('input-row').length + 1;

    newRow.innerHTML = `
        <td class="index-cell">${rowCount}</td> <!-- 编号单元格 -->
        <td><input type="number" class="form-control length" oninput="calculate()"></td>
        <td><input type="number" class="form-control width" oninput="calculate()"></td>
        <td><input type="number" class="form-control height" oninput="calculate()"></td>
        <td><input type="number" class="form-control weight" oninput="calculate()"></td>
        <td><input type="number" class="form-control quantity" oninput="calculate()"></td>
        <td class="result-cell">0.00 cbm</td>
        <td class="result-cell">0 kg</td> <!-- 新增列 -->
        <td class="result-cell">0 kg</td>
        <td class="result-cell">0 kg</td>
        <td class="result-cell">0 cm</td>
        <td>
            <button class="btn btn-success btn-sm" onclick="addRow()">+</button>
            <button class="btn btn-danger btn-sm" onclick="deleteRow(event)">-</button>
            <button class="btn btn-info btn-sm" onclick="copyRow(event)" title="复制当前行">📋</button>
        </td>
    `;
    table.appendChild(newRow);
}

// 删除当前行
function deleteRow(event) {
    let rows = document.querySelectorAll('.input-row');

    // 如果只有一行，弹出提示并阻止删除
    if (rows.length <= 1) {
        showToast('无法删除最后一行！', 'error');
        return; // 不进行删除
    }

    let row = event.target.closest('tr'); // 获取到当前行
    row.remove(); // 删除当前行
    
    // 重新编号
    let table = document.getElementById('box-table');
    let indexCells = table.getElementsByClassName('index-cell');
    for (let i = 0; i < indexCells.length; i++) {
        indexCells[i].textContent = i + 1; // 更新编号
    }

    calculate(); // 重新计算总计
}

// 复制当前行数据并新增一行
function copyRow(event) {
    let row = event.target.closest('tr'); // 获取当前行
    
    // 获取行中的数据
    const length = row.querySelector('.length')?.value || '';
    const width = row.querySelector('.width')?.value || '';
    const height = row.querySelector('.height')?.value || '';
    const weight = row.querySelector('.weight')?.value || '';
    const quantity = row.querySelector('.quantity')?.value || '';
    
    // 如果没有数据，提示用户
    if (!length && !width && !height && !weight && !quantity) {
        showToast('当前行没有数据可复制', 'warning');
        return;
    }
    
    // 创建新行
    let table = document.getElementById('box-table');
    let newRow = document.createElement('tr');
    newRow.classList.add('input-row');
    
    // 获取当前行数，用于生成编号
    let rowCount = table.getElementsByClassName('input-row').length + 1;
    
    // 创建新行的HTML，并填充当前行的数据
    newRow.innerHTML = `
        <td class="index-cell">${rowCount}</td>
        <td><input type="number" class="form-control length" oninput="calculate()" value="${length}"></td>
        <td><input type="number" class="form-control width" oninput="calculate()" value="${width}"></td>
        <td><input type="number" class="form-control height" oninput="calculate()" value="${height}"></td>
        <td><input type="number" class="form-control weight" oninput="calculate()" value="${weight}"></td>
        <td><input type="number" class="form-control quantity" oninput="calculate()" value="${quantity}"></td>
        <td class="result-cell">0.00 cbm</td>
        <td class="result-cell">0 kg</td>
        <td class="result-cell">0 kg</td>
        <td class="result-cell">0 kg</td>
        <td class="result-cell">0 cm</td>
        <td>
            <button class="btn btn-success btn-sm" onclick="addRow()">+</button>
            <button class="btn btn-danger btn-sm" onclick="deleteRow(event)">-</button>
            <button class="btn btn-info btn-sm" onclick="copyRow(event)" title="复制当前行">📋</button>
        </td>
    `;
    
    // 将新行添加到表格中
    table.appendChild(newRow);
    
    // 重新计算
    calculate();
    
    // 提示用户
    showToast('已复制当前行并新增一行', 'success');
}

// 更新邮编
function updatePostcode() {
    const addressInput = document.getElementById("address").value.trim().toUpperCase();
    const postcodeInput = document.getElementById("postcode");
    const countrySelect = document.getElementById("country-select");

    // 记录当前国家，用于检测是否发生变化
    const currentCountry = countrySelect.value;

    // 1. 遍历所有国家查找匹配
    let matchedCountry = "美国"; // 默认国家
    let matchedPostcode = "";

    for (const [country, postalMap] of Object.entries(addressByCountry)) {
        if (postalMap[addressInput]) {
            matchedCountry = country;
            matchedPostcode = postalMap[addressInput];
            break; // 找到后立即退出循环
        }
    }
    
    // 2. 更新界面
    countrySelect.value = matchedCountry;
    postcodeInput.value = matchedPostcode || addressInput; // 无匹配时直接显示输入的地址

    // 3. 只有国家发生变化时才更新运输方式
    if (currentCountry !== matchedCountry) {
        updateDeliveryMethods();
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
    if (window.remotePostcodes && window.remotePostcodes.includes(postcodeInput)) {
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

    // 添加"全部"按钮
    const allButton = document.createElement('button');
    allButton.className = 'btn btn-outline-primary active';
    allButton.textContent = '全部';
    allButton.setAttribute('data-category', '全部');
    allButton.onclick = () => filterTerms('全部', allButton);
    allButton.id = 'termTotal';
    categoryButtonsContainer.appendChild(allButton);

    // 从 data.js 中获取分类并生成按钮
    const categories = Object.keys(window.logisticsData.termsByCategory);
    categories.forEach(category => {
        const button = document.createElement('button');
        button.className = 'btn btn-outline-primary';
        button.textContent = category;
        button.setAttribute('data-category', category);
        button.onclick = () => filterTerms(category, button);
        categoryButtonsContainer.appendChild(button);
    });
    
    // 初始化回到顶部按钮
    if (typeof initBackToTopButton === 'function') {
        initBackToTopButton();
    }
}



// 初始化术语模态框
function initTermModal() {    
    // 初始化常用术语
    renderCategoryButtons();
    filterTerms('全部');
    
    // 初始化标签按钮
    renderTagButtons();
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
        // 只隐藏第二个模块的 Tab 内容，不影响第一个模块
        const secondModuleTabPanes = document.querySelectorAll("#myTabContent .tab-pane");
        secondModuleTabPanes.forEach(tabPane => {
            tabPane.classList.remove("show", "active");
        });

        // 只移除第二个模块的 Tab 导航按钮的激活状态
        const secondModuleTabButtons = document.querySelectorAll("#myTab .nav-link");
        secondModuleTabButtons.forEach(tabButton => {
            tabButton.classList.remove("active");
        });

        // 显示快递派查价 Tab
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

// 监听运输方式变化，当切换回非快递派时返回到单地址报价页面，并将下方 Tab 切回「快速查询」
function handleDeliveryMethodChange() {
    const channel = document.getElementById('delivery-method-select').value;
    
    if (!channel.includes("express")) {
        // 第一个模块：返回到单地址报价（#single-quote 在 #quoteTabsContent 内，不在 #myTabContent）
        const singleQuoteTab = document.getElementById('single-quote');
        if (singleQuoteTab) {
            document.querySelectorAll("#quoteTabsContent .tab-pane").forEach((pane) => {
                pane.classList.remove("show", "active");
            });
            document.querySelectorAll("#quoteTabs .nav-link").forEach((btn) => {
                btn.classList.remove("active");
            });
            singleQuoteTab.classList.add("show", "active");
        }
        const singleQuoteTabButton = document.querySelector('[data-bs-target="#single-quote"]');
        if (singleQuoteTabButton) {
            singleQuoteTabButton.classList.add("active");
        }

        // 第二个模块（#myTab）：清空后切到「快速查询」commonTab（之前误把 active 加在 single-quote 上，下方 Tab 区会空白）
        const secondModuleTabPanes = document.querySelectorAll("#myTabContent .tab-pane");
        secondModuleTabPanes.forEach(tabPane => {
            tabPane.classList.remove("show", "active");
        });
        const secondModuleTabButtons = document.querySelectorAll("#myTab .nav-link");
        secondModuleTabButtons.forEach(tabButton => {
            tabButton.classList.remove("active");
        });
        const commonTabPane = document.getElementById("commonTab");
        if (commonTabPane) {
            commonTabPane.classList.add("show", "active");
        }
        const commonTabButton = document.querySelector('[data-bs-target="#commonTab"]');
        if (commonTabButton) {
            commonTabButton.classList.add("active");
        }
    }
}

// MOQ输入控制
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

function toggleMOQBoxInput() {
    const moqBoxCheckbox = document.getElementById("moq-box-checkbox");
    const moqBoxInputContainer = document.getElementById("moq-box-input-container");

    // 根据复选框状态显示或隐藏输入框
    if (moqBoxCheckbox.checked) {
        moqBoxInputContainer.style.display = "block"; // 显示输入框
    } else {
        moqBoxInputContainer.style.display = "none"; // 隐藏输入框
    }
    updateQuote();
}

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

// 超尺寸输入控制
function toggleOverSizeFeeInput() {
    const overSizeFeeCheckbox = document.getElementById("oversize_check");
    const overSizeFeeInputContainer = document.getElementById("oversize-input-container");
    const quantity = document.getElementById("quantity").value;
    const oversize_quantity = document.getElementById("oversize-quantity");

    // 根据 checkbox 的状态显示或隐藏超尺寸输入框
    if (overSizeFeeCheckbox.checked) {
        overSizeFeeInputContainer.style.display = "block";
        oversize_quantity.value = quantity;
    } else {
        overSizeFeeInputContainer.style.display = "none";
    }

    // 触发更新
    updateQuote();
}


// 超重输入控制
function toggleOverWeightFeeInput() {
    const overWeightFeeCheckbox = document.getElementById("overweight_check");
    const overWeightFeeInputContainer = document.getElementById("overweight-input-container");
    const quantity = document.getElementById("quantity").value;
    const overweight_quantity = document.getElementById("overweight-quantity");

    // 根据 checkbox 的状态显示或隐藏超尺寸输入框
    if (overWeightFeeCheckbox.checked) {
        overWeightFeeInputContainer.style.display = "block";
        overweight_quantity.value = quantity;
    } else {
        overWeightFeeInputContainer.style.display = "none";
    }

    // 触发更新
    updateQuote();
}

// 显示特定地址的运输天数信息
function showSpecificAddressTransitTime(address) {
    // 移除之前的提示信息
    removeTransitTimeTooltip();
    
    if (!address || typeof specificAddressTransitTime === 'undefined' || !specificAddressTransitTime[address]) {
        return;
    }

    const addressConfig = specificAddressTransitTime[address];
    const addressInput = document.getElementById("address");
    
    // 创建提示信息
    let tooltipContent = `<div class="transit-time-tooltip">
        <strong>${address} 运输天数配置:</strong><br>`;
    
    for (const [channel, days] of Object.entries(addressConfig)) {
        tooltipContent += `${channel}: ${days} 天<br>`;
    }
    tooltipContent += '</div>';
    
    // 添加提示样式
    addressInput.classList.add('specific-address');
    
    // 创建或更新tooltip
    let tooltipInstance = bootstrap.Tooltip.getInstance(addressInput);
    if (!tooltipInstance) {
        tooltipInstance = new bootstrap.Tooltip(addressInput, {
            html: true,
            placement: 'top',
            trigger: 'hover',
            title: tooltipContent
        });
    } else {
        tooltipInstance.setContent({ '.tooltip-inner': tooltipContent });
    }
}

// 移除运输天数提示
function removeTransitTimeTooltip() {
    const addressInput = document.getElementById("address");
    addressInput.classList.remove('specific-address');
    
    const tooltipInstance = bootstrap.Tooltip.getInstance(addressInput);
    if (tooltipInstance) {
        tooltipInstance.dispose();
    }
}

// 检查特定地址并显示运输天数信息
function checkSpecificAddress() {
    const addressInput = document.getElementById("address").value.trim().toUpperCase();
    showSpecificAddressTransitTime(addressInput);
}

// ==================== 特别说明标签功能 ====================

/**
 * 初始化特别说明标签（从 data_logistics.js 中读取配置）
 */
function initSpecialNoteTags() {
    const container = document.getElementById('special-note-tags-container');
    if (!container || typeof specialNotes === 'undefined') return;
    
    // 清空容器
    container.innerHTML = '';
    
    // 根据配置生成按钮
    specialNotes.forEach(item => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'btn btn-sm btn-outline-secondary note-tag';
        btn.setAttribute('data-note-id', item.id);
        btn.setAttribute('data-note-cn', item.note.cn);
        btn.setAttribute('data-note-en', item.note.en);
        btn.onclick = function() { toggleNoteTag(this); };
        btn.innerHTML = `${item.icon} ${item.label}`; // 显示中文标签
        container.appendChild(btn);
    });
    
    // 添加清除按钮
    const clearBtn = document.createElement('button');
    clearBtn.type = 'button';
    clearBtn.className = 'btn btn-sm btn-outline-danger clear-note-btn';
    clearBtn.onclick = function() { clearAllNoteTags(); updateQuote(); };
    clearBtn.innerHTML = '✕ 清除';
    clearBtn.title = '清除所有选择';
    container.appendChild(clearBtn);
}

/**
 * 切换特别说明标签的选中状态
 * @param {HTMLElement} btn - 被点击的按钮元素
 */
function toggleNoteTag(btn) {
    btn.classList.toggle('btn-outline-secondary');
    btn.classList.toggle('btn-primary');
    btn.classList.toggle('active');
    
    // 更新报价文本
    updateQuote();
}

/**
 * 获取所有选中的特别说明
 * @param {string} lang - 语言选项 'cn' 或 'en'，默认 'en'
 * @returns {string[]} 选中的说明数组
 */
function getSelectedNotes(lang = 'en') {
    const selectedNotes = [];
    const noteTags = document.querySelectorAll('.note-tag.active');
    
    noteTags.forEach(tag => {
        const note = lang === 'cn' 
            ? tag.getAttribute('data-note-cn') 
            : tag.getAttribute('data-note-en');
        if (note) {
            selectedNotes.push(note);
        }
    });
    
    return selectedNotes;
}

/**
 * 清除所有特别说明的选中状态
 */
function clearAllNoteTags() {
    const noteTags = document.querySelectorAll('.note-tag');
    noteTags.forEach(tag => {
        tag.classList.remove('btn-primary', 'active');
        tag.classList.add('btn-outline-secondary');
    });
}

// 页面加载时初始化特别说明标签
document.addEventListener('DOMContentLoaded', function() {
    initSpecialNoteTags();
    // 初始化特别提示（延迟执行，确保数据已加载）
    setTimeout(() => {
        if (typeof updateQuoteTips === 'function') {
            updateQuoteTips();
        }
    }, 500);
});