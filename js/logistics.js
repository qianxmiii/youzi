// 新增常量 exchange_rate
const exchange_rate = 7.15; //美元汇率
const cost_exchange_rate = 7.2; //美元汇率
let valid_date = ''; //报价有效日期
const LINE_BREAK = '\n';
let addFee = new Decimal(0); //其他费用

// 引入 data.js 中的数组
const {deliveryMethodsByCountry, quickReplies, addressToPostcode, remotePostcodes} = window.data;

// 页面加载时初始化
window.onload = function () {

    // 获取下一个星期五的日期
    valid_date = getNextFriday();

    init(); // 初始化
    eventListener();
};

/**
 * 初始化
 */
function init() {

    // 初始化派送方式
    updateDeliveryMethods();
    // 渲染价格表格
    renderPriceTable();
    // 初始化时渲染标签按钮
    renderTagButtons();
    // 加载美国数据
    loadUSAData();
    // 初始化
    initQuickReplyCategories();
    // 初始化车型查询 Tab
    initVehicleTab();
}


/**
 * 监听输入
 */
function eventListener() {
    // 监听渠道下拉选项的变化
    document.getElementById("t4_channel").addEventListener("change", renderPriceTable());
    // 监听搜索框输入
    document.getElementById("usaSearchInput").addEventListener("input", searchUSAData);
}


// 计算箱规
function calculate() {
    let rows = document.querySelectorAll('.input-row');
    let totalQuantity = new Decimal(0);
    let totalVolume = new Decimal(0);
    let totalWeight = new Decimal(0);
    let totalDimensionWeight = new Decimal(0);
    let deliveryMethod = document.getElementById("delivery-method").value;
    let calCountry = document.getElementById("cal-country").value;
    let calChannel = document.getElementById("cal-channel").value;
    const rules = boxRules[calCountry]?.[calChannel]; // 获取当前国家和渠道的规则
    let warnings = [];
    let sizeinfo ='';

    rows.forEach((row, index) => {
        let length = new Decimal(row.querySelector('.length').value || 0);
        let width = new Decimal(row.querySelector('.width').value || 0);
        let height = new Decimal(row.querySelector('.height').value || 0);
        let weight = new Decimal(row.querySelector('.weight').value || 0);
        let quantity = new Decimal(row.querySelector('.quantity').value || 0);

        sizeinfo += `\n${weight}kg ${length}*${width}*${height}cm ${quantity}箱`;
        // 计算体积 (cbm)
        let volume = length.mul(width).mul(height).mul(quantity).dividedBy(1000000);
        volume = volume.mul(100).ceil().div(100); // 保留两位小数并向上取整

        // 计算单箱材积 (kg)
        let volumeRatio = deliveryMethod == "快递5000" ? new Decimal(5000) : new Decimal(6000);
        
        let singleDimensionWeight = length.mul(width).mul(height).div(volumeRatio).ceil(); // 向上取整

        // 计算实重 (kg)
        let rowWeight = weight.mul(quantity).mul(100).ceil().div(100); // 保留两位小数并向上取整

        // 计算材积重 (kg)
        let dimensionWeight = length.mul(width).mul(height).mul(quantity).div(6000).ceil(); // 向上取整

        // 检查派送方式为“快递派”时，调整实重和材积重
        if (deliveryMethod == "快递派") {
            let minWeight = new Decimal(12).mul(quantity); // 最低实重和材积重要求
            if (rowWeight.lessThan(minWeight)) rowWeight = minWeight; // 更新实重
            if (dimensionWeight.lessThan(minWeight)) dimensionWeight = minWeight; // 更新材积重
        }

        // 计算周长 (cm)
        let sides = [length, width, height].sort((a, b) => a.minus(b).toNumber()); // 排序：从小到大
        let perimeter = sides[0].add(sides[1]).mul(2).add(sides[2]);

        // 更新单行数据
        row.querySelector('.result-cell:nth-child(7)').innerText = `${volume} cbm`;
        row.querySelector('.result-cell:nth-child(8)').innerText = `${singleDimensionWeight} kg`; // 新增列
        row.querySelector('.result-cell:nth-child(9)').innerText = `${rowWeight} kg`;
        row.querySelector('.result-cell:nth-child(10)').innerText = `${dimensionWeight} kg`;
        row.querySelector('.result-cell:nth-child(11)').innerText = `${perimeter} cm`;

        let singleDimensionWeightCell = row.querySelector('.result-cell:nth-child(8)');
        singleDimensionWeightCell.classList.toggle('highlight-red', singleDimensionWeight.greaterThanOrEqualTo(25)); // 材积大于25kg就提示

        // 高亮显示周长
        let perimeterCell = row.querySelector('.result-cell:nth-child(11)');
        perimeterCell.classList.toggle('highlight-red', perimeter.greaterThanOrEqualTo(260));

        // 累加总计
        totalQuantity = totalQuantity.add(quantity);
        totalVolume = totalVolume.add(volume);
        totalWeight = totalWeight.add(rowWeight);
        totalDimensionWeight = totalDimensionWeight.add(dimensionWeight);

        // 检查规则
        if (rules) {
            let isOver = false;
            let warningStr = `第 ${index + 1} 行：${quantity} 箱，`;
            if (weight.greaterThan(rules.maxWeight)) {
                warningStr += `单件实重 ${weight} kg (> ${rules.maxWeight} kg),`;
                isOver = true;
            }
            if (sides[2].greaterThan(rules.maxLength)) {
                warningStr += `最长边 ${sides[2]} cm (> ${rules.maxLength} cm), `;
                isOver = true;
            }
            if (sides[1].greaterThan(rules.maxSecondLength)) {
                warningStr += `第二长边 ${sides[1]} cm (> ${rules.maxSecondLength} cm), `;
                isOver = true;
            }
            if (perimeter.greaterThan(rules.maxPerimeter)) {
                warningStr += `围长 ${perimeter} cm (> ${rules.maxPerimeter} cm),`;
                isOver = true;
            }
            if (rules.maxDimensionWeight && singleDimensionWeight > rules.maxDimensionWeight) {
                warningStr += `单箱材积 ${singleDimensionWeight} kg (> ${rules.maxDimensionWeight} kg),`;
                isOver = true;
            }

            if (isOver) warnings.push(warningStr);
        }
        
    });

    totalVolume = totalVolume.mul(100).ceil().div(100);// 向上取整保留两位小数
    totalWeight = totalWeight.ceil(); // 向上取整
    totalDimensionWeight = totalDimensionWeight.ceil();// 向上取整

    // 更新总计数据
    document.getElementById('total-volume').innerText = totalVolume.toString(); 
    document.getElementById('total-weight').innerText = totalWeight.toString(); 
    document.getElementById('total-quantity').innerText = totalQuantity.toString();
    document.getElementById('total-dimension-weight').innerText = totalDimensionWeight.toString(); // 向上取整

    // 计算计费重
    let billingWeight = Decimal.max(totalWeight, totalDimensionWeight.ceil()).ceil();
    document.getElementById('billing-weight').innerText = billingWeight.toString();

    // 计算泡比
    if (!totalWeight.equals(0) && !totalVolume.equals(0)) {
        let volumeRatio = totalWeight.dividedBy(totalVolume);
        document.getElementById('volume-ratio').innerText = volumeRatio.toFixed(0);
    }

     // 更新汇总信息
     document.getElementById('summary-size').innerText = sizeinfo;
     document.getElementById('summary-chargeweight').innerText = totalDimensionWeight;
     document.getElementById('summary-desc').innerText = `\n${totalQuantity}ctns ${totalWeight}kg ${totalVolume}cbm `;

    // 获取DOM元素
    const warningsTextarea = document.getElementById('box-warnings');
    const warningsToggle = document.getElementById('warningsToggle');
    const warningCount = document.getElementById('warningCount');
    const warningsCollapse = new bootstrap.Collapse('#warningsCollapse', {
        toggle: false
    });

    if (warnings.length > 0) {
        // 有警告的情况
        warningsTextarea.value = warnings.join('\n');
        warningsTextarea.classList.replace('no-warnings', 'has-warnings');

        // 显示警告按钮并更新计数
        warningsToggle.style.display = 'inline-block';
        warningCount.textContent = warnings.length;

        // 自动展开警告框
        warningsCollapse.show();

        // 添加动画效果
        warningsTextarea.style.animation = 'shake 0.5s';
        setTimeout(() => {
            warningsTextarea.style.animation = '';
        }, 500);
    } else {
        // 无警告的情况
        warningsTextarea.value = '✓ 所有箱规符合要求';
        warningsTextarea.classList.replace('has-warnings', 'no-warnings');

        // 隐藏警告按钮
        warningsToggle.style.display = 'none';

        // 自动收起警告框
        warningsCollapse.hide();
    }
}

// 导入数据
function importData() {

    let totalQuantity = parseInt(document.getElementById('total-quantity').innerText) || 0; //箱数
    let totalWeight = parseFloat(document.getElementById('total-weight').innerText) || 0; //实重
    let totalVolume = parseFloat(document.getElementById('total-volume').innerText) || 0; //体积
    document.getElementById('quantity').value = totalQuantity;
    document.getElementById('weight').value = totalWeight;
    document.getElementById('volume').value = totalVolume;

    updateQuote();

    // 获取图标元素
    const importIcon = document.getElementById('import-icon');

    // 改变图标为 bi-send-check
    importIcon.classList.remove('bi-send');
    importIcon.classList.add('bi-send-check');

    // 2 秒后恢复图标为 bi-send
    setTimeout(() => {
        importIcon.classList.remove('bi-send-check');
        importIcon.classList.add('bi-send');
    }, 2000);
}

// 显示报价
function updateQuote() {

    // 获取用户输入
    let data = getInputData();

    let dimensionWeight = new Decimal(0); //材积重 (kg)
    let chargeWeight = new Decimal(0); //计费重 (kg)
    let priceRmb = new Decimal(0); //计算报价RMB
    let priceUsd = new Decimal(0); //计算报价USD
    let totalProfitRmb = new Decimal(0); // 总利润RMB
    let totalPriceUsd = new Decimal(0); // 总报价USD
    let totalPriceRMB = new Decimal(0); // 总利润USD
    let unitPriceRMB = new Decimal(0); // 报价单价RMB
    let pickupFeeRMB = new Decimal(0); // 提货费RMB
    let pickupFeeUSD = new Decimal(0); // 提货费RMB
    
    let MOQ = '';
    let notes = ""; // 备注

    // 获取提货费
    let pickupFeeCheck = document.getElementById("pickup-fee-checkbox").checked;
    pickupFeeRMB = pickupFeeCheck ? parseFloat(document.getElementById("pickup-fee").value) || 0 : 0;
    pickupFeeUSD = pickupFeeCheck ? parseFloat(document.getElementById("pickup-fee-USD").value) || 0 : 0;
    pickUpFee = new Decimal(pickupFeeRMB).dividedBy(exchange_rate).add(pickupFeeUSD).toFixed(0);

    // 计算材积重 (kg) 使用公式：体积 * 1000000 / 6000
    if (data.totalVolume.greaterThan(0)) {
        dimensionWeight = Math.ceil(data.totalVolume.mul(1000000).dividedBy(6000));
        document.getElementById('dimensionWeight').value = dimensionWeight;
    } else {
        dimensionWeight = 0;
        document.getElementById('dimensionWeight').value = 0;
    }

    // 计算计费重 (kg)：取总实重与材积重的较大者
    chargeWeight = Decimal.max(data.totalWeight, dimensionWeight);
    if (data.channel.includes('express')) {
        let moqWeight = 0;
        let moqUnit = 0;
        if (data.channel == 'Air express' || data.channel == 'Air ups/fedex') {
            moqWeight = data.totalQuantity.mul(10);
            moqUnit = 10;
        } else {
            moqWeight = data.totalQuantity.mul(12);
            moqUnit = 12;
        }
        if (chargeWeight.lessThan(moqWeight)) {
            chargeWeight = moqWeight;
            MOQ = 'MOQ each box is '+ moqUnit + 'kg';
        }
    }

    // 如果有MOQ，以录入的MOQ计费重为准
    const moqInput = document.getElementById('moq-input');
    const moqValue = new Decimal(moqInput.value || 21); // 默认值为 21kg
    if (data.isMOQ) {
        if (chargeWeight.lessThan(moqValue)) {
            chargeWeight = moqValue;
        }
    }

    document.getElementById('chargeWeight').value = chargeWeight;

    // 计算计费重 (CBM)：取总实重与材积重的较大者
    let chargeCBM = new Decimal(Math.ceil(Decimal.max(data.totalWeight.dividedBy(363), data.totalVolume)* 100) / 100);
    document.getElementById('chargeCBM').value = chargeCBM;

    // 计算泡比
    let volumeRatio = new Decimal(0);
    if (!data.totalWeight.equals(0) && !data.totalVolume.equals(0)) {
        volumeRatio = data.totalWeight.dividedBy(data.totalVolume);
        document.getElementById('volumeRatio').value = volumeRatio.toFixed(0);
    } else {
        volumeRatio = new Decimal(0);
        document.getElementById('volumeRatio').value = 0;
    }

    // 泡比颜色设置
    let volumeRatioInput = document.getElementById('volumeRatio');
    if (volumeRatio.greaterThanOrEqualTo(200)) { // 大于等于200时字体为绿色
        volumeRatioInput.style.color = 'green';
    } else if (volumeRatio.lessThan(167)) { // 小于167时字体为蓝色
        volumeRatioInput.style.color = 'blue';
    } else {
        volumeRatioInput.style.color = ''; // 恢复默认颜色
    }


    if (data.isUSD){ //如果输入成本是美元，先转换成RMB
        data.costRmb = data.costRmb.mul(exchange_rate);
    }
    // 计算报价 (RMB) = 成本 (RMB) + 利润 (RMB)
    priceRmb = data.costRmb.add(data.profitRmb);
    document.getElementById("price_rmb").value = priceRmb.toFixed(2);
    
    // 计算报价 (USD) = 报价 (RMB) / exchange_rate
    priceUsd = new Decimal(0);
    if (data.quoteType.includes("CBM")) {
        priceUsd = priceRmb.dividedBy(exchange_rate).toFixed(0);
    } else {
        priceUsd = priceRmb.dividedBy(exchange_rate).toFixed(2); // 保留两位小数
    }
    document.getElementById("price_usd").value = priceUsd;

    // 计算利率 = 1 - (成本 (RMB) / 报价 (RMB))
    let profitRateInput = document.getElementById('profit_rate');
    if (!data.costRmb.equals(0) && !priceRmb.equals(0)) {
        let profitRate = new Decimal(1).minus(data.costRmb.dividedBy(priceRmb));
        profitRateInput.value = Math.ceil(profitRate * 100) + "%"; // 显示为百分比

        if (profitRate.lessThan(0.15)) {
            profitRateInput.style.color = '#ea4335';
        } else if (profitRate.lessThan(0.20)) {
            profitRateInput.style.color = '#fbbc05';
        } else if (profitRate.lessThan(0.25)) {
            profitRateInput.style.color = '#4285f4';
        } else if (profitRate.equals(0)) {
            profitRateInput.style.color = ''; // 恢复默认颜色
        } else {
            profitRateInput.style.color = '#34a853';
        }
    }
    
    // 计算总利润 (RMB) = 计费重 * 利润 (RMB)
    totalProfitRmb = new Decimal(0);
    if (data.quoteType.includes("CBM")) {
        totalProfitRmb = chargeCBM.mul(data.profitRmb);
    } else {
        totalProfitRmb = chargeWeight.mul(data.profitRmb);
    }
    document.getElementById("total_profit_rmb").value = totalProfitRmb; // 保留两位小数

    // 更新利率的 Tooltip
    updateProfitRateTooltip(totalProfitRmb);

    // 计算总报价 (USD)
    totalPriceUsd = new Decimal(0);
    if (data.quoteType.includes("CBM")) {
        totalPriceUsd = new Decimal(priceUsd).mul(chargeCBM);
    } else {
        totalPriceUsd = new Decimal(priceUsd).mul(chargeWeight);
    }
    document.getElementById("total_price_usd").value = totalPriceUsd;

    // 计算总报价 (RMB) = 总报价 (RMB) / exchange_rate
    totalPriceRMB = new Decimal(0);
    if (data.quoteType.includes("CBM")) {
        totalPriceRMB = new Decimal(priceRmb).mul(chargeCBM);
    } else {
        totalPriceRMB = new Decimal(priceRmb).mul(chargeWeight);
    }
    document.getElementById("total_price_rmb").value = totalPriceRMB.toFixed(2);

    // 计算单价(RMB) = 总报价 (RMB) / 计费重
    unitPriceRMB = chargeWeight !=0 ? totalPriceRMB.dividedBy(chargeWeight) : new Decimal(0);
    document.getElementById("unit_price_rmb").value = unitPriceRMB.toFixed(2);

    let unit = 'ctns ';
    if (data.totalQuantity <= 1) unit = 'ctn ';

    addFee = new Decimal(0); //每次初始化
    // 根据选择的备注格式动态生成备注内容
    if (data.quoteType === "通用") {
        // 构建备注内容
        notes = `To ${data.address},${data.totalQuantity.toFixed(0)}${unit}${data.totalWeight.toFixed(0)}kg ${data.totalVolume.toFixed(2)}cbm\n`;
        if (data.isDDU) notes += 'DDU ';
        notes += `${data.channel}: ${priceUsd} usd/kg * ${chargeWeight.toFixed(0)}kg = ${totalPriceUsd}usd `;
        notes += `${getTransitTime(data.country, data.channel, data.postcode)} days ${MOQ} `;
        if (data.isMOQ) notes += `MOQ is ${data.moqInput}kg `;
        if (data.isDDU) notes += getDDUFee(data.country, 1);
        if (data.isRemoteAddress && shippingChannels["快递派"].includes(data.channel)) notes += getRemoteAddressfee(data.totalQuantity);
        if (data.isOverSize) notes += getOverSizeFee(data.country, data.overSizeQuantity);
        if (data.isOverWeight) notes += getOverWeightFee(data.country, data.overWeightQuantity);
        if (data.pickupFeeCheck) notes += `\nPickup fee: ${pickUpFee} usd`;

    } else if (data.quoteType === "通用-CBM") {
        // 构建备注内容
        notes = `To ${data.address},${data.totalQuantity.toFixed(0)}${unit}${data.totalWeight.toFixed(0)}kg ${data.totalVolume.toFixed(2)}cbm\n`;
        if (data.isDDU) notes += 'DDU ';
        notes += `${data.channel}: ${priceUsd} usd/cbm * ${chargeCBM}cbm = ${totalPriceUsd}usd `;
        notes += `${getTransitTime(data.country, data.channel, data.postcode)} days`;
        if (data.isDDU) notes += getDDUFee(data.country, 1);
        if (data.pickupFeeCheck) notes += `\nPickup fee: ${pickUpFee} usd`;

    } else if (data.quoteType === "通用-单价") {
        // 构建备注内容
        notes = `${data.address} ${data.channel}: ${priceUsd} usd per kg `;
        notes += `${getTransitTime(data.country, data.channel, data.postcode)} days`;

    } else if (data.quoteType === "通用-RMB") {
        // 构建备注内容
        notes = `${data.address} ${data.totalQuantity.toFixed(0)}箱 ${data.totalWeight.toFixed(0)}kg ${data.totalVolume.toFixed(2)}cbm\n`;
        if (data.isDDU) notes += 'DDU ';
        notes += `${getCN(data.channel)}: ${priceRmb}RMB/kg * ${chargeWeight.toFixed(0)}kg = ${totalPriceRMB}RMB `;
        notes += `${getTransitTime(data.country, data.channel, data.postcode)} 天 ${MOQ} `;
        if (data.isDDU) notes += getDDUFee(data.country, 0);
        if (data.pickupFeeCheck) notes += `\n提货费: ${pickupFeeRMB} RMB`;
        notes += `\n总费用: ${totalPriceRMB.add(pickupFeeRMB).add(addFee)} RMB`;

    } else if (data.quoteType === "通用-RMB-CBM") {
        // 构建备注内容
        notes = `${data.address} ${data.totalQuantity.toFixed(0)}箱 ${data.totalWeight.toFixed(0)}kg ${data.totalVolume.toFixed(2)}cbm\n`;
        if (data.isDDU) notes += 'DDU ';
        notes += `${getCN(data.channel)}: ${priceRmb}RMB/cbm * ${chargeCBM}cbm = ${totalPriceRMB}RMB `;
        notes += `${getTransitTime(data.country, data.channel, data.postcode)} 天 ${MOQ} `;
        if (data.isDDU) notes += getDDUFee(data.country, 0); 
        if (data.pickupFeeCheck) notes += `\n提货费: ${pickupFeeRMB} RMB`;
        notes += `\n总费用: ${totalPriceRMB.add(pickupFeeRMB).add(addFee)} RMB`;

    } else if (data.quoteType === "PROBOXX") {
        // 构建备注内容
        notes = 'Hi Tal,\n\n';
        // notes = 'Hi Amit,\n\n';
        notes += `To ${data.address},${data.totalQuantity.toFixed(0)}${unit}${data.totalWeight.toFixed(0)}kg ${data.totalVolume.toFixed(2)}cbm\n`;
        notes += data.isDDU ?  'DDU ': 'DDP ';
        notes += `${data.channel}: ${priceUsd} usd/kg * ${chargeWeight.toFixed(0)}kg = ${totalPriceUsd}usd `;
        notes += `${getTransitTime(data.country, data.channel, data.postcode)} days ${MOQ} `;
        if (data.isMOQ) notes += `MOQ is ${data.moqInput}kg `;
        if (data.isRemoteAddress && shippingChannels["快递派"].includes(data.channel)) notes += getRemoteAddressfee(data.totalQuantity);
        if (data.isDDU) notes += getDDUFee(data.country, 1);
        if (data.isOverSize) notes += getOverSizeFee(data.country, data.overSizeQuantity);
        if (data.isOverWeight) notes += getOverWeightFee(data.country, data.overWeightQuantity);
        if (data.pickupFeeCheck) notes += `\nPickup fee: ${pickUpFee} usd`;
        notes += `\nTotal fee: ${totalPriceUsd.add(pickUpFee).add(addFee)} usd\n\nValid date: ${valid_date} `;
    } else if (data.quoteType === "PROBOXX-CBM") {
        // 构建备注内容
        notes = 'Hi Tal,\n\n';
        // notes = 'Hi Amit,\n\n';
        notes += `To ${data.address},${data.totalQuantity.toFixed(0)}${unit}${data.totalWeight.toFixed(0)}kg ${data.totalVolume.toFixed(2)}cbm\n`;
        notes += data.isDDU ? 'DDU ' : 'DDP ';
        notes += `${data.channel}: ${priceUsd} usd/cbm * ${chargeCBM}cbm = ${totalPriceUsd}usd `;
        notes += `${getTransitTime(data.country, data.channel, data.postcode)} days`;
        if (data.isDDU) notes += getDDUFee(data.country, 1);
        if (data.pickupFeeCheck) notes += `\nPickup fee: ${pickUpFee} usd`;
        notes += `\nTotal fee: ${totalPriceUsd.add(pickUpFee).add(addFee)} usd\n\nValid date: ${valid_date} `;
    } else if (data.quoteType === "163") {
        // 构建备注内容
        notes = `${data.address} = ${data.totalQuantity.toFixed(0)}${unit}${data.totalWeight.toFixed(0)}kg ${data.totalVolume.toFixed(2)}cbm\n`;
        if (data.isDDU) notes += 'DDU ';
        notes += `${data.channel}: ${priceUsd} usd/kg * ${chargeWeight.toFixed(0)}kg = ${totalPriceUsd}usd `;
        notes += `${getTransitTime(data.country, data.channel, data.postcode)} days ${MOQ} `;
        if (data.isMOQ) notes += `MOQ is ${data.moqInput}kg `;
        if (data.isDDU) notes += getDDUFee(data.country, 1);
        if (data.isRemoteAddress && shippingChannels["快递派"].includes(data.channel)) notes += getRemoteAddressfee(data.totalQuantity);
        if (data.isOverSize) notes += getOverSizeFee(data.country, data.overSizeQuantity);
        if (data.isOverWeight) notes += getOverWeightFee(data.country, data.overWeightQuantity);
        if (data.pickupFeeCheck) notes += `\nPickup fee: ${pickUpFee} usd`;

    } else if (data.quoteType === "161") {
        // 构建备注内容
        notes = `To ${data.address} ${data.totalQuantity.toFixed(0)}${unit}${data.totalWeight.toFixed(0)}kg ${data.totalVolume.toFixed(2)}cbm\n`;
        if (data.isDDU) notes += 'DDU ';
        notes += `${data.channel}: ${totalPriceUsd}usd `;
        notes += `${getTransitTime(data.country, data.channel, data.postcode)} days ${MOQ} `;
        if (data.isMOQ) notes += `MOQ is ${data.moqInput}kg `;
        if (data.isDDU) notes += getDDUFee(data.country, 1);
        if (data.isRemoteAddress && shippingChannels["快递派"].includes(data.channel)) notes += getRemoteAddressfee(data.totalQuantity);
        if (data.isOverSize) notes += getOverSizeFee(data.country, data.overSizeQuantity);
        if (data.isOverWeight) notes += getOverWeightFee(data.country, data.overWeightQuantity);
        if (data.pickupFeeCheck) notes += `\nPickup fee: ${pickUpFee} usd`;
        notes += `\nTotal fee: ${totalPriceUsd.add(pickUpFee).add(addFee)} usd\n\n`;
    }

    // 将备注内容填入 textarea
    document.getElementById("notes").value = notes;

}

// 识别箱规信息
function parseDimensions() {
    // 获取输入的文本
    const input = document.getElementById("dimension-input").value.trim();
    
    // 使用正则表达式分割输入，支持 '|' 或 'LCL Load Item' 或 或 'Air Load Item'作为分隔符
    // const rows = input.split(/\||== LCL Load Item/).map(row => row.trim());
    const rows = input.split(/\||== LCL Load Item|== Air Load Item/).map(row => row.trim());

    // 获取表格的 tbody 元素
    const tableBody = document.getElementById("box-table");

    // 清除表格中除第一行外的所有行
    while (tableBody.rows.length > 1) {
        tableBody.deleteRow(1);
    }


    // 处理每一行数据
    rows.forEach((row, index) => {

        // 如果当前行是空的，跳过
        if (!row) {
            return; // 跳过空行
        }

        // 使用正则表达式解析长、宽、高、重量和箱数
        const dimensionRegex = /(\d+(\.\d+)?)\s*[*xX×]\s*(\d+(\.\d+)?)\s*[*xX×]\s*(\d+(\.\d+)?)\s*(cm|inch|in|英寸)?/i;
        const weightRegex = /([\d.]+)\s*(kg|kgs|lb|lbs|磅)/i;
        const quantityRegex = /(\d+)\s*(X|\s*)\s*(BOX|BOXES|Boxs|CARTON|CARTONS|ctn|ctns|件|箱|pal|pallets|托)/i;

        // 提取长、宽、高
        const dimensionMatch = row.match(dimensionRegex);
        let length = 0, width = 0, height = 0;
        if (dimensionMatch) {
            length = parseFloat(dimensionMatch[1]);
            width = parseFloat(dimensionMatch[3]);
            height = parseFloat(dimensionMatch[5]);
            const unit = (dimensionMatch[7] || '').toLowerCase();
            // 如果是英寸单位，转换为厘米
            if (unit === 'inch' || unit === 'in' || unit === '英寸') {
                length *= 2.54;
                width *= 2.54;
                height *= 2.54;
            }
        }

        // 提取重量
        const weightMatch = row.match(weightRegex);
        let weight = 0;
        if (weightMatch) {
            weight = parseFloat(weightMatch[1]);
            const unit = (weightMatch[2] || '').toLowerCase();
            // 如果是磅单位，转换为千克
            if (unit === 'lb' || unit === 'lbs' || unit === '磅') {
                weight *= 0.453592;
            }
        }

        // 提取箱数
        const quantityMatch = row.match(quantityRegex);
        const quantity = quantityMatch ? parseInt(quantityMatch[1]) : 0;

        // 获取当前行（如果需要，添加新行）
        let currentRow;
        if (index === 0 || (index == 1 && !rows[0])) {
            currentRow = tableBody.rows[0]; // 第一行直接使用
        } else {
            currentRow = tableBody.insertRow(); // 添加新行
            currentRow.classList.add('input-row');
            currentRow.innerHTML = `
                <td class="index-cell">${index + 1}</td>
                <td><input type="number" class="form-control length" oninput="calculate()"></td>
                <td><input type="number" class="form-control width" oninput="calculate()"></td>
                <td><input type="number" class="form-control height" oninput="calculate()"></td>
                <td><input type="number" class="form-control weight" oninput="calculate()"></td>
                <td><input type="number" class="form-control quantity" oninput="calculate()"></td>
                <td class="result-cell">0.00 cbm</td>
                <td class="result-cell">0 kg</td>
                <td class="result-cell">0 kg</td>
                <td class="result-cell">0 kg</td>
                <td class="result-cell">0 cm</td>
                <td>
                    <button class="btn btn-success btn-sm" onclick="addRow()">+</button>
                    <button class="btn btn-danger btn-sm" onclick="deleteRow(event)">-</button>
                </td>
            `;
        }

        // 将解析后的数据填充到当前行
        currentRow.querySelector('.length').value = Math.ceil(length.toFixed(1));
        currentRow.querySelector('.width').value = Math.ceil(width.toFixed(1));
        currentRow.querySelector('.height').value = Math.ceil(height.toFixed(1));
        currentRow.querySelector('.weight').value = weight.toFixed(2);
        currentRow.querySelector('.quantity').value = quantity;

        // 触发计算
        calculate();
    });
}

// 识别地址、箱数、重量、体积信息
function parsePackageInfo() {
    const input = document.getElementById("package-info-input").value.trim();
    // 使用正则表达式解析箱数、重量、体积
    const volumeRegex = /([\d.]+)\s*(cbm|方)/i;
    const weightRegex = /([\d.]+)\s*(kg|kgs|lb|lbs|磅)/i;
    const quantityRegex = /(\d+)\s*(X|\s*)\s*(BOX|BOXES|Boxs|CARTON|CARTONS|ctn|ctns|件|箱|pal|pallets|托)/i;  
    // 前缀支持带To
    // 识别 1.通用亚马逊仓库 == 开头3个字母 + 1个数字 2. AWD仓库 == IUS 开头 + 一个字母（例如：IUSA）
    const addressRegex = /(?:To \s+)?((?:[A-Z]{3}\d)|IUS[A-Z])\b/i;

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

    // 识别地址代码
    const addressMatch = input.match(addressRegex);
    if (addressMatch && addressToPostcode.hasOwnProperty(addressMatch[0].toUpperCase())) {
        document.getElementById('address').value = addressMatch[0].toUpperCase();
        updatePostcode();
    }

    document.getElementById('quantity').value = quantity;
    document.getElementById('weight').value = Math.ceil(weight);
    document.getElementById('volume').value = new Decimal(volume).toDecimalPlaces(2, Decimal.ROUND_UP);
    
    // 触发计算
    updateQuote();
}

// 获取数据
function getInputData() {
    return {
        country: document.getElementById("country-select").value,
        origin: document.getElementById("origin-select").value,
        totalQuantity: new Decimal(document.getElementById('quantity').value || 0),
        totalWeight: new Decimal(document.getElementById('weight').value || 0),
        totalVolume: new Decimal(document.getElementById('volume').value || 0),
        dimensionWeight: new Decimal(document.getElementById('dimensionWeight').value || 0),
        channel: document.getElementById("delivery-method-select").value,
        address: document.getElementById("address").value.toUpperCase(),
        postcode: document.getElementById("postcode").value,
        costRmb: new Decimal(document.getElementById("cost_rmb").value || 0),
        profitRmb: new Decimal(document.getElementById("profit_rmb").value || 0),
        quoteType: document.getElementById("quote-type").value,
        isRemoteAddress: document.getElementById('remote-address').checked,
        isMOQ: document.getElementById('MOQ').checked,
        isDDU: document.getElementById('ddu_check').checked,
        isOverSize: document.getElementById('oversize_check').checked,
        overSizeQuantity: new Decimal(document.getElementById('oversize-quantity').value || 0),
        isOverWeight: document.getElementById('overweight_check').checked,
        overWeightQuantity: new Decimal(document.getElementById('overweight-quantity').value || 0),
        isUSD: document.getElementById('USD_check').checked,
        pickupFeeCheck: document.getElementById("pickup-fee-checkbox").checked,
        pickUpFeeRaw: parseFloat(document.getElementById("pickup-fee").value) || 0,
        moqInput: new Decimal(document.getElementById('moq-input').value || 21),
    };
}

/* 计算快递派成本 */
function showCost(origin,country,channel,postcode,weight,withBattery){

    let cost = 0;
    if(origin && country && channel.includes('express')){
        if (channel == 'Fast sea express' || channel == 'Fast Maston express' 
             || channel == 'Fast sea ups/fedex' || channel == 'Super sea express'){
                channel = "美森正班";
        } else if (channel == 'Normal sea express' || channel == 'Normal Maston express') {
            channel = "美森加班";
        } else if (channel == 'Sea express' || channel == 'Sea ups/fedex') {
            channel = "普船";
        } else if (channel == 'Air express' || channel == 'Air ups/fedex') {
            if (withBattery) {
                channel = "空派带电";
            } else {
                channel = "空派不带电";
            }
        } else{
            return;
        }
        document.getElementById('southTable').innerText = "华南 (" + channel + ")";
        document.getElementById('eastTable').innerText = "华东 (" + channel + ")";
        document.getElementById('t4_channel').value = channel;
        cost = calculatePrice(origin,channel,postcode,weight) || 0;
    }

    return cost;
}

// 获取成本列的 Tooltip 元素
const costTooltip = document.getElementById("cost-tooltip");

// 监听鼠标悬停事件
costTooltip.addEventListener("mouseenter", function () {
    // 获取必要的参数
    const origin = document.getElementById("origin-select").value;
    const country = document.getElementById("country-select").value;
    const channel = document.getElementById("delivery-method-select").value;
    const postcode = document.getElementById("postcode").value;
    const weight = parseFloat(document.getElementById("chargeWeight").value) || 0;
    const withBattery = document.getElementById("battery_check").checked;

    // 调用 showCost 函数
    const cost = showCost(origin, country, channel, postcode, weight, withBattery);

    // 更新 Tooltip 内容
    if (cost) {
        const tooltipInstance = bootstrap.Tooltip.getInstance(costTooltip);
        if (tooltipInstance) {
            tooltipInstance.setContent({ '.tooltip-inner': `${cost}` });
            tooltipInstance.show();
        }
    }
});

// 监听鼠标离开事件
costTooltip.addEventListener("mouseleave", function () {
    const tooltipInstance = bootstrap.Tooltip.getInstance(costTooltip);
    if (tooltipInstance) {
        tooltipInstance.hide();
    }
});

// 总利润 悬停显示
function updateProfitRateTooltip(totalProfitRmb) {
    const profitRateInput = document.getElementById("profit_rate");
    if (profitRateInput) {
        // 设置 Tooltip 的内容
        profitRateInput.setAttribute("title", `总利润：${totalProfitRmb.toFixed(2)} RMB`);

        // 初始化或更新 Tooltip
        const tooltip = bootstrap.Tooltip.getInstance(profitRateInput);
        if (tooltip) {
            tooltip.update(); // 更新 Tooltip 内容
        } else {
            // 初始化 Tooltip
            new bootstrap.Tooltip(profitRateInput, {
                placement: "top", // Tooltip 显示在顶部
                trigger: "hover"  // 鼠标悬停时显示
            });
        }
    }
}

// 获取提货费输入框元素
const pickupFeeInput = document.getElementById("pickup-fee");

// 监听鼠标悬停事件
pickupFeeInput.addEventListener("mouseenter", function () {
    // 获取实重和方数
    const totalWeight = parseFloat(document.getElementById("weight").value) || 0;
    const totalVolume = parseFloat(document.getElementById("volume").value) || 0;

    // 获取可选车型
    const availableVehicles = getAvailableVehicles(totalWeight, totalVolume);

    // 生成 Tooltip 内容
    let tooltipContent = "可选车型：\n";
    if (availableVehicles.length > 0) {
        availableVehicles.forEach(vehicle => {
            tooltipContent += `- ${vehicle.name}（载重：${vehicle.loadWeightRange[0]}~${vehicle.loadWeightRange[1]}kg，载方：${vehicle.loadVolumeRange[0]}~${vehicle.loadVolumeRange[1]}cbm）\n`;
        });
    } else {
        tooltipContent = "无合适车型，请调整重量或方数。";
    }

    // 设置 Tooltip 内容
    const tooltipInstance = bootstrap.Tooltip.getInstance(pickupFeeInput);
    if (tooltipInstance) {
        tooltipInstance.setContent({ '.tooltip-inner': tooltipContent });
        tooltipInstance.show();
    } else {
        // 初始化 Tooltip
        new bootstrap.Tooltip(pickupFeeInput, {
            title: tooltipContent,
            placement: "top", // Tooltip 显示在顶部
            trigger: "hover"  // 鼠标悬停时显示
        });
    }
});

// 监听鼠标离开事件
pickupFeeInput.addEventListener("mouseleave", function () {
    const tooltipInstance = bootstrap.Tooltip.getInstance(pickupFeeInput);
    if (tooltipInstance) {
        tooltipInstance.hide();
    }
});

/**
 * 根据重量和方数筛选可选车型
 * @param {number} weight - 货物重量 (kg)
 * @param {number} volume - 货物体积 (cbm)
 * @returns {Array} - 符合条件的车型列表
 */
function getAvailableVehicles(weight, volume) {
    return window.data.vehicleTypes.filter(vehicle => {
        const [minWeight, maxWeight] = vehicle.loadWeightRange;
        const [minVolume, maxVolume] = vehicle.loadVolumeRange;
        return weight <= maxWeight-100 && volume <= maxVolume-1;
    });
}

/**
 * 初始化车型查询 Tab
 */
function initVehicleTab() {
    // 动态加载起始地、收货地、货物类型和车型数据
    const pickupLocationSelect = document.getElementById("pickup-location");
    const deliveryLocationSelect = document.getElementById("delivery-location");
    const cargoTypeSelect = document.getElementById("cargo-type");
    const vehicleSelect = document.getElementById("vehicle-select");
    const vehicleTableBody = document.getElementById("vehicle-table-body");

    // // 动态加载起始地
    // window.data.pickupLocations.forEach(location => {
    //     const option = document.createElement("option");
    //     option.value = location;
    //     option.textContent = location;
    //     pickupLocationSelect.appendChild(option);
    // });

    // 动态加载收货地
    window.data.deliveryLocations.forEach(location => {
        const option = document.createElement("option");
        option.value = location;
        option.textContent = location;
        deliveryLocationSelect.appendChild(option);
    });

    // 动态加载货物类型
    window.data.cargoTypes.forEach(type => {
        const option = document.createElement("option");
        option.value = type;
        option.textContent = type;
        cargoTypeSelect.appendChild(option);
    });

    // 动态加载车型
    window.data.vehicleTypes.forEach(vehicle => {
        // 添加到下拉选项
        const option = document.createElement("option");
        option.value = vehicle.name;
        option.textContent = vehicle.name;
        vehicleSelect.appendChild(option);

        // 添加到表格
        const row = document.createElement("tr");
        row.innerHTML = `
            <td>${vehicle.name}</td>
            <td>${vehicle.lengthRange[0]}~${vehicle.lengthRange[1]}</td>
            <td>${vehicle.loadWeightRange[0]}~${vehicle.loadWeightRange[1]}</td>
            <td>${vehicle.loadVolumeRange[0]}~${vehicle.loadVolumeRange[1]}</td>
        `;
        vehicleTableBody.appendChild(row);
    });

    // 监听重量和方数输入框的变化
    const cargoWeightInput = document.getElementById("cargo-weight");
    const cargoVolumeInput = document.getElementById("cargo-volume");
    cargoWeightInput.addEventListener("input", updateVehicleOptions);
    cargoVolumeInput.addEventListener("input", updateVehicleOptions);

    // // 监听车型选择事件
    // vehicleSelect.addEventListener("change", function () {
    //     highlightSelectedVehicle(this.value);
    //     updatePickupFee(pickupLocationSelect.value,this.value);
    // });

    initWarehouseSelect();
}

function initWarehouseSelect() {
    const warehouseSelect = document.getElementById("delivery-location");
    if (!warehouseSelect) return;

    // 监听收货仓选择事件
    warehouseSelect.addEventListener("change", function () {
        updatePickupLocations(this.value);
    });

    updatePickupLocations(warehouseSelect.value);
}

function updatePickupLocations(warehouse) {
    const pickupLocationSelect = document.getElementById("pickup-location");
    if (!pickupLocationSelect) return;

    // 清空下拉菜单
    pickupLocationSelect.innerHTML = '';

    // 获取当前收货仓的起始地
    const pickupLocations = Object.keys(window.data.pickupFee[warehouse]?.pickupLocations || []);

    // 动态加载起始地选项
    pickupLocations.forEach(location => {
        const option = document.createElement("option");
        option.value = location;
        option.textContent = location;
        pickupLocationSelect.appendChild(option);
    });

    // 监听起始地选择事件
    pickupLocationSelect.addEventListener("change", function () {
        updateVehicleOptions(warehouse, this.value);
    });

    updateVehicleOptions(warehouse, pickupLocationSelect.value);
}

/**
 * 根据重量和方数更新车型下拉选项
 */
function updateVehicleOptions(warehouse, pickupLocation)  {
    const weight = parseFloat(document.getElementById("cargo-weight").value) || 0;
    const volume = parseFloat(document.getElementById("cargo-volume").value) || 0;

    // 获取合适的车型
    const suitableVehicles = getAvailableVehicles(weight, volume);

    // 更新车型下拉选项
    const vehicleSelect = document.getElementById("vehicle-select");

    // 如果没有合适的车型，提示用户
    if (suitableVehicles.length === 0) {
        vehicleSelect.innerHTML = '<option value="">无合适车型</option>';

        return;
    }

    vehicleSelect.innerHTML = ''; // 清空选项
    suitableVehicles.forEach(vehicle => {
        const option = document.createElement("option");
        option.value = vehicle.name;
        option.textContent = vehicle.name;
        vehicleSelect.appendChild(option);
    });

    // 找到容量最小的车型
    let minVehicle = suitableVehicles[0];
    for (let vehicle of suitableVehicles) {
        if (vehicle.loadWeightRange[1] < minVehicle.loadWeightRange[1] && 
            vehicle.loadVolumeRange[1] < minVehicle.loadVolumeRange[1]) {
            minVehicle = vehicle;
        }
    }

    // 高亮显示最小车型
    highlightSelectedVehicle(minVehicle.name);

    // 监听车型选择事件
    vehicleSelect.addEventListener("change", function () {
        updatePickupFee(warehouse, pickupLocation, this.value);
    });

    updatePickupFee(warehouse, pickupLocation, vehicleSelect.value);
}
/**
 * 突出显示所选车型行
 * @param {string} selectedVehicleName - 所选车型名称
 */
function highlightSelectedVehicle(selectedVehicleName) {
    const vehicleTableBody = document.getElementById("vehicle-table-body");
    const rows = vehicleTableBody.getElementsByTagName("tr");

    // 遍历所有行，移除高亮样式
    for (let row of rows) {
        row.classList.remove("highlight-red");
    }

    // 找到所选车型的行并添加高亮样式
    for (let row of rows) {
        const vehicleName = row.cells[0].textContent;
        if (vehicleName === selectedVehicleName) {
            row.classList.add("highlight-red");
            break;
        }
    }
}

/**
 * 更新提货费
 * @param {string} selectedVehicleName - 所选车型名称
 */
function updatePickupFee(warehouse, pickupLocation, selectedVehicle) {
    const vehicles = window.data.pickupFee[warehouse]?.pickupLocations[pickupLocation] || [];
    const selectedVehicleInfo = vehicles.find(vehicle => vehicle.vehicle === selectedVehicle);

    if (selectedVehicleInfo) {
        document.getElementById("pickup-fee-display").value = selectedVehicleInfo.fee;
    } else {
        document.getElementById("pickup-fee-display").value = "";
    }
}

