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

// 显示提示消息
function showToast(message, type = 'info') {
  const toastElement = document.getElementById('copyToast');
  const toastMessage = document.getElementById('toastMessage');
  
  toastMessage.textContent = message;
  
  // 根据类型设置样式
  const toast = new bootstrap.Toast(toastElement);
  toast.show();
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
  if (typeof bookmarksData !== 'undefined') {
    initBookmarks();
  }
});
