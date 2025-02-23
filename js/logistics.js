// 新增常量 exchange_rate
const exchange_rate = 7.25; //美元汇率
let valid_date = ''; //报价有效日期
const LINE_BREAK = '\n';

// 引入 data.js 中的数组
const {deliveryMethodsByCountry, quickReplies, addressToPostcode, remotePostcodes} = window.data;

// 页面加载时初始化
window.onload = function () {
    // 初始化派送方式
    updateDeliveryMethods();
    // 加载快捷回复选项
    loadQuickReplies();
    // 获取下一个星期五的日期
    valid_date = getNextFriday();
    // 渲染价格表格
    renderPriceTable();
    // 监听渠道下拉选项的变化
    document.getElementById("t4_channel").addEventListener("change", renderPriceTable());
    // 初始化时渲染标签按钮
    renderTagButtons();
};


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

    rows.forEach((row, index) => {
        let length = new Decimal(row.querySelector('.length').value || 0);
        let width = new Decimal(row.querySelector('.width').value || 0);
        let height = new Decimal(row.querySelector('.height').value || 0);
        let weight = new Decimal(row.querySelector('.weight').value || 0);
        let quantity = new Decimal(row.querySelector('.quantity').value || 0);

        // 计算体积 (cbm)
        let volume = length.mul(width).mul(height).mul(quantity).dividedBy(1000000);
        volume = Math.ceil(volume * 100) / 100; // 保留两位小数并向上取整

        // 计算单箱材积 (kg)
        let singleDimensionWeight = length.mul(width).mul(height).dividedBy(6000);
        singleDimensionWeight = Math.ceil(singleDimensionWeight); // 向上取整

        // 计算实重 (kg)
        let rowWeight = weight.mul(quantity);
        rowWeight = Math.ceil(rowWeight * 100) / 100; // 保留两位小数并向上取整

        // 计算材积重 (kg)
        let dimensionWeight = length.mul(width).mul(height).mul(quantity).dividedBy(6000);
        dimensionWeight = Math.ceil(dimensionWeight); // 向上取整

        // 检查派送方式为“快递派”时，调整实重和材积重
        if (deliveryMethod == "快递派") {
            let minWeight = new Decimal(12).mul(quantity); // 最低实重和材积重要求
            if (rowWeight.lessThan(minWeight)) {
                rowWeight = minWeight; // 更新实重
            }
            if (dimensionWeight.lessThan(minWeight)) {
                dimensionWeight = minWeight; // 更新材积重
            }
        }

        // 计算周长 (cm)
        let sides = [length, width, height];
        sides.sort((a, b) => a - b); // 排序：从小到大
        let perimeter = new Decimal(sides[0]).add(new Decimal(sides[1])).mul(2).add(new Decimal(sides[2]));

        // 更新单行数据
        row.querySelector('.result-cell:nth-child(6)').innerText = `${volume} cbm`;
        row.querySelector('.result-cell:nth-child(7)').innerText = `${singleDimensionWeight} kg`; // 新增列
        row.querySelector('.result-cell:nth-child(8)').innerText = `${rowWeight} kg`;
        row.querySelector('.result-cell:nth-child(9)').innerText = `${dimensionWeight} kg`;
        row.querySelector('.result-cell:nth-child(10)').innerText = `${perimeter} cm`;
        
        // 高亮显示周长
        let perimeterCell = row.querySelector('.result-cell:nth-child(10)');
        if (perimeter.greaterThanOrEqualTo(260)) {
            perimeterCell.classList.add('highlight-red');
        } else {
            perimeterCell.classList.remove('highlight-red');
        }

        // 累加总计
        totalQuantity = totalQuantity.add(quantity);
        totalVolume = totalVolume.add(volume);
        totalWeight = totalWeight.add(rowWeight);
        totalDimensionWeight = totalDimensionWeight.add(dimensionWeight);

        // 检查规则
        if (rules) {
            let isOver = 0;
            let waringstr = `第 ${index + 1} 行：${quantity} 箱，`;
            if (weight.greaterThan(rules.maxWeight)) {
                waringstr += `单件实重 ${weight} kg (> ${rules.maxWeight} kg),`;
                isOver = 1;
            }
            if (sides[2].greaterThan(rules.maxLength)) {
                waringstr += `最长边 ${sides[2]} cm (> ${rules.maxLength} cm), `;
                isOver = 1;
            }
            if (sides[1].greaterThan(rules.maxSecondLength)) {
                waringstr += `第二长边 ${sides[1]} cm (> ${rules.maxSecondLength} cm), `;
                isOver = 1;
            }
            if (perimeter.greaterThan(rules.maxPerimeter)) {
                waringstr += `围长 ${perimeter} cm (> ${rules.maxPerimeter} cm),`;
                isOver = 1;
            }
            if (rules.maxDimensionWeight && singleDimensionWeight.greaterThan(rules.maxDimensionWeight)) {
                waringstr += `单箱材积 ${singleDimensionWeight} kg (> ${rules.maxDimensionWeight} kg),`;
                isOver = 1;
            }

            if (isOver == 1) {
                warnings.push(waringstr);
            }
        }
        
    });

    // 更新总计数据
    document.getElementById('total-quantity').innerText = totalQuantity;
    document.getElementById('total-volume').innerText = Math.ceil(totalVolume * 100) / 100; // 向上取整保留两位小数
    document.getElementById('total-weight').innerText = Math.ceil(totalWeight); // 向上取整
    document.getElementById('total-dimension-weight').innerText = Math.ceil(totalDimensionWeight); // 向上取整

    // 计算计费重
    let billingWeight = Math.ceil(Decimal.max(totalWeight, totalDimensionWeight.ceil()));
    document.getElementById('billing-weight').innerText = billingWeight;

    // 计算泡比
    if (!totalWeight.equals(0) && !totalVolume.equals(0)) {
        let volumeRatio = totalWeight.dividedBy(totalVolume);
        document.getElementById('volume-ratio').innerText = volumeRatio.toFixed(0);
    }

    // 更新警告信息
    const warningsTextarea = document.getElementById('box-warnings');
    if (warnings.length > 0) {
        warningsTextarea.value = warnings.join('\n'); // 将警告信息拼接为字符串
        warningsTextarea.classList.remove('no-warnings'); // 移除绿色背景类
    } else {
        warningsTextarea.value = '无警告信息'; // 如果没有警告，显示“无警告信息”
        warningsTextarea.classList.add('no-warnings'); // 添加绿色背景类
    }
}

// 显示报价
function updateQuote() {
    // 获取用户输入
    let country = document.getElementById("country-select").value;
    let origin = document.getElementById("origin-select").value;
    let totalQuantity = new Decimal(document.getElementById('quantity').value || 0); // 箱数
    let totalWeight = new Decimal(document.getElementById('weight').value || 0); // 实重
    let totalVolume = new Decimal(document.getElementById('volume').value || 0); // 体积
    let dimensionWeight = new Decimal(document.getElementById('dimensionWeight').value || 0);
    let channel = document.getElementById("delivery-method-select").value;
    let address = document.getElementById("address").value.toUpperCase();
    let postcode = document.getElementById("postcode").value;
    let costRmb = new Decimal(document.getElementById("cost_rmb").value || 0);
    let profitRmb = new Decimal(document.getElementById("profit_rmb").value || 0);
    let MOQ = '';
    let quoteType = document.getElementById("quote-type").value; // 获取备注格式选择
    let notes = "";
    let pickUpFee = "";


    // 获取复选框值
    let isRemoteAddress = document.getElementById('remote-address').checked;
    let isMOQ = document.getElementById('MOQ').checked;
    let isDDU = document.getElementById('ddu_check').checked;

    // 获取提货费
    let pickupFeeCheck = document.getElementById("pickup-fee-checkbox").checked;
    pickUpFee = pickupFeeCheck ? parseFloat(document.getElementById("pickup-fee").value) || 0 : 0;
    pickUpFee = new Decimal(pickUpFee).dividedBy(exchange_rate).toFixed(0);

    // 计算材积重 (kg) 使用公式：体积 * 1000000 / 6000
    if (totalVolume.greaterThan(0)) {
        dimensionWeight = Math.ceil(totalVolume.mul(1000000).dividedBy(6000));
        document.getElementById('dimensionWeight').value = dimensionWeight;
    } else {
        dimensionWeight = 0;
        document.getElementById('dimensionWeight').value = 0;
    }

    // 计算计费重 (kg)：取总实重与材积重的较大者
    let chargeWeight = Decimal.max(totalWeight, dimensionWeight);
    if (channel.includes('express')) {
        let moqWeight = 0;
        let moqUnit = 0;
        if (channel == 'Air express' || channel == 'Air ups/fedex') {
            moqWeight = totalQuantity.mul(10);
            moqUnit = 10;
        } else {
            moqWeight = totalQuantity.mul(12);
            moqUnit = 12;
        }
        if (chargeWeight.lessThan(moqWeight)) {
            chargeWeight = moqWeight;
            MOQ = 'MOQ each box is '+ moqUnit + 'kg';
        }
    }
    document.getElementById('chargeWeight').value = chargeWeight;

    // 计算计费重 (CBM)：取总实重与材积重的较大者
    let chargeCBM = Math.ceil(Decimal.max(totalWeight.dividedBy(363), totalVolume)* 100) / 100;
    document.getElementById('chargeCBM').value = chargeCBM;

    // 计算泡比
    let volumeRatio = new Decimal(0);
    if (!totalWeight.equals(0) && !totalVolume.equals(0)) {
        volumeRatio = totalWeight.dividedBy(totalVolume);
        document.getElementById('volumeRatio').value = volumeRatio.toFixed(0);
    } else {
        volumeRatio = 0;
        document.getElementById('volumeRatio').value = 0;
    }

    // 泡比颜色设置
    let volumeRatioInput = document.getElementById('volumeRatio');
    if (volumeRatio >= 200) {
        volumeRatioInput.style.color = 'green'; // 大于等于200时字体为绿色
    } else if (volumeRatio < 167) {
        volumeRatioInput.style.color = 'blue'; // 小于167时字体为蓝色
    } else {
        volumeRatioInput.style.color = ''; // 恢复默认颜色
    }

    // 计算报价 (RMB) = 成本 (RMB) + 利润 (RMB)
    let priceRmb = costRmb.add(profitRmb);
    document.getElementById("price_rmb").value = priceRmb.toFixed(2);

    // 计算报价 (USD) = 报价 (RMB) / exchange_rate
    let priceUsd = new Decimal(0);
    if (quoteType.includes("CBM")) {
        priceUsd = priceRmb.dividedBy(exchange_rate).toFixed(0);
    } else {
        priceUsd = priceRmb.dividedBy(exchange_rate).toFixed(2); // 保留两位小数
    }
    document.getElementById("price_usd").value = priceUsd;

    // 计算利率 = 1 - (成本 (RMB) / 报价 (RMB))
    if (!costRmb.equals(0) && !priceRmb.equals(0)) {
        let profitRate = new Decimal(1).minus(costRmb.dividedBy(priceRmb));
        document.getElementById("profit_rate").value = Math.ceil(profitRate * 100) + "%"; // 显示为百分比
    }

    // 计算总利润 (RMB) = 计费重 * 利润 (RMB)
    let totalProfitRmb = chargeWeight.mul(profitRmb);
    document.getElementById("total_profit_rmb").value = totalProfitRmb; // 保留两位小数

    // 更新利率的 Tooltip
    updateProfitRateTooltip(totalProfitRmb);

    // 计算总报价 (USD)
    let totalPriceUsd = new Decimal(0);
    if (quoteType.includes("CBM")) {
        totalPriceUsd = new Decimal(priceUsd).mul(chargeCBM);
    } else {
        totalPriceUsd = new Decimal(priceUsd).mul(chargeWeight);
    }
    document.getElementById("total_price_usd").value = totalPriceUsd;

    // 计算总报价 (RMB) = 总报价 (RMB) / exchange_rate
    let totalPriceRMB = new Decimal(0);
    if (quoteType.includes("CBM")) {
        totalPriceRMB = new Decimal(priceRmb).mul(chargeCBM);
    } else {
        totalPriceRMB = new Decimal(priceRmb).mul(chargeWeight);
    }
    document.getElementById("total_price_rmb").value = totalPriceRMB.toFixed(2);

    let unit = 'ctns ';
    if (totalQuantity <= 1) {
        unit = 'ctn ';
    }

    // 根据选择的备注格式动态生成备注内容
    if (quoteType === "通用") {
        // 构建备注内容
        notes = 'To ' + address + ',' + totalQuantity.toFixed(0) + unit + totalWeight.toFixed(0) + 'kg ' + totalVolume.toFixed(2) + 'cbm' +
            '\n';
        if (isDDU) {
            notes += 'DDU ';
        }
        notes += channel + ": " + priceUsd + ' usd/kg * ' + chargeWeight.toFixed(0) + 'kg ';
        if (isDDU) {
            if (country == "英国") {
                notes += '+ 48usd ';
                totalPriceUsd = new Decimal(totalPriceUsd).plus(48);
            } else if (country == "欧洲") {
                notes += '+ 62usd ';
                totalPriceUsd = new Decimal(totalPriceUsd).plus(62);
            }
        }
        notes += '= ' + totalPriceUsd + 'usd ' + MOQ + ' ';
        const moqInput = document.getElementById('moq-input');
        if (isMOQ) {
            const moqValue = moqInput.value || 21; // 默认值为 21kg
            notes += `MOQ is ${moqValue}kg `;
        }

        notes += getTransitTime(country, channel, postcode) + 'days';
        if (isRemoteAddress) {

            notes += getRemoteAddressfee(totalQuantity);
        }
        
        if (pickupFeeCheck) {
            notes += '\n' + 'Pick up fee: ' + pickUpFee + ' usd';
        }


    } else if (quoteType === "通用-CBM") {
        // 构建备注内容
        notes = 'To ' + address + ',' + totalQuantity.toFixed(0) + unit + totalWeight.toFixed(0) + 'kg ' + totalVolume.toFixed(2) + 'cbm' +
            '\n';
        if (isDDU) {
            notes += 'DDU ';
        }
        notes += channel + ": " + priceUsd + ' usd/cbm * ' + chargeCBM + 'cbm = ' + totalPriceUsd + 'usd ';

        notes += getTransitTime(country, channel, postcode) + 'days';

    } else if (quoteType === "通用-单价") {
        // 构建备注内容
        notes = address + ' ' + channel + ': ' + priceUsd + ' usd per kg ' + getTransitTime(country, channel, postcode) + 'days';

    } else if (quoteType === "通用-RMB") {
        // 构建备注内容
        notes = address + ' ' + totalQuantity.toFixed(0) + '箱 ' + totalWeight.toFixed(0) + 'kg ' + totalVolume + 'cbm' +
            '\n';
        if (isDDU) {
            notes += 'DDU ';
        }
        notes += getCN(channel) + ": " + priceRmb + 'RMB/kg * ' + chargeWeight.toFixed(0) + 'kg = ' + totalPriceRMB + 'RMB ' + MOQ + ' ' +
            getTransitTime(country, channel, postcode) + '天';

    } else if (quoteType === "通用-RMB-CBM") {
        // 构建备注内容
        notes = totalQuantity.toFixed(0) + '箱 ' + totalWeight.toFixed(0) + 'kg ' + totalVolume + 'cbm' +
            '\n';
        if (isDDU) {
            notes += 'DDU ';
        }
        notes += getCN(channel) + ": " + priceRmb + 'RMB/cbm * ' + chargeCBM + 'kg = ' + totalPriceRMB + 'RMB ' + MOQ + ' ' +
            getTransitTime(country, channel, postcode) + '天';

    } else if (quoteType === "PROBOXX") {
        // 构建备注内容
        notes = 'Hi Tal,' +
            '\n' + '\n' +
            'To ' + address + ',' + totalQuantity.toFixed(0) + unit + totalWeight.toFixed(0) + 'kg ' + totalVolume + 'cbm' +
            '\n';
        if (isDDU) {
            notes += 'DDU ';
        } else {
            notes += 'DDP ';
        }
        notes += channel + ": " + priceUsd + ' usd per kg. estimate : ' +
            priceUsd + 'usd/kg * ' + chargeWeight.toFixed(0) + 'kg = ' + totalPriceUsd + 'usd ' + MOQ + ' ' +
            getTransitTime(country, channel, postcode) + 'days';
            if (isRemoteAddress) { notes += getRemoteAddressfee(totalQuantity);}   
            notes += '\n' +
            'Pick up fee: ' + pickUpFee + ' usd' +
            '\n' + '\n' +
            'Valid date: ' + valid_date;
    } else if (quoteType === "PROBOXX-CBM") {
        // 构建备注内容
        notes = 'Hi Tal,' +
            '\n' + '\n' +
            'To ' + address + ',' + totalQuantity.toFixed(0) + unit + totalWeight.toFixed(0) + 'kg ' + totalVolume + 'cbm' +
            '\n';
        if (isDDU) {
            notes += 'DDU ';
        } else {
            notes += 'DDP ';
        }
        notes += channel + ": " + priceUsd + ' usd per cbm. estimate : ' +
            priceUsd + 'usd/cbm * ' + chargeCBM + 'cbm = ' + totalPriceUsd + 'usd ' +
            getTransitTime(country, channel, postcode) + 'days' +
            '\n' +
            'Pick up fee: ' + pickUpFee + ' usd' +
            '\n' + '\n' +
            'Valid date: ' + valid_date;
    }

    // 将备注内容填入 textarea
    document.getElementById("notes").value = notes;

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
}

// 识别箱规信息
function parseDimensions() {
    // 获取输入的文本
    const input = document.getElementById("dimension-input").value.trim();

    // 使用正则表达式解析长、宽、高、重量和箱数
    const dimensionRegex = /(\d+(\.\d+)?)\s*[*xX×]\s*(\d+(\.\d+)?)\s*[*xX×]\s*(\d+(\.\d+)?)\s*(cm|inch|in|英寸)?/i;
    const weightRegex = /([\d.]+)\s*(kg|kgs|lb|lbs|磅)/i;
    const quantityRegex = /(\d+)\s*(X|\s*)\s*(BOX|BOXES|Boxs|CARTON|CARTONS|ctn|ctns|件|箱|pal|pallets|托)/i;

    // 提取长、宽、高
    const dimensionMatch = input.match(dimensionRegex);
    let length = 0,
        width = 0,
        height = 0;
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

    // 提取箱数
    const quantityMatch = input.match(quantityRegex);
    const quantity = quantityMatch ? parseInt(quantityMatch[1]) : 0;

    // 获取当前行的输入框
    const rows = document.querySelectorAll('.input-row');
    const currentRow = rows[rows.length - 1];

    // 填充到长、宽、高列
    currentRow.querySelector('.length').value = Math.ceil(length);
    currentRow.querySelector('.width').value = Math.ceil(width);
    currentRow.querySelector('.height').value = Math.ceil(height);

    // 填充到单箱实重列
    currentRow.querySelector('.weight').value = weight.toFixed(2);

    // 填充到箱数列
    currentRow.querySelector('.quantity').value = quantity;

    // 触发计算
    calculate();
}

// 识别地址、箱数、重量、体积信息
function parsePackageInfo() {
    const input = document.getElementById("package-info-input").value.trim();
    // 使用正则表达式解析箱数、重量、体积
    const volumeRegex = /([\d.]+)\s*(cbm|方)/i;
    const weightRegex = /([\d.]+)\s*(kg|kgs|lb|lbs|磅)/i;
    const quantityRegex = /(\d+)\s*(X|\s*)\s*(BOX|BOXES|Boxs|CARTON|CARTONS|ctn|ctns|件|箱|pal|pallets|托)/i;
    const addressRegex = /\b([A-Z]{3}\d{1})\b/i;  // 识别开头3个字母 + 1个数字

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
    }

    document.getElementById('quantity').value = quantity;
    document.getElementById('weight').value = Math.ceil(weight);
    document.getElementById('volume').value = new Decimal(volume).toDecimalPlaces(2, Decimal.ROUND_UP);
    
    // 触发计算
    updateQuote();
}


// 计算按方成本
function calculateCost() {
    // 获取输入值
    const quantity = parseFloat(document.getElementById('t_quantity').value) || 0;
    const weight = new Decimal(parseFloat(document.getElementById('t_weight').value) || 0);
    const volume = new Decimal(parseFloat(document.getElementById('t_volume').value) || 0);
    const pricePerCbm = new Decimal(parseFloat(document.getElementById('t_price-per-cbm').value) || 0);
    const goodsValue = new Decimal(parseFloat(document.getElementById('t_goods-value').value) || 0);
    const taxRate = new Decimal(parseFloat(document.getElementById('t_tax-rate').value) || 0);
    const deliveryFeeUSD = new Decimal(parseFloat(document.getElementById('t_delivery-fee-usd').value) || 0);

    // 计算计费方
    let chargeVolume = Decimal.max(volume, weight.dividedBy(363).toDecimalPlaces(2, Decimal.ROUND_UP));
    document.getElementById('t_charge-volume').textContent = chargeVolume.toFixed(2);

    // 计算泡比 泡比 = 实重 / 体积
    let volumeRatio = new Decimal(0);
    if (weight != 0 && volume != 0) {
        volumeRatio = weight.dividedBy(volume);
        document.getElementById('t_volume-ratio').textContent = volumeRatio.toFixed(0);
    }

    // 计算头程费用
    const forwardingCost = pricePerCbm.mul(chargeVolume);
    document.getElementById('t_freight-forwarding-cost').textContent = forwardingCost.toDecimalPlaces(2, Decimal.ROUND_UP);

    // 计算税金
    const taxAmount = goodsValue.mul(taxRate.plus(10)).dividedBy(100).mul(chargeVolume).mul(exchange_rate);
    document.getElementById('t_tax-amount').textContent = taxAmount.toDecimalPlaces(0, Decimal.ROUND_UP);

    // 计算派送费 (RMB)
    const deliveryFeeRMB = deliveryFeeUSD.mul(exchange_rate);
    document.getElementById('t_delivery-fee-rmb').textContent = deliveryFeeRMB.toFixed(2);

    // 计算总成本
    const totalCost = forwardingCost.plus(taxAmount).plus(deliveryFeeRMB);
    document.getElementById('t_total-cost').textContent = totalCost.toDecimalPlaces(0, Decimal.ROUND_UP);

    // 计算单价 (RMB/cbm)
    const unitPriceCbm = totalCost.dividedBy(chargeVolume);
    document.getElementById('t_unit-price-cbm').textContent = unitPriceCbm.toDecimalPlaces(0, Decimal.ROUND_UP);

    // 计算单价 (RMD/kg)
    const unitPriceKg = totalCost.dividedBy(weight);
    document.getElementById('t_unit-price-kg').textContent = unitPriceKg.toFixed(2);
}

 // 获取所有术语
 const allTerms = Object.values(termsByCategory).flat();

 // 分页相关变量
 let currentPage = 1;
 const termsPerPage = 10; // 每页显示的术语数量

 function renderTerms(filteredTerms = allTerms) {
    const termList = document.getElementById("termList");
    termList.innerHTML = ''; // 清空列表

    if (filteredTerms.length === 0) {
        document.getElementById("noResults").style.display = 'block';
    } else {
        document.getElementById("noResults").style.display = 'none';

        // 计算当前页的术语
        const startIndex = (currentPage - 1) * termsPerPage;
        const endIndex = startIndex + termsPerPage;
        const termsToShow = filteredTerms.slice(startIndex, endIndex);

        termsToShow.forEach(term => {
            const card = document.createElement('div');
            card.className = 'term-card';
            card.setAttribute('data-term', term.chinese);
            card.innerHTML = `
                <div class="card-body">
                    <h5 data-bs-toggle="tooltip" data-bs-title="${term.definition || '暂无释义'}">${term.chinese}</h5>
                    <p data-bs-toggle="tooltip" data-bs-title="${term.definition || '暂无释义'}">
                        ${term.english}
                        <span class="copy-btn" onclick="copyTerm(this, '${term.english}')">
                            <i class="bi bi-clipboard"></i>
                        </span>
                    </p>
                    <div class="tags">
                        ${term.tags.map(tag => {
                            const color = tagColors[tag] || "#6c757d"; // 默认灰色
                            return `<span class="badge" style="background-color: ${color}; color: white;">${tag}</span>`;
                        }).join('')}
                    </div>
                </div>
            `;
            termList.appendChild(card);
        });

        // 初始化 Tooltip
        const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
        const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
    }

    // 更新翻页按钮状态
    updatePaginationButtons(filteredTerms.length);
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
         const filteredTerms = termsByCategory[category] || [];
         renderTerms(filteredTerms);
     }

     // 重置当前页为第一页
     currentPage = 1;
 }

 // 搜索功能
 const searchInput = document.getElementById('searchInput');
 searchInput.addEventListener('input', function () {
     const keyword = this.value.trim().toLowerCase();
     const filteredTerms = allTerms.filter(term => 
         term.chinese.toLowerCase().includes(keyword) || 
         term.english.toLowerCase().includes(keyword)
     );
     renderTerms(filteredTerms);

     // 重置当前页为第一页
     currentPage = 1;
 });

 // 清除搜索
 function clearSearch() {
     searchInput.value = '';
     renderTerms(allTerms); // 重置为全部术语

     // 重置当前页为第一页
     currentPage = 1;
 }

 // 翻页功能
 function prevPage() {
     if (currentPage > 1) {
         currentPage--;
         renderTerms(getFilteredTerms());
     }
 }

 function nextPage() {
     const filteredTerms = getFilteredTerms();
     const totalPages = Math.ceil(filteredTerms.length / termsPerPage);
     if (currentPage < totalPages) {
         currentPage++;
         renderTerms(filteredTerms);
     }
 }

 // 获取当前筛选后的术语列表
 function getFilteredTerms() {
     const searchKeyword = document.getElementById('searchInput').value.trim().toLowerCase();
     const activeCategory = document.querySelector('.category-buttons .btn.active').textContent;

     if (activeCategory === '全部') {
         return allTerms.filter(term => 
             term.chinese.toLowerCase().includes(searchKeyword) || 
             term.english.toLowerCase().includes(searchKeyword)
         );
     } else {
         return (termsByCategory[activeCategory] || []).filter(term => 
             term.chinese.toLowerCase().includes(searchKeyword) || 
             term.english.toLowerCase().includes(searchKeyword)
         );
     }
 }

 // 更新翻页按钮状态
 function updatePaginationButtons(totalTerms) {
     const prevButton = document.getElementById('prevPage');
     const nextButton = document.getElementById('nextPage');

     if (prevButton && nextButton) {
        prevButton.disabled = currentPage === 1;
        nextButton.disabled = currentPage === Math.ceil(totalTerms / termsPerPage);
    } else {
        console.error('翻页按钮未找到');
    }
 }


 // 匹配邮编前缀到区域
function getRegionByZip(zip) {
    if (/^(0|1|2|3)/.test(zip)) return "美东0.1.2.3";
    else if (/^(4|5|6|7)/.test(zip)) return "美中4.5.6.7";
    else if (/^(96|97|98|99)/.test(zip)) return "美西96-99";
    else if (/^(8|9|90|91|92|93|94|95)/.test(zip)) return "美西8.9";
    
    return null;
}

// 获取重量对应的价格索引
function getWeightIndex(weight) {
    if (weight <= 12) return 0;
    if (weight <= 21) return 1;
    if (weight <= 45) return 2;
    if (weight <= 71) return 3;
    return 4; // 101KG+
}

// 动态生成快递派价格表格
function renderPriceTable() {
    const channel = document.getElementById("t4_channel").value;
    const southChinaTableElement = document.getElementById("southChinaPriceTable").getElementsByTagName("tbody")[0];
    const eastChinaTableElement = document.getElementById("eastChinaPriceTable").getElementsByTagName("tbody")[0];
    southChinaTableElement.innerHTML = ""; // 清空表格内容
    eastChinaTableElement.innerHTML = ""; // 清空表格内容

    // 获取当前渠道的价格数据
    const currentPriceTable = priceTable[channel];

    // 遍历价格数据表
    Object.keys(currentPriceTable).forEach(area => {
        // 添加华南价格行
        const southChinaRow = document.createElement("tr");
        southChinaRow.innerHTML = `
            <td>${area}</td>
            <td>${currentPriceTable[area]["华南"][0]}</td>
            <td>${currentPriceTable[area]["华南"][1]}</td>
            <td>${currentPriceTable[area]["华南"][2]}</td>
            <td>${currentPriceTable[area]["华南"][3]}</td>
            <td>${currentPriceTable[area]["华南"][4]}</td>
        `;
        southChinaTableElement.appendChild(southChinaRow);

        // 添加华东价格行
        const eastChinaRow = document.createElement("tr");
        eastChinaRow.innerHTML = `
            <td>${area}</td>
            <td>${currentPriceTable[area]["华东"][0]}</td>
            <td>${currentPriceTable[area]["华东"][1]}</td>
            <td>${currentPriceTable[area]["华东"][2]}</td>
            <td>${currentPriceTable[area]["华东"][3]}</td>
            <td>${currentPriceTable[area]["华东"][4]}</td>
        `;
        eastChinaTableElement.appendChild(eastChinaRow);
    });
}

// 计算价格并突出显示对应的单元格
function calculatePrice(region,channel,zipcode,weight) {

    if (!zipcode || isNaN(weight) || weight <= 0) {
        document.getElementById("t4_priceResult").innerHTML = "单价：请输入有效的邮编和重量";
        return;
    }
    
    const area = getRegionByZip(zipcode);
    if (!area || !priceTable[channel] || !priceTable[channel][area] || !priceTable[channel][area][region]) {
        document.getElementById("t4_priceResult").innerHTML = "单价：邮编不在配送范围内";
        console.log(JSON.stringify(priceTable, null, 2));
        return;
    }

    renderPriceTable();

    const weightIndex = getWeightIndex(weight);
    
    const price = priceTable[channel][area][region][weightIndex];

    document.getElementById("t4_priceResult").innerHTML = `单价：$${price} / KG`;

    // 突出显示对应的单元格
    highlightPriceCell(area, region, weightIndex);

    return price;
}

/* 计算成本 */
function showCost(origin,country,channel,postcode,weight,withBattery){

    let cost = 0;
    if(origin && country && channel.includes('express')){
        if (channel == 'Fast sea express' || channel == 'Fast Maston express' 
            || channel == 'Super sea express' || channel == 'Fast sea ups/fedex'){
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


// 获取偏远费
function getRemoteAddressfee(totalQuantity) {
    let remoteAddressStr = LINE_BREAK + 'Remote address fee: ';
    let remoteAddressFee = new Decimal(3.5).mul(totalQuantity);
    if (remoteAddressFee.lessThan(21)) {
        remoteAddressStr += 'MOQ is 21usd ';
    } else {
        remoteAddressStr += '3.5usd/ctn * ' + totalQuantity.toFixed(0) + 'ctns = ' + remoteAddressFee.toFixed(2) + 'usd ';
    }

    return remoteAddressStr;
}

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
}

// 更新标签按钮样式
function updateTagButtonStyles() {
    const tagButtons = document.querySelectorAll("#termTagBtns button");
    tagButtons.forEach(button => {
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
    });
}
function filterTermsByTags() {
    const allTerms = Object.values(termsByCategory).flat();

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
    const allTerms = Object.values(termsByCategory).flat();
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
}