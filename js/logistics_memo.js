// 物流备忘录功能模块
let currentView = 'list';
let currentFilter = 'all';
let searchKeyword = '';

// 初始化物流备忘录
function initLogisticsMemo() {
    // 绑定搜索事件
    document.getElementById('logisticsSearch').addEventListener('input', function(e) {
        searchKeyword = e.target.value.toLowerCase();
        filterContent();
    });

    // 绑定筛选事件
    document.getElementById('logisticsFilter').addEventListener('change', function(e) {
        currentFilter = e.target.value;
        filterContent();
    });

    // 默认显示国家信息
    showCountryInfo();
}

// 切换视图模式
function switchView(view) {
    currentView = view;
    
    // 更新按钮状态
    document.getElementById('viewList').classList.toggle('active', view === 'list');
    document.getElementById('viewGrid').classList.toggle('active', view === 'grid');
    
    // 重新渲染内容
    filterContent();
}

// 显示通用信息
function showGeneralInfo() {
    const content = document.getElementById('logisticsContent');
    const data = window.logisticsData.generalInfo;
    
    let html = `
        <div class="card">
            <div class="card-header">
                <h5 class="mb-0">通用信息</h5>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-6">
                        <h6><i class="bi bi-lightbulb"></i> 基础概念</h6>
                        <div class="accordion" id="basicConceptsAccordion">
    `;
    
    data.basicConcepts.forEach((concept, index) => {
        html += `
            <div class="accordion-item">
                <h2 class="accordion-header" id="heading${index}">
                    <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" 
                            data-bs-target="#collapse${index}" aria-expanded="false" aria-controls="collapse${index}">
                        ${concept.title}
                    </button>
                </h2>
                <div id="collapse${index}" class="accordion-collapse collapse" 
                     aria-labelledby="heading${index}" data-bs-parent="#basicConceptsAccordion">
                    <div class="accordion-body">
                        ${concept.content.replace(/\n/g, '<br>')}
                    </div>
                </div>
            </div>
        `;
    });
    
    html += `
                        </div>
                    </div>
                    <div class="col-md-6">
                        <h6><i class="bi bi-question-circle"></i> 常见问题</h6>
                        <div class="accordion" id="commonQuestionsAccordion">
    `;
    
    data.commonQuestions.forEach((qa, index) => {
        html += `
            <div class="accordion-item">
                <h2 class="accordion-header" id="qaHeading${index}">
                    <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" 
                            data-bs-target="#qaCollapse${index}" aria-expanded="false" aria-controls="qaCollapse${index}">
                        ${qa.question}
                    </button>
                </h2>
                <div id="qaCollapse${index}" class="accordion-collapse collapse" 
                     aria-labelledby="qaHeading${index}" data-bs-parent="#commonQuestionsAccordion">
                    <div class="accordion-body">
                        ${qa.answer}
                    </div>
                </div>
            </div>
        `;
    });
    
    html += `
                        </div>
                    </div>
                </div>
                <div class="mt-4">
                    <h6><i class="bi bi-book"></i> 术语词典</h6>
                    <div class="row" id="terminologyList">
                        <!-- 术语列表将通过JavaScript动态生成 -->
                    </div>
                </div>
            </div>
        </div>
    `;
    
    content.innerHTML = html;
    
    // 渲染术语列表
    renderTerminologyList();
    
    // 更新导航状态
    updateNavigationState('general');
}

// 显示国家信息
function showCountryInfo() {
    const content = document.getElementById('logisticsContent');
    const data = window.logisticsData.countryInfo;
    
    let html = `
        <div class="card">
            <div class="card-header">
                <h5 class="mb-0">国家信息</h5>
            </div>
            <div class="card-body">
                <div id="countryList" class="row">
                    <!-- 国家列表将通过JavaScript动态生成 -->
                </div>
            </div>
        </div>
    `;
    
    content.innerHTML = html;
    
    // 渲染国家列表
    renderCountryList();
    
    // 更新导航状态
    updateNavigationState('countries');
}


// 渲染国家列表
function renderCountryList() {
    const container = document.getElementById('countryList');
    const data = window.logisticsData.countryInfo;
    
    let html = '';
    
    data.forEach(country => {
        if (currentFilter !== 'all' && currentFilter !== 'countries') return;
        if (searchKeyword && !country.name.toLowerCase().includes(searchKeyword)) return;
        
        if (currentView === 'grid') {
            html += `
                <div class="col-md-6 col-lg-4 mb-3">
                    <div class="card h-100">
                        <div class="card-header d-flex justify-content-between align-items-center">
                            <h6 class="mb-0">${country.flag} ${country.name}</h6>
                            <small class="text-muted">${country.code}</small>
                        </div>
                        <div class="card-body">
                            <p class="card-text">
                                <strong>货币:</strong> ${country.generalInfo.currency}<br>
                                <strong>时区:</strong> ${country.generalInfo.timezone}<br>
                                <strong>语言:</strong> ${country.generalInfo.language}
                            </p>
                            <button class="btn btn-outline-primary btn-sm" onclick="showCountryDetail('${country.code}')">
                                查看详情
                            </button>
                        </div>
                    </div>
                </div>
            `;
        } else {
            html += `
                <div class="col-12 mb-2">
                    <div class="card">
                        <div class="card-body">
                            <div class="row align-items-center">
                                <div class="col-md-2">
                                    <h5 class="mb-0">${country.flag} ${country.name}</h5>
                                    <small class="text-muted">${country.code}</small>
                                </div>
                                <div class="col-md-3">
                                    <small class="text-muted">货币: ${country.generalInfo.currency}</small><br>
                                    <small class="text-muted">时区: ${country.generalInfo.timezone}</small>
                                </div>
                                <div class="col-md-3">
                                    <small class="text-muted">清关: ${country.logistics.customs.clearanceTime}</small><br>
                                    <small class="text-muted">关税: ${country.logistics.customs.duties}</small>
                                </div>
                                <div class="col-md-4 text-end">
                                    <button class="btn btn-outline-primary btn-sm" onclick="showCountryDetail('${country.code}')">
                                        查看详情
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }
    });
    
    container.innerHTML = html;
}

// 渲染术语列表
function renderTerminologyList() {
    const container = document.getElementById('terminologyList');
    const data = window.logisticsData.generalInfo.terminology;
    
    let html = '';
    
    data.forEach(term => {
        if (currentFilter !== 'all' && currentFilter !== 'terms') return;
        if (searchKeyword && !term.term.toLowerCase().includes(searchKeyword) && 
            !term.meaning.toLowerCase().includes(searchKeyword)) return;
        
        html += `
            <div class="col-md-6 col-lg-4 mb-2">
                <div class="card">
                    <div class="card-body p-2">
                        <h6 class="card-title mb-1">${term.term}</h6>
                        <p class="card-text small mb-1">${term.meaning}</p>
                        <span class="badge bg-secondary">${term.category}</span>
                    </div>
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}


// 显示国家详情
function showCountryDetail(countryCode) {
    const country = window.logisticsData.countryInfo.find(c => c.code === countryCode);
    if (!country) return;
    
    const content = document.getElementById('logisticsContent');
    
    let html = `
        <div class="card">
            <div class="card-header d-flex justify-content-between align-items-center">
                <h5 class="mb-0">${country.flag} ${country.name} 详细信息</h5>
                <button class="btn btn-outline-secondary btn-sm" onclick="showCountryInfo()">
                    <i class="bi bi-arrow-left"></i> 返回
                </button>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-6">
                        <h6>基本信息</h6>
                        <table class="table table-sm">
                            <tr><td><strong>货币:</strong></td><td>${country.generalInfo.currency}</td></tr>
                            <tr><td><strong>时区:</strong></td><td>${country.generalInfo.timezone}</td></tr>
                            <tr><td><strong>语言:</strong></td><td>${country.generalInfo.language}</td></tr>
                            <tr><td><strong>首都:</strong></td><td>${country.generalInfo.capital}</td></tr>
                        </table>
                        
                        <h6>物流信息</h6>
                        <p><strong>主要港口:</strong> ${country.logistics.majorPorts.join(', ')}</p>
                        <p><strong>主要机场:</strong> ${country.logistics.majorAirports.join(', ')}</p>
                        
                        <h6>清关信息</h6>
                        <table class="table table-sm">
                            <tr><td><strong>清关时间:</strong></td><td>${country.logistics.customs.clearanceTime}</td></tr>
                            <tr><td><strong>关税:</strong></td><td>${country.logistics.customs.duties}</td></tr>
                        </table>
                        <p><strong>所需文件:</strong> ${country.logistics.customs.requiredDocs.join(', ')}</p>
                        <p><strong>限制条件:</strong> ${country.logistics.customs.restrictions.join(', ')}</p>
                    </div>
                    <div class="col-md-6">
                        <h6>运输渠道</h6>
                        <p><strong>快递:</strong> ${country.logistics.shipping.express.join(', ')}</p>
                        <p><strong>空运:</strong> ${country.logistics.shipping.airFreight.join(', ')}</p>
                        <p><strong>海运:</strong> ${country.logistics.shipping.seaFreight.join(', ')}</p>
                        
                        <h6>价格参考</h6>
                        <table class="table table-sm">
                            <tr><td><strong>快递:</strong></td><td>${country.pricing.express}</td></tr>
                            <tr><td><strong>空运:</strong></td><td>${country.pricing.airFreight}</td></tr>
                            <tr><td><strong>海运:</strong></td><td>${country.pricing.seaFreight}</td></tr>
                        </table>
                        
                        <h6>注意事项</h6>
                        <p class="text-muted">${country.notes}</p>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    content.innerHTML = html;
}

// 筛选内容
function filterContent() {
    if (currentFilter === 'countries' || currentFilter === 'all') {
        showCountryInfo();
    } else if (currentFilter === 'terms') {
        showGeneralInfo();
    } else if (currentFilter === 'questions') {
        showGeneralInfo();
    }
}

// 更新导航状态
function updateNavigationState(activeItem) {
    // 移除所有活动状态
    document.querySelectorAll('.list-group-item').forEach(item => {
        item.classList.remove('active');
    });
    
    // 添加当前活动状态
    if (activeItem === 'general') {
        document.querySelector('[onclick="showGeneralInfo()"]').classList.add('active');
    } else if (activeItem === 'countries') {
        document.querySelector('[onclick="showCountryInfo()"]').classList.add('active');
    }
}

// 导出物流信息
function exportLogisticsInfo() {
    const data = window.logisticsData;
    const dataStr = JSON.stringify(data, null, 2);
    const dataBlob = new Blob([dataStr], {type: 'application/json'});
    
    const link = document.createElement('a');
    link.href = URL.createObjectURL(dataBlob);
    link.download = 'logistics_memo.json';
    link.click();
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 延迟初始化，确保数据已加载
    setTimeout(initLogisticsMemo, 100);
});
