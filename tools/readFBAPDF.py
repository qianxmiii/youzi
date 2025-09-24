import re
import PyPDF2
import json
import os

def load_address_config():
    """加载地址配置"""
    try:
        # 读取data_basic.js文件
        with open('data/data_basic.js', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取addressByCountry对象
        pattern = r'const addressByCountry = ({.*?});'
        match = re.search(pattern, content, re.DOTALL)
        
        if match:
            # 将JavaScript对象转换为Python字典
            js_obj = match.group(1)
            # 简单的转换，将JavaScript对象转换为JSON格式
            js_obj = re.sub(r'(\w+):', r'"\1":', js_obj)  # 给键加引号
            js_obj = re.sub(r'/\*.*?\*/', '', js_obj, flags=re.DOTALL)  # 移除注释
            js_obj = re.sub(r'//.*$', '', js_obj, flags=re.MULTILINE)  # 移除行注释
            
            # 尝试解析JSON
            try:
                return json.loads(js_obj)
            except:
                # 如果JSON解析失败，手动构建字典
                return build_address_dict_manually()
        else:
            return build_address_dict_manually()
    except:
        return build_address_dict_manually()

def build_address_dict_manually():
    """手动构建地址字典（作为备用方案）"""
    return {
        "美国": {
            "RDU4": "28303",
            "SBD1": "92316",
            "LAS1": "89044",
            "ONT8": "92551",
            "LGB8": "92376",
            "LAX9": "92337",
            "FWA4": "46809",
            "GYR2": "85395",
            "GYR3": "85043",
            "MQJ1": "46140",
            "IND9": "46143",
            "LLC6": "92376",  # 这个可能是LGB8的变体
            # 可以添加更多地址...
        }
    }

def extract_info_from_pdf(pdf_path):
    # 读取PDF文本内容
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
    
    # 清理文本，移除空字符和特殊字符
    text = text.replace('\x00', ' ').replace('\x0c', ' ').replace('\x1a', ' ')
    # 压缩多个空格为单个空格
    text = re.sub(r'\s+', ' ', text)


    # 通过PDF页面数量判断纸箱总数
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        box_total = len(reader.pages)

    # 提取FBA编号 - 查找第一个FBA编号作为前缀
    fba_matches = re.findall(r'(FBA[0-9A-Z]+)', text, re.IGNORECASE)
    fba_prefix = None
    if fba_matches:
        # 取第一个FBA编号，并截取到"U"之前的部分
        first_fba = fba_matches[0]
        u_index = first_fba.find('U')
        if u_index != -1:
            fba_prefix = first_fba[:u_index]
        else:
            fba_prefix = first_fba

    # 提取地址后缀 - 查找"-"后面的4个字符模式
    address_suffix = None
    
    # 方法1: 查找"-"后面的4个字符（如SBD1, LAS1等）
    dash_patterns = [
        r'-\s*([A-Z]{3}\d)\b',  # - SBD1
        r'-\s*([A-Z]{2}\d{2})\b',  # - AB12
        r'-\s*([A-Z]\d{3})\b',  # - A123
        r'-\s*([A-Z]{4})\b',  # - ABCD
    ]
    
    for pattern in dash_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            address_suffix = matches[0].upper()
            break
    
    # 方法2: 如果没找到"-"模式，查找被空格分隔的4字符模式
    if not address_suffix:
        spaced_patterns = [
            r'([A-Z]\s+[A-Z]\s+[A-Z]\s+\d)',  # A B C 1
            r'([A-Z]\s+[A-Z]\s+\d\s+\d)',  # A B 1 2
            r'([A-Z]\s+\d\s+\d\s+\d)',  # A 1 2 3
        ]
        
        for pattern in spaced_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                address_suffix = matches[0].replace(' ', '').upper()
                break

    return {
        "纸箱总数": box_total,
        "FBA前缀": fba_prefix,
        "地址后缀": address_suffix
    }

# 使用示例
if __name__ == "__main__":
    import os
    import glob
    
    # 加载地址配置
    address_config = load_address_config()
    
    # 指定文件夹路径
    folder_path = "C:\\Users\\qianx\\Desktop\\FBA"  # 当前目录，可以修改为其他路径，例如: "C:/Users/用户名/Desktop/PDF文件夹"
    
    # 查找文件夹下所有PDF文件
    pdf_files = glob.glob(os.path.join(folder_path, "*.pdf"))
    
    if not pdf_files:
        print("未找到PDF文件")
    else:
        print(f"找到 {len(pdf_files)} 个PDF文件")
        print("-" * 50)
        
        # 用于统计地址前缀的字典
        address_stats = {}
        
        for pdf_path in pdf_files:
            try:
                result = extract_info_from_pdf(pdf_path)
                
                # 获取文件名（不包含扩展名）
                filename = os.path.splitext(os.path.basename(pdf_path))[0]
                
                # 直接使用原地址后缀
                address_suffix = result['地址后缀']
                box_count = result['纸箱总数']
                
                # 统计地址前缀
                if address_suffix:
                    if address_suffix in address_stats:
                        address_stats[address_suffix] += box_count
                    else:
                        address_stats[address_suffix] = box_count
                
                # 按照指定格式输出
                output = f"[{filename}] - {address_suffix}={result['FBA前缀']}={box_count}CTNS"
                print(output)
                
            except Exception as e:
                print(f"处理文件 {pdf_path} 时出错: {e}")
        
        # 输出统计结果
        print("-" * 50)
        print("地址前缀统计:")
        total_all_boxes = 0
        for address, total_boxes in sorted(address_stats.items()):
            print(f"{address}: {total_boxes}CTNS")
            total_all_boxes += total_boxes
        
        print("-" * 30)
        print(f"总计: {total_all_boxes}CTNS")