import requests
import json
from datetime import datetime, timedelta
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import os


def load_config(config_file='config.json'):
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
            if 'vendors' not in config or not isinstance(config['vendors'], list):
                raise ValueError("配置文件必须包含'vendors'数组")
            
            for vendor in config['vendors']:
                name = vendor.get('name')
                if name == "鑫鲲鹏" or name == "华威尔":
                    required_keys = ['name', 'FACTNO', 'SUPNO', 'SUPPASS', 'APPKEY', 'apiUrl']
                else:
                    required_keys = ['name', 'appToken', 'appKey', 'apiUrl']
                
                for key in required_keys:
                    if key not in vendor:
                        raise ValueError(f"物流商 {name} 配置缺少字段: {key}")
            return config

    except FileNotFoundError:
        raise Exception(f"配置文件未找到：{config_file}")
    except json.JSONDecodeError:
        raise Exception("配置文件解析失败，请确认是合法 JSON")



def load_tracking_numbers(json_file='tracking_numbers.json'):
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # 期望是列表，每项包含 tracking_number 和 customer
        if not isinstance(data, list):
            raise ValueError("tracking_numbers.json 应为数组，数组元素为字典")
        for item in data:
            if 'tracking_number' not in item or 'customer' not in item:
                raise ValueError("tracking_numbers.json 每项必须包含 'tracking_number' 和 'customer' 字段")
        return data
    except FileNotFoundError:
        raise Exception(f"文件未找到：{json_file}")
    except json.JSONDecodeError:
        raise Exception("tracking_numbers.json 解析失败，请确认是合法 JSON")


def load_assignments(assign_file='assignments.json'):
    try:
        with open(assign_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # 期望是字典，key为单号，value为物流商名称
        if not isinstance(data, dict):
            raise ValueError("assignments.json 应为字典，键为单号，值为物流商名称")
        return data
    except FileNotFoundError:
        raise Exception(f"文件未找到：{assign_file}")
    except json.JSONDecodeError:
        raise Exception("assignments.json 解析失败，请确认是合法 JSON")

def fetch_tracking_data(tracking_item, vendor, max_retries=3):
    tracking_number = tracking_item['tracking_number']
    customer = tracking_item['customer']

    for attempt in range(max_retries):
        try:
            
            # 特殊逻辑
            if vendor["name"] == "鑫鲲鹏" or vendor["name"] == "华威尔":
                params = {
                    "FACTNO": vendor["FACTNO"],
                    "SUPNO": vendor["SUPNO"],
                    "SUPPASS": vendor["SUPPASS"],
                    "APPKEY": vendor["APPKEY"],
                    "PACKNO": [tracking_number]
                }
                response = requests.post(
                    vendor["apiUrl"],
                    json=params,
                    timeout=10
                )
                response.raise_for_status()
                result = response.json()

                if not isinstance(result, dict) or 'data' not in result or 'details' not in result['data']:
                    print(f"{vendor['name']}返回格式异常：{result}")
                    return None

                details = result['data']['details']

                if not isinstance(details, list) or not details:
                    print(f"{vendor['name']}返回详情格式异常：{details}")
                    return None

                # 状态字段
                kdzt = result['data'].get("kdzt", "")
                # 转单号
                express_number = result['data'].get("zycode", "")

                # 转为统一格式，details 中每个元素都有 zztm 和 guiji
                track_details = [{
                    "track_occur_date": item.get("zztm", ""),
                    "track_description": item.get("guiji", "")
                } for item in details if item.get("guiji")]

                return {
                    "tracking_number": tracking_number,
                    "customer": customer,
                    "vendor": vendor["name"],
                    "data": {
                        "track_status_name": kdzt,
                        "express_number": express_number,
                        "details": track_details
                    }
                }

            # ✅ 默认其他通用物流商逻辑
            else:
                params = {
                    "appToken": vendor["appToken"],
                    "appKey": vendor["appKey"],
                    "serviceMethod": "gettrack",
                    "paramsJson": json.dumps({"tracking_number": tracking_number})
                }

                response = requests.post(
                    vendor["apiUrl"],
                    data=params,
                    timeout=10
                )
                response.raise_for_status()
                result = response.json()

                if not result.get("success"):
                    print(f"运单 {tracking_number} 请求失败：{result.get('cnmessage')}")
                    return None

                return {
                    "tracking_number": tracking_number,
                    "customer": customer,
                    "vendor": vendor["name"],
                    "data": result["data"][0]
                }

        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                print(f"运单 {tracking_number} 第{attempt+1}次请求失败：{str(e)}")
                return None
            time.sleep(1)


def batch_fetch_by_assignments(tracking_list, assignments, vendors, max_workers=5):
    """
    只查询分配了物流商的单号，且对应的物流商必须在配置中
    """
    all_results = []

    # 物流商名称映射，方便快速查找
    vendor_map = {v['name']: v for v in vendors}

    # 筛选只保留有分配且配置中存在的单号
    filtered_list = []
    for item in tracking_list:
        tn = item['tracking_number']
        assigned_vendor = assignments.get(tn)
        if assigned_vendor and assigned_vendor in vendor_map:
            filtered_list.append((item, vendor_map[assigned_vendor]))
        else:
            print(f"跳过单号 {tn}，无对应物流商分配或物流商未配置")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_item = {
            executor.submit(fetch_tracking_data, item, vendor): (item, vendor)
            for item, vendor in filtered_list
        }

        for future in as_completed(future_to_item):
            item, vendor = future_to_item[future]
            try:
                data = future.result()
                if data:
                    print(f"运单 {item['tracking_number']} 查询成功，物流商 {vendor['name']}")
                    all_results.append(data)
                else:
                    print(f"运单 {item['tracking_number']} 查询失败，物流商 {vendor['name']}")
            except Exception as e:
                print(f"运单 {item['tracking_number']} 查询异常：{str(e)}")

    return all_results


def save_results(results, output_file):
    versioned_data = {
        "version": "1.0",
        "timestamp": datetime.now().isoformat(),
        "count": len(results),
        "success_count": len(results),
        "data": results
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(versioned_data, f, ensure_ascii=False, indent=2)
    print(f"\n成功记录已保存到：{output_file}")


def generate_html_report(results, output_file):
    today_str = datetime.now().strftime('%Y-%m-%d')

    customers_list = []

    # 生成唯一物流商和客户名列表（用于前端下拉框）
    customers_set = set()
    for r in results:
      customer = str(r.get("customer", "")).strip()
      if customer:
          customers_set.add(customer)

    customers_list = sorted(customers_set)

    customer_options = '\n'.join(f'<option value="{c}">{c}</option>' for c in customers_list)


    html_head = f"""<!DOCTYPE html>
<html lang="zh">
<head>
  <meta charset="UTF-8" />
  <title>物流查询报告</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <link href="css/common/bootstrap.min.css" rel="stylesheet" />
  <link rel="icon" href="rep_favicon.png" type="image/png">
  <style>
    .today-highlight {{
      background-color: #fff3cd;
      font-weight: bold;
    }}
    .tracking-card {{
      border: 1px solid #dee2e6;
      border-radius: .5rem;
      padding: 1rem;
      margin-bottom: 1rem;
    }}
    .tracking-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 10px;
    }}
    .tracking-number {{
      font-weight: bold;
      font-size: 1.1rem;
    }}
    .latest-track {{
      font-style: italic;
      color: #555;
      flex: 1 1 100%;
    }}
    .filter-row {{
      margin-bottom: 1rem;
      display: flex;
      flex-wrap: wrap;
      gap: 1rem;
    }}
    .filter-row > * {{
      flex: 1 1 150px;
    }}
    .collapse-table td {{
      padding: .5rem .75rem;
    }}
  </style>
</head>
<body>
<div class="container my-4">
  <h2 class="mb-3">物流查询报告</h2>
  <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

  <div class="filter-row">
    <input type="text" id="searchInput" class="form-control" placeholder="搜索运单号或客户名" onkeyup="filterTable()" />
    <select id="vendorFilter" class="form-select" onchange="filterTable()">
      <option value="">全部物流商</option>
      <option value="森磊">森磊</option>
      <option value="腾信">腾信</option>
      <option value="鹏远">鹏远</option>
      <option value="鑫鲲鹏">鑫鲲鹏</option>
      <option value="华威尔">华威尔</option>
    </select>
    <select id="customerFilter" class="form-select" onchange="filterTable()">
      <option value="">全部客户</option>
      {customer_options}
    </select>
    <select id="statusFilter" class="form-select" onchange="filterTable()">
      <option value="">全部状态</option>
      <option value="未出库">未出库</option>
      <option value="转运中">转运中</option>
      <option value="派送中">派送中</option>
      <option value="已签收">已签收</option>
    </select>
    <select id="todayFilter" class="form-select" onchange="filterTable()">
      <option value="">全部更新时间</option>
      <option value="today">今日更新</option>
      <option value="last2days">近两天更新</option>
      <option value="last3days">近三天更新</option>
      <option value="last7days">近一周更新</option>
    </select>
    <input type="text" id="trackKeywordFilter" class="form-control" placeholder="轨迹关键词筛选" onkeyup="filterTable()" />
  </div>

  <div id="trackingList">
"""

    
    html_body = ""

    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    three_days_ago = today - timedelta(days=3)
    one_week_ago = today - timedelta(days=7)

    for idx, item in enumerate(results):
        tracking_number = item.get("tracking_number", "")
        customer = item.get("customer", "")
        vendor = item.get("vendor", "")
        collapse_id = f"collapse_{idx}"
        status = item.get("data", {}).get("track_status_name", "")

        today_str = datetime.now().strftime('%Y-%m-%d')
        details = item.get("data", {}).get("details", [])

        # 更新日期判断逻辑
        has_today = False
        has_last2 = False
        has_last3 = False
        has_last7 = False

        for d in details:
            track_date_str = d.get("track_occur_date", "")
            if not track_date_str:
                continue

            # 解析日期（兼容多种格式）
            track_date = None
            for fmt in ('%Y-%m-%d', '%Y/%m/%d', '%Y%m%d', '%Y-%m-%d %H:%M:%S'):
                try:
                    track_date = datetime.strptime(track_date_str.split()[0], fmt).date()
                    break
                except:
                    continue

            if not track_date:
                continue

            if track_date == today:
                has_today = has_last3 = has_last7 = True
            elif track_date >= yesterday:
                has_last2=has_last3 = has_last7 = True
            elif track_date >= three_days_ago:
                has_last3 = has_last7 = True
            elif track_date >= one_week_ago:
                has_last7 = True

        # 添加到卡片属性
        html_body += f'<div class="tracking-card" data-vendor="{vendor}" data-customer="{customer}" data-status="{status}" ' \
                 f'data-today-update="{"true" if has_today else "false"}" ' \
                 f'data-last2-update="{"true" if has_last2 else "false"}" ' \
                 f'data-last3-update="{"true" if has_last3 else "false"}" ' \
                 f'data-last7-update="{"true" if has_last7 else "false"}" ' \
                 f'data-tracking-number="{tracking_number}" data-customername="{customer}">\n'
        html_body += f'  <div class="tracking-header">\n'
        html_body += f'    <div class="tracking-number">{tracking_number}</div>\n'
        html_body += f'    <div><b>客户:</b> {customer}</div>\n'
        html_body += f'    <div><b>物流商:</b> {vendor}</div>\n'
        if "data" in item:
            details = item["data"].get("details", [])
            latest = details[0] if details else {}
            latest_time = latest.get("track_occur_date", "")
            latest_desc = latest.get("track_description", "")
            html_body += f'    <div class="latest-track">{latest_time} - {latest_desc[:60]}</div>\n'
        else:
            html_body += f'    <div class="text-danger">无详细轨迹</div>\n'
        html_body += f'    <div><b>状态:</b> {status}</div>\n'
        html_body += f'  </div>\n'

        if "data" in item and item["data"].get("details"):
            html_body += f'  <div class="text-end mt-2">\n'
            html_body += f'    <a class="btn btn-sm btn-outline-primary" data-bs-toggle="collapse" href="#{collapse_id}" role="button" aria-expanded="false" aria-controls="{collapse_id}">展开/收起轨迹</a>\n'
            html_body += f'  </div>\n'

            html_body += f'  <div class="collapse mt-2" id="{collapse_id}">\n'
            html_body += f'    <table class="table table-sm table-bordered collapse-table">\n'
            html_body += f'      <thead class="table-light"><tr><th style="width:180px;">时间</th><th style="width:150px;">地点</th><th>轨迹描述</th></tr></thead>\n'
            html_body += f'      <tbody>\n'

            for d in item["data"]["details"]:
                time_str = d.get("track_occur_date", "")
                desc = d.get("track_description", "")
                location = d.get("track_location", "")
                row_class = "today-highlight" if time_str.startswith(today_str) else ""
                html_body += f'        <tr class="{row_class}"><td>{time_str}</td><td>{location}</td><td>{desc}</td></tr>\n'

            html_body += f'      </tbody>\n    </table>\n  </div>\n'

        html_body += '</div>\n'

    html_tail = f"""
  </div>
  <nav>
    <ul class="pagination justify-content-center" id="pagination"></ul>
  </nav>
</div>

<script src="js/common/bootstrap.bundle.min.js"></script>
<script>
const itemsPerPage = 100;
let currentPage = 1;
const trackingList = document.getElementById('trackingList');
const pagination = document.getElementById('pagination');

function filterTable() {{
  const searchText = document.getElementById('searchInput').value.toLowerCase();
  const vendorFilter = document.getElementById('vendorFilter').value;
  const customerFilter = document.getElementById('customerFilter').value;
  const statusFilter = document.getElementById('statusFilter').value;
  const todayFilter = document.getElementById('todayFilter').value;
  const trackKeyword = document.getElementById('trackKeywordFilter').value.toLowerCase();

  const statusMap = {{
    "未出库": ["未上网"],
    "转运中": ["转运中", "运输中", "已出库", "已开航", "清关中"],
    "派送中": ["派送中", "已交仓"],
    "已签收": ["派送妥投"]
  }};

  const filtered = Array.from(trackingList.children).filter(card => {{
    const tn = card.getAttribute('data-tracking-number').toLowerCase();
    const customer = card.getAttribute('data-customer');
    const vendor = card.getAttribute('data-vendor');
    const status = card.getAttribute('data-status');
    const todayUpdate = card.getAttribute('data-today-update');

    // 轨迹关键词匹配逻辑
    if (trackKeyword) {{
      const trackDescriptions = Array.from(card.querySelectorAll('td:nth-child(3)')).map(td => td.innerText.toLowerCase());
      if (!trackDescriptions.some(desc => desc.includes(trackKeyword))) {{
        return false;
      }}
    }}

    if (searchText && !(tn.includes(searchText) || customer.toLowerCase().includes(searchText))) return false;
    if (vendorFilter && vendorFilter !== vendor) return false;
    if (customerFilter && customerFilter !== customer) return false;
    if (statusFilter) {{
      const actualStatuses = statusMap[statusFilter] || [statusFilter];
      if (!actualStatuses.includes(status)) return false;
    }}
    // 更新时间筛选
    if (todayFilter === 'today') {{
      if (card.getAttribute('data-today-update') !== 'true') return false;
    }} 
    else if (todayFilter === 'last2days') {{
      if (card.getAttribute('data-last2-update') !== 'true') return false;
    }}
    else if (todayFilter === 'last3days') {{
      if (card.getAttribute('data-last3-update') !== 'true') return false;
    }}
    else if (todayFilter === 'last7days') {{
      if (card.getAttribute('data-last7-update') !== 'true') return false;
    }}

    return true;
  }});

  currentPage = 1;
  showPage(filtered);
  setupPagination(filtered.length);

  //关键词高亮
  highlightTrackKeywords(trackKeyword);
}}

function highlightTrackKeywords(keyword) {{
  const rows = document.querySelectorAll('.collapse-table td:nth-child(3)');
  rows.forEach(td => {{
    const text = td.innerText;
    if (!keyword) {{
      td.innerHTML = text; // 还原
    }} else {{
      const regex = new RegExp(`(${{keyword}})`, 'gi');
      td.innerHTML = text.replace(regex, '<mark>$1</mark>');
    }}
  }});
}}

function showPage(filteredItems) {{
  const start = (currentPage - 1) * itemsPerPage;
  const end = start + itemsPerPage;

  // 隐藏所有元素
  Array.from(trackingList.children).forEach(card => {{
    card.style.display = 'none';
  }});

  // 只显示当前页的元素
  filteredItems.forEach((item, index) => {{
    if (index >= start && index < end) {{
      item.style.display = '';
    }}
  }});
}}

function setupPagination(totalItems) {{
  pagination.innerHTML = '';
  const pageCount = Math.ceil(totalItems / itemsPerPage);
  if (pageCount <= 1) return;

  for (let i = 1; i <= pageCount; i++) {{
    const li = document.createElement('li');
    li.classList.add('page-item');
    if (i === currentPage) li.classList.add('active');
    const a = document.createElement('a');
    a.classList.add('page-link');
    a.href = '#';
    a.innerText = i;
    a.addEventListener('click', (e) => {{
      e.preventDefault();
      if (currentPage === i) return; // 点击当前页不刷新
      currentPage = i;

      // 重新执行筛选，分页显示
      filterTable();
    }});
    li.appendChild(a);
    pagination.appendChild(li);
  }}
}}


// 初始化时填充筛选器选项
function initFilters() {{
  const customerFilter = document.getElementById('customerFilter');

  // 填充物流商选项
  const vendors = Array.from(new Set(Array.from(trackingList.children).map(c => c.getAttribute('data-vendor')).filter(v=>v)));
  vendors.sort();
  vendors.forEach(v => {{
    const option = document.createElement('option');
    option.value = v;
    option.textContent = v;
  }});

  // 填充客户选项
  const customers = Array.from(new Set(Array.from(trackingList.children).map(c => c.getAttribute('data-customer')).filter(cust=>cust)));
  customers.sort();
  customers.forEach(c => {{
    const option = document.createElement('option');
    option.value = c;
    option.textContent = c;
    customerFilter.appendChild(option);
  }});
}}

document.addEventListener('DOMContentLoaded', () => {{
  initFilters();
  filterTable();
}});
</script>
</body>
</html>
"""

    html_content = html_head + html_body + html_tail

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"HTML报告已保存到：{output_file}")



def deduplicate_tracking_list(tracking_list):
    seen = set()
    unique_list = []
    for item in tracking_list:
        tn = item['tracking_number']
        if tn not in seen:
            seen.add(tn)
            unique_list.append(item)
    return unique_list

if __name__ == "__main__":
    try:
        config = load_config("config.json")
        tracking_list = load_tracking_numbers("tracking_numbers.json")
        tracking_list = deduplicate_tracking_list(tracking_list)
        assignments = load_assignments("assignments.json")
        print(f"成功加载 {len(tracking_list)} 个运单号，分配配置 {len(assignments)} 条")

        # Add this check after loading both files

        results = batch_fetch_by_assignments(tracking_list, assignments, config['vendors'], max_workers=1)

        os.makedirs("result", exist_ok=True)
        output_json = "tracking_results.json"
        save_results(results, output_json)

        output_html = "report.html"
        generate_html_report(results, output_html)

    except Exception as e:
        print(f"程序出错: {str(e)}")
