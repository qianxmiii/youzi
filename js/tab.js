/**
 * tab.js 标签相关功能
 */

 /**
  * Tab1 - 常用功能
  */

// 获取所有术语
const allTerms = Object.values(window.logisticsData.termsByCategory).flat();

/**
 * 通用术语搜索函数
 * @param {Object} term - 术语对象
 * @param {string} keyword - 搜索关键字
 * @returns {boolean} - 是否匹配
 */
function searchInTerm(term, keyword) {
    if (!keyword) return true;
    
    const lowerKeyword = keyword.toLowerCase();
    
    // 搜索中文名称
    if (term.chinese.toLowerCase().includes(lowerKeyword)) return true;
    
    // 搜索英文名称
    if (term.english.toLowerCase().includes(lowerKeyword)) return true;
    
    // 搜索描述内容
    if (term.definition && term.definition.toLowerCase().includes(lowerKeyword)) return true;
    
    // 搜索流程步骤内容
    if (term.type === 'process' && term.steps) {
        return term.steps.some(step => 
            step.title.toLowerCase().includes(lowerKeyword) || 
            step.description.toLowerCase().includes(lowerKeyword)
        );
    }
    
    // 搜索标签
    if (term.tags && term.tags.some(tag => tag.toLowerCase().includes(lowerKeyword))) return true;
    
    return false;
}

 // 术语统计相关变量
let totalTermsCount = 0;
let filteredTermsCount = 0;

// 术语视图模式
let termViewMode = 'list'; // 'list' 或 'grid'

// 切换术语视图模式
function switchTermView(view) {
    termViewMode = view;
    
    // 更新按钮状态
    document.getElementById('termListView').classList.toggle('active', view === 'list');
    document.getElementById('termGridView').classList.toggle('active', view === 'grid');
    
    // 重新渲染术语列表
    const searchKeyword = document.getElementById('searchInput').value.toLowerCase();
    const activeCategory = document.querySelector('.category-buttons .btn.active')?.textContent || '全部';
    const filteredTerms = getFilteredTerms(searchKeyword, activeCategory);
    renderTerms(filteredTerms);
}

function renderTerms(filteredTerms = allTerms) {
    const termList = document.getElementById("termList");
    termList.innerHTML = ''; // 清空列表

    // 更新术语统计
    totalTermsCount = allTerms.length;
    filteredTermsCount = filteredTerms.length;
    updateTermsStatistics();

    if (filteredTerms.length === 0) {
        document.getElementById("noResults").style.display = 'block';
    } else {
        document.getElementById("noResults").style.display = 'none';

        // 根据视图模式设置容器样式
        if (termViewMode === 'grid') {
            termList.className = 'row';
        } else {
            termList.className = 'term-list';
        }

        // 渲染所有术语（无限滚动）
        filteredTerms.forEach(term => {
            const card = document.createElement('div');
            
            // 检查是否为流程类型术语
            if (term.type === 'process' && term.steps) {
                // 流程步骤卡片 - 可折叠设计
                card.className = 'col-md-4 mb-3';
                card.innerHTML = `
                    <div class="card h-100 process-card-compact" data-process-id="${term.chinese}">
                        <div class="card-body">
                            <div class="process-header-compact">
                                <h6 class="card-title process-title-compact">
                                    <i class="bi bi-diagram-3 process-icon"></i>
                                    ${term.chinese}
                                </h6>
                            </div>
                            <p class="card-text process-subtitle-compact">
                                ${term.english}
                                <span class="copy-btn" onclick="copyTerm(this, '${term.english}')">
                                    <i class="bi bi-clipboard"></i>
                                </span>
                            </p>
                            <div class="process-summary process-summary-clickable" onclick="toggleProcessSteps(this)" data-bs-toggle="tooltip" data-bs-title="点击查看详细流程">
                                <small class="text-muted">
                                    <i class="bi bi-list-ol"></i>
                                    共 ${term.steps.length} 个步骤
                                    <i class="bi bi-chevron-down process-chevron"></i>
                                </small>
                            </div>
                            <div class="process-steps-detail" style="display: none;">
                                ${term.steps.map(step => `
                                    <div class="step-item-compact">
                                        <div class="step-number-compact">${step.step}</div>
                                        <div class="step-content-compact">
                                            <h6 class="step-title-compact">
                                                <i class="bi ${step.icon} step-icon-compact"></i>
                                                ${step.title}
                                            </h6>
                                            <p class="step-description-compact">${step.description}</p>
                                        </div>
                                    </div>
                                `).join('')}
                            </div>
                            <div class="tags">
                                ${term.tags.map(tag => {
                                    const color = tagColors[tag] || "#6c757d";
                                    return `<span class="badge" style="background-color: ${color}; color: white;">${tag}</span>`;
                                }).join('')}
                            </div>
                        </div>
                    </div>
                `;
            } else if (termViewMode === 'grid') {
                // 网格样式 - 支持可展开卡片设计
                card.className = 'col-md-4 mb-3';
                const hasDefinition = term.definition && typeof term.definition === 'string' && term.definition.trim() !== '';
                card.innerHTML = `
                    <div class="card h-100 term-card-grid">
                        <div class="card-body">
                            <div class="term-header-grid">
                                <h6 class="card-title" data-bs-toggle="tooltip" data-bs-title="${(typeof term.definition === 'string' ? term.definition : '暂无释义').replace(/"/g, '&quot;')}">${term.chinese}</h6>
                                ${hasDefinition ? `<button class="btn btn-sm btn-outline-info definition-toggle-grid" onclick="toggleDefinitionGrid(this)" data-bs-toggle="tooltip" data-bs-title="点击查看详细说明">
                                    <i class="bi bi-info-circle"></i>
                                </button>` : ''}
                            </div>
                            <p class="card-text" data-bs-toggle="tooltip" data-bs-title="${(typeof term.definition === 'string' ? term.definition : '暂无释义').replace(/"/g, '&quot;')}">
                                ${term.english}
                                <span class="copy-btn" onclick="copyTerm(this, '${term.english}')">
                                    <i class="bi bi-clipboard"></i>
                                </span>
                            </p>
                            ${hasDefinition ? `<div class="term-definition-grid" style="display: none;">
                                <div class="definition-content-grid">
                                    <strong>详细说明：</strong>
                                    <p>${typeof term.definition === 'string' ? term.definition : '暂无详细说明'}</p>
                                </div>
                            </div>` : ''}
                            <div class="tags">
                                ${term.tags.map(tag => {
                                    const color = tagColors[tag] || "#6c757d"; // 默认灰色
                                    return `<span class="badge" style="background-color: ${color}; color: white;">${tag}</span>`;
                                }).join('')}
                            </div>
                        </div>
                    </div>
                `;
            } else {
                // 列表样式 - 直接显示释义内容，适合批量复习
                card.className = 'term-card';
                card.setAttribute('data-term', term.chinese);
                const hasDefinition = term.definition && typeof term.definition === 'string' && term.definition.trim() !== '';
                card.innerHTML = `
                    <div class="card-body">
                        <div class="term-header-list">
                            <h5>${term.chinese}</h5>
                            <p class="term-english">
                                ${term.english}
                                <span class="copy-btn" onclick="copyTerm(this, '${term.english}')">
                                    <i class="bi bi-clipboard"></i>
                                </span>
                            </p>
                        </div>
                        ${hasDefinition ? `<div class="term-definition-list">
                            <div class="definition-content-list">
                                <strong>释义：</strong>
                                <span>${typeof term.definition === 'string' ? term.definition : '暂无详细说明'}</span>
                            </div>
                        </div>` : ''}
                        <div class="tags">
                            ${term.tags.map(tag => {
                                const color = tagColors[tag] || "#6c757d"; // 默认灰色
                                return `<span class="badge" style="background-color: ${color}; color: white;">${tag}</span>`;
                            }).join('')}
                        </div>
                    </div>
                `;
            }
            
            termList.appendChild(card);
        });

        // 初始化 Tooltip
        const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
        const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => {
            // 先销毁已存在的tooltip实例
            const existingTooltip = bootstrap.Tooltip.getInstance(tooltipTriggerEl);
            if (existingTooltip) {
                existingTooltip.dispose();
            }
            
            // 确保元素有正确的属性
            const title = tooltipTriggerEl.getAttribute('data-bs-title');
            if (!title) {
                return null;
            }
            
            try {
                return new bootstrap.Tooltip(tooltipTriggerEl, {
                    trigger: 'hover focus',
                    placement: 'top',
                    delay: { show: 500, hide: 100 },
                    html: false
                });
            } catch (error) {
                console.error('Error creating tooltip:', error, tooltipTriggerEl);
                return null;
            }
        }).filter(tooltip => tooltip !== null);
    }
}

// 更新术语统计
function updateTermsStatistics() {
    const termsCountElement = document.getElementById('termsCount');
    if (termsCountElement) {
        if (filteredTermsCount === totalTermsCount) {
            termsCountElement.textContent = `共 ${totalTermsCount} 个术语`;
        } else {
            termsCountElement.textContent = `共找到 ${filteredTermsCount} 个术语（共 ${totalTermsCount} 个）`;
        }
    }
}

// 回到顶部功能
function scrollToTop() {
    const modalBody = document.querySelector('#termModal .modal-body');
    if (modalBody) {
        modalBody.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    }
}

// 监听滚动事件，显示/隐藏回到顶部按钮
function initBackToTopButton() {
    const modalBody = document.querySelector('#termModal .modal-body');
    const backToTopBtn = document.getElementById('backToTop');
    
    if (modalBody && backToTopBtn) {
        modalBody.addEventListener('scroll', function() {
            if (modalBody.scrollTop > 300) {
                backToTopBtn.style.display = 'block';
            } else {
                backToTopBtn.style.display = 'none';
            }
        });
    }
}

// 切换列表视图中的定义显示
function toggleDefinition(button) {
    const card = button.closest('.term-card');
    const definition = card.querySelector('.term-definition');
    const icon = button.querySelector('i');
    
    if (definition.style.display === 'none') {
        definition.style.display = 'block';
        icon.className = 'bi bi-chevron-up';
        button.setAttribute('data-bs-title', '点击收起详细说明');
    } else {
        definition.style.display = 'none';
        icon.className = 'bi bi-info-circle';
        button.setAttribute('data-bs-title', '点击查看详细说明');
    }
    
    // 重新初始化tooltip
    const tooltip = bootstrap.Tooltip.getInstance(button);
    if (tooltip) {
        tooltip.dispose();
    }
    new bootstrap.Tooltip(button);
}

// 切换网格视图中的定义显示
function toggleDefinitionGrid(button) {
    const card = button.closest('.term-card-grid');
    const definition = card.querySelector('.term-definition-grid');
    const icon = button.querySelector('i');
    
    if (definition.style.display === 'none') {
        definition.style.display = 'block';
        icon.className = 'bi bi-chevron-up';
        button.setAttribute('data-bs-title', '点击收起详细说明');
        
        // 调整卡片高度以适应展开内容
        card.style.height = 'auto';
    } else {
        definition.style.display = 'none';
        icon.className = 'bi bi-info-circle';
        button.setAttribute('data-bs-title', '点击查看详细说明');
        
        // 恢复卡片高度
        card.style.height = '100%';
    }
    
    // 重新初始化tooltip
    const tooltip = bootstrap.Tooltip.getInstance(button);
    if (tooltip) {
        tooltip.dispose();
    }
    new bootstrap.Tooltip(button);
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

 }

 // 初始化搜索功能
function initSearchFunction() {
    const searchInput = document.getElementById('searchInput');
    if (!searchInput) {
        console.warn('搜索输入框未找到，将在DOM加载完成后重试');
        return;
    }
    
    searchInput.addEventListener('input', function () {
        const keyword = this.value.trim();
        const filteredTerms = allTerms.filter(term => searchInTerm(term, keyword));
        renderTerms(filteredTerms);
    });
}

 // 清除搜索
 function clearSearch() {
     searchInput.value = '';
     
     // 重置分类选择到"全部"
     document.querySelectorAll('.category-buttons .btn').forEach(btn => {
         btn.classList.remove('active');
     });
     // 激活"全部"分类按钮
     const allCategoryBtn = document.querySelector('.category-buttons .btn[data-category="全部"]');
     if (allCategoryBtn) {
         allCategoryBtn.classList.add('active');
     }
     
     // 清除所有选中的标签
     selectedTags = [];
     updateTagButtonStyles();
     updateClearTagsButton();
     
     renderTerms(allTerms); // 重置为全部术语
 }


 // 获取当前筛选后的术语列表
 function getFilteredTerms() {
     const searchKeyword = document.getElementById('searchInput').value.trim();
     const activeCategory = document.querySelector('.category-buttons .btn.active').textContent;

     if (activeCategory === '全部') {
         return allTerms.filter(term => searchInTerm(term, searchKeyword));
     } else {
         return (window.logisticsData.termsByCategory[activeCategory] || []).filter(term => searchInTerm(term, searchKeyword));
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
    
    // 更新清除按钮的显示状态
    updateClearTagsButton();
}

// 更新标签按钮样式
function updateTagButtonStyles() {
    const tagButtons = document.querySelectorAll("#termTagBtns button");
    tagButtons.forEach(button => {
        const dataTag = button.getAttribute("data-tag");
        
        // 处理"全部"按钮
        if (dataTag === "all") {
            if (selectedTags.length === 0) {
                // 没有选中任何标签时，"全部"按钮保持蓝色高亮
                button.style.color = "#fff";
                button.style.borderColor = "#007bff";
                button.style.backgroundColor = "#007bff";
                button.style.fontWeight = "bold";
            } else {
                // 有选中标签时，"全部"按钮变为普通样式
                button.style.color = "#333";
                button.style.borderColor = "#ccc";
                button.style.backgroundColor = "#f8f9fa";
                button.style.fontWeight = "normal";
            }
        } else {
            // 处理其他标签按钮
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

    // 添加"全部"选项按钮
    const allButton = document.createElement("button");
    allButton.className = "btn btn-sm me-2 mb-2";
    allButton.innerText = "全部";
    allButton.setAttribute("data-tag", "all");
    
    // 全部按钮的特殊样式
    allButton.style.color = "#fff";
    allButton.style.borderColor = "#007bff";
    allButton.style.backgroundColor = "#007bff";
    allButton.style.fontWeight = "bold";
    
    allButton.onclick = () => clearAllTags();
    tagButtonsContainer.appendChild(allButton);

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
    
    // 更新清除按钮的显示状态
    updateClearTagsButton();
}

// 清除所有选中的标签
function clearAllTags() {
    selectedTags = [];
    updateTagButtonStyles();
    filterTermsByTags();
    updateClearTagsButton();
}

// 更新清除标签按钮的显示状态
function updateClearTagsButton() {
    const clearBtn = document.getElementById('clearTagsBtn');
    if (clearBtn) {
        if (selectedTags.length > 0) {
            clearBtn.style.display = 'block';
        } else {
            clearBtn.style.display = 'none';
        }
    }
}




// 高亮关键词
function highlightKeyword(element, keyword) {
    const regex = new RegExp(keyword, 'gi');
    element.innerHTML = element.innerHTML.replace(regex, match => `<span class="highlight">${match}</span>`);
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
    if (window.data && window.data.quickReplies) {
        window.data.quickReplies.forEach(category => {
            const button = document.createElement("button");
            button.className = "btn btn-outline-primary me-2 mb-2";
            button.textContent = category.category;
            button.onclick = () => loadQuickReplies(category.category);
            categoriesContainer.appendChild(button);
        });
    }

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

    if (!window.data || !window.data.quickReplies) {
        console.error('快捷回复数据未加载');
        return;
    }

    if (selectedCategory === "全部") {
        // 加载所有分类的回复
        window.data.quickReplies.forEach(category => {
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
        const selectedCategoryData = window.data.quickReplies.find(category => category.category === selectedCategory);
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
    if (window.data && window.data.quickReplies) {
        window.data.quickReplies.forEach(category => {
            allReplies.push(...category.replies);
        });
    }

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

        // 显示成功提示tooltip
        showCopyTooltip(button, '复制成功！', 'success');

        // 2 秒后恢复按钮样式
        setTimeout(() => {
            button.innerHTML = '<i class="bi bi-clipboard"></i>';
            button.classList.remove('copied');
            hideCopyTooltip(button);
        }, 2000);
    }).catch(err => {
        console.error('复制失败：', err);
        
        // 显示失败提示tooltip
        showCopyTooltip(button, '复制失败，请手动复制', 'error');
        
        // 3 秒后隐藏tooltip
        setTimeout(() => {
            hideCopyTooltip(button);
        }, 3000);
    });
}

/* 显示复制提示tooltip */
function showCopyTooltip(button, message, type) {
    // 移除已存在的tooltip
    hideCopyTooltip(button);
    
    // 创建tooltip元素
    const tooltip = document.createElement('div');
    tooltip.className = `copy-tooltip copy-tooltip-${type}`;
    tooltip.textContent = message;
    
    // 添加到按钮的父元素
    const parent = button.closest('.card-body') || button.parentElement;
    parent.style.position = 'relative';
    parent.appendChild(tooltip);
    
    // 计算位置
    const buttonRect = button.getBoundingClientRect();
    const parentRect = parent.getBoundingClientRect();
    
    tooltip.style.left = `${buttonRect.left - parentRect.left + buttonRect.width / 2}px`;
    tooltip.style.top = `${buttonRect.top - parentRect.top - 35}px`;
    
    // 添加显示动画
    setTimeout(() => {
        tooltip.classList.add('show');
    }, 10);
}

/* 隐藏复制提示tooltip */
function hideCopyTooltip(button) {
    const parent = button.closest('.card-body') || button.parentElement;
    const existingTooltip = parent.querySelector('.copy-tooltip');
    if (existingTooltip) {
        existingTooltip.classList.remove('show');
        setTimeout(() => {
            if (existingTooltip.parentNode) {
                existingTooltip.parentNode.removeChild(existingTooltip);
            }
        }, 200);
    }
}

/**
 * Tab 3 - 成本计算
 */

// 识别地址、箱数、重量、体积信息
function parseCalTabCargoInfo() {
    const input = document.getElementById("cargo-input").value.trim();
    // 使用正则表达式解析箱数、重量、体积、尺寸
    const volumeRegex = /([\d.]+)\s*(cbm|方)/i;
    const weightRegex = /([\d.]+)\s*(kg|kgs|lb|lbs|磅)/i;
    const quantityRegex = /(\d+)\s*(X|\s*)\s*(BOX|BOXES|Boxs|CARTON|CARTONS|ctn|ctns|件|箱|pal|pallets|托)/i;
    // 尺寸识别正则表达式，支持各种分隔符和单位
    const dimensionRegex = /(\d+(?:\.\d+)?)\s*[*xX×]\s*(\d+(?:\.\d+)?)\s*[*xX×]\s*(\d+(?:\.\d+)?)\s*(cm|mm|MM|m|M|米|inch|in|英寸)?/i;
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

    // 提取尺寸信息
    const dimensionMatch = input.match(dimensionRegex);
    let length = 0, width = 0, height = 0;
    if (dimensionMatch) {
        length = parseFloat(dimensionMatch[1]);
        width = parseFloat(dimensionMatch[2]);
        height = parseFloat(dimensionMatch[3]);
        const unit = (dimensionMatch[4] || '').toLowerCase();
        
        // 如果是英寸单位，转换为厘米
        if (unit === 'inch' || unit === 'in' || unit === '英寸') {
            length *= 2.54;
            width *= 2.54;
            height *= 2.54;
        }
        // 如果是毫米单位，转换为厘米
        else if (unit === 'mm') {
            length /= 10;
            width /= 10;
            height /= 10;
        }
        // 如果是米单位，转换为厘米
        else if (unit === 'm' || unit === '米') {
            length *= 100;
            width *= 100;
            height *= 100;
        }
        
        // 如果识别到尺寸但没有识别到体积，自动计算体积
        if (volume === 0 && quantity > 0) {
            volume = (length * width * height * quantity) / 1000000; // 转换为cbm
        }
    }

    document.getElementById('t_quantity').value = quantity;
    document.getElementById('t_weight').value = Math.ceil(weight);
    document.getElementById('t_volume').value = new Decimal(volume).toDecimalPlaces(2, Decimal.ROUND_UP);

    // 更新所有包税成本计算行的数据
    const tbody = document.getElementById('DDPTableBody');
    if (tbody) {
        const rows = tbody.querySelectorAll('tr');
        rows.forEach((row, index) => {
            const quantityEl = document.getElementById('tp_quantity_' + index);
            const weightEl = document.getElementById('tp_weight_' + index);
            const volumeEl = document.getElementById('tp_volume_' + index);
            if (quantityEl) quantityEl.value = quantity;
            if (weightEl) weightEl.value = Math.ceil(weight);
            if (volumeEl) volumeEl.value = new Decimal(volume).toDecimalPlaces(2, Decimal.ROUND_UP);
        });
    }
    
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

// 切换按方包税
function toggleByVolumeTaxIncluded() {
    const checkbox = document.getElementById('t_by-volume-tax-included');
    const inputField = document.getElementById('t_by-volume-tax-included-value');
    const goodsValueField = document.getElementById('t_goods-value');
    
    if (checkbox.checked) {
        // 显示输入框
        inputField.style.display = 'block';
        // 货值设为0
        goodsValueField.value = '0';
        // 禁用货值输入框
        goodsValueField.disabled = true;
    } else {
        // 隐藏输入框
        inputField.style.display = 'none';
        // 恢复货值输入框
        goodsValueField.disabled = false;
        // 如果货值是0，恢复为默认值167
        if (goodsValueField.value === '0' || goodsValueField.value === '') {
            goodsValueField.value = '167';
        }
    }
    // 重新计算
    calculateCostDDU();
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
    // 检查是否选中按方包税
    const byVolumeTaxIncluded = document.getElementById('t_by-volume-tax-included').checked;
    let actualPricePerCbm = pricePerCbm;
    
    if (byVolumeTaxIncluded) {
        // 实际按方包税 = 按方表价 + 输入框中的值
        const additionalValue = new Decimal(parseFloat(document.getElementById('t_by-volume-tax-included-value').value) || 0);
        actualPricePerCbm = pricePerCbm.plus(additionalValue);
    }
    
    const forwardingCost = actualPricePerCbm.mul(chargeVolume);
    document.getElementById('t_freight-forwarding-cost').textContent = forwardingCost.toDecimalPlaces(2, Decimal.ROUND_UP);

    // 计算税金 关税加征20%
    const taxAmount = goodsValue.mul(taxRate.plus(20).dividedBy(100).mul(volume).mul(cost_exchange_rate));
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

// 计算包税成本（计算所有行，兼容旧代码）
function calculateCostDDP() {
    const tbody = document.getElementById('DDPTableBody');
    if (!tbody) return;
    const rows = tbody.querySelectorAll('tr');
    rows.forEach((row, index) => {
        calculateCostDDPRow(index);
    });
}

// 计算包税成本（支持多行）
function calculateCostDDPRow(rowIndex) {
    try {
        // 获取输入值
        const quantityEl = document.getElementById('tp_quantity_' + rowIndex);
        const weightEl = document.getElementById('tp_weight_' + rowIndex);
        const volumeEl = document.getElementById('tp_volume_' + rowIndex);
        const pricePerKgEl = document.getElementById('tp_price-per-kg_' + rowIndex);
        const deliveryFeeUSDEl = document.getElementById('tp_delivery-fee-usd_' + rowIndex);
        const deliveryFeeRMBEl = document.getElementById('tp_delivery-fee-rmb_' + rowIndex);
        
        if (!weightEl || !volumeEl || !pricePerKgEl || !deliveryFeeUSDEl || !deliveryFeeRMBEl) {
            console.error('包税成本计算：找不到必要的元素，rowIndex=' + rowIndex);
            return;
        }
        
        const quantity = parseFloat(quantityEl ? quantityEl.value : 0) || 0;
        const weight = new Decimal(parseFloat(weightEl.value) || 0);
        const volume = new Decimal(parseFloat(volumeEl.value) || 0);
        const pricePerKg = new Decimal(parseFloat(pricePerKgEl.value) || 0);
        const deliveryFeeUSD = new Decimal(parseFloat(deliveryFeeUSDEl.value) || 0);
        const deliveryFeeRMB = new Decimal(parseFloat(deliveryFeeRMBEl.value) || 0);

        // 计算计费重
        let chargeWeight = Decimal.max(weight,volume.mul(1000000).dividedBy(6000)).toDecimalPlaces(0, Decimal.ROUND_UP);
        const chargeWeightEl = document.getElementById('tp_charge-weight_' + rowIndex);
        if (chargeWeightEl) chargeWeightEl.textContent = chargeWeight;

        // 计算计费方
        const weightRatioEl = document.getElementById('weight-ratio-select');
        const weightRatio = weightRatioEl ? weightRatioEl.value : '363';
        let chargeVolume;
        if (weightRatio === 'actual') {
            // 实际方：只使用体积
            chargeVolume = volume;
        } else {
            // 使用选择的重量比计算
            const ratio = parseFloat(weightRatio);
            chargeVolume = Decimal.max(volume, weight.dividedBy(ratio).toDecimalPlaces(2, Decimal.ROUND_UP));
        }
        const chargeCbmEl = document.getElementById('tp_charge-cbm_' + rowIndex);
        if (chargeCbmEl) chargeCbmEl.textContent = chargeVolume.toDecimalPlaces(2, Decimal.ROUND_UP);

        // 计算泡比 泡比 = 实重 / 体积
        let volumeRatio = new Decimal(0);
        if (!weight.equals(0) && !volume.equals(0)) {
            volumeRatio = weight.dividedBy(volume);
        }
        const volumeRatioEl = document.getElementById('tp_volume-ratio_' + rowIndex);
        if (volumeRatioEl) volumeRatioEl.textContent = volumeRatio.toFixed(0);

        // 计算头程费用
        const forwardingCost = pricePerKg.mul(chargeWeight);
        const forwardingCostEl = document.getElementById('tp_freight-forwarding-cost_' + rowIndex);
        if (forwardingCostEl) forwardingCostEl.textContent = forwardingCost.toDecimalPlaces(2, Decimal.ROUND_UP);

        // 计算派送费 (RMB)
        const deliveryFeeTran = deliveryFeeUSD.mul(exchange_rate);
        const totalDeliveryFee = new Decimal(deliveryFeeRMB.add(deliveryFeeTran).toFixed(2));
        const deliveryFeeFinalEl = document.getElementById('tp_delivery-fee-final_' + rowIndex);
        if (deliveryFeeFinalEl) deliveryFeeFinalEl.textContent = totalDeliveryFee;

        // 计算总成本
        const totalCost = forwardingCost.plus(totalDeliveryFee);
        const totalCostEl = document.getElementById('tp_total-cost_' + rowIndex);
        if (totalCostEl) totalCostEl.textContent = totalCost.toDecimalPlaces(0, Decimal.ROUND_UP);
        
        // 计算单价 (RMB/cbm)
        const unitPriceCbm = chargeVolume.greaterThan(0) ? totalCost.dividedBy(chargeVolume) : new Decimal(0);
        const unitPriceCbmEl = document.getElementById('tp_unit-price-cbm_' + rowIndex);
        if (unitPriceCbmEl) unitPriceCbmEl.textContent = unitPriceCbm.toDecimalPlaces(0, Decimal.ROUND_UP);

        // 计算单价 (RMD/kg)
        const unitPriceKg = chargeWeight.greaterThan(0) ? totalCost.dividedBy(chargeWeight) : new Decimal(0);
        const unitPriceKgEl = document.getElementById('tp_unit-price-kg_' + rowIndex);
        if (unitPriceKgEl) unitPriceKgEl.textContent = unitPriceKg.toFixed(2);
    } catch (error) {
        console.error('包税成本计算错误，rowIndex=' + rowIndex, error);
    }
}

// 新增包税成本计算行
function addDDPRow() {
    const tbody = document.getElementById('DDPTableBody');
    const rows = tbody.querySelectorAll('tr');
    const newRowIndex = rows.length;
    
    // 获取最后一行的数据作为模板
    const lastRow = rows[rows.length - 1];
    const lastRowIndex = parseInt(lastRow.getAttribute('data-row-index'));
    
    // 创建新行
    const newRow = lastRow.cloneNode(true);
    newRow.setAttribute('data-row-index', newRowIndex);
    
    // 更新所有ID和事件处理
    const inputs = newRow.querySelectorAll('input');
    inputs.forEach(input => {
        const oldId = input.id;
        if (oldId) {
            const newId = oldId.replace('_' + lastRowIndex, '_' + newRowIndex);
            input.id = newId;
            input.value = ''; // 清空输入值
            input.oninput = function() { calculateCostDDPRow(newRowIndex); };
        }
    });
    
    const spans = newRow.querySelectorAll('span');
    spans.forEach(span => {
        const oldId = span.id;
        if (oldId) {
            const newId = oldId.replace('_' + lastRowIndex, '_' + newRowIndex);
            span.id = newId;
            span.textContent = '0.00';
            // 确保单价列保持加粗样式
            if (newId.includes('tp_unit-price-cbm_') || newId.includes('tp_unit-price-kg_')) {
                span.classList.add('fw-bold');
            }
        }
    });
    
    // 更新操作按钮
    const buttons = newRow.querySelectorAll('button');
    buttons.forEach(button => {
        const onclick = button.getAttribute('onclick');
        if (onclick) {
            if (onclick.includes('copyDDPRow')) {
                button.setAttribute('onclick', 'copyDDPRow(' + newRowIndex + ')');
            } else if (onclick.includes('deleteDDPRow')) {
                button.setAttribute('onclick', 'deleteDDPRow(' + newRowIndex + ')');
                button.disabled = false; // 新行可以删除
            }
        }
    });
    
    tbody.appendChild(newRow);
}

// 复制包税成本计算行
function copyDDPRow(rowIndex) {
    const tbody = document.getElementById('DDPTableBody');
    const rows = tbody.querySelectorAll('tr');
    const sourceRow = rows[rowIndex];
    const newRowIndex = rows.length;
    
    // 创建新行
    const newRow = sourceRow.cloneNode(true);
    newRow.setAttribute('data-row-index', newRowIndex);
    
    // 更新所有ID和事件处理，并复制值
    const inputs = newRow.querySelectorAll('input');
    inputs.forEach(input => {
        const oldId = input.id;
        if (oldId) {
            const newId = oldId.replace('_' + rowIndex, '_' + newRowIndex);
            input.id = newId;
            // 复制输入值
            const sourceInput = document.getElementById(oldId);
            if (sourceInput) {
                input.value = sourceInput.value;
            }
            input.oninput = function() { calculateCostDDPRow(newRowIndex); };
        }
    });
    
    const spans = newRow.querySelectorAll('span');
    spans.forEach(span => {
        const oldId = span.id;
        if (oldId) {
            const newId = oldId.replace('_' + rowIndex, '_' + newRowIndex);
            span.id = newId;
            // 复制显示值
            const sourceSpan = document.getElementById(oldId);
            if (sourceSpan) {
                span.textContent = sourceSpan.textContent;
            }
            // 确保单价列保持加粗样式
            if (newId.includes('tp_unit-price-cbm_') || newId.includes('tp_unit-price-kg_')) {
                span.classList.add('fw-bold');
            }
        }
    });
    
    // 更新操作按钮
    const buttons = newRow.querySelectorAll('button');
    buttons.forEach(button => {
        const onclick = button.getAttribute('onclick');
        if (onclick) {
            if (onclick.includes('copyDDPRow')) {
                button.setAttribute('onclick', 'copyDDPRow(' + newRowIndex + ')');
            } else if (onclick.includes('deleteDDPRow')) {
                button.setAttribute('onclick', 'deleteDDPRow(' + newRowIndex + ')');
                button.disabled = false; // 复制的行可以删除
            }
        }
    });
    
    tbody.appendChild(newRow);
    
    // 重新计算新行的值
    calculateCostDDPRow(newRowIndex);
}

// 删除包税成本计算行
function deleteDDPRow(rowIndex) {
    const tbody = document.getElementById('DDPTableBody');
    const rows = tbody.querySelectorAll('tr');
    
    // 至少保留一行
    if (rows.length <= 1) {
        return;
    }
    
    const rowToDelete = rows[rowIndex];
    if (rowToDelete) {
        rowToDelete.remove();
        
        // 重新索引所有行
        const remainingRows = tbody.querySelectorAll('tr');
        remainingRows.forEach((row, index) => {
            row.setAttribute('data-row-index', index);
            
            // 更新所有ID
            const inputs = row.querySelectorAll('input');
            inputs.forEach(input => {
                const oldId = input.id;
                if (oldId) {
                    const baseId = oldId.substring(0, oldId.lastIndexOf('_'));
                    const newId = baseId + '_' + index;
                    input.id = newId;
                    input.oninput = function() { calculateCostDDPRow(index); };
                }
            });
            
            const spans = row.querySelectorAll('span');
            spans.forEach(span => {
                const oldId = span.id;
                if (oldId) {
                    const baseId = oldId.substring(0, oldId.lastIndexOf('_'));
                    const newId = baseId + '_' + index;
                    span.id = newId;
                }
            });
            
            // 更新操作按钮
            const buttons = row.querySelectorAll('button');
            buttons.forEach(button => {
                const onclick = button.getAttribute('onclick');
                if (onclick) {
                    if (onclick.includes('copyDDPRow')) {
                        button.setAttribute('onclick', 'copyDDPRow(' + index + ')');
                    } else if (onclick.includes('deleteDDPRow')) {
                        button.setAttribute('onclick', 'deleteDDPRow(' + index + ')');
                        // 如果只剩一行，禁用删除按钮
                        button.disabled = remainingRows.length === 1;
                    }
                }
            });
        });
    }
}


/**
 * Tab 4 - 快递派查价
 */
// 动态生成快递派价格表格
function initCarrierSelect() {
    const sel = document.getElementById('t4_carrier');
    if (!sel || !window.data || !expressPricing) return;
    const carriers = Object.keys(expressPricing);
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
    name: '巴黎', 
    timezone: 'Europe/Paris', 
    country: '法国',
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

/**
 * 切换流程步骤显示/隐藏
 */
function toggleProcessSteps(element) {
  const card = element.closest('.process-card-compact');
  const stepsDetail = card.querySelector('.process-steps-detail');
  const chevron = element.querySelector('.process-chevron');
  
  if (stepsDetail.style.display === 'none' || !stepsDetail.style.display) {
    // 展开
    stepsDetail.style.display = 'block';
    stepsDetail.style.maxHeight = '0';
    stepsDetail.style.overflow = 'hidden';
    stepsDetail.style.opacity = '0';
    stepsDetail.style.transform = 'translateY(-10px)';
    
    // 立即更新箭头和提示
    chevron.className = 'bi bi-chevron-up process-chevron';
    element.setAttribute('data-bs-title', '点击收起详细流程');
    
    // 强制重排，然后开始动画
    stepsDetail.offsetHeight;
    
    stepsDetail.style.transition = 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)';
    stepsDetail.style.maxHeight = '1000px';
    stepsDetail.style.opacity = '1';
    stepsDetail.style.transform = 'translateY(0)';
    
    // 动画完成后清理样式
    setTimeout(() => {
      stepsDetail.style.maxHeight = 'none';
      stepsDetail.style.overflow = 'visible';
    }, 400);
  } else {
    // 收起
    stepsDetail.style.maxHeight = stepsDetail.scrollHeight + 'px';
    stepsDetail.style.overflow = 'hidden';
    stepsDetail.style.transition = 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)';
    
    // 强制重排
    stepsDetail.offsetHeight;
    
    // 开始收起动画
    stepsDetail.style.maxHeight = '0';
    stepsDetail.style.opacity = '0';
    stepsDetail.style.transform = 'translateY(-10px)';
    
    // 动画完成后隐藏元素
    setTimeout(() => {
      stepsDetail.style.display = 'none';
      stepsDetail.style.maxHeight = 'none';
      stepsDetail.style.overflow = 'visible';
      stepsDetail.style.opacity = '1';
      stepsDetail.style.transform = 'translateY(0)';
    }, 300);
    
    // 立即更新箭头和提示
    chevron.className = 'bi bi-chevron-down process-chevron';
    element.setAttribute('data-bs-title', '点击查看详细流程');
  }
  
  // 更新tooltip
  const tooltip = bootstrap.Tooltip.getInstance(element);
  if (tooltip) {
    tooltip.dispose();
    new bootstrap.Tooltip(element);
  }
}