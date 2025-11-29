// 显示工具提示的辅助函数（保留用于兼容）
function showTooltip(message, duration=2000, elementId='copyBtn') {
    const btn = document.getElementById(elementId);
    if (!btn) return;
    
    let tooltip = bootstrap.Tooltip.getInstance(btn);
    
    if (!tooltip) {
        tooltip = new bootstrap.Tooltip(btn, {
            title: message,
            trigger: 'manual'
        });
    } else {
        tooltip.setContent({'.tooltip-inner': message});
    }
    
    tooltip.show();
    setTimeout(() => tooltip.hide(), duration);
}

// 更新复制按钮的选中数量显示
function updateCopyButtonCount() {
    const selected = document.querySelectorAll('.tracking-checkbox:checked');
    const count = Array.from(selected).filter(checkbox => {
        const row = checkbox.closest('tr');
        return row && row.style.display !== 'none';
    }).length;
    
    const countBadge = document.getElementById('copy-count');
    if (countBadge) {
        if (count > 0) {
            countBadge.textContent = count;
            countBadge.classList.remove('hidden');
        } else {
            countBadge.classList.add('hidden');
        }
    }
    
    // 更新工具提示
    const copyBtn = document.getElementById('copyBtn');
    if (copyBtn) {
        const tooltip = bootstrap.Tooltip.getInstance(copyBtn);
        if (tooltip) {
            tooltip.setContent({'.tooltip-inner': count > 0 ? `复制 ${count} 个运单号` : '复制选中运单号'});
        }
    }
}

function toggleSelectAll(source) {
    const allRows = document.querySelectorAll('#logisticsTable tbody tr');
    let hasVisible = false;
    
    allRows.forEach(row => {
        if (row.style.display !== 'none') {
            const checkbox = row.querySelector('.tracking-checkbox');
            checkbox.checked = source.checked;
            hasVisible = true;
        }
    });
    
    if (!hasVisible) {
        source.checked = false;
        showToast('没有可选的运单', 'warning');
    }
    
    // 更新复制按钮计数
    updateCopyButtonCount();
}

// 清除所有选择
function clearAllSelections() {
    // 取消所有复选框的选中状态
    document.querySelectorAll('.tracking-checkbox:checked').forEach(checkbox => {
        checkbox.checked = false;
    });
    
    // 取消全选复选框
    const selectAllCheckbox = document.getElementById('selectAll');
    if (selectAllCheckbox) {
        selectAllCheckbox.checked = false;
    }
    
    // 更新复制按钮计数
    updateCopyButtonCount();
    
    // 显示提示
    showToast('已清除所有选择', 'success');
}

function copySelectedTrackingNumbers() {
    const selected = [];
    document.querySelectorAll('.tracking-checkbox:checked').forEach(checkbox => {
        // 检查父行是否可见
        const row = checkbox.closest('tr');
        if (row.style.display !== 'none') {
            selected.push(checkbox.value);
        }
    });
    
    if (selected.length === 0) {
        showToast('请至少选择一个运单号', 'warning');
        return;
    }
    
    // 更新计数
    updateCopyButtonCount();
    
    const textToCopy = selected.join(' ');
    
    // 创建临时textarea元素
    const textarea = document.createElement('textarea');
    textarea.value = textToCopy;
    textarea.style.position = 'fixed';  // 防止页面滚动
    document.body.appendChild(textarea);
    textarea.select();
    
    try {
        const successful = document.execCommand('copy');
        var copyBtn = document.getElementById('copyBtn');
        var tooltip = bootstrap.Tooltip.getInstance(copyBtn);

        // 使用 showToast 显示结果
        if (successful) {
            showToast('复制成功！', 'success');
        } else {
            showToast('复制失败', 'error');
        }

        if (successful) {
            // 获取图标元素
            const copyIcon = document.getElementById('copy-icon');

            // 改变图标为 bi-send-check
            copyIcon.classList.remove('bi-clipboard');
            copyIcon.classList.add('bi-check-all');

            // 2 秒后恢复图标
            setTimeout(() => {
                copyIcon.classList.remove('bi-check-all');
                copyIcon.classList.add('bi-clipboard');
            }, 2000);
            
            // 更新计数
            updateCopyButtonCount();
        }

    } catch (err) {
        console.error('复制失败: ', err);
        showToast('复制失败，请手动复制', 'error');
    } finally {
        document.body.removeChild(textarea);
    }
}

function filterTable(type) {
    var rows = document.querySelectorAll("#logisticsTable tbody tr");
    rows.forEach(row => {
        var days = parseInt(row.getAttribute("data-days"));
        var isWarehouse = row.getAttribute("data-warehouse") === '1';
        var eta3 = row.getAttribute("data-eta3") === '1';
        let shouldShow = false;
        if (type === "all") {
            shouldShow = true;
        } else if (type === "7") {
            shouldShow = (days > 7);
        } else if (type === "14") {
            shouldShow = (days > 14);
        } else if (type === "warehouse") {
            shouldShow = isWarehouse;
        } else if (type === "eta3") {
            shouldShow = eta3;
        }
        row.setAttribute('data-filtered', shouldShow ? 'true' : 'false');
    });
    // 重置客户和国家筛选
    document.getElementById("customerFilter").value = "";
    document.getElementById("countryFilter").value = "";
    document.getElementById("trackFilterInput").value = "";
    
    // 清除筛选缓存
    clearFilterCache();
    
    // 筛选后重置到第一页并更新分页
    currentPage = 1;
    displayPage();
    updatePagination();
}

function filterByTrackingNumbers() {
    const input = document.getElementById('trackingSearchInput').value.trim();
    if (!input) {
        filterAll();
        return;
    }
    
    const trackingNumbers = input.split(/\s+/).map(num => num.trim());
    const rows = document.querySelectorAll('#logisticsTable tbody tr');
    
    rows.forEach(row => {
        const rowTrackingNumber = row.cells[1].textContent.trim(); // 运单号在第二列（索引1）
        const shouldShow = trackingNumbers.some(num => 
            rowTrackingNumber.includes(num));
        
        row.setAttribute('data-filtered', shouldShow ? 'true' : 'false');
    });
    
    // 清除筛选缓存
    clearFilterCache();
    
    // 筛选后重置到第一页并更新分页
    currentPage = 1;
    displayPage();
    updatePagination();
}

// 分页相关变量
let currentPage = 1;
let pageSize = parseInt(localStorage.getItem('staleShipmentsPageSize')) || 10; // 从localStorage读取或使用默认值10
let filteredRowsCache = null; // 缓存筛选结果，提升性能

// 获取所有应该显示的行（基于筛选条件）
function getFilteredRows(useCache = true) {
    // 如果使用缓存且缓存存在，直接返回
    if (useCache && filteredRowsCache !== null) {
        return filteredRowsCache;
    }
    
    const allRows = document.querySelectorAll('#logisticsTable tbody tr');
    const filtered = Array.from(allRows).filter(row => {
        // 检查行是否有data-filtered属性，如果没有则默认显示
        const filtered = row.getAttribute('data-filtered');
        return filtered !== 'false';
    });
    
    // 更新缓存
    filteredRowsCache = filtered;
    return filtered;
}

// 清除筛选结果缓存
function clearFilterCache() {
    filteredRowsCache = null;
}

// 更新分页显示
function updatePagination() {
    const filteredRows = getFilteredRows();
    const totalRows = filteredRows.length;
    const totalPages = Math.ceil(totalRows / pageSize);
    
    // 更新分页信息（更详细的信息）
    const start = totalRows === 0 ? 0 : (currentPage - 1) * pageSize + 1;
    const end = Math.min(currentPage * pageSize, totalRows);
    const infoText = totalPages > 0 
        ? `显示 ${start}-${end} 条，共 ${totalRows} 条（第 ${currentPage}/${totalPages} 页）`
        : `共 ${totalRows} 条`;
    document.getElementById('paginationInfo').textContent = infoText;
    
    // 生成分页按钮
    const pagination = document.getElementById('pagination');
    pagination.innerHTML = '';
    
    if (totalPages <= 1) {
        // 即使只有一页，也显示跳转输入框（如果有数据）
        if (totalRows > 0) {
            addPageJumpInput(pagination, totalPages);
        }
        return; // 如果只有一页或没有数据，不显示分页按钮
    }
    
    // 上一页按钮
    const prevLi = document.createElement('li');
    prevLi.className = `page-item ${currentPage === 1 ? 'disabled' : ''}`;
    prevLi.innerHTML = `<a class="page-link" href="#" onclick="goToPage(${currentPage - 1}); return false;">上一页</a>`;
    pagination.appendChild(prevLi);
    
    // 页码按钮
    const maxButtons = 7; // 最多显示7个页码按钮
    let startPage = Math.max(1, currentPage - Math.floor(maxButtons / 2));
    let endPage = Math.min(totalPages, startPage + maxButtons - 1);
    
    if (endPage - startPage < maxButtons - 1) {
        startPage = Math.max(1, endPage - maxButtons + 1);
    }
    
    // 第一页
    if (startPage > 1) {
        const firstLi = document.createElement('li');
        firstLi.className = 'page-item';
        firstLi.innerHTML = `<a class="page-link" href="#" onclick="goToPage(1); return false;">1</a>`;
        pagination.appendChild(firstLi);
        
        if (startPage > 2) {
            const ellipsisLi = document.createElement('li');
            ellipsisLi.className = 'page-item disabled';
            ellipsisLi.innerHTML = '<span class="page-link">...</span>';
            pagination.appendChild(ellipsisLi);
        }
    }
    
    // 中间页码
    for (let i = startPage; i <= endPage; i++) {
        const li = document.createElement('li');
        li.className = `page-item ${i === currentPage ? 'active' : ''}`;
        li.innerHTML = `<a class="page-link" href="#" onclick="goToPage(${i}); return false;">${i}</a>`;
        pagination.appendChild(li);
    }
    
    // 最后一页
    if (endPage < totalPages) {
        if (endPage < totalPages - 1) {
            const ellipsisLi = document.createElement('li');
            ellipsisLi.className = 'page-item disabled';
            ellipsisLi.innerHTML = '<span class="page-link">...</span>';
            pagination.appendChild(ellipsisLi);
        }
        
        const lastLi = document.createElement('li');
        lastLi.className = 'page-item';
        lastLi.innerHTML = `<a class="page-link" href="#" onclick="goToPage(${totalPages}); return false;">${totalPages}</a>`;
        pagination.appendChild(lastLi);
    }
    
    // 下一页按钮
    const nextLi = document.createElement('li');
    nextLi.className = `page-item ${currentPage === totalPages ? 'disabled' : ''}`;
    nextLi.innerHTML = `<a class="page-link" href="#" onclick="goToPage(${currentPage + 1}); return false;">下一页</a>`;
    pagination.appendChild(nextLi);
    
    // 添加跳转输入框
    addPageJumpInput(pagination, totalPages);
}

// 添加跳转到指定页面的输入框
function addPageJumpInput(pagination, totalPages) {
    const jumpLi = document.createElement('li');
    jumpLi.className = 'page-item';
    jumpLi.style.marginLeft = '10px';
    jumpLi.innerHTML = `
        <div class="input-group" style="width: 120px;">
            <input type="number" class="form-control form-control-sm" 
                   id="pageJumpInput" 
                   min="1" max="${totalPages}" 
                   placeholder="跳转" 
                   style="width: 60px; text-align: center;"
                   onkeypress="if(event.key==='Enter') jumpToPage()">
            <button class="btn btn-outline-secondary btn-sm" type="button" onclick="jumpToPage()" style="padding: 0 8px;">
                <i class="bi bi-arrow-right"></i>
            </button>
        </div>
    `;
    pagination.appendChild(jumpLi);
}

// 跳转到指定页面（通过输入框）
function jumpToPage() {
    const input = document.getElementById('pageJumpInput');
    if (!input) return;
    
    const targetPage = parseInt(input.value);
    if (targetPage && targetPage >= 1) {
        goToPage(targetPage);
        input.value = ''; // 清空输入框
    }
}

// 跳转到指定页面
function goToPage(page) {
    const filteredRows = getFilteredRows();
    const totalPages = Math.ceil(filteredRows.length / pageSize);
    
    if (page < 1 || page > totalPages) {
        return;
    }
    
    currentPage = page;
    displayPage();
    updatePagination();
    
    // 滚动到表格顶部
    document.getElementById('logisticsTable').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// 显示当前页的数据
function displayPage() {
    const filteredRows = getFilteredRows();
    const start = (currentPage - 1) * pageSize;
    const end = start + pageSize;
    
    // 先隐藏所有行
    const allRows = document.querySelectorAll('#logisticsTable tbody tr');
    allRows.forEach(row => {
        row.style.display = 'none';
    });
    
    // 显示当前页的行
    filteredRows.forEach((row, index) => {
        if (index >= start && index < end) {
            row.style.display = '';
        }
    });
}

// 改变每页显示数量
function changePageSize() {
    const select = document.getElementById('pageSizeSelect');
    pageSize = parseInt(select.value);
    
    // 保存到localStorage
    localStorage.setItem('staleShipmentsPageSize', pageSize.toString());
    
    currentPage = 1; // 重置到第一页
    displayPage();
    updatePagination();
}

// 防抖函数
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function filterAll() {
    document.getElementById('selectAll').checked = false; // 当筛选条件变化时，自动取消全选状态
    // 取消所有已选中的复选框（包括不可见的）
    document.querySelectorAll('.tracking-checkbox:checked').forEach(checkbox => {
        checkbox.checked = false;
    });
    
    // 更新复制按钮计数
    updateCopyButtonCount();

    const customerFilter = document.getElementById('customerFilter').value.toLowerCase();
    const countryFilter = document.getElementById('countryFilter').value.toLowerCase();
    const channelFilter = document.getElementById('channelFilter').value.toLowerCase();
    const carrierFilter = document.getElementById('carrierFilter').value.toLowerCase();
    const trackFilter = document.getElementById('trackFilterInput').value.toLowerCase();
    const problemFilter = document.getElementById('problemFilter').value;
    const statusFilter = document.getElementById('statusFilter').value;
    const channelFilterValue = document.getElementById('channelFilter').value;

    const rows = document.querySelectorAll('#logisticsTable tbody tr');
    rows.forEach(row => {
        const customer = row.getAttribute('data-customer').toLowerCase();
        const country = row.getAttribute('data-country').toLowerCase();
        const channel = row.getAttribute('data-channel').toLowerCase();
        const trackText = row.getAttribute('data-track').toLowerCase();
        const isProblem = row.getAttribute('data-problem') === '1';
        const rowStatus = row.getAttribute('data-status');
        const carrier = row.getAttribute('data-carrier').toLowerCase();

        // 综合所有筛选条件
        const showRow = 
            (customerFilter === '' || customer.includes(customerFilter)) &&
            (countryFilter === '' || country.includes(countryFilter)) &&
            (channelFilterValue === '' || 
             channelFilterValue === 'all_channels' ||
             channelFilterValue.split(',').some(filterChannel => channel.includes(filterChannel.toLowerCase()))) &&
            (carrierFilter === '' || carrier.includes(carrierFilter)) &&
            (trackFilter === '' || trackText.includes(trackFilter)) &&
            (problemFilter === 'all' || 
             (problemFilter === 'normal' && !isProblem) || 
             (problemFilter === 'problem' && isProblem))&&
                (!statusFilter || rowStatus === statusFilter);

        row.setAttribute('data-filtered', showRow ? 'true' : 'false');

        document.getElementById('trackingSearchInput').value = '';
    });
    
    // 清除筛选缓存
    clearFilterCache();
    
    // 筛选后重置到第一页并更新分页
    currentPage = 1;
    displayPage();
    updatePagination();
}

// 创建防抖的筛选函数
const debouncedFilterAll = debounce(filterAll, 300);

// 键盘快捷键支持
document.addEventListener('keydown', function(e) {
    // 只在没有输入框聚焦时响应快捷键
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') {
        return;
    }
    
    // Ctrl/Cmd + 左箭头：上一页
    if ((e.ctrlKey || e.metaKey) && e.key === 'ArrowLeft') {
        e.preventDefault();
        goToPage(currentPage - 1);
    }
    // Ctrl/Cmd + 右箭头：下一页
    else if ((e.ctrlKey || e.metaKey) && e.key === 'ArrowRight') {
        e.preventDefault();
        goToPage(currentPage + 1);
    }
    // Ctrl/Cmd + Home：第一页
    else if ((e.ctrlKey || e.metaKey) && e.key === 'Home') {
        e.preventDefault();
        goToPage(1);
    }
    // Ctrl/Cmd + End：最后一页
    else if ((e.ctrlKey || e.metaKey) && e.key === 'End') {
        e.preventDefault();
        const filteredRows = getFilteredRows();
        const totalPages = Math.ceil(filteredRows.length / pageSize);
        goToPage(totalPages);
    }
});

document.addEventListener('DOMContentLoaded', function () {
    const buttons = document.querySelectorAll('button[data-bs-toggle="collapse"]');
    buttons.forEach(btn => {
        const target = document.querySelector(btn.getAttribute('data-bs-target'));
        if (!target) return;
        target.addEventListener('show.bs.collapse', () => btn.textContent = '收起');
        target.addEventListener('hide.bs.collapse', () => btn.textContent = '展开更多');
    });
    // 初始化所有悬浮按钮的tooltip
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl, {
            trigger: 'manual'
        });
    });
    
    // 初始化：所有行默认应该显示
    const allRows = document.querySelectorAll('#logisticsTable tbody tr');
    allRows.forEach(row => {
        row.setAttribute('data-filtered', 'true');
    });
    
    // 从localStorage恢复每页显示数量
    const savedPageSize = localStorage.getItem('staleShipmentsPageSize');
    if (savedPageSize) {
        pageSize = parseInt(savedPageSize);
        const pageSizeSelect = document.getElementById('pageSizeSelect');
        if (pageSizeSelect) {
            pageSizeSelect.value = savedPageSize;
        }
    }
    
    // 为所有复选框添加变化监听，实时更新计数
    document.addEventListener('change', function(e) {
        if (e.target.classList.contains('tracking-checkbox')) {
            updateCopyButtonCount();
        }
    });
    
    // 初始化分页
    displayPage();
    updatePagination();
    
    // 初始化复制按钮计数
    updateCopyButtonCount();
});

