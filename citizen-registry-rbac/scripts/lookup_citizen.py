#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Citizen Registry & Identity Lookup with RBAC Masking Support.
Part of the citizen-registry-rbac OpenClaw skill.
Uses only Python Standard Library (zipfile + xml.etree.ElementTree).
No third-party packages required (works directly on any Linux VPS or Windows).
"""

import sys
import os
import argparse
import json
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import unicodedata

# Force UTF-8 output across platforms
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

DEFAULT_DATA_PATHS = [
    os.environ.get("CITIZEN_DATA_FILE", ""),
    r"D:\DỮ LIỆU CÔNG VIỆC TẬP THỂ\DỮ LIỆU SAU SÁP NHẬP THÔN\NHÂN DÂN THÔN NGUYỄN BÌNH\BẢNG A6- TDP - NGUYỄN BÌNH 01.07.26 ( 0k ).xlsx",
    os.path.expanduser("~/.openclaw/data/bang_a6.xlsx"),
    os.path.expanduser("~/.config/citizen-registry-rbac/bang_a6.xlsx"),
    os.path.join(os.path.dirname(__file__), "..", "data", "bang_a6.xlsx")
]

def resolve_data_path(custom_path=None):
    if custom_path and os.path.exists(custom_path):
        return os.path.abspath(custom_path)
    for p in DEFAULT_DATA_PATHS:
        if p and os.path.exists(p):
            return os.path.abspath(p)
    return None

def remove_accents(input_str):
    if not input_str:
        return ""
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)]).lower()

def mask_cccd(cccd_str):
    if not cccd_str or len(cccd_str) < 6:
        return cccd_str
    return cccd_str[:4] + "******" + cccd_str[-2:]

def mask_phone(phone_str):
    if not phone_str or len(phone_str) < 7:
        return phone_str
    return phone_str[:3] + "****" + phone_str[-3:]

def parse_excel_date(serial):
    if not serial:
        return ""
    try:
        days = float(serial)
        dt = datetime(1899, 12, 30) + timedelta(days=days)
        return dt.strftime('%d/%m/%Y')
    except Exception:
        return str(serial)

def load_rows_from_xlsx(filepath):
    ns = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    with zipfile.ZipFile(filepath) as z:
        shared_strings = []
        if 'xl/sharedStrings.xml' in z.namelist():
            root_ss = ET.fromstring(z.read('xl/sharedStrings.xml'))
            shared_strings = [
                ''.join(t.text or '' for t in item.iter('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t'))
                for item in root_ss.findall('m:si', ns)
            ]

        # Prefer sheet1.xml
        sheet_target = 'xl/worksheets/sheet1.xml'
        if sheet_target not in z.namelist():
            sheets = [n for n in z.namelist() if n.startswith('xl/worksheets/sheet') and n.endswith('.xml')]
            if not sheets:
                raise ValueError("Không tìm thấy worksheet trong file excel.")
            sheet_target = sheets[0]

        sheet = ET.fromstring(z.read(sheet_target))

    rows = []
    for row in sheet.findall('.//m:row', ns):
        row_number = str(row.get('r'))
        vals = {}
        for cell in row.findall('m:c', ns):
            node = cell.find('m:v', ns)
            if node is None:
                continue
            col = cell.get('r', '')[:-len(row_number)]
            raw = node.text or ''
            val = shared_strings[int(raw)] if cell.get('t') == 's' and raw.isdigit() and int(raw) < len(shared_strings) else raw
            vals[col] = val
        if vals:
            vals['_row'] = row_number
            rows.append(vals)
    return rows

def query_records(rows, query, mask=False):
    query_clean = query.strip()
    query_norm = remove_accents(query_clean)
    matches = []

    for r in rows:
        stt = r.get('A', '').strip()
        stt2 = r.get('B', '').strip()
        name = r.get('C', '').strip()
        rel = r.get('D', '').strip()
        dob_raw = r.get('E', '').strip()
        gender = r.get('F', '').strip()
        phone = r.get('G', '').strip()
        cccd = r.get('H', '').strip()
        chu_ho = r.get('K', '').strip()
        ma_ho = r.get('L', '').strip()
        dia_chi = r.get('M', '').strip()
        ghi_chu = r.get('J', '').strip()

        name_norm = remove_accents(name)
        chu_ho_norm = remove_accents(chu_ho)

        is_match = False
        if query_norm and (query_norm in name_norm or query_norm in chu_ho_norm):
            is_match = True
        elif query_clean and (query_clean == cccd or (len(query_clean) >= 4 and query_clean in cccd)):
            is_match = True
        elif query_clean and (query_clean == phone or (len(query_clean) >= 4 and query_clean in phone)):
            is_match = True
        elif query_clean and query_clean.upper() == ma_ho.upper():
            is_match = True
        elif query_clean and (query_clean == stt or query_clean == stt2):
            is_match = True

        if is_match:
            dob = parse_excel_date(dob_raw)
            matches.append({
                'stt': stt or stt2 or r.get('_row'),
                'name': name,
                'rel': rel or ('Chủ hộ' if name == chu_ho else '-'),
                'dob': dob,
                'gender': gender,
                'phone': mask_phone(phone) if mask else phone,
                'cccd': mask_cccd(cccd) if mask else cccd,
                'chu_ho': chu_ho,
                'ma_ho': ma_ho,
                'dia_chi': dia_chi,
                'ghi_chu': ghi_chu
            })
    return matches

def main():
    parser = argparse.ArgumentParser(description="Tra cứu dữ liệu dân cư và CCCD có hỗ trợ phân quyền che số (RBAC).")
    parser.add_argument("query", nargs="*", help="Từ khóa tìm kiếm (Họ tên, CCCD, SĐT, Mã hộ, hoặc STT)")
    parser.add_argument("--data-file", help="Đường dẫn tới file Excel dữ liệu (mặc định lấy theo CITIZEN_DATA_FILE hoặc BẢNG A6)")
    parser.add_argument("--mask", action="store_true", help="Bật chế độ che mờ CCCD và SĐT (cho Group chat hoặc kênh công cộng)")
    parser.add_argument("--json", action="store_true", help="Xuất kết quả dưới định dạng JSON")
    parser.add_argument("--doctor", action="store_true", help="Kiểm tra môi trường và file dữ liệu")

    args = parser.parse_args()

    data_path = resolve_data_path(args.data_file)

    if args.doctor:
        print("=== Citizen Registry RBAC Doctor ===")
        print(f"Python: {sys.version}")
        print(f"Platform: {sys.platform}")
        print(f"Data File Target: {data_path or 'CHƯA TÌM THẤY'}")
        if data_path:
            try:
                rows = load_rows_from_xlsx(data_path)
                print(f"Tình trạng file: HỢP LỆ (Tổng số dòng đọc được: {len(rows)})")
                print("Doctor result: OK")
                sys.exit(0)
            except Exception as e:
                print(f"Lỗi đọc file: {e}")
                sys.exit(1)
        else:
            print("Lỗi: Không tìm thấy file dữ liệu. Vui lòng thiết lập biến môi trường CITIZEN_DATA_FILE hoặc truyền --data-file.")
            sys.exit(1)

    query_str = " ".join(args.query).strip()
    if not query_str:
        parser.print_help()
        sys.exit(0)

    if not data_path:
        print("Lỗi: Không tìm thấy file dữ liệu Excel. Hãy cấu hình --data-file hoặc biến môi trường CITIZEN_DATA_FILE.")
        sys.exit(1)

    try:
        rows = load_rows_from_xlsx(data_path)
    except Exception as e:
        print(f"Lỗi đọc dữ liệu: {e}")
        sys.exit(1)

    results = query_records(rows, query_str, mask=args.mask)

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return

    if not results:
        print(f"Không tìm thấy kết quả nào phù hợp với: '{query_str}'")
        return

    mode_label = "[Chế độ che mờ bảo vệ dữ liệu]" if args.mask else "[Chế độ đầy đủ cho Quản trị viên/DM]"
    print(f"Tìm thấy {len(results)} kết quả cho '{query_str}' {mode_label}:\n")
    for i, m in enumerate(results, 1):
        print(f"--- Kết quả #{i} ---")
        print(f"• STT trong bảng: {m['stt']}")
        print(f"• Họ và tên: {m['name']}")
        print(f"• Ngày sinh: {m['dob']} ({m['gender']})")
        print(f"• Số CCCD: {m['cccd'] or 'Chưa có'}")
        print(f"• Số điện thoại: {m['phone'] or 'Không có'}")
        print(f"• Quan hệ với chủ hộ: {m['rel'] or '-'}")
        print(f"• Chủ hộ: {m['chu_ho']} (Mã hộ: {m['ma_ho']})")
        print(f"• Địa chỉ: {m['dia_chi']}")
        if m['ghi_chu']:
            print(f"• Ghi chú: {m['ghi_chu']}")
        print()

if __name__ == '__main__':
    main()
