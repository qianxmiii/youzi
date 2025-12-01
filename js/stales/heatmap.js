// 热力图功能
let heatmapChart = null;

// 初始化热力图
function initHeatmap() {
    const chartElement = document.getElementById('heatmapChart');
    if (!chartElement) {
        console.warn('热力图容器未找到');
        return;
    }
    
    if (!window.heatmapData) {
        console.warn('热力图数据未找到');
        return;
    }
    
    const heatmapTypeRadio = document.querySelector('input[name="heatmapType"]:checked');
    const heatmapDimensionRadio = document.querySelector('input[name="heatmapDimension"]:checked');
    
    if (!heatmapTypeRadio || !heatmapDimensionRadio) {
        console.warn('热力图选项未找到');
        return;
    }
    
    const heatmapType = heatmapTypeRadio.value;
    const heatmapDimension = heatmapDimensionRadio.value;
    
    console.log('热力图类型:', heatmapType, '维度:', heatmapDimension);
    updateHeatmap(heatmapType, heatmapDimension);
    
    // 监听选择变化
    document.querySelectorAll('input[name="heatmapType"]').forEach(radio => {
        radio.addEventListener('change', () => {
            const type = document.querySelector('input[name="heatmapType"]:checked').value;
            const dimension = document.querySelector('input[name="heatmapDimension"]:checked').value;
            updateHeatmap(type, dimension);
        });
    });
    
    document.querySelectorAll('input[name="heatmapDimension"]').forEach(radio => {
        radio.addEventListener('change', () => {
            const type = document.querySelector('input[name="heatmapType"]:checked').value;
            const dimension = document.querySelector('input[name="heatmapDimension"]:checked').value;
            updateHeatmap(type, dimension);
        });
    });
}

// 更新热力图
function updateHeatmap(type, dimension) {
    const ctx = document.getElementById('heatmapChart');
    if (!ctx || !window.heatmapData) return;
    
    // 销毁旧图表
    if (heatmapChart) {
        heatmapChart.destroy();
    }
    
    // 如果是客户×国家交叉热力图
    if (dimension === 'customer_country') {
        createMatrixHeatmap(type);
        return;
    }
    
    let labels = [];
    let data = [];
    let backgroundColor = [];
    
    // 根据维度获取数据
    let sourceData = {};
    if (dimension === 'customer') {
        sourceData = window.heatmapData.by_customer || {};
        labels = Object.keys(sourceData).sort();
    } else if (dimension === 'country') {
        sourceData = window.heatmapData.by_country || {};
        labels = Object.keys(sourceData).sort();
    } else if (dimension === 'channel') {
        sourceData = window.heatmapData.by_channel || {};
        labels = Object.keys(sourceData).sort();
    }
    
    // 提取数据并计算颜色
    labels.forEach(label => {
        const value = sourceData[label] ? (sourceData[label][type] || 0) : 0;
        data.push(value);
    });
    
    const maxValue = Math.max(...data, 1);
    backgroundColor = data.map(value => getHeatmapColor(value, maxValue));
    
    // 创建图表
    heatmapChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: getTypeLabel(type),
                data: data,
                backgroundColor: backgroundColor,
                borderColor: backgroundColor.map(c => c.replace('0.8', '1').replace('0.6', '1').replace('0.5', '1')),
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${getTypeLabel(type)}: ${context.parsed.y}`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                },
                x: {
                    ticks: {
                        maxRotation: 45,
                        minRotation: 45
                    }
                }
            }
        }
    });
}

// 创建矩阵热力图（客户×国家）
function createMatrixHeatmap(type) {
    const ctx = document.getElementById('heatmapChart');
    if (!ctx || !window.heatmapData || !window.heatmapData.customer_country) {
        return;
    }
    
    if (heatmapChart) {
        heatmapChart.destroy();
    }
    
    const customerCountryData = window.heatmapData.customer_country;
    const customers = new Set();
    const countries = new Set();
    const matrix = {};
    
    Object.values(customerCountryData).forEach(item => {
        customers.add(item.customer);
        countries.add(item.country);
        const key = `${item.customer}|${item.country}`;
        matrix[key] = item[type] || 0;
    });
    
    const customerList = Array.from(customers).sort();
    const countryList = Array.from(countries).sort();
    
    // 准备数据 - 每个国家一个数据集
    const datasets = countryList.map((country) => {
        const data = customerList.map(customer => {
            const key = `${customer}|${country}`;
            return matrix[key] || 0;
        });
        
        const maxValue = Math.max(...Object.values(matrix), 1);
        const backgroundColor = data.map(v => getHeatmapColor(v, maxValue));
        
        return {
            label: country,
            data: data,
            backgroundColor: backgroundColor,
            borderWidth: 1
        };
    });
    
    heatmapChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: customerList,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: true,
                    position: 'right'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.dataset.label}: ${context.parsed.y}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    stacked: true,
                    ticks: {
                        maxRotation: 45,
                        minRotation: 45
                    }
                },
                y: {
                    stacked: true,
                    beginAtZero: true
                }
            }
        }
    });
}

// 获取颜色（根据数值大小）
function getHeatmapColor(value, maxValue) {
    if (maxValue === 0) return 'rgba(200, 200, 200, 0.5)';
    
    const ratio = value / maxValue;
    if (ratio < 0.25) {
        return `rgba(144, 238, 144, ${0.3 + ratio * 0.5})`; // 浅绿
    } else if (ratio < 0.5) {
        return `rgba(255, 255, 0, ${0.5 + (ratio - 0.25) * 0.3})`; // 黄色
    } else if (ratio < 0.75) {
        return `rgba(255, 165, 0, ${0.6 + (ratio - 0.5) * 0.3})`; // 橙色
    } else {
        return `rgba(255, 0, 0, ${0.7 + (ratio - 0.75) * 0.3})`; // 红色
    }
}

// 获取类型标签
function getTypeLabel(type) {
    const labels = {
        'total': '总运单数',
        'inspection': '查验运单',
        'stale_7': '超过7天未更新',
        'stale_14': '超过14天未更新'
    };
    return labels[type] || type;
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 监听热力图展开事件，只在展开时初始化
    const heatmapCollapse = document.getElementById('heatmapCollapse');
    if (heatmapCollapse) {
        heatmapCollapse.addEventListener('shown.bs.collapse', function() {
            // 延迟初始化，确保Chart.js已加载
            setTimeout(() => {
                const chartElement = document.getElementById('heatmapChart');
                if (!chartElement) {
                    console.warn('热力图容器未找到');
                    return;
                }
                
                if (typeof Chart === 'undefined') {
                    console.error('Chart.js 未加载');
                    return;
                }
                
                if (!window.heatmapData) {
                    console.warn('热力图数据未找到');
                    return;
                }
                
                // 如果图表还未初始化，则初始化
                if (!heatmapChart) {
                    console.log('初始化热力图，数据:', window.heatmapData);
                    initHeatmap();
                }
            }, 100);
        });
        
        // 如果热力图默认是展开的，立即初始化
        if (heatmapCollapse.classList.contains('show')) {
            setTimeout(() => {
                const chartElement = document.getElementById('heatmapChart');
                if (chartElement && typeof Chart !== 'undefined' && window.heatmapData && !heatmapChart) {
                    console.log('初始化热力图，数据:', window.heatmapData);
                    initHeatmap();
                }
            }, 200);
        }
    }
});

