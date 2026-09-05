import fitz  # PyMuPDF
import json
import time
import os
from dotenv import load_dotenv
from groq import Groq

# Load environment variables from .env file
load_dotenv()

# Set your API Key here or in your environment variables
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

def extract_text(pdf_path):
    print(f"Reading {pdf_path}...")
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text("text") + "\n"
    return text

def chunk_text(text, max_chars=8000):
    """Splits the massive PDF text into slightly larger chunks (8000 chars) to reduce total requests."""
    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = ""
    for p in paragraphs:
        if len(current_chunk) + len(p) > max_chars:
            chunks.append(current_chunk)
            current_chunk = p + "\n\n"
        else:
            current_chunk += p + "\n\n"
    if current_chunk:
        chunks.append(current_chunk)
    return chunks

def parse_with_groq(pdf_path, output_json_path):
    if not GROQ_API_KEY or GROQ_API_KEY == "YOUR_GROQ_API_KEY_HERE":
        print("ERROR: Please put your GROQ_API_KEY in the .env file.")
        return

    client = Groq(api_key=GROQ_API_KEY)
    raw_text = extract_text(pdf_path)
    chunks = chunk_text(raw_text, 4000) # Increased chunk size to reduce total requests
    
    all_questions = []
    
    print(f"Broke PDF into {len(chunks)} chunks. Processing with Groq...")
    
    for i, chunk in enumerate(chunks):
        print(f"Processing chunk {i+1}/{len(chunks)}...")
        
        prompt = f"""
        You are an expert exam parser. Extract all multiple-choice questions from the text below. 
        Return the result strictly as a JSON object containing a "questions" array.
        
        CRITICAL RULES:
        1. You MUST use DOUBLE QUOTES (") for all JSON keys and string values, NEVER single quotes.
        2. Ensure the JSON is completely valid.
        
        Each question MUST follow this schema exactly:
        {{
            "id": [integer, continue from 1],
            "text": "[Question text]",
            "options": ["A) [opt]", "B) [opt]", "C) [opt]", "D) [opt]"],
            "correct": "[A, B, C, or D if known, else empty string]",
            "explanation": "[Explanation if available, else empty string]"
        }}
        
        If there is garbage text (like headers/footers/dates), IGNORE IT.
        Only extract real questions.
        
        TEXT TO PARSE:
        {chunk}
        """
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                time.sleep(2) # Base sleep to respect RPM
                
                response = client.chat.completions.create(
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a JSON-only API. You must output only a valid JSON object starting with { and ending with }."
                        },
                        {
                            "role": "user",
                            "content": prompt,
                        }
                    ], 
                    model="groq/compound-mini", # Best Groq model for reasoning
                    temperature=0.1
                )
                
                # Extract JSON using regex in case the model adds markdown like ```json ... ```
                import re
                import ast
                raw_content = response.choices[0].message.content
                match = re.search(r'\{[\s\S]*\}', raw_content)
                if match:
                    json_str = match.group(0)
                    try:
                        result_json = json.loads(json_str)
                    except json.JSONDecodeError:
                        # Fallback: Model output single quotes or unescaped characters. Try parsing as Python dict.
                        try:
                            result_json = ast.literal_eval(json_str)
                        except Exception:
                            # If it still fails, raise error to trigger retry
                            raise Exception(f"Failed to parse JSON string: {json_str[:50]}...")
                            
                    if "questions" in result_json:
                        all_questions.extend(result_json["questions"])
                        print(f"  -> Extracted {len(result_json['questions'])} questions.")
                else:
                    print("  -> Failed to find JSON in response.")
                
                break # Success, break out of retry loop

            except Exception as e:
                error_msg = str(e)
                print(f"  -> Error on attempt {attempt+1}: {error_msg}")
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 10
                    print(f"  -> Waiting {wait_time} seconds before retrying...")
                    time.sleep(wait_time)
                else:
                    print(f"  -> Giving up on chunk {i+1} after {max_retries} attempts.")
            
    # Clean up IDs to be perfectly sequential
    for idx, q in enumerate(all_questions):
        q["id"] = idx + 1
        
    print(f"\nTotal Questions Extracted: {len(all_questions)}")

    # Build the final Exam JSON Structure
    exam_data = {
        "meta": {
            "title": "SSC Mock Test (Parsed by Groq)",
            "exam_type": "SSC_EXAM",
            "date": "2024-09-04",
            "total_time": 7200,
            "timer_mode": "sectional",
            "negative_marking": 0.25,
            "bilingual": False,
            "instructions": ["Parsed with Groq AI."]
        },
        "sections": [
            {
                "id": "full_exam",
                "name": "Full Exam",
                "time": 7200,
                "questions": all_questions
            }
        ]
    }
    
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(exam_data, f, indent=4, ensure_ascii=False)
        
    print(f"Successfully saved clean exam to {output_json_path}!")

if __name__ == "__main__":
    parse_with_groq("exam2.pdf", "parsed_exam_groq.json")
