import json

def load_tracking_numbers_to_remove():
    try:
        with open('data/remove_tracking.txt', 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return []
            return content.split()
    except FileNotFoundError:
        print("Error: remove_tracking.txt file not found")
        return []

def remove_tracking_numbers(tracking_numbers):
    if not tracking_numbers:
        print("No tracking numbers to remove")
        return

    print(f"Processing removal for tracking numbers: {', '.join(tracking_numbers)}")
    
    # Process assignments.json
    try:
        with open('data/assignments.json', 'r', encoding='utf-8') as f:
            assignments = json.load(f)
        
        for tn in tracking_numbers:
            assignments.pop(tn, None)
        
        with open('data/assignments.json', 'w', encoding='utf-8') as f:
            json.dump(assignments, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Error processing assignments.json: {str(e)}")
        return
    
    # Process tracking_numbers.json - 直接删除行，保持原格式
    try:
        with open('data/tracking_numbers.json', 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        original_count = len([line for line in lines if '"tracking_number"' in line])
        removed_count = 0
        
        # 过滤掉包含要删除运单号的行
        filtered_lines = []
        for i, line in enumerate(lines):
            should_keep = True
            for tn in tracking_numbers:
                # 检查行中是否包含该运单号
                if f'"tracking_number": "{tn}"' in line:
                    should_keep = False
                    removed_count += 1
                    # 如果删除的行不是最后一行，检查上一行是否有逗号需要移除
                    if i > 0 and i < len(lines) - 1:
                        prev_line = filtered_lines[-1] if filtered_lines else ''
                        # 如果上一行以逗号结尾，且下一行是 ] 或空行，移除逗号
                        if prev_line.rstrip().endswith(',') and (i + 1 < len(lines) and lines[i + 1].strip() in [']', '']):
                            filtered_lines[-1] = prev_line.rstrip().rstrip(',') + '\n'
                    break
            if should_keep:
                filtered_lines.append(line)
        
        # 清理最后一项后的逗号（如果存在）
        for i in range(len(filtered_lines) - 1, -1, -1):
            line = filtered_lines[i]
            if line.strip() == ']':
                # 检查上一行是否有逗号
                if i > 0 and filtered_lines[i - 1].rstrip().endswith(','):
                    filtered_lines[i - 1] = filtered_lines[i - 1].rstrip().rstrip(',') + '\n'
                break
        
        with open('data/tracking_numbers.json', 'w', encoding='utf-8') as f:
            f.writelines(filtered_lines)
        
        print(f"Removed {removed_count} entries from tracking_numbers.json")
    except Exception as e:
        print(f"Error processing tracking_numbers.json: {str(e)}")
        return

    print("Removal process completed successfully")

if __name__ == "__main__":
    tracking_numbers = load_tracking_numbers_to_remove()
    remove_tracking_numbers(tracking_numbers)