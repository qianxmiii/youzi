// 常用网址数据文件
const bookmarksData = [
  // 快递公司
  {
    id: 1,
    name: "DHL官网",
    url: "https://www.dhl.com",
    description: "DHL快递查询和下单",
    category: "快递公司",
    icon: "🚚",
    tags: ["快递", "查询", "下单"]
  },
  {
    id: 2,
    name: "FedEx官网",
    url: "https://www.fedex.com",
    description: "FedEx快递查询和下单",
    category: "快递公司",
    icon: "📦",
    tags: ["快递", "查询", "下单"]
  },
  {
    id: 3,
    name: "UPS官网",
    url: "https://www.ups.com",
    description: "UPS快递查询和下单",
    category: "快递公司",
    icon: "📮",
    tags: ["快递", "查询", "下单"]
  },
  {
    id: 4,
    name: "TNT官网",
    url: "https://www.tnt.com",
    description: "TNT快递查询和下单",
    category: "快递公司",
    icon: "🚛",
    tags: ["快递", "查询", "下单"]
  },
  {
    id: 5,
    name: "顺丰速运",
    url: "https://www.sf-express.com",
    description: "顺丰速运官网",
    category: "快递公司",
    icon: "📬",
    tags: ["快递", "国内", "查询"]
  },
  {
    id: 6,
    name: "圆通速递",
    url: "https://www.yto.net.cn",
    description: "圆通速递官网",
    category: "快递公司",
    icon: "📭",
    tags: ["快递", "国内", "查询"]
  },
  {
    id: 32,
    name: "德邦快递",
    url: "https://www.deppon.com/mail/price",
    description: "德邦快递价格时效查询",
    category: "快递公司",
    icon: "🚚",
    tags: ["快递", "中国"]
  },
  {
    id: 33,
    name: "安能物流",
    url: "https://www.ane56.com/self-Freight.html",
    description: "安能物流",
    category: "快递公司",
    icon: "🚛",
    tags: ["快递", "中国"]
  },

  // 物流工具
  {
    id: 7,
    name: "17TRACK",
    url: "https://www.17track.net",
    description: "全球快递查询平台",
    category: "物流工具",
    icon: "🌍",
    tags: ["查询", "全球", "物流"]
  },
  {
    id: 8,
    name: "快递100",
    url: "https://www.kuaidi100.com",
    description: "国内快递查询平台",
    category: "物流工具",
    icon: "📊",
    tags: ["查询", "国内", "快递"]
  },
  {
    id: 9,
    name: "Track-Trace",
    url: "https://www.track-trace.com",
    description: "国际快递查询平台",
    category: "物流工具",
    icon: "🔍",
    tags: ["查询", "国际", "快递"]
  },
  {
    id: 10,
    name: "AfterShip",
    url: "https://www.aftership.com",
    description: "包裹跟踪平台",
    category: "物流工具",
    icon: "📱",
    tags: ["查询", "跟踪", "物流"]
  },
  {
    id: 35,
    name: "Sagawa-佐川急便",
    url: "https://k2k.sagawa-exp.co.jp/p/sagawa/web/okurijoinput.jsp",
    description: "佐川急便",
    category: "快递公司",
    icon: "📦",
    tags: ["日本", "快递"]
  },

  // 海关查询
  {
    id: 11,
    name: "中国海关总署",
    url: "http://www.customs.gov.cn",
    description: "中国海关总署官网",
    category: "海关查询",
    icon: "🏛️",
    tags: ["海关", "政策", "查询"]
  },
  {
    id: 12,
    name: "美国海关CBP",
    url: "https://www.cbp.gov",
    description: "美国海关和边境保护局",
    category: "海关查询",
    icon: "🇺🇸",
    tags: ["海关", "美国", "政策"]
  },
  {
    id: 13,
    name: "欧盟海关",
    url: "https://ec.europa.eu/taxation_customs",
    description: "欧盟海关和税务联盟",
    category: "海关查询",
    icon: "🇪🇺",
    tags: ["海关", "欧盟", "政策"]
  },
  {
    id: 14,
    name: "HSCode查询",
    url: "https://www.hscode.org",
    description: "海关编码查询工具",
    category: "海关查询",
    icon: "🔢",
    tags: ["海关编码", "查询", "工具"]
  },
  {
    id: 30,
    name: "中国国际贸易单一窗口",
    url: "https://www.singlewindow.cn/#/publicInquiryDetail?id=pi5",
    description: "中国国际贸易单一窗口公共查询",
    category: "海关查询",
    icon: "🏛️",
    tags: ["海关", "报关", "中国"]
  },
  {
    id: 31,
    name: "海关备案查询",
    url: "http://202.127.48.145:8888/zscq/search/jsp/vBrandSearchIndex.jsp",
    description: "知识产权海关保护备案查询",
    category: "海关查询",
    icon: "📋",
    tags: ["海关", "备案", "品牌"]
  },
  {
    id: 34,
    name: "美国FDA查询",
    url: "https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfrl/rl.cfm",
    description: "美国FDA查询",
    category: "海关查询",
    icon: "🏥",
    tags: ["FDA", "美国"]
  },

  // 汇率查询
  {
    id: 15,
    name: "XE汇率",
    url: "https://www.xe.com",
    description: "实时汇率查询",
    category: "汇率查询",
    icon: "💱",
    tags: ["汇率", "货币", "实时"]
  },
  {
    id: 16,
    name: "OANDA汇率",
    url: "https://www.oanda.com",
    description: "专业汇率查询平台",
    category: "汇率查询",
    icon: "📈",
    tags: ["汇率", "专业", "历史"]
  },
  {
    id: 17,
    name: "中国银行汇率",
    url: "https://www.boc.cn/sourcedb/whpj",
    description: "中国银行外汇牌价",
    category: "汇率查询",
    icon: "🏦",
    tags: ["汇率", "中国银行", "牌价"]
  },

  // 其他工具
  {
    id: 18,
    name: "世界时钟",
    url: "https://www.timeanddate.com",
    description: "全球时区时间查询",
    category: "其他工具",
    icon: "🕐",
    tags: ["时间", "时区", "全球"]
  },
  {
    id: 19,
    name: "Google翻译",
    url: "https://translate.google.com",
    description: "在线翻译工具",
    category: "其他工具",
    icon: "🌐",
    tags: ["翻译", "语言", "在线"]
  },
  {
    id: 20,
    name: "单位换算",
    url: "https://www.convertworld.com",
    description: "各种单位换算工具",
    category: "其他工具",
    icon: "📏",
    tags: ["换算", "单位", "工具"]
  },
  {
    id: 21,
    name: "天气查询",
    url: "https://www.weather.com",
    description: "全球天气查询",
    category: "其他工具",
    icon: "🌤️",
    tags: ["天气", "全球", "查询"]
  },
  {
    id: 22,
    name: "地图查询",
    url: "https://www.google.com/maps",
    description: "Google地图",
    category: "其他工具",
    icon: "🗺️",
    tags: ["地图", "导航", "位置"]
  },
  {
    id: 23,
    name: "计算器",
    url: "https://www.calculator.net",
    description: "在线计算器工具",
    category: "其他工具",
    icon: "🧮",
    tags: ["计算", "工具", "在线"]
  },
  {
    id: 24,
    name: "PDF工具",
    url: "https://smallpdf.com",
    description: "PDF在线处理工具",
    category: "其他工具",
    icon: "📄",
    tags: ["PDF", "转换", "工具"]
  } ,
  {
    id: 25,
    name: "欧盟进口税率查询",
    url: "http://ec.europa.eu",
    description: "欧盟进口税率查询",
    category: "税率查询",
    icon: "📄",
    tags: ["税率", "欧盟"]  
  },
  {
    id: 26,
    name: "美国进口税率查询",
    url: "https://hts.usitc.gov",
    description: "美国进口税率查询",
    category: "税率查询",
    icon: "📄",
    tags: ["税率", "美国"]
  },
  {
    id: 27,
    name: "加拿大进口税率查询",
    url: "http://www.cbsa-asfc.gc.ca",
    description: "加拿大进口税率查询",
    category: "税率查询",
    icon: "📄",
    tags: ["税率", "加拿大"]
  },
  {
    id: 28,
    name: "澳大利亚进口税率查询",
    url: "https://ftaportal.dfat.gov.au",
    description: "澳大利亚进口税率查询",
    category: "税率查询",
    icon: "📄",
    tags: ["税率", "澳大利亚"]
  },
  {
    id: 29,
    name: "日本进口税率查询",
    url: "http://www.customs.go.jp",
    description: "日本进口税率查询",
    category: "税率查询",
    icon: "📄",
    tags: ["税率", "日本"]
  }
];

// 将数据暴露到全局
window.bookmarksData = bookmarksData;
