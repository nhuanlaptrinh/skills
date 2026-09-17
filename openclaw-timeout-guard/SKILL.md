---
name: openclaw-timeout-guard
description: Cấu hình, nâng cấp, kiểm tra hoặc đồng bộ timeoutSeconds (mặc định 180s) cho OpenClaw Bot trên Docker member VPS hoặc standalone host VPS, phòng chống lỗi "Request timed out before a response was generated" khi mô hình xử lý file PDF nặng, video hoặc khi upstream proxy có timeout dài (120s).
---

# OpenClaw Timeout Guard

## Khi nào dùng

Dùng skill này khi:
1. Bot OpenClaw (Telegram / Zalo) báo lỗi:
   ```text
   Request timed out before a response was generated. Please try again, or increase agents.defaults.timeoutSeconds in your config.
   ```
2. Bot cần xử lý các tác vụ nặng:
   - File PDF quét/nhiều trang (>80k tokens)
   - Tác vụ dựng video, media hoặc OCR
   - Xử lý kịch bản phân tích phức tạp
3. Upstream 9Router / Reliable Proxy đang đặt `REQUEST_TIMEOUT_MS = 120s` và cần đồng bộ thời gian kiên nhẫn của Bot OpenClaw (`agents.defaults.timeoutSeconds = 180s`) để đảm bảo quy tắc:
   $$\text{Client Timeout (180s)} > \text{Proxy Upstream Timeout (120s)}$$
4. Cần kiểm tra (audit) hoặc áp dụng đồng loạt cho một hoặc toàn bộ member VPS trên server.

---

## Đường dẫn công cụ chuẩn

Script tự động quản lý timeout đặt tại:
```text
/root/.agents/skills/openclaw-timeout-guard/scripts/manage_openclaw_timeout.py
```

Thư mục lưu backup tự động:
```text
/root/_Backups/openclaw-timeout-guard/<member_or_target>/<UTC_timestamp>/openclaw.json.before
```

---

## Lệnh kiểm tra (Audit / Read-only)

Kiểm tra thời gian timeout hiện tại mà không thay đổi bất kỳ file nào:

```bash
# 1. Kiểm tra 1 member VPS cụ thể
python3 /root/.agents/skills/openclaw-timeout-guard/scripts/manage_openclaw_timeout.py --member tranvanminh --check

# 2. Quét kiểm tra TOÀN BỘ các member VPS trên server
python3 /root/.agents/skills/openclaw-timeout-guard/scripts/manage_openclaw_timeout.py --member all --check

# 3. Kiểm tra OpenClaw trên host chính (hoặc VPS độc lập)
python3 /root/.agents/skills/openclaw-timeout-guard/scripts/manage_openclaw_timeout.py --config /root/.openclaw/openclaw.json --check
```

---

## Lệnh chạy thử (Dry-run)

Mặc định nếu không truyền `--apply`, script luôn chạy ở chế độ **Dry-run an toàn**:

```bash
# Thử nghiệm nâng timeout lên 180s (mặc định) cho member
python3 /root/.agents/skills/openclaw-timeout-guard/scripts/manage_openclaw_timeout.py --member tranvanminh

# Thử nghiệm với số giây tùy chọn (ví dụ 300s)
python3 /root/.agents/skills/openclaw-timeout-guard/scripts/manage_openclaw_timeout.py --member tranvanminh --timeout 300
```

---

## Lệnh chạy thật (Apply)

Sau khi kiểm tra dry-run, thêm cờ `--apply` cùng các tùy chọn xác thực:

```bash
# 1. Nâng timeout lên 180s cho 1 member, tự động backup + validate + reload Gateway
python3 /root/.agents/skills/openclaw-timeout-guard/scripts/manage_openclaw_timeout.py \
  --member tranvanminh \
  --timeout 180 \
  --apply \
  --validate \
  --reload

# 2. Áp dụng cho host OpenClaw hoặc file config chỉ định trên VPS khác
python3 /root/.agents/skills/openclaw-timeout-guard/scripts/manage_openclaw_timeout.py \
  --config /root/.openclaw/openclaw.json \
  --timeout 180 \
  --apply \
  --validate \
  --reload

# 3. Áp dụng kèm kiểm tra khói cô lập (smoke test không gửi tin nhắn thật)
python3 /root/.agents/skills/openclaw-timeout-guard/scripts/manage_openclaw_timeout.py \
  --member tranvanminh \
  --timeout 180 \
  --apply \
  --validate \
  --reload \
  --smoke-test
```

---

## Input / Output

- **Input**:
  - Tên member VPS (ví dụ `tranvanminh`, `tienphong`, `avata`) hoặc đường dẫn tới `openclaw.json`.
  - Mức timeout mong muốn (mặc định khuyến nghị: `180` giây).
- **Output**:
  - File cấu hình `openclaw.json` được cập nhật nguyên tử (atomic write, giữ nguyên quyền file).
  - Bản sao lưu nguyên vẹn trước khi sửa tại `/root/_Backups/openclaw-timeout-guard/<target>/<timestamp>/openclaw.json.before`.
  - Kết quả xác thực cú pháp `openclaw config validate`.
  - Supervisor / systemd service `openclaw-gateway` được khởi động lại mượt mà.

---

## Kiểm tra sau khi thực hiện

1. Kiểm tra trạng thái kênh Telegram / Zalo trong container:
   ```bash
   docker exec user-<member> openclaw channels status --probe
   ```
   Xác nhận trả về: `running, connected, works`.

2. Kiểm tra tiến trình Supervisor:
   ```bash
   docker exec user-<member> supervisorctl status openclaw-gateway
   ```

3. Kiểm tra log gateway nếu cần:
   ```bash
   docker exec user-<member> tail -n 50 /root/.openclaw/logs/gateway.log
   ```

---

## Khôi phục (Rollback)

Nếu cần hoàn tác lại cấu hình trước đó:
```bash
# 1. Khôi phục từ bản backup
cp /root/_Backups/openclaw-timeout-guard/<member>/<timestamp>/openclaw.json.before \
   /root/Apps/member_vps/docker-users/data/<member>/root/.openclaw/openclaw.json

# 2. Xác thực và reload lại Gateway
docker exec user-<member> openclaw config validate
docker exec user-<member> supervisorctl restart openclaw-gateway
```

---

## Quy tắc an toàn

1. Không bao giờ in hoặc ghi API key, Bot token, password, private key hoặc secret trong argv, log hay tài liệu.
2. Luôn chạy `--check` hoặc `--dry-run` trước khi dùng `--apply`.
3. Khi reload Gateway trong member Docker, chỉ reload service `openclaw-gateway` của Supervisor, **không restart cả container Docker** (để tránh ngắt kết nối SSH, XRDP, Nginx của người dùng).
4. Không gửi tin nhắn thử nghiệm thật vào Telegram/Zalo của khách hàng. Chỉ dùng isolated session key cho smoke-test.
5. Sau khi cập nhật production, ghi nhận vào `/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md`.
