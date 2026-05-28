---
name: xuat-pdf-ebook-sach
description: Xuất nội dung Markdown chương sách, ebook, giáo trình, tài liệu dài thành PDF chuyên nghiệp, dễ đọc, có trang bìa, giãn dòng thoáng, heading rõ, khung ghi nhớ/bài tập, và có thể chèn logo. Use when Codex needs to convert `.md` ebook/book/chapter content to a polished PDF for reading or sharing.
---

# Xuat PDF Ebook Sach

## Workflow

1. Xac dinh file Markdown nguon va duong dan PDF dich.
2. Neu co logo, uu tien dung logo do tren trang bia bang tham so `--logo`.
3. Dung script `scripts/export_ebook_pdf.py` de xuat PDF thay vi viet lai HTML/CSS moi lan.
4. Sau khi xuat, kiem tra PDF bang PyMuPDF (`fitz`) hoac render nhanh 1-3 trang dau/cuoi de xem bo cuc.
5. Neu chu qua day, tang trang bang cach tang line-height, tang margin, hoac bat `--split-long-paragraphs`.

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
- Trang bia toi gian, co logo neu co.
- Doan van dai duoc tach thanh cum ngan hon trong ban PDF de doc de hon, khong sua file Markdown goc.
- Heading `##` co mau nhan nhe va duong ke tren.
- Phan `Chuong nay chi can nho...` va `Bai tap cuoi chuong` duoc dong khung rieng.

## Luu Y

- Khong sua noi dung Markdown goc neu nguoi dung chi yeu cau xuat PDF.
- Neu duong dan co tieng Viet tren Windows, uu tien chay script tu thu muc cha va truyen duong dan tu PowerShell, khong hard-code chuoi Unicode trong inline Python.
- Neu Chrome khong co trong PATH, script tu tim Chrome/Edge theo duong dan cai dat pho bien tren Windows.
- Sau khi render preview tam, xoa anh preview va file HTML tam truoc khi ket thuc.
