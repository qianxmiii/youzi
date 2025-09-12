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
    {name: "气球", hscode: "9505906000", taxrate: "0" },
    {name: "装饰板", hscode: "3926400010", taxrate: "5.3" },
    {name: "大豆蜡", hscode: "3406000000", taxrate: "7.5" },
    {name: "橡胶手套", hscode: "3926201050", taxrate: "0" },
    {name: "游戏卡牌", hscode: "9504904000", taxrate: "0" }
];

// 将数组数据挂载到 window 对象上
window.data = {
    vehicleTypes: vehicleTypes,
    deliveryLocations: deliveryLocations,
    cargoTypes: cargoTypes,
    commonProducts: commonProducts,
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
                    { vehicle: "微面", fee: 320 },
                    { vehicle: "小面", fee: 400 },
                    { vehicle: "中面", fee: 420 },
                    { vehicle: "微货", fee: 450 },
                    { vehicle: "小厢货", fee: 550 },
                    { vehicle: "3米8", fee: 700 },
                    { vehicle: "4米2", fee: 850 },
                    { vehicle: "5米2", fee: 950 },
                    { vehicle: "6米8", fee: 1150 },
                    { vehicle: "7米6", fee: 1300 },
                    { vehicle: "9米6", fee: 1400 },
                    { vehicle: "13米", fee: 2200 },
                    { vehicle: "17米5", fee: 2800 }
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


