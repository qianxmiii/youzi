# costCalTab 成本计算迁移分析

来源：

- `index.html`：`#costCalTab`
- `js/tab.js`：`parseCalTabCargoInfo`、`calculateCostDDU`、`calculateCostDDPRow` 等
- `js/logistics.js`：汇率常量 `exchange_rate = 6.8`、`cost_exchange_rate = 7.1`
- `data/data.js`：常用产品、HS Code、税率
- `data/data_price.js`：包税成本「按 kg 表价」下拉选项

本文用于迁移到 `youzi_v2` 前的业务梳理。当前旧版实现是纯前端 DOM 计算，没有后端 API。

## 1. 功能说明

`costCalTab` 是旧版首页里的“成本计算”Tab，用于根据货物重量、体积、表价、税率、派送费等参数快速计算物流成本。

页面分为三部分：

1. 成本计算参数
   - 支持从一段文本中自动识别箱数、重量、体积、尺寸。
   - 支持选择常用产品，自动带出 HS Code 和税率。
   - 支持选择重量比：`363`、`360`、`400`、`450`、`500`、`实际方`。

2. 自税成本计算
   - 适用于税金单独计算的成本模型。
   - 输入按方表价、货值、税率、派送费。
   - 输出计费方、泡比、头程费、税金、总成本、单价/cbm、单价/kg。
   - 支持“按方包税”开关：开启后按方价格会叠加额外包税金额，同时货值置 0 并禁用。

3. 包税成本计算
   - 适用于按 kg 表价包税的成本模型。
   - 支持多行计算，可新增、复制、删除行。
   - 输入实重、体积、按 kg 表价、派送费 USD、派送费 RMB。
   - 输出计费重、计费方、泡比、头程费、最终派送费、总成本、单价/cbm、单价/kg。

## 2. 所有计算公式

### 2.1 统一识别逻辑

输入框：`cargo-input`

支持识别：

| 类型 | 识别规则 | 示例 |
| --- | --- | --- |
| 箱数 | 数字 + `BOX` / `BOXES` / `Boxs` / `CARTON` / `CARTONS` / `ctn` / `ctns` / `件` / `箱` / `pal` / `pallets` / `托` | `21ctns` |
| 重量 | 数字 + `kg` / `kgs` / `lb` / `lbs` / `磅` | `8.3 kg` |
| 体积 | 数字 + `cbm` / `方` | `2.126 cbm` |
| 尺寸 | `L*W*H`，分隔符支持 `*` / `x` / `X` / `×` / 西里尔 `х` / `Х` | `50*40*30cm` |
| 地址代码 | 可识别 `ABC1` 形式，但当前识别结果未写入页面字段 | `To ONT8` |

重量换算：

```text
如果单位是 lb / lbs / 磅：
weight_kg = weight_lb * 0.453592
```

尺寸换算到厘米：

```text
inch / in / 英寸：cm = inch * 2.54
mm：cm = mm / 10
m / 米：cm = m * 100
cm 或空单位：按 cm 处理
```

尺寸推导体积：

```text
如果识别到尺寸、箱数 > 0，并且没有直接识别到体积：
volume_cbm = length_cm * width_cm * height_cm * quantity / 1,000,000
```

写入页面时：

```text
t_quantity = quantity
t_weight = ceil(weight_kg)
t_volume = ceil_to_2_decimal_places(volume_cbm)

tp_quantity_i = quantity
tp_weight_i = ceil(weight_kg)
tp_volume_i = ceil_to_2_decimal_places(volume_cbm)
```

其中 `ceil_to_2_decimal_places` 对应 Decimal.js：

```js
new Decimal(value).toDecimalPlaces(2, Decimal.ROUND_UP)
```

### 2.2 常用产品税率

产品数据来自 `window.data.commonProducts`：

| 产品 | HS Code | 税率 |
| --- | --- | --- |
| 脚轮 | `3926909985` | `12.8` |
| 门把手 | `8302426000` | `10.9` |
| 气球 | `9505906000` | `0` |
| 装饰板 | `3926400010` | `5.3` |
| 大豆蜡 | `3406000000` | `7.5` |
| 橡胶手套 | `3926201050` | `0` |
| 游戏卡牌 | `9504904000` | `0` |

选择产品后：

```text
t_tax-rate = product.taxrate
product-hscode = product.hscode
重新计算自税成本
```

取消选择后：

```text
t_tax-rate = ""
product-hscode = ""
```

### 2.3 重量比与计费方

重量比字段：`weight-ratio-select`

可选值：

```text
363 / 360 / 400 / 450 / 500 / actual
```

自税和包税都使用同一套计费方公式：

```text
如果 weightRatio = actual：
chargeVolume = volume

否则：
weightVolume = ceil_to_2_decimal_places(weight / weightRatio)
chargeVolume = max(volume, weightVolume)
```

### 2.4 泡比

自税和包税均使用：

```text
volumeRatio = weight / volume
```

展示规则：

```text
volumeRatioDisplay = round_to_0_decimal_places(volumeRatio)
```

旧代码使用：

```js
volumeRatio.toFixed(0)
```

### 2.5 自税成本 DDU 公式

输入：

```text
quantity
weight
volume
pricePerCbm
goodsValue
taxRate
deliveryFeeUSD
weightRatio
byVolumeTaxIncluded
byVolumeTaxIncludedValue
```

汇率：

```text
cost_exchange_rate = 7.1
```

计费方：

```text
chargeVolume = weightRatio == actual
  ? volume
  : max(volume, ceil_to_2_decimal_places(weight / weightRatio))
```

按方包税开关：

```text
如果 byVolumeTaxIncluded = false：
actualPricePerCbm = pricePerCbm

如果 byVolumeTaxIncluded = true：
actualPricePerCbm = pricePerCbm + byVolumeTaxIncludedValue
goodsValue = 0
goodsValue 输入框禁用
```

头程费：

```text
forwardingCost = actualPricePerCbm * chargeVolume
forwardingCostDisplay = ceil_to_2_decimal_places(forwardingCost)
```

税金：

```text
taxAmount = goodsValue * ((taxRate + 20) / 100) * volume * cost_exchange_rate
taxAmountDisplay = ceil_to_0_decimal_places(taxAmount)
```

说明：旧版页面文案标注“美国基础关税加征 20%”，所以实际税率是输入税率再加 `20`。

派送费：

```text
deliveryFeeRMB = deliveryFeeUSD * cost_exchange_rate
deliveryFeeRMBDisplay = fixed_2_decimal_places(deliveryFeeRMB)
```

总成本：

```text
totalCost = forwardingCost + taxAmount + deliveryFeeRMB
totalCostDisplay = ceil_to_0_decimal_places(totalCost)
```

单价/cbm：

```text
unitPriceCbm = chargeVolume > 0 ? totalCost / chargeVolume : 0
unitPriceCbmDisplay = ceil_to_0_decimal_places(unitPriceCbm)
```

单价/kg：

```text
unitPriceKg = weight > 0 ? totalCost / weight : 0
unitPriceKgDisplay = fixed_2_decimal_places(unitPriceKg)
```

### 2.6 包税成本 DDP 公式

包税成本支持多行，每行字段 ID 带行号后缀：`_0`、`_1`、`_2`。

输入：

```text
quantity
weight
volume
pricePerKg
deliveryFeeUSD
deliveryFeeRMB
weightRatio
```

汇率：

```text
exchange_rate = 6.8
```

注意：DDP 用的是 `exchange_rate = 6.8`，DDU 用的是 `cost_exchange_rate = 7.1`。这是旧代码现状，迁移时需要确认是否有业务原因。

计费重：

```text
volumeWeight = volume * 1,000,000 / 6000
chargeWeight = ceil_to_0_decimal_places(max(weight, volumeWeight))
```

计费方：

```text
chargeVolume = weightRatio == actual
  ? volume
  : max(volume, ceil_to_2_decimal_places(weight / weightRatio))
```

泡比：

```text
volumeRatio = weight / volume
volumeRatioDisplay = round_to_0_decimal_places(volumeRatio)
```

头程费：

```text
forwardingCost = pricePerKg * chargeWeight
forwardingCostDisplay = ceil_to_2_decimal_places(forwardingCost)
```

派送费：

```text
deliveryFeeFromUSD = deliveryFeeUSD * exchange_rate
totalDeliveryFee = deliveryFeeRMB + deliveryFeeFromUSD
totalDeliveryFeeDisplay = fixed_2_decimal_places(totalDeliveryFee)
```

总成本：

```text
totalCost = forwardingCost + totalDeliveryFee
totalCostDisplay = ceil_to_0_decimal_places(totalCost)
```

单价/cbm：

```text
unitPriceCbm = chargeVolume > 0 ? totalCost / chargeVolume : 0
unitPriceCbmDisplay = ceil_to_0_decimal_places(unitPriceCbm)
```

单价/kg：

```text
unitPriceKg = chargeWeight > 0 ? totalCost / chargeWeight : 0
unitPriceKgDisplay = fixed_2_decimal_places(unitPriceKg)
```

### 2.7 包税 kg 表价下拉

来自 `window.ddpKgPriceOptions`：

| 选项 | 价格 |
| --- | --- |
| 洛杉矶自提(特惠) | `3.48` |
| 洛杉矶自提(OA) | `3.68` |
| 洛杉矶自提(以星合德) | `4.8` |
| 洛杉矶自提(美森) | `8.78` |
| 纽约自提 | `4.28` |
| 奥克兰自提 | `3.78` |
| 休斯顿自提 | `4.28` |
| 芝加哥自提 | `4.88` |
| 萨瓦纳自提 | `4.38` |

旧版使用 `<datalist>`，用户既可以选择预设价格，也可以手输价格。

## 3. 输入输出字段

### 3.1 公共输入字段

| 字段 ID | 名称 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `cargo-input` | 报价识别 | text | 空 | 输入自然语言货物信息 |
| `product-select` | 常用产品 | select | 空 | 选择后自动带出 HS Code 和税率 |
| `product-hscode` | 海关编码 | readonly text | 空 | 产品选择后展示 |
| `weight-ratio-select` | 重量比 | select | `363` | 控制计费方计算 |

### 3.2 自税 DDU 输入字段

| 字段 ID | 名称 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `t_quantity` | 箱数 | number | 空/0 | 隐藏列，当前不参与公式 |
| `t_weight` | 实重 kg | number | 空/0 | 参与计费方、泡比、单价/kg |
| `t_volume` | 体积 cbm | number | 空/0 | 参与计费方、税金、泡比 |
| `t_price-per-cbm` | 按方表价 RMB | number | 空/0 | 头程费单价 |
| `t_by-volume-tax-included` | 按方包税 | checkbox | false | 开启后叠加包税金额 |
| `t_by-volume-tax-included-value` | 按方包税附加值 | number | `0` | 仅开关开启时显示 |
| `t_goods-value` | 货值 USD | number | `167` | 税金基数；按方包税时置 0 并禁用 |
| `t_tax-rate` | 税率 % | number | 空/0 | 实际计算会额外加 20 |
| `t_delivery-fee-usd` | 派送费 USD | number | 空/0 | 按 `cost_exchange_rate` 转 RMB |

### 3.3 自税 DDU 输出字段

| 字段 ID | 名称 | 格式 | 公式 |
| --- | --- | --- | --- |
| `t_charge-volume` | 计费方 cbm | 2 位小数 | `max(volume, ceil2(weight / ratio))` 或实际方 |
| `t_volume-ratio` | 泡比 | 0 位小数 | `weight / volume` |
| `t_freight-forwarding-cost` | 头程费 RMB | 向上保留 2 位 | `actualPricePerCbm * chargeVolume` |
| `t_delivery-fee-rmb` | 派送费 RMB | 固定 2 位 | `deliveryFeeUSD * 7.1` |
| `t_tax-amount` | 税金 RMB | 向上取整 | `goodsValue * ((taxRate + 20) / 100) * volume * 7.1` |
| `t_total-cost` | 总成本 RMB | 向上取整 | `forwardingCost + taxAmount + deliveryFeeRMB` |
| `t_unit-price-cbm` | 单价 RMB/cbm | 向上取整 | `totalCost / chargeVolume` |
| `t_unit-price-kg` | 单价 RMB/kg | 固定 2 位 | `totalCost / weight` |

### 3.4 包税 DDP 输入字段

每行字段 ID 后缀为行号。

| 字段 ID 模板 | 名称 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `tp_quantity_{i}` | 箱数 | number | 空/0 | 隐藏列，当前不参与公式 |
| `tp_weight_{i}` | 实重 kg | number | 空/0 | 参与计费重、计费方、泡比 |
| `tp_volume_{i}` | 体积 cbm | number | 空/0 | 参与材积重、计费方、泡比 |
| `tp_price-per-kg_{i}` | 按 kg 表价 | number + datalist | 空/0 | 头程费单价 |
| `tp_delivery-fee-usd_{i}` | 派送费 USD | number | 空/0 | 按 `exchange_rate` 转 RMB |
| `tp_delivery-fee-rmb_{i}` | 派送费 RMB | number | 空/0 | 与 USD 折算值相加 |

### 3.5 包税 DDP 输出字段

| 字段 ID 模板 | 名称 | 格式 | 公式 |
| --- | --- | --- | --- |
| `tp_charge-weight_{i}` | 计费重 kg | 向上取整 | `max(weight, volume * 1000000 / 6000)` |
| `tp_charge-cbm_{i}` | 计费方 cbm | 向上保留 2 位 | `max(volume, ceil2(weight / ratio))` 或实际方 |
| `tp_volume-ratio_{i}` | 泡比 | 0 位小数 | `weight / volume` |
| `tp_freight-forwarding-cost_{i}` | 头程费 RMB | 向上保留 2 位 | `pricePerKg * chargeWeight` |
| `tp_delivery-fee-final_{i}` | 派送费 RMB | 固定 2 位 | `deliveryFeeRMB + deliveryFeeUSD * 6.8` |
| `tp_total-cost_{i}` | 总成本 RMB | 向上取整 | `forwardingCost + totalDeliveryFee` |
| `tp_unit-price-cbm_{i}` | 单价 RMB/cbm | 向上取整 | `totalCost / chargeVolume` |
| `tp_unit-price-kg_{i}` | 单价 RMB/kg | 固定 2 位 | `totalCost / chargeWeight` |

### 3.6 包税 DDP 行操作

| 操作 | 函数 | 行为 |
| --- | --- | --- |
| 新增行 | `addDDPRow()` | 克隆最后一行，更新 ID 和事件，清空输入，输出置 `0.00` |
| 复制行 | `copyDDPRow(rowIndex)` | 克隆指定行，复制输入和输出值，重新计算新行 |
| 删除行 | `deleteDDPRow(rowIndex)` | 至少保留一行；删除后重新编号所有行 ID 和事件 |

## 4. 边界条件

### 4.1 空值与非法数值

旧代码规则：

```js
parseFloat(value) || 0
```

因此：

- 空字符串按 `0` 处理。
- 非数字字符串按 `0` 处理。
- `NaN` 按 `0` 处理。
- 负数没有显式禁止，会参与计算。

迁移建议：在 `youzi_v2` 中应考虑禁止负数，或至少给出校验提示。

### 4.2 除零

自税：

```text
chargeVolume <= 0 时，unitPriceCbm = 0
weight <= 0 时，unitPriceKg = 0
```

包税：

```text
chargeVolume <= 0 时，unitPriceCbm = 0
chargeWeight <= 0 时，unitPriceKg = 0
```

泡比：

```text
weight = 0 或 volume = 0 时，显示 0
```

### 4.3 体积识别优先级

如果文本里直接包含体积，如 `2.126 cbm`，则使用直接识别的体积。

如果没有体积，但包含尺寸和箱数，则按尺寸推导体积。

如果有尺寸但没有箱数，则不会自动推导体积。

### 4.4 重量识别与取整

识别到重量后写入页面时会执行：

```text
weight = ceil(weight_kg)
```

例如 `8.3 kg` 会写入 `9`。

### 4.5 DDU 与 DDP 汇率不一致

旧代码存在两个汇率：

```text
exchange_rate = 6.8
cost_exchange_rate = 7.1
```

DDU 使用 `7.1`。

DDP 使用 `6.8`。

迁移时需要确认：

- 是否保留两个汇率。
- 是否改为系统配置。
- 是否按业务模块命名，例如 `taxCostExchangeRate`、`deliveryExchangeRate`。

### 4.6 按方包税开关

开启：

```text
显示 t_by-volume-tax-included-value
t_goods-value = 0
t_goods-value.disabled = true
actualPricePerCbm = t_price-per-cbm + t_by-volume-tax-included-value
```

关闭：

```text
隐藏 t_by-volume-tax-included-value
t_goods-value.disabled = false
如果货值为空或 0，则恢复为 167
```

### 4.7 包税 DDP 至少一行

删除行时：

```text
如果总行数 <= 1，不执行删除
```

初始行删除按钮禁用；当多行存在时，新增/复制出来的行可以删除。

### 4.8 潜在兼容问题

1. 地址代码识别后没有被使用。
   - `addressRegex` 存在，但没有写入任何字段。

2. `quantity` 当前不参与任何成本公式。
   - 只作为隐藏字段保存和同步到 DDU/DDP。

3. DDP 表头存在两个“派送费(RMB)”列。
   - 一个是输入 `tp_delivery-fee-rmb_{i}`。
   - 一个是输出 `tp_delivery-fee-final_{i}`。
   - 迁移时建议改名为“派送费(RMB输入)”和“派送费合计(RMB)”。

4. DDU 税金使用 `volume`，不是 `chargeVolume`。
   - 公式为 `goodsValue * taxRate * volume * 汇率`。
   - 是否应使用实际体积还是计费方，需要业务确认。

5. DDP 计费重使用材积重 `volume * 1000000 / 6000`，与页面重量比选择无关。
   - 重量比只影响 `计费方` 和 `单价/cbm`。

## 5. 测试案例

以下案例按旧代码公式计算，迁移后应保持一致，除非业务确认要修正。

### 5.1 货物文本识别：重量 kg + 体积 cbm

输入：

```text
cargo-input = "21ctns 8.3 kg 2.126 cbm"
```

期望：

```text
t_quantity = 21
t_weight = 9
t_volume = 2.13
tp_quantity_0 = 21
tp_weight_0 = 9
tp_volume_0 = 2.13
```

### 5.2 货物文本识别：磅转 kg

输入：

```text
cargo-input = "10ctns 100 lbs 1.2 cbm"
```

计算：

```text
100 * 0.453592 = 45.3592
ceil(45.3592) = 46
```

期望：

```text
t_quantity = 10
t_weight = 46
t_volume = 1.20
```

### 5.3 货物文本识别：尺寸推导体积

输入：

```text
cargo-input = "2ctns 10kg 50*40*30cm"
```

计算：

```text
volume = 50 * 40 * 30 * 2 / 1,000,000 = 0.12 cbm
weight = 10
```

期望：

```text
t_quantity = 2
t_weight = 10
t_volume = 0.12
```

### 5.4 自税 DDU：普通自税

输入：

```text
weightRatio = 363
t_weight = 100
t_volume = 0.20
t_price-per-cbm = 1000
t_goods-value = 167
t_tax-rate = 10
t_delivery-fee-usd = 20
t_by-volume-tax-included = false
cost_exchange_rate = 7.1
```

计算：

```text
weight / 363 = 0.27548 -> ceil2 = 0.28
chargeVolume = max(0.20, 0.28) = 0.28
forwardingCost = 1000 * 0.28 = 280.00
taxAmount = 167 * ((10 + 20) / 100) * 0.20 * 7.1 = 71.142 -> ceil0 = 72
deliveryFeeRMB = 20 * 7.1 = 142.00
totalCost = 280 + 71.142 + 142 = 493.142 -> ceil0 = 494
unitPriceCbm = 493.142 / 0.28 = 1761.22 -> ceil0 = 1762
unitPriceKg = 493.142 / 100 = 4.93142 -> fixed2 = 4.93
```

期望显示：

```text
t_charge-volume = 0.28
t_volume-ratio = 500
t_freight-forwarding-cost = 280.00
t_tax-amount = 72
t_delivery-fee-rmb = 142.00
t_total-cost = 494
t_unit-price-cbm = 1762
t_unit-price-kg = 4.93
```

### 5.5 自税 DDU：实际方

输入：

```text
weightRatio = actual
t_weight = 100
t_volume = 0.20
t_price-per-cbm = 1000
t_goods-value = 167
t_tax-rate = 10
t_delivery-fee-usd = 20
```

期望：

```text
t_charge-volume = 0.20
forwardingCost = 200.00
taxAmount = 72
deliveryFeeRMB = 142.00
totalCost = ceil0(200 + 71.142 + 142) = 414
unitPriceCbm = ceil0(413.142 / 0.20) = 2066
unitPriceKg = fixed2(413.142 / 100) = 4.13
```

### 5.6 自税 DDU：按方包税开启

输入：

```text
weightRatio = 363
t_weight = 100
t_volume = 0.20
t_price-per-cbm = 1000
t_by-volume-tax-included = true
t_by-volume-tax-included-value = 200
t_goods-value = 0
t_tax-rate = 10
t_delivery-fee-usd = 20
```

计算：

```text
chargeVolume = 0.28
actualPricePerCbm = 1000 + 200 = 1200
forwardingCost = 1200 * 0.28 = 336.00
taxAmount = 0
deliveryFeeRMB = 142.00
totalCost = 478.00
```

期望：

```text
t_goods-value disabled = true
t_freight-forwarding-cost = 336.00
t_tax-amount = 0
t_total-cost = 478
t_unit-price-cbm = ceil0(478 / 0.28) = 1708
t_unit-price-kg = fixed2(478 / 100) = 4.78
```

### 5.7 包税 DDP：普通计算

输入：

```text
weightRatio = 363
tp_weight_0 = 100
tp_volume_0 = 0.20
tp_price-per-kg_0 = 4
tp_delivery-fee-usd_0 = 10
tp_delivery-fee-rmb_0 = 20
exchange_rate = 6.8
```

计算：

```text
volumeWeight = 0.20 * 1,000,000 / 6000 = 33.333
chargeWeight = ceil0(max(100, 33.333)) = 100
chargeVolume = max(0.20, ceil2(100 / 363)) = max(0.20, 0.28) = 0.28
forwardingCost = 4 * 100 = 400.00
deliveryFeeFromUSD = 10 * 6.8 = 68.00
totalDeliveryFee = 20 + 68 = 88.00
totalCost = 400 + 88 = 488
unitPriceCbm = ceil0(488 / 0.28) = 1743
unitPriceKg = fixed2(488 / 100) = 4.88
```

期望显示：

```text
tp_charge-weight_0 = 100
tp_charge-cbm_0 = 0.28
tp_volume-ratio_0 = 500
tp_freight-forwarding-cost_0 = 400.00
tp_delivery-fee-final_0 = 88.00
tp_total-cost_0 = 488
tp_unit-price-cbm_0 = 1743
tp_unit-price-kg_0 = 4.88
```

### 5.8 包税 DDP：材积重大于实重

输入：

```text
tp_weight_0 = 10
tp_volume_0 = 1.00
tp_price-per-kg_0 = 4
tp_delivery-fee-usd_0 = 0
tp_delivery-fee-rmb_0 = 0
```

计算：

```text
volumeWeight = 1.00 * 1,000,000 / 6000 = 166.6667
chargeWeight = 167
forwardingCost = 4 * 167 = 668
```

期望：

```text
tp_charge-weight_0 = 167
tp_freight-forwarding-cost_0 = 668.00
tp_total-cost_0 = 668
```

### 5.9 包税 DDP：新增/复制/删除行

步骤：

1. 初始只有第 0 行。
2. 点击新增行。
3. 点击复制第 0 行。
4. 删除第 1 行。

期望：

```text
新增行后：
- 行数 +1
- 新行 ID 后缀为当前行号
- 新行输入为空
- 新行输出为 0.00
- 新行删除按钮可用

复制行后：
- 行数 +1
- 输入值和输出值从源行复制
- 新行重新计算一次

删除行后：
- 至少保留一行
- 剩余行重新从 0 开始编号
- 每行 oninput / onclick 绑定到新的行号
```

### 5.10 空输入

输入：

```text
所有 number 输入为空
```

期望：

```text
所有参与计算的输入按 0 处理
自税：
t_charge-volume = 0.00
t_volume-ratio = 0
t_freight-forwarding-cost = 0.00
t_tax-amount = 0
t_delivery-fee-rmb = 0.00
t_total-cost = 0
t_unit-price-cbm = 0
t_unit-price-kg = 0.00

包税：
tp_charge-weight_0 = 0
tp_charge-cbm_0 = 0.00
tp_volume-ratio_0 = 0
tp_freight-forwarding-cost_0 = 0.00
tp_delivery-fee-final_0 = 0.00
tp_total-cost_0 = 0
tp_unit-price-cbm_0 = 0
tp_unit-price-kg_0 = 0.00
```

