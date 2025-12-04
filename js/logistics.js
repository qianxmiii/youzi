/**
 * logistics.js 物流相关功能
 */

// 新增常量 exchange_rate
const exchange_rate = 7.05; //美元汇率
const cost_exchange_rate = 7.15; //美元汇率
let valid_date = ''; //报价有效日期
const LINE_BREAK = '\n';
let addFee = new Decimal(0); //其他费用
const receiver = "Dear";

// 引入 data.js 中的数组
const {deliveryMethodsByCountry, quickReplies} = window.data;

// 页面加载时初始化
window.onload = function () {

    // 获取下一个星期五的日期
    // valid_date = getNextFriday();
    valid_date = "12/6";

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
    // 初始化
    initQuickReplyCategories();
    // 初始化车型查询 Tab
    initVehicleTab();
    // 初始化Tab 常用地址簿
    initAddressBook();
    // 初始化产品选择下拉框
    initProductSelect();
    // 初始化分泡比例控制
    initVolumeRatioControl();
}


/**
 * 监听输入
 */
function eventListener() {
    // 监听渠道下拉选项的变化
    document.getElementById("t4_channel").addEventListener("change", renderPriceTable());
    
    // 监听备注框 Ctrl+C 复制触发保存报价历史
    const notesEl = document.getElementById('notes');
    if (notesEl) {
        notesEl.addEventListener('keydown', function(e) {
            const isCtrlC = (e.ctrlKey || e.metaKey) && (e.key === 'c' || e.key === 'C' || e.keyCode === 67);
            if (isCtrlC) {
                setTimeout(() => {
                    if (typeof saveQuoteHistory === 'function') {
                        saveQuoteHistory();
                    }
                }, 0);
            }
        });
    }
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
    
    // 显示派送方式提示信息
    showDeliveryMethodHint(deliveryMethod);
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

        // 计算材积重 (kg) —— 与派送方式联动（快递5000 使用 5000，否则使用 6000）
        let dimensionWeight = length
            .mul(width)
            .mul(height)
            .mul(quantity)
            .div(volumeRatio)
            .ceil(); // 向上取整

        // 检查派送方式为"快递派"时，调整实重和材积重
        if (deliveryMethod == "海派") {
            let minWeight = new Decimal(12).mul(quantity); // 最低实重和材积重要求
            if (rowWeight.lessThan(minWeight)) rowWeight = minWeight; // 更新实重
            if (dimensionWeight.lessThan(minWeight)) dimensionWeight = minWeight; // 更新材积重
        } else if (deliveryMethod == "空派") {
            let minWeight = new Decimal(10).mul(quantity); // 最低实重和材积重要求
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

        // 检查特殊尺寸（长宽高大于等于62cm）
        let lengthCell = row.querySelector('.length');
        let widthCell = row.querySelector('.width');
        let heightCell = row.querySelector('.height');
        let weightCell = row.querySelector('.weight');

        // 移除之前的整行样式
        row.classList.remove('special-size-warning');

        // 只给超过62cm的单元格添加样式
        if (length.greaterThanOrEqualTo(62)) {
            lengthCell.classList.add('special-size-warning');
        } else {
            lengthCell.classList.remove('special-size-warning');
        }

        if (width.greaterThanOrEqualTo(62)) {
            widthCell.classList.add('special-size-warning');
        } else {
            widthCell.classList.remove('special-size-warning');
        }

        if (height.greaterThanOrEqualTo(62)) {
            heightCell.classList.add('special-size-warning');
        } else {
            heightCell.classList.remove('special-size-warning');
        }

        // 检查单箱实重（大于等于22kg）
        if (weight.greaterThanOrEqualTo(22)) {
            weightCell.classList.add('single-weight-warning');
        } else {
            weightCell.classList.remove('single-weight-warning');
        }

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
    
    // 自动保存计算历史（延迟3秒保存，避免频繁保存）
    setTimeout(() => {
        if (typeof saveCalculationHistory === 'function') {
            saveCalculationHistory();
        }
    }, 3000);
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
    
    // 分泡计算
    const volumeRatioSelect = document.getElementById("volume-ratio-select");
    if (volumeRatioSelect && volumeRatioSelect.value) {
        const volumeRatio = parseFloat(volumeRatioSelect.value) / 100; // 转换为小数
        const actualWeight = new Decimal(data.totalWeight);
        const volumeWeight = new Decimal(dimensionWeight);
        
        // 应用分泡公式：实重 + (泡重 - 实重) × (1 - 分泡比例)
        if (volumeWeight.greaterThan(actualWeight)) {
            const volumeDifference = volumeWeight.minus(actualWeight);
            const discountFactor = new Decimal(1).minus(volumeRatio);
            const discountedVolume = volumeDifference.mul(discountFactor);
            chargeWeight = actualWeight.plus(discountedVolume).ceil(); // 向上取整
        }
    }
    
    if (data.channel.includes('express')) {
        let moqWeight = 0;
        let moqUnit = 0;
        if (data.channel == 'Air express') {
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
    
    // 更新分泡比例显示
    if (typeof toggleVolumeRatioVisibility === 'function') {
        toggleVolumeRatioVisibility();
    }

    // 泡比颜色设置和tooltip
    let volumeRatioInput = document.getElementById('volumeRatio');
    if (volumeRatio.greaterThanOrEqualTo(200)) { // 大于等于200时字体为绿色
        volumeRatioInput.style.color = 'green';
        
        // 从配置中获取tooltip内容
        const billingWeight = new Decimal(document.getElementById('chargeWeight').value || 0);
        const tooltipContent = getCarrierDiscountTooltip(volumeRatio, billingWeight);
        volumeRatioInput.setAttribute('data-bs-toggle', 'tooltip');
        volumeRatioInput.setAttribute('data-bs-placement', 'top');
        volumeRatioInput.setAttribute('data-bs-title', tooltipContent);
        volumeRatioInput.setAttribute('title', tooltipContent);
        
        // 初始化或更新tooltip
        const existingTooltip = bootstrap.Tooltip.getInstance(volumeRatioInput);
        if (existingTooltip) {
            existingTooltip.dispose();
        }
        new bootstrap.Tooltip(volumeRatioInput, {
            html: true,
            placement: 'top'
        });
    } else if (volumeRatio.lessThan(167)) { // 小于167时字体为蓝色
        volumeRatioInput.style.color = 'blue';
        // 移除tooltip
        volumeRatioInput.removeAttribute('data-bs-toggle');
        volumeRatioInput.removeAttribute('data-bs-placement');
        volumeRatioInput.removeAttribute('data-bs-title');
        volumeRatioInput.removeAttribute('title');
        const existingTooltip = bootstrap.Tooltip.getInstance(volumeRatioInput);
        if (existingTooltip) {
            existingTooltip.dispose();
        }
    } else {
        volumeRatioInput.style.color = ''; // 恢复默认颜色
        // 移除tooltip
        volumeRatioInput.removeAttribute('data-bs-toggle');
        volumeRatioInput.removeAttribute('data-bs-placement');
        volumeRatioInput.removeAttribute('data-bs-title');
        volumeRatioInput.removeAttribute('title');
        const existingTooltip = bootstrap.Tooltip.getInstance(volumeRatioInput);
        if (existingTooltip) {
            existingTooltip.dispose();
        }
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
    document.getElementById("unit_price").value = unitPriceRMB.toFixed(2);

    let unit = 'ctns ';
    if (data.totalQuantity <= 1) unit = 'ctn ';

    addFee = new Decimal(0); //每次初始化
    // 根据选择的备注格式动态生成备注内容
    if (data.quoteType === "通用") {
        // 构建备注内容
        notes = `To ${data.address},${data.totalQuantity.toFixed(0)}${unit}${data.totalWeight.toFixed(0)}kg ${data.totalVolume.toFixed(2)}cbm\n`;
        notes += data.isDDU ?  'DDU ': 'DDP ';
        notes += `${data.channel}: ${priceUsd} usd/kg * ${chargeWeight.toFixed(0)}kg = ${totalPriceUsd}usd `;
        notes += `${getTransitTime(data.country, data.channel, data.postcode, data.address)} days ${MOQ} `;
        if (data.isMOQ) notes += `MOQ is ${data.moqInput}kg `;
        if (data.isDDU) notes += getDDUFee(data.country, 1);
        if (data.isRemoteAddress && shippingChannels["快递派"].includes(data.channel)) notes += getRemoteAddressfee(data.totalQuantity);
        if (data.isOverSize) notes += getOverSizeFee(data.country, data.overSizeQuantity, "USD", data.overSizeFee);
        if (data.isOverWeight) notes += getOverWeightFee(data.country, data.overWeightQuantity, "USD", data.overWeightFee);
        if (data.pickupFeeCheck) notes += `\nPickup fee: ${pickUpFee} usd`;
        notes += `\nTotal fee: ${totalPriceUsd.add(pickUpFee).add(addFee)} usd`;

    } else if (data.quoteType === "通用-CBM") {
        // 构建备注内容
        notes = `To ${data.address},${data.totalQuantity.toFixed(0)}${unit}${data.totalWeight.toFixed(0)}kg ${data.totalVolume.toFixed(2)}cbm\n`;
        notes += data.isDDU ?  'DDU ': 'DDP ';
        notes += `${data.channel}: ${priceUsd} usd/cbm * ${chargeCBM}cbm = ${totalPriceUsd}usd `;
        notes += `${getTransitTime(data.country, data.channel, data.postcode, data.address)} days`;
        if (data.isDDU) notes += getDDUFee(data.country, 1);
        if (data.pickupFeeCheck) notes += `\nPickup fee: ${pickUpFee} usd`;
        notes += `\nTotal fee: ${totalPriceUsd.add(pickUpFee).add(addFee)} usd`;

    } else if (data.quoteType === "通用-单价") {
        // 构建备注内容
        notes = `${data.address} ${data.channel}: ${priceUsd} usd per kg `;
        notes += `${getTransitTime(data.country, data.channel, data.postcode, data.address)} days`;

    } else if (data.quoteType === "通用-RMB") {
        // 构建备注内容
        notes = `${data.address} ${data.totalQuantity.toFixed(0)}箱 ${data.totalWeight.toFixed(0)}kg ${data.totalVolume.toFixed(2)}cbm\n`;
        notes += data.isDDU ?  'DDU ': 'DDP ';
        notes += `${getCN(data.channel)}: ${priceRmb}RMB/kg * ${chargeWeight.toFixed(0)}kg = ${totalPriceRMB}RMB `;
        notes += `${getTransitTime(data.country, data.channel, data.postcode, data.address)} 天 ${MOQ} `;
        if (data.isDDU) notes += getDDUFee(data.country, 0);
        if (data.isRemoteAddress && shippingChannels["快递派"].includes(data.channel)) notes += getRemoteAddressfee(data.totalQuantity,"RMB");
        if (data.isOverSize) notes += getOverSizeFee(data.country, data.overSizeQuantity, "RMB", data.overSizeFee);
        if (data.isOverWeight) notes += getOverWeightFee(data.country, data.overWeightQuantity, "RMB", data.overWeightFee);
        if (data.pickupFeeCheck) notes += `\n提货费: ${pickupFeeRMB} RMB`;
        notes += `\n总费用: ${totalPriceRMB.add(pickupFeeRMB).add(addFee)} RMB`;

    } else if (data.quoteType === "通用-RMB-CBM") {
        // 构建备注内容
        notes = `${data.address} ${data.totalQuantity.toFixed(0)}箱 ${data.totalWeight.toFixed(0)}kg ${data.totalVolume.toFixed(2)}cbm\n`;
        notes += data.isDDU ?  'DDU ': 'DDP ';
        notes += `${getCN(data.channel)}: ${priceRmb}RMB/cbm * ${chargeCBM}cbm = ${totalPriceRMB}RMB `;
        notes += `${getTransitTime(data.country, data.channel, data.postcode, data.address)} 天 ${MOQ} `;
        if (data.isDDU) notes += getDDUFee(data.country, 0); 
        if (data.pickupFeeCheck) notes += `\n提货费: ${pickupFeeRMB} RMB`;
        notes += `\n总费用: ${totalPriceRMB.add(pickupFeeRMB).add(addFee)} RMB`;

    } else if (data.quoteType === "PROBOXX") {
        // 构建备注内容
        notes = `${receiver},\n\n`;
        notes += `To ${data.address},${data.totalQuantity.toFixed(0)}${unit}${data.totalWeight.toFixed(0)}kg ${data.totalVolume.toFixed(2)}cbm\n`;
        notes += data.isDDU ?  'DDU ': 'DDP ';
        notes += `${data.channel}: ${priceUsd} usd/kg * ${chargeWeight.toFixed(0)}kg = ${totalPriceUsd}usd `;
        notes += `${getTransitTime(data.country, data.channel, data.postcode, data.address)} days ${MOQ} `;
        if (data.isMOQ) notes += `MOQ is ${data.moqInput}kg `;
        if (data.isRemoteAddress && shippingChannels["快递派"].includes(data.channel)) notes += getRemoteAddressfee(data.totalQuantity);
        if (data.isDDU) notes += getDDUFee(data.country, 1);
        if (data.isOverSize) notes += getOverSizeFee(data.country, data.overSizeQuantity, "USD", data.overSizeFee);
        if (data.isOverWeight) notes += getOverWeightFee(data.country, data.overWeightQuantity, "USD", data.overWeightFee);
        if (data.pickupFeeCheck) notes += `\nPickup fee: ${pickUpFee} usd`;
        notes += `\nTotal fee: ${totalPriceUsd.add(pickUpFee).add(addFee)} usd\n\nValid date: ${valid_date} `;
    } else if (data.quoteType === "PROBOXX-CBM") {
        // 构建备注内容
        notes = `${receiver},\n\n`;
        notes += `To ${data.address},${data.totalQuantity.toFixed(0)}${unit}${data.totalWeight.toFixed(0)}kg ${data.totalVolume.toFixed(2)}cbm\n`;
        notes += data.isDDU ? 'DDU ' : 'DDP ';
        notes += `${data.channel}: ${priceUsd} usd/cbm * ${chargeCBM}cbm = ${totalPriceUsd}usd `;
        notes += `${getTransitTime(data.country, data.channel, data.postcode, data.address)} days`;
        if (data.isDDU) notes += getDDUFee(data.country, 1);
        if (data.pickupFeeCheck) notes += `\nPickup fee: ${pickUpFee} usd`;
        notes += `\nTotal fee: ${totalPriceUsd.add(pickUpFee).add(addFee)} usd\n\nValid date: ${valid_date} `;
    } else if (data.quoteType === "163") {
        // 构建备注内容
        notes = `${data.address} = ${data.totalQuantity.toFixed(0)}${unit}${data.totalWeight.toFixed(0)}kg ${data.totalVolume.toFixed(2)}cbm\n`;
        if (data.isDDU) notes += 'DDU ';
        notes += `${data.channel}: ${priceUsd} usd/kg * ${chargeWeight.toFixed(0)}kg = ${totalPriceUsd}usd `;
        notes += `${getTransitTime(data.country, data.channel, data.postcode, data.address)} days ${MOQ} `;
        if (data.isMOQ) notes += `MOQ is ${data.moqInput}kg `;
        if (data.isDDU) notes += getDDUFee(data.country, 1);
        if (data.isRemoteAddress && shippingChannels["快递派"].includes(data.channel)) notes += getRemoteAddressfee(data.totalQuantity);
        if (data.isOverSize) notes += getOverSizeFee(data.country, data.overSizeQuantity, "USD", data.overSizeFee);
        if (data.isOverWeight) notes += getOverWeightFee(data.country, data.overWeightQuantity, "USD", data.overWeightFee);
        if (data.pickupFeeCheck) notes += `\nPickup fee: ${pickUpFee} usd`;

    } else if (data.quoteType === "161") {
        // 构建备注内容
        notes = `To ${data.address} ${data.totalQuantity.toFixed(0)}${unit}${data.totalWeight.toFixed(0)}kg ${data.totalVolume.toFixed(2)}cbm\n`;
        if (data.isDDU) notes += 'DDU ';
        notes += `${data.channel}: ${totalPriceUsd}usd `;
        notes += `${getTransitTime(data.country, data.channel, data.postcode, data.address)} days ${MOQ} `;
        if (data.isMOQ) notes += `MOQ is ${data.moqInput}kg `;
        if (data.isDDU) notes += getDDUFee(data.country, 1);
        if (data.isRemoteAddress && shippingChannels["快递派"].includes(data.channel)) notes += getRemoteAddressfee(data.totalQuantity);
        if (data.isOverSize) notes += getOverSizeFee(data.country, data.overSizeQuantity, "USD", data.overSizeFee);
        if (data.isOverWeight) notes += getOverWeightFee(data.country, data.overWeightQuantity, "USD", data.overWeightFee);
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
    const rows = input.split(/\||== LCL Load Item|== Air Load Item/).map(row => row.trim()).filter(row => row); // 过滤掉空字符串

    // 获取表格的 tbody 元素
    const tableBody = document.getElementById("box-table");

    // 清除表格中除第一行外的所有行
    while (tableBody.rows.length > 1) {
        tableBody.deleteRow(1);
    }

    // 行号计数器，用于正确编号
    let rowNumber = 0;

    // 处理每一行数据
    rows.forEach((row, index) => {

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

        // 增加行号计数器
        rowNumber++;

        // 获取当前行（如果需要，添加新行）
        let currentRow;
        if (rowNumber === 1) {
            currentRow = tableBody.rows[0]; // 第一行直接使用
            // 更新第一行的编号
            currentRow.querySelector('.index-cell').textContent = rowNumber;
        } else {
            currentRow = tableBody.insertRow(); // 添加新行
            currentRow.classList.add('input-row');
            currentRow.innerHTML = `
                <td class="index-cell">${rowNumber}</td>
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

// 调整所有箱规的尺寸（运输后尺寸增加）
function adjustDimensions(increment) {
    // 获取所有输入行
    const rows = document.querySelectorAll('.input-row');
    
    // 遍历每一行
    rows.forEach(row => {
        // 获取长、宽、高输入框
        const lengthInput = row.querySelector('.length');
        const widthInput = row.querySelector('.width');
        const heightInput = row.querySelector('.height');
        
        // 获取当前值并增加（只处理有值的输入框）
        if (lengthInput && lengthInput.value && !isNaN(parseFloat(lengthInput.value))) {
            const currentLength = parseFloat(lengthInput.value);
            lengthInput.value = (currentLength + increment).toFixed(1);
        }
        
        if (widthInput && widthInput.value && !isNaN(parseFloat(widthInput.value))) {
            const currentWidth = parseFloat(widthInput.value);
            widthInput.value = (currentWidth + increment).toFixed(1);
        }
        
        if (heightInput && heightInput.value && !isNaN(parseFloat(heightInput.value))) {
            const currentHeight = parseFloat(heightInput.value);
            heightInput.value = (currentHeight + increment).toFixed(1);
        }
    });
    
    // 重新计算
    calculate();
}

// 识别地址、箱数、重量、体积信息
function parsePackageInfo() {
    const input = document.getElementById("package-info-input").value.trim();
    // 使用正则表达式解析箱数、重量、体积、尺寸
    const volumeRegex = /([\d.]+)\s*(cbm|方)/i;
    const weightRegex = /([\d.]+)\s*(kg|kgs|lb|lbs|磅)/i;
    const quantityRegex = /(\d+)\s*(X|\s*)\s*(BOX|BOXES|Boxs|CARTON|CARTONS|ctn|ctns|件|箱|pal|pallets|托)/i;
    // 尺寸识别正则表达式，支持各种分隔符和单位
    const dimensionRegex = /(\d+(?:\.\d+)?)\s*[*xX×]\s*(\d+(?:\.\d+)?)\s*[*xX×]\s*(\d+(?:\.\d+)?)\s*(cm|inch|in|英寸)?/i;
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
        
        // 如果识别到尺寸但没有识别到体积，自动计算体积
        if (volume === 0 && quantity > 0) {
            volume = (length * width * height * quantity) / 1000000; // 转换为cbm
        }
    }

    // 识别地址代码
    // 识别地址代码（适配新版 addressByCountry 结构）
    const addressMatch = input.match(addressRegex);
    if (addressMatch) {
        const addressCode = addressMatch[0].toUpperCase();
        let found = false;
        
        // 记录当前国家，用于检测是否发生变化
        const currentCountry = document.getElementById('country-select').value;
        
        // 遍历所有国家查找匹配
        for (const country in addressByCountry) {
            if (addressByCountry[country][addressCode]) {
                document.getElementById('address').value = addressCode;
                document.getElementById('postcode').value = addressByCountry[country][addressCode];
                document.getElementById('country-select').value = country;
                found = true;
                
                // 只有国家发生变化时才更新运输方式
                if (currentCountry !== country) {
                    updateDeliveryMethods();
                }
                // 检查邮编是否为偏远地区
                checkRemoteAddress();
                break;
            }
        }
        
        // 未匹配时的处理（可选）
        if (!found) {
            document.getElementById('address').value = addressCode;
            const defaultCountry = "美国";
            document.getElementById('country-select').value = defaultCountry;
            
            // 只有国家发生变化时才更新运输方式
            if (currentCountry !== defaultCountry) {
                updateDeliveryMethods();
            }
            // 检查邮编是否为偏远地区（即使未匹配，也可能输入的是邮编）
            checkRemoteAddress();
        }
    }

    document.getElementById('quantity').value = quantity;
    document.getElementById('weight').value = Math.ceil(weight);
    document.getElementById('volume').value = new Decimal(volume).toDecimalPlaces(2, Decimal.ROUND_UP);
    
    // 触发计算
    updateQuote();
}

// 检查成本输入，当渠道不为Air express且美元复选框选中时，如果成本超过3显示友好提示
function checkCostInput() {
    const channel = document.getElementById("delivery-method-select").value;
    const isUSD = document.getElementById('USD_check').checked;
    const costValue = parseFloat(document.getElementById("cost_rmb").value) || 0;
    const costInput = document.getElementById("cost_rmb");
    
    // 当渠道不为Air express且美元复选框选中时
    if (!channel.includes("Air express") && isUSD && costValue > 3) {
        // 显示友好提示
        showCostInputWarning();
        // 同时给输入框添加视觉提示
        costInput.style.borderColor = "#ffc107";
        costInput.style.backgroundColor = "#fff3cd";
    } else {
        // 隐藏提示
        hideCostInputWarning();
        // 恢复输入框样式
        costInput.style.borderColor = "";
        costInput.style.backgroundColor = "";
    }
}

// 显示成本输入警告
function showCostInputWarning() {
    const existingWarning = document.getElementById("cost-input-warning");
    
    if (!existingWarning) {
        // 创建toast通知
        const toast = document.createElement("div");
        toast.id = "cost-input-warning";
        toast.className = "toast align-items-center text-bg-warning border-0";
        toast.setAttribute("role", "alert");
        toast.setAttribute("aria-live", "assertive");
        toast.setAttribute("aria-atomic", "true");
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 1050;
            min-width: 300px;
        `;
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <i class="bi bi-exclamation-triangle me-2"></i>
                    您输入的是RMB但美元复选框已勾选，请检查是否需要取消美元复选框
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        
        // 将toast添加到body中
        document.body.appendChild(toast);
        
        // 初始化并显示toast
        const bsToast = new bootstrap.Toast(toast, {
            autohide: true,
            delay: 3000
        });
        bsToast.show();
        
        // toast隐藏后自动移除元素
        toast.addEventListener('hidden.bs.toast', function () {
            toast.remove();
        });
    }
}

// 隐藏成本输入警告
function hideCostInputWarning() {
    const existingWarning = document.getElementById("cost-input-warning");
    if (existingWarning) {
        existingWarning.remove();
    }
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
        overSizeFee: parseFloat(document.getElementById('oversize-input').value) || 0,
        isOverWeight: document.getElementById('overweight_check').checked,
        overWeightQuantity: new Decimal(document.getElementById('overweight-quantity').value || 0),
        overWeightFee: parseFloat(document.getElementById('overweight-input').value) || 0,
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
             || channel == 'Super sea express'){
                channel = "美森正班";
        } else if (channel == 'Normal sea express' || channel == 'Normal Maston express') {
            channel = "美森加班";
        } else if (channel == 'Sea express') {
            channel = "普船";
        } else if (channel == 'Air express') {
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

// 初始化成本提示功能
function initCostTooltip() {
    // 获取成本列的 Tooltip 元素
    const costTooltip = document.getElementById("cost-tooltip");
    
    if (!costTooltip) {
        console.warn('成本提示元素未找到，将在DOM加载完成后重试');
        return;
    }

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
            let tooltipInstance = bootstrap.Tooltip.getInstance(costTooltip);
            if (!tooltipInstance) {
                tooltipInstance = new bootstrap.Tooltip(costTooltip, {
                    placement: "top",
                    trigger: "hover",
                    title: `${cost}`
                });
            } else {
                tooltipInstance.setContent({ '.tooltip-inner': `${cost}` });
            }
            tooltipInstance.show();
        }
    });

    // 监听鼠标离开事件
    costTooltip.addEventListener("mouseleave", function () {
        const tooltipInstance = bootstrap.Tooltip.getInstance(costTooltip);
        if (tooltipInstance) {
            tooltipInstance.hide();
        }
    });
}

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

// 初始化提货费提示功能
function initPickupFeeTooltip() {
    // 获取提货费输入框元素
    const pickupFeeInput = document.getElementById("pickup-fee");
    
    if (!pickupFeeInput) {
        console.warn('提货费提示元素未找到，将在DOM加载完成后重试');
        return;
    }

    // 监听鼠标悬停事件
    pickupFeeInput.addEventListener("mouseenter", function () {
        // 获取实重和方数
        const totalWeight = parseFloat(document.getElementById("weight").value) || 0;
        const totalVolume = parseFloat(document.getElementById("volume").value) || 0;

        // 获取可选车型
        const availableVehicles = getAvailableVehicles(totalWeight, totalVolume);

        // 生成 Tooltip 内容
        let tooltipContent = "可选车型：<br>";
        if (availableVehicles.length > 0) {
            availableVehicles.forEach((vehicle, index) => {
                if (index === 0) {
                    // 第一行特殊显示 - 推荐车型
                    tooltipContent += `<strong style="color:rgb(181, 176, 174);">★ ${vehicle.name}</strong><span style="color: #ff6600;">（载重：${vehicle.loadWeightRange[0]}~${vehicle.loadWeightRange[1]}kg，载方：${vehicle.loadVolumeRange[0]}~${vehicle.loadVolumeRange[1]}cbm）</span><br>`;
                } else {
                    // 其他行正常显示
                    tooltipContent += `- ${vehicle.name}（载重：${vehicle.loadWeightRange[0]}~${vehicle.loadWeightRange[1]}kg，载方：${vehicle.loadVolumeRange[0]}~${vehicle.loadVolumeRange[1]}cbm）<br>`;
                }
            });
        } else {
            tooltipContent = "无合适车型，请调整重量或方数。";
        }

        // 设置 Tooltip 内容
        const tooltipInstance = bootstrap.Tooltip.getInstance(pickupFeeInput);
        if (tooltipInstance) {
            tooltipInstance.dispose(); // 销毁现有实例
        }
        
        // 重新初始化 Tooltip
        new bootstrap.Tooltip(pickupFeeInput, {
            title: tooltipContent,
            placement: "top", // Tooltip 显示在顶部
            trigger: "hover",  // 鼠标悬停时显示
            html: true // 支持HTML内容
        });
        
        // 显示tooltip
        const newTooltipInstance = bootstrap.Tooltip.getInstance(pickupFeeInput);
        if (newTooltipInstance) {
            newTooltipInstance.show();
            
            // 等待tooltip显示后设置样式
            setTimeout(() => {
                const tooltipElement = document.querySelector('.tooltip');
                if (tooltipElement) {
                    const tooltipInner = tooltipElement.querySelector('.tooltip-inner');
                    if (tooltipInner) {
                        // 设置tooltip样式
                        tooltipInner.style.backgroundColor = '#fff';
                        tooltipInner.style.color = '#495057';
                        tooltipInner.style.border = '2px solidrgb(164, 159, 156)';
                        tooltipInner.style.borderRadius = '8px';
                        tooltipInner.style.boxShadow = '0 4px 12px rgba(175, 166, 161, 0.3)';
                        tooltipInner.style.fontSize = '0.85rem';
                        tooltipInner.style.padding = '0.75rem 1rem';
                        tooltipInner.style.maxWidth = '500px';
                        tooltipInner.style.minWidth = '350px';
                        tooltipInner.style.textAlign = 'left';
                        tooltipInner.style.lineHeight = '1.4';
                        
                        // 设置推荐车型的样式
                        const strongElements = tooltipInner.querySelectorAll('strong');
                        strongElements.forEach(strong => {
                            strong.style.color = '#ff6600';
                            strong.style.fontWeight = 'bold';
                        });
                        
                        // 设置推荐车型信息的样式
                        const spanElements = tooltipInner.querySelectorAll('span');
                        spanElements.forEach(span => {
                            span.style.color = '#ff6600';
                            span.style.fontWeight = 'normal';
                        });
                    }
                }
            }, 10);
        }
    });

    // 监听鼠标离开事件
    pickupFeeInput.addEventListener("mouseleave", function () {
        const tooltipInstance = bootstrap.Tooltip.getInstance(pickupFeeInput);
        if (tooltipInstance) {
            tooltipInstance.hide();
        }
    });
}

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

/**
 * 一键清空箱规表格
 */
function clearBoxTable() {
    // 清空箱规识别输入框
    document.getElementById('dimension-input').value = '';
    
    // 获取表格的 tbody 元素
    const tableBody = document.getElementById("box-table");
    
    // 清除表格中除第一行外的所有行
    while (tableBody.rows.length > 1) {
        tableBody.deleteRow(1);
    }
    
    // 清空第一行的所有输入框
    const firstRow = tableBody.rows[0];
    firstRow.querySelector('.length').value = '';
    firstRow.querySelector('.width').value = '';
    firstRow.querySelector('.height').value = '';
    firstRow.querySelector('.weight').value = '';
    firstRow.querySelector('.quantity').value = '';
    
    // 清空第一行的结果显示
    firstRow.querySelector('.result-cell:nth-child(7)').innerText = '0.00 cbm';
    firstRow.querySelector('.result-cell:nth-child(8)').innerText = '0 kg';
    firstRow.querySelector('.result-cell:nth-child(9)').innerText = '0 kg';
    firstRow.querySelector('.result-cell:nth-child(10)').innerText = '0 kg';
    firstRow.querySelector('.result-cell:nth-child(11)').innerText = '0 cm';
    
    // 移除所有警告样式
    firstRow.classList.remove('special-size-warning');
    firstRow.querySelector('.length').classList.remove('special-size-warning');
    firstRow.querySelector('.width').classList.remove('special-size-warning');
    firstRow.querySelector('.height').classList.remove('special-size-warning');
    firstRow.querySelector('.weight').classList.remove('single-weight-warning');
    
    // 重置总计数据
    document.getElementById('total-volume').innerText = '0.00';
    document.getElementById('total-weight').innerText = '0';
    document.getElementById('total-quantity').innerText = '0';
    document.getElementById('total-dimension-weight').innerText = '0';
    document.getElementById('billing-weight').innerText = '0';
    document.getElementById('volume-ratio').innerText = '0.00';
    
    // 清空汇总信息
    document.getElementById('summary-size').innerText = '[length]*[width]*[height]cm';
    document.getElementById('summary-chargeweight').innerText = '0';
    document.getElementById('summary-desc').innerText = '0ctns 0kg 0cbm';
    
    // 清空警告信息
    const warningsTextarea = document.getElementById('box-warnings');
    if (warningsTextarea) {
        warningsTextarea.value = '✓ 所有箱规符合要求';
        warningsTextarea.classList.replace('has-warnings', 'no-warnings');
    }
    
    // 隐藏警告按钮
    const warningsToggle = document.getElementById('warningsToggle');
    if (warningsToggle) {
        warningsToggle.style.display = 'none';
    }
    
    // 收起警告框
    const warningsCollapse = new bootstrap.Collapse('#warningsCollapse', {
        toggle: false
    });
    warningsCollapse.hide();
}

/**
 * 保存报价历史记录
 */
function saveQuoteHistory() {
    try {
        // 获取当前报价的所有数据
        const quoteData = {
            id: generateQuoteId(),
            timestamp: new Date().toLocaleString('zh-CN'),
            
            // 基础信息
            address: (document.getElementById('address').value || '').toUpperCase(),
            postcode: document.getElementById('postcode').value || '',
            country: document.getElementById('country-select').value || '',
            deliveryMethod: document.getElementById('delivery-method-select').value || '',
            origin: document.getElementById('origin-select').value || '',
            
            // 货物信息
            quantity: parseFloat(document.getElementById('quantity').value) || 0,
            weight: parseFloat(document.getElementById('weight').value) || 0,
            volume: parseFloat(document.getElementById('volume').value) || 0,
            
            // 费用信息
            costRmb: parseFloat(document.getElementById('cost_rmb').value) || 0,
            profitRmb: parseFloat(document.getElementById('profit_rmb').value) || 0,
            priceRmb: parseFloat(document.getElementById('price_rmb').value) || 0,
            priceUsd: parseFloat(document.getElementById('price_usd').value) || 0,
            
            // 特殊选项
            isRemote: document.getElementById('remote-address').checked || false,
            hasBattery: document.getElementById('battery_check').checked || false,
            isOversize: document.getElementById('oversize_check').checked || false,
            oversizeFee: parseFloat(document.getElementById('oversize-input').value) || 0,
            oversizeQuantity: parseFloat(document.getElementById('oversize-quantity').value) || 0,
            isOverweight: document.getElementById('overweight_check').checked || false,
            overweightFee: parseFloat(document.getElementById('overweight-input').value) || 0,
            overweightQuantity: parseFloat(document.getElementById('overweight-quantity').value) || 0,
            isMOQ: document.getElementById('MOQ').checked || false,
            moqValue: parseFloat(document.getElementById('moq-input').value) || 0,
            hasPickupFee: document.getElementById('pickup-fee-checkbox').checked || false,
            pickupFeeRmb: parseFloat(document.getElementById('pickup-fee').value) || 0,
            pickupFeeUsd: parseFloat(document.getElementById('pickup-fee-USD').value) || 0,
            isDDU: document.getElementById('ddu_check').checked || false,
            isUSD: document.getElementById('USD_check').checked || false,
            
            // 计算结果
            chargeWeight: parseFloat(document.getElementById('chargeWeight').value) || 0,
            chargeCBM: parseFloat(document.getElementById('chargeCBM').value) || 0,
            volumeRatio: parseFloat(document.getElementById('volumeRatio').value) || 0,
            totalPriceUsd: parseFloat(document.getElementById('total_price_usd').value) || 0,
            totalPriceRmb: parseFloat(document.getElementById('total_price_rmb').value) || 0,
            unitPriceRmb: parseFloat(document.getElementById('unit_price').value) || 0,
            
            // 报价格式
            quoteType: document.getElementById('quote-type').value || '通用',
            notes: document.getElementById('notes').value || ''
        };
        
        // 获取现有历史记录
        let history = JSON.parse(localStorage.getItem('quoteHistory') || '[]');
        
        // 添加新记录到开头
        history.unshift(quoteData);
        
        // 限制历史记录数量（最多保存100条）
        if (history.length > 100) {
            history = history.slice(0, 100);
        }
        
        // 保存到localStorage
        localStorage.setItem('quoteHistory', JSON.stringify(history));
        
        console.log('报价历史记录已保存:', quoteData.id);
        
    } catch (error) {
        console.error('保存报价历史记录失败:', error);
    }
}

/**
 * 生成报价ID
 */
function generateQuoteId() {
    const now = new Date();
    const dateStr = now.getFullYear().toString() + 
                   (now.getMonth() + 1).toString().padStart(2, '0') + 
                   now.getDate().toString().padStart(2, '0');
    const timeStr = now.getHours().toString().padStart(2, '0') + 
                   now.getMinutes().toString().padStart(2, '0') + 
                   now.getSeconds().toString().padStart(2, '0');
    return `quote_${dateStr}_${timeStr}`;
}

/**
 * 加载报价历史记录
 */
function loadQuoteHistory() {
    try {
        const history = JSON.parse(localStorage.getItem('quoteHistory') || '[]');
        renderQuoteHistoryTable(history);
        updateQuoteHistoryInfo(history.length);
    } catch (error) {
        console.error('加载报价历史记录失败:', error);
    }
}

/**
 * 渲染报价历史记录表格
 */
function renderQuoteHistoryTable(history, page = 1, pageSize = 10) {
    const tbody = document.getElementById('quoteHistoryTableBody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    if (history.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" class="text-center text-muted">暂无历史记录</td></tr>';
        return;
    }
    
    // 分页处理
    const startIndex = (page - 1) * pageSize;
    const endIndex = startIndex + pageSize;
    const pageData = history.slice(startIndex, endIndex);
    
    pageData.forEach(record => {
        const row = document.createElement('tr');
        // 构建费用显示信息
        let feeInfo = [];
        if (record.hasPickupFee && (record.pickupFeeRmb > 0 || record.pickupFeeUsd > 0)) {
            const fees = [];
            if (record.pickupFeeRmb > 0) fees.push(`¥${record.pickupFeeRmb}`);
            if (record.pickupFeeUsd > 0) fees.push(`$${record.pickupFeeUsd}`);
            feeInfo.push(`<span class="badge bg-info">提货费: ${fees.join(' / ')}</span>`);
        }
        if (record.isOversize && record.oversizeFee > 0) {
            feeInfo.push(`<span class="badge bg-warning">超尺寸: ¥${record.oversizeFee}/箱</span>`);
        }
        if (record.isOverweight && record.overweightFee > 0) {
            feeInfo.push(`<span class="badge bg-danger">超重: ¥${record.overweightFee}/箱</span>`);
        }
        if (record.isMOQ && record.moqValue > 0) {
            feeInfo.push(`<span class="badge bg-secondary">MOQ: ${record.moqValue}kg</span>`);
        }
        
        // 构建运费、偏远、带电等状态信息
        let statusInfo = [];
        if (record.isRemote) {
            statusInfo.push(`<span class="badge bg-dark text-white" style="font-size: 0.7rem;">偏远</span>`);
        }
        if (record.hasBattery) {
            statusInfo.push(`<span class="badge bg-success text-white" style="font-size: 0.7rem;">带电</span>`);
        }
        if (record.isDDU) {
            statusInfo.push(`<span class="badge bg-primary text-white" style="font-size: 0.7rem;">DDU</span>`);
        }
        if (record.isUSD) {
            statusInfo.push(`<span class="badge bg-warning text-dark" style="font-size: 0.7rem;">USD</span>`);
        }
        
        const feeInfoHtml = feeInfo.join(' ');
        const statusInfoHtml = statusInfo.join(' ');
        
        row.innerHTML = `
            <td>${record.timestamp}</td>
            <td>${record.address}</td>
            <td>${record.country}</td>
            <td>${record.quantity}</td>
            <td>${record.weight}</td>
            <td>${record.volume}</td>
            <td>${record.priceUsd}</td>
            <td>
                <div style="font-weight: bold; font-size: 1.1rem; color: #dc3545; text-shadow: 1px 1px 2px rgba(0,0,0,0.1);">$${record.totalPriceUsd}</div>
                <div style="margin-top: 2px;">${statusInfoHtml}</div>
                <div style="margin-top: 2px;">${feeInfoHtml}</div>
            </td>
            <td>
                <button class="btn btn-sm btn-outline-primary" onclick="loadQuoteToForm('${record.id}')" title="加载到表单">
                    <i class="bi bi-arrow-clockwise"></i>
                </button>
                <button class="btn btn-sm btn-outline-danger" onclick="deleteQuoteHistory('${record.id}')" title="删除">
                    <i class="bi bi-trash"></i>
                </button>
            </td>
        `;
        tbody.appendChild(row);
    });
    
    // 更新分页信息
    updateQuoteHistoryPagination(history.length, page, pageSize);
}

/**
 * 更新报价历史记录信息
 */
function updateQuoteHistoryInfo(totalCount) {
    const infoElement = document.getElementById('quoteHistoryInfo');
    if (infoElement) {
        infoElement.textContent = `共 ${totalCount} 条记录`;
    }
}

/**
 * 更新报价历史记录分页
 */
function updateQuoteHistoryPagination(totalCount, currentPage, pageSize) {
    const totalPages = Math.ceil(totalCount / pageSize);
    const pageInfoElement = document.getElementById('quoteHistoryPageInfo');
    const prevBtn = document.getElementById('quoteHistoryPrev');
    const nextBtn = document.getElementById('quoteHistoryNext');
    
    if (pageInfoElement) {
        pageInfoElement.textContent = `第 ${currentPage} 页，共 ${totalPages} 页`;
    }
    
    if (prevBtn) {
        prevBtn.disabled = currentPage <= 1;
    }
    
    if (nextBtn) {
        nextBtn.disabled = currentPage >= totalPages;
    }
    
    // 保存当前分页状态
    window.currentQuoteHistoryPage = currentPage;
    window.currentQuoteHistoryPageSize = pageSize;
}

/**
 * 搜索报价历史记录
 */
function searchQuoteHistory() {
    const searchTerm = document.getElementById('quoteHistorySearch').value.toLowerCase();
    const countryFilter = document.getElementById('quoteHistoryCountry').value;
    const dateRange = document.getElementById('quoteHistoryDateRange').value;
    
    let history = JSON.parse(localStorage.getItem('quoteHistory') || '[]');
    
    // 应用筛选
    let filteredHistory = history.filter(record => {
        // 搜索词筛选
        const matchesSearch = !searchTerm || 
            record.address.toLowerCase().includes(searchTerm) ||
            record.postcode.toLowerCase().includes(searchTerm);
        
        // 国家筛选
        const matchesCountry = !countryFilter || record.country === countryFilter;
        
        // 日期筛选
        let matchesDate = true;
        if (dateRange !== 'all') {
            const recordDate = new Date(record.timestamp);
            const now = new Date();
            const daysDiff = (now - recordDate) / (1000 * 60 * 60 * 24);
            matchesDate = daysDiff <= parseInt(dateRange);
        }
        
        return matchesSearch && matchesCountry && matchesDate;
    });
    
    renderQuoteHistoryTable(filteredHistory, 1, 10);
    updateQuoteHistoryInfo(filteredHistory.length);
}

/**
 * 上一页
 */
function prevQuoteHistoryPage() {
    const currentPage = window.currentQuoteHistoryPage || 1;
    if (currentPage > 1) {
        const history = JSON.parse(localStorage.getItem('quoteHistory') || '[]');
        renderQuoteHistoryTable(history, currentPage - 1, 10);
    }
}

/**
 * 下一页
 */
function nextQuoteHistoryPage() {
    const currentPage = window.currentQuoteHistoryPage || 1;
    const history = JSON.parse(localStorage.getItem('quoteHistory') || '[]');
    const totalPages = Math.ceil(history.length / 10);
    
    if (currentPage < totalPages) {
        renderQuoteHistoryTable(history, currentPage + 1, 10);
    }
}

/**
 * 加载报价到表单
 */
function loadQuoteToForm(quoteId) {
    try {
        const history = JSON.parse(localStorage.getItem('quoteHistory') || '[]');
        const record = history.find(item => item.id === quoteId);
        
        if (!record) {
            showToast('未找到该报价记录', 'warning');
            return;
        }
        
        // 填充表单数据
        document.getElementById('address').value = record.address;
        document.getElementById('postcode').value = record.postcode;
        document.getElementById('country-select').value = record.country;
        document.getElementById('delivery-method-select').value = record.deliveryMethod;
        document.getElementById('origin-select').value = record.origin;
        
        document.getElementById('quantity').value = record.quantity;
        document.getElementById('weight').value = record.weight;
        document.getElementById('volume').value = record.volume;
        
        document.getElementById('cost_rmb').value = record.costRmb;
        document.getElementById('profit_rmb').value = record.profitRmb;
        
        // 设置特殊选项
        document.getElementById('remote-address').checked = record.isRemote;
        document.getElementById('battery_check').checked = record.hasBattery;
        document.getElementById('oversize_check').checked = record.isOversize;
        document.getElementById('oversize-input').value = record.oversizeFee || 0;
        document.getElementById('oversize-quantity').value = record.oversizeQuantity || 0;
        document.getElementById('overweight_check').checked = record.isOverweight;
        document.getElementById('overweight-input').value = record.overweightFee || 0;
        document.getElementById('overweight-quantity').value = record.overweightQuantity || 0;
        document.getElementById('MOQ').checked = record.isMOQ;
        document.getElementById('moq-input').value = record.moqValue || 0;
        document.getElementById('pickup-fee-checkbox').checked = record.hasPickupFee;
        document.getElementById('pickup-fee').value = record.pickupFeeRmb || 0;
        document.getElementById('pickup-fee-USD').value = record.pickupFeeUsd || 0;
        document.getElementById('ddu_check').checked = record.isDDU;
        document.getElementById('USD_check').checked = record.isUSD;
        
        // 触发各种输入框的显示/隐藏
        toggleOverSizeFeeInput();
        toggleOverWeightFeeInput();
        toggleMOQInput();
        togglePickupFeeInput();
        
        document.getElementById('quote-type').value = record.quoteType;
        document.getElementById('notes').value = record.notes;
        
        // 触发计算更新
        updateQuote();
        
        // 关闭模态框
        const modal = bootstrap.Modal.getInstance(document.getElementById('quoteHistoryModal'));
        if (modal) {
            modal.hide();
        }
        
        // 显示成功提示
        showToast('报价记录已加载到表单');
        
    } catch (error) {
        console.error('加载报价记录失败:', error);
        showToast('加载报价记录失败', 'error');
    }
}

/**
 * 删除报价历史记录
 */
function deleteQuoteHistory(quoteId) {
    if (!confirm('确定要删除这条报价记录吗？')) {
        return;
    }
    
    try {
        let history = JSON.parse(localStorage.getItem('quoteHistory') || '[]');
        history = history.filter(item => item.id !== quoteId);
        localStorage.setItem('quoteHistory', JSON.stringify(history));
        
        // 重新加载表格
        loadQuoteHistory();
        showToast('报价记录已删除');
        
    } catch (error) {
        console.error('删除报价记录失败:', error);
        showToast('删除报价记录失败', 'error');
    }
}

/**
 * 清空报价历史记录
 */
function clearQuoteHistory() {
    if (!confirm('确定要清空所有报价历史记录吗？此操作不可恢复！')) {
        return;
    }
    
    try {
        localStorage.removeItem('quoteHistory');
        loadQuoteHistory();
        showToast('所有报价历史记录已清空');
        
    } catch (error) {
        console.error('清空报价历史记录失败:', error);
        showToast('清空报价历史记录失败', 'error');
    }
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

/**
 * 显示提示信息
 */
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

// 页面加载完成后初始化报价历史记录功能
document.addEventListener('DOMContentLoaded', function() {
    // 初始化成本提示功能
    initCostTooltip();
    
    // 初始化提货费提示功能
    initPickupFeeTooltip();
    
    // 监听报价历史记录模态框的显示事件
    const quoteHistoryModal = document.getElementById('quoteHistoryModal');
    if (quoteHistoryModal) {
        quoteHistoryModal.addEventListener('shown.bs.modal', function() {
            loadQuoteHistory();
        });
    }
    
    // 监听搜索框的回车事件
    const searchInput = document.getElementById('quoteHistorySearch');
    if (searchInput) {
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                searchQuoteHistory();
            }
        });
    }
});
// ==================== 智能批量报价功能 ====================

/**
 * 批量报价数据
 */
let batchQuoteData = {
    boxSpec: null,
    addressDistribution: [],
    results: []
};

/**
 * 解析箱规信息
 */
function parseBatchBoxSpec() {
    const input = document.getElementById('batch-box-spec').value.trim();
    if (!input) {
        batchQuoteData.boxSpec = null;
        return;
    }
    
    // 使用更灵活的正则表达式解析箱规信息
    // 支持多种格式：45*45*50 10KG 50CTNS 或 45x45x50 10kg 50箱 等
    const dimensionRegex = /(\d+(?:\.\d+)?)\s*[*xX×]\s*(\d+(?:\.\d+)?)\s*[*xX×]\s*(\d+(?:\.\d+)?)\s*(cm|inch|in|英寸)?/i;
    const weightRegex = /([\d.]+)\s*(kg|kgs|lb|lbs|磅)/i;
    const quantityRegex = /(\d+)\s*(X|\s*)\s*(BOX|BOXES|Boxs|CARTON|CARTONS|ctn|ctns|件|箱|pal|pallets|托)/i;
    
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
    }
    
    // 提取重量信息
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
    
    // 提取箱数信息
    const quantityMatch = input.match(quantityRegex);
    let totalQuantity = 0;
    if (quantityMatch) {
        totalQuantity = parseInt(quantityMatch[1]);
    }
    
    // 验证是否成功解析了所有必要信息
    if (length > 0 && width > 0 && height > 0 && weight > 0 && totalQuantity > 0) {
        const volume = (length * width * height) / 1000000; // 转换为cbm
        
        batchQuoteData.boxSpec = {
            length: length,
            width: width,
            height: height,
            weight: weight,
            volume: volume,
            totalQuantity: totalQuantity
        };
        
        console.log('解析箱规成功:', batchQuoteData.boxSpec);
    } else {
        batchQuoteData.boxSpec = null;
        console.log('箱规格式不正确，请确保包含：长*宽*高 重量 总箱数');
    }
}

/**
 * 解析地址分配
 */
function parseBatchAddressDistribution() {
    const input = document.getElementById('batch-address-distribution').value.trim();
    if (!input) {
        batchQuoteData.addressDistribution = [];
        return;
    }
    
    // 解析格式：RDU4 4CTNS | AVP1 25CTNS | LAS1 20CTNS | GYR3 1CTNS
    const addressPairs = input.split('|').map(pair => pair.trim());
    const distribution = [];
    
    addressPairs.forEach(pair => {
        const regex = /([A-Z0-9]+)\s+(\d+)\s*(?:CTNS|ctns)?/i;
        const match = pair.match(regex);
        
        if (match) {
            const [, address, quantity] = match;
            distribution.push({
                address: address.toUpperCase(),
                quantity: parseInt(quantity)
            });
        }
    });
    
    batchQuoteData.addressDistribution = distribution;
}

/**
 * 获取选中的渠道
 */
function getSelectedChannels() {
    const checkboxes = document.querySelectorAll('input[type="checkbox"][value*="truck"], input[type="checkbox"][value*="express"]');
    const selectedChannels = [];
    checkboxes.forEach(checkbox => {
        if (checkbox.checked) {
            selectedChannels.push(checkbox.value);
        }
    });
    return selectedChannels;
}

/**
 * 检查是否需要显示发货区域选择
 */
function checkShippingRegionVisibility() {
    const selectedChannels = getSelectedChannels();
    const hasExpressChannel = selectedChannels.some(channel => 
        channel === 'Sea express' || channel === 'Fast sea express' || channel === 'Air express'
    );
    
    const regionContainer = document.getElementById('batch-shipping-region-container');
    if (regionContainer) {
        regionContainer.style.display = hasExpressChannel ? 'block' : 'none';
    }
}

/**
 * 添加渠道选择事件监听器
 */
function addChannelSelectionListeners() {
    const checkboxes = document.querySelectorAll('input[type="checkbox"][value*="truck"], input[type="checkbox"][value*="express"]');
    checkboxes.forEach(checkbox => {
        checkbox.addEventListener('change', checkShippingRegionVisibility);
    });
}

/**
 * 获取渠道徽章样式
 */
function getChannelBadgeClass(channel) {
    switch(channel) {
        case 'Sea truck':
            return 'bg-primary';
        case 'Fast sea truck':
            return 'bg-info';
        case 'Sea express':
            return 'bg-success';
        case 'Fast sea express':
            return 'bg-warning';
        case 'Air express':
            return 'bg-danger';
        default:
            return 'bg-secondary';
    }
}

/**
 * 获取邮编颜色编码
 */
function getPostcodeColorClass(postcode, channel) {
    if (channel !== 'Sea express' && channel !== 'Fast sea express' && channel !== 'Air express') {
        return '';
    }
    
    if (!postcode || postcode.length === 0) {
        return '';
    }
    
    const firstDigit = postcode.charAt(0);
    switch(firstDigit) {
        case '0':
        case '1':
        case '2':
        case '3':
            return 'text-danger fw-bold'; // 红色
        case '4':
        case '5':
        case '6':
        case '7':
            return 'text-warning fw-bold'; // 黄色
        case '9':
            if (postcode.startsWith('96') || postcode.startsWith('97') || postcode.startsWith('98') || postcode.startsWith('99')) {
                return 'text-info fw-bold'; // 蓝色
            }
            return 'text-primary fw-bold'; // 默认蓝色
        case '8':
        case '9':
            return 'text-primary fw-bold'; // 蓝色
        default:
            return '';
    }
}

/**
 * 检查邮编是否为偏远地区
 */
function isRemotePostcode(postcode) {
    if (!postcode || !window.remotePostcodes) {
        return false;
    }
    return window.remotePostcodes.includes(postcode);
}

/**
 * 获取地址显示内容（偏远地区添加图标）
 */
function getAddressDisplayContent(address, postcode, channel) {
    if (channel !== 'Sea express' && channel !== 'Fast sea express' && channel !== 'Air express') {
        return `<span class="fw-bold">${address}</span>`;
    }
    
    if (isRemotePostcode(postcode)) {
        return `<span class="position-relative fw-bold">
                    <i class="bi bi-geo-alt-fill text-danger position-absolute" style="top: -2px; left: -12px; font-size: 0.8rem;" title="偏远地区"></i>
                    ${address}
                </span>`;
    }
    
    return `<span class="fw-bold">${address}</span>`;
}

/**
 * 生成批量报价
 */
function generateBatchQuote() {
    if (!batchQuoteData.boxSpec) {
        showToast('请先输入箱规信息');
        return;
    }
    
    if (batchQuoteData.addressDistribution.length === 0) {
        showToast('请先输入地址分配');
        return;
    }
    
    // 验证总箱数是否匹配
    const totalDistributedQuantity = batchQuoteData.addressDistribution.reduce((sum, item) => sum + item.quantity, 0);
    if (totalDistributedQuantity !== batchQuoteData.boxSpec.totalQuantity) {
        showToast(`总箱数不匹配！箱规中总箱数：${batchQuoteData.boxSpec.totalQuantity}，分配箱数：${totalDistributedQuantity}`);
        return;
    }
    
    // 获取当前选择的渠道和发货地
    const selectedChannels = getSelectedChannels();
    const origin = document.getElementById('origin-select').value;
    const country = document.getElementById('country-select').value;
    
    if (selectedChannels.length === 0) {
        showToast('请至少选择一个渠道');
        return;
    }
    
    if (!origin) {
        showToast('请先选择发货地');
        return;
    }
    
    // 检查是否需要发货区域
    const hasExpressChannel = selectedChannels.some(channel => 
        channel === 'Sea express' || channel === 'Fast sea express' || channel === 'Air express'
    );
    
    if (hasExpressChannel) {
        const shippingRegion = document.getElementById('batch-shipping-region').value;
        if (!shippingRegion) {
            showToast('请选择发货区域');
            return;
        }
    }
    
    // 生成每个地址和每个渠道的报价
    const results = [];
    batchQuoteData.addressDistribution.forEach(item => {
        const totalWeight = new Decimal(batchQuoteData.boxSpec.weight).mul(new Decimal(item.quantity));
        const totalVolume = new Decimal(batchQuoteData.boxSpec.volume).mul(new Decimal(item.quantity));
        const chargeWeight = Decimal.max(totalWeight, totalVolume.mul(new Decimal(1000000)).div(new Decimal(6000))).ceil();
        const profit = new Decimal(document.getElementById('batch-profit').value || 0);

        // 遍历所有国家查找匹配
        let matchedCountry = "美国"; // 默认国家
        let postcode = "";

        for (const [country, postalMap] of Object.entries(addressByCountry)) {
            if (postalMap[item.address]) {
                matchedCountry = country;
                postcode = postalMap[item.address];
                break; // 找到后立即退出循环
            }
        }
        
        // 为每个选中的渠道生成报价
        selectedChannels.forEach(channel => {
            // 计算成本
            let unitCostRMB;
            
            // 对于Sea/Air express类渠道，使用showCost函数计算
            if (channel === 'Sea express' || channel === 'Fast sea express' || channel === 'Air express') {
                const shippingRegion = document.getElementById('batch-shipping-region').value;
                const withBattery = false; // 默认不带电池
                unitCostRMB = showCost(shippingRegion, matchedCountry, channel, postcode, totalWeight, withBattery) || 0;
            } else if (seaTruckPrice[item.address + (channel === 'Fast sea truck' ? ' Fast' : '')] !== undefined) {
                unitCostRMB = seaTruckPrice[item.address + (channel === 'Fast sea truck' ? ' Fast' : '')];
            } else {
                unitCostRMB = 0;
            }
            
            // 计算利润和报价
            const unitProfitRMB = new Decimal(profit);
            const unitPriceRMB = new Decimal(unitCostRMB).plus(unitProfitRMB);
            const unitPrice = new Decimal(unitPriceRMB).div(new Decimal(exchange_rate)).toFixed(2); //转换成美元
            const totalPrice = new Decimal(unitPrice).mul(new Decimal(chargeWeight)); // 使用计费重计算总价
            const transitTime = getTransitTime(matchedCountry, channel, postcode, item.address);
        
        results.push({
            address: item.address,
            postcode: postcode,
                channel: channel,
            quantity: item.quantity,
            singleWeight: batchQuoteData.boxSpec.weight,
            singleVolume: batchQuoteData.boxSpec.volume,
            totalWeight: totalWeight,
            totalVolume: totalVolume,
            chargeWeight: chargeWeight,
                unitCostRMB: unitCostRMB, // 成本RMB
                unitProfitRMB: unitProfitRMB.toNumber(), // 利润RMB
                unitPriceRMB: unitPriceRMB.toNumber(), // 报价RMB
                unitPrice: unitPrice, // 报价USD
            totalPrice: totalPrice,
            transitTime: transitTime
            });
        });
    });
    
    batchQuoteData.results = results;
    renderBatchQuoteTable();
    
    // 显示表格，隐藏空状态
    document.getElementById('batch-quote-tables-container').style.display = 'block';
    document.getElementById('batch-quote-empty-state').style.display = 'none';
    
    showToast('批量报价生成完成');
}

/**
 * 渲染批量报价表格
 */
function renderBatchQuoteTable() {
    const container = document.getElementById('batch-quote-tables-container');
    container.innerHTML = '';
    
    // 按渠道分组
    const channelGroups = {};
    batchQuoteData.results.forEach((item, index) => {
        if (!channelGroups[item.channel]) {
            channelGroups[item.channel] = [];
        }
        channelGroups[item.channel].push({...item, originalIndex: index});
    });
    
    // 为每个渠道创建独立的折叠面板
    const channelKeys = Object.keys(channelGroups);
    channelKeys.forEach((channel, index) => {
        const items = channelGroups[channel];
        const channelId = channel.toLowerCase().replace(/\s+/g, '-');
        const isFirst = index === 0; // 第一个渠道默认展开
        
        // 计算该渠道的汇总数据
        let totalQuantity = new Decimal(0);
        let totalWeight = new Decimal(0);
        let totalVolume = new Decimal(0);
        let totalPrice = new Decimal(0);
        let totalCost = new Decimal(0);
        let totalProfit = new Decimal(0);
        let totalChargeWeight = new Decimal(0);
        let addressCount = 0;
        
        items.forEach(item => {
            totalQuantity = totalQuantity.plus(new Decimal(item.quantity));
            totalWeight = totalWeight.plus(new Decimal(item.totalWeight));
            totalVolume = totalVolume.plus(new Decimal(item.totalVolume));
            totalPrice = totalPrice.plus(new Decimal(item.totalPrice));
            totalCost = totalCost.plus(new Decimal(item.unitCostRMB).mul(new Decimal(item.chargeWeight)));
            totalProfit = totalProfit.plus(new Decimal(item.unitProfitRMB).mul(new Decimal(item.chargeWeight)));
            totalChargeWeight = totalChargeWeight.plus(new Decimal(item.chargeWeight));
        });
        
        // 计算地址数量（去重）
        const uniqueAddresses = new Set(items.map(item => item.address));
        addressCount = uniqueAddresses.size;
        
        // 计算利率
        const profitRate = totalCost.greaterThan(0) ? totalProfit.div(totalCost).mul(100) : new Decimal(0);
        
        // 创建折叠面板
        const collapseItem = document.createElement('div');
        collapseItem.className = 'accordion-item mb-3';
        collapseItem.innerHTML = `
            <h2 class="accordion-header" id="heading-${channelId}">
                <button class="accordion-button ${isFirst ? '' : 'collapsed'}" type="button" 
                        data-bs-toggle="collapse" data-bs-target="#collapse-${channelId}" 
                        aria-expanded="${isFirst ? 'true' : 'false'}" aria-controls="collapse-${channelId}">
                    <span class="badge ${getChannelBadgeClass(channel)} me-2">${channel}</span>
                    报价详情 (${items.length}个地址)
                </button>
            </h2>
            <div id="collapse-${channelId}" class="accordion-collapse collapse ${isFirst ? 'show' : ''}" 
                 aria-labelledby="heading-${channelId}" data-bs-parent="#batch-quote-tables-container">
                <div class="accordion-body">
                    <!-- 表格 -->
                    <div class="table-responsive mb-4">
                        <table class="table table-bordered table-sm">
                            <thead>
                                <tr>
                                    <th style="width: 8%">地址</th>
                                    <th style="width: 6%">邮编</th>
                                    <th style="width: 4%">箱数</th>
                                    <th style="width: 7%">总实重(KG)</th>
                                    <th style="width: 7%">总体积(cbm)</th>
                                    <th style="width: 7%">计费重(kg)</th>
                                    <th style="width: 5%">泡比</th>
                                    <th style="width: 7%">成本(RMB)</th>
                                    <th style="width: 7%">利润(RMB)</th>
                                    <th style="width: 7%">报价(RMB)</th>
                                    <th style="width: 7%">报价(USD)</th>
                                    <th style="width: 7%">总价(USD)</th>
                                    <th style="width: 6%">时效(天)</th>
                                </tr>
                            </thead>
                            <tbody id="batch-quote-tbody-${channelId}">
                                <!-- 数据将在这里生成 -->
                            </tbody>
                        </table>
                    </div>
                    
                    <!-- 汇总信息 -->
                    <div class="mt-3">
                        <!-- 核心财务指标 -->
                        <div class="row mb-3">
                            <div class="col-md-2-4">
                                <div class="summary-card weight-card">
                                    <div class="card-icon">⚖️</div>
                                    <div class="card-content">
                                        <div class="card-title">总计费重</div>
                                        <div class="card-value">${totalChargeWeight.ceil().toNumber()} KG</div>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-2-4">
                                <div class="summary-card cost-card">
                                    <div class="card-icon">💸</div>
                                    <div class="card-content">
                                        <div class="card-title">总成本 <span class="currency-unit">RMB</span></div>
                                        <div class="card-value">${totalCost.ceil().toNumber()}</div>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-2-4">
                                <div class="summary-card price-card">
                                    <div class="card-icon">💵</div>
                                    <div class="card-content">
                                        <div class="card-title">总报价 <span class="currency-unit">RMB</span></div>
                                        <div class="card-value">${totalCost.plus(totalProfit).ceil().toNumber()}</div>
                                        <div class="card-subvalue">(${totalPrice.toFixed(2)} USD)</div>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-2-4">
                                <div class="summary-card profit-card">
                                    <div class="card-icon">💰</div>
                                    <div class="card-content">
                                        <div class="card-title">总利润 <span class="currency-unit">RMB</span></div>
                                        <div class="card-value">${totalProfit.ceil().toNumber()}</div>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-2-4">
                                <div class="summary-card rate-card">
                                    <div class="card-icon">📊</div>
                                    <div class="card-content">
                                        <div class="card-title">利率</div>
                                        <div class="card-value">${profitRate.toFixed(1)}%</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- 基础数据统计 -->
                        <div class="row">
                            <div class="col-md-2-4">
                                <div class="data-card">
                                    <div class="data-label">总箱数</div>
                                    <div class="data-value">${totalQuantity}</div>
                                </div>
                            </div>
                            <div class="col-md-2-4">
                                <div class="data-card">
                                    <div class="data-label">总实重</div>
                                    <div class="data-value">${Math.ceil(totalWeight)} KG</div>
                                </div>
                            </div>
                            <div class="col-md-2-4">
                                <div class="data-card">
                                    <div class="data-label">总体积</div>
                                    <div class="data-value">${totalVolume.mul(100).ceil().div(100).toFixed(2)} cbm</div>
                                </div>
                            </div>
                            <div class="col-md-2-4">
                                <div class="data-card">
                                    <div class="data-label">地址数</div>
                                    <div class="data-value">${addressCount}</div>
                                </div>
                            </div>
                            <div class="col-md-2-4">
                                <div class="data-card status-card">
                                    <div class="data-label">状态</div>
                                    <div class="data-value text-success">已生成 ${items.length} 个报价</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        container.appendChild(collapseItem);
        
        // 填充表格数据
        const tbody = collapseItem.querySelector(`#batch-quote-tbody-${channelId}`);
                items.forEach(item => {
            const volumeRatio = new Decimal(item.totalVolume).greaterThan(0) ? new Decimal(item.totalWeight).div(new Decimal(item.totalVolume)).round() : new Decimal(0);
            const postcodeColorClass = getPostcodeColorClass(item.postcode, item.channel);
            const addressDisplayContent = getAddressDisplayContent(item.address, item.postcode, item.channel);
            
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${addressDisplayContent}</td>
                <td><span class="${postcodeColorClass}">${item.postcode}</span></td>
                <td>${item.quantity}</td>
                <td>${Math.ceil(item.totalWeight)}</td>
                <td>${new Decimal(item.totalVolume).mul(100).ceil().div(100).toFixed(2)}</td>
                <td>${Math.ceil(item.chargeWeight)}</td>
                <td>${volumeRatio.toNumber()}</td>
                <td>
                    <input type="number" 
                           class="form-control form-control-sm batch-cost-rmb" 
                           value="${item.unitCostRMB.toFixed(2)}" 
                           step="0.01"
                           data-index="${item.originalIndex}"
                           onchange="updateBatchQuoteCost(${item.originalIndex}, this.value)"
                           style="min-width: 70px;" />
                </td>
                <td>
                    <input type="number" 
                           class="form-control form-control-sm batch-profit-rmb" 
                           value="${item.unitProfitRMB.toFixed(2)}" 
                           step="0.01"
                           data-index="${item.originalIndex}"
                           onchange="updateBatchQuoteProfit(${item.originalIndex}, this.value)"
                           style="min-width: 70px;" />
                </td>
                <td>
                    <span class="batch-price-rmb" data-index="${item.originalIndex}">${item.unitPriceRMB.toFixed(2)}</span>
                </td>
                <td>
                    <span class="batch-usd-price" data-index="${item.originalIndex}">${item.unitPrice}</span>
                </td>
                <td>
                    <span class="batch-total-price" data-index="${item.originalIndex}">${item.totalPrice.toFixed(2)}</span>
                </td>
                <td>${item.transitTime}</td>
            `;
            tbody.appendChild(row);
        });
    });
}

/**
 * 更新批量报价成本
 */
function updateBatchQuoteCost(index, newCostRMB) {
    if (index < 0 || index >= batchQuoteData.results.length) return;
    
    const item = batchQuoteData.results[index];
    const costRMB = new Decimal(newCostRMB || 0);
    
    // 更新数据
    item.unitCostRMB = costRMB.toNumber();
    // 重新计算报价（成本 + 利润）
    item.unitPriceRMB = costRMB.plus(new Decimal(item.unitProfitRMB)).toNumber();
    item.unitPrice = new Decimal(item.unitPriceRMB).div(new Decimal(exchange_rate)).toFixed(2);
    item.totalPrice = new Decimal(item.unitPrice).mul(new Decimal(item.chargeWeight)).toFixed(2);
    
    // 更新页面显示
    updateBatchQuoteDisplay(index);
    
    // 更新折叠框内的汇总信息
    updateCollapseSummaryInfo();
}

/**
 * 更新批量报价利润
 */
function updateBatchQuoteProfit(index, newProfitRMB) {
    if (index < 0 || index >= batchQuoteData.results.length) return;
    
    const item = batchQuoteData.results[index];
    const profitRMB = new Decimal(newProfitRMB || 0);
    
    // 更新数据
    item.unitProfitRMB = profitRMB.toNumber();
    // 重新计算报价（成本 + 利润）
    item.unitPriceRMB = new Decimal(item.unitCostRMB).plus(profitRMB).toNumber();
    item.unitPrice = new Decimal(item.unitPriceRMB).div(new Decimal(exchange_rate)).toFixed(2);
    console.log("item.unitPrice", item.unitPrice);
    item.totalPrice = new Decimal(item.unitPrice).mul(new Decimal(item.chargeWeight)).toFixed(2);
    
    // 更新页面显示
    updateBatchQuoteDisplay(index);
    
    // 更新折叠框内的汇总信息
    updateCollapseSummaryInfo();
}

/**
 * 更新批量报价价格
 */
function updateBatchQuotePrice(index, newPriceRMB) {
    if (index < 0 || index >= batchQuoteData.results.length) return;
    
    const item = batchQuoteData.results[index];
    const priceRMB = new Decimal(newPriceRMB || 0);
    
    // 更新数据
    item.unitPriceRMB = priceRMB.toNumber();
    item.unitProfitRMB = priceRMB.minus(new Decimal(item.unitCostRMB)).toNumber();
    item.unitPrice = priceRMB.div(new Decimal(exchange_rate)).toFixed(2);
    item.totalPrice = new Decimal(item.unitPrice).mul(new Decimal(item.chargeWeight)).toFixed(2);
    
    // 更新页面显示
    updateBatchQuoteDisplay(index);
    
    // 更新汇总信息
    updateCollapseSummaryInfo();
}

/**
 * 更新批量报价显示
 */
function updateBatchQuoteDisplay(index) {
    const item = batchQuoteData.results[index];
    
    // 更新报价RMB显示
    const priceRmbElement = document.querySelector(`.batch-price-rmb[data-index="${index}"]`);
    if (priceRmbElement) {
        priceRmbElement.textContent = item.unitPriceRMB.toFixed(2);
    }
    
    // 更新USD价格显示
    const usdPriceElement = document.querySelector(`.batch-usd-price[data-index="${index}"]`);
    if (usdPriceElement) {
        usdPriceElement.textContent = item.unitPrice;
    }
    
    // 更新总价显示
    const totalPriceElement = document.querySelector(`.batch-total-price[data-index="${index}"]`);
    if (totalPriceElement) {
        totalPriceElement.textContent = item.totalPrice;
    }
}

/**
 * 更新折叠框内的汇总信息
 */
function updateCollapseSummaryInfo() {
    if (!batchQuoteData.results || batchQuoteData.results.length === 0) {
        return;
    }
    
    // 按渠道分组
    const channelGroups = {};
    batchQuoteData.results.forEach(item => {
        if (!channelGroups[item.channel]) {
            channelGroups[item.channel] = [];
        }
        channelGroups[item.channel].push(item);
    });
    
    // 为每个渠道更新汇总信息
    Object.keys(channelGroups).forEach(channel => {
        const items = channelGroups[channel];
        const channelId = channel.toLowerCase().replace(/\s+/g, '-');
        
        // 计算该渠道的汇总数据
        let totalQuantity = new Decimal(0);
        let totalWeight = new Decimal(0);
        let totalVolume = new Decimal(0);
        let totalPrice = new Decimal(0);
        let totalCost = new Decimal(0);
        let totalProfit = new Decimal(0);
        let totalChargeWeight = new Decimal(0);
        let addressCount = 0;
        
        items.forEach(item => {
            totalQuantity = totalQuantity.plus(new Decimal(item.quantity));
            totalWeight = totalWeight.plus(new Decimal(item.totalWeight));
            totalVolume = totalVolume.plus(new Decimal(item.totalVolume));
            totalPrice = totalPrice.plus(new Decimal(item.totalPrice));
            totalCost = totalCost.plus(new Decimal(item.unitCostRMB).mul(new Decimal(item.chargeWeight)));
            totalProfit = totalProfit.plus(new Decimal(item.unitProfitRMB).mul(new Decimal(item.chargeWeight)));
            totalChargeWeight = totalChargeWeight.plus(new Decimal(item.chargeWeight));
        });
        
        // 计算地址数量（去重）
        const uniqueAddresses = new Set(items.map(item => item.address));
        addressCount = uniqueAddresses.size;
        
        // 计算利率
        const profitRate = totalCost.greaterThan(0) ? totalProfit.div(totalCost).mul(100) : new Decimal(0);
        
        // 更新折叠框内的汇总信息
        const collapseElement = document.getElementById(`collapse-${channelId}`);
        if (collapseElement) {
            const summarySection = collapseElement.querySelector('.mt-3');
            if (summarySection) {
                summarySection.innerHTML = `
                    <!-- 核心财务指标 -->
                    <div class="row mb-3">
                        <div class="col-md-2-4">
                            <div class="summary-card weight-card">
                                <div class="card-icon">⚖️</div>
                                <div class="card-content">
                                    <div class="card-title">总计费重</div>
                                    <div class="card-value">${totalChargeWeight.ceil().toNumber()} KG</div>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-2-4">
                            <div class="summary-card cost-card">
                                <div class="card-icon">💸</div>
                                <div class="card-content">
                                    <div class="card-title">总成本 <span class="currency-unit">RMB</span></div>
                                    <div class="card-value">${totalCost.ceil().toNumber()}</div>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-2-4">
                            <div class="summary-card price-card">
                                <div class="card-icon">💵</div>
                                <div class="card-content">
                                    <div class="card-title">总报价 <span class="currency-unit">RMB</span></div>
                                    <div class="card-value">${totalCost.plus(totalProfit).ceil().toNumber()}</div>
                                    <div class="card-subvalue">(${totalPrice.toFixed(2)} USD)</div>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-2-4">
                            <div class="summary-card profit-card">
                                <div class="card-icon">💰</div>
                                <div class="card-content">
                                    <div class="card-title">总利润 <span class="currency-unit">RMB</span></div>
                                    <div class="card-value">${totalProfit.ceil().toNumber()}</div>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-2-4">
                            <div class="summary-card rate-card">
                                <div class="card-icon">📊</div>
                                <div class="card-content">
                                    <div class="card-title">利率</div>
                                    <div class="card-value">${profitRate.toFixed(1)}%</div>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- 基础数据统计 -->
                    <div class="row">
                        <div class="col-md-2-4">
                            <div class="data-card">
                                <div class="data-label">总箱数</div>
                                <div class="data-value">${totalQuantity}</div>
                            </div>
                        </div>
                        <div class="col-md-2-4">
                            <div class="data-card">
                                <div class="data-label">总实重</div>
                                <div class="data-value">${Math.ceil(totalWeight)} KG</div>
                            </div>
                        </div>
                        <div class="col-md-2-4">
                            <div class="data-card">
                                <div class="data-label">总体积</div>
                                <div class="data-value">${totalVolume.mul(100).ceil().div(100).toFixed(2)} cbm</div>
                            </div>
                        </div>
                        <div class="col-md-2-4">
                            <div class="data-card">
                                <div class="data-label">地址数</div>
                                <div class="data-value">${addressCount}</div>
                            </div>
                        </div>
                        <div class="col-md-2-4">
                            <div class="data-card status-card">
                                <div class="data-label">状态</div>
                                <div class="data-value text-success">已生成 ${items.length} 个报价</div>
                            </div>
                        </div>
                    </div>
                `;
            }
        }
    });
}



/**
 * 导出批量报价
 */
function exportBatchQuote() {
    if (batchQuoteData.results.length === 0) {
        showToast('请先生成批量报价');
        return;
    }

    // 获取导出格式
    const exportFormat = document.getElementById('batch-export-format').value;
    
    let exportText = '';
    
    if (exportFormat === 'by-address') {
        exportText = exportByAddress();
    } else if (exportFormat === 'by-channel') {
        exportText = exportByChannel();
    } else if (exportFormat === 'excel') {
        exportExcel();
        return; // Excel导出不需要复制到剪贴板
    }
    
    // 复制到剪贴板
    navigator.clipboard.writeText(exportText).then(() => {
        showToast('批量报价单已复制到剪贴板');
    }).catch(() => {
        alert(exportText);
    });
}

/**
 * 按地址导出格式
 */
function exportByAddress() {
    let exportText = '';
    
    // 按地址分组
    const addressGroups = {};
    batchQuoteData.results.forEach(item => {
        if (!addressGroups[item.address]) {
            addressGroups[item.address] = [];
        }
        addressGroups[item.address].push(item);
    });

    // 为每个地址生成报价
    Object.keys(addressGroups).forEach(address => {
        const items = addressGroups[address];
        const firstItem = items[0];
        
        exportText += `To ${address},${firstItem.quantity}ctns ${Math.ceil(firstItem.totalWeight)}kg ${firstItem.totalVolume.toFixed(2)}cbm\n`;
        
        // 为每个渠道生成报价行
        items.forEach(item => {
            const unitPrice = new Decimal(item.unitPrice);
            const totalCost = unitPrice.mul(new Decimal(item.chargeWeight));

            exportText += `${item.channel}: ${unitPrice.toFixed(2)} usd/kg * ${Math.ceil(item.chargeWeight)}kg = ${totalCost.toFixed(2)}usd ${item.transitTime} days\n`;
        });

        exportText += '\n';
    });

    // 添加汇总信息
    exportText += getExportSummary();
    
    return exportText;
}

/**
 * 按渠道导出格式
 */
function exportByChannel() {
    let exportText = '';
    
    // 按渠道分组
    const channelGroups = {};
    batchQuoteData.results.forEach(item => {
        if (!channelGroups[item.channel]) {
            channelGroups[item.channel] = [];
        }
        channelGroups[item.channel].push(item);
    });

    // 为每个渠道生成报价
    Object.keys(channelGroups).forEach(channel => {
        const items = channelGroups[channel];
        
        // 为每个地址生成报价行
        items.forEach(item => {
            const unitPrice = new Decimal(item.unitPrice);
            const totalCost = unitPrice.mul(new Decimal(item.chargeWeight));

            exportText += `To ${item.address},${item.quantity}ctns ${Math.ceil(item.totalWeight)}kg ${item.totalVolume.toFixed(2)}cbm\n`;
            exportText += `${item.channel}: ${unitPrice.toFixed(2)} usd/kg * ${Math.ceil(item.chargeWeight)}kg = ${totalCost.toFixed(2)}usd ${item.transitTime} days\n\n`;
        });
    });

    // 添加汇总信息
    exportText += getExportSummary();
    
    return exportText;
}

/**
 * 导出Excel格式
 */
function exportExcel() {
    if (!batchQuoteData.boxSpec) {
        showToast('请先生成批量报价');
        return;
    }
    
    // 创建工作簿
    const wb = XLSX.utils.book_new();
    
    // 准备数据
    const data = [];
    
    // 添加表头
    data.push([
        'AD',           // 地址
        'CTNS',         // 箱数
        'Size',         // 箱规尺寸
        'Weight',       // 单箱实重
        'Volume',       // 总体积
        'Volume weight', // 总材积重
        'Actual weight', // 总实重
        'Chargeable weight', // 总计费重
        'unit price',   // 报价(USD)
        'total cost',   // 总价(USD)
        'transit time', // 时效
        '泡比',         // 泡比
        'Remark'        // 详细备注信息
    ]);
    
    // 按渠道分组数据
    const channelGroups = {};
    batchQuoteData.results.forEach(item => {
        if (!channelGroups[item.channel]) {
            channelGroups[item.channel] = [];
        }
        channelGroups[item.channel].push(item);
    });
    
    // 生成数据行
    Object.keys(channelGroups).forEach(channel => {
        const items = channelGroups[channel];
        
        items.forEach(item => {
            const boxSpec = batchQuoteData.boxSpec;
            const size = `${boxSpec.length}*${boxSpec.width}*${boxSpec.height}`;
            const singleWeight = boxSpec.weight; // 单箱实重
            const totalVolume = new Decimal(item.totalVolume).mul(100).ceil().div(100); // 总体积
            const volumeWeight = new Decimal(item.totalVolume).mul(new Decimal(1000000)).div(new Decimal(6000)).ceil(); // 总材积重
            const actualWeight = new Decimal(item.totalWeight).ceil(); // 总实重
            const chargeableWeight = new Decimal(item.chargeWeight).ceil(); // 总计费重
            const unitPrice = new Decimal(item.unitPrice).toFixed(2); // 报价(USD)
            const totalCost = new Decimal(item.unitPrice).mul(new Decimal(item.chargeWeight)).toFixed(2); // 总价(USD)
            const transitTime = item.transitTime + ' days'; // 时效
            const volumeRatio = new Decimal(item.totalVolume).greaterThan(0) ? 
                new Decimal(item.totalWeight).div(new Decimal(item.totalVolume)).round().toNumber() : 0; // 泡比
            
            // 生成备注信息
            const remark = `To ${item.address},${item.quantity}ctns ${Math.ceil(item.totalWeight)}kg ${totalVolume.toFixed(2)}cbm\n${item.channel}: ${unitPrice} usd/kg * ${Math.ceil(item.chargeWeight)}kg = ${totalCost}usd ${transitTime}`;
            
            // 添加数据行
            data.push([
                item.address,           // AD - 地址
                item.quantity,          // CTNS - 箱数
                size,                   // Size - 箱规尺寸
                singleWeight,           // Weight - 单箱实重
                parseFloat(totalVolume.toFixed(2)), // Volume - 总体积
                volumeWeight.toNumber(), // Volume weight - 总材积重
                actualWeight.toNumber(), // Actual weight - 总实重
                chargeableWeight.toNumber(), // Chargeable weight - 总计费重
                parseFloat(unitPrice),  // unit price - 报价(USD)
                parseFloat(totalCost),  // total cost - 总价(USD)
                transitTime,            // transit time - 时效
                volumeRatio,            // 泡比
                remark                  // Remark - 详细信息
            ]);
        });
    });
    
    // 添加汇总行
    const boxSpec = batchQuoteData.boxSpec;
    const totalQuantity = boxSpec.totalQuantity;
    const totalVolume = new Decimal(boxSpec.volume).mul(new Decimal(totalQuantity));
    const totalWeight = new Decimal(boxSpec.weight).mul(new Decimal(totalQuantity));
    
    // 计算基础总成本（不含提货费）
    let baseTotalCost = new Decimal(0);
    batchQuoteData.results.forEach(item => {
        const itemCost = new Decimal(item.unitPrice).mul(new Decimal(item.chargeWeight));
        baseTotalCost = baseTotalCost.plus(itemCost);
    });
    
    // 获取提货费
    let pickupFee = new Decimal(document.getElementById('batch-pickup-fee').value || 0);
    pickupFee = pickupFee.div(new Decimal(exchange_rate)).ceil();
    
    // 计算最终总价（基础总成本 + 提货费）
    const totalCost = baseTotalCost.plus(pickupFee);
    
    // 如果有提货费，先添加提货费行
    if (pickupFee.greaterThan(0)) {
        data.push([
            '',                             // AD
            '',                             // CTNS
            '',                             // Size
            '',                             // Weight
            '',                             // Volume
            '',                             // Volume weight
            '',                             // Actual weight
            '',                             // Chargeable weight
            'Pickup fee',                             // unit price
            parseFloat(pickupFee.toFixed(2)), // Pickup fee - 提货费
            '',                             // transit time
            '',                             // 泡比
            ''                    // Remark
        ]);
    }
    
    // 添加总价行
    data.push([
        '',                             // AD
        totalQuantity,                  // CTNS - 总箱数
        'boxes',                        // Size
        '',                             // Weight
        parseFloat(totalVolume.mul(100).ceil().div(100).toFixed(2)), // Volume - 总体积
        'cbm',                          // Volume weight
        '',                             // Actual weight - 总实重
        '',                             // Chargeable weight
        'Total',                        // unit price
        parseFloat(totalCost.toFixed(2)), // total cost - 总价
        '',                             // transit time
        '',                             // 泡比
        ''                              // Remark
    ]);
    
    // 创建工作表
    const ws = XLSX.utils.aoa_to_sheet(data);
    
    // 设置列宽
    ws['!cols'] = [
        { wch: 10 }, // AD
        { wch: 8 },  // CTNS
        { wch: 12 }, // Size
        { wch: 10 }, // Weight
        { wch: 10 }, // Volume
        { wch: 12 }, // Volume weight
        { wch: 12 }, // Actual weight
        { wch: 15 }, // Chargeable weight
        { wch: 10 }, // unit price
        { wch: 10 }, // total cost
        { wch: 12 }, // transit time
        { wch: 8 },  // 泡比
        { wch: 50 }  // Remark
    ];
    
    // 添加工作表到工作簿
    XLSX.utils.book_append_sheet(wb, ws, 'Sheet1');
    
    // 生成文件名：XXctns_quote_月日
    const now = new Date();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    const fileName = `${totalQuantity}ctns_quote_${month}${day}.xlsx`;
    
    // 生成并下载Excel文件
    XLSX.writeFile(wb, fileName);
    
    showToast('Excel文件已下载');
}

/**
 * 下载CSV文件
 */
function downloadCSV(csvContent, filename) {
    const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    
    if (link.download !== undefined) {
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', filename);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        showToast('Excel文件已下载');
    } else {
        showToast('浏览器不支持文件下载');
    }
}

/**
 * 获取导出汇总信息
 */
function getExportSummary() {
    // 直接使用箱规信息计算汇总
    if (!batchQuoteData.boxSpec) {
        return '---\nTotal are 0ctns 0kg 0.00cbm\nPickup fee: 0 usd\n';
    }
    
    const boxSpec = batchQuoteData.boxSpec;
    const totalQuantity = new Decimal(boxSpec.totalQuantity);
    const totalWeight = new Decimal(boxSpec.weight).mul(totalQuantity);
    const totalVolume = new Decimal(boxSpec.volume).mul(totalQuantity);

    let pickupFee = new Decimal(document.getElementById('batch-pickup-fee').value || 0);
    pickupFee = pickupFee.div(new Decimal(exchange_rate)).ceil();

    let summaryText = '---\n';
    summaryText += `Total are ${totalQuantity.toNumber()}ctns ${totalWeight.ceil().toNumber()}kg ${totalVolume.mul(100).ceil().div(100).toFixed(2)}cbm\n`;
    summaryText += `Pickup fee: ${pickupFee.toNumber()} usd\n`;
    
    return summaryText;
}

/**
 * 清空批量报价
 */
function clearBatchQuote() {
    document.getElementById('batch-box-spec').value = '';
    document.getElementById('batch-address-distribution').value = '';
    document.getElementById('batch-quote-tbody').innerHTML = '';
    
    batchQuoteData = {
        boxSpec: null,
        addressDistribution: [],
        results: []
    };
    
    // 清空汇总信息
    document.getElementById('batch-total-quantity').textContent = '0';
    document.getElementById('batch-total-weight').textContent = '0';
    document.getElementById('batch-total-charge-weight').textContent = '0';
    document.getElementById('batch-total-volume').textContent = '0';
    document.getElementById('batch-total-cost').textContent = '0';
    document.getElementById('batch-total-profit').textContent = '0';
    document.getElementById('batch-profit-rate').textContent = '0';
    document.getElementById('batch-total-price-rmb').textContent = '0';
    document.getElementById('batch-total-price-usd').textContent = '0';
    document.getElementById('batch-address-count').textContent = '0';
    document.getElementById('batch-address-count-2').textContent = '0';
    
    // 隐藏表格，显示空状态
    document.getElementById('batch-quote-tables-container').style.display = 'none';
    document.getElementById('batch-quote-empty-state').style.display = 'block';
    
    showToast('批量报价已清空');
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 添加渠道选择事件监听器
    addChannelSelectionListeners();
});

/**
 * 快速添加常用地址组合
 */
function addCommonAddressCombination() {
    // 示例：45*45*50 10KG 50CTNS
    document.getElementById('batch-box-spec').value = '45*45*50 10KG 50CTNS';
    parseBatchBoxSpec();
    
    // 示例：RDU4 4CTNS | AVP1 25CTNS | LAS1 20CTNS | GYR3 1CTNS
    document.getElementById('batch-address-distribution').value = 'RDU4 4CTNS | AVP1 25CTNS | LAS1 20CTNS | GYR3 1CTNS';
    parseBatchAddressDistribution();
    
    // 示例利润
    document.getElementById('batch-profit').value = '0.5';
    
    showToast('已添加示例数据，请修改后点击"生成报价"');
}

// 显示派送方式提示信息
function showDeliveryMethodHint(deliveryMethod) {
    const hintElement = document.getElementById('delivery-method-hint');
    const hintTextElement = document.getElementById('delivery-hint-text');
    
    if (!hintElement || !hintTextElement) return;
    
    // 根据派送方式显示不同的提示信息
    switch(deliveryMethod) {
        case '海派':
            hintTextElement.textContent = '单箱最低计费重为12kg';
            hintElement.style.display = 'block';
            break;
        case '空派':
            hintTextElement.textContent = '单箱最低计费重为10kg';
            hintElement.style.display = 'block';
            break;
        default:
            hintElement.style.display = 'none';
            break;
    }
}

/**
 * 获取承运商货重比减tooltip内容
 * @param {Decimal} volumeRatio - 泡比值
 * @param {Decimal} billingWeight - 计费重
 * @returns {string} - tooltip内容
 */
function getCarrierDiscountTooltip(volumeRatio, billingWeight = null) {
    // 获取当前选择的承运商
    const currentCarrier = getCurrentCarrier();
    const carrierConfig = carrierWeightRatioDiscounts[currentCarrier] || carrierWeightRatioDiscounts[defaultCarrier];
    
    // 检查是否满足最低计费重要求
    if (billingWeight && carrierConfig.minBillingWeight) {
        if (billingWeight.lessThan(carrierConfig.minBillingWeight)) {
            return `${carrierConfig.name}货重比减：\n需要${carrierConfig.minBillingWeight}KG及以上才有货重比减\n当前计费重：${billingWeight}KG`;
        }
    }
    
    // 构建tooltip内容 - 只显示当前泡比能满足的折扣
    let tooltipContent = `${carrierConfig.name}货重比减：\n`;
    
    // 找到当前泡比能满足的所有折扣
    const applicableDiscounts = carrierConfig.discounts.filter(item => 
        volumeRatio.greaterThanOrEqualTo(item.ratio)
    );
    
    if (applicableDiscounts.length > 0) {
        applicableDiscounts.forEach(item => {
            tooltipContent += `1:${item.ratio}减${item.discount}\n`;
        });
    } else {
        tooltipContent += `当前泡比${volumeRatio}不满足任何折扣条件`;
    }
    
    // 移除最后的换行符
    tooltipContent = tooltipContent.trim();
    
    return tooltipContent;
}

/**
 * 获取当前选择的承运商
 * @returns {string} - 承运商名称
 */
function getCurrentCarrier() {
    const carrierSelect = document.getElementById('carrier-select');
    if (carrierSelect && carrierSelect.value) {
        return carrierSelect.value;
    }
    return defaultCarrier;
}

/**
 * 根据泡比获取适用的折扣
 * @param {Decimal} volumeRatio - 泡比值
 * @param {string} carrier - 承运商名称
 * @param {Decimal} billingWeight - 计费重
 * @returns {number} - 折扣值
 */
function getApplicableDiscount(volumeRatio, carrier = null, billingWeight = null) {
    const carrierName = carrier || getCurrentCarrier();
    const carrierConfig = carrierWeightRatioDiscounts[carrierName] || carrierWeightRatioDiscounts[defaultCarrier];
    
    // 检查是否满足最低计费重要求
    if (billingWeight && carrierConfig.minBillingWeight) {
        if (billingWeight.lessThan(carrierConfig.minBillingWeight)) {
            return 0; // 不满足最低计费重要求，无折扣
        }
    }
    
    // 找到适用的最大折扣
    let applicableDiscount = 0;
    for (const item of carrierConfig.discounts) {
        if (volumeRatio.greaterThanOrEqualTo(item.ratio)) {
            applicableDiscount = item.discount;
        } else {
            break;
        }
    }
    
    return applicableDiscount;
}

/**
 * 更新承运商tooltip
 * 当用户切换承运商时调用
 */
function updateCarrierTooltip() {
    // 重新计算泡比tooltip
    const volumeRatioInput = document.getElementById('volumeRatio');
    const volumeRatio = new Decimal(volumeRatioInput.value || 0);
    
    if (volumeRatio.greaterThanOrEqualTo(200)) {
        // 更新tooltip内容
        const billingWeight = new Decimal(document.getElementById('chargeWeight').value || 0);
        const tooltipContent = getCarrierDiscountTooltip(volumeRatio, billingWeight);
        volumeRatioInput.setAttribute('data-bs-title', tooltipContent);
        volumeRatioInput.setAttribute('title', tooltipContent);
        
        // 重新初始化tooltip
        const existingTooltip = bootstrap.Tooltip.getInstance(volumeRatioInput);
        if (existingTooltip) {
            existingTooltip.dispose();
        }
        new bootstrap.Tooltip(volumeRatioInput, {
            html: true,
            placement: 'top'
        });
    }
}

/**
 * 初始化承运商选择器
 * 页面加载时调用
 */
function initCarrierSelector() {
    const carrierSelect = document.getElementById('carrier-select');
    if (carrierSelect) {
        // 设置默认承运商
        carrierSelect.value = defaultCarrier;
        
        // 动态生成选项（从配置中读取）
        carrierSelect.innerHTML = '';
        Object.keys(carrierWeightRatioDiscounts).forEach(carrierName => {
            const option = document.createElement('option');
            option.value = carrierName;
            option.textContent = carrierWeightRatioDiscounts[carrierName].name;
            carrierSelect.appendChild(option);
        });
        
        // 设置默认选中项
        carrierSelect.value = defaultCarrier;
    }
}

/**
 * 初始化分泡比例控制
 */
function initVolumeRatioControl() {
    // 监听派送方式变化
    const deliveryMethodSelect = document.getElementById("delivery-method-select");
    if (deliveryMethodSelect) {
        deliveryMethodSelect.addEventListener("change", toggleVolumeRatioVisibility);
    }
    
    // 初始检查
    toggleVolumeRatioVisibility();
}

/**
 * 切换分泡比例选项的显示/隐藏
 */
function toggleVolumeRatioVisibility() {
    const deliveryMethodSelect = document.getElementById("delivery-method-select");
    const volumeRatioContainer = document.getElementById("volume-ratio-container");
    
    if (!deliveryMethodSelect || !volumeRatioContainer) return;
    
    const selectedMethod = deliveryMethodSelect.value;
    
    // 检查是否为快递派渠道
    const isExpressDelivery = shippingChannels["快递派"].includes(selectedMethod);
    
    // 获取当前泡比
    const volumeRatioElement = document.getElementById("volumeRatio");
    const currentVolumeRatio = volumeRatioElement ? parseFloat(volumeRatioElement.value) || 0 : 0;
    
    // 判断是否显示分泡选项：快递派渠道 且 泡比小于167
    const shouldShowVolumeRatio = isExpressDelivery && currentVolumeRatio < 167;
    
    if (shouldShowVolumeRatio) {
        volumeRatioContainer.style.display = "block";
    } else {
        volumeRatioContainer.style.display = "none";
        // 重置选择
        const volumeRatioSelect = document.getElementById("volume-ratio-select");
        if (volumeRatioSelect) {
            volumeRatioSelect.value = ""; // 重置为默认值（不分泡）
        }
    }
}

/**
 * 导出客户地址簿为Excel文件
 */
function exportAddressBook() {
    try {
        // 获取地址数据
        const addressData = getAddressBookData();
        
        console.log('地址数据:', addressData);
        console.log('数据长度:', addressData.length);
        
        if (!addressData || addressData.length === 0) {
            showToast('没有地址数据可导出。请确保customerAddresses变量中有数据。', 'warning');
            return;
        }
        
        // 创建工作簿
        const wb = XLSX.utils.book_new();
        
        // 准备数据
        const wsData = [
            ['客户', '邮编', '详细地址', '公司名', '联系人', '电话', '商业/住宅', '偏远地址']
        ];
        
        addressData.forEach(address => {
            wsData.push([
                address.customer || '',
                address.postcode || '',
                address.address || '',
                address.company || '',
                address.contact || '',
                address.phone || '',
                address.type === 'commercial' ? 'commercial' : 'personal',
                address.region === 'remote' ? 'remote' : 'non-remote'
            ]);
        });
        
        // 创建工作表
        const ws = XLSX.utils.aoa_to_sheet(wsData);
        
        // 设置列宽
        ws['!cols'] = [
            { wch: 10 }, // 客户
            { wch: 8 },  // 邮编
            { wch: 30 }, // 详细地址
            { wch: 20 }, // 公司名
            { wch: 15 }, // 联系人
            { wch: 15 }, // 电话
            { wch: 8 },  // 类型
            { wch: 8 }   // 区域
        ];
        
        // 添加工作表到工作簿
        XLSX.utils.book_append_sheet(wb, ws, '客户地址簿');
        
        // 生成文件名
        const now = new Date();
        const timestamp = now.getFullYear() + 
                         String(now.getMonth() + 1).padStart(2, '0') + 
                         String(now.getDate()).padStart(2, '0') + '_' +
                         String(now.getHours()).padStart(2, '0') + 
                         String(now.getMinutes()).padStart(2, '0');
        const fileName = `客户地址簿_${timestamp}.xlsx`;
        
        // 导出文件
        XLSX.writeFile(wb, fileName);
        
        showToast('地址簿导出成功', 'success');
        
    } catch (error) {
        console.error('导出地址簿失败:', error);
        showToast('导出失败，请重试', 'error');
    }
}


/**
 * 获取地址簿数据
 */
function getAddressBookData() {
    try {
        // 只从全局变量customerAddresses获取数据
        if (typeof customerAddresses !== 'undefined' && customerAddresses && customerAddresses.length > 0) {
            // 转换数据格式以匹配导出需求
            return customerAddresses.map(addr => ({
                customer: addr.customer || '',
                postcode: addr.postalCode || '',
                address: addr.address || '',
                company: addr.company || '',
                contact: addr.contact || '',
                phone: addr.phone || '',
                type: addr.isCommercial ? 'commercial' : 'personal',
                region: addr.isRemote ? 'remote' : 'non-remote'
            }));
        }
        
        return [];
    } catch (error) {
        console.error('获取地址簿数据失败:', error);
        return [];
    }
}


/**
 * 显示提示消息（支持多种类型）
 * @param {string} message - 提示消息
 * @param {string} type - 类型: 'success', 'error', 'warning', 'info'，默认为 'success'
 */
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