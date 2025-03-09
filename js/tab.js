
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

    // 计算税金 关税加征20%
    const taxAmount = goodsValue.mul(taxRate.plus(20)).dividedBy(100).mul(chargeVolume).mul(exchange_rate);
    document.getElementById('t_tax-amount').textContent = taxAmount.toDecimalPlaces(0, Decimal.ROUND_UP);

    // 计算派送费 (RMB)
    const deliveryFeeRMB = deliveryFeeUSD.mul(exchange_rate);
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
    const deliveryFeeRMB = deliveryFeeUSD.mul(exchange_rate);
    document.getElementById('tp_delivery-fee-rmb').textContent = deliveryFeeRMB.toFixed(2);

    // 计算总成本
    const totalCost = forwardingCost.plus(deliveryFeeRMB);
    document.getElementById('tp_total-cost').textContent = totalCost.toDecimalPlaces(0, Decimal.ROUND_UP);
    
    // 计算单价 (RMB/cbm)
    const unitPriceCbm = totalCost.dividedBy(chargeVolume);
    document.getElementById('tp_unit-price-cbm').textContent = unitPriceCbm.toDecimalPlaces(0, Decimal.ROUND_UP);

    // 计算单价 (RMD/kg)
    const unitPriceKg = totalCost.dividedBy(weight);
    document.getElementById('tp_unit-price-kg').textContent = unitPriceKg.toFixed(2);
}