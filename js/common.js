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
    const daysToFriday = 7+((5 - currentDay + 7) % 7);  // 星期五是5
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

    const usaTransitData = transitTimeData["USA"]; // 获取美国时效数据
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
    const caTransitData = transitTimeData["Canada"]; // 获取加拿大时效数据
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

    const transitData = transitTimeData["Europe"]; // 获取加拿大时效数据
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
    const transitData = transitTimeData["UK"]; // 获取加拿大时效数据
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
    const transitData = transitTimeData["Austrilia"]; // 获取加拿大时效数据
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
    const allTerms = Object.values(termsByCategory).flat();
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
    return (window.data && window.data.expressPricing && window.data.expressPricing[carrier]) || null;
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
 * 显示提示消息
 */
function showToast(message, type = 'info') {
    // 如果页面中有toast组件，使用它
    const toast = document.getElementById('copyToast');
    if (toast) {
        const toastMessage = document.getElementById('toastMessage');
        if (toastMessage) {
            toastMessage.textContent = message;
        }
        
        // 显示toast
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
    } else {
        // 简单的alert提示
        alert(message);
    }
}



// 页面加载完成后初始化历史记录显示
document.addEventListener('DOMContentLoaded', function() {
    // 初始化Bootstrap tooltips
    initBootstrapTooltips();
    
    // 延迟一点时间确保其他组件已加载
    setTimeout(() => {
        updateHistoryDisplay();
    }, 500);
});

