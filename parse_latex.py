import os
import re
import json
import sys

def convert_pdf_to_latex(pdf_path, output_latex_path):
    """Converts a PDF file to LaTeX format using pdf2docx + pypandoc."""
    print(f"Step 1: Converting PDF '{pdf_path}' to intermediate DOCX...")
    docx_path = pdf_path.rsplit(".", 1)[0] + "_temp.docx"
    
    try:
        from pdf2docx import Converter
        cv = Converter(pdf_path)
        cv.convert(docx_path, start=0, end=None)
        cv.close()
        print(f"Converted PDF to '{docx_path}'.")
    except Exception as e:
        print(f"Error converting PDF to DOCX with pdf2docx: {e}")
        return False

    print(f"Step 2: Converting DOCX '{docx_path}' to LaTeX '{output_latex_path}'...")
    try:
        import pypandoc
        # Try downloading pandoc automatically if not installed
        try:
            pypandoc.ensure_pandoc_installed()
        except Exception:
            pass
        pypandoc.convert_file(docx_path, 'latex', outputfile=output_latex_path)
        print(f"Successfully generated LaTeX file: '{output_latex_path}'!")
        
        # Cleanup temporary docx file
        if os.path.exists(docx_path):
            os.remove(docx_path)
        return True
    except Exception as e:
        print(f"Error converting DOCX to LaTeX using pypandoc: {e}")
        print("Tip: Install pandoc system-wide or run 'python -c \"import pypandoc; pypandoc.download_pandoc()\"'")
        return False

def clean_latex(text):
    """Strips LaTeX layout tags like \\textbf{}, \\quote, \\includegraphics, longtables, etc."""
    # Remove comments (% ...)
    text = re.sub(r'%.*?$', '', text, flags=re.MULTILINE)
    
    # Remove longtable grid markup, column definitions & headers
    text = re.sub(r'\[\]\{@\{\}.*?\}\}', '', text, flags=re.DOTALL)
    text = re.sub(r'>\{\\raggedright.*?\}', '', text)
    text = re.sub(r'\\real\{.*?\}', '', text)
    text = re.sub(r'\\column-width.*?\+\s*\d+tabcolsep', '', text)
    text = re.sub(r'\[[bt]\]\{\\linewidth\}\\raggedright', '', text)
    text = re.sub(r'\\multicolumn\{\d+\}\{.*?\}\{\s*', '', text)
    text = re.sub(r'\\multirow\{\d+\}\{.*?\}\{\s*', '', text)
    
    # Remove environments
    text = re.sub(r'\\begin\{minipage\}.*?\}', '', text)
    text = re.sub(r'\\end\{minipage\}', '', text)
    text = re.sub(r'\\begin\{quote\}', '', text)
    text = re.sub(r'\\end\{quote\}', '', text)
    text = re.sub(r'\\begin\{longtable\}.*?\}', '', text)
    text = re.sub(r'\\end\{longtable\}', '', text)
    text = re.sub(r'\\begin\{table\}.*?\}', '', text)
    text = re.sub(r'\\end\{table\}', '', text)
    text = re.sub(r'\\begin\{tabular\}.*?\}', '', text)
    text = re.sub(r'\\end\{tabular\}', '', text)
    text = re.sub(r'\\begin\{.*?\}', '', text)
    text = re.sub(r'\\end\{.*?\}', '', text)
    
    # Remove table rules and structural footer/header commands
    text = re.sub(r'\\noalign\{\}', '', text)
    text = re.sub(r'\\endlastfoot', '', text)
    text = re.sub(r'\\endfirsthead', '', text)
    text = re.sub(r'\\endhead', '', text)
    text = re.sub(r'\\endfoot', '', text)
    text = re.sub(r'\\toprule(?:\(\))?', '', text)
    text = re.sub(r'\\bottomrule(?:\(\))?', '', text)
    text = re.sub(r'\\midrule(?:\(\))?', '', text)
    text = re.sub(r'\\strut', '', text)
    
    text = re.sub(r'&', ' ', text)
    # Remove images
    text = re.sub(r'\\includegraphics\[.*?\]\{.*?\}', '', text)
    text = re.sub(r'\\includegraphics\{.*?\}', '', text)
    
    # Remove LaTeX formatting commands but keep content: \textbf{content} -> content
    text = re.sub(r'\\textbf\{(.*?)\}', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'\\emph\{(.*?)\}', r'\1', text, flags=re.DOTALL)
    
    # Remove miscellaneous commands
    text = re.sub(r'\\textquotesingle', "'", text)
    text = re.sub(r'\\hspace\{.*?\}', '', text)
    text = re.sub(r'\\\[.*?\]', '', text)
    text = re.sub(r'\\\\', '\n', text)
    
    # Clean up isolated LaTeX tokens/braces
    text = re.sub(r'\\[a-zA-Z]+', '', text) # Any lingering \command
    text = re.sub(r'^\s*\}', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\{', '', text, flags=re.MULTILINE)
    
    # Remove excessive spaces & blank lines
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()

def parse_latex_to_json(input_path, output_json_path):
    # Check if input is a PDF file
    if input_path.lower().endswith('.pdf'):
        latex_path = input_path.rsplit('.', 1)[0] + "_converted.latex"
        success = convert_pdf_to_latex(input_path, latex_path)
        if not success:
            print("PDF conversion failed. Proceeding with raw text extraction if possible...")
        else:
            input_path = latex_path

    print(f"Reading LaTeX content from '{input_path}'...")
    with open(input_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    # Clean raw LaTeX formatting
    cleaned_content = clean_latex(content)

    # Split by Question markers like Q.1, Q.2, Q.100, .2 etc.
    q_blocks = re.split(r'\n(?=Q\.\s*\d+|\.\d+|\bQ\d+\b)', cleaned_content)
    
    questions = []
    
    for block in q_blocks:
        block = block.strip()
        # Ensure it's a real question block
        if not re.search(r'^(?:Q\.\s*\d+|\.\d+|\bQ\d+\b)', block, re.IGNORECASE):
            continue
            
        # Extract Question Number & Initial Text
        q_match = re.match(r'^(?:Q\.\s*(\d+)|\.(\d+)|\bQ(\d+)\b)\s*(.*)', block, re.DOTALL | re.IGNORECASE)
        if not q_match:
            continue
            
        q_num = q_match.group(1) or q_match.group(2) or q_match.group(3)
        rest_of_block = q_match.group(4)
        
        # Find options A., B., C., D.
        opt_pattern = r'\n(?=[A-D]\.\s)'
        parts = re.split(opt_pattern, rest_of_block)
        
        q_text = parts[0].replace('\n', ' ').strip()
        
        options = []
        answer = ""
        explanation = ""
        
        if len(parts) > 1:
            option_chunks = parts[1:]
            for chunk in option_chunks:
                # Check if this chunk contains the Answer
                ans_match = re.search(r'Answer:\s*([A-D])', chunk, re.IGNORECASE)
                if ans_match:
                    answer = ans_match.group(1).upper()
                    opt_part = chunk[:ans_match.start()].strip()
                    expl_part = chunk[ans_match.end():].strip()
                    
                    if opt_part:
                        opt_part = opt_part.replace('\n', ' ').strip()
                        options.append(opt_part)
                        
                    sol_match = re.search(r'Sol:(.*)', expl_part, re.DOTALL | re.IGNORECASE)
                    if sol_match:
                        explanation = sol_match.group(1).replace('\n', ' ').strip()
                    else:
                        explanation = expl_part.replace('\n', ' ').strip()
                else:
                    opt_part = chunk.replace('\n', ' ').strip()
                    if opt_part:
                        options.append(opt_part)
        
        # Standardize options format (A) Text ...)
        clean_opts = []
        for opt in options:
            opt_clean = re.sub(r'^[A-D]\.\s*', '', opt).strip()
            if opt_clean:
                clean_opts.append(opt_clean)
                
        formatted_opts = []
        letters = ['A', 'B', 'C', 'D']
        for idx, opt_str in enumerate(clean_opts[:4]):
            formatted_opts.append(f"{letters[idx]}) {opt_str}")
            
        while len(formatted_opts) < 4:
            letter = letters[len(formatted_opts)]
            formatted_opts.append(f"{letter}) Option missing")

        questions.append({
            "id": int(q_num) if q_num and q_num.isdigit() else len(questions) + 1,
            "text": q_text,
            "options": formatted_opts,
            "correct": answer,
            "explanation": explanation
        })

    # Sort questions by ID
    questions.sort(key=lambda x: x["id"])

    # Categorize questions into SSC Stenographer standard sections
    sec_ga = []
    sec_gi = []
    sec_eng = []

    for q in questions:
        q_id = q["id"]
        if q_id <= 50:
            sec_ga.append(q)
        elif q_id <= 100:
            sec_gi.append(q)
        else:
            sec_eng.append(q)

    exam_data = {
        "meta": {
            "title": "SSC Stenographer 2025 (Held on 6 Aug 2025 Shift 1)",
            "exam_type": "SSC_STENOGRAPHER",
            "date": "2025-08-06",
            "total_time": 7200,
            "timer_mode": "sectional",
            "negative_marking": 0.25,
            "bilingual": False,
            "instructions": [
                "The examination consists of objective type multiple choice questions.",
                "Questions 1-50: General Awareness, Questions 51-100: General Intelligence & Reasoning, Questions 101-200: English Language & Comprehension.",
                "Negative marking of 0.25 marks per incorrect answer."
            ]
        },
        "sections": [
            {
                "id": "general_awareness",
                "name": "General Awareness",
                "time": 1800,
                "questions": sec_ga
            },
            {
                "id": "general_intelligence",
                "name": "General Intelligence & Reasoning",
                "time": 1800,
                "questions": sec_gi
            },
            {
                "id": "english_language",
                "name": "English Language & Comprehension",
                "time": 3600,
                "questions": sec_eng
            }
        ]
    }

    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(exam_data, f, indent=4, ensure_ascii=False)

    print(f"Successfully extracted {len(questions)} questions into {output_json_path} across {len(exam_data['sections'])} sections!")

if __name__ == "__main__":
    # Support command line args: python parse_latex.py paper.latex parsed_latex_exam.json
    input_file = sys.argv[1] if len(sys.argv) > 1 else "paper.latex"
    output_file = sys.argv[2] if len(sys.argv) > 2 else "parsed_latex_exam.json"
    
    parse_latex_to_json(input_file, output_file)
