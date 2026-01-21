/**
 * 仓库查询功能
 */

// 存储所有仓库数据
let allWarehouses = [];
let filteredWarehouses = [];
let selectedWarehouseIds = new Set();

/**
 * 初始化仓库查询模态框
 */
function initWarehouseModal() {
    // 加载仓库数据
    if (window.warehouseData && window.warehouseData.warehouses) {
        allWarehouses = window.warehouseData.warehouses;
        filteredWarehouses = [...allWarehouses];
        
        // 初始化筛选选项
        initWarehouseFilters();
        
        // 渲染表格
        renderWarehouseTable();
        
        // 更新统计信息和按钮状态
        updateWarehouseStats();
        updateSelectAllButton();
    } else {
        console.error('仓库数据未加载');
        document.getElementById('warehouseTableBody').innerHTML = `
            <tr>
                <td colspan="8" class="text-center text-danger py-4">
                    <i class="bi bi-exclamation-triangle"></i> 仓库数据未加载，请检查数据文件
                </td>
            </tr>
        `;
    }
}

/**
 * 初始化筛选选项
 */
function initWarehouseFilters() {
    // 初始化地址类型筛选
    const filterTypeSelect = document.getElementById('warehouseFilterType');
    if (filterTypeSelect) {
        const addressTypes = new Set();
        allWarehouses.forEach(warehouse => {
            if (warehouse['地址类型']) {
                addressTypes.add(warehouse['地址类型']);
            }
        });
        
        filterTypeSelect.innerHTML = '<option value="">全部地址类型</option>';
        Array.from(addressTypes).sort().forEach(type => {
            const option = document.createElement('option');
            option.value = type;
            option.textContent = type;
            filterTypeSelect.appendChild(option);
        });
    }
    
    // 初始化国家代码筛选
    const filterCountrySelect = document.getElementById('warehouseFilterCountry');
    if (filterCountrySelect) {
        const countryCodes = new Set();
        allWarehouses.forEach(warehouse => {
            if (warehouse['国家代码']) {
                countryCodes.add(warehouse['国家代码']);
            }
        });
        
        filterCountrySelect.innerHTML = '<option value="">全部国家代码</option>';
        Array.from(countryCodes).sort().forEach(code => {
            const option = document.createElement('option');
            option.value = code;
            option.textContent = code;
            filterCountrySelect.appendChild(option);
        });
    }
    
    // 初始化州省筛选
    const filterStateSelect = document.getElementById('warehouseFilterState');
    if (filterStateSelect) {
        const states = new Set();
        allWarehouses.forEach(warehouse => {
            if (warehouse['州省']) {
                states.add(warehouse['州省']);
            }
        });
        
        filterStateSelect.innerHTML = '<option value="">全部州省</option>';
        Array.from(states).sort().forEach(state => {
            const option = document.createElement('option');
            option.value = state;
            option.textContent = state;
            filterStateSelect.appendChild(option);
        });
    }
}

/**
 * 筛选仓库
 */
function filterWarehouses() {
    const searchInput = document.getElementById('warehouseSearchInput');
    const filterTypeSelect = document.getElementById('warehouseFilterType');
    const filterCountrySelect = document.getElementById('warehouseFilterCountry');
    const filterStateSelect = document.getElementById('warehouseFilterState');
    
    const searchTerm = (searchInput ? searchInput.value.trim().toLowerCase() : '');
    const filterType = (filterTypeSelect ? filterTypeSelect.value : '');
    const filterCountry = (filterCountrySelect ? filterCountrySelect.value : '');
    const filterState = (filterStateSelect ? filterStateSelect.value : '');
    
    filteredWarehouses = allWarehouses.filter(warehouse => {
        // 搜索筛选
        let matchesSearch = true;
        if (searchTerm) {
            matchesSearch = Object.values(warehouse).some(value => {
                if (value === null || value === undefined) return false;
                return String(value).toLowerCase().includes(searchTerm);
            });
        }
        
        // 地址类型筛选
        let matchesType = true;
        if (filterType) {
            matchesType = warehouse['地址类型'] === filterType;
        }
        
        // 国家代码筛选
        let matchesCountry = true;
        if (filterCountry) {
            matchesCountry = warehouse['国家代码'] === filterCountry;
        }
        
        // 州省筛选
        let matchesState = true;
        if (filterState) {
            matchesState = warehouse['州省'] === filterState;
        }
        
        return matchesSearch && matchesType && matchesCountry && matchesState;
    });
    
    // 重新渲染表格
    renderWarehouseTable();
    updateWarehouseStats();
    
    // 重置全选状态
    selectedWarehouseIds.clear();
    updateSelectAllButton();
    updateWarehouseStats();
}

/**
 * 渲染仓库表格
 */
function renderWarehouseTable() {
    const tbody = document.getElementById('warehouseTableBody');
    if (!tbody) return;
    
    if (filteredWarehouses.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center text-muted py-4">
                    <i class="bi bi-inbox"></i> 没有找到匹配的仓库
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = filteredWarehouses.map((warehouse, index) => {
        const id = `warehouse-${index}`;
        const isSelected = selectedWarehouseIds.has(id);
        
        return `
            <tr>
                <td>
                    <input type="checkbox" class="warehouse-checkbox" 
                           id="${id}" 
                           data-index="${index}"
                           ${isSelected ? 'checked' : ''}
                           onchange="toggleWarehouseSelection('${id}')">
                </td>
                <td><strong>${warehouse['仓库代码'] || ''}</strong></td>
                <td>${warehouse['地址'] || ''}</td>
                <td>${warehouse['城市'] || ''}</td>
                <td>${warehouse['州省'] || ''}</td>
                <td>${warehouse['邮编'] || ''}</td>
                <td>${warehouse['国家代码'] || ''}</td>
                <td>
                    <button class="btn btn-sm btn-outline-primary" 
                            onclick="copyWarehouseInfo(${index})" 
                            title="复制仓库信息">
                        <i class="bi bi-clipboard"></i>
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

/**
 * 更新统计信息
 */
function updateWarehouseStats() {
    const countElement = document.getElementById('warehouseCount');
    const selectedCountElement = document.getElementById('warehouseSelectedCount');
    
    if (countElement) {
        countElement.textContent = `共 ${filteredWarehouses.length} 条记录`;
    }
    
    if (selectedCountElement) {
        selectedCountElement.textContent = `已选中 ${selectedWarehouseIds.size} 条`;
    }
}

/**
 * 切换单个仓库选择状态
 */
function toggleWarehouseSelection(id) {
    const checkbox = document.getElementById(id);
    if (!checkbox) return;
    
    if (checkbox.checked) {
        selectedWarehouseIds.add(id);
    } else {
        selectedWarehouseIds.delete(id);
    }
    
    updateWarehouseStats();
    updateSelectAllButton();
}

/**
 * 全选/取消全选
 */
function toggleAllWarehouses(checkbox) {
    if (checkbox.checked) {
        filteredWarehouses.forEach((_, index) => {
            const id = `warehouse-${index}`;
            selectedWarehouseIds.add(id);
            const itemCheckbox = document.getElementById(id);
            if (itemCheckbox) {
                itemCheckbox.checked = true;
            }
        });
    } else {
        filteredWarehouses.forEach((_, index) => {
            const id = `warehouse-${index}`;
            selectedWarehouseIds.delete(id);
            const itemCheckbox = document.getElementById(id);
            if (itemCheckbox) {
                itemCheckbox.checked = false;
            }
        });
    }
    
    updateWarehouseStats();
    updateSelectAllButton();
}

/**
 * 更新全选按钮文本和图标
 */
function updateSelectAllButton() {
    const selectAllBtn = document.getElementById('selectAllWarehousesBtn');
    const selectAllBtnText = document.getElementById('selectAllBtnText');
    const selectAllCheckbox = document.getElementById('warehouseSelectAll');
    
    if (!selectAllBtn || !selectAllBtnText) return;
    
    // 检查是否所有项都被选中
    const allSelected = filteredWarehouses.length > 0 && 
        filteredWarehouses.every((_, index) => {
            const id = `warehouse-${index}`;
            return selectedWarehouseIds.has(id);
        });
    
    if (allSelected) {
        // 全部选中，显示"取消全选"
        selectAllBtnText.textContent = '取消全选';
        selectAllBtn.querySelector('i').className = 'bi bi-x-square';
        if (selectAllCheckbox) {
            selectAllCheckbox.checked = true;
        }
    } else {
        // 未全部选中，显示"全选"
        selectAllBtnText.textContent = '全选';
        selectAllBtn.querySelector('i').className = 'bi bi-check-all';
        if (selectAllCheckbox) {
            selectAllCheckbox.checked = false;
        }
    }
}

/**
 * 切换全选/取消全选（按钮点击）
 */
function toggleSelectAllWarehouses() {
    const selectAllCheckbox = document.getElementById('warehouseSelectAll');
    if (!selectAllCheckbox) return;
    
    // 检查当前是否全部选中
    const allSelected = filteredWarehouses.length > 0 && 
        filteredWarehouses.every((_, index) => {
            const id = `warehouse-${index}`;
            return selectedWarehouseIds.has(id);
        });
    
    // 切换状态
    selectAllCheckbox.checked = !allSelected;
    toggleAllWarehouses(selectAllCheckbox);
}

/**
 * 选择所有仓库（已废弃，使用toggleSelectAllWarehouses）
 */
function selectAllWarehouses() {
    toggleSelectAllWarehouses();
}

/**
 * 复制单个仓库信息
 */
function copyWarehouseInfo(index) {
    if (index < 0 || index >= filteredWarehouses.length) return;
    
    const warehouse = filteredWarehouses[index];
    const info = formatWarehouseInfo(warehouse);
    
    copyToClipboard(info, '仓库信息已复制到剪贴板');
}

/**
 * 复制选中的仓库
 */
function copySelectedWarehouses() {
    if (selectedWarehouseIds.size === 0) {
        showToast('请先选择要复制的仓库', 'warning');
        return;
    }
    
    const selectedWarehouses = [];
    selectedWarehouseIds.forEach(id => {
        const checkbox = document.getElementById(id);
        if (checkbox) {
            const index = parseInt(checkbox.getAttribute('data-index'));
            if (index >= 0 && index < filteredWarehouses.length) {
                selectedWarehouses.push(filteredWarehouses[index]);
            }
        }
    });
    
    if (selectedWarehouses.length === 0) {
        showToast('没有选中的仓库', 'warning');
        return;
    }
    
    // 格式化仓库信息
    const info = selectedWarehouses.map(warehouse => formatWarehouseInfo(warehouse)).join('\n');
    
    copyToClipboard(info, `已复制 ${selectedWarehouses.length} 条仓库信息`);
}

/**
 * 格式化仓库信息
 * 格式: 仓库代码 - 地址, 城市 州省 邮编 国家
 * 例如: RDU4 - 6835 West Buckeye Road, Phoenix AZ 85043 US
 */
function formatWarehouseInfo(warehouse) {
    const parts = [];
    
    // 仓库代码
    if (warehouse['仓库代码']) {
        parts.push(warehouse['仓库代码']);
    }
    
    // 地址部分
    const addressParts = [];
    if (warehouse['地址']) {
        addressParts.push(warehouse['地址']);
    }
    
    // 城市、州省、邮编、国家
    const locationParts = [];
    if (warehouse['城市']) {
        locationParts.push(warehouse['城市']);
    }
    if (warehouse['州省']) {
        locationParts.push(warehouse['州省']);
    }
    if (warehouse['邮编'] || warehouse['国家代邮编']) {
        const zipcode = warehouse['邮编'] || warehouse['国家代邮编'];
        locationParts.push(zipcode);
    }
    if (warehouse['国家代码']) {
        locationParts.push(warehouse['国家代码']);
    }
    
    // 组合地址部分
    if (addressParts.length > 0) {
        parts.push(addressParts.join(''));
    }
    
    // 组合位置信息
    if (locationParts.length > 0) {
        if (addressParts.length > 0) {
            parts.push(', ' + locationParts.join(' '));
        } else {
            parts.push(locationParts.join(' '));
        }
    }
    
    // 最终格式: 仓库代码 - 地址, 城市 州省 邮编 国家
    if (parts.length > 1) {
        return parts[0] + ' - ' + parts.slice(1).join('');
    } else if (parts.length === 1) {
        return parts[0];
    }
    
    return '';
}

/**
 * 复制到剪贴板
 */
function copyToClipboard(text, message) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(() => {
            showToast(message || '已复制到剪贴板', 'success');
        }).catch(err => {
            console.error('复制失败:', err);
            fallbackCopyToClipboard(text, message);
        });
    } else {
        fallbackCopyToClipboard(text, message);
    }
}

/**
 * 备用复制方法
 */
function fallbackCopyToClipboard(text, message) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    document.body.appendChild(textArea);
    textArea.select();
    
    try {
        document.execCommand('copy');
        showToast(message || '已复制到剪贴板', 'success');
    } catch (err) {
        console.error('复制失败:', err);
        showToast('复制失败，请手动复制', 'error');
    }
    
    document.body.removeChild(textArea);
}

// showToast函数已在common.js中定义，直接使用即可

/**
 * 导出仓库数据为Excel文件
 */
function exportWarehouseExcel() {
    try {
        if (!filteredWarehouses || filteredWarehouses.length === 0) {
            showToast('没有可导出的仓库数据', 'warning');
            return;
        }
        
        // 检查XLSX库是否可用
        if (typeof XLSX === 'undefined') {
            showToast('Excel导出功能需要加载xlsx库，请检查页面是否已引入', 'error');
            return;
        }
        
        // 创建工作簿
        const wb = XLSX.utils.book_new();
        
        // 准备数据
        const wsData = [];
        
        // 添加表头 - 根据实际数据字段动态生成
        const headers = [];
        if (filteredWarehouses.length > 0) {
            // 获取第一条记录的所有字段作为表头
            const firstRecord = filteredWarehouses[0];
            headers.push(...Object.keys(firstRecord));
        } else {
            // 默认表头
            headers.push('仓库代码', '地址', '城市', '州省', '邮编', '国家代码', '地址类型', '收件人公司名', '收件人', '电话');
        }
        
        wsData.push(headers);
        
        // 添加数据行
        filteredWarehouses.forEach(warehouse => {
            const row = headers.map(header => {
                const value = warehouse[header];
                // 处理null、undefined和空值
                if (value === null || value === undefined) {
                    return '';
                }
                return String(value);
            });
            wsData.push(row);
        });
        
        // 使用ExcelJS生成带字体的Excel文件
        if (typeof ExcelJS !== 'undefined') {
            const workbook = new ExcelJS.Workbook();
            const worksheet = workbook.addWorksheet('仓库数据');
            
            // 设置默认字体为微软雅黑
            worksheet.defaultFont = { name: '微软雅黑', size: 11 };
            
            // 添加数据
            wsData.forEach((row) => {
                const excelRow = worksheet.addRow(row);
                excelRow.eachCell((cell) => {
                    cell.font = { name: '微软雅黑', size: 11 };
                });
            });
            
            // 设置列宽（根据字段数量动态设置）
            const colWidths = headers.map(() => 15);
            // 特殊字段设置更宽的列
            const wideColumns = ['地址', '收件人公司名', '详细地址'];
            headers.forEach((header, index) => {
                if (wideColumns.includes(header)) {
                    colWidths[index] = 30;
                } else if (header === '仓库代码' || header === '邮编') {
                    colWidths[index] = 12;
                }
            });
            worksheet.columns = colWidths.map(width => ({ width }));
            
            // 生成文件名
            const now = new Date();
            const year = now.getFullYear();
            const month = String(now.getMonth() + 1).padStart(2, '0');
            const day = String(now.getDate()).padStart(2, '0');
            const hour = String(now.getHours()).padStart(2, '0');
            const minute = String(now.getMinutes()).padStart(2, '0');
            const fileName = `仓库数据_${year}${month}${day}_${hour}${minute}.xlsx`;
            
            // 生成并下载Excel文件
            workbook.xlsx.writeBuffer().then(function(buffer) {
                const blob = new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
                const link = document.createElement('a');
                link.href = URL.createObjectURL(blob);
                link.download = fileName;
                link.click();
                URL.revokeObjectURL(link.href);
            });
            
            showToast(`已导出 ${filteredWarehouses.length} 条仓库数据到Excel`, 'success');
        } else {
            // 降级使用XLSX
            const ws = XLSX.utils.aoa_to_sheet(wsData);
            const colWidths = headers.map(() => ({ wch: 15 }));
            const wideColumns = ['地址', '收件人公司名', '详细地址'];
            headers.forEach((header, index) => {
                if (wideColumns.includes(header)) {
                    colWidths[index] = { wch: 30 };
                } else if (header === '仓库代码' || header === '邮编') {
                    colWidths[index] = { wch: 12 };
                }
            });
            ws['!cols'] = colWidths;
            XLSX.utils.book_append_sheet(wb, ws, '仓库数据');
            const now = new Date();
            const year = now.getFullYear();
            const month = String(now.getMonth() + 1).padStart(2, '0');
            const day = String(now.getDate()).padStart(2, '0');
            const hour = String(now.getHours()).padStart(2, '0');
            const minute = String(now.getMinutes()).padStart(2, '0');
            const fileName = `仓库数据_${year}${month}${day}_${hour}${minute}.xlsx`;
            XLSX.writeFile(wb, fileName);
            showToast(`已导出 ${filteredWarehouses.length} 条仓库数据到Excel`, 'success');
        }
        
    } catch (error) {
        console.error('导出Excel失败:', error);
        showToast('导出Excel失败: ' + error.message, 'error');
    }
}

