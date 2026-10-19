---
name: core-openclaw-runtime
description: Điều phối cấu hình runtime, model, timeout, memory, workspace, session và policy OpenClaw.
---

## Chính sách model — 2026-10-19

- Chỉ dùng đúng bốn model hội thoại/suy luận: `GPT-6.1-sol`, `GPT-6-terra`, `GPT-6-luna`, `GPT-6-astra`. Mặc định khi cài mới hoặc không chỉ định model là `GPT-6.1-sol`.
- Primary, fallback và lựa chọn trong wizard chỉ lấy từ danh sách này; không tự dùng alias/model cũ hoặc bật DeepSeek dù môi trường có key. Giữ provider hiện có và ghép `<provider>/<model-id>` đúng case.
- Trước khi apply, xác minh model đích trong `/v1/models` của provider thực tế; nếu không có thì dừng, không tự đổi tên hay chọn model ngoài danh sách. Chỉ cấu hình hiểu ảnh khi đã kiểm tra backend hỗ trợ.
- Đây là chính sách chọn model, không phải quyền tự đổi runtime đang chạy. Không đổi model STT/TTS/tạo ảnh thành model chat; các tính năng media chuyên dụng giữ workflow và kiểm tra riêng.

Đây là skill chính (entry point). Dùng nó để chọn và điều phối các skill chuyên biệt bên dưới; không tạo workflow trùng lặp khi skill phụ đã có hướng dẫn chi tiết.

Skill liên quan: openclaw-host-upgrade, validate-openclaw-json, openclaw-member-model-switch, openclaw-timeout-guard, openclaw-memory-fts-only, openclaw-session-token-rotation, set-openclaw-thinking-levels, unify-openclaw-bot-workspace

Giữ nguyên nguyên tắc an toàn của project và đọc AGENTS.md, Second AI Brain, checklist production trước khi thay đổi hệ thống.
