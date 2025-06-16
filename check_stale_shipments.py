import json
import requests
from datetime import datetime, timedelta
import re


def load_config(filename='config.json'):
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_tracking_numbers(filename='tracking_numbers.json'):
    with open(filename, 'r', encoding='utf-8') as f:
        # 这里假设每条有 tracking_number 和 customer 字段
        return json.load(f)

# 新增：解析ETA日期的函数，支持多种格式
def parse_eta_date(node_desc):
    # 匹配 ETA:6.12、ETA 6/12 等格式（忽略大小写）
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
        # 如果ETA日期比当前时间早很多，可能是跨年，调整到下一年
        if eta_date < now - timedelta(days=180):
            try:
                eta_date = datetime(year + 1, month, day)
            except ValueError:
                return None
        return eta_date
    return None

# 新增：判断ETA是否在指定天数内
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
                # 批量数据
                data = result.get('data', [])
                # 关联客户信息
                for d in data:
                    # 通过运单号匹配客户名
                    match = next((x for x in batch if x['tracking_number'] == d.get('odd')), None)
                    d['customer'] = match.get('customer') if match else ''
                all_results.extend(data)
            else:
                print(f"查询失败: {result.get('msg')}")
        except Exception as e:
            print(f"请求异常: {e}")

    return all_results


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
        # 新增字段：是否3天内到港
        item["eta_within_3_days"] = is_eta_within_days(item, days=3)

    # 按未更新天数降序排序（-1放后面）
    results.sort(key=lambda x: (x['days_stale'] if x['days_stale'] >= 0 else -9999), reverse=True)
    return results


def generate_html_report(results, output_file="stales.html"):
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # 取所有客户名，去重排序
    customers = sorted({item.get('customer', '') for item in results if item.get('customer', '')})

    html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8" />
    <title>运单轨迹报告</title>
    <link href="css/common/bootstrap.min.css" rel="stylesheet" />
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

    @media (max-width: 768px) {{
        .filter-buttons,
        .filter-customer,
        .filter-track {{
            display: block;
            margin-bottom: 10px;
        }}

        .filter-customer select,
        .filter-track input {{
            width: 100%;
            margin-bottom: 10px;
        }}
    }}

    </style>
</head>
<body>
<div class="container mt-4">
    <h2>运单轨迹报告</h2>
    <p>生成时间: {now_str}</p>
    
    <div class="filter-buttons mb-2">
        <button class="btn btn-outline-secondary btn-sm" onclick="filterTable('all')">✅全部</button>
        <button class="btn btn-outline-warning btn-sm" onclick="filterTable('7')">超过7天未更新</button>
        <button class="btn btn-outline-danger btn-sm" onclick="filterTable('14')">🚨超过14天未更新</button>
        <button class="btn btn-outline-info btn-sm" onclick="filterTable('warehouse')">📦未更新</button>
        <button class="btn btn-outline-success btn-sm" onclick="filterTable('eta3')">🛳️3天内到港</button>
    </div>
    
    <div class="filter-customer mb-3">
        <label>客户筛选:</label>
        <select id="customerFilter" onchange="filterByCustomer()">
            <option value="">全部客户</option>"""
    for c in customers:
        html += f'<option value="{c}">{c}</option>'
    html += """
        </select>
    </div>
    <div class="filter-track mb-3">
        <label>轨迹关键词筛选:</label>
        <input type="text" id="trackFilterInput" placeholder="如: ETA, delivered..." oninput="filterByTrack()" class="form-control form-control-sm" style="width: 300px; display: inline-block;">
    </div>

    <table class="table table-bordered table-hover" id="logisticsTable">
        <thead class="table-light">
            <tr>
                <th>运单号</th>
                <th>客户名称</th>
                <th>最后更新时间</th>
                <th>未更新天数</th>
                <th>状态</th>
                <th>目的国</th>
                <th>轨迹</th>
            </tr>
        </thead>
        <tbody>
    """

    status_map = {
        2: "转运中",
        3: "已签收"
    }
    for item in results:
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

        track_list = "<br>".join([
            f"{log.get('nodeTime', '')} - {log.get('nodeDesc', '')}"
            for log in item.get("logisticsInfors", [])
        ])

        # 拼接轨迹内容，用于 JS 模糊匹配筛选
        track_text = " ".join([
            f"{log.get('nodeTime', '')} {log.get('nodeDesc', '')}"
            for log in item.get("logisticsInfors", [])
        ]).lower().replace('"', '&quot;')  # 转义双引号以防 HTML 错乱
        eta_flag = 1 if item.get("eta_within_3_days") else 0
        # data 属性用于 JS 筛选
        html += f"""
            <tr class="{row_class}" data-days="{days if isinstance(days, int) else 0}" 
                data-warehouse="{1 if latest_desc == 'Your goods are in the warehouse' else 0}" 
                data-eta3="{eta_flag}"
                data-customer="{customer}"
                data-track="{track_text}">
                <td>{item.get('odd')}</td>
                <td>{customer}</td>
                <td>{item.get('last_update', '')}</td>
                <td><span class="badge bg-danger">{days}</span></td>
                <td>{status}</td>
                <td>{delivery_country}</td>
                <td><div class="track-content">{track_list}</div></td>
            </tr>
        """

    html += """
        </tbody>
    </table>
</div>

<script>
function filterTable(type) {
    var rows = document.querySelectorAll("#logisticsTable tbody tr");
    rows.forEach(row => {
        var days = parseInt(row.getAttribute("data-days"));
        var isWarehouse = row.getAttribute("data-warehouse") === '1';
        var eta3 = row.getAttribute("data-eta3") === '1';
        if (type === "all") {
            row.style.display = "";
        } else if (type === "7") {
            row.style.display = (days > 7) ? "" : "none";
        } else if (type === "14") {
            row.style.display = (days > 14) ? "" : "none";
        } else if (type === "warehouse") {
            row.style.display = isWarehouse ? "" : "none";
        } else if (type === "eta3") {
            row.style.display = eta3 ? "" : "none";
        }
    });
    // 客户筛选重置
    document.getElementById("customerFilter").value = "";
}

function filterByCustomer() {
    var select = document.getElementById("customerFilter");
    var customer = select.value;
    var rows = document.querySelectorAll("#logisticsTable tbody tr");

    rows.forEach(row => {
        var rowCustomer = row.getAttribute("data-customer");
        // 如果客户筛选有值，则只显示匹配客户的行
        if (customer === "" || rowCustomer === customer) {
            row.style.display = "";
        } else {
            row.style.display = "none";
        }
    });
    // 筛选类型按钮重置为全部
    // 注意如果想让客户筛选和未更新天数筛选共存，可以改这里逻辑
    // document.querySelectorAll(".filter-buttons button").forEach(btn => btn.classList.remove('active'));
}
function filterByTrack() {
    var keyword = document.getElementById("trackFilterInput").value.trim().toLowerCase();
    var rows = document.querySelectorAll("#logisticsTable tbody tr");

    rows.forEach(row => {
        const trackData = row.getAttribute("data-track") || "";
        const trackDiv = row.querySelector(".track-content");
        const originalText = trackDiv.textContent;
        // 如果无关键词，则恢复原内容
        if (!keyword) {
            row.style.display = "";
            trackDiv.innerHTML = originalText;
            return;
        }
        if (trackData.includes(keyword)) {
            row.style.display = "";

            // 高亮匹配关键词（大小写不敏感）
            const regex = new RegExp(`(${keyword})`, 'gi');
            const highlighted = originalText.replace(regex, '<span class="highlight">$1</span>');
            trackDiv.innerHTML = highlighted;

        } else {
            row.style.display = "none";
            trackDiv.innerHTML = originalText; // 清除旧高亮
        }
    });

    // 重置客户筛选和状态筛选
    document.getElementById("customerFilter").value = "";
}

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
