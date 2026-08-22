/**
 * rules.js 规则相关功能
 */

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
    if (weight < 21) return 0;
    if (weight < 45) return 1;
    if (weight < 71) return 2;
    if (weight < 101) return 3;
    return 4; // 101KG+
}

// 获取偏远费/住宅费（费用规则相同，feeLabel 可选：'residential' 显示住宅费，否则显示偏远地址费）
function getRemoteAddressfee(totalQuantity, unit, feeLabel) {
    let remoteAddressStr = "";
    let remoteAddressFee = new Decimal(0);
    const isResidential = feeLabel === 'residential';
    if (unit == "RMB") {
        remoteAddressStr = LINE_BREAK + (isResidential ? '住宅费: ' : '偏远地址费: ');
        remoteAddressFee = new Decimal(25).mul(totalQuantity);
        if (remoteAddressFee.lessThan(150)) {
            remoteAddressStr += '25RMB/箱，低消150RMB ';
            addFee = addFee.add(21);
        } else {
            remoteAddressStr += '25RMB/箱 * ' + totalQuantity.toFixed(0) + '箱 = ' + remoteAddressFee + 'RMB ';
            addFee = addFee.add(remoteAddressFee);
        }
    } else {
        remoteAddressStr = LINE_BREAK + (isResidential ? 'Residential fee: ' : 'Remote address fee: ');
        remoteAddressFee = new Decimal(3.5).mul(totalQuantity);
        remoteAddressStr += '3.5usd/ctn * ' + totalQuantity.toFixed(0) + 'ctns = ' + remoteAddressFee + 'usd ';
            addFee = addFee.add(remoteAddressFee);
        // 去掉偏远费低消
        // if (remoteAddressFee.lessThan(21)) {
        //     remoteAddressStr += 'MOQ is 21usd ';
        //     addFee = addFee.add(21);
        // } else {
        //     remoteAddressStr += '3.5usd/ctn * ' + totalQuantity.toFixed(0) + 'ctns = ' + remoteAddressFee + 'usd ';
        //     addFee = addFee.add(remoteAddressFee);
        // }
    }
    return remoteAddressStr;
}

/** 超长/超尺寸/超重默认单价：Air express 用空派档，其它渠道用海派档 */
function isAirExpressChannel(channel) {
    return String(channel || '').includes('Air express');
}

function getSurchargeRates(channel) {
    if (isAirExpressChannel(channel)) {
        return {
            oversize: { rmb: 200, usd: 30 },
            overlength: { rmb: 200, usd: 30 },
            overweight: { rmb: 280, usd: 42 },
        };
    }
    return {
        oversize: { rmb: 150, usd: 21 },
        overlength: { rmb: 150, usd: 21 },
        overweight: { rmb: 180, usd: 25 },
    };
}

function currentQuoteChannel() {
    return document.getElementById('delivery-method-select')?.value || '';
}

function resolveSurchargeUnitFee(feePerBox, unit, rmbDefault, usdDefault) {
    let fee = feePerBox || (unit == "RMB" ? rmbDefault : usdDefault);
    if (feePerBox && unit == "USD") {
        fee = Math.round(feePerBox * usdDefault / rmbDefault);
    }
    return fee;
}

let lastSurchargeChannel = null;

/** 按当前渠道把超长/超尺寸/超重输入框同步为对应默认 RMB（仅覆盖空值或已知默认档） */
function applySurchargeFeeDefaults(force) {
    const channel = currentQuoteChannel();
    if (!force && channel === lastSurchargeChannel) return;
    lastSurchargeChannel = channel;
    const rates = getSurchargeRates(channel);
    const knownOversize = [150, 200];
    const knownOverweight = [180, 280];
    const overlengthEl = document.getElementById('overlength-input');
    const oversizeEl = document.getElementById('oversize-input');
    const overweightEl = document.getElementById('overweight-input');
    if (overlengthEl && (!overlengthEl.value || knownOversize.includes(Number(overlengthEl.value)))) {
        overlengthEl.value = rates.overlength.rmb;
    }
    if (oversizeEl && (!oversizeEl.value || knownOversize.includes(Number(oversizeEl.value)))) {
        oversizeEl.value = rates.oversize.rmb;
    }
    if (overweightEl && (!overweightEl.value || knownOverweight.includes(Number(overweightEl.value)))) {
        overweightEl.value = rates.overweight.rmb;
    }
}

// 获取超长费（默认单价与超尺寸相同）
function getOverLengthFee(country, totalQuantity, unit, feePerBox = null) {
    let overLengthStr = "";
    let overLengthFee = new Decimal(0);
    const rate = getSurchargeRates(currentQuoteChannel()).overlength;
    const fee = resolveSurchargeUnitFee(feePerBox, unit, rate.rmb, rate.usd);

    if (unit == "RMB") {
        overLengthStr = LINE_BREAK + '超长费: ';
        overLengthFee = new Decimal(fee).mul(totalQuantity).toFixed(2);
        overLengthStr += fee + 'RMB/箱 * ' + totalQuantity.toFixed(0) + '箱 = ' + overLengthFee + 'RMB ';
        addFee = addFee.add(overLengthFee);
    } else {
        overLengthStr = LINE_BREAK + 'OverLength fee: ';
        overLengthFee = new Decimal(fee).mul(totalQuantity).toFixed(2);
        overLengthStr += fee + 'usd/ctn * ' + totalQuantity.toFixed(0) + 'ctns = ' + overLengthFee + 'usd ';
        addFee = addFee.add(overLengthFee);
    }
    return overLengthStr;
}

// 获取超尺寸费
function getOverSizeFee(country, totalQuantity, unit, feePerBox = null) {
    let overSizeStr = "";
    let overSizeFee = new Decimal(0);
    const rate = getSurchargeRates(currentQuoteChannel()).oversize;
    const fee = resolveSurchargeUnitFee(feePerBox, unit, rate.rmb, rate.usd);

    if (unit == "RMB") {
        overSizeStr = LINE_BREAK + '超尺寸费: ';
        overSizeFee = new Decimal(fee).mul(totalQuantity).toFixed(2);
        overSizeStr += fee + 'RMB/箱 * ' + totalQuantity.toFixed(0) + '箱 = ' + overSizeFee + 'RMB ';
        addFee = addFee.add(overSizeFee)

    } else {
        overSizeStr = LINE_BREAK + 'OverSize fee: ';
        overSizeFee = new Decimal(fee).mul(totalQuantity).toFixed(2);
        overSizeStr += fee + 'usd/ctn * ' + totalQuantity.toFixed(0) + 'ctns = ' + overSizeFee + 'usd ';
        addFee = addFee.add(overSizeFee);
    }
    return overSizeStr;
}

// 获取超重费
function getOverWeightFee(country, totalQuantity, unit, feePerBox = null) {
    let overWeightStr = "";
    let overWeightFee = new Decimal(0);
    const rate = getSurchargeRates(currentQuoteChannel()).overweight;
    const fee = resolveSurchargeUnitFee(feePerBox, unit, rate.rmb, rate.usd);

    if (unit == "RMB") {
        overWeightStr = LINE_BREAK + '超重费: ';
        overWeightFee = new Decimal(fee).mul(totalQuantity).toFixed(2);
        overWeightStr += fee + 'RMB/箱 * ' + totalQuantity.toFixed(0) + '箱 = ' + overWeightFee + 'RMB ';
        addFee = addFee.add(overWeightFee);

    } else {
        overWeightStr = LINE_BREAK + 'OverWeight fee: ';
        overWeightFee = new Decimal(fee).mul(totalQuantity).toFixed(2);
        overWeightStr += fee + 'usd/ctn * ' + totalQuantity.toFixed(0) + 'ctns = ' + overWeightFee + 'usd ';
        addFee = addFee.add(overWeightFee);
    }


    return overWeightStr;
}

// 根据国家获取DDU操作费
/**
 * 
 * @param {*} country 
 * @param {0 中文 1 英文} type 
 * @returns 
 */
function getDDUFee(country,type){
    let str = '';
    if (country == "欧洲") {
        if (type == 0){
            str += '\n' + '清关费: 450RMB';
            addFee = addFee.add(450);
        } else {
            str += '\n' + 'Customs clearance fee: 62usd';
            addFee = addFee.add(62);
        }
        
    } else if (country == "英国") {
        if (type == 0){
            str += '\n' + '清关费: 350RMB';
            addFee = addFee.add(350);
        } else {
            str += '\n' + 'Customs clearance fee: 48usd';
            addFee = addFee.add(48);
        }        
    }
    return str;
}