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

/**
 * 获取时效
 */
function getTransitTime(country, channel, postcode) {
    let transitTime = "";
    postcode = postcode != null ? postcode[0] : 0;

    switch (country) {
        case "美国":
            transitTime = getTransitTimeUSA(channel, postcode);
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

