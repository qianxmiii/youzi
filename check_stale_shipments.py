import json
import requests
from datetime import datetime, timedelta
import re


def load_config(filename='config/config.json'):
    with open(filename, 'r', encoding='utf-8') as f:
        config = json.load(f)
        # 确保channel_filters有默认值
        config.setdefault('channel_filters', {
            "空运": ["Air truck", "Air express"],
            "快递派": ["Sea express", "Air express"],
            "卡派": ["Sea truck", "Air truck"],
            "海运": ["Sea express", "Sea truck"]
        })
        return config


def load_tracking_numbers(filename='data/tracking_numbers.json'):
    with open(filename, 'r', encoding='utf-8') as f:
        # 这里假设每条有 tracking_number 和 customer 字段
        return json.load(f)


def parse_eta_date(node_desc):
    pattern = r'ETA[:：]?\s*(\d{1,2})[./\/](\d{1,2})'
    match = re.search(pattern, node_desc, re.IGNORECASE)
    if match:
        month = int(match.group(1))
        day = int(match.group(2))
        now = datetime.now()
        year = now.year
        try:
            eta_date = datetime(year, month, day)
        except ValueError:
            return None
        if eta_date < now - timedelta(days=180):
            try:
                eta_date = datetime(year + 1, month, day)
            except ValueError:
                return None
        return eta_date
    return None


def is_eta_within_days(item, days=3):
    logs = item.get("logisticsInfors", [])
    for log in logs:
        eta_date = parse_eta_date(log.get("nodeDesc", ""))
        if eta_date:
            now = datetime.now()
            if 0 <= (eta_date - now).days <= days:
                return True
    return False


def query_logistics_api(tracking_list, base_url, batch_size=10):
    all_results = []
    headers = {"Content-Type": "application/json"}

    for i in range(0, len(tracking_list), batch_size):
        batch = tracking_list[i:i + batch_size]
        odds = [item['tracking_number'] for item in batch]
        payload = json.dumps({"odds": odds}, ensure_ascii=False)

        try:
            resp = requests.post(base_url, data=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            result = resp.json()
            if result.get('code') == 200:
                data = result.get('data', [])
                for d in data:
                    match = next((x for x in batch if x['tracking_number'] == d.get('odd')), None)
                    d['customer'] = match.get('customer') if match else ''
                    d['channel'] = match.get('channel', '') if match else ''
                    d['carrier'] = match.get('carrier', '') if match else ''
                all_results.extend(data)
            else:
                print(f"查询失败: {result.get('msg')}")
        except Exception as e:
            print(f"请求异常: {e}")

    return all_results


def highlight_keywords(text):
    keywords = ["POD", "签收", "派送", "delivered"]
    for kw in keywords:
        text = re.sub(f"(?i){kw}", lambda m: f"<span class='highlight'>{m.group(0)}</span>", text)
    return text


def annotate_shipments(results):
    now = datetime.now()
    for item in results:
        logs = item.get("logisticsInfors", [])
        if logs:
            try:
                latest_log = logs[0]
                latest_time = datetime.strptime(latest_log["nodeTime"], "%Y-%m-%d %H:%M:%S")
                item["last_update"] = latest_log["nodeTime"]
                item["days_stale"] = (now - latest_time).days
                item["latest_desc"] = latest_log.get("nodeDesc", "")
            except Exception:
                item["last_update"] = "解析失败"
                item["days_stale"] = -1
                item["latest_desc"] = ""
        else:
            item["last_update"] = "无记录"
            item["days_stale"] = -1
            item["latest_desc"] = ""

        item["eta_within_3_days"] = is_eta_within_days(item, days=3)

    results.sort(key=lambda x: (x['days_stale'] if x['days_stale'] >= 0 else -9999), reverse=True)
    return results


def calculate_heatmap_data(results, inspection_items):
    """计算热力图数据：按客户/国家/渠道统计"""
    heatmap_data = {
        'by_customer': {},
        'by_country': {},
        'by_channel': {},
        'customer_country': {}  # 客户-国家交叉统计
    }
    
    # 统计查验运单
    inspection_tracking_numbers = set(inspection_items.keys())
    
    for item in results:
        customer = item.get('customer', '未知客户')
        country = item.get('deliveryCountry', {}).get('name', '未知国家')
        channel = item.get('channel', '未知渠道')
        tracking_number = item.get("tracking_number") or item.get("odd") or ""
        
        is_inspection = tracking_number in inspection_tracking_numbers
        days_stale = item.get('days_stale', 0)
        
        # 按客户统计
        if customer not in heatmap_data['by_customer']:
            heatmap_data['by_customer'][customer] = {
                'total': 0,
                'inspection': 0,
                'stale_7': 0,  # 超过7天未更新
                'stale_14': 0  # 超过14天未更新
            }
        heatmap_data['by_customer'][customer]['total'] += 1
        if is_inspection:
            heatmap_data['by_customer'][customer]['inspection'] += 1
        if days_stale > 7:
            heatmap_data['by_customer'][customer]['stale_7'] += 1
        if days_stale > 14:
            heatmap_data['by_customer'][customer]['stale_14'] += 1
        
        # 按国家统计
        if country not in heatmap_data['by_country']:
            heatmap_data['by_country'][country] = {
                'total': 0,
                'inspection': 0,
                'stale_7': 0,
                'stale_14': 0
            }
        heatmap_data['by_country'][country]['total'] += 1
        if is_inspection:
            heatmap_data['by_country'][country]['inspection'] += 1
        if days_stale > 7:
            heatmap_data['by_country'][country]['stale_7'] += 1
        if days_stale > 14:
            heatmap_data['by_country'][country]['stale_14'] += 1
        
        # 按渠道统计
        if channel not in heatmap_data['by_channel']:
            heatmap_data['by_channel'][channel] = {
                'total': 0,
                'inspection': 0,
                'stale_7': 0,
                'stale_14': 0
            }
        heatmap_data['by_channel'][channel]['total'] += 1
        if is_inspection:
            heatmap_data['by_channel'][channel]['inspection'] += 1
        if days_stale > 7:
            heatmap_data['by_channel'][channel]['stale_7'] += 1
        if days_stale > 14:
            heatmap_data['by_channel'][channel]['stale_14'] += 1
        
        # 客户-国家交叉统计
        key = f"{customer}|{country}"
        if key not in heatmap_data['customer_country']:
            heatmap_data['customer_country'][key] = {
                'customer': customer,
                'country': country,
                'total': 0,
                'inspection': 0,
                'stale_7': 0,
                'stale_14': 0
            }
        heatmap_data['customer_country'][key]['total'] += 1
        if is_inspection:
            heatmap_data['customer_country'][key]['inspection'] += 1
        if days_stale > 7:
            heatmap_data['customer_country'][key]['stale_7'] += 1
        if days_stale > 14:
            heatmap_data['customer_country'][key]['stale_14'] += 1
    
    return heatmap_data


def generate_html_report(results, output_file="stales.html"):
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # 获取唯一的承运商列表
    carriers = sorted({item.get('carrier', '') for item in results if item.get('carrier', '')})
    
    config = load_config()
    channel_filters = config.get('channel_filters', {})

    # 客户名去重排序
    customers = sorted({item.get('customer', '') for item in results if item.get('customer', '')})
    # 国家名去重排序，deliveryCountry.name 字段，防止空值
    countries = sorted({item.get('deliveryCountry', {}).get('name', '') for item in results if item.get('deliveryCountry', {}).get('name', '')})
    channels = sorted({item.get('channel', '') for item in results if item.get('channel', '')})
    
    # 读取查验信息并计算统计信息（需要在HTML生成之前完成）
    try:
        with open("data/inspection.json", "r", encoding="utf-8") as f:
            inspection_items = json.load(f)
    except FileNotFoundError:
        inspection_items = {}
    
    # 计算查验统计信息
    inspection_stats = {
        'total': 0,
        'domestic': 0,
        'overseas': 0,
        'over_14_days': 0,
        'total_days': 0,
        'avg_days': 0
    }
    
    for tracking_number, info in inspection_items.items():
        inspection_stats['total'] += 1
        location = info.get('location', '')
        if location == '国内':
            inspection_stats['domestic'] += 1
        elif location == '国外':
            inspection_stats['overseas'] += 1
        
        start_time = info.get('start_time', '')
        if start_time:
            try:
                start_date = datetime.strptime(start_time, "%Y-%m-%d")
                now = datetime.now()
                days = (now - start_date).days
                if days >= 0:
                    inspection_stats['total_days'] += days
                    if days >= 14:
                        inspection_stats['over_14_days'] += 1
            except ValueError:
                pass
    
    if inspection_stats['total'] > 0:
        inspection_stats['avg_days'] = round(inspection_stats['total_days'] / inspection_stats['total'], 1)
    
    # 计算热力图数据
    try:
        heatmap_data = calculate_heatmap_data(results, inspection_items)
        # 将热力图数据转换为 JSON 字符串（在 HTML 生成之前，转义特殊字符）
        heatmap_data_json = json.dumps(heatmap_data, ensure_ascii=False).replace('</script>', '<\\/script>')
    except Exception as e:
        print(f"计算热力图数据时出错: {e}")
        heatmap_data_json = '{}'  # 使用空对象作为默认值
    
    html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8" />
    <title>运单轨迹报告</title>
    <link href="css/common/bootstrap.min.css" rel="stylesheet" />
    <link href="css/common/bootstrap-icons.min.css" rel="stylesheet" />
    <link href="css/stales.css" rel="stylesheet" />
    <link rel="icon" href="img/stale_favicon.png" type="image/png">
    <!-- Chart.js 图表库 -->
    <script src="js/common/chart.umd.min.js"></script>
</head>
<body>
<div class="container mt-4">
    <div class="page-header mb-4">
        <h3 class="page-title">
            <i class="bi bi-clipboard-data"></i> 运单轨迹报告
        </h3>
        <p class="page-subtitle">
            <i class="bi bi-clock"></i> 生成时间: {now_str}
        </p>
    </div>
    
    <!-- 查验统计信息面板 -->
    {f'<div class="alert alert-info mb-3" id="inspectionStatsPanel">' + 
     f'<div class="row text-center">' +
     f'<div class="col-md-2"><strong><i class="bi bi-shield-exclamation"></i> 查验总数</strong><br>' +
     f'<span class="badge bg-danger fs-6">{inspection_stats["total"]}</span></div>' +
     f'<div class="col-md-2"><strong><i class="bi bi-c-circle"></i> 国内查验</strong><br>' +
     f'<span class="badge bg-warning text-dark fs-6">{inspection_stats["domestic"]}</span></div>' +
     f'<div class="col-md-2"><strong><i class="bi bi-globe"></i> 国外查验</strong><br>' +
     f'<span class="badge bg-info fs-6">{inspection_stats["overseas"]}</span></div>' +
     f'<div class="col-md-2"><strong><i class="bi bi-exclamation-triangle"></i> 超过14天</strong><br>' +
     f'<span class="badge bg-danger fs-6">{inspection_stats["over_14_days"]}</span></div>' +
     f'<div class="col-md-2"><strong><i class="bi bi-calendar-range"></i> 平均天数</strong><br>' +
     f'<span class="badge bg-secondary fs-6">{inspection_stats["avg_days"]}天</span></div>' +
     f'<div class="col-md-2"><button class="btn btn-sm btn-outline-primary" onclick="filterTable(\'inspection\')">' +
     f'<i class="bi bi-filter"></i> 仅显示查验</button></div>' +
     f'</div></div>' if inspection_stats['total'] > 0 else ''}
    
    <!-- 热力图区域 -->
    <div class="card mb-4">
        <div class="card-header">
            <h5 class="mb-0">
                <i class="bi bi-diagram-3"></i> 数据热力图
                <button class="btn btn-sm btn-outline-secondary float-end" type="button" data-bs-toggle="collapse" data-bs-target="#heatmapCollapse">
                    <i class="bi bi-chevron-down"></i> 展开/收起
                </button>
            </h5>
        </div>
        <div class="collapse" id="heatmapCollapse">
            <div class="card-body">
                <!-- 热力图类型选择 -->
                <div class="mb-3">
                    <div class="btn-group" role="group">
                        <input type="radio" class="btn-check" name="heatmapType" id="heatmapTotal" value="total" checked>
                        <label class="btn btn-outline-primary" for="heatmapTotal">总运单数</label>
                        
                        <input type="radio" class="btn-check" name="heatmapType" id="heatmapInspection" value="inspection">
                        <label class="btn btn-outline-primary" for="heatmapInspection">查验运单</label>
                        
                        <input type="radio" class="btn-check" name="heatmapType" id="heatmapStale7" value="stale_7">
                        <label class="btn btn-outline-primary" for="heatmapStale7">超过7天未更新</label>
                        
                        <input type="radio" class="btn-check" name="heatmapType" id="heatmapStale14" value="stale_14">
                        <label class="btn btn-outline-primary" for="heatmapStale14">超过14天未更新</label>
                    </div>
                </div>
                
                <!-- 热力图维度选择 -->
                <div class="mb-3">
                    <div class="btn-group" role="group">
                        <input type="radio" class="btn-check" name="heatmapDimension" id="heatmapByCustomer" value="customer" checked>
                        <label class="btn btn-outline-secondary" for="heatmapByCustomer">按客户</label>
                        
                        <input type="radio" class="btn-check" name="heatmapDimension" id="heatmapByCountry" value="country">
                        <label class="btn btn-outline-secondary" for="heatmapByCountry">按国家</label>
                        
                        <input type="radio" class="btn-check" name="heatmapDimension" id="heatmapByChannel" value="channel">
                        <label class="btn btn-outline-secondary" for="heatmapByChannel">按渠道</label>
                        
                        <input type="radio" class="btn-check" name="heatmapDimension" id="heatmapCustomerCountry" value="customer_country">
                        <label class="btn btn-outline-secondary" for="heatmapCustomerCountry">客户×国家</label>
                    </div>
                </div>
                
                <!-- 热力图容器 -->
                <div id="heatmapContainer" style="min-height: 400px; position: relative;">
                    <canvas id="heatmapChart"></canvas>
                </div>
            </div>
        </div>
    </div>
    
    <div class="filter-buttons mb-3">
        <button class="btn btn-outline-secondary btn-sm" onclick="filterTable('all')">
            <i class="bi bi-list-ul"></i> 全部
        </button>
        <button class="btn btn-outline-warning btn-sm" onclick="filterTable('7')">
            <i class="bi bi-exclamation-triangle"></i> 超过7天未更新
        </button>
        <button class="btn btn-outline-danger btn-sm" onclick="filterTable('14')">
            <i class="bi bi-exclamation-circle"></i> 超过14天未更新
        </button>
        <button class="btn btn-outline-info btn-sm" onclick="filterTable('warehouse')">
            <i class="bi bi-box-seam"></i> 未更新
        </button>
        <button class="btn btn-outline-success btn-sm" onclick="filterTable('eta3')">
            <i class="bi bi-ship"></i> 3天内到港
        </button>
        {f'<button class="btn btn-outline-danger btn-sm" onclick="filterTable(\'inspection14\')">' +
         f'<i class="bi bi-shield-exclamation"></i> 查验超过14天</button>' if inspection_stats['over_14_days'] > 0 else ''}
    </div>
    
    <div class="d-flex mb-3 gap-3">

    <!-- 客户筛选 -->
    <div class="col-md-2">
        <div class="form-floating">
            <select id="customerFilter" class="form-select" onchange="filterAll()">
            <option value="">全部客户</option>"""
    for c in customers:
        html += f'<option value="{c}">{c}</option>'
    html += """
        </select>
            <label><i class="bi bi-person"></i> 客户筛选</label>
        </div>
    </div>
    <!-- 承运商筛选 -->
    <div class="col-md-2">
        <div class="form-floating">
            <select id="carrierFilter" class="form-select" onchange="filterAll()">
            <option value="">全部承运商</option>"""
    for carrier in carriers:
        html += f'<option value="{carrier}">{carrier}</option>'
    html += """
            </select>
            <label><i class="bi bi-truck"></i> 承运商</label>
        </div>
    </div>
    <!-- 国家筛选 -->
    <div class="col-md-2">
        <div class="form-floating">
            <select id="countryFilter" class="form-select" onchange="filterAll()">
            <option value="">全部国家</option>"""
    for co in countries:
        html += f'<option value="{co}">{co}</option>'
    html += """
        </select>
            <label><i class="bi bi-globe"></i> 国家筛选</label>
        </div>
    </div>
    <!-- 渠道筛选 -->
    <div class="col-md-2">
        <div class="form-floating">
            <select id="channelFilter" class="form-select" onchange="filterAll()">
                <option value="">全部渠道</option>
                <option value="all_channels">所有运输方式</option>"""
    
    # 添加配置的渠道筛选选项
    for filter_name, channels in channel_filters.items():
        channel_list = ",".join(channels)
        html += f'<option value="{channel_list}">{filter_name}</option>'
    
    # 添加单独渠道选项（从实际数据中获取）
    unique_channels = sorted({item.get('channel', '') for item in results if item.get('channel', '')})
    html += f'<option value="=====">''=====''</option>'
    for channel in unique_channels:
        html += f'<option value="{channel}">{channel}</option>'
    
    html += """
            </select>
            <label><i class="bi bi-diagram-3"></i> 渠道</label>
        </div>
    </div>
    </div>
    <div class="d-flex mb-3 gap-3"> 
        <!-- 问题件筛选 -->
    <div class="col-md-2">
        <div class="form-floating">
            <select class="form-select form-select" id="problemFilter" onchange="filterAll() ">
                <option value="all">所有运单</option>
                <option value="normal" selected>非问题件</option>
                <option value="problem">问题件</option>
            </select>
            <label><i class="bi bi-exclamation-octagon"></i> 问题件筛选</label>
        </div>
    </div>
    <!-- 状态筛选 -->
    <div class="col-md-2">
        <div class="form-floating">
            <select class="form-select form-select" id="statusFilter" onchange="filterAll() ">
                <option value="">所有状态</option>
                <option value="转运中">转运中</option>
                <option value="已签收">已签收</option>
                <option value="查验">查验</option>
            </select>
            <label><i class="bi bi-flag"></i> 状态筛选</label>
        </div>
    </div>
    <!-- 查验地点筛选 -->
    <div class="col-md-2">
        <div class="form-floating">
            <select class="form-select form-select" id="inspectionLocationFilter" onchange="filterAll() ">
                <option value="">所有查验地点</option>
                <option value="国内">国内</option>
                <option value="国外">国外</option>
            </select>
            <label><i class="bi bi-geo-alt"></i> 查验地点</label>
        </div>
    </div>
    </div>
    <!-- 查询区域 -->
    <div class="search-section d-flex align-items-end gap-3 mb-3">
        <!-- 运单号查询 -->
        <div class="tracking-search d-flex align-items-center gap-2">
            <label for="trackingSearchInput" class="form-label mb-0">
                <i class="bi bi-search"></i> 运单号查询
            </label>
            <div class="input-group" style="width: auto;">
                <span class="input-group-text"><i class="bi bi-upc-scan"></i></span>
                <input type="text" id="trackingSearchInput" 
                       placeholder="输入运单号，多个用空格分隔" 
                       class="form-control form-control-sm"
                       style="min-width: 250px;">
                <button class="btn btn-outline-primary" onclick="filterByTrackingNumbers()">
                    <i class="bi bi-search"></i> 查询
                </button>
            </div>
        </div>
        <!-- 轨迹查询 -->
        <div class="filter-track d-flex align-items-center gap-2">
            <label class="form-label mb-0">
                <i class="bi bi-list-check"></i> 轨迹查询
            </label>
            <div class="input-group" style="width: 300px;">
                <span class="input-group-text"><i class="bi bi-funnel"></i></span>
                <input type="text" id="trackFilterInput" oninput="debouncedFilterAll()" 
                       class="form-control form-control-sm" 
                       placeholder="搜索轨迹信息...">
            </div>
        </div>
        <!-- 结果数量提示 -->
        <div class="result-count-info ms-auto">
            <span class="badge bg-info text-white" id="resultCountBadge">
                <i class="bi bi-list-ul"></i> 共 <span id="resultCount">0</span> 条结果
            </span>
        </div>
    </div>
    <!-- 悬浮按钮组 -->
    <div class="floating-buttons">
        <!-- 清除选择按钮 -->
        <button id="clearBtn" class="floating-action-btn floating-clear-btn" onclick="clearAllSelections()" data-bs-toggle="tooltip" data-bs-placement="left" title="清除所有选择">
            <i class="bi bi-x-circle"></i>
        </button>
        <!-- 复制按钮 -->
        <button id="copyBtn" class="floating-action-btn floating-copy-btn" onclick="copySelectedTrackingNumbers()" data-bs-toggle="tooltip" data-bs-placement="left" title="复制选中运单号">
            <i id="copy-icon" class="bi bi-clipboard"></i>
            <span id="copy-count" class="copy-count-badge">0</span>
        </button>
    </div>
    <br/>
    <table class="table table-bordered table-hover" id="logisticsTable">
        <thead class="table-light">
            <tr>
                <th style="width: 50px"><input type="checkbox" class="form-check-input" id="selectAll" onclick="toggleSelectAll(this)" title="只选中当前筛选条件下可见的运单"></th>
                <th style="width: 120px"><i class="bi bi-upc"></i> 运单号</th>
                <th style="width: 100px"><i class="bi bi-person"></i> 客户名</th>
                <th style="width: 100px"><i class="bi bi-diagram-3"></i> 渠道</th>
                <th style="width: 100px"><i class="bi bi-truck"></i> 承运商</th>
                <th style="width: 100px"><i class="bi bi-calendar-x"></i> 未更新天数</th>
                <th style="width: 100px"><i class="bi bi-flag"></i> 状态</th>
                <th style="width: 100px"><i class="bi bi-globe"></i> 目的国</th>
                <th style="width: 500px; min-width: 400px"><i class="bi bi-list-check"></i> 轨迹</th>
                <th style="width: 100px"><i class="bi bi-info-circle"></i> 备注</th>
            </tr>
        </thead>
        <tbody>
    """

    status_map = {
        "2": "转运中",
        "3": "已签收"
    }
    
    with open("data/problem_items.json", "r", encoding="utf-8") as f:
        problem_items = json.load(f)

    for item in results:
        tracking_number = item.get("tracking_number") or item.get("odd") or ""
        problem_reason = problem_items.get(tracking_number)
        problem_class = "problem-item" if tracking_number in problem_items else ""
        days = item.get("days_stale")
        latest_desc = item.get("latest_desc", "")
        delivery_country = item.get("deliveryCountry", {}).get("name", "")
        customer = item.get("customer", "")
        status_code = item.get("status", 0)
        status = status_map.get(status_code, str(status_code))
        
        # 检查是否为查验状态
        inspection_info = inspection_items.get(tracking_number)
        if inspection_info:
            status = "查验"
            inspection_location = inspection_info.get("location", "")
            inspection_start_time = inspection_info.get("start_time", "")
            # 计算查验天数
            inspection_days = -1
            if inspection_start_time:
                try:
                    start_date = datetime.strptime(inspection_start_time, "%Y-%m-%d")
                    now = datetime.now()
                    inspection_days = (now - start_date).days
                except ValueError:
                    inspection_days = -1
        else:
            inspection_location = ""
            inspection_start_time = ""
            inspection_days = -1
        
        row_class = ""
        if isinstance(days, int):
            if days > 14:
                row_class = "very-stale"
            elif days > 7:
                row_class = "stale-row"

        track_logs = item.get("logisticsInfors", [])
        short_logs = track_logs[:2]
        remaining_logs = track_logs[2:]
        
        short_html = "<br>".join([
            highlight_keywords(f"{log.get('nodeTime', '')} - {log.get('nodeDesc', '')}")
            for log in short_logs
        ])
        
        hidden_html = "<br>".join([
            highlight_keywords(f"{log.get('nodeTime', '')} - {log.get('nodeDesc', '')}")
            for log in remaining_logs
        ])
        
        expand_id = f"collapse_{item.get('odd')}"
        button_html = ""
        if remaining_logs:
            button_html = f'''
                <button class="btn btn-sm btn-link p-0" type="button" data-bs-toggle="collapse" data-bs-target="#{expand_id}" aria-expanded="false" aria-controls="{expand_id}">
                    展开更多
                </button>
            '''
        
        track_cell = f'''
            <div class="track-content">
            {short_html}<br>{button_html}
            <div class="collapse mt-1" id="{expand_id}">
                {hidden_html}
            </div>
            </div>
        '''

        track_text = " ".join([
            f"{log.get('nodeTime', '')} {log.get('nodeDesc', '')}"
            for log in item.get("logisticsInfors", [])
        ]).replace('"', '&quot;')

        eta_flag = 1 if item.get("eta_within_3_days") else 0
        is_warehouse = 1 if latest_desc == 'Your goods are in the warehouse' else 0
        tracking_number = item.get("tracking_number") or item.get("odd") or ""
        problem_reason = problem_items.get(tracking_number)

        if problem_reason:
            problem_badge = f'<span class="badge rounded-pill text-bg-info ms-2" title="{problem_reason}"><i class="bi bi-exclamation-octagon"></i> 问题件</span>'
        else:
            problem_badge = ''
        # 根据未更新天数设置badge颜色
        if not isinstance(days, int):
            badge_class = "bg-secondary"
            days_display = "-"
        elif days <= 1:
            badge_class = "bg-success"  # 绿色，更新及时
            days_display = str(days)
        elif days <= 3:
            badge_class = "bg-primary"  # 蓝色，正常
            days_display = str(days)
        elif days <= 7:
            badge_class = "bg-warning text-dark"  # 黄色，提醒
            days_display = str(days)
        elif days <= 14:
            badge_class = "bg-danger"  # 红色，比较严重
            days_display = str(days)
        else:
            badge_class = "bg-dark"  # 深色，严重超时
            days_display = str(days)
        # 根据状态添加图标和样式
        if status == '已签收':
            status_html = f'<span class="badge bg-success"><i class="bi bi-check-circle"></i> {status}</span>'
        elif status == '查验':
            # 计算查验天数显示
            if inspection_days >= 0:
                days_text = f"（{inspection_days}天）"
            else:
                days_text = ""
            # tooltip显示详细信息
            tooltip_text = f"查验地点：{inspection_location or '未知'}"
            if inspection_start_time:
                tooltip_text += f"<br>开始时间：{inspection_start_time}"
            if inspection_days >= 0:
                tooltip_text += f"<br>查验天数：{inspection_days}天"
            
            # 根据查验地点选择图标
            if inspection_location == "国内":
                inspection_icon = "bi-c-circle"  # 建筑图标表示国内
            elif inspection_location == "国外":
                inspection_icon = "bi-globe"  # 地球图标表示国外
            else:
                inspection_icon = "bi-shield-exclamation"  # 默认图标
            
            # 根据查验地点和天数设置颜色
            # 国内：少于14天浅红色，大于等于14天深红色
            # 国外：少于14天浅红色，大于等于14天深红色
            if inspection_days >= 14:
                # 大于等于14天：深红色
                if inspection_location == "国内":
                    badge_color = "background-color: #c82333;"  # 深红色
                elif inspection_location == "国外":
                    badge_color = "background-color: #bd2130;"  # 稍深的红色
                else:
                    badge_color = "background-color: #c82333;"  # 默认深红色
            elif inspection_days >= 0:
                # 少于14天：浅红色
                if inspection_location == "国内":
                    badge_color = "background-color: #ff6b6b;"  # 浅红色
                elif inspection_location == "国外":
                    badge_color = "background-color: #ff8787;"  # 稍浅的红色
                else:
                    badge_color = "background-color: #ff6b6b;"  # 默认浅红色
            else:
                # 无法计算天数：使用默认深红色
                badge_color = "background-color: #dc3545;"
            
            status_html = f'<span class="badge" style="{badge_color} color: white;" data-bs-toggle="tooltip" data-bs-placement="top" data-bs-html="true" title="{tooltip_text}"><i class="bi {inspection_icon}"></i> 查验{days_text}</span>'
        else:
            status_html = f'<span class="badge bg-warning text-dark"><i class="bi bi-arrow-repeat"></i> {status}</span>'
        
        html += f"""
            <tr class="{row_class}{problem_class}" data-days="{days if isinstance(days, int) else 0 }" 
                data-warehouse="{is_warehouse}" 
                data-eta3="{eta_flag}"
                data-customer="{customer}"
                data-country="{delivery_country}"
                data-channel="{item.get('channel', '')}"
                data-carrier="{item.get('carrier', '')}"
                data-track="{track_text}"
                data-problem="{'1' if tracking_number in problem_items else '0'}"
                data-status="{status}"
                data-inspection-location="{inspection_location}"
                data-inspection-start-time="{inspection_start_time}"
                data-inspection-days="{inspection_days}"
                >
                <td><input type="checkbox" class="tracking-checkbox form-check-input" value="{tracking_number}"></td>
                <td><strong>{item.get('odd')}</strong></td>
                <td>{customer}</td>
                <td><span class="badge bg-secondary">{item.get('channel', '')}</span></td>
                <td><span class="badge bg-light text-dark">{item.get('carrier', '')}</span></td>
                <td><span class="badge {badge_class}" data-bs-toggle="tooltip" data-bs-placement="top" title="{item.get('last_update', '')}">{days_display}</span></td>
                <td>{status_html}</td>
                <td><i class="bi bi-geo-alt"></i> {delivery_country}</td>
                <td>{track_cell}</td>
                <td>{problem_badge}</td>
            </tr>
        """

    html += """
        </tbody>
    </table>
    
    <!-- 分页控件 -->
    <div class="pagination-container">
        <div class="pagination-info">
            <div class="page-size-selector">
                <label for="pageSizeSelect">
                    <i class="bi bi-list-columns"></i> 每页显示:
                </label>
                <select id="pageSizeSelect" class="form-select form-select-sm" onchange="changePageSize()" style="width: 100px;">
                    <option value="10" selected>10</option>
                    <option value="30">30</option>
                    <option value="50">50</option>
                    <option value="100">100</option>
                    <option value="200">200</option>
                    <option value="500">500</option>
                </select>
            </div>
            <span id="paginationInfo" class="text-muted">
                <i class="bi bi-info-circle"></i> 显示 0-0 条，共 0 条
            </span>
        </div>
        <nav>
            <ul class="pagination pagination-sm mb-0" id="pagination">
                <!-- 分页按钮将通过JavaScript动态生成 -->
            </ul>
        </nav>
    </div>
</div>

<!-- Toast 提示框 -->
<div class="position-fixed top-0 start-50 translate-middle-x" style="z-index: 9999; margin-top: 20px;">
    <div id="copyToast" class="custom-toast" role="alert" aria-live="assertive" aria-atomic="true" style="display: none;">
        <div class="custom-toast-content">
            <div class="custom-toast-icon" id="toastIcon"></div>
            <span id="toastMessage" class="custom-toast-message"></span>
        </div>
    </div>
</div>
"""
    
    # 使用 f-string 添加热力图数据和脚本（必须在普通字符串结束后）
    html += f"""
<!-- 热力图数据 -->
<script>
    window.heatmapData = {heatmap_data_json};
</script>

<script src="js/common/bootstrap.bundle.min.js"></script>
<script src="js/common.js"></script>
<script src="js/stales/stales.js"></script>
<script src="js/stales/heatmap.js"></script>
</body>
</html>"""

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"HTML报告已生成: {output_file}")


if __name__ == "__main__":
    print("开始查询和分析运单轨迹...")

    config = load_config()
    tracking_list = load_tracking_numbers()
    print(f"共读取 {len(tracking_list)} 个运单号")

    logistics_data = query_logistics_api(tracking_list, base_url=config["base_url"])
    full_data = annotate_shipments(logistics_data)
    generate_html_report(full_data)

    print("处理完成！")
