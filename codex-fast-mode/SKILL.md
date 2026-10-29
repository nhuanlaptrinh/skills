---
name: codex-fast-mode
description: Bật fast cho model OpenClaw dùng API tương thích Codex hoặc cho Codex CLI/Extension, giữ nguyên model, nhà cung cấp và API key đang có.
---

# Fast cho OpenClaw và Codex

Phân biệt nơi cần bật: **OpenClaw chat** và **Codex CLI/Extension** có cấu hình riêng. Chỉ bật nơi người dùng yêu cầu; không tự chuyển model, nhà cung cấp hay sao chép API key. Fast là service tier, không phải reasoning effort.

## OpenClaw dùng API key nhà cung cấp Codex

1. Xác định đúng máy, user, instance OpenClaw, agent và model đang dùng. API key, URL và provider phải là cấu hình đã cài của OpenClaw; không lấy key của khách khác, không in key hoặc ghi key vào skill. Với nhiều instance, xác định `OPENCLAW_CONFIG_PATH`/`OPENCLAW_STATE_DIR` thực tế của Gateway và CLI đúng instance. Nếu model phiên hiện tại khác primary, xác định `provider/model` chính xác, không đổi primary.
2. Với OpenClaw từ 2026.10.6 và provider `api: openai-completions`, chạy `python <skill-dir>/scripts/switch_openclaw_fast.py --config <openclaw.json>`; thêm `--model-ref <provider/model>` cho model phiên khác primary, hoặc `--agent <id>` để giới hạn agent có cấu hình riêng. Python 3.11+ là bắt buộc. Windows/macOS/Linux cài private runtime có thể truyền `--node <node> --openclaw-entry <openclaw.mjs>`; nếu CLI nằm trên PATH có thể dùng `--openclaw-bin <openclaw>`.
3. Helper giữ nguyên model, API key, auth, URL và phần body sẵn có; thêm `agents.defaults.models["provider/model"].params.extra_body.service_tier = "priority"` hoặc cài tương ứng trong agent được chọn. Đây là tham số gửi **thật** trong request của API `openai-completions`, không phải `fastModeDefault` cho custom provider và không đổi file Codex. Setting ở defaults áp dụng cho các agent dùng cùng model; helper cảnh báo agent có override ưu tiên cao hơn. `--agent` không tự sửa `extra_body` cấp toàn agent vì có thể ảnh hưởng model khác. Nếu kế thừa `extra_body` chung, helper sao chép giá trị hiện tại; thay đổi body chung về sau không tự cập nhật bản sao theo model.
4. Helper kiểm tra version, validate bằng CLI OpenClaw trên file tạm, sao lưu config và ghi nguyên tử. Thư mục config và backup phải chỉ cho user phù hợp truy cập; trên Windows kiểm tra ACL, vì chmod không thay thế ACL. Nếu config JSON5 có comment, `$include`, model/provider mơ hồ, runtime khác hoặc API không phải `openai-completions`, dừng và báo; không ghi đè hoặc đoán định. Với provider OpenAI Responses hay loại khác, tìm cơ chế fast được runtime/provider đó hỗ trợ thay vì áp dụng bừa helper.
5. Kiểm tra config/instance thực tế sau thay đổi; Gateway có thể hot reload, nếu chưa nhận thì chỉ reload/restart đúng instance khi an toàn. Phiên/agent có thể dùng model hoặc override khác. `extra_body` là tham số cố định theo model, **không** đảm bảo `/fast off` sẽ bỏ nó; muốn hoàn tác, khôi phục riêng giá trị đã thay đổi từ backup sau khi đối chiếu config hiện tại, không ghi đè thay đổi mới.
6. Chỉ báo đã **yêu cầu priority**, không khẳng định backend xử lý fast nếu chưa có telemetry/phản hồi chứng minh. Gateway/model/tài khoản có thể không hỗ trợ hoặc tính giá khác. Không gửi inference tính phí, tin nhắn thật hoặc đổi key chỉ để kiểm tra nếu chưa được phép.

## Codex CLI/Extension

1. Xác định máy, tài khoản và `CODEX_HOME` (mặc định `~/.codex`); giữ nguyên model trừ khi người dùng chỉ định model khác. Chạy `python <skill-dir>/scripts/switch_fast.py`; thêm `--model GPT-6.1-terra` chỉ khi được yêu cầu. Dùng `--config <đường-dẫn>` nếu cần.
2. Chạy `python <skill-dir>/scripts/ensure_fast_catalog.py` với đúng CLI (`--codex-bin <đường-dẫn>` khi cần). Nếu gateway dùng `GPT-6.1-terra` nhưng catalog chỉ có `gpt-6.1-terra`, helper tạo alias từ model đã quảng bá `priority`. Thiếu hỗ trợ thì báo và dừng; catalog riêng là snapshot cần đồng bộ về sau.
3. Tạo phiên Codex mới hoặc tải lại Extension; kiểm tra profile/đối số có thể ghi đè. Script sao lưu config và giữ provider, URL, profile, MCP, credentials, model không được yêu cầu đổi và `model_reasoning_effort`. Không in token hoặc chép `auth.json`. Codex ánh xạ fast sang `service_tier: priority`; chỉ xác nhận backend thực thi khi có bằng chứng.
