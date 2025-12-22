/**
 * common.js 通用功能
 */

// 初始化Bootstrap tooltips
function initBootstrapTooltips() {
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
}

// 获取当前时间并转为北京时间（UTC +8）
function getBeijingTime() {
    const now = new Date();
    const beijingTime = new Date(now.getTime() + (8 * 60 * 60 * 1000)); // 加8小时
    return beijingTime;
}

// 获取下个星期五的日期（MM/DD格式）
function getNextFriday() {
    const beijingTime = getBeijingTime();
    const currentDay = beijingTime.getDay();
    
    // 计算到下一个周五的天数（总是返回下周五）
    let daysToFriday;
    if (currentDay === 5) {
        // 如果今天是周五，返回下周五（7天后）
        daysToFriday = 7;
    } else {
        // 其他情况，计算到下周五的天数
        daysToFriday = (5 - currentDay + 7) % 7 + 7;
    }
    
    const nextFriday = new Date(beijingTime);
    nextFriday.setDate(beijingTime.getDate() + daysToFriday);

    const month = nextFriday.getMonth() + 1; // 月份是从0开始的
    const day = nextFriday.getDate();
    return `${month.toString().padStart(2, '0')}/${day.toString().padStart(2, '0')}`;
}

/**
 * 获取时效
 */
function getTransitTime(country, channel, postcode, address) {
    let transitTime = "";
    postcode = postcode != null ? postcode[0] : 0;

    switch (country) {
        case "美国":
            transitTime = getTransitTimeUSA(channel, postcode, address);
            break;
        case "加拿大":
            transitTime = getTransitTimeCA(channel, postcode);
            break;
        case "欧洲":
            transitTime = getTransitTimeEU(channel, postcode);
            break;
        case "英国":
            transitTime = getTransitTimeUK(channel, postcode);
            break;
        case "澳大利亚":
            transitTime = getTransitTimeAU(channel, postcode);
            break;
        default:
            transitTime = ""; // 或者其他默认值
    }
    return transitTime;
}

/**
 * 获取美国时效
 */
function getTransitTimeUSA(channel, postcode, address) {
    // 优先检查特定地址的配置
    if (address && typeof specificAddressTransitTime !== 'undefined' && specificAddressTransitTime[address]) {
        const addressConfig = specificAddressTransitTime[address];
        if (addressConfig[channel]) {
            return addressConfig[channel];
        }
    }

    const usaTransitData = transitTimeData["美国"]; // 获取美国时效数据
    if (!usaTransitData || !usaTransitData[channel]) {
        return ""; // 如果渠道不存在，返回空字符串
    }

    const channelData = usaTransitData[channel]; // 获取当前渠道的时效数据

    // 根据邮编范围匹配时效
    if (channelData["default"]) {
        return channelData["default"]; // 返回默认时效
    }

    if (channel == "Sea truck") { //卡派 4开头地址时效 萨凡纳等
        // 根据邮编范围匹配时效
        if (postcode < 5) {
            return channelData["0-4"] || ""; // 美东
        } else if (postcode < 8) {
            return channelData["5-7"] || ""; // 美中
        } else {
            return channelData["8-9"] || ""; // 美西
        }
    } else {
        // 根据邮编范围匹配时效
        if (postcode < 4) {
            return channelData["0-3"] || ""; // 美东
        } else if (postcode < 8) {
            return channelData["4-7"] || ""; // 美中
        } else {
            return channelData["8-9"] || ""; // 美西
        }
    }

}

/**
 * 获取加拿大时效
 */
function getTransitTimeCA(channel, postcode) {
    const caTransitData = transitTimeData["加拿大"]; // 获取加拿大时效数据
    if (!caTransitData || !caTransitData[channel]) {
        return ""; // 如果渠道不存在，返回空字符串
    }

    const channelData = caTransitData[channel]; // 获取当前渠道的时效数据

    // 返回默认时效
    return channelData["default"] || "";
}

/**
 * 获取欧洲时效
 */
function getTransitTimeEU(channel, postcode) {

    const transitData = transitTimeData["欧洲"]; // 获取欧洲时效数据
    if (!transitData || !transitData[channel]) {
        return ""; // 如果渠道不存在，返回空字符串
    }

    const channelData = transitData[channel]; // 获取当前渠道的时效数据

    // 返回默认时效
    return channelData["default"] || "";
}

/**
 * 获取英国时效
 */
function getTransitTimeUK(channel, postcode) {
    const transitData = transitTimeData["英国"]; // 获取英国时效数据
    if (!transitData || !transitData[channel]) {
        return ""; // 如果渠道不存在，返回空字符串
    }

    const channelData = transitData[channel]; // 获取当前渠道的时效数据

    // 返回默认时效
    return channelData["default"] || "";
}

/**
 * 获取加拿大时效
 */
function getTransitTimeAU(channel, postcode) {
    const transitData = transitTimeData["澳大利亚"]; // 获取澳大利亚时效数据
    if (!transitData || !transitData[channel]) {
        return ""; // 如果渠道不存在，返回空字符串
    }

    const channelData = transitData[channel]; // 获取当前渠道的时效数据

    // 返回默认时效
    return channelData["default"] || "";
}

/**
 * 获取中文渠道名
 */
function getCN(channel) {
     try {
        const channelMap = window.data?.channelNames || {};
        return channelMap[channel] ?? channelMap._default ?? channel;
    } catch (e) {
        console.error('获取渠道名称失败:', e);
        return channel; // 出错时返回原渠道名
    }
}

// 获取每个标签的术语数量
function getTagCounts() {
    const allTerms = Object.values(window.logisticsData.termsByCategory).flat();
    const tagCounts = {};

    allTerms.forEach(term => {
        if (term.tags && Array.isArray(term.tags)) {
            term.tags.forEach(tag => {

                if (!tagCounts[tag]) {
                    tagCounts[tag] = 0;
                }
                tagCounts[tag]++;
            });
        }
    });

    return tagCounts;
}

// 偏远地址时效
function getRemoteTranTime(channel,transitTime) {
    if (channel == 'Sea truck'){
        transitTime = addDays(transitTime, 5);
    }
    return transitTime;
}

// 增加天数
function addDays(transitTime, days) {
    let match = transitTime.match(/(\d+)-(\d+)/); // 使用正则匹配两个数字

    if (match) {
        let start = parseInt(match[1], 10) + days; // 提取第一个数字并加5
        let end = parseInt(match[2], 10) + days; // 提取第二个数字并加5

        return `${start}-${end}`; // 返回修改后的字符串
    } else {
        return transitTime; // 若格式不匹配，返回错误信息
    }
}

// ==================== 计算历史功能 ====================

/**
 * 保存计算历史
 */
function saveCalculationHistory() {
    // 获取当前计算数据
    const currentData = getCurrentCalculationData();
    
    if (!currentData || !isValidCalculation(currentData)) {
        return; // 如果数据无效，不保存
    }
    
    // 获取现有历史记录
    const history = JSON.parse(localStorage.getItem('calculationHistory') || '[]');
    
    // 创建新的历史记录
    const newRecord = {
        id: Date.now(),
        timestamp: new Date().toISOString(),
        data: currentData,
        summary: generateHistorySummary(currentData),
        details: generateHistoryDetails(currentData)
    };
    
    // 检查是否已存在相同的计算记录（避免重复）
    const isDuplicate = history.some(record => 
        record.data.totalQuantity === currentData.totalQuantity &&
        record.data.totalWeight === currentData.totalWeight &&
        record.data.totalVolume === currentData.totalVolume
    );
    
    if (!isDuplicate) {
        // 将新记录添加到开头
        history.unshift(newRecord);
        
        // 只保留最近50条记录
        if (history.length > 50) {
            history.splice(50);
        }
        
        // 保存到本地存储
        localStorage.setItem('calculationHistory', JSON.stringify(history));
        
        // 更新显示
        updateHistoryDisplay();
        
        // 显示保存成功提示
        showToast('计算记录已保存', 'success');
    }
}

/**
 * 获取当前计算数据
 */
function getCurrentCalculationData() {
    const totalQuantity = parseInt(document.getElementById('total-quantity')?.textContent || '0');
    const totalVolume = parseFloat(document.getElementById('total-volume')?.textContent || '0');
    const totalWeight = parseFloat(document.getElementById('total-weight')?.textContent || '0');
    const totalDimensionWeight = parseFloat(document.getElementById('total-dimension-weight')?.textContent || '0');
    const billingWeight = parseFloat(document.getElementById('billing-weight')?.textContent || '0');
    const volumeRatio = parseFloat(document.getElementById('volume-ratio')?.textContent || '0');
    
    // 获取箱规表格数据
    const boxData = getBoxTableData();
    
    return {
        totalQuantity,
        totalVolume,
        totalWeight,
        totalDimensionWeight,
        billingWeight,
        volumeRatio,
        boxData,
        timestamp: new Date().toISOString()
    };
}

/**
 * 获取箱规表格数据
 */
function getBoxTableData() {
    const rows = document.querySelectorAll('#box-table tr.input-row');
    const boxData = [];
    
    rows.forEach(row => {
        const length = parseFloat(row.querySelector('.length')?.value || '0');
        const width = parseFloat(row.querySelector('.width')?.value || '0');
        const height = parseFloat(row.querySelector('.height')?.value || '0');
        const weight = parseFloat(row.querySelector('.weight')?.value || '0');
        const quantity = parseInt(row.querySelector('.quantity')?.value || '0');
        
        if (length > 0 && width > 0 && height > 0 && weight > 0 && quantity > 0) {
            boxData.push({ length, width, height, weight, quantity });
        }
    });
    
    return boxData;
}

/**
 * 验证计算数据是否有效
 */
function isValidCalculation(data) {
    return data.totalQuantity > 0 && 
           data.totalWeight > 0 && 
           data.totalVolume > 0 &&
           data.boxData.length > 0;
}

/**
 * 生成历史记录摘要
 */
function generateHistorySummary(data) {
    return `${data.totalQuantity}箱 ${data.totalWeight}kg ${data.totalVolume.toFixed(2)}cbm`;
}

/**
 * 生成历史记录详细信息
 */
function generateHistoryDetails(data) {
    const boxCount = data.boxData.length;
    const avgWeight = (data.totalWeight / data.totalQuantity).toFixed(2);
    const avgVolume = (data.totalVolume / data.totalQuantity).toFixed(3);
    
    return `${boxCount}种规格 | 平均${avgWeight}kg/箱 | 平均${avgVolume}cbm/箱`;
}

/**
 * 更新历史记录显示
 */
function updateHistoryDisplay() {
    const history = JSON.parse(localStorage.getItem('calculationHistory') || '[]');
    const container = document.getElementById('history-container');
    const countElement = document.getElementById('historyCount');
    
    if (!container || !countElement) return;
    
    // 更新计数
    countElement.textContent = history.length;
    
    if (history.length === 0) {
        container.innerHTML = '<div class="history-empty">暂无计算记录</div>';
        return;
    }
    
    // 生成历史记录HTML
    const historyHTML = history.map(record => `
        <div class="history-item" onclick="loadCalculationFromHistory(${record.id})" title="点击加载此计算">
            <div class="history-time">${formatHistoryTime(record.timestamp)}</div>
            <div class="history-summary">${record.summary}</div>
            <div class="history-details">${record.details}</div>
        </div>
    `).join('');
    
    container.innerHTML = historyHTML;
}

/**
 * 格式化历史记录时间
 */
function formatHistoryTime(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    
    if (diffMins < 1) return '刚刚';
    if (diffMins < 60) return `${diffMins}分钟前`;
    if (diffHours < 24) return `${diffHours}小时前`;
    if (diffDays < 7) return `${diffDays}天前`;
    
    return date.toLocaleDateString('zh-CN', {
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

/**
 * 从历史记录加载计算
 */
function loadCalculationFromHistory(historyId) {
    const history = JSON.parse(localStorage.getItem('calculationHistory') || '[]');
    const record = history.find(h => h.id === historyId);
    
    if (!record) {
        showToast('历史记录不存在', 'error');
        return;
    }
    
    // 加载箱规数据
    loadBoxDataFromHistory(record.data.boxData);
    
    // 更新汇总信息
    updateSummaryFromHistory(record.data);
    
    // 高亮选中的历史记录
    highlightSelectedHistory(historyId);
    
    // 显示加载成功提示
    showToast('已加载历史记录', 'success');
    
    // 自动展开历史记录区域
    const historyCollapse = new bootstrap.Collapse(document.getElementById('historyCollapse'));
    historyCollapse.show();
}

/**
 * 加载箱规数据到表格
 */
function loadBoxDataFromHistory(boxData) {
    const tableBody = document.getElementById('box-table');
    if (!tableBody) return;
    
    // 清空现有行（保留第一行）
    const existingRows = tableBody.querySelectorAll('tr.input-row');
    for (let i = 1; i < existingRows.length; i++) {
        existingRows[i].remove();
    }
    
    // 加载数据到第一行
    if (boxData.length > 0) {
        const firstRow = tableBody.querySelector('tr.input-row');
        const firstBox = boxData[0];
        
        firstRow.querySelector('.length').value = firstBox.length;
        firstRow.querySelector('.width').value = firstBox.width;
        firstRow.querySelector('.height').value = firstBox.height;
        firstRow.querySelector('.weight').value = firstBox.weight;
        firstRow.querySelector('.quantity').value = firstBox.quantity;
        
        // 添加额外的行
        for (let i = 1; i < boxData.length; i++) {
            addRow();
            const newRow = tableBody.querySelector(`tr.input-row:nth-child(${i + 1})`);
            const box = boxData[i];
            
            newRow.querySelector('.length').value = box.length;
            newRow.querySelector('.width').value = box.width;
            newRow.querySelector('.height').value = box.height;
            newRow.querySelector('.weight').value = box.weight;
            newRow.querySelector('.quantity').value = box.quantity;
        }
        
        // 重新计算
        calculate();
    }
}

/**
 * 更新汇总信息
 */
function updateSummaryFromHistory(data) {
    const elements = {
        'total-quantity': data.totalQuantity,
        'total-volume': data.totalVolume.toFixed(2),
        'total-weight': data.totalWeight,
        'total-dimension-weight': data.totalDimensionWeight,
        'billing-weight': data.billingWeight,
        'volume-ratio': data.volumeRatio.toFixed(2)
    };
    
    Object.entries(elements).forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    });
}

// === 承运商定制查价通用函数 ===
function getCarrierCfg(carrier) {
    return (window.data && expressPricing && expressPricing[carrier]) || null;
}

function getWeightIndexByBreaks(breaks, weight) {
    const list = breaks || [];
    const w = Number(weight || 0);
    
    // 如果没有断点，返回0
    if (list.length === 0) return 0;
    
    // 从最后一个断点开始向前查找，找到第一个大于等于当前重量的断点
    // 这样确保找到最合适的档位（该公斤段及以上的公斤适用于这个价格）
    for (let i = list.length - 1; i >= 0; i--) {
        if (w >= list[i]) {
            return i;
        }
    }
    
    // 如果重量小于所有断点，匹配到第一个档位（MOQ档位）
    return 0;
}

function getZipLabelByGroups(groups, zipcode) {
    const z = String(zipcode || "");
    for (const g of (groups || [])) {
        if ((g.prefixes || []).some(p => z.startsWith(p))) return g.label;
    }
    return "_default";
}

// 支持承运商下多渠道：优先取子渠道配置，缺失时回退承运商级默认
function getCarrierPrice(params) {
    const { carrier, channel, origin, zipcode, weight } = params;
    const carrierCfg = getCarrierCfg(carrier);
    if (!carrierCfg) return null;

    const channelCfg = (carrierCfg.channels && carrierCfg.channels[channel]) || {};

    const weightBreaks = channelCfg.weightBreaks || carrierCfg.weightBreaks || [];
    const zipGroups = channelCfg.zipGroups || carrierCfg.zipGroups || [];
    const prices = (channelCfg.prices || carrierCfg.prices || {});

    const idx = getWeightIndexByBreaks(weightBreaks, weight);
    const zipLabel = getZipLabelByGroups(zipGroups, zipcode);
    // 区域价格回退：优先 origin（华东/华南），否则用另一区域或 _default
    const otherRegion = origin === '华南' ? '华东' : '华南';
    const regionMap = prices[origin] || prices[otherRegion] || prices['_default'] || null;
    if (!regionMap) return null;
    const row = regionMap[zipLabel] || regionMap["_default"] || null;
    if (!row) return null;
    return row[idx] != null ? row[idx] : null;
}

function getWeightHeaders(breaks) {
    if (!breaks || breaks.length === 0) return ["∞KG+"]; // 兜底
    // 仅展示 断点KG+；首断点作为低消（包含小于首断点）
    return breaks.map(b => `${b}KG+`);
}

// 获取用于渲染的最终断点（考虑渠道覆盖）
function getEffectiveBreaks(carrier, channel) {
    const cfg = getCarrierCfg(carrier);
    if (!cfg) return [];
    const ch = (cfg.channels && cfg.channels[channel]) || {};
    return ch.weightBreaks || cfg.weightBreaks || [];
}

// 规范化价格数组长度以匹配列头
function normalizePriceRow(arr, headersLen) {
    if (!Array.isArray(arr)) return [];
    // 如果数据仍包含“<首断点”那一档（长度=断点数+1），去掉第一个
    if (arr.length === headersLen + 1) return arr.slice(1);
    // 否则截断或填充到相同长度
    if (arr.length > headersLen) return arr.slice(0, headersLen);
    if (arr.length < headersLen) return arr.concat(new Array(headersLen - arr.length).fill('-'));
    return arr;
}

/**
 * 高亮选中的历史记录
 */
function highlightSelectedHistory(historyId) {
    // 移除所有高亮
    document.querySelectorAll('.history-item').forEach(item => {
        item.classList.remove('selected');
    });
    
    // 高亮选中的记录
    const selectedItem = document.querySelector(`[onclick*="${historyId}"]`);
    if (selectedItem) {
        selectedItem.classList.add('selected');
    }
}

/**
 * 清空计算历史
 */
function clearHistory() {
    if (confirm('确定要清空所有计算历史吗？此操作不可恢复。')) {
        localStorage.removeItem('calculationHistory');
        updateHistoryDisplay();
        showToast('历史记录已清空', 'success');
    }
}

/**
 * 获取 Toast 图标 SVG
 */
function getToastIcon(type) {
    const icons = {
        success: `<svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M16.7071 5.29289C17.0976 5.68342 17.0976 6.31658 16.7071 6.70711L8.70711 14.7071C8.31658 15.0976 7.68342 15.0976 7.29289 14.7071L3.29289 10.7071C2.90237 10.3166 2.90237 9.68342 3.29289 9.29289C3.68342 8.90237 4.31658 8.90237 4.70711 9.29289L8 12.5858L15.2929 5.29289C15.6834 4.90237 16.3166 4.90237 16.7071 5.29289Z" fill="white"/>
        </svg>`,
        error: `<svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="10" cy="10" r="9" fill="white"/>
            <path d="M6 6L14 14M14 6L6 14" stroke="#dc3545" stroke-width="2" stroke-linecap="round"/>
        </svg>`,
        warning: `<svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M10 2L2 18H18L10 2Z" fill="white"/>
            <path d="M10 7V11M10 15H10.01" stroke="#ffc107" stroke-width="1.5" stroke-linecap="round"/>
        </svg>`,
        info: `<svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="10" cy="10" r="9" fill="white"/>
            <path d="M10 6V10M10 14H10.01" stroke="#0dcaf0" stroke-width="1.5" stroke-linecap="round"/>
        </svg>`
    };
    return icons[type] || icons.success;
}

/**
 * 显示提示消息（支持多种类型）
 * @param {string} message - 提示消息
 * @param {string} type - 类型: 'success', 'error', 'warning', 'info'，默认为 'success'
 */
function showToast(message, type = 'success') {
    // 如果页面中有toast组件，使用它
    const toastElement = document.getElementById('copyToast');
    if (toastElement) {
        const toastMessage = document.getElementById('toastMessage');
        const toastIcon = document.getElementById('toastIcon');
        if (toastMessage && toastIcon) {
            // 设置消息内容
            toastMessage.textContent = message;
            
            // 设置图标和类型
            toastIcon.innerHTML = getToastIcon(type);
            // 移除所有类型类，然后添加当前类型
            toastIcon.classList.remove('success', 'error', 'warning', 'info');
            toastIcon.classList.add(type);
            
            // 清除之前的淡出动画类
            toastElement.classList.remove('fade-out');
            
            // 显示弹窗
            toastElement.style.display = 'block';
            
            // 3秒后自动隐藏
            setTimeout(() => {
                toastElement.classList.add('fade-out');
                setTimeout(() => {
                    toastElement.style.display = 'none';
                }, 300);
            }, 3000);
        }
    } else {
        // 简单的alert提示
        alert(message);
    }
}



// ==================== 批量派送时间查询功能 ====================

/**
 * 获取下周的指定工作日（0-6：日-六），北京时间
 */
function getNextWeekdayBJ(targetDow) {
    const now = getBeijingTime();
    const dow = now.getDay();
    // 确保是"下周"的该星期
    const daysToNextWeek = 7 - dow;           // 到下周日的天数
    const nextWeekSunday = new Date(now);
    nextWeekSunday.setDate(now.getDate() + daysToNextWeek);
    const delta = (targetDow + 7) % 7;        // 从下周日偏移到目标周几
    const next = new Date(nextWeekSunday);
    next.setDate(nextWeekSunday.getDate() + delta);
    return next; // Date
}

/**
 * Fast sea → 下周三，其它 → 下周四
 */
function getDefaultETDByChannel(channel) {
    const isFast = channel === 'Fast sea truck' || channel === 'Fast sea express';
    const targetDow = isFast ? 3 : 4; // 3:周三, 4:周四
    return getNextWeekdayBJ(targetDow);
}

function formatDateMMDD(date) {
    const m = (date.getMonth() + 1).toString().padStart(2, '0');
    const d = date.getDate().toString().padStart(2, '0');
    return `${m}/${d}`;
}

/**
 * 解析"35-45"或"35-45 days"→ {min:35, max:45}
 */
function parseTransitRange(str) {
    if (!str) return null;
    const m = String(str).match(/(\d+)\s*[-~到]\s*(\d+)/);
    if (m) return { min: parseInt(m[1], 10), max: parseInt(m[2], 10) };
    const n = String(str).match(/(\d+)/g);
    if (n && n.length === 1) return { min: parseInt(n[0], 10), max: parseInt(n[0], 10) };
    return null;
}

function addDaysDate(date, days) {
    const d = new Date(date);
    d.setDate(d.getDate() + days);
    return d;
}

/**
 * 输入：Date etd, '35-45' → {etaStart:Date, etaEnd:Date}
 */
function calcEtaRange(etdDate, transitStr) {
    const r = parseTransitRange(transitStr);
    if (!r) return null;
    return {
        etaStart: addDaysDate(etdDate, r.min),
        etaEnd: addDaysDate(etdDate, r.max)
    };
}

/**
 * 格式化英文日期 (Dec 5th)
 */
function formatDateEN(date) {
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    
    const month = months[date.getMonth()];
    const day = date.getDate();
    
    // 添加序数后缀
    let dayStr = day.toString();
    if (day === 1 || day === 21 || day === 31) {
        dayStr += 'st';
    } else if (day === 2 || day === 22) {
        dayStr += 'nd';
    } else if (day === 3 || day === 23) {
        dayStr += 'rd';
    } else {
        dayStr += 'th';
    }
    
    return `${month} ${dayStr}`;
}

/**
 * 解析ETD字符串为日期输入格式 (MM/DD -> YYYY-MM-DD)
 */
function parseETDToDateInput(etdStr) {
    if (!etdStr) return '';
    
    // 解析 MM/DD 格式
    const match = etdStr.match(/(\d{1,2})\/(\d{1,2})/);
    if (match) {
        const month = parseInt(match[1], 10);
        const day = parseInt(match[2], 10);
        
        // 假设是当前年份，如果日期已过则用下一年
        const currentYear = new Date().getFullYear();
        const date = new Date(currentYear, month - 1, day);
        
        // 如果日期已过，使用下一年
        if (date < new Date()) {
            date.setFullYear(currentYear + 1);
        }
        
        return date.toISOString().slice(0, 10);
    }
    
    return '';
}

/**
 * 批量查询派送时间
 */
function batchQueryDeliveryTime() {
    const addressesInput = document.getElementById('deliveryAddresses').value.trim();
    const channel = document.getElementById('deliveryChannel').value;
    const etdInput = document.getElementById('deliveryETD').value;
    
    if (!addressesInput) {
        showToast('请输入地址代码', 'warning');
        return;
    }
    
    // 解析地址列表
    const addresses = addressesInput.split(',').map(addr => addr.trim()).filter(addr => addr);
    if (addresses.length === 0) {
        showToast('请输入有效的地址代码', 'warning');
        return;
    }
    
    // 确定ETD
    let etdDate;
    if (etdInput) {
        etdDate = new Date(etdInput + 'T00:00:00');
    } else {
        etdDate = getDefaultETDByChannel(channel);
        // 更新输入框显示默认ETD
        document.getElementById('deliveryETD').value = etdDate.toISOString().slice(0, 10);
    }
    
    // 批量查询结果
    const results = [];
    
    addresses.forEach(address => {
        // 查找地址对应的国家和邮编
        let matchedCountry = "美国";
        let postcode = "";
        
        for (const [country, postalMap] of Object.entries(addressByCountry)) {
            if (postalMap[address]) {
                matchedCountry = country;
                postcode = postalMap[address];
                break;
            }
        }
        
        // 获取时效
        const transitTime = getTransitTime(matchedCountry, channel, postcode, address);
        
        // 计算ETA
        const eta = calcEtaRange(etdDate, transitTime);
        
        // 格式化结果
        const channelCN = getCN(channel);
        const etdStr = formatDateMMDD(etdDate);
        const etaStr = eta ? `${formatDateMMDD(eta.etaStart)} - ${formatDateMMDD(eta.etaEnd)}` : '无法计算';
        
        // 生成复制格式
        const enFormat = eta ? `${address} estimate delivery time: ${formatDateEN(eta.etaStart)} to ${formatDateEN(eta.etaEnd)}.` : `${address} estimate delivery time: 无法计算`;
        const cnFormat = eta ? `${address} 预计派送时间: ${etaStr}` : `${address} 预计派送时间: 无法计算`;
        
        results.push({
            address,
            postcode,
            channel: channelCN,
            etd: etdStr,
            transitTime,
            eta: etaStr,
            enFormat,
            cnFormat
        });
    });
    
    // 渲染表格
    renderDeliveryResultTable(results);
    
    // 更新计数
    document.getElementById('deliveryResultCount').textContent = `${results.length} 条记录`;
    
    showToast(`批量查询完成，共 ${results.length} 条记录`, 'success');
}

/**
 * 渲染查询结果表格
 */
function renderDeliveryResultTable(results) {
    const tbody = document.getElementById('deliveryResultBody');
    
    if (results.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="9" class="text-center text-muted py-4">
                    <i class="bi bi-info-circle"></i> 请输入地址代码并点击"批量查询"
                </td>
            </tr>
        `;
        return;
    }
    
    const rows = results.map((result, index) => `
        <tr data-index="${index}">
            <td><strong>${result.address}</strong></td>
            <td>${result.postcode}</td>
            <td>${result.channel}</td>
            <td>
                <input type="date" class="form-control form-control-sm" 
                       value="${parseETDToDateInput(result.etd)}" 
                       onchange="updateRowETD(${index}, this.value)"
                       style="min-width: 120px;">
            </td>
            <td>
                <input type="text" class="form-control form-control-sm" 
                       value="${result.transitTime}" 
                       onchange="updateRowTransitTime(${index}, this.value)"
                       style="min-width: 100px;">
            </td>
            <td class="text-success fw-bold" id="eta-${index}">${result.eta}</td>
            <td>
                <div class="d-flex gap-1">
                  <button class="btn btn-outline-primary btn-sm" onclick="copyRowEN(${index})" title="复制英文" style="min-width: 50px;">
                      EN
                  </button>
                  <button class="btn btn-outline-success btn-sm" onclick="copyRowCN(${index})" title="复制中文" style="min-width: 50px;">
                      中文
                  </button>
                </div>
            </td>
        </tr>
    `).join('');
    
    tbody.innerHTML = rows;
}

/**
 * 更新行的ETD
 */
function updateRowETD(index, newETD) {
    const row = document.querySelector(`tr[data-index="${index}"]`);
    if (!row) return;
    
    const transitTimeInput = row.querySelector('input[type="text"]');
    const transitTime = transitTimeInput.value;
    
    const etdDate = new Date(newETD + 'T00:00:00');
    const eta = calcEtaRange(etdDate, transitTime);
    
    if (eta) {
        const etaStr = `${formatDateMMDD(eta.etaStart)} - ${formatDateMMDD(eta.etaEnd)}`;
        document.getElementById(`eta-${index}`).textContent = etaStr;
    } else {
        document.getElementById(`eta-${index}`).textContent = '无法计算';
    }
}

/**
 * 更新行的运输时间
 */
function updateRowTransitTime(index, newTransitTime) {
    const row = document.querySelector(`tr[data-index="${index}"]`);
    if (!row) return;
    
    const etdInput = row.querySelector('input[type="date"]');
    const etdDate = new Date(etdInput.value + 'T00:00:00');
    const eta = calcEtaRange(etdDate, newTransitTime);
    
    if (eta) {
        const etaStr = `${formatDateMMDD(eta.etaStart)} - ${formatDateMMDD(eta.etaEnd)}`;
        document.getElementById(`eta-${index}`).textContent = etaStr;
    } else {
        document.getElementById(`eta-${index}`).textContent = '无法计算';
    }
}

/**
 * 复制单行结果
 */
function copyRowEN(index) {
    const row = document.querySelector(`tr[data-index="${index}"]`);
    if (!row) return;
    const address = row.cells[0].textContent.trim();
    const etdInput = row.querySelector('input[type="date"]').value;
    const transit = row.querySelector('input[type="text"]').value;
    const etdDate = new Date(etdInput + 'T00:00:00');
    const eta = calcEtaRange(etdDate, transit);
    if (!eta) { showToast('无法计算ETA', 'error'); return; }
    const text = `${address} estimate delivery time: ${formatDateEN(eta.etaStart)} to ${formatDateEN(eta.etaEnd)}.`;
    navigator.clipboard.writeText(text).then(() => showToast('英文结果已复制到剪贴板','success')).catch(()=>showToast('复制失败','error'));
}

function copyRowCN(index) {
    const row = document.querySelector(`tr[data-index="${index}"]`);
    if (!row) return;
    const address = row.cells[0].textContent.trim();
    const etdInput = row.querySelector('input[type="date"]').value;
    const transit = row.querySelector('input[type="text"]').value;
    const etdDate = new Date(etdInput + 'T00:00:00');
    const eta = calcEtaRange(etdDate, transit);
    if (!eta) { showToast('无法计算ETA', 'error'); return; }
    const text = `${address} 预计派送时间: ${formatDateMMDD(eta.etaStart)} - ${formatDateMMDD(eta.etaEnd)}`;
    navigator.clipboard.writeText(text).then(() => showToast('中文结果已复制到剪贴板','success')).catch(()=>showToast('复制失败','error'));
}

/**
 * 复制批量结果 - 英文格式
 */
function copyBatchResultEN() {
    const tbody = document.getElementById('deliveryResultBody');
    const rows = tbody.querySelectorAll('tr');
    
    if (rows.length === 0 || rows[0].querySelector('td').colSpan) {
        showToast('没有查询结果可复制', 'warning');
        return;
    }
    
    const results = [];
    rows.forEach(row => {
        const cells = row.querySelectorAll('td');
        if (cells.length >= 7) {
            const address = cells[0].textContent.trim();
            const etdStr = row.querySelector('input[type="date"]').value;
            const transit = row.querySelector('input[type="text"]').value;
            const etdDate = new Date(etdStr + 'T00:00:00');
            const eta = calcEtaRange(etdDate, transit);
            if (eta) {
                results.push(`${address} estimate delivery time: ${formatDateEN(eta.etaStart)} to ${formatDateEN(eta.etaEnd)}.`);
            }
        }
    });
    
    if (results.length === 0) {
        showToast('没有有效结果可复制', 'warning');
        return;
    }
    
    const copyText = results.join('\n');
    
    navigator.clipboard.writeText(copyText).then(() => {
        showToast(`已复制 ${results.length} 条英文结果到剪贴板`, 'success');
    }).catch(() => {
        showToast('复制失败', 'error');
    });
}

/**
 * 复制批量结果 - 中文格式
 */
function copyBatchResultCN() {
    const tbody = document.getElementById('deliveryResultBody');
    const rows = tbody.querySelectorAll('tr');
    
    if (rows.length === 0 || rows[0].querySelector('td').colSpan) {
        showToast('没有查询结果可复制', 'warning');
        return;
    }
    
    const results = [];
    rows.forEach(row => {
        const cells = row.querySelectorAll('td');
        if (cells.length >= 7) {
            const address = cells[0].textContent.trim();
            const etdStr = row.querySelector('input[type="date"]').value;
            const transit = row.querySelector('input[type="text"]').value;
            const etdDate = new Date(etdStr + 'T00:00:00');
            const eta = calcEtaRange(etdDate, transit);
            if (eta) {
                results.push(`${address} 预计派送时间: ${formatDateMMDD(eta.etaStart)} - ${formatDateMMDD(eta.etaEnd)}`);
            }
        }
    });
    
    if (results.length === 0) {
        showToast('没有有效结果可复制', 'warning');
        return;
    }
    
    const copyText = results.join('\n');
    
    navigator.clipboard.writeText(copyText).then(() => {
        showToast(`已复制 ${results.length} 条中文结果到剪贴板`, 'success');
    }).catch(() => {
        showToast('复制失败', 'error');
    });
}

/**
 * 复制批量结果 - 表格格式
 */
function copyBatchResultTable() {
    const tbody = document.getElementById('deliveryResultBody');
    const rows = tbody.querySelectorAll('tr');
    
    if (rows.length === 0 || rows[0].querySelector('td').colSpan) {
        showToast('没有查询结果可复制', 'warning');
        return;
    }
    
    const results = [];
    rows.forEach(row => {
        const cells = row.querySelectorAll('td');
        if (cells.length >= 7) {
            const address = cells[0].textContent.trim();
            const postcode = cells[1].textContent.trim();
            const channel = cells[2].textContent.trim();
            const etd = row.querySelector('input[type="date"]').value;
            const transitTime = row.querySelector('input[type="text"]').value;
            const eta = cells[5].textContent.trim();
            results.push(`${address}\t${postcode}\t${channel}\t${etd}\t${transitTime}\t${eta}`);
        }
    });
    
    if (results.length === 0) {
        showToast('没有有效结果可复制', 'warning');
        return;
    }
    
    const header = '地址\t邮编\t渠道\tETD\t运输时间\t预计派送';
    const copyText = header + '\n' + results.join('\n');
    
    navigator.clipboard.writeText(copyText).then(() => {
        showToast(`已复制 ${results.length} 条表格结果到剪贴板`, 'success');
    }).catch(() => {
        showToast('复制失败', 'error');
    });
}

/**
 * 地址输入自动转大写
 */
function convertAddressesToUpper() {
    const textarea = document.getElementById('deliveryAddresses');
    const cursorPos = textarea.selectionStart;
    const oldValue = textarea.value;
    const newValue = oldValue.toUpperCase();
    
    if (oldValue !== newValue) {
        textarea.value = newValue;
        // 恢复光标位置
        textarea.setSelectionRange(cursorPos, cursorPos);
    }
}

/**
 * 复制表格所有英文结果
 */
function copyAllTableEN() {
    const tbody = document.getElementById('deliveryResultBody');
    const rows = tbody.querySelectorAll('tr');
    
    if (rows.length === 0) {
        showToast('没有查询结果可复制', 'warning');
        return;
    }
    
    // 检查是否有空状态行
    const firstRow = rows[0];
    if (firstRow.querySelector('td[colspan]')) {
        showToast('没有查询结果可复制', 'warning');
        return;
    }
    
    const results = [];
    rows.forEach(row => {
        const cells = row.querySelectorAll('td');
        if (cells.length >= 7) {
            const address = cells[0].textContent.trim();
            const etdInput = row.querySelector('input[type="date"]');
            const transitInput = row.querySelector('input[type="text"]');
            
            if (etdInput && transitInput) {
                const etdStr = etdInput.value;
                const transit = transitInput.value;
                const etdDate = new Date(etdStr + 'T00:00:00');
                const eta = calcEtaRange(etdDate, transit);
                if (eta) {
                    results.push(`${address} estimate delivery time: ${formatDateEN(eta.etaStart)} to ${formatDateEN(eta.etaEnd)}.`);
                }
            }
        }
    });
    
    if (results.length === 0) {
        showToast('没有有效结果可复制', 'warning');
        return;
    }
    
    const copyText = results.join('\n');
    
    navigator.clipboard.writeText(copyText).then(() => {
        showToast(`已复制 ${results.length} 条英文结果到剪贴板`, 'success');
    }).catch(() => {
        showToast('复制失败', 'error');
    });
}

/**
 * 重置查询
 */
function resetDeliveryQuery() {
    document.getElementById('deliveryAddresses').value = '';
    document.getElementById('deliveryChannel').value = 'Sea truck';
    document.getElementById('deliveryETD').value = '';
    document.getElementById('deliveryResultCount').textContent = '0 条记录';
    
    // 清空表格
    const tbody = document.getElementById('deliveryResultBody');
    tbody.innerHTML = `
        <tr>
            <td colspan="7" class="text-center text-muted py-4">
                <i class="bi bi-info-circle"></i> 请输入地址代码并点击"批量查询"
            </td>
        </tr>
    `;
    
    // 重新设置默认ETD
    const defaultETD = getDefaultETDByChannel('Sea truck');
    document.getElementById('deliveryETD').value = defaultETD.toISOString().slice(0, 10);
}

// 页面加载完成后初始化历史记录显示
// 初始化计算历史和汇总信息按钮的选中状态
function initCollapseButtonStates() {
    const historyCollapse = document.getElementById('historyCollapse');
    const summaryCollapse = document.getElementById('summaryCollapse');
    const historyButton = document.querySelector('button[data-bs-target="#historyCollapse"]');
    const summaryButton = document.querySelector('button[data-bs-target="#summaryCollapse"]');
    
    if (historyCollapse && historyButton) {
        historyCollapse.addEventListener('show.bs.collapse', function() {
            historyButton.classList.add('active');
        });
        historyCollapse.addEventListener('hide.bs.collapse', function() {
            historyButton.classList.remove('active');
        });
    }
    
    if (summaryCollapse && summaryButton) {
        summaryCollapse.addEventListener('show.bs.collapse', function() {
            summaryButton.classList.add('active');
        });
        summaryCollapse.addEventListener('hide.bs.collapse', function() {
            summaryButton.classList.remove('active');
        });
    }
}

document.addEventListener('DOMContentLoaded', function() {
    // 初始化collapse按钮状态
    initCollapseButtonStates();
    // 初始化Bootstrap tooltips
    initBootstrapTooltips();
    
    // 延迟一点时间确保其他组件已加载
    setTimeout(() => {
        updateHistoryDisplay();
    }, 500);
});

