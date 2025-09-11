// 物流备忘录数据文件
// 通用信息数据
const logisticsGeneralInfo = {
    basicConcepts: [
        {
            title: "DDP vs DDU",
            content: "DDP (Delivered Duty Paid): 包税到门，卖方承担所有费用和风险\nDDU (Delivered Duty Unpaid): 自税到门，买方承担进口关税和税费"
        },
        {
            title: "重量计算方式",
            content: "实重 (Actual Weight): 货物实际重量\n体积重 (Volumetric Weight): 长×宽×高÷6000 (空运) 或 ÷5000 (快递)\n计费重 (Chargeable Weight): 取实重和体积重的较大值"
        },
        {
            title: "清关流程",
            content: "1. 货物到达目的港\n2. 提交清关文件\n3. 海关查验\n4. 缴纳关税\n5. 放行提货"
        }
    ],
    terminology: [
        { term: "DDP", meaning: "Delivered Duty Paid - 包税到门", category: "贸易术语" },
        { term: "DDU", meaning: "Delivered Duty Unpaid - 自税到门", category: "贸易术语" },
        { term: "CIF", meaning: "Cost, Insurance and Freight - 成本加保险费加运费", category: "贸易术语" },
        { term: "FOB", meaning: "Free On Board - 离岸价", category: "贸易术语" },
        { term: "EXW", meaning: "Ex Works - 工厂交货", category: "贸易术语" },
        { term: "HSCode", meaning: "Harmonized System Code - 海关编码", category: "清关术语" },
        { term: "Commercial Invoice", meaning: "商业发票", category: "清关术语" },
        { term: "Packing List", meaning: "装箱单", category: "清关术语" },
        { term: "Bill of Lading", meaning: "提单", category: "运输术语" },
        { term: "Air Waybill", meaning: "空运单", category: "运输术语" },
        { term: "Customs Clearance", meaning: "清关", category: "清关术语" },
        { term: "Duty", meaning: "关税", category: "清关术语" },
        { term: "VAT", meaning: "Value Added Tax - 增值税", category: "税务术语" },
        { term: "GST", meaning: "Goods and Services Tax - 商品服务税", category: "税务术语" },
        { term: "TNT", meaning: "TNT Express - 快递公司", category: "快递公司" },
        { term: "DHL", meaning: "DHL Express - 快递公司", category: "快递公司" },
        { term: "FedEx", meaning: "Federal Express - 快递公司", category: "快递公司" },
        { term: "UPS", meaning: "United Parcel Service - 快递公司", category: "快递公司" }
    ],
    commonQuestions: [
        {
            question: "如何选择合适的运输方式？",
            answer: "根据货物重量、体积、时效要求、成本预算等因素综合考虑。小件货物选择快递，大件货物选择空运或海运。"
        },
        {
            question: "清关需要多长时间？",
            answer: "一般3-7个工作日，具体时间取决于目的国海关效率和文件完整性。"
        },
        {
            question: "如何降低物流成本？",
            answer: "1. 合理包装减少体积重\n2. 选择合适的运输方式\n3. 批量发货享受优惠\n4. 提前规划避免加急费用"
        }
    ]
};

// 国家信息数据
const countryLogisticsInfo = [
    {
        code: "US",
        name: "美国",
        flag: "🇺🇸",
        generalInfo: {
            currency: "USD",
            timezone: "UTC-5 to UTC-10",
            language: "英语",
            capital: "华盛顿"
        },
        logistics: {
            majorPorts: ["洛杉矶", "长滩", "纽约", "迈阿密", "西雅图"],
            majorAirports: ["LAX", "JFK", "MIA", "SEA", "ORD"],
            customs: {
                clearanceTime: "3-5个工作日",
                requiredDocs: ["商业发票", "装箱单", "提单", "原产地证"],
                restrictions: ["食品需要FDA认证", "电子产品需要FCC认证"],
                duties: "根据HSCode确定，一般5-25%"
            },
            shipping: {
                express: ["DHL", "FedEx", "UPS", "TNT"],
                airFreight: ["国泰航空", "美联航", "达美航空"],
                seaFreight: ["马士基", "中远海运", "长荣海运"]
            }
        },
        pricing: {
            express: "首重$25-35，续重$5-8/kg",
            airFreight: "$4-8/kg",
            seaFreight: "$800-1200/20ft, $1200-1800/40ft"
        },
        notes: "美国对电子产品、食品、药品有严格的认证要求，建议提前了解相关法规。"
    },
    {
        code: "GB",
        name: "英国",
        flag: "🇬🇧",
        generalInfo: {
            currency: "GBP",
            timezone: "UTC+0",
            language: "英语",
            capital: "伦敦"
        },
        logistics: {
            majorPorts: ["南安普顿", "费利克斯托", "利物浦"],
            majorAirports: ["LHR", "LGW", "STN", "LTN"],
            customs: {
                clearanceTime: "2-4个工作日",
                requiredDocs: ["商业发票", "装箱单", "提单", "原产地证"],
                restrictions: ["食品需要FSA认证", "电子产品需要CE认证"],
                duties: "根据HSCode确定，一般0-20%"
            },
            shipping: {
                express: ["DHL", "FedEx", "UPS", "TNT"],
                airFreight: ["英航", "维珍航空", "国泰航空"],
                seaFreight: ["马士基", "中远海运", "长荣海运"]
            }
        },
        pricing: {
            express: "首重£20-30，续重£4-6/kg",
            airFreight: "£3-6/kg",
            seaFreight: "£600-900/20ft, £900-1400/40ft"
        },
        notes: "英国脱欧后清关流程有所变化，建议提前了解最新政策。"
    },
    {
        code: "DE",
        name: "德国",
        flag: "🇩🇪",
        generalInfo: {
            currency: "EUR",
            timezone: "UTC+1",
            language: "德语",
            capital: "柏林"
        },
        logistics: {
            majorPorts: ["汉堡", "不来梅", "威廉港"],
            majorAirports: ["FRA", "MUC", "DUS", "HAM"],
            customs: {
                clearanceTime: "2-3个工作日",
                requiredDocs: ["商业发票", "装箱单", "提单", "原产地证"],
                restrictions: ["食品需要欧盟认证", "电子产品需要CE认证"],
                duties: "根据HSCode确定，一般0-15%"
            },
            shipping: {
                express: ["DHL", "FedEx", "UPS", "TNT"],
                airFreight: ["汉莎航空", "国泰航空", "法航"],
                seaFreight: ["马士基", "中远海运", "长荣海运"]
            }
        },
        pricing: {
            express: "首重€20-30，续重€4-6/kg",
            airFreight: "€3-6/kg",
            seaFreight: "€500-800/20ft, €800-1200/40ft"
        },
        notes: "德国是欧盟成员国，清关相对简单，但需要符合欧盟标准。"
    },
    {
        code: "AU",
        name: "澳大利亚",
        flag: "🇦🇺",
        generalInfo: {
            currency: "AUD",
            timezone: "UTC+8 to UTC+10",
            language: "英语",
            capital: "堪培拉"
        },
        logistics: {
            majorPorts: ["悉尼", "墨尔本", "布里斯班", "珀斯"],
            majorAirports: ["SYD", "MEL", "BNE", "PER"],
            customs: {
                clearanceTime: "3-5个工作日",
                requiredDocs: ["商业发票", "装箱单", "提单", "原产地证"],
                restrictions: ["食品需要AQIS认证", "电子产品需要ACMA认证"],
                duties: "根据HSCode确定，一般0-10%"
            },
            shipping: {
                express: ["DHL", "FedEx", "UPS", "TNT"],
                airFreight: ["澳航", "国泰航空", "新航"],
                seaFreight: ["马士基", "中远海运", "长荣海运"]
            }
        },
        pricing: {
            express: "首重A$30-40，续重A$6-10/kg",
            airFreight: "A$5-10/kg",
            seaFreight: "A$800-1200/20ft, A$1200-1800/40ft"
        },
        notes: "澳大利亚对生物安全要求严格，食品、动植物产品需要特殊处理。"
    },
    {
        code: "CA",
        name: "加拿大",
        flag: "🇨🇦",
        generalInfo: {
            currency: "CAD",
            timezone: "UTC-3.5 to UTC-8",
            language: "英语/法语",
            capital: "渥太华"
        },
        logistics: {
            majorPorts: ["温哥华", "多伦多", "蒙特利尔", "哈利法克斯"],
            majorAirports: ["YYZ", "YVR", "YUL", "YHZ"],
            customs: {
                clearanceTime: "2-4个工作日",
                requiredDocs: ["商业发票", "装箱单", "提单", "原产地证"],
                restrictions: ["食品需要CFIA认证", "电子产品需要IC认证"],
                duties: "根据HSCode确定，一般0-15%"
            },
            shipping: {
                express: ["DHL", "FedEx", "UPS", "TNT"],
                airFreight: ["加航", "国泰航空", "美联航"],
                seaFreight: ["马士基", "中远海运", "长荣海运"]
            }
        },
        pricing: {
            express: "首重C$25-35，续重C$5-8/kg",
            airFreight: "C$4-8/kg",
            seaFreight: "C$700-1100/20ft, C$1100-1700/40ft"
        },
        notes: "加拿大与美国有自由贸易协定，但清关流程仍需独立处理。"
    },
    {
        code: "JP",
        name: "日本",
        flag: "🇯🇵",
        generalInfo: {
            currency: "JPY",
            timezone: "UTC+9",
            language: "日语",
            capital: "东京"
        },
        logistics: {
            majorPorts: ["横滨", "神户", "名古屋", "大阪"],
            majorAirports: ["NRT", "HND", "KIX", "NGO"],
            customs: {
                clearanceTime: "1-3个工作日",
                requiredDocs: ["商业发票", "装箱单", "提单", "原产地证"],
                restrictions: ["食品需要厚生劳动省认证", "电子产品需要PSE认证"],
                duties: "根据HSCode确定，一般0-10%"
            },
            shipping: {
                express: ["DHL", "FedEx", "UPS", "TNT"],
                airFreight: ["日航", "全日空", "国泰航空"],
                seaFreight: ["马士基", "中远海运", "长荣海运"]
            }
        },
        pricing: {
            express: "首重¥3000-4000，续重¥500-800/kg",
            airFreight: "¥400-800/kg",
            seaFreight: "¥60000-90000/20ft, ¥90000-140000/40ft"
        },
        notes: "日本对产品质量要求极高，建议选择可靠的供应商和物流商。"
    }
];


// 术语分类数据
const termsByCategory = {
    
    "物流类": [
        {
            chinese: "中欧卡航完整流程",
            english: "Complete China-Europe Trucking Process",
            definition: `1.货物接收与装柜：客户将货物送至指定地点，由中欧卡航进行接收并装柜。
          \n 2.内陆运输：货物通过卡车进行内陆运输至新疆口岸。
          \n 3.换装与报关出境：货物在新疆口岸进行换装，并办理报关出境手续。
          \n 4.国际运输：货物通过哈萨克斯坦、俄罗斯、白俄罗斯等国家进行国际运输。
          \n 5.清关与派送：货物在波兰、匈牙利或比利时等清关地点进行清关，并由当地合作伙伴进行末端派送。`,
            tags: ["流程", "卡航", "完整", "步骤"],
        },
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
        { chinese: "清关", english: "customs clearance", definition: "货物通过海关检查并完成相关手续的过程", tags: ["基础", "物流"]},
        { chinese: "自动舱单系统", english: "AMS", definition: "Automated Manifest System: 美国海关用于预先录入和审查货物数据的系统", tags: ["基础", "物流"]},
        { chinese: "滞期费", english: "demurrage", definition: "集装箱在目的地码头或堆场的超期使用费，通常发生在收货人清关提货前", tags: ["基础", "物流"]},
        { chinese: "滞箱费", english: "detention", definition: "如果清关后将集装箱提出堆场或码头，但未在规定期限内返还空箱，就会产生集装箱超期使用费用", tags: ["基础", "物流"]},
        { chinese: "堆存费", english: "storage", definition: "码头允许免费堆存的时间，超过这个时间后，每天每柜会产生一定的堆存费或滞港费", tags: ["基础", "物流"]},  
        { chinese: "码头费", english: "THC", definition: "terminal handling charge: 码头费", tags: ["基础", "物流"]},
    ],
    "税务类": [
        { chinese: "汇率", english: "exchange rate", definition: "不同货币之间的兑换比率", tags: ["基础", "物流"]},
        { chinese: "增值税", english: "VAT", definition: "Value Added Tax: 对商品增值部分征收的税款", tags: ["基础", "物流"]},
        { chinese: "关税", english: "duty", definition: "进口货物需要缴纳的税款", tags: ["基础", "物流"]},
        { chinese: "关税税率", english: "tariff", definition: "用于计算关税的税率", tags: ["基础", "物流"]},
        { chinese: "增值税", english: "VAT", definition: "Value Added Tax: 对商品增值部分征收的税款", tags: ["基础", "物流"]},
        { chinese: "海关编码", english: "HS Code", definition: "Harmonized System Code: 海关编码其实是依据《商品名称及编码协调制度的国际公约》（简称HS），用科学系统的方法将商品分类。HS采用六位数编码，把全部国际贸易商品分为22类，98章。章以下再分为目和子目。商品编码第一、二位数码代表“章”，第三、四位数码代表“目”（Heading），第五、六位数码代表“子目”（Subheading）。前6位数是HS国际标准编码，后2-4位数是各个国家海关按照实际情况再进行延伸，所以大家才会常说前6位海关编码是国际通用的。", tags: ["基础", "物流"]},
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
        { chinese: "OA联盟", english: "Ocean Alliance", definition: "OA联盟（Ocean Alliance）是由四家船公司组成的强大联盟，分别是法国达飞轮船（CMA CGM）、中远海运（COSCO）、长荣海运（EMC）和东方海外（OOCL）", tags: ["物流","航线"]},
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

// 将数据暴露到全局
window.logisticsData = {
    generalInfo: logisticsGeneralInfo,
    countryInfo: countryLogisticsInfo,
    termsByCategory: termsByCategory
};
