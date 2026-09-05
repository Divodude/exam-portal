import os
import json
import glob

def build_exam_list():
    exams_dir = 'exams'
    if not os.path.exists(exams_dir):
        print(f"Directory '{exams_dir}' does not exist.")
        return

    exam_files = glob.glob(os.path.join(exams_dir, '*.json'))
    exams_list = []

    for file_path in exam_files:
        if os.path.basename(file_path) == 'index.json':
            continue
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Extract metadata
            if 'meta' in data and 'title' in data['meta']:
                title = data['meta']['title']
            else:
                title = os.path.basename(file_path)
                
            exams_list.append({
                'title': title,
                'file': os.path.basename(file_path)
            })
            print(f"Found exam: {title} ({os.path.basename(file_path)})")
            
        except Exception as e:
            print(f"Error reading {file_path}: {e}")

    index_path = os.path.join(exams_dir, 'index.json')
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(exams_list, f, indent=4)
        
    print(f"Successfully wrote {len(exams_list)} exams to {index_path}")

if __name__ == "__main__":
    build_exam_list()
