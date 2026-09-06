---
name: "openclaw-large-pdf-recovery"
description: "Nhan PDF lon tu file local hoac link HTTPS, kiem tra tinh hop le, tach thanh cac phan duoi gioi han staging 50 MiB cua OpenClaw, trich text va tao manifest de phan tich tiep."
---

# OpenClaw large PDF recovery

Dung skill nay khi Telegram da tai PDF/video nhung OpenClaw bao `Inbound media staging skipped` hoac file vuot 50 MiB. Telegram Local Bot API co the tai toi 2000 MiB, nhung sandbox staging cua OpenClaw 2026.8.2 gioi han cung 50 MiB; dat part o muc 45 MiB de co du margin.

Muc tieu cua skill la tach file lon de OpenClaw truy cap duoc, sau do phan tich PDF bang tool `pdf` va model vision. Tach part chi la buoc van chuyen; khong duoc coi file `.txt` rong la bang chung khong doc duoc ban scan.

## Pham vi va an toan

- Khong xoa hoac sua file goc trong `/root/.openclaw/media/inbound`.
- Khong ghi URL day du vao log/manifest; link HTTPS co the chua token. Chi luu hostname va hash file.
- Khong in noi dung tai lieu ra man hinh. Manifest chi luu kich thuoc, checksum, so trang va so ky tu text.
- Chi nhan link `https://`; link Google Drive/SharePoint can mot URL tai truc tiep va quyen truy cap phu hop.
- Luon dung document venv de co PyMuPDF:
  `/root/.openclaw/tools/document-venv/bin/python`.

## Cong cu

- Script global: `/root/.agents/skills/openclaw-large-pdf-recovery/scripts/recover_large_pdf.py`
- Ban workspace cua member: `/root/.openclaw/workspace/skills/openclaw-large-pdf-recovery/scripts/recover_large_pdf.py`
- Trong container `user-minhvuong`, duong dan host tuong ung la:
  `/root/Apps/member_vps/docker-users/data/minhvuong/root/.openclaw/workspace/skills/openclaw-large-pdf-recovery/`.

## Quy trinh

1. Tim file moi nhat trong inbound, khong di chuyen hay xoa file:

   ```bash
   find /root/.openclaw/media/inbound -maxdepth 1 -type f -iname '*.pdf' -printf '%T@ %p\n' | sort -nr | head
   ```

2. Dry-run de kiem tra dau PDF, so trang, SHA-256 va text nhung khong tao part:

   ```bash
   /root/.openclaw/tools/document-venv/bin/python \
     /root/.openclaw/workspace/skills/openclaw-large-pdf-recovery/scripts/recover_large_pdf.py \
     --input /root/.openclaw/media/inbound/<file>.pdf --target-mb 45 --dry-run
   ```

3. Tach PDF va trich text vao job rieng:

   ```bash
   /root/.openclaw/tools/document-venv/bin/python \
     /root/.openclaw/workspace/skills/openclaw-large-pdf-recovery/scripts/recover_large_pdf.py \
     --input /root/.openclaw/media/inbound/<file>.pdf \
     --output-dir /root/.openclaw/workspace/media/large-pdf/<job-id> \
     --target-mb 45
   ```

   Moi part co ten kem khoang trang, file `.txt` cung ten va `manifest.json`. Script mo lai tung part, kiem tra checksum va bao phu du so trang.

4. Phan tich ban scan bang vision model:

   - Uu tien dung tool `pdf` cua OpenClaw voi `pdf` la duong dan file goc, `prompt` neu ro yeu cau can doc, va `pages` theo tung khoang trang.
   - Tool `pdf` tu chon trich text neu co lop chu; neu text qua it, no render cac trang thanh anh va gui anh cho model vision da cau hinh tai `agents.defaults.pdfModel`.
   - Voi ban ve A1, khong nap 40 trang trong mot lan neu can doc thong so nho; chia thanh cac khoang 1-5, 6-10... hoac chi dinh cac trang can kiem tra.
   - Khong suy dien thong so tu ten file, `pdfinfo`, kich thuoc anh, metadata hoac nhom cong viec. Moi con so ky thuat phai gan voi so trang/vung da xem.
   - Neu chu nho khong ro, tra loi phan nao doc chac, phan nao chua xac nhan va yeu cau trang/vung phan giai cao hon; khong tu dien gia tri.

   Vi du tool call logic:

   ```text
   pdf: /root/.openclaw/media/inbound/<file>.pdf
   pages: 1-5
   prompt: Doc cac trang ban ve scan bang cach xem anh render. Trich ten ban ve, ghi chu va thong so nhin thay ro; gan moi ket qua voi so trang; khong doan so lieu mo.
   maxBytesMb: 2000
   ```

   Neu tool `pdf` khong co trong agent surface, dung `pdftoppm` render trang/vung vao workspace roi chuyen anh cho mot luot vision duoc ho tro. Khong gui file goc 155 MB truc tiep vao prompt.

4. Neu nguoi dung khong gui duoc file, dung link tai HTTPS truc tiep:

   ```bash
   /root/.openclaw/tools/document-venv/bin/python \
     /root/.openclaw/workspace/skills/openclaw-large-pdf-recovery/scripts/recover_large_pdf.py \
     --url 'https://example.invalid/download.pdf' \
     --output-dir /root/.openclaw/workspace/media/large-pdf/<job-id> \
     --target-mb 45
   ```

   Script tai theo stream, gioi han mac dinh 2000 MiB, kiem tra `%PDF-`, sau do xoa ban tai tam; khong luu URL day du.

## OCR va tai lieu scan

`--ocr` chi ghi nhan/truyen trang thai OCR. Neu `tesseract` va `pdftoppm` co san, co the bo sung buoc OCR rieng cho cac trang scan da chon; neu thieu, tach PDF va text nhung van thanh cong, manifest se co canh bao. Tesseract la OCR phu tro, khong thay the vision model. Khong cai them goi tren production neu chua backup va danh gia dung luong.

## Kiem tra sau khi chay

- Tat ca part mo duoc bang PyMuPDF va co `size_bytes < 52428800` (truong hop mot trang don le qua lon se duoc ghi warning).
- `manifest.json` co SHA-256 cua file goc va tung part; so trang cac part phai phu hop file goc.
- Chi gui tung part qua Telegram sau khi xac nhan ton tai, doc duoc, dung destination va co receipt `messageId` theo reliable-media-delivery.
- Neu can ghep lai o may khac, dung `qpdf --empty --pages part-*.pdf -- merged.pdf` khi qpdf duoc cai; khong ghi de file goc.

## Rerun

Dung `--output-dir` moi cho moi job. Neu rerun cung thu muc, kiem tra file hien co truoc; khong xoa thu muc production tu dong.
