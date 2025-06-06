
 /**
  * Tab1 - 常用功能
  */

 // 获取所有术语
 const allTerms = Object.values(termsByCategory).flat();

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
         const filteredTerms = termsByCategory[category] || [];
         renderTerms(filteredTerms);
     }

     // 重置当前页为第一页
     currentPage = 1;
 }

 // 搜索功能
 const searchInput = document.getElementById('searchInput');
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
         return (termsByCategory[activeCategory] || []).filter(term => 
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
    const allTerms = Object.values(termsByCategory).flat();

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
    const allTerms = Object.values(termsByCategory).flat();
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

// 计算自税成本
function calculateCostDDU() {
    // 获取输入值
    const quantity = parseFloat(document.getElementById('t_quantity').value) || 0;
    const weight = new Decimal(parseFloat(document.getElementById('t_weight').value) || 0);
    const volume = new Decimal(parseFloat(document.getElementById('t_volume').value) || 0);
    const pricePerCbm = new Decimal(parseFloat(document.getElementById('t_price-per-cbm').value) || 0);
    const goodsValue = new Decimal(parseFloat(document.getElementById('t_goods-value').value) || 0);
    const taxRate = new Decimal(parseFloat(document.getElementById('t_tax-rate').value) || 0);
    const deliveryFeeUSD = new Decimal(parseFloat(document.getElementById('t_delivery-fee-usd').value) || 0);

    // 计算计费方
    let chargeVolume = Decimal.max(volume, weight.dividedBy(363).toDecimalPlaces(2, Decimal.ROUND_UP));
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
    const unitPriceCbm = totalCost.dividedBy(chargeVolume);
    document.getElementById('t_unit-price-cbm').textContent = unitPriceCbm.toDecimalPlaces(0, Decimal.ROUND_UP);

    // 计算单价 (RMD/kg)
    const unitPriceKg = totalCost.dividedBy(weight);
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
    let chargeVolume = Decimal.max(volume, weight.dividedBy(363).toDecimalPlaces(2, Decimal.ROUND_UP));
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
    const unitPriceCbm = totalCost.dividedBy(chargeVolume);
    document.getElementById('tp_unit-price-cbm').textContent = unitPriceCbm.toDecimalPlaces(0, Decimal.ROUND_UP);

    // 计算单价 (RMD/kg)
    const unitPriceKg = totalCost.dividedBy(chargeWeight);
    document.getElementById('tp_unit-price-kg').textContent = unitPriceKg.toFixed(2);
}


/**
 * Tab 4 - 快递派查价
 */
// 动态生成快递派价格表格
function renderPriceTable() {
    const channel = document.getElementById("t4_channel").value;
    const southChinaTableElement = document.getElementById("southChinaPriceTable").getElementsByTagName("tbody")[0];
    const eastChinaTableElement = document.getElementById("eastChinaPriceTable").getElementsByTagName("tbody")[0];
    southChinaTableElement.innerHTML = ""; // 清空表格内容
    eastChinaTableElement.innerHTML = ""; // 清空表格内容

    // 获取当前渠道的价格数据
    const currentPriceTable = priceTable[channel];

    // 遍历价格数据表
    Object.keys(currentPriceTable).forEach(area => {
        // 添加华南价格行
        const southChinaRow = document.createElement("tr");
        southChinaRow.innerHTML = `
            <td>${area}</td>
            <td>${currentPriceTable[area]["华南"][0]}</td>
            <td>${currentPriceTable[area]["华南"][1]}</td>
            <td>${currentPriceTable[area]["华南"][2]}</td>
            <td>${currentPriceTable[area]["华南"][3]}</td>
            <td>${currentPriceTable[area]["华南"][4]}</td>
        `;
        southChinaTableElement.appendChild(southChinaRow);

        // 添加华东价格行
        const eastChinaRow = document.createElement("tr");
        eastChinaRow.innerHTML = `
            <td>${area}</td>
            <td>${currentPriceTable[area]["华东"][0]}</td>
            <td>${currentPriceTable[area]["华东"][1]}</td>
            <td>${currentPriceTable[area]["华东"][2]}</td>
            <td>${currentPriceTable[area]["华东"][3]}</td>
            <td>${currentPriceTable[area]["华东"][4]}</td>
        `;
        eastChinaTableElement.appendChild(eastChinaRow);
    });
}

// 计算价格并突出显示对应的单元格
function calculatePrice(region,channel,zipcode,weight) {

    if (!zipcode || isNaN(weight) || weight <= 0) {
        document.getElementById("t4_priceResult").innerHTML = "单价：请输入有效的邮编和重量";
        return;
    }
    
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

    // 突出显示对应的单元格
    highlightPriceCell(area, region, weightIndex);

    return price;
}