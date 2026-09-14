---
name: zalo-separated-services
description: Vận hành lớp tách riêng Login, Sender và n8n Adapter cho Zalo automation.
---

Các entrypoint dùng lại project hiện tại `/root/Automation/zalo/01_zalo_lg_se` mà không di chuyển profile.

- Login: `/root/Automation/zalo/zalo_login_service/open_rdp.sh`, `status.sh`
- Sender: `/root/Automation/zalo/zalo_sender_service/check.sh`, `send.sh`
- Adapter: `/root/Automation/zalo/zalo_n8n_adapter/preflight.sh`, `run.sh`

Kiểm tra an toàn:
```bash
/root/Automation/zalo/zalo_sender_service/check.sh
/root/Automation/zalo/zalo_n8n_adapter/preflight.sh
```

Mở đăng nhập RDP:
```bash
/root/Automation/zalo/zalo_login_service/open_rdp.sh
```

Không chạy `send.sh` hoặc `run.sh` nếu chưa được yêu cầu gửi thật. Không tạo/copy profile Zalo mới; chỉ dùng profile hiện tại.
