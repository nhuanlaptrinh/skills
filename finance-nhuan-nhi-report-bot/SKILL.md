---
name: finance-nhuan-nhi-report-bot
description: Báo cáo tài chính nhà Nhuần Nhi theo ngày/tháng qua Telegram, đọc CSV chi tiêu gia đình và doanh thu công ty trong /root/Data/finance_nhuan_nhi, chạy thủ công hoặc cron 21:00 hằng ngày.
---

# Finance Nhuần Nhi Report Bot

Dùng skill này khi cần xem, kiểm tra, chạy lại, sửa hoặc thiết lập báo cáo tài chính nhà Nhuần Nhi qua Telegram.

## Đường dẫn

- Dữ liệu: `/root/Data/finance_nhuan_nhi`
- App: `/root/Automation/finance/finance_nhuan_nhi_report_bot`
- Script chính: `/root/Automation/finance/finance_nhuan_nhi_report_bot/scripts/send_daily_finance_report.py`
- Wrapper cron: `/root/Automation/finance/finance_nhuan_nhi_report_bot/scripts/run_daily_report.sh`
- Log: `/root/Automation/finance/finance_nhuan_nhi_report_bot/logs/daily_report.log`
- Env local: `/root/Automation/finance/finance_nhuan_nhi_report_bot/.env`
- Env mẫu: `/root/Automation/finance/finance_nhuan_nhi_report_bot/.env.example`

## Cấu trúc dữ liệu theo tháng

```text
/root/Data/finance_nhuan_nhi/YYYY/YYYY-MM/
├── chi_tieu.csv
├── doanh_thu_cong_ty.csv
└── bao_cao_thang.md
```

## Input CSV

### `chi_tieu.csv`

Cột bắt buộc:

```csv
ngay,loai,danh_muc,noi_dung,so_tien,nguoi,ghi_chu
```

### `doanh_thu_cong_ty.csv`

Cột bắt buộc:

```csv
ngay,doanh_thu_du_kien,doanh_thu_thuc_te,chi_momo,chi_bidv,chi_ads,chi_cty,ghi_chu
```

## Lệnh dry-run

Xem báo cáo nhưng không gửi Telegram:

```bash
/usr/bin/python3 /root/Automation/finance/finance_nhuan_nhi_report_bot/scripts/send_daily_finance_report.py --date 2026-07-06 --dry-run
```

## Lệnh chạy thật

Gửi báo cáo Telegram theo ngày hiện tại:

```bash
/root/Automation/finance/finance_nhuan_nhi_report_bot/scripts/run_daily_report.sh
```

Gửi báo cáo cho một ngày cụ thể:

```bash
/usr/bin/python3 /root/Automation/finance/finance_nhuan_nhi_report_bot/scripts/send_daily_finance_report.py --date YYYY-MM-DD
```

## Cron

Lịch chuẩn: 21:00 hằng ngày giờ Việt Nam, tương đương 14:00 UTC trên VPS.

```cron
# finance_nhuan_nhi_report_bot: send daily finance report at 21:00 Asia/Ho_Chi_Minh (14:00 UTC)
0 14 * * * /root/Automation/finance/finance_nhuan_nhi_report_bot/scripts/run_daily_report.sh
```

## Output Telegram

Báo cáo gồm:

- Tổng chi/thu gia đình trong ngày.
- Doanh thu công ty dự kiến và thực tế trong ngày.
- Chi tiết từng khoản chi trong ngày.
- Lũy kế tháng.
- Top danh mục chi tháng.

## Fast Path cho bot Telegram

- Với yêu cầu tài chính thông thường, chỉ chọn đúng tháng/ngày và các file cần thiết; không quét toàn bộ workspace, lịch sử phiên hoặc thư mục skill.
- Gom các thao tác đọc độc lập vào cùng một lượt tool; ưu tiên đọc `chi_tieu.csv`, `doanh_thu_cong_ty.csv` và `bao_cao_thang.md` theo lô trước khi tính toán.
- Ưu tiên tool đọc/ghi file. Không dùng `exec` để đọc, tìm kiếm, parse hoặc cập nhật CSV/XLSX nếu tool file hoặc script chuyên dụng trong skill đã đáp ứng.
- Chỉ dùng `exec` cho dry-run được nêu trong skill, hoặc khi người dùng yêu cầu kiểm tra hệ thống/không có tool tương đương; không chạy healthcheck VPS diện rộng cho câu hỏi tài chính đơn giản.
- Sau khi gom dữ liệu, trả lời trong ít lượt model/tool nhất có thể; nếu cần cập nhật thì ghi một lần và chạy kiểm tra cần thiết một lần.
- Nếu người dùng hỏi đồng thời nghiệp vụ tài chính và tình trạng VPS, tách hai phần; không để chẩn đoán hệ thống làm chậm phản hồi tài chính.

## Quy tắc an toàn

- Không ghi Telegram bot token, mật khẩu, cookie, OTP, private key vào skill, README, log hoặc câu trả lời.
- File `.env` phải có quyền `600` và không được in nội dung ra terminal.
- Khi sửa cron, backup crontab vào `/root/_Backups` trước.
- Khi test, ưu tiên `--dry-run` trước khi gửi Telegram thật.
- Không thay thế toàn bộ crontab; chỉ append job của project nếu chưa tồn tại.

## Báo cáo Excel cuối tháng

Khi người dùng yêu cầu tổng hợp báo cáo cuối tháng, luôn xuất kèm **01 file Excel hoàn chỉnh** theo form chuẩn tại:

```text
/root/.agents/skills/finance-nhuan-nhi-report-bot/templates/bao_cao_tai_chinh_nhuan_nhi_mau.xlsx
```

### Quy trình bắt buộc

1. Đọc toàn bộ `chi_tieu.csv` và `doanh_thu_cong_ty.csv` của đúng tháng cần báo cáo.
2. Giữ nguyên cấu trúc 3 sheet của file mẫu: `Tổng quan`, `Chi tiêu chi tiết`, `Doanh thu & chi công ty`.
3. Tính riêng theo **danh mục**, không chỉ theo trường `loai`:
   - `Tích luỹ`: cộng mọi dòng có `danh_muc` là `Tích luỹ`, kể cả khi `loai` là `tích luỹ` hoặc `chi`.
   - `Tiết kiệm ngân hàng`: cộng mọi danh mục chứa `Tiết kiệm` (ví dụ `Tiết kiệm gửi NH`).
   - `Chi gia đình`: tổng các khoản chi còn lại, không gồm tiết kiệm và tích luỹ.
   - `Tổng chi công ty`: `chi_momo + chi_bidv + chi_ads + chi_cty`.
   - `Thu nhập tháng`: doanh thu thực tế trừ tổng chi công ty.
   - `Còn lại tạm tính (đã trừ ads)`: thu nhập tháng trừ chi gia đình, tiết kiệm và tích luỹ.
4. Điền đầy đủ tiêu đề `CHI GIA ĐÌNH THEO DANH MỤC`, tổng hợp danh mục và toàn bộ dữ liệu chi tiết trong tháng.
5. Trước khi gửi, mở lại file để kiểm tra: file tồn tại/đọc được, 3 sheet đủ dữ liệu, và các tổng `Tích luỹ`, `Tiết kiệm`, `Chi gia đình`, `Còn lại` khớp dữ liệu CSV.
6. Đặt tên file: `bao_cao_tai_chinh_nhuan_nhi_YYYY-MM_hoan_chinh.xlsx` và gửi kèm trong phản hồi.

## Quy tắc ghi chú trong Excel

Ở sheet `Doanh thu & chi công ty`, cột `Ghi chú` chỉ ghi các lưu ý đặc biệt phát sinh khi ghi nhận khoản thu/chi (ví dụ: đính chính, bổ sung ngày khác, chuyển tiền cá nhân không tính doanh thu, hoàn phí khách hàng, hoặc nội dung chi công ty/ads/Momo/BIDV cần lưu ý). Không lặp lại từng số tiền doanh thu, phép cộng các khoản thu, hay tổng doanh thu trong ghi chú vì các số liệu đã có ở các cột tương ứng. Khi lập báo cáo tháng sau, áp dụng quy tắc này mặc định.
