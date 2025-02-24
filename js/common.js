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


// 插入快捷回复
function insertQuickReply() {
    const selectedOption = document.getElementById('quick-reply').selectedOptions[0]; // 获取选中的选项
    const chineseMessage = selectedOption.value; // 获取中文文本
    const englishMessage = selectedOption.getAttribute('data-en'); // 获取英文文本

    // 将中文和英文消息插入到对应的文本框
    document.getElementById('chinese-message').value = chineseMessage;
    document.getElementById('english-message').value = englishMessage;
}

// 初始化快捷回复下拉框
function loadQuickReplies() {
    const quickReplySelect = document.getElementById('quick-reply');
    quickReplies.forEach((reply, index) => {
        const option = document.createElement('option');
        option.value = reply.chinese; // 设置中文作为option的值
        option.setAttribute('data-en', reply.english); // 设置英文作为data-en属性
        option.innerText = reply.chinese; // 显示中文文本
        quickReplySelect.appendChild(option);
    });
}

// 插入快捷回复
function insertQuickReply() {
    const selectedOption = document.getElementById('quick-reply').selectedOptions[0]; // 获取选中的选项
    const chineseMessage = selectedOption.value; // 获取中文文本
    const englishMessage = selectedOption.getAttribute('data-en'); // 获取英文文本

    // 将中文和英文消息插入到对应的文本框
    document.getElementById('chinese-message').value = chineseMessage;
    document.getElementById('english-message').value = englishMessage;
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

    // 根据邮编范围匹配时效
    if (postcode < 5) {
        return channelData["0-4"] || ""; // 美东
    } else if (postcode < 8) {
        return channelData["5-7"] || ""; // 美中
    } else {
        return channelData["8-9"] || ""; // 美西
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
            return '普船快递派';
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

function getRemoteTranTime(channel,transitTime) {
    if (channel == 'Sea truck'){
        transitTime = addDays(transitTime, 5);
    }
    return transitTime;
}

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