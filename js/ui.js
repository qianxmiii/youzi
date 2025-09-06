
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
    
    // 重新编号
    let table = document.getElementById('box-table');
    let indexCells = table.getElementsByClassName('index-cell');
    for (let i = 0; i < indexCells.length; i++) {
        indexCells[i].textContent = i + 1; // 更新编号
    }

    calculate(); // 重新计算总计
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

    for (const [country, postalMap] of Object.entries(window.data.addressByCountry)) {
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
    if (remotePostcodes.includes(postcodeInput)) {
        remoteAddressCheckbox.checked = true;
    } else {
        remoteAddressCheckbox.checked = false;
    }

    // 触发更新
    updateQuote();
}

// 常见问题数据
const faqData = [
    {
        id: 1,
        question: "如何选择合适的运输方式？",
        answer: "根据货物重量、体积、时效要求、成本预算等因素综合考虑。小件货物选择快递，大件货物选择空运或海运。",
        category: "运输方式",
        icon: "bi-truck"
    },
    {
        id: 2,
        question: "清关需要多长时间？",
        answer: "一般3-7个工作日，具体时间取决于目的国海关效率和文件完整性。",
        category: "清关流程",
        icon: "bi-shield-check"
    },
    {
        id: 3,
        question: "如何降低物流成本？",
        answer: "1. 合理包装减少体积重\n2. 选择合适的运输方式\n3. 批量发货享受优惠\n4. 提前规划避免加急费用",
        category: "成本控制",
        icon: "bi-currency-dollar"
    },
    {
        id: 4,
        question: "什么是DDP和DDU？",
        answer: "DDP (Delivered Duty Paid): 包税到门，卖方承担所有费用和风险\nDDU (Delivered Duty Unpaid): 自税到门，买方承担进口关税和税费",
        category: "贸易术语",
        icon: "bi-file-text"
    },
    {
        id: 5,
        question: "如何计算体积重？",
        answer: "体积重 = 长×宽×高÷6000 (空运) 或 ÷5000 (快递)\n计费重 = max(实重, 体积重)",
        category: "重量计算",
        icon: "bi-calculator"
    },
    {
        id: 6,
        question: "货物丢失如何索赔？",
        answer: "1. 立即联系承运商\n2. 提供相关文件证明\n3. 填写索赔申请表\n4. 等待调查结果\n5. 获得赔偿",
        category: "理赔流程",
        icon: "bi-exclamation-triangle"
    },
    {
        id: 7,
        question: "哪些物品不能邮寄？",
        answer: "易燃易爆品、液体、粉末、电池、食品、药品、动植物制品等。具体限制请咨询承运商。",
        category: "禁运物品",
        icon: "bi-x-circle"
    },
    {
        id: 8,
        question: "如何跟踪货物状态？",
        answer: "使用承运商提供的运单号在官网或APP上查询，或联系客服获取最新状态。",
        category: "货物跟踪",
        icon: "bi-geo-alt"
    }
];

// 动态生成分类按钮
function renderCategoryButtons() {
    const categoryButtonsContainer = document.getElementById('categoryButtons');
    if (!categoryButtonsContainer) return;

    // 清空现有按钮
    categoryButtonsContainer.innerHTML = '';

    // 添加"全部"按钮
    const allButton = document.createElement('button');
    allButton.className = 'btn btn-outline-primary';
    allButton.textContent = '全部';
    allButton.onclick = () => filterTerms('全部', allButton);
    allButton.id = 'termTotal';
    categoryButtonsContainer.appendChild(allButton);

    // 从 data.js 中获取分类并生成按钮
    const categories = Object.keys(window.logisticsData.termsByCategory);
    categories.forEach(category => {
        const button = document.createElement('button');
        button.className = 'btn btn-outline-primary';
        button.textContent = category;
        button.onclick = () => filterTerms(category, button);
        categoryButtonsContainer.appendChild(button);
    });
    
    // 初始化回到顶部按钮
    if (typeof initBackToTopButton === 'function') {
        initBackToTopButton();
    }
}

// 初始化常见问题手风琴
function initFaqAccordion() {
    const accordionContainer = document.getElementById('faqAccordion');
    if (!accordionContainer) return;

    accordionContainer.innerHTML = '';

    faqData.forEach((faq, index) => {
        const accordionItem = document.createElement('div');
        accordionItem.className = 'accordion-item';
        accordionItem.innerHTML = `
            <h2 class="accordion-header" id="faq-heading-${index}">
                <button class="accordion-button collapsed" type="button" 
                        data-bs-toggle="collapse" data-bs-target="#faq-collapse-${index}" 
                        aria-expanded="false" aria-controls="faq-collapse-${index}">
                    <i class="bi ${faq.icon} me-2"></i>
                    ${faq.question}
                </button>
            </h2>
            <div id="faq-collapse-${index}" class="accordion-collapse collapse" 
                 aria-labelledby="faq-heading-${index}" data-bs-parent="#faqAccordion">
                <div class="accordion-body">
                    <i class="bi bi-lightbulb me-2 text-warning"></i>
                    ${faq.answer.replace(/\n/g, '<br>')}
                </div>
            </div>
        `;
        accordionContainer.appendChild(accordionItem);
    });
}

// 切换FAQ卡片翻转状态
function toggleFaqCard(card) {
    card.classList.toggle('flipped');
}

// 搜索常见问题
function searchFaq() {
    const searchInput = document.getElementById('faqSearchInput');
    const searchTerm = searchInput.value.toLowerCase().trim();
    const accordionItems = document.querySelectorAll('.accordion-item');
    const noResults = document.getElementById('faqNoResults');
    
    let visibleCount = 0;
    
    accordionItems.forEach(item => {
        const question = item.querySelector('.accordion-button').textContent.toLowerCase();
        const answer = item.querySelector('.accordion-body').textContent.toLowerCase();
        
        if (question.includes(searchTerm) || answer.includes(searchTerm)) {
            item.style.display = 'block';
            visibleCount++;
        } else {
            item.style.display = 'none';
        }
    });
    
    // 显示/隐藏无结果提示
    if (visibleCount === 0 && searchTerm !== '') {
        noResults.style.display = 'block';
    } else {
        noResults.style.display = 'none';
    }
}

// 清空FAQ搜索
function clearFaqSearch() {
    const searchInput = document.getElementById('faqSearchInput');
    searchInput.value = '';
    searchFaq();
}

// 初始化术语模态框
function initTermModal() {
    // 初始化常用术语
    renderCategoryButtons();
    filterTerms('全部');
    
    // 初始化常见问题
    initFaqAccordion();
    
    // 添加搜索事件监听器
    const faqSearchInput = document.getElementById('faqSearchInput');
    if (faqSearchInput) {
        faqSearchInput.addEventListener('input', searchFaq);
    }
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

// 监听运输方式变化，当切换回非快递派时返回到单地址报价页面
function handleDeliveryMethodChange() {
    const channel = document.getElementById('delivery-method-select').value;
    
    if (!channel.includes("express")) {
        // 如果不是快递派，返回到单地址报价页面
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

        // 显示单地址报价页面
        const singleQuoteTab = document.getElementById('single-quote');
        if (singleQuoteTab) {
            singleQuoteTab.classList.add("show", "active");
        }

        // 激活单地址报价Tab导航按钮
        const singleQuoteTabButton = document.querySelector('[data-bs-target="#single-quote"]');
        if (singleQuoteTabButton) {
            singleQuoteTabButton.classList.add("active");
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