const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));

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

// 初始化分类按纽
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
 * 获取时效
 */
function getTransitTime(country, channel, postcode) {
    let transitTime = "";
    postcode = postcode != null ? postcode[0] : 0;

    if (country == "美国") {
        transitTime = getTransitTimeUSA(channel, postcode);
        let isRemoteAddress = document.getElementById('remote-address').checked;
        if (isRemoteAddress) {
            transitTime = getRemoteTranTime(channel,transitTime);
        }      
    } else if (country == "加拿大") {
        transitTime = getTransitTimeCA(channel, postcode);
    } else if (country == "欧洲") {
        transitTime = getTransitTimeEU(channel, postcode);
    } else if (country == "英国") {
        transitTime = getTransitTimeUK(channel, postcode);
    }
    return transitTime;
}

/**
 * 获取美国时效
 */
function getTransitTimeUSA(channel, postcode) {
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
    let transitTime = "";
    if (channel == "Sea truck") {
        transitTime = "50-55";
    } else if (channel == "Sea express") {
        transitTime = "45-50";
    } else if (channel == "Air express") {
        transitTime = "8-12";
    }

    return transitTime;
}

/**
 * 获取英国时效
 */
function getTransitTimeUK(channel, postcode) {
    let transitTime = "";
    if (channel == "Sea truck") {
        transitTime = "50-55";
    } else if (channel == "Sea express") {
        transitTime = "45-50";
    } else if (channel == "Air express") {
        transitTime = "8-12";
    }

    return transitTime;
}

/**
 * 获取中文渠道名
 */
function getCN(channel) {
    switch (channel) {
        case 'Sea express':
            return '海运快递派';
        case 'Fast sea express':
            return '快船快递派';
        case 'Air express':
            return '空运快递派';
        default:
            return '普船卡派';
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
      let end = parseInt(match[2], 10) + days;   // 提取第二个数字并加5
  
      return `${start}-${end}`; // 返回修改后的字符串
    } else {
      return transitTime; // 若格式不匹配，返回错误信息
    }
  }