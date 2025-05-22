// 计算材积重
function calCBMWeight(totalVolume) {
    if (totalVolume.greaterThan(0)) {
        return new Decimal(Math.ceil(totalVolume.mul(1000000).dividedBy(6000)));
    }
    return new Decimal(0);
}

// 计算重货计费方
function calHeavyCargoChargeCBM(data) {
    return new Decimal(Math.ceil(Decimal.max(data.totalWeight.dividedBy(363), data.totalVolume) * 100) / 100);
}

// 计算泡比
function calculateVolumeRatio(data) {
    if (!data.totalWeight.equals(0) && !data.totalVolume.equals(0)) {
        return data.totalWeight.dividedBy(data.totalVolume);
    }
    return new Decimal(0);
}