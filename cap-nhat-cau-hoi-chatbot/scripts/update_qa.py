import os
import sys
import argparse
import csv
import re
import openpyxl

def find_target_dir(base_dir, domain_query):
    # Find the domain directory matching domain_query
    for name in os.listdir(base_dir):
        if domain_query.lower() in name.lower() and os.path.isdir(os.path.join(base_dir, name)):
            domain_dir = os.path.join(base_dir, name)
            # Find subfolder starting with 01_du_lieu_
            for sub in os.listdir(domain_dir):
                if sub.startswith("01_du_lieu_") and os.path.isdir(os.path.join(domain_dir, sub)):
                    return os.path.join(domain_dir, sub)
    return None

def update_csv_file(file_path, q_key, new_ans):
    rows = []
    updated = False
    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
            rows.append(header)
        except StopIteration:
            return False
        
        for row in reader:
            if len(row) >= 2:
                q, a = row[0], row[1]
                if q_key.lower() in q.lower():
                    a = new_ans
                    updated = True
                rows.append([q, a])
            else:
                rows.append(row)

    if updated:
        with open(file_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(rows)
        return True
    return False

def update_xlsx_file(file_path, q_key, new_ans):
    wb = openpyxl.load_workbook(file_path)
    ws = wb.active
    updated = False
    for row in ws.iter_rows(min_row=2):
        if len(row) >= 2:
            q_cell = row[0]
            a_cell = row[1]
            if q_cell.value and q_key.lower() in str(q_cell.value).lower():
                a_cell.value = new_ans
                updated = True
    if updated:
        wb.save(file_path)
        return True
    return False

def update_md_file(file_path, q_key, new_ans, is_website=False):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.split("\n")
    new_lines = []
    i = 0
    updated = False
    
    while i < len(lines):
        line = lines[i]
        
        # Case A: Heading matches q_key
        if line.startswith("#") and q_key.lower() in line.lower():
            new_lines.append(line)
            i += 1
            section_lines = []
            heading_level = len(line) - len(line.lstrip("#"))
            
            while i < len(lines):
                next_line = lines[i]
                if next_line.startswith("#"):
                    next_level = len(next_line) - len(next_line.lstrip("#"))
                    if next_level <= heading_level:
                        break
                if next_line.strip() == "---":
                    break
                section_lines.append(next_line)
                i += 1
            
            section_content = "\n".join(section_lines)
            
            if is_website:
                stripped = section_content.strip()
                if stripped:
                    section_content = section_content.replace(stripped, new_ans)
                    updated = True
            else:
                if "> " in section_content or section_content.strip().startswith(">"):
                    # Blockquote format
                    blockquote_ans = "\n".join([f"> {p}" if p.strip() else ">" for p in new_ans.split("\n")])
                    sub_lines = section_content.split("\n")
                    first_bq = -1
                    last_bq = -1
                    for idx, sl in enumerate(sub_lines):
                        if sl.strip().startswith(">"):
                            if first_bq == -1:
                                first_bq = idx
                            last_bq = idx
                    if first_bq != -1:
                        sub_lines[first_bq:last_bq+1] = [blockquote_ans]
                        section_content = "\n".join(sub_lines)
                        updated = True
                elif "**AI:**" in section_content:
                    parts = section_content.split("**AI:**", 1)
                    section_content = parts[0] + "**AI:** " + new_ans
                    updated = True
                elif "AI:" in section_content:
                    parts = section_content.split("AI:", 1)
                    section_content = parts[0] + "AI: " + new_ans
                    updated = True
                else:
                    stripped = section_content.strip()
                    if stripped:
                        section_content = section_content.replace(stripped, new_ans)
                        updated = True
                        
            new_lines.append(section_content)
            continue

        # Case B: Plain text line matches q_key (e.g. in website.md)
        elif (not line.startswith(("#", "*", ">", "-", "1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9.", "0.")) 
              and q_key.lower() in line.lower() 
              and len(line.strip()) > 5):
            new_lines.append(line)
            i += 1
            section_lines = []
            while i < len(lines):
                next_line = lines[i]
                if next_line.startswith("#") or (not next_line.strip() and len(section_lines) > 0):
                    break
                section_lines.append(next_line)
                i += 1
            
            section_content = "\n".join(section_lines)
            stripped = section_content.strip()
            if stripped:
                section_content = section_content.replace(stripped, new_ans)
                updated = True
            new_lines.append(section_content)
            continue
            
        new_lines.append(line)
        i += 1
        
    if updated:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(new_lines))
        return True
    return False

def main():
    parser = argparse.ArgumentParser(description="Skill: Cập nhật Câu Hỏi & Câu Trả Lời cho các khóa học.")
    parser.add_argument("--domain", required=True, help="Tên hoặc ký hiệu của khóa học/domain (ví dụ: ancl, alt, oplw).")
    parser.add_argument("--key", required=True, help="Từ khóa hoặc câu hỏi cần khớp (ví dụ: 'tài khoản AI trả phí' hoặc 'tốn nhiều tiền').")
    parser.add_argument("--answer", required=True, help="Nội dung câu trả lời mới.")
    args = parser.parse_args()

    base_dir = "/root/Second_Brain/01_chuong_trinh_dao_tao"
    target_dir = find_target_dir(base_dir, args.domain)
    
    if not target_dir:
        print(f"Error: Không tìm thấy thư mục dữ liệu cho domain '{args.domain}'")
        sys.exit(1)
        
    print(f"Thư mục dữ liệu tìm thấy: {target_dir}")

    # Process all files in the target directory
    for file_name in os.listdir(target_dir):
        file_path = os.path.join(target_dir, file_name)
        if not os.path.isfile(file_path):
            continue
            
        if file_name.endswith(".csv") and "nap_ai_fanpage" in file_name:
            if update_csv_file(file_path, args.key, args.answer):
                print(f"-> Đã cập nhật file CSV: {file_name}")
            else:
                print(f"   Không tìm thấy từ khóa '{args.key}' trong file CSV: {file_name}")
                
        elif file_name.endswith(".xlsx") and "nap_ai_fanpage" in file_name:
            if update_xlsx_file(file_path, args.key, args.answer):
                print(f"-> Đã cập nhật file XLSX: {file_name}")
            else:
                print(f"   Không tìm thấy từ khóa '{args.key}' trong file XLSX: {file_name}")
                
        elif file_name.endswith(".md") and "chatbot_tu_van" in file_name:
            if update_md_file(file_path, args.key, args.answer, is_website=False):
                print(f"-> Đã cập nhật file Chatbot MD: {file_name}")
            else:
                print(f"   Không tìm thấy từ khóa '{args.key}' trong file Chatbot MD: {file_name}")
                
        elif file_name.endswith(".md") and "lam_website" in file_name:
            # We want to match with website format
            if update_md_file(file_path, args.key, args.answer, is_website=True):
                print(f"-> Đã cập nhật file Website MD: {file_name}")
            else:
                print(f"   Không tìm thấy từ khóa '{args.key}' trong file Website MD: {file_name}")

if __name__ == "__main__":
    main()
