
 /**
  * Tab1 - 常用功能
  */

 // 获取所有术语
 const allTerms = Object.values(window.logisticsData.termsByCategory).flat();

 // 分页相关变量
 let currentPage = 1;
 const termsPerPage = 10; // 每页显示的术语数量

 function renderTerms(filteredTerms = allTerms) {
    const termList = document.getElementById("termList");
    termList.innerHTML = ''; // 清空列表

    if (filteredTerms.length === 0) {
        document.getElementById("noResults").style.display = 'block';
    } else {
        document.getElementById("noResults").style.display = 'none';

        // 计算当前页的术语
        const startIndex = (currentPage - 1) * termsPerPage;
        const endIndex = startIndex + termsPerPage;
        const termsToShow = filteredTerms.slice(startIndex, endIndex);

        termsToShow.forEach(term => {
            const card = document.createElement('div');
            card.className = 'term-card';
            card.setAttribute('data-term', term.chinese);
            card.innerHTML = `
                <div class="card-body">
                    <h5 data-bs-toggle="tooltip" data-bs-title="${term.definition || '暂无释义'}">${term.chinese}</h5>
                    <p data-bs-toggle="tooltip" data-bs-title="${term.definition || '暂无释义'}">
                        ${term.english}
                        <span class="copy-btn" onclick="copyTerm(this, '${term.english}')">
                            <i class="bi bi-clipboard"></i>
                        </span>
                    </p>
                    <div class="tags">
                        ${term.tags.map(tag => {
                            const color = tagColors[tag] || "#6c757d"; // 默认灰色
                            return `<span class="badge" style="background-color: ${color}; color: white;">${tag}</span>`;
                        }).join('')}
                    </div>
                </div>
            `;
            termList.appendChild(card);
        });

        // 初始化 Tooltip
        const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
        const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
    }

    // 更新翻页按钮状态
    updatePaginationButtons(filteredTerms.length);
}

  

 // 分类筛选
 function filterTerms(category, button) {
     const searchInput = document.getElementById('searchInput');
     searchInput.value = ''; // 清空搜索框

     // 移除所有按钮的 active 类
     document.querySelectorAll('.category-buttons .btn').forEach(btn => {
         btn.classList.remove('active');
     });

     // 为当前按钮添加 active 类
     if (button) {
         button.classList.add('active');
     }

     // 筛选术语
     if (category === '全部') {
         document.getElementById('termTotal').classList.add('active');
         renderTerms(allTerms);
     } else {
         const filteredTerms = window.logisticsData.termsByCategory[category] || [];
         renderTerms(filteredTerms);
     }

     // 重置当前页为第一页
     currentPage = 1;
 }

 // 初始化搜索功能
function initSearchFunction() {
    const searchInput = document.getElementById('searchInput');
    if (!searchInput) {
        console.warn('搜索输入框未找到，将在DOM加载完成后重试');
        return;
    }
    
    searchInput.addEventListener('input', function () {
        const keyword = this.value.trim().toLowerCase();
        const filteredTerms = allTerms.filter(term => 
            term.chinese.toLowerCase().includes(keyword) || 
            term.english.toLowerCase().includes(keyword)
        );
        renderTerms(filteredTerms);

        // 重置当前页为第一页
        currentPage = 1;
    });
}

 // 清除搜索
 function clearSearch() {
     searchInput.value = '';
     renderTerms(allTerms); // 重置为全部术语

     // 重置当前页为第一页
     currentPage = 1;
 }

 // 翻页功能
 function prevPage() {
     if (currentPage > 1) {
         currentPage--;
         renderTerms(getFilteredTerms());
     }
 }

 function nextPage() {
     const filteredTerms = getFilteredTerms();
     const totalPages = Math.ceil(filteredTerms.length / termsPerPage);
     if (currentPage < totalPages) {
         currentPage++;
         renderTerms(filteredTerms);
     }
 }

 // 获取当前筛选后的术语列表
 function getFilteredTerms() {
     const searchKeyword = document.getElementById('searchInput').value.trim().toLowerCase();
     const activeCategory = document.querySelector('.category-buttons .btn.active').textContent;

     if (activeCategory === '全部') {
         return allTerms.filter(term => 
             term.chinese.toLowerCase().includes(searchKeyword) || 
             term.english.toLowerCase().includes(searchKeyword)
         );
     } else {
         return (window.logisticsData.termsByCategory[activeCategory] || []).filter(term => 
             term.chinese.toLowerCase().includes(searchKeyword) || 
             term.english.toLowerCase().includes(searchKeyword)
         );
     }
 }

 // 更新翻页按钮状态
 function updatePaginationButtons(totalTerms) {
     const prevButton = document.getElementById('prevPage');
     const nextButton = document.getElementById('nextPage');

     if (prevButton && nextButton) {
        prevButton.disabled = currentPage === 1;
        nextButton.disabled = currentPage === Math.ceil(totalTerms / termsPerPage);
    } else {
        console.error('翻页按钮未找到');
    }
 }

 let selectedTags = []; // 存储当前选中的标签

// 切换标签筛选状态
function toggleTagFilter(tag) {
    if (selectedTags.includes(tag)) {
        // 如果标签已选中，则移除
        selectedTags = selectedTags.filter(t => t !== tag);
    } else {
        // 如果标签未选中，则添加
        selectedTags.push(tag);
    }

    // 更新按钮样式
    updateTagButtonStyles();

    // 根据选中的标签筛选术语
    filterTermsByTags();
}

// 更新标签按钮样式
function updateTagButtonStyles() {
    const tagButtons = document.querySelectorAll("#termTagBtns button");
    tagButtons.forEach(button => {
        const match = button.innerText.match(/^[^\(]+/);
        if (match) {
            const tag = match[0].trim().toLowerCase(); // 统一小写
            const tagMatch = selectedTags.some(selectedTag => selectedTag.trim().toLowerCase() === tag);

            // 修改选中效果
            if (tagMatch) {
                button.classList.add("selected");
            } else {
                button.classList.remove("selected");
            }
        }
    });
}
function filterTermsByTags() {
    const allTerms = Object.values(window.logisticsData.termsByCategory).flat();

    // 如果没有选中任何标签，则显示所有术语
    if (selectedTags.length === 0) {
        renderTerms(allTerms);
        return;
    }

    const selectedTagsSet = new Set(selectedTags); 

    const filteredTerms = allTerms.filter(term => {
        // 确保 term.tags 是数组且包含选中的所有标签
        if (Array.isArray(term.tags)) {
            return selectedTags.every(tag => {
                return term.tags.includes(tag);
            });
        }
        return false; // 如果 term 没有 tags 属性，过滤掉
    });
    // 渲染筛选后的术语列表
    renderTerms(filteredTerms);
}

// 获取所有术语的标签
function getAllTags() {
    const allTerms = Object.values(window.logisticsData.termsByCategory).flat();
    const tags = new Set();
    allTerms.forEach(term => {
        if (term.tags && Array.isArray(term.tags)) {
            term.tags.forEach(tag => tags.add(tag));
        }
    });
    return Array.from(tags);
}

// 动态生成标签按钮
function renderTagButtons() {
    const tagButtonsContainer = document.getElementById("termTagBtns");
    const tags = getAllTags();
    const tagCounts = getTagCounts();

    // 清空现有按钮
    tagButtonsContainer.innerHTML = '';

    // 为每个标签生成按钮
    tags.forEach(tag => {
        const button = document.createElement("button");
        button.className = "btn btn-sm me-2 mb-2";
        button.innerText = `${tag} (${tagCounts[tag]})`; // 显示标签和术语数量
        button.setAttribute("data-tag", tag); // 添加 data-tag 属性

        // 统一颜色
        button.style.color = "#333"; // 文字颜色
        button.style.borderColor = "#ccc"; // 边框颜色
        button.style.backgroundColor = "#f8f9fa"; // 背景颜色

        button.onclick = () => toggleTagFilter(tag);
        tagButtonsContainer.appendChild(button);
    });
}


// 动态加载分类数据
function loadUSAData() {
    const accordion = document.getElementById("usaAccordion");
    accordion.innerHTML = usaCategories
        .map(
            (category, index) => `
            <div class="accordion-item">
                <h2 class="accordion-header" id="heading${category.id}">
                    <button class="accordion-button ${index === 0 ? "" : ""}" type="button" data-bs-toggle="collapse" data-bs-target="#collapse${category.id}" aria-expanded="${index === 0 ? "true" : "false"}" aria-controls="collapse${category.id}">
                        ${category.title}
                    </button>
                </h2>
                <div id="collapse${category.id}" class="accordion-collapse collapse ${index === 0 ? "show" : ""}" aria-labelledby="heading${category.id}" data-bs-parent="#usaAccordion">
                    <div class="accordion-body" id="content${category.id}">
                        ${category.render(category.data)}
                    </div>
                </div>
            </div>
        `
        )
        .join("");
}

// 搜索功能
function searchUSAData() {
    const keyword = document.getElementById("usaSearchInput").value.trim().toLowerCase();
    const resultsContainer = document.getElementById("usaSearchResults");
    resultsContainer.innerHTML = ''; // 清空之前的结果

    if (!keyword) {
        // 如果关键词为空，显示所有数据
        usaCategories.forEach(category => {
            const contentElement = document.getElementById(`content${category.id}`);
            if (contentElement) {
                contentElement.innerHTML = category.render(category.data);
            }
        });
        return;
    }

    // 遍历所有分类
    usaCategories.forEach(category => {
        const filteredData = category.data.filter(item => {
            if (typeof item === "string") {
                return item.toLowerCase().includes(keyword);
            } else if (typeof item === "object") {
                return Object.values(item).some(value =>
                    String(value).toLowerCase().includes(keyword)
                );
            }
            return false;
        });

        // 如果有匹配结果，渲染该分类
        if (filteredData.length > 0) {
            const categoryElement = document.createElement("div");
            categoryElement.className = "search-category";
            categoryElement.innerHTML = `
                <h3>${category.title} <span class="match-count">(${filteredData.length} 条结果)</span></h3>
                <div class="search-results">
                    ${category.render(filteredData)}
                </div>
            `;
            resultsContainer.appendChild(categoryElement);

            // 高亮关键词
            highlightKeyword(categoryElement, keyword);
        }
    });

    // 如果没有匹配结果，显示提示
    if (resultsContainer.innerHTML === '') {
        resultsContainer.innerHTML = '<p>未找到匹配的结果。</p>';
    }
}

// 高亮关键词
function highlightKeyword(element, keyword) {
    const regex = new RegExp(keyword, 'gi');
    element.innerHTML = element.innerHTML.replace(regex, match => `<span class="highlight">${match}</span>`);
}

// 实时搜索
document.getElementById("usaSearchInput").addEventListener("input", searchUSAData);

// 清除搜索
function clearUSASearch() {
    document.getElementById("usaSearchInput").value = "";
    loadUSAData(); // 重新加载所有数据
}

/**
 * Tab2 - 快捷回复
 */
// 初始化快捷回复分类按纽
function initQuickReplyCategories() {
    const categoriesContainer = document.getElementById("quick-reply-categories");
    categoriesContainer.innerHTML = ''; // 清空默认内容

    // 添加“全部”分类按钮
    const allButton = document.createElement("button");
    allButton.className = "btn btn-outline-primary me-2 mb-2 active";
    allButton.textContent = "全部";
    allButton.onclick = () => loadQuickReplies("全部");
    categoriesContainer.appendChild(allButton);

    // 添加其他分类按钮
    quickReplies.forEach(category => {
        const button = document.createElement("button");
        button.className = "btn btn-outline-primary me-2 mb-2";
        button.textContent = category.category;
        button.onclick = () => loadQuickReplies(category.category);
        categoriesContainer.appendChild(button);
    });

    // 默认加载“全部”分类的回复
    loadQuickReplies("全部");
}

// 加载分类下的回复
function loadQuickReplies(selectedCategory) {
    const replySelect = document.getElementById("quick-reply-select");
    replySelect.innerHTML = '<option value="">请选择回复</option>'; // 清空默认选项

    // 更新分类按钮的选中状态
    const categoriesContainer = document.getElementById("quick-reply-categories");
    const buttons = categoriesContainer.querySelectorAll("button");
    buttons.forEach(button => {
        button.classList.remove("active");
        if (button.textContent === selectedCategory) {
            button.classList.add("active");
        }
    });

    if (selectedCategory === "全部") {
        // 加载所有分类的回复
        quickReplies.forEach(category => {
            category.replies.forEach(reply => {
                const option = document.createElement("option");
                option.value = reply.chinese; // 中文作为值
                option.setAttribute("data-en", reply.english); // 英文作为属性
                option.textContent = reply.chinese; // 显示中文
                replySelect.appendChild(option);
            });
        });
    } else {
        // 加载指定分类的回复
        const selectedCategoryData = quickReplies.find(category => category.category === selectedCategory);
        if (selectedCategoryData) {
            selectedCategoryData.replies.forEach(reply => {
                const option = document.createElement("option");
                option.value = reply.chinese; // 中文作为值
                option.setAttribute("data-en", reply.english); // 英文作为属性
                option.textContent = reply.chinese; // 显示中文
                replySelect.appendChild(option);
            });
        }
    }
}

//过滤回复内容
function filterQuickReplies() {
    const searchInput = document.getElementById("quick-reply-search").value.trim().toLowerCase();
    const dropdownList = document.getElementById("quick-reply-dropdown");
    dropdownList.innerHTML = ''; // 清空下拉列表

    if (!searchInput) {
        dropdownList.style.display = "none"; // 如果搜索框为空，隐藏下拉列表
        return;
    }

    // 获取所有分类的回复
    let allReplies = [];
    quickReplies.forEach(category => {
        allReplies.push(...category.replies);
    });

    // 过滤匹配的回复
    const filteredReplies = allReplies.filter(reply =>
        reply.chinese.toLowerCase().includes(searchInput) ||
        reply.english.toLowerCase().includes(searchInput)
    );

    // 显示匹配的回复
    if (filteredReplies.length > 0) {
        filteredReplies.forEach(reply => {
            const item = document.createElement("div");
            item.className = "dropdown-item";
            item.textContent = reply.chinese; // 显示中文描述
            item.setAttribute("data-en", reply.english); // 存储英文描述
            item.onclick = () => selectQuickReply(reply.chinese, reply.english);
            dropdownList.appendChild(item);
        });
        dropdownList.style.display = "block"; // 显示下拉列表
    } else {
        dropdownList.style.display = "none"; // 如果没有匹配结果，隐藏下拉列表
    }
}

// 选择回复
function selectQuickReply(chinese, english) {
    // 更新中文和英文消息
    document.getElementById("chinese-message").value = chinese;
    document.getElementById("english-message").value = english;

    // 隐藏下拉列表
    document.getElementById("quick-reply-dropdown").style.display = "none";
}

// 插入快捷回复
function insertQuickReply() {
    const replySelect = document.getElementById("quick-reply-select");
    const selectedOption = replySelect.selectedOptions[0];

    if (selectedOption && selectedOption.value) {
        // 更新中文和英文消息
        document.getElementById("chinese-message").value = selectedOption.value;
        document.getElementById("english-message").value = selectedOption.getAttribute("data-en");
    } else {
        // 清空消息
        document.getElementById("chinese-message").value = "";
        document.getElementById("english-message").value = "";
    }
}

/* 复制快捷回复 */
function copyQuickReply(textareaId, button) {
    const textarea = document.getElementById(textareaId);
    textarea.select();
    document.execCommand("copy");

    // 更新按钮状态
    button.innerHTML = '<i class="bi bi-clipboard-check"></i> ' + (textareaId === "chinese-message" ? "已复制" : "Copied");
    button.classList.add("btn-success");
    button.classList.remove("btn-outline-success");

    // 1.5秒后恢复按钮状态
    setTimeout(() => {
        button.innerHTML = '<i class="bi bi-clipboard"></i> ' + (textareaId === "chinese-message" ? "复制" : "Copy");
        button.classList.remove("btn-success");
        button.classList.add("btn-outline-success");
    }, 1500);
}

/* 复制术语英文 */
function copyTerm(button, text) {
    navigator.clipboard.writeText(text).then(() => {
        // 修改按钮样式
        button.innerHTML = '<i class="bi bi-check"></i>';
        button.classList.add('copied');

        // 2 秒后恢复按钮样式
        setTimeout(() => {
            button.innerHTML = '<i class="bi bi-clipboard"></i>';
            button.classList.remove('copied');
        }, 2000);
    }).catch(err => {
        console.error('复制失败：', err);
    });
}

/**
 * Tab 3 - 成本计算
 */

// 识别地址、箱数、重量、体积信息
function parseCalTabCargoInfo() {
    const input = document.getElementById("cargo-input").value.trim();
    // 使用正则表达式解析箱数、重量、体积
    const volumeRegex = /([\d.]+)\s*(cbm|方)/i;
    const weightRegex = /([\d.]+)\s*(kg|kgs|lb|lbs|磅)/i;
    const quantityRegex = /(\d+)\s*(X|\s*)\s*(BOX|BOXES|Boxs|CARTON|CARTONS|ctn|ctns|件|箱|pal|pallets|托)/i;
    const addressRegex = /(?:To \s+)?([A-Z]{3}\d{1})\b/i;  // 识别开头3个字母 + 1个数字 前缀支持带To
    

    // 提取箱数
    const quantityMatch = input.match(quantityRegex);
    let quantity = quantityMatch ? parseInt(quantityMatch[1]) : 0;

    // 提取方数
    const volumeMatch = input.match(volumeRegex);
    let volume = volumeMatch ? parseFloat(volumeMatch[1]) : 0;

    // 提取重量
    const weightMatch = input.match(weightRegex);
    let weight = 0;
    if (weightMatch) {
        weight = parseFloat(weightMatch[1]);
        const unit = (weightMatch[2] || '').toLowerCase();

        // 如果是磅单位，转换为千克
        if (unit === 'lb' || unit === 'lbs' || unit === '磅') {
            weight *= 0.453592;
        }
    }

    document.getElementById('t_quantity').value = quantity;
    document.getElementById('t_weight').value = Math.ceil(weight);
    document.getElementById('t_volume').value = new Decimal(volume).toDecimalPlaces(2, Decimal.ROUND_UP);

    document.getElementById('tp_quantity').value = quantity;
    document.getElementById('tp_weight').value = Math.ceil(weight);
    document.getElementById('tp_volume').value = new Decimal(volume).toDecimalPlaces(2, Decimal.ROUND_UP);
    
    // 触发计算
    calculateCostDDU();
    calculateCostDDP();
}

// 初始化产品选择下拉框
function initProductSelect() {
    const select = document.getElementById('product-select');
    if (!select || !window.data || !window.data.commonProducts) return;
    
    // 清空现有选项（保留默认选项）
    select.innerHTML = '<option value="" selected>请选择产品</option>';
    
    // 添加产品选项
    window.data.commonProducts.forEach(product => {
        const option = document.createElement('option');
        option.value = product.name;
        option.setAttribute('data-hscode', product.hscode);
        option.setAttribute('data-taxrate', product.taxrate);
        option.textContent = product.name;
        select.appendChild(option);
    });
}

function onProductChange() {
    const select = document.getElementById('product-select');
    const selectedOption = select.options[select.selectedIndex];
    if (selectedOption && selectedOption.value !== "") {
        const taxRate = selectedOption.getAttribute('data-taxrate');
        const hscode = selectedOption.getAttribute('data-hscode');

        // 填入税率输入框
        document.getElementById('t_tax-rate').value = taxRate;

        // 显示海关编码
        document.getElementById('product-hscode').value = hscode;
        calculateCostDDU();
    } else {
        // 没选产品时清空
        document.getElementById('t_tax-rate').value = "";
        document.getElementById('product-hscode').value = "";
    }
}


// 计算自税成本
function calculateCostDDU() {
    // 获取输入值
    const quantity = parseFloat(document.getElementById('t_quantity').value) || 0;
    const weight = new Decimal(parseFloat(document.getElementById('t_weight').value) || 0);
    const volume = new Decimal(parseFloat(document.getElementById('t_volume').value) || 0);
    const pricePerCbm = new Decimal(parseFloat(document.getElementById('t_price-per-cbm').value) || 0);
    const goodsValue = new Decimal(parseFloat(document.getElementById('t_goods-value').value) || 0);
    // 获取税率值
    const taxRate = new Decimal(parseFloat(document.getElementById('t_tax-rate').value) || 0);
    const deliveryFeeUSD = new Decimal(parseFloat(document.getElementById('t_delivery-fee-usd').value) || 0);

    // 计算计费方
    const weightRatio = document.getElementById('weight-ratio-select').value;
    let chargeVolume;
    if (weightRatio === 'actual') {
        // 实际方：只使用体积
        chargeVolume = volume;
    } else {
        // 使用选择的重量比计算
        const ratio = parseFloat(weightRatio);
        chargeVolume = Decimal.max(volume, weight.dividedBy(ratio).toDecimalPlaces(2, Decimal.ROUND_UP));
    }
    document.getElementById('t_charge-volume').textContent = chargeVolume.toFixed(2);

    // 计算泡比 泡比 = 实重 / 体积
    let volumeRatio = new Decimal(0);
    if (weight != 0 && volume != 0) {
        volumeRatio = weight.dividedBy(volume);
        document.getElementById('t_volume-ratio').textContent = volumeRatio.toFixed(0);
    }

    // 计算头程费用
    const forwardingCost = pricePerCbm.mul(chargeVolume);
    document.getElementById('t_freight-forwarding-cost').textContent = forwardingCost.toDecimalPlaces(2, Decimal.ROUND_UP);

    // 计算税金 关税加征30%
    const taxAmount = goodsValue.mul(taxRate.plus(30).dividedBy(100).mul(volume).mul(cost_exchange_rate));
    document.getElementById('t_tax-amount').textContent = taxAmount.toDecimalPlaces(0, Decimal.ROUND_UP);

    // 计算派送费 (RMB)
    const deliveryFeeRMB = deliveryFeeUSD.mul(cost_exchange_rate);
    document.getElementById('t_delivery-fee-rmb').textContent = deliveryFeeRMB.toFixed(2);

    // 计算总成本
    const totalCost = forwardingCost.plus(taxAmount).plus(deliveryFeeRMB);
    document.getElementById('t_total-cost').textContent = totalCost.toDecimalPlaces(0, Decimal.ROUND_UP);

    // 计算单价 (RMB/cbm)
    const unitPriceCbm = chargeVolume.greaterThan(0) ? totalCost.dividedBy(chargeVolume) : new Decimal(0);
    document.getElementById('t_unit-price-cbm').textContent = unitPriceCbm.toDecimalPlaces(0, Decimal.ROUND_UP);

    // 计算单价 (RMD/kg)
    const unitPriceKg = weight.greaterThan(0) ? totalCost.dividedBy(weight) : new Decimal(0);
    document.getElementById('t_unit-price-kg').textContent = unitPriceKg.toFixed(2);
}

// 计算包税成本
function calculateCostDDP() {
    // 获取输入值
    const quantity = parseFloat(document.getElementById('tp_quantity').value) || 0;
    const weight = new Decimal(parseFloat(document.getElementById('tp_weight').value) || 0);
    const volume = new Decimal(parseFloat(document.getElementById('tp_volume').value) || 0);
    const pricePerKg = new Decimal(parseFloat(document.getElementById('tp_price-per-kg').value) || 0);
    const deliveryFeeUSD = new Decimal(parseFloat(document.getElementById('tp_delivery-fee-usd').value) || 0);
    const deliveryFeeRMB = new Decimal(parseFloat(document.getElementById('tp_delivery-fee-rmb').value) || 0);

    // 计算计费重
    let chargeWeight = Decimal.max(weight,volume.mul(1000000).dividedBy(6000)).toDecimalPlaces(0, Decimal.ROUND_UP);
    document.getElementById('tp_charge-weight').textContent = chargeWeight;

    // 计算计费方
    const weightRatio = document.getElementById('weight-ratio-select').value;
    let chargeVolume;
    if (weightRatio === 'actual') {
        // 实际方：只使用体积
        chargeVolume = volume;
    } else {
        // 使用选择的重量比计算
        const ratio = parseFloat(weightRatio);
        chargeVolume = Decimal.max(volume, weight.dividedBy(ratio).toDecimalPlaces(2, Decimal.ROUND_UP));
    }
    document.getElementById('tp_charge-cbm').textContent = chargeVolume.toDecimalPlaces(2, Decimal.ROUND_UP);


    // 计算泡比 泡比 = 实重 / 体积
    let volumeRatio = new Decimal(0);
    if (weight != 0 && volume != 0) {
        volumeRatio = weight.dividedBy(volume);
        document.getElementById('tp_volume-ratio').textContent = volumeRatio.toFixed(0);
    }

    // 计算头程费用
    const forwardingCost = pricePerKg.mul(chargeWeight);
    document.getElementById('tp_freight-forwarding-cost').textContent = forwardingCost.toDecimalPlaces(2, Decimal.ROUND_UP);

    // 计算派送费 (RMB)
    const deliveryFeeTran = deliveryFeeUSD.mul(exchange_rate);
    const totalDeliveryFee = new Decimal(deliveryFeeRMB.add(deliveryFeeTran).toFixed(2));
    document.getElementById('tp_delivery-fee-final').textContent = totalDeliveryFee;

    // 计算总成本
    const totalCost = forwardingCost.plus(totalDeliveryFee);
    document.getElementById('tp_total-cost').textContent = totalCost.toDecimalPlaces(0, Decimal.ROUND_UP);
    
    // 计算单价 (RMB/cbm)
    const unitPriceCbm = chargeVolume.greaterThan(0) ? totalCost.dividedBy(chargeVolume) : new Decimal(0);
    document.getElementById('tp_unit-price-cbm').textContent = unitPriceCbm.toDecimalPlaces(0, Decimal.ROUND_UP);

    // 计算单价 (RMD/kg)
    const unitPriceKg = chargeWeight.greaterThan(0) ? totalCost.dividedBy(chargeWeight) : new Decimal(0);
    document.getElementById('tp_unit-price-kg').textContent = unitPriceKg.toFixed(2);
}


/**
 * Tab 4 - 快递派查价
 */
// 动态生成快递派价格表格
function initCarrierSelect() {
    const sel = document.getElementById('t4_carrier');
    if (!sel || !window.data || !window.data.expressPricing) return;
    const carriers = Object.keys(window.data.expressPricing);
    sel.innerHTML = carriers.map(c => `<option value="${c}">${c}</option>`).join('');
    sel.addEventListener('change', function() {
        syncChannelWithCarrier();
        renderPriceTable();
    });
}

function renderPriceTable() {
    const southTable = document.getElementById("southChinaPriceTable");
    const eastTable = document.getElementById("eastChinaPriceTable");
    const southTbody = southTable?.getElementsByTagName("tbody")[0];
    const eastTbody = eastTable?.getElementsByTagName("tbody")[0];
    if (!southTbody || !eastTbody) return;

    southTbody.innerHTML = "";
    eastTbody.innerHTML = "";

    const carrier = (document.getElementById('t4_carrier') || {}).value;
    const cfg = typeof getCarrierCfg === 'function' ? getCarrierCfg(carrier) : null;

    // 如果未配置承运商，则回退到原有 channel 表逻辑
    if (!cfg) {
        const channel = document.getElementById("t4_channel").value;
        const currentPriceTable = priceTable[channel] || {};
        Object.keys(currentPriceTable).forEach(area => {
            const southRow = document.createElement("tr");
            southRow.innerHTML = `
                <td>${area}</td>
                <td>${currentPriceTable[area]["华南"][0]}</td>
                <td>${currentPriceTable[area]["华南"][1]}</td>
                <td>${currentPriceTable[area]["华南"][2]}</td>
                <td>${currentPriceTable[area]["华南"][3]}</td>
                <td>${currentPriceTable[area]["华南"][4]}</td>
            `;
            southTbody.appendChild(southRow);

            const eastRow = document.createElement("tr");
            eastRow.innerHTML = `
                <td>${area}</td>
                <td>${currentPriceTable[area]["华东"][0]}</td>
                <td>${currentPriceTable[area]["华东"][1]}</td>
                <td>${currentPriceTable[area]["华东"][2]}</td>
                <td>${currentPriceTable[area]["华东"][3]}</td>
                <td>${currentPriceTable[area]["华东"][4]}</td>
            `;
            eastTbody.appendChild(eastRow);
        });
        return;
    }

    // 基于承运商配置动态渲染
    const channel = (document.getElementById("t4_channel") || {}).value;
    const effectiveBreaks = typeof getEffectiveBreaks === 'function' ? getEffectiveBreaks(carrier, channel) : (cfg?.weightBreaks || []);
    const headers = typeof getWeightHeaders === 'function' ? getWeightHeaders(effectiveBreaks) : [];
    // 更新两个表头
    const southThead = southTable.querySelector('thead tr');
    const eastThead = eastTable.querySelector('thead tr');
    if (southThead && headers.length) {
        southThead.innerHTML = `<th>区域</th>` + headers.map(h => `<th>${h}</th>`).join('');
    }
    if (eastThead && headers.length) {
        eastThead.innerHTML = `<th>区域</th>` + headers.map(h => `<th>${h}</th>`).join('');
    }

    // 优先渠道价、否则承运商级价
    const prices = (cfg.channels && cfg.channels[channel] && cfg.channels[channel].prices) || cfg.prices || {};

    // 如果缺少一侧区域，则使用同价逻辑渲染
    const southPrices = prices?.["华南"] || prices?.["华东"] || prices?.['_default'] || {};
    const eastPrices  = prices?.["华东"] || prices?.["华南"] || prices?.['_default'] || {};

    // 华南
    Object.keys(southPrices).forEach(label => {
        const row = document.createElement('tr');
        const arr = southPrices[label] || [];
        row.innerHTML = `<td>${label}</td>` + headers.map((_,i) => `<td>${arr[i] ?? '-'}</td>`).join('');
        southTbody.appendChild(row);
    });
    // 华东
    Object.keys(eastPrices).forEach(label => {
        const row = document.createElement('tr');
        const arr = eastPrices[label] || [];
        row.innerHTML = `<td>${label}</td>` + headers.map((_,i) => `<td>${arr[i] ?? '-'}</td>`).join('');
        eastTbody.appendChild(row);
    });
}

// 页面加载后初始化承运商下拉与价格表
document.addEventListener('DOMContentLoaded', function () {
    // 初始化搜索功能
    initSearchFunction();
    
    // 初始化世界时钟
    try {
        initWorldClock();
    } catch (e) { console.warn('initWorldClock error', e); }
    
    try {
        initCarrierSelect();
    } catch (e) { console.warn('initCarrierSelect error', e); }
    try {
        syncChannelWithCarrier();
        renderPriceTable();
    } catch (e) { console.warn('renderPriceTable error', e); }
});

// 当承运商切换时，同步渠道下拉为该承运商可用渠道
function syncChannelWithCarrier() {
    const carrier = (document.getElementById('t4_carrier') || {}).value;
    const channelSel = document.getElementById('t4_channel');
    if (!carrier || !channelSel || typeof getCarrierCfg !== 'function') return;
    const cfg = getCarrierCfg(carrier);
    if (!cfg || !cfg.channels) return;

    const available = Object.keys(cfg.channels);
    if (available.length === 0) return;

    // 重建渠道下拉，仅展示该承运商支持的渠道
    const current = channelSel.value;
    channelSel.innerHTML = available.map(ch => `<option value="${ch}">${ch}</option>`).join('');
    // 保持当前值如在可选范围，否则选第一个
    if (available.includes(current)) {
        channelSel.value = current;
    }
    if (!available.includes(channelSel.value)) {
        channelSel.value = available[0];
    }
}

// 计算价格并突出显示对应的单元格
function calculatePrice(region,channel,zipcode,weight) {
    if (!zipcode || isNaN(weight) || weight <= 0) {
        document.getElementById("t4_priceResult").innerHTML = "单价：请输入有效的邮编和重量";
        return;
    }
    // 优先承运商配置 先注释掉，后面来调试
    const carrier = (document.getElementById('t4_carrier') || {}).value;
    if (carrier && typeof getCarrierPrice === 'function') {
        const price = getCarrierPrice({ carrier, channel, origin: region, zipcode, weight });
        if (price != null) {
            document.getElementById("t4_priceResult").innerHTML = `单价：$${price} / KG`;
            // 高亮承运商表格对应单元格
            try {
                renderPriceTable();
                const effectiveBreaks = (typeof getEffectiveBreaks === 'function') ? getEffectiveBreaks(carrier, channel) : [];
                const weightIndex = (typeof getWeightIndexByBreaks === 'function') ? getWeightIndexByBreaks(effectiveBreaks, weight) : 0;
                const cfg = (typeof getCarrierCfg === 'function') ? getCarrierCfg(carrier) : null;
                const zipGroups = (cfg && cfg.channels && cfg.channels[channel] && cfg.channels[channel].zipGroups) || (cfg && cfg.zipGroups) || [];
                const zipLabel = (typeof getZipLabelByGroups === 'function') ? getZipLabelByGroups(zipGroups, zipcode) : '';
                if (typeof highlightCarrierPriceCell === 'function') {
                    highlightCarrierPriceCell(zipLabel, weightIndex, region);
                }
            } catch (e) { console.warn('highlight carrier cell error', e); }
            return price;
        }
    }

    // 回退到旧逻辑
    const area = getRegionByZip(zipcode);
    if (!area || !priceTable[channel] || !priceTable[channel][area] || !priceTable[channel][area][region]) {
        document.getElementById("t4_priceResult").innerHTML = "单价：邮编不在配送范围内";
        console.log(JSON.stringify(priceTable, null, 2));
        return;
    }

    renderPriceTable();
    const weightIndex = getWeightIndex(weight);
    const price = priceTable[channel][area][region][weightIndex];
    document.getElementById("t4_priceResult").innerHTML = `单价：$${price} / KG`;
    highlightPriceCell(area, region, weightIndex);
    return price;
}

// 高亮承运商动态表格的单元格（根据 zipLabel 行与 weightIdx 列）
function highlightCarrierPriceCell(zipLabel, weightIdx) {
    // 复用旧的清理逻辑，去除所有历史高亮
    if (typeof clearHighlightedCells === 'function') {
        try { clearHighlightedCells(); } catch(e) {}
    }

    const tables = [document.getElementById('southChinaPriceTable'), document.getElementById('eastChinaPriceTable')];
    tables.forEach(tbl => {
        if (!tbl) return;
        const rows = tbl.querySelectorAll('tbody tr');
        rows.forEach(row => {
            const first = row.querySelector('td');
            if (first && first.textContent.trim() === String(zipLabel)) {
                const tds = row.querySelectorAll('td');
                const target = tds[1 + weightIdx]; // 第0列为标签
                if (target) {
                    // 与原有高亮方式一致：包一层 span.highlight，避免样式不一致
                    target.innerHTML = `<span class="highlight">${target.textContent}</span>`;
                }
            }
        });
    });
}

/**
 * 世界时钟功能
 */
// 世界时钟配置
const worldClockConfig = [
  { 
    name: '北京', 
    timezone: 'Asia/Shanghai', 
    country: '中国',
    timezoneName: '东八区',
    offsetFromBeijing: 0, // 基准时间
    isEditable: true // 可编辑标记
  },
  { 
    name: '洛杉矶', 
    timezone: 'America/Los_Angeles', 
    country: '美国',
    timezoneName: '西八区',
    offsetFromBeijing: -16 // 比北京时间慢16小时（夏令时-15小时）
  },
  { 
    name: '纽约', 
    timezone: 'America/New_York', 
    country: '美国',
    timezoneName: '西五区',
    offsetFromBeijing: -13 // 比北京时间慢13小时（夏令时-12小时）
  },
  { 
    name: '温哥华', 
    timezone: 'America/Vancouver', 
    country: '加拿大',
    timezoneName: '西八区',
    offsetFromBeijing: -16 // 比北京时间慢16小时（夏令时-15小时）
  },
  { 
    name: '多伦多', 
    timezone: 'America/Toronto', 
    country: '加拿大',
    timezoneName: '西五区',
    offsetFromBeijing: -13 // 比北京时间慢13小时（夏令时-12小时）
  },
  { 
    name: '悉尼', 
    timezone: 'Australia/Sydney', 
    country: '澳大利亚',
    timezoneName: '东十区',
    offsetFromBeijing: +2 // 比北京时间快2小时（夏令时+3小时）
  },
  { 
    name: '柏林', 
    timezone: 'Europe/Berlin', 
    country: '德国',
    timezoneName: '东一区',
    offsetFromBeijing: -7 // 比北京时间慢7小时（夏令时-6小时）
  },
  { 
    name: '伦敦', 
    timezone: 'Europe/London', 
    country: '英国',
    timezoneName: '零时区',
    offsetFromBeijing: -8 // 比北京时间慢8小时（夏令时-7小时）
  },
  { 
    name: '耶路撒冷', 
    timezone: 'Asia/Jerusalem', 
    country: '以色列',
    timezoneName: '东二区',
    offsetFromBeijing: -6 // 比北京时间慢6小时（夏令时-5小时）
  },
  { 
    name: '卡拉奇', 
    timezone: 'Asia/Karachi', 
    country: '巴基斯坦',
    timezoneName: '东五区',
    offsetFromBeijing: -3 // 比北京时间慢3小时
  }
];

let worldClockInterval = null;
let customBeijingTime = null; // 自定义的北京时间

// 初始化世界时钟
function initWorldClock() {
  const modal = document.getElementById('worldClockModal');
  
  // 当模态框显示时启动时钟
  modal.addEventListener('shown.bs.modal', function() {
    renderWorldClocks();
    startWorldClock();
  });
  
  // 当模态框隐藏时停止时钟
  modal.addEventListener('hidden.bs.modal', function() {
    stopWorldClock();
  });
}

// 渲染世界时钟
function renderWorldClocks() {
  const container = document.getElementById('worldClockContainer');
  container.innerHTML = '';
  
  worldClockConfig.forEach(config => {
    const clockCard = document.createElement('div');
    clockCard.className = 'col-md-4 col-lg-3 mb-4';
    // 如果是可编辑的时钟（中国时钟），添加点击编辑功能
    const isEditable = config.isEditable;
    const timeDisplay = isEditable ? `
      <div class="clock-time-container">
        <div class="clock-time digital-clock editable-time" data-timezone="${config.timezone}" onclick="toggleTimeEdit('${config.timezone}')" style="cursor: pointer;">
          <span class="time-digit">--</span>:<span class="time-digit">--</span>:<span class="time-digit">--</span>
        </div>
        <div class="time-edit-container" id="edit-${config.timezone}" style="display: none;">
          <input type="datetime-local" class="form-control form-control-sm" id="time-input-${config.timezone}" onchange="updateCustomTime('${config.timezone}')">
          <button type="button" class="btn btn-sm btn-success mt-1" onclick="applyCustomTime('${config.timezone}')">应用</button>
          <button type="button" class="btn btn-sm btn-secondary mt-1" onclick="resetTime('${config.timezone}')">重置</button>
        </div>
      </div>
    ` : `
      <div class="clock-time-container">
        <div class="clock-time digital-clock" data-timezone="${config.timezone}">
          <span class="time-digit">--</span>:<span class="time-digit">--</span>:<span class="time-digit">--</span>
        </div>
      </div>
    `;

    clockCard.innerHTML = `
      <div class="card world-clock-card">
        <div class="card-body text-center">
          <div class="clock-country mb-2">${config.country} (${config.name})</div>
          <div class="timezone-info mb-2">
            <span class="timezone-name">${config.timezoneName}</span>
          </div>
          ${timeDisplay}
          <div class="clock-date" data-timezone="${config.timezone}">
            --/--/----
          </div>
          <div class="time-difference" data-timezone="${config.timezone}">
            --小时
          </div>
        </div>
      </div>
    `;
    container.appendChild(clockCard);
  });
}

// 启动世界时钟
function startWorldClock() {
  // 立即更新一次
  updateWorldClocks();
  
  // 每秒更新一次
  worldClockInterval = setInterval(updateWorldClocks, 1000);
}

// 停止世界时钟
function stopWorldClock() {
  if (worldClockInterval) {
    clearInterval(worldClockInterval);
    worldClockInterval = null;
  }
}

// 更新世界时钟显示
function updateWorldClocks() {
  // 获取基准时间（自定义北京时间或当前北京时间）
  const baseTime = customBeijingTime || new Date();
  
  worldClockConfig.forEach(config => {
    const timeElement = document.querySelector(`[data-timezone="${config.timezone}"].clock-time`);
    const dateElement = document.querySelector(`[data-timezone="${config.timezone}"].clock-date`);
    const diffElement = document.querySelector(`[data-timezone="${config.timezone}"].time-difference`);
    
    if (timeElement && dateElement && diffElement) {
      try {
        let timeInTimezone;
        
        if (config.isEditable && customBeijingTime) {
          // 如果是可编辑的时钟且有自定义时间，直接使用自定义时间
          timeInTimezone = new Date(customBeijingTime);
        } else if (config.isEditable) {
          // 如果是可编辑的时钟但没有自定义时间，使用当前北京时间
          timeInTimezone = new Date();
        } else {
          // 其他时钟根据与北京时间的时差计算
          const offsetMs = config.offsetFromBeijing * 60 * 60 * 1000;
          timeInTimezone = new Date(baseTime.getTime() + offsetMs);
        }
        
        // 格式化时间
        const hours = timeInTimezone.getHours().toString().padStart(2, '0');
        const minutes = timeInTimezone.getMinutes().toString().padStart(2, '0');
        const seconds = timeInTimezone.getSeconds().toString().padStart(2, '0');
        
        // 格式化日期
        const dateString = timeInTimezone.toLocaleDateString('zh-CN', {
          year: 'numeric',
          month: '2-digit',
          day: '2-digit'
        });
        
        // 计算时差（相对于北京时间）
        const beijingTime = customBeijingTime || new Date();
        const timeDiff = calculateTimeDifference(beijingTime, timeInTimezone);
        
        // 更新电子表显示
        const timeDigits = timeElement.querySelectorAll('.time-digit');
        if (timeDigits.length === 3) {
          timeDigits[0].textContent = hours;
          timeDigits[1].textContent = minutes;
          timeDigits[2].textContent = seconds;
        }
        
        dateElement.textContent = dateString;
        diffElement.textContent = timeDiff;
      } catch (error) {
        console.error(`更新时区 ${config.timezone} 时间失败:`, error);
        timeElement.textContent = '--:--:--';
        dateElement.textContent = '--/--/----';
        diffElement.textContent = '--小时';
      }
    }
  });
}


// 计算时差
function calculateTimeDifference(beijingTime, targetTime) {
  // 计算两个时间的差值（毫秒）
  const diffMs = targetTime.getTime() - beijingTime.getTime();
  
  // 转换为小时
  const diffHours = Math.round(diffMs / (1000 * 60 * 60));
  
  // 格式化显示
  if (diffHours === 0) {
    return '±0小时';
  } else if (diffHours > 0) {
    return `+${diffHours}小时`;
  } else {
    return `${diffHours}小时`;
  }
}

// 切换时间编辑模式
function toggleTimeEdit(timezone) {
  const editContainer = document.getElementById(`edit-${timezone}`);
  if (editContainer.style.display === 'none') {
    editContainer.style.display = 'block';
    // 设置当前时间到输入框
    const now = customBeijingTime || new Date();
    const timeString = now.toISOString().slice(0, 16);
    document.getElementById(`time-input-${timezone}`).value = timeString;
  } else {
    editContainer.style.display = 'none';
  }
}

// 更新自定义时间
function updateCustomTime(timezone) {
  const timeInput = document.getElementById(`time-input-${timezone}`);
  const selectedTime = new Date(timeInput.value);
  if (!isNaN(selectedTime.getTime())) {
    customBeijingTime = selectedTime;
    updateWorldClocks();
  }
}

// 应用自定义时间
function applyCustomTime(timezone) {
  const timeInput = document.getElementById(`time-input-${timezone}`);
  const selectedTime = new Date(timeInput.value);
  if (!isNaN(selectedTime.getTime())) {
    customBeijingTime = selectedTime;
    updateWorldClocks();
    document.getElementById(`edit-${timezone}`).style.display = 'none';
  }
}

// 重置时间
function resetTime(timezone) {
  customBeijingTime = null;
  updateWorldClocks();
  document.getElementById(`edit-${timezone}`).style.display = 'none';
}

/**
 * 日期计算功能
 */

// 日期加减计算
function calculateDateFromDays() {
  const baseDate = document.getElementById('baseDate').value;
  const daysInput = document.getElementById('daysInput').value;
  const resultElement = document.getElementById('dateResult1');
  
  if (!baseDate || !daysInput) {
    resultElement.innerHTML = '请选择日期并输入天数';
    resultElement.className = 'alert alert-warning';
    return;
  }
  
  const baseDateObj = new Date(baseDate);
  const days = parseInt(daysInput);
  
  if (isNaN(days)) {
    resultElement.innerHTML = '请输入有效的天数';
    resultElement.className = 'alert alert-danger';
    return;
  }
  
  // 计算新日期
  const newDate = new Date(baseDateObj);
  newDate.setDate(baseDateObj.getDate() + days);
  
  // 格式化日期
  const formattedDate = newDate.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    weekday: 'long'
  });
  
  const direction = days > 0 ? '往后' : days < 0 ? '往前' : '';
  const absDays = Math.abs(days);
  
  resultElement.innerHTML = `
    <strong>计算结果：</strong><br>
    基准日期：${baseDate}<br>
    计算天数：${daysInput}天 (${direction}${absDays}天)<br>
    结果日期：${formattedDate}
  `;
  resultElement.className = 'alert alert-success';
}

// 日期差计算
function calculateDateDifference() {
  const startDate = document.getElementById('startDate').value;
  const endDate = document.getElementById('endDate').value;
  const resultElement = document.getElementById('dateResult2');
  
  if (!startDate || !endDate) {
    resultElement.innerHTML = '请选择开始日期和结束日期';
    resultElement.className = 'alert alert-warning';
    return;
  }
  
  const startDateObj = new Date(startDate);
  const endDateObj = new Date(endDate);
  
  if (startDateObj > endDateObj) {
    resultElement.innerHTML = '开始日期不能晚于结束日期';
    resultElement.className = 'alert alert-danger';
    return;
  }
  
  // 计算日期差
  const timeDiff = endDateObj.getTime() - startDateObj.getTime();
  const daysDiff = Math.ceil(timeDiff / (1000 * 3600 * 24));
  
  // 计算年、月、日
  const years = Math.floor(daysDiff / 365);
  const months = Math.floor((daysDiff % 365) / 30);
  const days = daysDiff % 30;
  
  let resultText = `<strong>计算结果：</strong><br>`;
  resultText += `开始日期：${startDate}<br>`;
  resultText += `结束日期：${endDate}<br>`;
  resultText += `相差天数：${daysDiff}天<br>`;
  
  if (years > 0) {
    resultText += `约 ${years}年`;
    if (months > 0) resultText += ` ${months}个月`;
    if (days > 0) resultText += ` ${days}天`;
  } else if (months > 0) {
    resultText += `约 ${months}个月`;
    if (days > 0) resultText += ` ${days}天`;
  } else {
    resultText += `共 ${daysDiff}天`;
  }
  
  resultElement.innerHTML = resultText;
  resultElement.className = 'alert alert-success';
}

// 清空日期计算1
function clearDateCalc1() {
  document.getElementById('baseDate').value = '';
  document.getElementById('daysInput').value = '';
  document.getElementById('dateResult1').innerHTML = '请选择日期并输入天数';
  document.getElementById('dateResult1').className = 'alert alert-info';
}

// 清空日期计算2
function clearDateCalc2() {
  document.getElementById('startDate').value = '';
  document.getElementById('endDate').value = '';
  document.getElementById('dateResult2').innerHTML = '请选择开始日期和结束日期';
  document.getElementById('dateResult2').className = 'alert alert-info';
}

// 设为今天
function setToday() {
  const today = new Date().toISOString().split('T')[0];
  document.getElementById('baseDate').value = today;
  document.getElementById('startDate').value = today;
  calculateDateFromDays();
  calculateDateDifference();
}

// 设为明天
function setTomorrow() {
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  const tomorrowStr = tomorrow.toISOString().split('T')[0];
  document.getElementById('baseDate').value = tomorrowStr;
  document.getElementById('endDate').value = tomorrowStr;
  calculateDateFromDays();
  calculateDateDifference();
}

// 设为昨天
function setYesterday() {
  const yesterday = new Date();
  yesterday.setDate(yesterday.getDate() - 1);
  const yesterdayStr = yesterday.toISOString().split('T')[0];
  document.getElementById('baseDate').value = yesterdayStr;
  document.getElementById('startDate').value = yesterdayStr;
  calculateDateFromDays();
  calculateDateDifference();
}

// 全部清空
function clearAllDateCalc() {
  clearDateCalc1();
  clearDateCalc2();
}

/**
 * 初始化地址簿功能
 */
function initAddressBook() {

  const modal = new bootstrap.Modal('#addressModal');
  
  // 打开模态框时加载数据
  document.getElementById('openAddressBook').addEventListener('click', function() {
    renderAddressTable();
  });

  // 绑定筛选事件
  document.getElementById('addressSearch').addEventListener('input', filterAddresses);
  document.getElementById('addressTypeFilter').addEventListener('change', filterAddresses);
  document.getElementById('remoteFilter').addEventListener('change', filterAddresses);
}

/**
 * 渲染地址表格
 */
function renderAddressTable(data = customerAddresses) {
  const tbody = document.getElementById('addressTableBody');
  tbody.innerHTML = '';

  data.forEach(addr => {
    const row = document.createElement('tr');
    row.innerHTML = `
      <td width="5%">${addr.customer}</td>
      <td width="5%">${addr.postalCode}</td>
      <td width="40%" class="text-truncate" title="${addr.address}">
        ${addr.address}
      </td>
      <td width="15%">${addr.company || '-'}</td>
      <td width="10%">${addr.contact || '-'}</td>
      <td width="5%">${addr.phone || '-'}</td>
      <td width="5%">
        <span class="badge ${addr.isCommercial ? 'bg-primary' : 'bg-success'}">
          ${addr.isCommercial ? '商业' : '住宅'}
        </span>
      </td>
      <td width="5%">
        <span class="badge ${addr.isRemote ? 'bg-danger' : 'bg-success'}">
          ${addr.isRemote ? '偏远' : '非偏远'}
        </span>
      </td>
      <td width="10%">
        <button class="btn btn-sm btn-outline-primary py-0 px-2"
                onclick="copyAddress(${addr.id})"
                title="复制地址信息">
          <i class="bi bi-clipboard"></i>
        </button>
      </td>
    `;
    tbody.appendChild(row);
  });
}

/**
 * 筛选地址
 */
function filterAddresses() {
  const searchTerm = document.getElementById('addressSearch').value.toLowerCase();
  const typeFilter = document.getElementById('addressTypeFilter').value;
  const remoteFilter = document.getElementById('remoteFilter').value;

  const filtered = customerAddresses.filter(addr => {
    return (
      // 搜索条件（新增对公司名、联系人、电话的搜索）
      (addr.customer.toLowerCase().includes(searchTerm) ||
      addr.postalCode.includes(searchTerm) ||
      addr.address.toLowerCase().includes(searchTerm) ||
      (addr.company && addr.company.toLowerCase().includes(searchTerm)) ||
      (addr.contact && addr.contact.toLowerCase().includes(searchTerm)) ||
      (addr.phone && addr.phone.includes(searchTerm))
    ) && (
      // 类型条件
      typeFilter === 'all' || 
      (typeFilter === 'commercial' && addr.isCommercial) ||
      (typeFilter === 'personal' && !addr.isCommercial)
    ) && (
      // 偏远条件
      remoteFilter === 'all' || 
      (remoteFilter === 'remote' && addr.isRemote) ||
      (remoteFilter === 'non-remote' && !addr.isRemote)
    ));
  });

  renderAddressTable(filtered);
}

/**
 * 使用选中的地址
 */
/**
 * 复制地址信息到剪贴板
 */
function copyAddress(id) {
  const addr = customerAddresses.find(a => a.id === id);
  if (!addr) return;

  // 构建要复制的文本内容
  let addressText = '';
  if (addr.company) addressText += `${addr.company}\n`;
  if (addr.contact) addressText += `${addr.contact}\n`;
  if (addr.phone) addressText += `${addr.phone}\n`;
  addressText += `${addr.address}`;

  // 使用Clipboard API复制文本
  navigator.clipboard.writeText(addressText.trim())
    .then(() => {
      // 显示复制成功的提示
      const toast = new bootstrap.Toast(document.getElementById('copyToast'));
      document.getElementById('toastMessage').textContent = '地址已复制到剪贴板';
      toast.show();
    })
    .catch(err => {
      console.error('复制失败:', err);
      // 备用复制方法
      const textarea = document.createElement('textarea');
      textarea.value = addressText;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      
      const toast = new bootstrap.Toast(document.getElementById('copyToast'));
      document.getElementById('toastMessage').textContent = '地址已复制(兼容模式)';
      toast.show();
    });
}