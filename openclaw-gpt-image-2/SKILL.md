---
name: openclaw-gpt-image-2
description: Dùng khi cần bật cho bot OpenClaw của member tạo ảnh bằng model gpt-image-2 qua 9router codex.anhlaptrinh.vn, dùng key 9router riêng của member đó; áp dụng mọi VPS.
---
# Bật tạo ảnh gpt-image-2 cho member OpenClaw

Mục tiêu: bot của member tạo ảnh bằng `cx/gpt-image-2` qua 9router (`https://codex.anhlaptrinh.vn/v1`), dùng **key 9router của chính member đó**, không đổi model đọc ảnh, không restart nếu hot reload được.

## Nguyên tắc
- Không chép key của member khác, không in key ra log/chat. Chỉ tham chiếu bằng biến môi trường (`${TEN_BIEN}`).
- Sao lưu `openclaw.json` trước khi sửa, kèm script rollback (mặc định chỉ xem trước, cần `--apply` mới khôi phục).
- Chỉ đụng container/member được yêu cầu. Không gửi ảnh thử vào chat của khách.
- Nếu VPS do bot khác quản lý (ví dụ VPS2/VPS3/VPS4), giao việc cho bot quản lý VPS đó kèm skill này, không tự SSH vào.

## Các bước
1. **Tìm mẫu đang chạy (nếu có).** Trên cùng VPS, tìm member đã có `cx/gpt-image-2` trong `openclaw.json` (grep `gpt-image-2`). Đọc khối `models.providers.openai`, `agents.defaults.mediaModels.image` và `plugins.entries.openai` để làm mẫu; bỏ qua phần key.
2. **Xác định key của member đích.** Xem provider 9router mà member đang dùng cho model chữ (ví dụ `token-codex`, `9rt`...) lấy key từ biến môi trường nào (ví dụ `TOKEN_CODEX_API_KEY`). Dùng lại đúng biến đó. Nếu member chưa có key 9router riêng, dừng lại và hỏi chủ.
3. **Sao lưu** `openclaw.json` của member vào `/root/_Backups/<member>-gpt-image-2-<UTC timestamp>/` cùng `rollback.py`.
4. **Sửa `openclaw.json` của member** (ưu tiên `openclaw config set` hoặc sửa JSON có kiểm tra hợp lệ):
   - Thêm provider `models.providers.openai`:
     - `baseUrl`: `https://codex.anhlaptrinh.vn/v1`
     - `api`: `openai-completions`
     - `apiKey`: `${<BIEN_KEY_CUA_MEMBER>}`
     - model `cx/gpt-image-2` (giữ cùng cấu trúc khai báo model như mẫu)
   - `agents.defaults.mediaModels.image.primary` = `openai/cx/gpt-image-2`
   - `plugins.entries.openai.enabled` = `true`
   - **Giữ nguyên** `imageModel` (model đọc/nhìn ảnh) và các model chữ.
   - Nếu member đã có provider tên `openai` dùng cho việc khác, đừng ghi đè; báo lại để chọn tên provider khác.
5. **Nạp cấu hình.** Để gateway hot reload; kiểm tra log thấy reload thành công và PID gateway không đổi. Chỉ restart gateway của đúng member nếu hot reload không nhận.
6. **Kiểm tra.**
   - Kênh Zalo/Telegram của member vẫn kết nối.
   - Tạo thử: `openclaw infer image generate --model openai/cx/gpt-image-2 --prompt "..."` trong container member; xác nhận ra file PNG (thường 1536x1024) trong workspace. Không gửi ảnh vào chat nào.
   - Tùy chọn: kiểm tra 9router `usageHistory` (`/root/.9router/db/data.sqlite`, mở read-only) thấy lượt `gpt-image-2` ghi đúng key của member.
7. **Báo cáo:** những gì đã đổi (không kèm key), đường dẫn backup + cách rollback, có restart hay không, trạng thái kênh, kết quả ảnh thử (đính kèm nếu chuyển được), và ghi chú bất thường có sẵn từ trước (không tự sửa).

## Lưu ý
- Hiện 9router ghi chi phí `gpt-image-2` bằng 0 vì bảng giá codex/openai chưa có mục này; nếu cần tính tiền khách thì phải thêm giá riêng.
- Nếu `infer image generate` lỗi 401/403: key không có quyền model `cx/gpt-image-2` trên 9router. Lỗi timeout: kiểm tra `agents.defaults.timeoutSeconds` và tình trạng reliable_chat_proxy.

Skill liên quan: core-openclaw-media, 9router-image
