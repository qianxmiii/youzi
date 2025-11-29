import json
import requests
from datetime import datetime, timedelta
import re


def load_config(filename='config.json'):
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


def load_tracking_numbers(filename='tracking_numbers.json'):
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
    
    html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8" />
    <title>运单轨迹报告</title>
    <link href="css/common/bootstrap.min.css" rel="stylesheet" />
    <link href="css/common/bootstrap-icons.min.css" rel="stylesheet" />
    <link rel="icon" href="img/stale_favicon.png" type="image/png">
    <style>
        .very-stale {{ background-color: #ffcdd2; }}
        .stale-row {{ background-color: #fff9c4; }}
        .badge {{ font-size: 12px; }}
        .filter-buttons button, .filter-customer select {{
            margin-right: 5px; margin-bottom: 10px;
        }}
        .filter-customer label {{
            margin-right: 5px;
        }}
        .highlight {{
            background-color: yellow;
            font-weight: bold;
        }}
        body {{
            font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
            background-color: #f9f9fb;
            color: #333;
        }}

        h2 {{
            margin-top: 20px;
            font-weight: 600;
            color: #2c3e50;
        }}

        .container {{
            background-color: #fff;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
            padding: 25px;
        }}

        .filter-buttons button,
        .filter-customer select,
        .filter-track input {{
            margin: 5px 8px 15px 0;
        }}

        .filter-track input {{
            padding: 5px 10px;
            border: 1px solid #ccc;
            border-radius: 5px;
            width: 250px;
        }}

        table.table {{
            border-radius: 6px;
            overflow: hidden;
        }}

        table th {{
            background-color: #f0f3f5;
            text-align: center;
        }}

        table td {{
            vertical-align: middle;
            font-size: 14px;
        }}

        .very-stale {{
            background-color: #fbeaea !important;
        }}

        .stale-row {{
            background-color: #fff6e0 !important;
        }}

        .badge {{
            font-size: 12px;
            padding: 4px 8px;
        }}

        .highlight {{
            background-color: #ffff80;
            font-weight: bold;
            padding: 0 2px;
            border-radius: 3px;
        }}
        td.unupdated-days {{
           width: 100px;
           text-align: center;
           font-weight: 600;
           color: #444;
           font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
           font-size: 14px;
           background-color: #f0f8ff;
           border-radius: 4px;
           padding: 5px 8px;
           white-space: nowrap;
         }}
         td.unupdated-days.low {{
           color: #2a9d8f;
         }}
         td.unupdated-days.medium {{
           color: #e9c46a;
           font-weight: 700;
         }}
         td.unupdated-days.high {{
           color: #e76f51;
           font-weight: 900;
         }}
         
         /* 问题件强调样式 */
         tr.problem-item {{
             border-left: 3px solid #ffc107;
         }}
         
         /* 分页样式 */
         .pagination-container {{
             display: flex;
             justify-content: space-between;
             align-items: center;
             margin-top: 20px;
             padding: 15px;
             background-color: #f8f9fa;
             border-radius: 6px;
         }}
         .pagination-info {{
             display: flex;
             align-items: center;
             gap: 15px;
         }}
         .pagination {{
             margin: 0;
         }}
         .page-size-selector {{
             display: flex;
             align-items: center;
             gap: 8px;
         }}
         .page-size-selector label {{
             margin: 0;
             white-space: nowrap;
         }}
         .page-size-selector select {{
             width: auto;
             padding: 5px 10px;
         }}
    </style>
</head>
<body>
<div class="container mt-4">
    <h3>运单轨迹报告</h3>
    <p>生成时间: {now_str}</p>
    
    <div class="filter-buttons mb-2">
        <button class="btn btn-outline-secondary btn-sm" onclick="filterTable('all')">✅全部</button>
        <button class="btn btn-outline-warning btn-sm" onclick="filterTable('7')">超过7天未更新</button>
        <button class="btn btn-outline-danger btn-sm" onclick="filterTable('14')">🚨超过14天未更新</button>
        <button class="btn btn-outline-info btn-sm" onclick="filterTable('warehouse')">📦未更新</button>
        <button class="btn btn-outline-success btn-sm" onclick="filterTable('eta3')">🛳️3天内到港</button>
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
            <label>客户筛选</label>
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
            <label>承运商</label>
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
            <label>国家筛选</label>
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
            <label>渠道</label>
        </div>
    </div>
    </div>
    <div class="d-flex mb-3 gap-3"> 
        <!-- 问题件筛选 -->
    <div class="col-md-2">
        <div class="form-floating">
            <select class="form-select form-select" id="problemFilter" onchange="filterAll() ">
                <option value="all">所有运单</option>
                <option value="normal">非问题件</option>
                <option value="problem">问题件</option>
            </select>
            <label>问题件筛选</label>
        </div>
    </div>
    <!-- 状态筛选 -->
    <div class="col-md-2">
        <div class="form-floating">
            <select class="form-select form-select" id="statusFilter" onchange="filterAll() ">
                <option value="">所有状态</option>
                <option value="转运中">转运中</option>
                <option value="已签收">已签收</option>
            </select>
            <label>状态筛选</label>
        </div>
    </div>
    </div>
    <!-- 运单号查询 -->
    <div class="tracking-search d-flex align-items-center gap-2 mb-5">
        <label for="trackingSearchInput" class="form-label mb-0">运单号查询</label>
        <input type="text" id="trackingSearchInput" 
               placeholder="输入运单号，多个用空格分隔" 
               class="form-control form-control-sm w-auto"
               style="min-width: 250px;">
        <button class="btn btn-outline-primary" onclick="filterByTrackingNumbers()">查询</button>
    </div>
    <div class="filter-track flex-grow-1">
        <label>轨迹查询</label>
        <input type="text" id="trackFilterInput" oninput="filterAll()" class="form-control form-control-sm" style="width: 300px; display: inline-block;">
    </div>
    <div class="mt-3">
        <button id="copyBtn" class="btn btn-outline-dark" onclick="copySelectedTrackingNumbers()" data-bs-toggle="tooltip" data-bs-placement="top" title="">
            <i id="copy-icon" class="bi bi-clipboard"></i> 复制选中运单号
        </button>
    </div>
    <br/>
    <table class="table table-bordered table-hover" id="logisticsTable">
        <thead class="table-light">
            <tr>
                <th><input type="checkbox" class="form-check-input" id="selectAll" onclick="toggleSelectAll(this)" title="只选中当前筛选条件下可见的运单"></th>
                <th>运单号</th>
                <th>客户名</th>
                <th>渠道</th>
                <th>承运商</th>
                <th>最后更新时间</th>
                <th>未更新天数</th>
                <th>状态</th>
                <th>目的国</th>
                <th>轨迹</th>
                <th>备注</th>
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
            problem_badge = f'<span class="badge rounded-pill text-bg-info ms-2" title="{problem_reason}">问题件</span>'
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
                >
                <td><input type="checkbox" class="tracking-checkbox form-check-input" value="{tracking_number}"></td>
                <td>{item.get('odd')}</td>
                <td>{customer}</td>
                <td>{item.get('channel', '')}</td>
                <td>{item.get('carrier', '')}</td>
                <td>{item.get('last_update', '')}</td>
                <td><span class="badge {badge_class}">{days_display}</span></td>
                <td>{status}</td>
                <td>{delivery_country}</td>
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
                <label for="pageSizeSelect">每页显示:</label>
                <select id="pageSizeSelect" class="form-select form-select-sm" onchange="changePageSize()" style="width: auto;">
                    <option value="20" selected>20</option>
                    <option value="50">50</option>
                    <option value="100">100</option>
                    <option value="200">200</option>
                    <option value="500">500</option>
                </select>
            </div>
            <span id="paginationInfo" class="text-muted">显示 0-0 条，共 0 条</span>
        </div>
        <nav>
            <ul class="pagination pagination-sm mb-0" id="pagination">
                <!-- 分页按钮将通过JavaScript动态生成 -->
            </ul>
        </nav>
    </div>
</div>
<script src="js/common/bootstrap.bundle.min.js"></script>
<script>
// 显示工具提示的辅助函数
function showTooltip(message, duration=2000) {
    const btn = document.getElementById('copyBtn');
    let tooltip = bootstrap.Tooltip.getInstance(btn);
    
    if (!tooltip) {
        tooltip = new bootstrap.Tooltip(btn, {
            title: message,
            trigger: 'manual'
        });
    } else {
        tooltip.setContent({'.tooltip-inner': message});
    }
    
    tooltip.show();
    setTimeout(() => tooltip.hide(), duration);
}
function toggleSelectAll(source) {
    const allRows = document.querySelectorAll('#logisticsTable tbody tr');
    let hasVisible = false;
    
    allRows.forEach(row => {
        if (row.style.display !== 'none') {
            const checkbox = row.querySelector('.tracking-checkbox');
            checkbox.checked = source.checked;
            hasVisible = true;
        }
    });
    
    if (!hasVisible) {
        source.checked = false;
        showTooltip('没有可选的运单');
    }
}
function copySelectedTrackingNumbers() {
    const selected = [];
    document.querySelectorAll('.tracking-checkbox:checked').forEach(checkbox => {
        // 检查父行是否可见
        const row = checkbox.closest('tr');
        if (row.style.display !== 'none') {
            selected.push(checkbox.value);
        }
    });
    
    if (selected.length === 0) {
        showTooltip('请至少选择一个运单号');
        return;
    }
    
    const textToCopy = selected.join(' ');
    
    // 创建临时textarea元素
    const textarea = document.createElement('textarea');
    textarea.value = textToCopy;
    textarea.style.position = 'fixed';  // 防止页面滚动
    document.body.appendChild(textarea);
    textarea.select();
    
    try {
        const successful = document.execCommand('copy');
        var copyBtn = document.getElementById('copyBtn');
        var tooltip = bootstrap.Tooltip.getInstance(copyBtn);

        if (!tooltip) {
            tooltip = new bootstrap.Tooltip(copyBtn, {
                title: successful ? '复制成功!' : '复制失败',
                trigger: 'manual'
            });
        } else {
            tooltip.setContent({'.tooltip-inner': successful ? '复制成功!' : '复制失败'});
        }
        
        tooltip.show();

        if (successful) {
            // 获取图标元素
            const copyIcon = document.getElementById('copy-icon');

            // 改变图标为 bi-send-check
            copyIcon.classList.remove('bi-clipboard');
            copyIcon.classList.add('bi-check-all');

            // 2 秒后恢复图标为 bi-send
            setTimeout(() => {
                copyIcon.classList.remove('bi-check-all');
                copyIcon.classList.add('bi-clipboard');
                tooltip.hide();
            }, 2000);
        }

    } catch (err) {
        console.error('复制失败: ', err);
        alert('复制失败，请手动复制');
    } finally {
        document.body.removeChild(textarea);
    }
}
function filterTable(type) {
    var rows = document.querySelectorAll("#logisticsTable tbody tr");
    rows.forEach(row => {
        var days = parseInt(row.getAttribute("data-days"));
        var isWarehouse = row.getAttribute("data-warehouse") === '1';
        var eta3 = row.getAttribute("data-eta3") === '1';
        let shouldShow = false;
        if (type === "all") {
            shouldShow = true;
        } else if (type === "7") {
            shouldShow = (days > 7);
        } else if (type === "14") {
            shouldShow = (days > 14);
        } else if (type === "warehouse") {
            shouldShow = isWarehouse;
        } else if (type === "eta3") {
            shouldShow = eta3;
        }
        row.setAttribute('data-filtered', shouldShow ? 'true' : 'false');
    });
    // 重置客户和国家筛选
    document.getElementById("customerFilter").value = "";
    document.getElementById("countryFilter").value = "";
    document.getElementById("trackFilterInput").value = "";
    
    // 筛选后重置到第一页并更新分页
    currentPage = 1;
    displayPage();
    updatePagination();
}
function filterByTrackingNumbers() {
    const input = document.getElementById('trackingSearchInput').value.trim();
    if (!input) {
        filterAll();
        return;
    }
    
    const trackingNumbers = input.split(/\\s+/).map(num => num.trim());
    const rows = document.querySelectorAll('#logisticsTable tbody tr');
    
    rows.forEach(row => {
        const rowTrackingNumber = row.cells[1].textContent.trim(); // 运单号在第二列（索引1）
        const shouldShow = trackingNumbers.some(num => 
            rowTrackingNumber.includes(num));
        
        row.setAttribute('data-filtered', shouldShow ? 'true' : 'false');
    });
    
    // 筛选后重置到第一页并更新分页
    currentPage = 1;
    displayPage();
    updatePagination();
}

// 分页相关变量
let currentPage = 1;
let pageSize = 20;

// 获取所有应该显示的行（基于筛选条件）
function getFilteredRows() {
    const allRows = document.querySelectorAll('#logisticsTable tbody tr');
    return Array.from(allRows).filter(row => {
        // 检查行是否有data-filtered属性，如果没有则默认显示
        const filtered = row.getAttribute('data-filtered');
        return filtered !== 'false';
    });
}

// 更新分页显示
function updatePagination() {
    const filteredRows = getFilteredRows();
    const totalRows = filteredRows.length;
    const totalPages = Math.ceil(totalRows / pageSize);
    
    // 更新分页信息
    const start = totalRows === 0 ? 0 : (currentPage - 1) * pageSize + 1;
    const end = Math.min(currentPage * pageSize, totalRows);
    document.getElementById('paginationInfo').textContent = `显示 ${start}-${end} 条，共 ${totalRows} 条`;
    
    // 生成分页按钮
    const pagination = document.getElementById('pagination');
    pagination.innerHTML = '';
    
    if (totalPages <= 1) {
        return; // 如果只有一页或没有数据，不显示分页
    }
    
    // 上一页按钮
    const prevLi = document.createElement('li');
    prevLi.className = `page-item ${currentPage === 1 ? 'disabled' : ''}`;
    prevLi.innerHTML = `<a class="page-link" href="#" onclick="goToPage(${currentPage - 1}); return false;">上一页</a>`;
    pagination.appendChild(prevLi);
    
    // 页码按钮
    const maxButtons = 7; // 最多显示7个页码按钮
    let startPage = Math.max(1, currentPage - Math.floor(maxButtons / 2));
    let endPage = Math.min(totalPages, startPage + maxButtons - 1);
    
    if (endPage - startPage < maxButtons - 1) {
        startPage = Math.max(1, endPage - maxButtons + 1);
    }
    
    // 第一页
    if (startPage > 1) {
        const firstLi = document.createElement('li');
        firstLi.className = 'page-item';
        firstLi.innerHTML = `<a class="page-link" href="#" onclick="goToPage(1); return false;">1</a>`;
        pagination.appendChild(firstLi);
        
        if (startPage > 2) {
            const ellipsisLi = document.createElement('li');
            ellipsisLi.className = 'page-item disabled';
            ellipsisLi.innerHTML = '<span class="page-link">...</span>';
            pagination.appendChild(ellipsisLi);
        }
    }
    
    // 中间页码
    for (let i = startPage; i <= endPage; i++) {
        const li = document.createElement('li');
        li.className = `page-item ${i === currentPage ? 'active' : ''}`;
        li.innerHTML = `<a class="page-link" href="#" onclick="goToPage(${i}); return false;">${i}</a>`;
        pagination.appendChild(li);
    }
    
    // 最后一页
    if (endPage < totalPages) {
        if (endPage < totalPages - 1) {
            const ellipsisLi = document.createElement('li');
            ellipsisLi.className = 'page-item disabled';
            ellipsisLi.innerHTML = '<span class="page-link">...</span>';
            pagination.appendChild(ellipsisLi);
        }
        
        const lastLi = document.createElement('li');
        lastLi.className = 'page-item';
        lastLi.innerHTML = `<a class="page-link" href="#" onclick="goToPage(${totalPages}); return false;">${totalPages}</a>`;
        pagination.appendChild(lastLi);
    }
    
    // 下一页按钮
    const nextLi = document.createElement('li');
    nextLi.className = `page-item ${currentPage === totalPages ? 'disabled' : ''}`;
    nextLi.innerHTML = `<a class="page-link" href="#" onclick="goToPage(${currentPage + 1}); return false;">下一页</a>`;
    pagination.appendChild(nextLi);
}

// 跳转到指定页面
function goToPage(page) {
    const filteredRows = getFilteredRows();
    const totalPages = Math.ceil(filteredRows.length / pageSize);
    
    if (page < 1 || page > totalPages) {
        return;
    }
    
    currentPage = page;
    displayPage();
    updatePagination();
    
    // 滚动到表格顶部
    document.getElementById('logisticsTable').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// 显示当前页的数据
function displayPage() {
    const filteredRows = getFilteredRows();
    const start = (currentPage - 1) * pageSize;
    const end = start + pageSize;
    
    // 先隐藏所有行
    const allRows = document.querySelectorAll('#logisticsTable tbody tr');
    allRows.forEach(row => {
        row.style.display = 'none';
    });
    
    // 显示当前页的行
    filteredRows.forEach((row, index) => {
        if (index >= start && index < end) {
            row.style.display = '';
        }
    });
}

// 改变每页显示数量
function changePageSize() {
    const select = document.getElementById('pageSizeSelect');
    pageSize = parseInt(select.value);
    currentPage = 1; // 重置到第一页
    displayPage();
    updatePagination();
}

function filterAll() {
    document.getElementById('selectAll').checked = false; // 当筛选条件变化时，自动取消全选状态
    // 取消所有已选中的复选框（包括不可见的）
    document.querySelectorAll('.tracking-checkbox:checked').forEach(checkbox => {
        checkbox.checked = false;
    });

    const customerFilter = document.getElementById('customerFilter').value.toLowerCase();
    const countryFilter = document.getElementById('countryFilter').value.toLowerCase();
    const channelFilter = document.getElementById('channelFilter').value.toLowerCase();
    const carrierFilter = document.getElementById('carrierFilter').value.toLowerCase();
    const trackFilter = document.getElementById('trackFilterInput').value.toLowerCase();
    const problemFilter = document.getElementById('problemFilter').value;
    const statusFilter = document.getElementById('statusFilter').value;
    const channelFilterValue = document.getElementById('channelFilter').value;

    const rows = document.querySelectorAll('#logisticsTable tbody tr');
    rows.forEach(row => {
        const customer = row.getAttribute('data-customer').toLowerCase();
        const country = row.getAttribute('data-country').toLowerCase();
        const channel = row.getAttribute('data-channel').toLowerCase();
        const trackText = row.getAttribute('data-track').toLowerCase();
        const isProblem = row.getAttribute('data-problem') === '1';
        const rowStatus = row.getAttribute('data-status');
        const carrier = row.getAttribute('data-carrier').toLowerCase();

        // 综合所有筛选条件
        const showRow = 
            (customerFilter === '' || customer.includes(customerFilter)) &&
            (countryFilter === '' || country.includes(countryFilter)) &&
            (channelFilterValue === '' || 
             channelFilterValue === 'all_channels' ||
             channelFilterValue.split(',').some(filterChannel => channel.includes(filterChannel.toLowerCase()))) &&
            (carrierFilter === '' || carrier.includes(carrierFilter)) &&
            (trackFilter === '' || trackText.includes(trackFilter)) &&
            (problemFilter === 'all' || 
             (problemFilter === 'normal' && !isProblem) || 
             (problemFilter === 'problem' && isProblem))&&
                (!statusFilter || rowStatus === statusFilter);

        row.setAttribute('data-filtered', showRow ? 'true' : 'false');

        document.getElementById('trackingSearchInput').value = '';
    });
    
    // 筛选后重置到第一页并更新分页
    currentPage = 1;
    displayPage();
    updatePagination();
}

document.addEventListener('DOMContentLoaded', function () {
    const buttons = document.querySelectorAll('button[data-bs-toggle="collapse"]');
    buttons.forEach(btn => {
        const target = document.querySelector(btn.getAttribute('data-bs-target'));
        if (!target) return;
        target.addEventListener('show.bs.collapse', () => btn.textContent = '收起');
        target.addEventListener('hide.bs.collapse', () => btn.textContent = '展开更多');
    });
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl, {
            trigger: 'manual'
        });
    });
    
    // 初始化：所有行默认应该显示
    const allRows = document.querySelectorAll('#logisticsTable tbody tr');
    allRows.forEach(row => {
        row.setAttribute('data-filtered', 'true');
    });
    
    // 初始化分页
    displayPage();
    updatePagination();
});
</script>
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
