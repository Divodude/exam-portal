import fitz  # PyMuPDF
import re
import json

def parse_pdf_to_json(pdf_path, output_json_path):
    print(f"Reading {pdf_path}...")
    doc = fitz.open(pdf_path)
    
    raw_text = ""
    for page in doc:
        raw_text += page.get_text("text") + "\n"
        
    print("Parsing text...")
    
    # Basic Regex Patterns (You may need to tweak these based on your exact PDF formatting)
    # Matches "1. ", "Q1.", "1)", etc.
    question_pattern = re.compile(r'(?:Q?\d+[\.\)]\s)(.*?)(?=(?:Q?\d+[\.\)]\s)|$)', re.DOTALL | re.IGNORECASE)
    
    # Matches "A)", "(A)", "a.", etc.
    options_pattern = re.compile(r'([A-D][\.\)]|\([A-D]\))\s(.*?)(?=(?:[A-D][\.\)]|\([A-D]\))|$)', re.DOTALL | re.IGNORECASE)

    questions_list = []
    
    # Find all question blocks
    question_blocks = question_pattern.findall(raw_text)
    
    for i, q_block in enumerate(question_blocks):
        q_id = i + 1
        
        # Split the block into the question text and the options text
        # Usually options start with A) or (A)
        split_match = re.search(r'([A-D][\.\)]|\([A-D]\))', q_block, re.IGNORECASE)
        
        if split_match:
            split_idx = split_match.start()
            q_text = q_block[:split_idx].strip()
            options_chunk = q_block[split_idx:]
            
            # Extract options
            raw_options = options_pattern.findall(options_chunk)
            options = []
            for opt_marker, opt_text in raw_options:
                opt_text = opt_text.strip().replace('\n', ' ')
                # Format to standard "A) Text"
                clean_marker = opt_marker.replace('(', '').replace(')', '').replace('.', '').upper() + ")"
                options.append(f"{clean_marker} {opt_text}")
                
            # If we didn't find exactly 4 options, pad it so the UI doesn't break
            while len(options) < 4:
                options.append("Option missing in PDF")
            options = options[:4]
                
        else:
            q_text = q_block.strip()
            options = ["A) -", "B) -", "C) -", "D) -"]
            
        # Clean up question text
        q_text = q_text.replace('\n', ' ')

        # Since a PDF doesn't easily highlight the correct answer, we leave it blank for manual review
        questions_list.append({
            "id": q_id,
            "text": q_text,
            "options": options,
            "correct": "", 
            "explanation": "Explanation not automatically extracted."
        })

    # Build the final JSON structure
    exam_data = {
        "meta": {
            "title": "Extracted Exam",
            "exam_type": "SSC_CGL",
            "date": "2024-09-04",
            "total_time": 3600,
            "timer_mode": "sectional",
            "negative_marking": 0.5,
            "bilingual": False,
            "instructions": ["Parsed automatically from PDF."]
        },
        "sections": [
            {
                "id": "section_1",
                "name": "General Section",
                "time": 3600,
                "questions": questions_list
            }
        ]
    }
    
    print(f"Extracted {len(questions_list)} questions.")
    
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(exam_data, f, indent=4, ensure_ascii=False)
        
    print(f"Successfully saved to {output_json_path}")

if __name__ == "__main__":
    parse_pdf_to_json("exam2.pdf", "parsed_exam.json")
