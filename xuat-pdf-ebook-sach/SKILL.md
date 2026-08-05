---
name: xuat-pdf-ebook-sach
description: Xuất nội dung Markdown chương sách, ebook, giáo trình, tài liệu dài thành PDF chuyên nghiệp, dễ đọc, có trang bìa, giãn dòng thoáng, heading rõ, khung ghi nhớ/bài tập, và có thể chèn logo. Use when Codex needs to convert `.md` ebook/book/chapter content to a polished PDF for reading or sharing.
---

# Xuat PDF Ebook Sach

## Workflow

1. Xac dinh file Markdown nguon va duong dan PDF dich.
2. Neu co logo, uu tien dung logo do tren trang bia bang tham so `--logo`; logo phai giu dung ty le, khong keo gian, khong bop meo.
3. Dung script `scripts/export_ebook_pdf.py` de xuat PDF thay vi viet lai HTML/CSS moi lan.
4. Ap dung form bia chuyen nghiep Anh Lap Trinh ben duoi khi lam ebook cho anh Nhuan.
5. Sau khi xuat, kiem tra PDF bang PyMuPDF (`fitz`) hoac render nhanh 1-3 trang dau/cuoi de xem bo cuc, dac biet la trang bia.
6. Neu chu qua day, tang trang bang cach tang line-height, tang margin, hoac bat `--split-long-paragraphs`.


## Form bia chuyen nghiep Anh Lap Trinh

Giu form nay cho cac ebook sau neu nguoi dung khong yeu cau style khac. Day la form bia ebook OpenClaw da duoc anh Nhuan duyet ngay 2026-06-24.

- Kho A4.
- Nen bia toi, sach, hien dai; uu tien xanh than/den xanh.
- Co grid/pattern nhe hoac mang gradient nhe, khong roi mat.
- Logo Anh Lap Trinh dat o vung tren cua bia, kich thuoc vua phai, dung `object-fit: contain`; tuyet doi khong bop meo/keo gian logo.
- Co kicker nho phia tren tieu de, vi du: `EBOOK HUONG DAN THUC CHIEN`, `TAI LIEU THUC CHIEN`, hoac nhan phu hop noi dung.
- Tieu de chinh viet lon, ro, uu tien 2-4 dong, chu trang hoac gan trang, tuong phan cao.
- Co subtitle/mo ta ngan ngay duoi tieu de, giai thich loi ich chinh cua ebook.
- Co mot dong benefit/dinh vi ngan neu phu hop.
- Co thong tin tac gia/thuong hieu va phien ban/ngay o gan cuoi bia.
- Co cau brand/tagline o cuoi bia: `Cu ung dung vao cong viec di, vuong thi go.`
- Bo cuc thoang, canh le deu, tranh nhoi qua nhieu chu.

Template luu tai: `templates/anh_lap_trinh_ebook_cover.md`.

Vi du da duoc anh Nhuan duyet form:

```text
EBOOK HUONG DAN THUC CHIEN
CAI DAT
OPENCLAW
Dieu khien may tinh qua Telegram, Zalo va web chat
Lam viec o bat ky dau — chi can mot chiec dien thoai
Nguyen Van Nhuan - Anh Lap Trinh • Phien ban 2026_06_23
Cu ung dung vao cong viec di, vuong thi go.
```

## Command Mau

```powershell
python C:\Users\nhuan\.codex\skills\xuat-pdf-ebook-sach\scripts\export_ebook_pdf.py `
  --input "path\to\chapter.md" `
  --output "path\to\chapter.pdf" `
  --logo "path\to\logo.png" `
  --subtitle "Ebook: Tao tro ly A.I lam thay cong viec cho ban"
```

Neu khong truyen `--output`, script tu tao PDF cung ten voi file Markdown.

## Style Mac Dinh

- Kho A4, le thoang.
- Font `Segoe UI`, fallback Arial.
- Trang bia chuyen nghiep theo form Anh Lap Trinh: nen toi, grid nhe, logo dung ty le, tieu de lon, subtitle ro, tagline thuong hieu.
- Doan van dai duoc tach thanh cum ngan hon trong ban PDF de doc de hon, khong sua file Markdown goc.
- Heading `##` co mau nhan nhe va duong ke tren.
- Phan `Chuong nay chi can nho...` va `Bai tap cuoi chuong` duoc dong khung rieng.

## Luu Y

- Khong sua noi dung Markdown goc neu nguoi dung chi yeu cau xuat PDF.
- Neu duong dan co tieng Viet tren Windows, uu tien chay script tu thu muc cha va truyen duong dan tu PowerShell, khong hard-code chuoi Unicode trong inline Python.
- Neu Chrome khong co trong PATH, script tu tim Chrome/Edge theo duong dan cai dat pho bien tren Windows.
- Sau khi render preview tam, xoa anh preview va file HTML tam truoc khi ket thuc.
