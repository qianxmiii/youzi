// 常用网址功能模块
let currentBookmarkView = 'list';
let filteredBookmarks = [];

// 初始化常用网址功能
function initBookmarks() {
  // 绑定搜索事件
  document.getElementById('bookmarkSearch').addEventListener('input', filterBookmarks);
  
  // 绑定分类按钮事件
  const categoryButtons = document.querySelectorAll('#bookmarkCategoryButtons button');
  categoryButtons.forEach(button => {
    button.addEventListener('click', function() {
      // 移除所有按钮的active类
      categoryButtons.forEach(btn => btn.classList.remove('active'));
      // 为当前按钮添加active类
      this.classList.add('active');
      // 执行筛选
      filterBookmarks();
    });
  });
  
  // 设置默认视图为网格
  currentBookmarkView = 'grid';
  document.getElementById('bookmarkListView').classList.remove('active');
  document.getElementById('bookmarkGridView').classList.add('active');
  
  // 初始化显示
  filteredBookmarks = [...bookmarksData];
  renderBookmarks();
}

// 切换视图模式
function switchBookmarkView(view) {
  currentBookmarkView = view;
  
  // 更新按钮状态
  document.getElementById('bookmarkListView').classList.toggle('active', view === 'list');
  document.getElementById('bookmarkGridView').classList.toggle('active', view === 'grid');
  
  // 重新渲染
  renderBookmarks();
}

// 筛选网址
function filterBookmarks() {
  const searchTerm = document.getElementById('bookmarkSearch').value.toLowerCase();
  const activeCategoryButton = document.querySelector('#bookmarkCategoryButtons button.active');
  const categoryFilter = activeCategoryButton ? activeCategoryButton.dataset.category : 'all';
  
  filteredBookmarks = bookmarksData.filter(bookmark => {
    const matchesSearch = !searchTerm || 
      bookmark.name.toLowerCase().includes(searchTerm) ||
      bookmark.description.toLowerCase().includes(searchTerm) ||
      bookmark.url.toLowerCase().includes(searchTerm) ||
      bookmark.tags.some(tag => tag.toLowerCase().includes(searchTerm));
    
    const matchesCategory = categoryFilter === 'all' || bookmark.category === categoryFilter;
    
    return matchesSearch && matchesCategory;
  });
  
  renderBookmarks();
}

// 渲染网址列表
function renderBookmarks() {
  const container = document.getElementById('bookmarkList');
  const noResults = document.getElementById('noBookmarkResults');
  const countElement = document.getElementById('bookmarkCount');
  
  // 更新统计信息
  countElement.textContent = `共找到 ${filteredBookmarks.length} 个网址`;
  
  if (filteredBookmarks.length === 0) {
    container.style.display = 'none';
    noResults.style.display = 'block';
    return;
  }
  
  container.style.display = 'block';
  noResults.style.display = 'none';
  
  if (currentBookmarkView === 'list') {
    renderListView(container);
  } else {
    renderGridView(container);
  }
}

// 渲染列表视图
function renderListView(container) {
  container.className = 'bookmark-list list-view';
  container.innerHTML = filteredBookmarks.map(bookmark => `
    <div class="bookmark-item list-item" data-id="${bookmark.id}">
      <div class="bookmark-icon">${bookmark.icon}</div>
      <div class="bookmark-content">
        <div class="bookmark-header">
          <h6 class="bookmark-name">${bookmark.name}</h6>
          <div class="bookmark-actions">
            <button class="btn btn-sm btn-outline-primary" onclick="openBookmark('${bookmark.url}')" title="打开网址">
              <i class="bi bi-box-arrow-up-right"></i>
            </button>
            <button class="btn btn-sm btn-outline-secondary" onclick="copyBookmarkUrl('${bookmark.url}')" title="复制网址">
              <i class="bi bi-clipboard"></i>
            </button>
          </div>
        </div>
        <p class="bookmark-description">${bookmark.description}</p>
        <div class="bookmark-meta">
          <span class="badge bg-secondary">${bookmark.category}</span>
        </div>
        <div class="bookmark-tags">
          ${bookmark.tags.map(tag => `<span class="badge bg-light text-dark">${tag}</span>`).join(' ')}
        </div>
      </div>
    </div>
  `).join('');
}

// 渲染网格视图
function renderGridView(container) {
  container.className = 'bookmark-list grid-view';
  container.innerHTML = filteredBookmarks.map(bookmark => `
    <div class="bookmark-item grid-item" data-id="${bookmark.id}">
      <div class="bookmark-card">
        <div class="bookmark-card-header">
          <div class="bookmark-icon">${bookmark.icon}</div>
          <div class="bookmark-actions">
            <button class="btn btn-sm btn-outline-primary" onclick="openBookmark('${bookmark.url}')" title="打开网址">
              <i class="bi bi-box-arrow-up-right"></i>
            </button>
            <button class="btn btn-sm btn-outline-secondary" onclick="copyBookmarkUrl('${bookmark.url}')" title="复制网址">
              <i class="bi bi-clipboard"></i>
            </button>
          </div>
        </div>
        <div class="bookmark-card-body">
          <h6 class="bookmark-name">${bookmark.name}</h6>
          <p class="bookmark-description">${bookmark.description}</p>
          <div class="bookmark-meta">
            <span class="badge bg-secondary">${bookmark.category}</span>
          </div>
          <div class="bookmark-tags">
            ${bookmark.tags.map(tag => `<span class="badge bg-light text-dark">${tag}</span>`).join(' ')}
          </div>
        </div>
      </div>
    </div>
  `).join('');
}

// 打开网址
function openBookmark(url) {
  window.open(url, '_blank');
  showToast('正在打开网址...', 'success');
}

// 复制网址
function copyBookmarkUrl(url) {
  navigator.clipboard.writeText(url).then(() => {
    showToast('网址已复制到剪贴板', 'success');
  }).catch(err => {
    // 降级方案
    const textArea = document.createElement('textarea');
    textArea.value = url;
    document.body.appendChild(textArea);
    textArea.select();
    document.execCommand('copy');
    document.body.removeChild(textArea);
    showToast('网址已复制到剪贴板', 'success');
  });
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

// 显示提示消息（支持多种类型）
function showToast(message, type = 'success') {
  const toastElement = document.getElementById('copyToast');
  const toastMessage = document.getElementById('toastMessage');
  const toastIcon = document.getElementById('toastIcon');
  
  if (toastElement && toastMessage && toastIcon) {
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
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
  if (typeof bookmarksData !== 'undefined') {
    initBookmarks();
  }
});
