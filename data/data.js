/**
 * data.js 数据配置文件
 */

const shippingChannels = {
    "卡派": [
      "Sea truck", 
      "Fast sea truck", 
      "Fast Maston truck",
      "Super Maston truck",
      "Normal Maston truck",
      "Normal sea truck",
      "Train truck",
      "Road truck",
    ],
    "快递派": [
      "Sea express", 
      "Air express", 
      "Air ups/fedex", 
      "Fast sea ups/fedex",
      "Fast sea express",
      "Fast Maston express",
      "Fast sea ups/fedex",
      "Super sea express",
      "Normal Maston express",
      "Normal sea express",
      "Normal sea ups/fedex",
      "Train express",
      "Road express"
    ]
  };
// 车型数据
const vehicleTypes = [
    {
        "name": "微面",
        "lengthRange": [140, 170], // 厢长范围 (cm)
        "loadWeightRange": [300, 500], // 载重范围 (kg)
        "loadVolumeRange": [1.7, 2.4] // 载方范围 (cbm)
    },
    {
        "name": "小面",
        "lengthRange": [180, 240],
        "loadWeightRange": [500, 800],
        "loadVolumeRange": [2.4, 4.0]
    },
    {
        "name": "中面",
        "lengthRange": [240, 320],
        "loadWeightRange": [800, 1200],
        "loadVolumeRange": [3.7, 6.1]
    },
    {
        "name": "微货",
        "lengthRange": [200, 290],
        "loadWeightRange": [800, 1200],
        "loadVolumeRange": [4.2, 6.7]
    },
    {
        "name": "小厢货",
        "lengthRange": [300, 370],
        "loadWeightRange": [1000, 1500],
        "loadVolumeRange": [7.2, 9.6]
    },
    {
        "name": "3米8",
        "lengthRange": [380, 410],
        "loadWeightRange": [1500, 2000],
        "loadVolumeRange": [12.3, 18.9]
    },
    {
        "name": "4米2",
        "lengthRange": [380, 430],
        "loadWeightRange": [1500, 2000],
        "loadVolumeRange": [12.3, 19.8]
    },
    {
        "name": "5米2",
        "lengthRange": [500, 620],
        "loadWeightRange": [2000, 6000],
        "loadVolumeRange": [21, 28.6]
    },
    {
        "name": "6米8",
        "lengthRange": [640, 720],
        "loadWeightRange": [6000, 10000],
        "loadVolumeRange": [35.3, 43.2]
    },
    {
        "name": "7米6",
        "lengthRange": [730, 780],
        "loadWeightRange": [8000, 12000],
        "loadVolumeRange": [42, 48.7]
    },
    {
        "name": "9米6",
        "lengthRange": [900, 980],
        "loadWeightRange": [10000, 18000],
        "loadVolumeRange": [51.8, 61.2]
    },
    {
        "name": "13米",
        "lengthRange": [1170, 1300],
        "loadWeightRange": [18000, 32000],
        "loadVolumeRange": [67.3, 81.1]
    },
    {
        "name": "17米5",
        "lengthRange": [1600, 1750],
        "loadWeightRange": [25000, 35000],
        "loadVolumeRange": [100, 137.2]
    }
];

const deliveryLocations = ["深圳仓", "义乌仓"]; // 收货地
const cargoTypes = ["纸箱", "托盘"]; // 货物类型

// 常用产品数据
const commonProducts = [
    {name: "脚轮", hscode: "3926909985", taxrate: "12.8" },
    {name: "门把手", hscode: "8302426000", taxrate: "10.9" },
    {name: "游戏卡牌", hscode: "9504904000", taxrate: "0" }
];

// 将数组数据挂载到 window 对象上
window.data = {
    vehicleTypes: vehicleTypes,
    deliveryLocations: deliveryLocations,
    cargoTypes: cargoTypes,
    commonProducts: commonProducts,
    seaTruckPrice: {
        "RDU4": 5.4,
        "ONT8": 3.5,
        "AVP1": 5.8,
        "LAS1": 4.2,
        "GYR3": 4.4   
    },
    // 承运商自定义价格配置（可按需扩展/维护）
    expressPricing: {
        // 承运商下可有多个渠道；渠道可继承承运商级别的断点/分组/价格并覆盖
        "鑫鲲鹏": {
            // 可选：承运商级默认（作为子渠道未配置项的继承来源）
            weightBreaks: [12, 21, 45, 71, 101],
            zipGroups: [
                { label: "美西96-99", prefixes: ["96", "97", "98", "99"] },
                { label: "美东0.1.2.3", prefixes: ["0", "1", "2", "3"] },
                { label: "美中4.5.6.7", prefixes: ["4", "5", "6", "7"] },
                { label: "美西8.9", prefixes: ["8", "9"] }
            ],
            channels: {
                "普船": {
                    // 子渠道可覆盖断点/分组
                    // weightBreaks: [12, 21, 45, 71, 101],
                    // zipGroups: [...],
                    prices: {
                        "华东": {
                            "美东0.1.2.3": [14.2, 13.2, 11.7, 10.2, 9.7],
                            "美中4.5.6.7": [13.2, 12.2, 10.7, 9.2, 8.7],
                            "美西8.9": [11.7, 10.7, 9.2, 7.7, 7.2],
                            "美西96-99": [13.2, 12.2, 10.7, 9.2, 8.7]
                        },
                        "华南": {
                            "美东0.1.2.3": [14.0, 13.0, 11.5, 10.0, 9.5],
                            "美中4.5.6.7": [13.0, 12.0, 10.5, 9.0, 8.5],
                            "美西8.9": [11.5, 10.5, 9.0, 7.5, 7.0],
                            "美西96-99": [13.0, 12.0, 10.5, 9.0, 8.5]
                        }
                    }
                },
                "美森加班": {
                    // 子渠道可覆盖断点/分组
                    // weightBreaks: [12, 21, 45, 71, 101],
                    // zipGroups: [...],
                    prices: {
                        "华东": {
                            "美东0.1.2.3": [17.5, 15.5, 15.0, 14.0, 13.0],
                            "美中4.5.6.7": [16.5, 14.5, 14.0, 13.0, 12.0],
                            "美西8.9": [15.0, 13.0, 12.5, 11.5, 10.5],
                            "美西96-99": [16.5, 14.5, 14.0, 13.0, 12.0]
                        },
                        "华南": {
                            "美东0.1.2.3": [18.0, 16.0, 15.5, 14.5, 13.5],
                            "美中4.5.6.7": [17.0, 15.0, 14.5, 13.5, 12.5],
                            "美西8.9": [15.5, 13.5, 13.0, 12.0, 11.0],
                            "美西96-99": [17.0, 15.0, 14.5, 13.5, 12.5]
                        }
                    }
                },
                // 与页面渠道下拉一致（示例：美森正班）
                "美森正班": {
                    // 子渠道可覆盖断点/分组
                    // weightBreaks: [12, 21, 45, 71, 101],
                    // zipGroups: [...],
                    prices: {
                        "华东": {
                            "美东0.1.2.3": [18.0, 16.0, 15.5, 14.5, 13.5],
                            "美中4.5.6.7": [17.0, 15.0, 14.5, 13.5, 12.5],
                            "美西8.9": [15.5, 13.5, 13.0, 12.0, 11.0],
                            "美西96-99": [17.0, 15.0, 14.5, 13.5, 12.5]
                        },
                        "华南": {
                            "美东0.1.2.3": [18.5, 16.5, 16.0, 15.0, 14.0],
                            "美中4.5.6.7": [17.5, 15.5, 15.0, 14.0, 13.0],
                            "美西8.9": [16.0, 14.0, 13.5, 12.5, 11.5],
                            "美西96-99": [17.5, 15.5, 15.0, 14.0, 13.0]
                        }
                    }
                },
                "以星合德": {
                    // 子渠道可覆盖断点/分组
                    // weightBreaks: [12, 21, 45, 71, 101],
                    // zipGroups: [...],
                    "华东": {
                        "美东0.1.2.3": [15.3, 14.3, 12.8, 11.3, 10.8],
                        "美中4.5.6.7": [14.3, 13.3, 11.8, 10.3, 9.8],
                        "美西8.9": [12.8, 11.8, 10.3, 8.8, 8.3],
                        "美西96-99": [14.3, 13.3, 11.8, 10.3, 9.8]
                    },
                    "华南": {
                        "美东0.1.2.3": [14.9, 13.9, 12.4, 10.9, 10.4],
                        "美中4.5.6.7": [13.9, 12.9, 11.4, 9.9, 9.4],
                        "美西8.9": [12.4, 11.4, 9.9, 8.4, 7.9],
                        "美西96-99": [13.9, 12.9, 11.4, 9.9, 9.4]
                    }
                },
                "空派不带电": {
                    weightBreaks: [12, 21, 71, 101],
                    prices: {
                        "华东": {
                            "美东0.1.2.3": [45, 43, 42, 40],
                            "美中4.5.6.7": [44, 42, 41, 39],
                            "美西8.9": [43, 41, 40, 38],
                            "美西96-99": [45, 43, 42, 40]
                        },
                        "华南": {
                            "美东0.1.2.3": [44, 42, 41, 39],
                            "美中4.5.6.7": [43, 41, 40, 38],
                            "美西8.9": [42, 40, 39, 37],
                            "美西96-99": [44, 42, 41, 39]
                        }
                    }
                },
                "空派带电": {
                    weightBreaks: [12, 21, 71, 101],
                    prices: {
                        "华东": {
                            "美东0.1.2.3": [47, 45, 44, 42],
                            "美中4.5.6.7": [46, 44, 43, 41],
                            "美西8.9": [45, 43, 42, 40],
                            "美西96-99": [47, 45, 44, 42]
                        },
                        "华南": {
                            "美东0.1.2.3": [46, 44, 43, 41],
                            "美中4.5.6.7": [45, 43, 42, 40],
                            "美西8.9": [44, 42, 41, 39],
                            "美西96-99": [46, 44, 43, 41]
                        }
                    }
                }
            }
        },
        "华威尔": {
            // 可选：承运商级默认（作为子渠道未配置项的继承来源）
            weightBreaks: [10, 21, 71, 101],
            zipGroups: [
                { label: "美西7.8.9", prefixes: ["7", "8", "9"] },
                { label: "美东0.1.2.3.4.5.6", prefixes: ["0", "1", "2", "3", "4", "5", "6"] }
            ],
            channels: {
                // 与页面渠道下拉一致（示例：美森正班）
                "空派不带电": {
                    // 子渠道可覆盖断点/分组
                    // weightBreaks: [12, 21, 45, 71, 101],
                    // zipGroups: [...],
                    prices: {
                        "华南": {
                            "美西7.8.9": [42,40,38,36],
                            "美东0.1.2.3.4.5.6": [45,43,41,39]
                        }
                    }
                },
                "空派带电": {
                    // 子渠道可覆盖断点/分组
                    // weightBreaks: [12, 21, 45, 71, 101],
                    // zipGroups: [...],
                    prices: {
                        "华南": {
                            "美西7.8.9": [46, 43, 40, 38],
                            "美东0.1.2.3.4.5.6": [50.5, 47.5, 44.5, 41.5]
                        }
                    }
                }
            },
        },
        "腾信": {
            // 可选：承运商级默认（作为子渠道未配置项的继承来源）
            weightBreaks: [21, 100],
            zipGroups: [
                { label: "美西8.9", prefixes: ["8", "9"] },
                { label: "美中4.5.6.7", prefixes: ["4", "5", "6", "7"] },
                { label: "美东0.1.2.3", prefixes: ["0", "1", "2", "3"] }
            ],
            channels: {
                // 与页面渠道下拉一致（示例：美森正班）
                "普船": {
                    prices: {
                        "华东": {
                            "美西8.9": [10.5, 8.0],
                            "美中4.5.6.7": [11.8, 9.3],
                            "美东0.1.2.3": [12.8, 10.3]
                        },
                        "华南": {
                            "美西8.9": [10.5, 8.0],
                            "美中4.5.6.7": [11.8, 9.3],
                            "美东0.1.2.3": [12.8, 10.3]
                        }
                    }
                },
                "以星合德": {
                    prices: {
                        "华东": {
                            "美西8.9": [12.2, 9.7],
                            "美中4.5.6.7": [13.7, 11.2],
                            "美东0.1.2.3": [14.7, 12.2]
                        },
                        "华南": {
                            "美西8.9": [11.6, 9.1],
                            "美中4.5.6.7": [13.1, 10.6],
                            "美东0.1.2.3": [14.1, 11.6]
                        }
                    }
                },
                "美森加班": {
                    prices: {
                        "华东": {
                            "美西8.9": [15.3, 12.8],
                            "美中4.5.6.7": [16.8, 14.3],
                            "美东0.1.2.3": [17.8, 15.3]
                        },
                        "华南": {
                            "美西8.9": [15.8, 13.3],
                            "美中4.5.6.7": [17.3, 14.8],
                            "美东0.1.2.3": [18.3, 15.8]
                        }
                    }
                },
                "美森正班": {
                    prices: {
                        "华东": {
                            "美西8.9": [15.6, 13.1],
                            "美中4.5.6.7": [17.1, 14.6],
                            "美东0.1.2.3": [18.1, 15.6]
                        },
                        "华南": {
                            "美西8.9": [16.1, 13.6],
                            "美中4.5.6.7": [17.6, 15.1],
                            "美东0.1.2.3": [18.6, 16.1]
                        }
                    }
                }
            }
        }
    },
    pickupFee: {
        "深圳仓": {
            // 起始地配置
            pickupLocations: {
                "深圳-龙岗": [
                    { vehicle: "微面", fee: 150 },
                    { vehicle: "小面", fee: 250 },
                    { vehicle: "中面", fee: 280 },
                    { vehicle: "微货", fee: 260 },
                    { vehicle: "小厢货", fee: 420 },
                    { vehicle: "3米8", fee: 360 },
                    { vehicle: "4米2", fee: 480 },
                    { vehicle: "5米2", fee: 500 },
                    { vehicle: "6米8", fee: 600 },
                    { vehicle: "7米6", fee: 750 },
                    { vehicle: "9米6", fee: 900 },
                    { vehicle: "13米", fee: 1500 },
                    { vehicle: "17米5", fee: 1700 }
                ],
                "东莞": [
                    { vehicle: "微面", fee: 180 },
                    { vehicle: "小面", fee: 240 },
                    { vehicle: "中面", fee: 280 },
                    { vehicle: "微货", fee: 280 },
                    { vehicle: "小厢货", fee: 350 },
                    { vehicle: "3米8", fee: 420 },
                    { vehicle: "4米2", fee: 500 },
                    { vehicle: "5米2", fee: 580 },
                    { vehicle: "6米8", fee: 750 },
                    { vehicle: "7米6", fee: 800 },
                    { vehicle: "9米6", fee: 1000 },
                    { vehicle: "13米", fee: 1700 },
                    { vehicle: "17米5", fee: 1900 }
                ]
            }
        },
		"义乌仓": {
            pickupLocations: {
                "宁波": [
                    { vehicle: "微面", fee: 400 },
                    { vehicle: "小面", fee: 550 },
                    { vehicle: "中面", fee: 640 },
                    { vehicle: "微货", fee: 640 },
                    { vehicle: "小厢货", fee: 720 },
                    { vehicle: "3米8", fee: 700 },
                    { vehicle: "4米2", fee: 1000 },
                    { vehicle: "5米2", fee: 1100 },
                    { vehicle: "6米8", fee: 1250 },
                    { vehicle: "7米6", fee: 1500 },
                    { vehicle: "9米6", fee: 1800 },
                    { vehicle: "13米", fee: 2500 },
                    { vehicle: "17米5", fee: 3200 }
                ]
            }
        }
    },
    // 快捷回复数组
    quickReplies: [
        {
            category: "物流",
            replies: [
                { chinese: "卫星仓不建议快递派，有拒收风险。", english: "AWD warehouse not suggest ship by express, There is a risk of rejection." },
                { chinese: "支付方式", english: "You could make payment to us by Bank transfer, Paypal, Payoneer and alibaba link. " },
                {
                    chinese: "如因节假日、码头塞港、罢工、天气、海关查验等不可抗拒因素导致延误不做任何赔偿",
                    english: "Due to force majeure factors such as holidays, port congestion, strikes, weather conditions, and customs inspections, no compensation will be made for any delays."
                },
                {
                    chinese: "英国标准托盘尺寸：120cm*100cm*180cm, 欧盟标准托盘：120cm*80cm*180cm",
                    english: "UK Standard pallet size: 120cm*100cm*180cm, European Standard pallet size: 120cm*80cm*180cm"
                }  
            ]
        },
        {
            category: "产品",
            replies: [
                { chinese: "请确认产品无牌不侵权", english: "Please confirm that the product is not infringing."},
                { chinese: "不带电带磁", english: "Without battery, without magnet."},
                { chinese: "带电带磁", english: "With battery or magnet."},
                { chinese: "木制品需提供商检报告，原木制品还需提供熏蒸报告", english: "For Wooden products, pls provide the commodity inspection report. For raw wooden products, fumigation report is also needed." },
                { chinese: "带电请提供MSDS，运输鉴定报告，锂电池还需要提供UN38.3", english: "For battery goods, please provide MSDS and transport report. For lithium batteries, UN38.3 is also needed." },
                { chinese: "儿童产品请提供CPC", english: "For children's products, please provide CPC." }

            ]
        },
        {
            category: "地址",
            replies: [
                { chinese: "纽酷美国仓库地址", english: "【美西】 10889 Tamarind Ave, Fontana, CA 92337 \n 【奥克兰】 757 E 11th St, Tracy, CA 95376 \n 【西雅图】 21846 76th Ave S, Kent, WA 98032 \n 【芝加哥】 16675 W. Prologis Parkway, Lockport, IL 60441 \n 【萨凡纳】 774 King George Blvd, Savannah, GA 31419 \n 【休斯顿】 611 S Cravens Rd #200, Missouri City, TX 77489 \n 【新泽西】 1130 State St, Perth Amboy, NJ 08861" }
            ]
        },
        {
            category: "快速查询",
            replies: [
                {
                    chinese: "美国海派不走地址",
                    english: "波多黎各、维尔京群岛: 006-009" 
                    + "\n" + "夏威夷、关岛：966-969" 
                    + "\n" + "阿拉斯加：995-999" 
                    + "\n" + "军方地址" 
                },
                { chinese: "加拿大邮编查询", english: "温哥华：V开头邮编" + "\n" + "卡尔加里：T/S开头邮编" + "\n" + "多伦多：R/L/N/M/P开头邮编" + "\n" + "渥太华/蒙特利尔: K/H/J/G/E/B/A/C/Y/X开头邮编" }
            ]
        },
        {
            category: "轨迹",
            replies: [
                // 海运
                { 
                    chinese: "货物已装柜，等待国内报关", 
                    english: "The goods have been loaded into the container and is ready for domestic customs declaration."
                },
                { 
                    chinese: "国内报关已完成，等待放行", 
                    english: "The goods have been declared by domestic customs and is waiting for release."
                },
                { 
                    chinese: "国内清关已完成，等待运输", 
                    english: "The goods have been cleared by domestic customs and is ready for shipment."
                },
                { 
                    chinese: "已到港，等待卸船", 
                    english: "Arrived at port, waiting for unloading."
                },
                { 
                    chinese: "已卸船，等待预约提柜", 
                    english: "The ship has been unloaded, waiting for an appointment to pick up the container."
                },
                { 
                    chinese: "已提柜，等待拆柜", 
                    english: "The container has been picked up, waiting for unpacking."
                },
                
                // ---
                { 
                    chinese: "已交付UPS/Fedex，请留意官网更新", 
                    english: "Has been handed over to UPS/Fedex, please pay attention to the official website update."
                }
            ]
        }
    ],

    // 地址和邮编的映射关系
    addressByCountry: {
        "美国": {
            "ONT8": "92551",
            "SBD1": "92316",
            "LGB8": "92376",
            "LAX9": "92337",

            "JOT1": "92408",
            "XLX2": "92571",
            "XLX7": "92394",
            "ONT2": "92408",
            "ONT6": "92551",
            "ONT7": "92374",
            "ONT9": "92374",
            "SNA4": "92376",
            "QXY9": "92223",
            "KRB1": "92408",
            "POC1": "92336",
            "POC2": "91761",
            "POC3": "92509",
            "XLG1": "92374",
            "FAT1": "93725",
            "FAT2": "93291",
            "MIT2": "93263",
            "TCY1": "95206",
            "SMF1": "95835",
            "SMF3": "95206",
            "SMF6": "95837",
            "SMF7": "95688",
            "OAK3": "95363",
            "OAK4": "95304",
            "MCE1": "95380",
            "MCC1": "95742",
            "HLI2": "95023",
            "SJC7": "95377",
            "SJC8": "94538",
            "PDX7": "97317",
            "PDX6": "97203",
            "PDX9": "97060",
            "BFI1": "98390",
            "BFI3": "98327",
            "BFI4": "98032",
            "TCY2": "95215", /* 偏远 */
            "SCK1": "95215", /* 偏远 */
            "SCK4": "95215", /* 偏远 */
            "SCK8": "94561", /* 偏远 */

            "GEG2": "99216",
            "GEG1": "99224",
            "PSC2": "99301",

            "VGT2": "89115",
            "GEU5": "85395",
            "GEU3": "85396", /* 偏远 */
            "GEU2": "85307",
            "GYR1": "85338",
            "GYR2": "85395",
            "GYR3": "85043",
            "PHX1": "85340",
            "PHX3": "85043",
            "PHX5": "85338",
            "PHX6": "85043",
            "PHX7": "85043",
            "SLC3": "84116",
            "SLC2": "84081",
            "SLC1": "84116",
            "DEN2": "80019",
            "DEN8": "80018",
            "LAS6": "89115",
            "LAS1": "89044", /* 偏远 */
            "ABQ2": "87031", /* 偏远 */

            "SAT1": "78154",
            "SAT2": "78666",
            "SAT4": "78245",
            "SAT6": "78666",
            "HOU8": "77545",
            "HOU2": "77038",
            "IAH3": "77032",
            "FTW1": "75241",
            "FTW4": "76177",
            "FTW8": "75241",
            "DFW6": "75019",
            "DFW8": "75261",
            "OKC1": "73159",
            "OKC2": "73159",
            "LIT2": "72117",
            "LFT1": "70520",
            "FTW5": "75126", /* 偏远 */
            "AMA1": "79108", /* 偏远 */

            "ICT2": "67219",
            "MKC6": "66102",
            "MKC4": "66021",
            "FOE1": "66109",
            "MCI3": "64068",
            "STL3": "65738",
            "STL4": "62025",
            "STL6": "62025",
            "STL8": "63376",
            "IGQ2": "60484",
            "RFD2": "60142",
            "RFD4": "60142",
            "ORD2": "60410",
            "MDW2": "60433",
            "MDW4": "60433",
            "MDW6": "60446",
            "MDW7": "60449",
            "MDW8": "60085",
            "MDW9": "60502",


            "JVL1": "53511",
            "MKE1": "53144",
            "MKE2": "53154",

            "DET2": "48317",
            "DET1": "48150",
            "LAN2": "48917",
            "FWA4": "46809",
            "IND9": "46143",
            "PPO4": "46410",
            "MQJ1": "46140",
            "MQJ2": "46184",
            "CMH3": "45050",
            "AKR1": "44705",
            "AKC1": "44320",
            "SDF1": "42718", /* 偏远 */
            "SDF4": "40165", /* 偏远 */

            "MEM1": "38118",
            "MEM2": "38611",
            "MEM4": "38128",
            "MEM6": "38654",
            "MEM8": "38611",
            "CHA1": "37416",
            "BNA2": "37090",
            "BNA6": "37040",
            "PBI3": "34986",
            "TMB8": "33032",
            "MIA1": "33054", 
            "TPA1": "33570",
            "TPA2": "33811",
            "TPA3": "33823",
            "TPA6": "34475",
            "MCO1": "32824",
            "MCO2": "32725",
            "JAX3": "32210",
            "SAV3": "31216",
            "MGE1": "30517",
            "ATL3": "30567",
            "ATL2": "30087",
            "CHA2": "37310", /* 偏远 */
            "HSV1": "35756", /* 偏远 */
            "HSV2": "35756", /* 偏远 */
            "MGE3": "30549", /* 偏远 */
            "RYY2": "30184", /* 偏远 */

            "RDU2": "27577",
            "RDU4": "28303",
            "XLX6": "28134",
            "CLT2": "28214",
            "CLT6": "28134",
            "GSO1": "27284",
            "ORF2": "23321",
            "XRI3": "23234",
            "XLX1": "21740",
            "HGR2": "21740",
            "HGR6": "21740",
            "RIC1": "23803",
            "RIC2": "23836",
            "RIC3": "23234",
            "RMN3": "22406",
            "CHO1": "22939",
            "DCA6": "21219",
            "BWI1": "20166",
            "BWI2": "21224",
            "BWI4": "22624",

            "PHL1": "19720",
            "PHL2": "18015",
            "PHL3": "19720",
            "PHL4": "17015",
            "PHL5": "17339",
            "PHL6": "17015",
            "PHL7": "19709",
            "PHL8": "19709",
            "ILG1": "19720",
            "ABE4": "18045",
            "AVP1": "18202",
            "HEA2": "18031",
            "MDT1": "17015",
            "MDT4": "17408",
            "HIA1": "17057",
            "LBE1": "15672",
            "PIT1": "15205",
            "PIT2": "15126", /* 偏远 */
            "ALB1": "12033", /* 偏远 */
            "WBW2": "18447", /* 偏远 */
            "SWF2": "12533", /* 偏远 */
            "SWF1": "12575", /* 偏远 */

            "TEB3": "08085",
            "TEB4": "08069",
            "TEB6": "08512",
            "TEB9": "08873",
            "ABE8": "08518",
            "ACY2": "08016",
            "EWR9": "07008",
            "BOS1": "03063",
            "BOS6": "02150",
            "BOS7": "02720",
            "XEW5": "08077",
            "XPB2": "32712",

            "IUSP": "92344",
            "IUSQ": "92374",
            "IUSJ": "92223",
            "IUSF": "75241",
            "IUSM": "60563",
            "IUTI": "92374",
            "IUTH": "78666",
            "IUSW": "92344",/* 偏远 */
            "IUTE": "85338",
            "IUSR": "29330", /* 偏远 */
            "IUSL": "21901", /* 偏远 */
            "IUST": "17225", /* 偏远 */

            /* 沃尔玛 */
            "DFW2n": "76177",
            "ATL1": "30349", /* 偏远 */
            "ATL3": "30567", /* 偏远 */
            "MCI1n": "66619",
            "DFW5S": "75146",
            "LAX2T": "91708",
        },
        "加拿大": {
            "YYZ1": "L5N1L8",
            "YYZ2": "L9T0K1",
            "YYZ3": "L6Y5Z4",
            "YYZ4": "L6Y6L5",
            "YYZ7": "L7E4L8",
            "YYZ9": "M1X1N5",
            "YOO1": "L1Z0J2",
            "YHM1": "L0R1W1",
            "YEG1": "T9E0B4",
            "YEG2": "T7X2X2",
            "YOW1": "K4B0L3",
            "YOW3": "K2J7C7",
            "YVR2": "V3M5Y9",
            "YVR3": "V3L5H4",
            "YVR4": "V4M0B9",
            "YYC1": "T4A1C6",
            "YYC4": "T2C5X1",
            "YYC6": "T2C5V8",
            "YXX2": "V6W0C6",
            "YXU1": "N5P0G9",
            "YGK1": "K8N0V2"
        },
        "英国": {
            /* 英国 */
            "BHX2": "LE67 1FB",
            "BHX3": "NN11 8PQ",
            "BHX4": "CV5 9PF",
            "BHX5": "CV23 0XF",
            "BHX7": "LE10 3FF",
            "BHX8": "B98 9AY",
            "BRS1": "BS35 4DJ",
            "BRS2": "SN3 4DB",
            "CWL1": "SA1 8QX",
            "DAILI": "UB2 5FB",
            "DSA6": "LS26 9FT",
            "DSA7": "WF11 0AB",
            "EDI4": "KY11 8ST",
            "EMA1": "DE74 2BB",
            "EMA2": "NG17 5NB",
            "EMA3": "NG16 3UA",
            "EUK5": "PE2 9EN",
            "GLA1": "PA19 1BQ",
            "LBA1": "DN4 5JS",
            "LBA2": "DN11 0BG",
            "LBA4": "DN11 0GU",
            "LBA5": "LS9 0PS",
            "LCY2": "RM18 7AN",
            "LCY3": "DA1 5XU",
            "LPL2": "L33 7AP",
            "LTN1": "MK43 0ZA",
            "LTN2": "HP27 0LF",
            "LTN4": "LU5 4FE",
            "LTN7": "MK43 9JH",
            "LTN9": "LU5 4FE",
            "MAN1": "M90 5AA",
            "MAN2": "WA5 3XA",
            "MAN3": "BL5 1EE",
            "MAN4": "S43 4PZ",
            "MME1": "DL1 4BF",
            "MME2": "DH6 5NP",
            "NCL1": "NE10 8YA",
            "XBH1": "NN11 8QL",
            "XBH2": "CV23 0WB",
            "XBH3": "LE3 8JT",
            "XBH4": "WV10 7GW",
            "XBH5": "LE17 4XY",
            "XBH7": "IP32 7FQ",
            "XDS1": "DN3 3EA",
            "XLP1": "CH5 2LL",
            "XLT1": "PE2 6UG",
            "XLT2": "PE2 6TE",
            "XPL1": "WA8 8WJ",
            "XUKS": "DE74 2BB",
            "EMA4": "B76 9AH",
            "NCL2": "TS22 5TH",
            "XUKA": "WA7 3BN",
            "LBA8": "LS15 0BF"
        },
        "欧洲": {
            /* 德国 */
            "DTM2": "44145",
            "HAJ1": "38350",
            "BER3": "14656",
            "BER8": "12529",
            "BER6": "13507",
            "CGN1": "56330",
            "DTM1": "59368",
            "DTM9": "58454",
            "DUS2": "47495",
            "EDEA": "44145",
            "DTM3": "44145",
            "FRA3": "36251",
            "HAM2": "21423",
            "LEJ1": "04347",
            "LEJ3": "39171",
            "LEJ5": "07554",
            "KSF7": "34466",
            "KTW5": "04758",
            "RLG1": "18196",
            "STR1": "75177",
            "STR2": "89522",
            "WRO1": "04758",
            "XWR3": "04758",
            "WRO2": "06126",
            "WRO5": "06126",
            "XDU1": "34323",
            "XFR4": "31629",
            "XDU2": "46147",
            "XSC1": "67661",
            "SCN2": "67661",
            "BRE4": "28832",
            "XPO1": "04758",
            "XDEA": "15713",
            "XDEV": "37081",
            "MHG9": "63801",
            "POZ1": "06126",
            "LCJ2": "04758",

            /* 法国 */
            "BVA1": "80337",
            "BVA1-80440": "80440",
            "CDFR": "33610",
            "CDG7": "60300",
            "CDG7-": "60452",
            "ETZ2": "57685",
            "LIL1": "59553",
            "LIL1-1": "59553",
            "LYS1": "71100",
            "LYS1-71311": "71311",
            "MRS1": "26200",
            "MRS1-26132": "26132",
            "ORY1": "45772",
            "ORY1-45770": "45770",
            "ORY4": "91220",
            "ORY4-91225": "91225",
            "VESK": "77176",
            "XFRG": "45410",
            "XOR1": "91090",
            "XOR2": "38290",
            "XOS1": "62117",

            /* 西班牙 */
            "BCN1": "08820",
            "BCN2": "08107",
            "MAD4": "28830",
            "MAD6": "45200",
            "MAD9": "28804",
            "PESG": "45200",
            "SVQ1": "41703",
            "XESA": "19208",
            "XESB": "19208",

            /* 意大利 */
            "BGY1": "24050",
            "BLQ1": "45020",
            "FCO1": "02032",
            "FCO2": "00034",
            "MXP3": "13100",
            "MXP5": "29015",
            "MXP6": "28100",
            "TRN1": "10037",
            "XITC": "20080",
            "XITF": "29100",
            "XMP1": "45031",
            "XMP2": "20080"
        },
        "澳大利亚": {
            /* 澳大利亚 */
            "BWU1": "2170",
            "BWU2": "2178",
            "VANE": "2178",
            "BWU6": "2175",
            "XAU2": "2142",
            "MEL1": "3175",
            "XAU1": "3043",
            "MEL5": "3023",
            "AVV2": "3977",
            "BNE1": "4178",
            "PER2": "6105",
            "PER3": "6105",
            "PER4": "6164"
        }
    },

    // 偏远地区邮编列表
    remotePostcodes: [
        "89044", "60421", "46231", "66021", "67337",
        "40165", "42718", "21901", "89408", "18424", "18707", 
        "17257", "19530", "37090", "37090", "37310", "77423", 
        "23803", "53125", "98327", "95215", "15126", "12533",
        "79108", "87031", "18447", "29330", "17225", "94561",
        "30549", "30184", "75126", "92344", "30567", "85396",
        "35756", "80018"
    ],

    // 派送方式按国家分类
    deliveryMethodsByCountry: {
        "美国": ["Sea truck", "Sea express", "Air express", "Fast sea express", "Fast Maston express", "Super sea express",
            "Fast sea truck", "Fast Maston truck", "Normal sea express", "Normal Maston express", "Normal Maston truck","Normal sea truck","Express", "Sea ups/fedex", 
            "Fast sea ups/fedex", "Air ups/fedex","UPS/Fedex/DHL"
        ],
        "加拿大": ["Sea truck", "Sea express", "Air express", "Fast sea express", "Fast Maston express", "Super sea express",
            "Fast sea truck", "Fast Maston truck", "Normal sea express", "Normal Maston express", "Normal Maston truck","Normal sea truck", "Express"
        ],
        "欧洲": ["Sea truck", "Sea express", "Air truck", "Air express", "Train express", "Train truck", "Road express","Road truck","Express"],
        "英国": ["Sea truck", "Sea express", "Air truck", "Air express", "Train express", "Train truck", "Road express","Road truck","Express"],
        "澳大利亚": ["Sea truck", "Sea express"],
        "其他": ["Express"]
    },

    // 渠道名称中英文映射
    channelNames: {
        'Sea express': '普船快递派',
        'Fast sea express': '快船快递派',
        'Fast Maston express': '美森快递派',
        'Fast Maston truck': '美森卡派',
        'Fast sea truck': '快船卡派', 
        'Normal sea express': '加班快递派', 
        'Normal Maston express': '加班快递派', 
        'Normal Maston truck': '加班卡派', 
        'Normal sea truck': '加班卡派', 
        'Air express': '空派',
        'Air truck': '空卡',
        'UPS/Fedex/DHL': 'UPS/Fedex/DHL',
        'Train express': '铁路快递派',
        'Train truck': '铁路卡派',
        'Road express': '卡航快递派',
        'Road truck': '卡航卡派',
        // 默认值
        '_default': '普船卡派'
    }
};



const transitTimeData = {
    "美国": {
        "Sea truck": {
            "0-4": "40-50",
            "5-7": "35-40",
            "8-9": "30-35"
        },
        "Sea express": {
            "default": "30-35"
        },
        "Sea ups/fedex": {
            "default": "30-35"
        },
        "Air express": {
            "default": "8-12"
        },
        "Air ups/fedex": {
            "default": "8-12"
        },
        "Fast sea express": {
            "0-3": "20-25",
            "4-7": "18-22",
            "8-9": "15-20"
        },
        "Fast Maston express": {
            "0-3": "20-25",
            "4-7": "18-22",
            "8-9": "16-20"
        },
        "Super sea express": {
            "0-3": "20-25",
            "4-7": "18-22",
            "8-9": "16-20"
        },
        "Fast sea ups/fedex": {
            "0-3": "20-25",
            "4-7": "18-22",
            "8-9": "16-20"
        },
        "Normal sea express": {
            "0-3": "21-26",
            "4-7": "19-23",
            "8-9": "17-22"
        },
        "Normal Maston express": {
            "0-3": "21-26",
            "4-7": "19-23",
            "8-9": "17-21"
        },
        "Fast sea truck": {
            "0-3": "25-28",
            "4-7": "20-24",
            "8-9": "18-22"
        },
        "Fast Maston truck": {
            "0-3": "25-28",
            "4-7": "20-24",
            "8-9": "18-22" 
        },
        "Express": {
            "default": "6-8"
        }
    },
    "加拿大": {
        "Sea truck": {
            "default": "35-45"
        },
        "Sea express": {
            "default": "32-38"
        },
        "Fast Maston truck": {
            "default": "22-28"
        },
        "Fast sea truck": {
            "default": "22-28"
        },
        "Fast Maston express": {
            "default": "20-28"
        },
        "Fast sea express": {
            "default": "20-28"
        },
        "Super sea express": {
            "default": "20-28"
        },
        "Air express": {
            "default": "10-15"
        }
    },
    "欧洲": {
        "Sea truck": {
            "default": "50-55"
        },
        "Sea express": {
            "default": "45-50"
        },
        "Train truck": {
            "default": "28-38"
        },
        "Train express": {
            "default": "28-38"
        },
        "Road truck": {
            "default": "22-28"
        },
        "Road express": {
            "default": "22-28"
        },
        "Air express": {
            "default": "8-12"
        },
        "Express": {
            "default": "5-8"
        }
    },
    "英国": {
        "Sea truck": {
            "default": "45-55"
        },
        "Sea express": {
            "default": "40-50"
        },
        "Train truck": {
            "default": "30-40"
        },
        "Train express": {
            "default": "30-38"
        },
        "Road truck": {
            "default": "24-28"
        },
        "Road express": {
            "default": "23-27"
        },
        "Air express": {
            "default": "8-12"
        },
        "Express": {
            "default": "5-8"
        }
    },
    "澳大利亚": {
        "Sea truck": {
            "default": "30-35"
        },
        "Sea express": {
            "default": "30-35"
        }
    }
};

const tagColors = {
    "基础": "#007bff",
    "物流": "#28a745",
    "美国": "#1b1b71",
    "欧洲": "#ffcc02",
    "加拿大": "#fe0000",
    "澳新线": "#01226f", // 黄色
    "港口": "#17a2b8", // 青色
    "税务": "#6610f2", // 紫色
    "保险": "#fd7e14", // 橙色
    "产品": "#e83e8c", // 粉色
    "航线": "#20c997"  // 青绿色
};


const boxRules = {
    "美国": {
        "UPS": {
            maxWeight: 22, // 单件最大重量
            maxLength: 120, // 最长边
            maxSecondLength: 75, // 第二长边
            maxPerimeter: 260, // 最大围长
            rejectWeight: 29, // 拒收重量
            rejectLength: 243, // 拒收最长边
            rejectPerimeter: 320 // 拒收围长
        },
        "FEDEX": {
            maxWeight: 22,
            maxLength: 120,
            maxSecondLength: 75,
            maxPerimeter: 260,
            rejectWeight: 29,
            rejectLength: 243,
            rejectPerimeter: 320
        }
    },
    "加拿大": {
        "UPS": {
            maxWeight: 22,
            maxLength: 120,
            maxSecondLength: 75,
            maxPerimeter: 260,
            rejectWeight: 29,
            rejectLength: 243,
            rejectPerimeter: 320
        },
        "FEDEX": {
            maxWeight: 22,
            maxLength: 120,
            maxSecondLength: 75,
            maxPerimeter: 260,
            rejectWeight: 29,
            rejectLength: 243,
            rejectPerimeter: 320
        }
    },
    "欧洲": {
        "UPS": {
            maxWeight: 25,
            maxLength: 100,
            maxSecondLength: 75,
            maxPerimeter: 300,
            maxDimensionWeight: 25,
            rejectWeight: 30,
            rejectLength: 160,
            rejectPerimeter: 390,
            rejectDimensionWeight: 35
        },
        "CWE": {
            maxWeight: 30,
            maxLength: 100,
            maxSecondLength: 75,
            maxPerimeter: 300,
            maxDimensionWeight: 30,
            rejectWeight: 30,
            rejectLength: 120,
            rejectSecondLength: 80,
            rejectDimensionWeight: 30
        },
        "GLS": {
            maxWeight: 30,
            maxLength: 110,
            maxSecondLength: 70,
            maxDimensionWeight: 25,
            rejectWeight: 40,
            rejectLength: 160,
            rejectPerimeter: 300
        }
    },
    "英国": {
        "DPD": {
            maxWeight: 30,
            maxLength: 100,
            maxSecondLength: 70,
            maxThirdLength: 60,
            maxPerimeter: 260,
            maxDimensionWeight: 25,
            rejectWeight: 29,
            rejectLength: 160,
            rejectPerimeter: 230,
            rejectDimensionWeight: 35
        }
    }
};


// 特定地址的运输天数映射配置
const specificAddressTransitTime = {
    "ONT8": { "Sea truck": "25-30"},
    "LGB8": { "Sea truck": "25-30"},
    "SBD1": { "Sea truck": "25-30"},
    "LAX9": { "Sea truck": "25-30"},
    // 芝加哥
    "IND9": { "Sea truck": "38-45"},
    "FWA4": { "Sea truck": "38-45"},
    "MQJ1": { "Sea truck": "38-45"},
    "PPO4": { "Sea truck": "38-45"},

    // 休斯顿
    "IAH3": { "Sea truck": "38-45"},
    "FTW1": { "Sea truck": "38-45"},
    "SAT1": { "Sea truck": "38-45"},
    "SAT4": { "Sea truck": "38-45"},
    "MEM1": { "Sea truck": "38-45"},
    "MEM6": { "Sea truck": "38-45"},
    "DFW6": { "Sea truck": "38-45"},
    "HOU8": { "Sea truck": "38-45"},
    "IUSF": { "Sea truck": "38-45"},

    // 美东
    "ABE8": { "Sea truck": "40-45"},
    "TEB9": { "Sea truck": "40-45"},
    "XEW5": { "Sea truck": "40-45"},
    "ACY2": { "Sea truck": "40-45"}
};


