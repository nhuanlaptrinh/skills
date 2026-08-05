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

## Quy tắc an toàn

- Không ghi Telegram bot token, mật khẩu, cookie, OTP, private key vào skill, README, log hoặc câu trả lời.
- File `.env` phải có quyền `600` và không được in nội dung ra terminal.
- Khi sửa cron, backup crontab vào `/root/_Backups` trước.
- Khi test, ưu tiên `--dry-run` trước khi gửi Telegram thật.
- Không thay thế toàn bộ crontab; chỉ append job của project nếu chưa tồn tại.
