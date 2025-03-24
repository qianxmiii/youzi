// data.js
const shippingChannels = {
    "卡派": [
      "Sea truck", 
      "Fast sea truck", 
      "Fast Maston truck",
      "Super Maston truck",
      "Normal Maston truck",
      "Normal sea truck"
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
      "Truck express"
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

// 将数组数据挂载到 window 对象上
window.data = {
    vehicleTypes: vehicleTypes,
    deliveryLocations: deliveryLocations,
    cargoTypes: cargoTypes,
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
                { chinese: "支付方式", english: "You can make payment to us by Bank transfer, Paypal, Payoneer and alibaba link" },
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
                { chinese: "请确认产品无牌不侵权", english: "Please confirm that the product is unlicensed and not infringing."},
                { chinese: "木制品需提供商检报告，原木制品还需提供熏蒸报告", english: "Wooden products the commodity inspection report. For raw wooden products, fumigation report is also required." },
                { chinese: "带电请提供MSDS，运输鉴定报告，锂电池还需要提供UN38.3", english: "If with batteries , please provide MSDS and the Transportation Identification Report.For lithium batteries, the UN38.3 test report is also required." },
                { chinese: "儿童产品请提供CPC和CPSC.", english: "For children's products, please provide CPC." }

            ]
        },
        {
            category: "地址",
            replies: [
                { chinese: "浙江省金华市义乌市稠江街道德贸路2号（2楼37号-38号）启函物流园，余乐（转May），15157953544", english: "Qihan Logistics Park, No. 2 Demao Road, Choujiang Street, Yiwu City, Jinhua City, Zhejiang Province (No. 37-38, 2nd floor platform),  Mr yu, 15157953544" },
                { chinese: "深圳市宝安区福海街道和平社区富桥工业区二区北(加运美旁) 虎哥（转May） 15920082662", english: "Building A4, 1st Floor, Zone 2, Fuqiao Industrial Zone, Fuhai Street, Bao'an District, Shenzhen City, Guangdong Province HuGe 15920082662" }
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

                // 空运
                { 
                    chinese: "已提柜，等待拆柜", 
                    english: "The container has been picked up, waiting for unpacking."
                },
                
                // ---
                { 
                    chinese: "已交付UPS，请留意官网更新", 
                    english: "Has been handed over to UPS, please pay attention to the official website update."
                },
                { 
                    chinese: "已交付Fedex，请留意官网更新", 
                    english: "Has been handed over to Fedex, please pay attention to the official website update."
                },
            ]
        }
    ],

    // 地址和邮编的映射关系
    addressToPostcode: {
        "ONT8": "92551",
        "SBD1": "92316",
        "LGB8": "92376",
        "LAX9": "92337",

        "QXY9": "92223",
        "KRB1": "92408",
        "POC3": "92509",
        "POC1": "92336",
        "XLG1": "92374",
        "FAT1": "93725",
        "FAT2": "93291",
        "MIT2": "93263",
        "SMF6": "95837",
        "SMF3": "95206",
        "OAK3": "95363",
        "MCE1": "95380",
        "PDX7": "97317",
        "BFI1": "98390",
        "BFI3": "98327",
        "SCK4": "95215", /* 偏远 */
        "SCK8": "94561", /* 偏远 */
    
        "GEG2": "99216",
        "GEG1": "99224",
        "PSC2": "99301",
             
        "VGT2": "89115",
        "GEU5": "85395",
        "GEU3": "85396",
        "GEU2": "85307",
        "GYR1": "85338",
        "GYR2": "85395",
        "GYR3": "85043",
        "PHX7": "85043",
        "SLC2": "84081",
        "SLC1": "84116",
        "DEN2": "80019",
        "DEN8": "80018",
        "LAS1": "89044", /* 偏远 */
        "ABQ2": "87031", /* 偏远 */

        "SAT4": "78245",
        "SAT2": "78666",
        "SAT1": "78154",
        "IAH3": "77032",
        "FTW5": "75126",
        "FTW4": "76177",
        "FTW1": "75241",
        "DFW6": "75019",
        "OKC2": "73159",
        "OKC1": "73159",
        "LIT2": "72117",
        "LFT1": "70520",
        "AMA1": "79108", /* 偏远 */

        "ICT2": "67219",
        "FOE1": "66109",
        "MCI3": "64068",
        "STL3": "65738",
        "STL4": "62025",
        "IGQ2": "60484",
        "RFD2": "60142",
        "ORD2": "60410",
        "MDW2": "60433",
        "MDW4": "60433",
        "RFD4": "60142",

        "JVL1": "53511",
        
        "DET2": "48317",
        "DET1": "48150",
        "LAN2": "48917",
        "FWA4": "46809",
        "IND9": "46143",
        "PPO4": "46410",
        "MQJ1": "46140",
        "CMH3": "45050",
        "AKR1": "44705",
        "AKC1": "44320",
        
        "MEM1": "38118",
        "MEM6": "38654",
        "CHA1": "37416",
        "BNA6": "37040",
        "PBI3": "34986",
        "TMB8": "33032",
        "MIA1": "33054",
        "TPA3": "33823",
        "TPA2": "33811",
        "MCO1": "32824",
        "MCO2": "32725",
        "JAX3": "32210",
        "SAV3": "31216",
        "MGE1": "30517",
        "ATL3": "30567",
        "ATL2": "30087",
        "CHA2": "37310", /* 偏远 */
        "HSV1": "35756", /* 偏远 */
        "MGE3": "30549", /* 偏远 */
        "RYY2": "30184", /* 偏远 */
  
        "RDU4": "28303", 
        "CLT2": "28214",
        "GSO1": "27284",
        "ORF2": "23321",
        "XLX1": "21740",
        "RDU2": "27577",
        "HGR6": "21740",  
        "RMN3": "22406",    
        "CHO1": "22939",
        "DCA6": "21219",
        "BWI4": "22624",
        "BWI2": "21224",
        "BWI1": "20166",
        
        "ILG1": "19720",
        "AVP1": "18202",
        "MDT4": "17408",
        "HIA1": "17057",
        "LBE1": "15672",       
        "PIT2": "15126", /* 偏远 */      
        "ALB1": "12033", /* 偏远 */
        "WBW2": "18447", /* 偏远 */
        "SWF2": "12533", /* 偏远 */
        "SWF1": "12575", /* 偏远 */
        
        "TEB9": "08873",
        "ABE8": "08518",
        "ACY2": "08016",
        "BOS1": "03063",
        "BOS6": "02150",
        "BOS7": "02720",
 
        "IUSP": "92344",
        "IUSQ": "92374",
        "IUSJ": "92223",
        "IUSF": "75241",
        "IUSM": "60563",
        "IUSR": "29330", /* 偏远 */
        "IUSL": "21901", /* 偏远 */
        "IUST": "17225", /* 偏远 */

        /* 加拿大 */
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
        "YGK1": "K8N0V2",

        /* 德国 */
        "DTM2": "44145",
        "HAJ1": "38350",
        "BER8": "12529",
        "BER3": "14656",
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
        "MAN1": "M90 5AA",
        "MAN2": "WA5 3XA",
        "MAN3": "BL5 1EE",
        "MAN4": "S43 4PZ",
        "MME1": "DL1 4BF",
        "MME2": "DH6 5NP",
        "NCL1": "NE10 8YA",
        "XBH3": "LE3 8JT",
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
        "LBA8": "LS15 0BF"
    },

    // 偏远地区邮编列表
    remotePostcodes: [
        "89044", "60421", "46231", "66021", "67337", "66021", 
        "40165", "42718", "21901", "89408", "18424", "18707", 
        "17257", "19530", "37090", "37090", "37310", "77423", 
        "23803", "53125", "98327", "95215", "15126", "12533",
        "79108", "87031", "18447", "29330", "17225", "94561"
    ],

    // 派送方式按国家分类
    deliveryMethodsByCountry: {
        "美国": ["Sea truck", "Sea express", "Air express", "Fast sea express", "Fast Maston express", "Super sea express",
            "Fast sea truck", "Fast Maston truck", "Normal sea express", "Normal Maston express", "Express", "Sea ups/fedex", 
            "Fast sea ups/fedex", "Air ups/fedex",
        ],
        "加拿大": ["Sea truck", "Sea express", "Air express", "Fast sea express", "Fast Maston express", "Super sea express",
            "Fast sea truck", "Fast Maston truck", "Normal sea express", "Normal Maston express", "Express"
        ],
        "欧洲": ["Sea truck", "Sea express", "Air express", "Train express", "Train truck", "Truck express","Express"],
        "英国": ["Sea truck", "Sea express", "Air express", "Train express", "Train truck", "Truck express","Express"],
        "其他": ["Express"]
    }   
};

// 价格数据表（支持不同渠道）
const priceTable = {
    "美森正班": {
        "美东0.1.2.3": {
            "华南": [18.8, 16.8, 16.3, 15.3, 14.3],
            "华东": [18.3, 16.3, 15.8, 14.8, 13.8]
        },
        "美中4.5.6.7": {
            "华南": [18.3, 16.3, 15.8, 14.8, 13.8],
            "华东": [17.8, 15.8, 15.3, 14.3, 13.3]
        },
        "美西8.9": {
            "华南": [16.8, 14.8, 14.3, 13.3, 12.3],
            "华东": [16.3, 14.3, 13.8, 12.8, 11.8]
        },
        "美西96-99": {
            "华南": [18.8, 16.8, 16.3, 15.3, 14.3],
            "华东": [18.3, 16.3, 15.8, 14.8, 13.8]
        }
    },
    "美森加班": {
        "美东0.1.2.3": {
            "华南": [18.5, 16.5, 16.0, 15.0, 14.0],
            "华东": [18.0, 16.0, 15.5, 14.5, 13.5]
        },
        "美中4.5.6.7": {
            "华南": [18.0, 16.0, 15.5, 14.5, 13.5],
            "华东": [17.5, 15.5, 15.0, 14.0, 13.0]
        },
        "美西8.9": {
            "华南": [16.5, 14.5, 14.0, 13.0, 12.0],
            "华东": [16.0, 14.0, 13.5, 12.5, 11.5]
        },
        "美西96-99": {
            "华南": [18.5, 16.5, 16.0, 15.0, 14.0],
            "华东": [18.0, 16.0, 15.5, 14.5, 13.5]
        }
    },
    "普船": {
        "美东0.1.2.3": {
            "华南": [14.4, 13.4, 11.9, 10.4, 9.9],
            "华东": [14.4, 13.4, 11.9, 10.4, 9.9]
        },
        "美中4.5.6.7": {
            "华南": [13.9, 12.9, 11.4, 9.9, 9.4],
            "华东": [13.9, 12.9, 11.4, 9.9, 9.4]
        },
        "美西8.9": {
            "华南": [12.4, 11.4, 9.9, 8.4, 7.9],
            "华东": [12.4, 11.4, 9.9, 8.4, 7.9]
        },
        "美西96-99": {
            "华南": [14.4, 13.4, 11.9, 10.4, 9.9],
            "华东": [14.4, 13.4, 11.9, 10.4, 9.9]
        }
    },
    "空派不带电": {
        "美东0.1.2.3": {
            "华南": [44, 42, 42, 41, 39],
            "华东": [45, 43, 43, 42, 40]
        }, 
        "美中4.5.6.7": { 
            "华南": [43, 41, 41, 40, 38],
            "华东": [44, 42, 42, 41, 39]
        }, 
        "美西8.9": { 
            "华南": [42, 40, 40, 39, 37],
            "华东": [43, 41, 41, 40, 38]
        }, 
        "美西96-99": { 
            "华南": [44, 42, 42, 41, 39],
            "华东": [45, 43, 43, 42, 40]
        }
    },
    "空派带电": {
        "美东0.1.2.3": {
            "华南": [46, 44, 44, 43, 41],
            "华东": [46, 44, 44, 43, 41]
        },
        "美中4.5.6.7": {
            "华南": [45, 43, 43, 42, 40],
            "华东": [45, 43, 43, 42, 40]
        },
        "美西8.9": {
            "华南": [44, 42, 42, 41, 39],
            "华东": [44, 42, 42, 41, 39]
        },
        "美西96-99": {
            "华南": [46, 44, 44, 43, 41],
            "华东": [46, 44, 44, 43, 41]
        }
    },
    "美森正班-偏远": {
        "美东0.1.2.3": {
            "华南": [17.8, 17.8, 17.8, 17.8, 15.3],
            "华东": [17.3, 17.3, 17.3, 17.3, 14.8]
        },
        "美中4.5.6.7": {
            "华南": [16.8, 16.8, 16.8, 16.8, 14.3],
            "华东": [16.3, 16.3, 16.3, 16.3, 13.8]
        },
        "美西8.9": {
            "华南": [15.3, 15.3, 15.3, 15.3, 12.8],
            "华东": [14.8, 14.8, 14.8, 14.8, 12.3]
        },
        "美西96-99": {
            "华南": [15.3, 15.3, 15.3, 15.3, 12.8],
            "华东": [14.8, 14.8, 14.8, 14.8, 12.3]
        }
    },
};

const termsByCategory = {
    "物流类": [
        { chinese: "货运代理", english: "freight forwarder", definition: "受托处理货物运输的代理人，负责安排运输及相关服务", tags: ["基础", "物流"]},
        { chinese: "报价", english: "quotation", definition: "卖方根据买方需求提供的价格信息", tags: ["基础", "物流"]},
        { chinese: "发货人", english: "SHPR/Shipper", definition: "货物的实际出口方或安排货物出口的一方", tags: ["基础", "物流"]},
        { chinese: "收货人", english: "CNEE/Consignee", definition: "货物的实际进口方或安排货物进口的一方", tags: ["基础", "物流"]},
        { chinese: "收货人", english: "NTFY/Notify party", definition: "通知人,货物到达时被通知的一方", tags: ["基础", "物流"]},
        { chinese: "承运人", english: "carrier", definition: "提供运输服务的公司，如航运公司、航空公司、卡车公司等", tags: ["基础", "物流"]},
        { chinese: "工厂交货", english: "EXW", definition: "Ex Works: 工厂交货，卖方在其地点提供货物，买方承担所有费用和风险", tags: ["基础", "物流"]},
        { chinese: "离岸价", english: "FOB", definition: "Free on Board: 装运港船上交货，卖方将货物装上船后，费用和风险转移给买方", tags: ["基础", "物流"]},
        { chinese: "门到门", english: "door to door", definition: "提供从卖方位置到买方位置的一站式物流服务",tags: ["基础", "物流"]},
        { chinese: "港到港", english: "port to port", definition: "提供从起运港到目的港的运输服务", tags: ["基础", "物流"]},
        { chinese: "提货", english: "pickup", definition: "从指定地点取走货物", tags: ["基础", "物流"]},
        { chinese: "交货", english: "delivery", definition: "将货物送到指定地点", tags: ["基础", "物流"]},
        { chinese: "付款方式", english: "payment terms", definition: "买方支付货款的方式", tags: ["基础", "物流"]},
        { chinese: "交货时间", english: "delivery time", definition: "货物送到客户手中的时间", tags: ["基础", "物流"]},
        { chinese: "运输方式", english: "shipping method", definition: "货物运输的方式，例如海运、空运、陆运等", tags: ["基础", "物流"]},
        { chinese: "运输单据", english: "shipping documents", definition: "运输单据，包括提单、运单、保险单等", tags: ["基础", "物流"]},
        { chinese: "运输", english: "transportation", tags: ["基础", "物流"]},
        { chinese: "库存", english: "inventory", tags: ["基础", "物流"]},
        { chinese: "物流", english: "logistics", tags: ["基础", "物流"]},
        { chinese: "样品", english: "samples", definition: "用于展示产品的样品", tags: ["基础", "物流"]},
        { chinese: "交货期", english: "lead Time", definition: "从订单确认到货物交付的时间间隔", tags: ["基础", "物流"]},
        { chinese: "唛头", english: "shipping mark", definition: "唛头", tags: ["基础", "物流"]},

        { chinese: "订舱", english: "booking", definition: "向船公司或航空公司预订运输舱位", tags: ["基础", "物流"]},
        
        { chinese: "预计离港时间", english: "ETD", definition: "Estimated Time of Departure: 预计离港时间", tags: ["基础", "物流"]},
        { chinese: "预计到达时间", english: "ETA", definition: "Estimated Time of Arrival: 预计到达时间", tags: ["基础", "物流"]},

        { chinese: "码头", english: "terminal", definition: "货物装卸和存放的地方", tags: ["基础", "物流"]},
        { chinese: "泊位", english: "berth", definition: "船舶在码头停靠的位置", tags: ["基础", "物流"]},
        { chinese: "起重机", english: "crane", definition: "用于装卸货物的设备", tags: ["基础", "物流"]},
        { chinese: "叉车", english: "forklift", definition: "搬运货物的工具", tags: ["基础", "物流"]},
        { chinese: "装货港/起运港", english: "POL/port of loading", definition: "货物装船的出发港口", tags: ["基础", "物流"]},
        { chinese: "卸货港/目的港", english: "POD/port of discharge", definition: "货物卸船的到达港口", tags: ["基础", "物流"]},
        { chinese: "船舶", english: "vessel", definition: "用于海上运输的船只", tags: ["基础", "物流"]},
        { chinese: "航班", english: "flight", definition: "用于航空运输的航班", tags: ["基础", "物流"]},
        { chinese: "卡车", english: "truck", definition: "用于陆路运输的车辆", tags: ["基础", "物流"]},
        { chinese: "铁路", english: "rail", definition: "用于铁路运输的列车", tags: ["基础", "物流"]},

        { chinese: "整柜", english: "FCL", definition: "Full Container Load: 整箱货运输，货物占满整一个集装箱", tags: ["基础", "物流"]},
        { chinese: "拼箱", english: "LCL", definition: "Less than Container Load: 拼箱货运输，货物不足整箱，与其他货物一起装箱", tags: ["基础", "物流"]},
        { chinese: "装箱", english: "Container stuffing", definition: "将货物装入集装箱", tags: ["基础", "物流"]},
        { chinese: "拆箱", english: "Container unstuffing", definition: "从集装箱中取出货物", tags: ["基础", "物流"]},

        { chinese: "直运", english: "direct shipment", definition: "货物从起点直接运往终点", tags: ["基础", "物流"]},
        { chinese: "转运", english: "transshipment", definition: "货物在中途港口换装其他运输工具", tags: ["基础", "物流"]},
        { chinese: "内陆运输", english: "Inland haulage", definition: "货物在陆地上的运输过程", tags: ["基础", "物流"]},

        { chinese: "运输时间", english: "transit time", definition: "货物从起运点到目的地所需的时间", tags: ["基础", "物流"]},
        { chinese: "运输计划", english: "shipping schedule", definition: "货物运输的路线和时间安排", tags: ["基础", "物流"]},

        { chinese: "体积重量", english: "Volume Weight", definition: "根据货物体积计算的重量", tags: ["基础", "物流"]},
        { chinese: "实际重量", english: "Actual Weight", definition: "货物的真实重量", tags: ["基础", "物流"]},
        { chinese: "计费重量", english: "Chargeable Weight", definition: "用于计算运费的重量", tags: ["基础", "物流"]},
        

        { chinese: "不定期船运输", english: "tramp shipping", definition: "船舶无固定航线和船期，根据货源情况安排航行", tags: ["基础", "物流"]}
    ],
    "费用类": [
        { chinese: "海运费", english: "sea freight", definition: "通过海运方式运输货物所需支付的费用", tags: ["基础", "物流"]},          
        { chinese: "空运费", english: "air freight", definition: "通过航空方式运输货物所需支付的费用", tags: ["基础", "物流"]},   

        { chinese: "超重费", english: "Overweight fee", definition: "超重附加费：由于货物单件重量超过规定标准，运输方对超出部分加收的费用，以弥补额外的运输成本和风险", tags: ["基础", "物流"]},   
        { chinese: "超大费", english: "Oversize fee", definition: "超大附加费：针对货物的尺寸超过运输工具或装卸设备的标准尺寸而征收的额外费用，确保特殊规格货物的顺利运输", tags: ["基础", "物流"]},   

        { chinese: "文件费", english: "DOC/Document Fee", definition: "办理运输文件所需支付的费用", tags: ["基础", "物流"]},          
        { chinese: "旺季附加费", english: "PSS/peak season surcharge", definition: "peak season surcharge", tags: ["基础", "物流"]}        
    ],
    "单证类": [
        { chinese: "提单", english: "BL/BOL", definition: "Bill of Lading: 是海上货物运输的重要单据，具有物权凭证等作用", tags: ["基础", "物流"]},
        { chinese: "正本提单", english: "OBL", definition: "Original Bill of Lading: 具有提货权的提单原件", tags: ["基础", "物流"]},
        { chinese: "主提单", english: "MBL", definition: "Master Bill of Lading: 通常由航运公司或航空公司签发的提单", tags: ["基础", "物流"]},
        { chinese: "货代提单", english: "HBL", definition: "House Bill of Lading: 由货运代理签发的提单，也是托运人和承运人之间的运输合同", tags: ["基础", "物流"]},
        { chinese: "航空运单", english: "AWB", definition: "Air Waybill: 航空货运的提单", tags: ["基础", "物流"]},
        { chinese: "航空主运单", english: "MAWB", definition: "Master Air Waybill: 航空公司签发的运单", tags: ["基础", "物流"]},
        { chinese: "航空分运单", english: "HAWB", definition: "House Air Waybill: 货代公司签发的运单", tags: ["基础", "物流"]},
        { chinese: "电放提单", english: "Telex Release Bill of Lading", definition: "通过电子方式放货的提单", tags: ["基础", "物流"]},

        { chinese: "交货地", english: "POD", definition: "Place of Delivery: 交货地", tags: ["基础", "物流"]},

        { chinese: "商业发票", english: "CI/Commercial Invoice", definition: "货物买卖的票据，包含货物细节及价格", tags: ["基础", "物流"]},
        { chinese: "形式发票", english: "proforma invoice", definition: "用于预估价格和确认订单", tags: ["基础", "物流"]},
        { chinese: "装箱单", english: "PL/Packing List", definition: "装箱单，列明货物清单及包装细节", tags: ["基础", "物流"]},
        { chinese: "装货单", english: "S/O", definition: "Shipping Order: 船公司签发给托运人的装货指令", tags: ["基础", "物流"]},
        { chinese: "商检", english: "customs inspection", tags: ["基础", "物流"]},
        { chinese: "熏蒸证书", english: "fumigation certificate", tags: ["基础", "物流"]}
    ],
    "海关类": [
        { chinese: "清关", english: "customs clearance",definition: {} ,tags: ["基础", "物流"]},
        { chinese: "自动舱单系统", english: "AMS", definition: "Automated Manifest System: 美国海关用于预先录入和审查货物数据的系统", tags: ["基础", "物流"]},
        { chinese: "滞期费", english: "demurrage", definition: "集装箱在目的地码头或堆场的超期使用费，通常发生在收货人清关提货前", tags: ["基础", "物流"]},
        { chinese: "滞箱费", english: "detention", definition: "如果清关后将集装箱提出堆场或码头，但未在规定期限内返还空箱，就会产生集装箱超期使用费用", tags: ["基础", "物流"]},
        { chinese: "堆存费", english: "storage", definition: "码头允许免费堆存的时间，超过这个时间后，每天每柜会产生一定的堆存费或滞港费", tags: ["基础", "物流"]},  
        
        { chinese: "码头费", english: "THC", definition: "terminal handling charge: 码头费", tags: ["基础", "物流"]}    
    ],
    "税务类": [
        { chinese: "汇率", english: "exchange rate", definition: "不同货币之间的兑换比率", tags: ["基础", "物流"]},
        { chinese: "增值税", english: "VAT", definition: "Value Added Tax: 对商品增值部分征收的税款", tags: ["基础", "物流"]},
        { chinese: "关税", english: "duty", definition: "进口货物需要缴纳的税款", tags: ["基础", "物流"]},
        { chinese: "关税税率", english: "tariff", definition: "用于计算关税的税率", tags: ["基础", "物流"]},
        { chinese: "增值税", english: "VAT", definition: "Value Added Tax: 对商品增值部分征收的税款", tags: ["基础", "物流"]},
        { chinese: "海关编码", english: "HS Code", definition: "Harmonized System Code: 海关编码，用于商品分类和监管", tags: ["基础", "物流"]},
        { chinese: "退税", english: "tax refund", tags: ["基础", "物流"]},
        { chinese: "报关行", english: "customs broker", definition: "负责货物进出口通关手续", tags: ["基础", "物流"]}
    ],
    "保险类": [
        { chinese: "保险费", english: "insurance premium", definition: "保险的费用", tags: ["基础", "物流"]},
        { chinese: "保险单", english: "insurance policy", definition: "保险单", tags: ["基础", "物流"]},
        { chinese: "保险范围", english: "insurance coverage", definition: "保险提供的保障范围", tags: ["基础", "物流"]},
        { chinese: "索赔", english: "claim", definition: "保险事故发生后，向保险公司提出赔偿请求", tags: ["基础", "物流"]}
    ],
    "产品类": [
        { chinese: "纺织品", english: "textile", definition: "包括棉花、毛线、丝绸等材料制成的产品", tags: ["基础", "物流"]},
        { chinese: "服装", english: "apparel", definition: "包括衣服、鞋帽等", tags: ["基础", "物流"]},
        { chinese: "鞋类", english: "footwear", definition: "包括鞋类，包括鞋、靴子、凉鞋等", tags: ["基础", "物流"]},
        { chinese: "电子产品", english: "electronics", definition: "包括手机、电脑、电视等", tags: ["基础", "物流"]},
        { chinese: "金属产品", english: "metals", definition: "包括钢铁、铝、铜等", tags: ["基础", "物流"]},
        { chinese: "家用电器", english: "home appliances", definition: "包括冰箱、洗衣机、空调等", tags: ["基础", "物流"]},
        { chinese: "化妆品", english: "cosmetics", definition: "包括护肤品、彩妆、香水等", tags: ["基础", "物流"]}
    ],
    "航线类": [
        // 美国
        { chinese: "洛杉矶", english: "LA/Los Angeles", definition: "位于加利福尼亚州西南部，是美国最大的集装箱港口", tags: ["港口", "美国", "美西"]},
        { chinese: "长滩", english: "LB/Long Beach", definition: "紧邻洛杉矶码头，拥堵情况相对较少。美森轮船的独立码头就位于此处", tags: ["港口", "美国", "美西"]},
        { chinese: "奥克兰", english: "OAK/Oakland", definition: "位于加利福尼亚州", tags: ["港口", "美国", "美西"]},
        { chinese: "旧金山", english: "SFO/San Francisco", definition: "也称为三藩市，是加利福尼亚州的重要港口", tags: ["港口", "美国", "美西"]},
        { chinese: "西雅图", english: "SEA/Seattle", definition: "位于华盛顿州", tags: ["港口", "美国", "美西"]},
        { chinese: "塔科玛", english: "TAC/Tacoma", definition: "位于华盛顿州", tags: ["港口", "美国", "美西"]},
        
        { chinese: "芝加哥", english: "CHI/Chicago", definition: "位于伊利诺伊州,美国中部", tags: ["港口", "美国", "美中"]},

        { chinese: "纽约", english: "NY/New York", definition: "位于华盛顿州", tags: ["港口", "美国", "美东"]},
        { chinese: "休斯敦", english: "HOU/Houston", definition: "位于德克萨斯州，是重要的能源和物流中心", tags: ["港口", "美国", "美东"]},
        { chinese: "迈阿密", english: "MIA/Miami", definition: "位于佛罗里达州，是热带水果和海产品的集散地", tags: ["港口", "美国", "美东"]},
        { chinese: "萨凡纳", english: "SAV/Savanah", definition: "位于乔治亚州", tags: ["港口", "美国", "美东"]},
        { chinese: "查尔斯顿", english: "CHA/Charleston", definition: "位于南卡罗来纳州", tags: ["港口", "美国", "美东"]},

        // 加拿大
        { chinese: "温哥华", english: "Vancouver", definition: "位于加拿大西海岸，也是北美西海岸最重要的港口之一，也是北美太平洋沿岸最大的港口之一", tags: ["港口", "加拿大"]},
        { chinese: "蒙特利尔", english: "Montreal", definition: "位于加拿大东部，是加拿大最大的内陆港口城市。 蒙特利尔港是加拿大最大的内河港口，通过圣劳伦斯河与大西洋相连，是北美最重要的国际贸易港口之一", tags: ["港口", "加拿大"]},
        { chinese: "多伦多", english: "Toronto", definition: "位于加拿大安大略省的岸边", tags: ["港口", "加拿大"]},
        
        // 欧洲
        { chinese: "安特卫普", english: "Antwerp", definition: "比利时", tags: ["港口", "欧洲"]},
        { chinese: "汉堡", english: "Hamburg", definition: "德国", tags: ["港口", "欧洲"]},
        { chinese: "不莱梅", english: "Bremen", definition: "德国", tags: ["港口", "欧洲"]},
        { chinese: "鹿特丹", english: "Rotterdam", definition: "荷兰", tags: ["港口", "欧洲"]},
        { chinese: "阿姆斯特丹", english: "Amsterdam", definition: "荷兰", tags: ["港口", "欧洲"]},
        { chinese: "勒阿弗尔", english: "Le Havre", definition: "法国", tags: ["港口", "欧洲"]},
        { chinese: "费利克斯托", english: "Le Havre", definition: "英国", tags: ["港口", "欧洲"]},
        { chinese: "南安普顿", english: "Southampton", definition: "英国", tags: ["港口", "欧洲"]},
        { chinese: "伦敦", english: "London", definition: "英国", tags: ["港口", "欧洲"]},
        { chinese: "曼彻斯特", english: "Manchester", definition: "英国", tags: ["港口", "欧洲"]},
        { chinese: "维也纳", english: "Vienna", definition: "奥地利", tags: ["港口", "欧洲"]},
        { chinese: "都柏林", english: "Dublin", definition: "爱尔兰", tags: ["港口", "欧洲"]},
        { chinese: "布达佩斯", english: "Budapest", definition: "匈牙利", tags: ["港口", "欧洲"]},
        { chinese: "华沙", english: "Warsaw", definition: "波兰", tags: ["港口", "欧洲"]},
        { chinese: "布拉格", english: "Prague", definition: "捷克斯洛伐克", tags: ["港口", "欧洲"]},
        { chinese: "奥尔胡斯", english: "Aarhus", definition: "丹麦", tags: ["港口", "欧洲"]},
        { chinese: "哥本哈根", english: "Copenhagen", definition: "丹麦", tags: ["港口", "欧洲"]},
        { chinese: "哥德堡", english: "Gothenburg", definition: "瑞典", tags: ["港口", "欧洲"]},
        { chinese: "斯德哥尔摩", english: "Stockholm", definition: "瑞典", tags: ["港口", "欧洲"]},
        { chinese: "奥斯陆", english: "Oslo", definition: "挪威", tags: ["港口", "欧洲"]},
        { chinese: "赫尔辛基", english: "Helsinki", definition: "芬兰", tags: ["港口", "欧洲"]},
        { chinese: "里斯本", english: "Lisbon", definition: "葡萄牙", tags: ["港口", "欧洲"]},
        { chinese: "莱肖埃斯", english: "Leixões", definition: "葡萄牙", tags: ["港口", "欧洲"]},
        { chinese: "波尔图", english: "Porto", definition: "葡萄牙", tags: ["港口", "欧洲"]},

        // 澳新
        { chinese: "悉尼", english: "Sydney", definition: "澳大利亚", tags: ["港口", "澳新线"]},
        { chinese: "墨尔本", english: "Melbourne", definition: "澳大利亚", tags: ["港口", "澳新线"]},
        { chinese: "布里斯班", english: "Brisbane", definition: "澳大利亚", tags: ["港口", "澳新线"]},
        { chinese: "阿德莱德", english: "Adelaide", definition: "澳大利亚", tags: ["港口", "澳新线"]},
        { chinese: "奥克兰", english: "Auckland", definition: "新西兰", tags: ["港口", "澳新线"]},
        { chinese: "利特顿", english: "Lyttelton", definition: "新西兰", tags: ["港口", "澳新线"]},
        { chinese: "惠灵顿", english: "Wellington", definition: "新西兰", tags: ["港口", "澳新线"]}
    ]
};


const transitTimeData = {
    "USA": {
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
    "Canada": {
        "Sea truck": {
            "default": "35-45"
        },
        "Sea express": {
            "default": "32-38"
        },
        "Air express": {
            "default": "10-15"
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
    "US": {
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
    "CA": {
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
    "EU": {
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
    "UK": {
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

// 分类配置
const usaCategories = [
    {
        id: "zipCodes",
        title: "美国州邮编分布",
        data: [
            { area: "美东", state: "加利福尼亚", short: "CA", prefix: "90-96" },
            { area: "美东", state: "纽约", short: "NY", prefix: "10-14" },
            { area: "美东", state: "德克萨斯", short: "TX", prefix: "75-79" },
            { area: "美东", state: "佛罗里达", short: "FL", prefix: "32-34" },
            // 其他州数据...
        ],
        render: (data) => `
            <table class="table table-bordered">
                <thead>
                    <tr>
                        <th>州</th>
                        <th>邮编前缀</th>
                    </tr>
                </thead>
                <tbody>
                    ${data.map(item => `
                        <tr>
                            <td>${item.area}</td>
                            <td>${item.state}</td>
                            <td>${item.short}</td>
                            <td>${item.prefix}</td>
                        </tr>
                    `).join("")}
                </tbody>
            </table>
        `
    },
    {
        id: "prohibitedItems",
        title: "美国禁运品",
        data: [
            "易燃易爆物品",
            "毒品及违禁药品",
            "武器及弹药",
            "活体动物",
            "假冒伪劣商品",
            // 其他禁运品...
        ],
        render: (data) => `
            <ul>
                ${data.map(item => `<li>${item}</li>`).join("")}
            </ul>
        `
    },
    // 其他分类...
];


