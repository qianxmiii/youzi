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

// 获取偏远费
function getRemoteAddressfee(totalQuantity) {
    let remoteAddressStr = LINE_BREAK + 'Remote address fee: ';
    let remoteAddressFee = new Decimal(3.5).mul(totalQuantity);
    if (remoteAddressFee.lessThan(21)) {
        remoteAddressStr += 'MOQ is 21usd ';
        addFee = addFee.add(21);
    } else {
        remoteAddressStr += '3.5usd/ctn * ' + totalQuantity.toFixed(0) + 'ctns = ' + remoteAddressFee + 'usd ';
        addFee = addFee.add(remoteAddressFee);
    }

    return remoteAddressStr;
}

// 获取超尺寸费
function getOverSizeFee(country, totalQuantity) {
    let overSizeStr = LINE_BREAK + 'OverSize fee: ';
    let overSizeFee = new Decimal(21).mul(totalQuantity).toFixed(2);
    overSizeStr += '21usd/ctn * ' + totalQuantity.toFixed(0) + 'ctns = ' + overSizeFee+ 'usd ';
    addFee = addFee.add(overSizeFee);

    return overSizeStr;
}

// 获取超重费
function getOverWeightFee(country, totalQuantity) {
    let overWeightStr = LINE_BREAK + 'OverWeight fee: ';
    let overWeightFee = new Decimal(25).mul(totalQuantity).toFixed(2) ;
    overWeightStr += '25usd/ctn * ' + totalQuantity.toFixed(0) + 'ctns = ' + overWeightFee+ 'usd ';
    addFee = addFee.add(overWeightFee);
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