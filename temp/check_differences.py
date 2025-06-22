# 查找运单号是否配置渠道和客户名
import json

def load_json_file(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)

def find_differences():
    try:
        # Load the files
        assignments = load_json_file('assignments.json')
        tracking_numbers_data = load_json_file('tracking_numbers.json')
        
        # Get sets of tracking numbers
        assigned_tns = set(assignments.keys())
        tracking_tns = {item['tracking_number'] for item in tracking_numbers_data}
        
        # Find differences
        in_assign_not_in_tracking = assigned_tns - tracking_tns
        in_tracking_not_in_assign = tracking_tns - assigned_tns
        
        # Print results
        print("\nTracking numbers in 【assignments.json】 but not in 【tracking_numbers.json】:")
        for tn in sorted(in_assign_not_in_tracking):
            print(tn)
            
        print("\nTracking numbers in 【tracking_numbers.json】 but not in 【assignments.json】:")
        for tn in sorted(in_tracking_not_in_assign):
            print(tn)
            
        print(f"\nSummary:")
        print(f"Total in assignments: {len(assigned_tns)}")
        print(f"Total in tracking_numbers: {len(tracking_tns)}")
        print(f"Only in assignments: {len(in_assign_not_in_tracking)}")
        print(f"Only in tracking_numbers: {len(in_tracking_not_in_assign)}")
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    find_differences()