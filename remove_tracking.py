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
    
    # Process tracking_numbers.json
    try:
        with open('tracking_numbers.json', 'r', encoding='utf-8') as f:
            tracking_data = json.load(f)
        
        original_count = len(tracking_data)
        tracking_data = [item for item in tracking_data if item['tracking_number'] not in tracking_numbers]
        removed_count = original_count - len(tracking_data)
        
        with open('tracking_numbers.json', 'w', encoding='utf-8') as f:
            json.dump(tracking_data, f, ensure_ascii=False, indent=4)
        
        print(f"Removed {removed_count} entries from tracking_numbers.json")
    except Exception as e:
        print(f"Error processing tracking_numbers.json: {str(e)}")
        return

    print("Removal process completed successfully")

if __name__ == "__main__":
    tracking_numbers = load_tracking_numbers_to_remove()
    remove_tracking_numbers(tracking_numbers)