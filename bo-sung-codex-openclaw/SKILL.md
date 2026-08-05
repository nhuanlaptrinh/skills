---
name: bo-sung-codex-openclaw
description: Configure OpenClaw on a VPS so 9router stays the primary model provider and Codex/OpenAI OAuth is added as fallback, including remote OAuth redirect paste steps, config patching, auth verification, and test commands. Use when the user asks to bổ sung Codex, thêm Codex fallback, đăng nhập Codex cho OpenClaw, test OpenAI fallback, or repair OpenClaw 9router/Codex auth.
---

# Bổ sung Codex/OpenAI fallback cho OpenClaw

## Mục tiêu

Dùng skill này khi cần giữ `9router` làm model chính trong OpenClaw và thêm `Codex/OpenAI` làm phương án dự phòng. Quy trình phù hợp VPS/headless: mở OAuth URL trên trình duyệt local, paste full redirect URL về terminal VPS, rồi test bằng `openclaw infer`.

## Nguyên tắc an toàn

- Không ghi token, OAuth code, redirect URL thật, email thật vào skill, log công khai, commit hoặc tài liệu chia sẻ.
- Khi cần minh họa, dùng placeholder: `email_cua_ban@example.com`, `Nhap_API_Cua_Ban`, `http://localhost:1455/auth/callback?code=...&state=...`.
- Trước khi sửa `~/.openclaw/openclaw.json`, luôn backup hoặc xác nhận OpenClaw đã tạo backup.
- Không đổi model chính sang OpenAI nếu người dùng muốn `9router` là primary; chỉ thêm OpenAI vào `fallbacks`.

## Quy trình nhanh

### 1. Kiểm tra trạng thái hiện tại

```bash
openclaw models status
openclaw models auth list
openclaw config validate
```

Xác định:
- Default/primary hiện đang là model 9router, thường như `9r/codex` hoặc `9router/ModeFree`.
- Fallback đã có `openai/gpt-5.5` chưa.
- Auth store của agent hiện tại có profile OpenAI OAuth chưa.

### 2. Cập nhật cấu hình fallback

Sửa `~/.openclaw/openclaw.json` để phần mặc định có cấu trúc tương tự:

```json
{
  "auth": {
    "profiles": {
      "openai:personal": {
        "provider": "openai",
        "mode": "oauth"
      }
    },
    "order": {
      "openai": ["openai:personal"]
    }
  },
  "agents": {
    "defaults": {
      "model": {
        "primary": "9r/codex",
        "fallbacks": ["openai/gpt-5.5"]
      },
      "models": {
        "9r/codex": {},
        "9r/*": {},
        "openai/*": {},
        "openai/gpt-5.5": {}
      }
    }
  }
}
```

Điều chỉnh `primary` theo provider 9router đang có thật trên VPS, ví dụ `9r/codex`. Giữ nguyên các provider/key hiện có trong `models.providers`.

### 3. Đăng nhập Codex/OpenAI OAuth trên VPS

Chạy một trong các lệnh sau, ưu tiên OpenClaw auth flow vì nó lưu vào agent auth store:

```bash
openclaw models auth login --provider openai 
```

Với OAuth URL trên VPS/headless:
1. Mở URL `https://auth.openai.com/oauth/authorize?...` trên trình duyệt máy local.
2. Đăng nhập ChatGPT/OpenAI.
3. Browser sẽ chuyển về URL dạng `http://localhost:1455/auth/callback?code=...&scope=...&state=...`.
4. Copy toàn bộ URL trên thanh địa chỉ, không copy dấu nhắc terminal.
5. Paste vào dòng `Paste the authorization code (or full redirect URL):` rồi nhấn Enter.

Nếu thấy thông báo kiểu `Updated config`, `Auth profile: openai:<email> (openai/oauth)`, nghĩa là OAuth đã lưu.

### 4. Test sau đăng nhập

Chạy:

```bash
openclaw models auth list
openclaw config validate
openclaw models status
openclaw infer model run --local --model openai/gpt-5.5 --prompt 'Reply exactly: OpenAI fallback OK'
```

Kết luận OK khi có đủ các dấu hiệu:
- `openclaw config validate` trả về `Config valid`.
- `openclaw models status` hiển thị `Default : 9r/codex` hoặc model 9router đang dùng.
- `Fallbacks` có `openai/gpt-5.5`.
- `Runtime auth` cho OpenAI/Codex có `status=usable`.
- Lệnh `infer model run` trả về đúng nội dung test, ví dụ `OpenAI fallback OK`.

## Script hỗ trợ

Có thể chạy script kiểm tra nhanh đi kèm skill:

```bash
bash /root/.agents/skills/bo-sung-codex-openclaw/scripts/test_openclaw_codex_fallback.sh
```

Script này chỉ đọc trạng thái và gọi prompt test ngắn với `openai/gpt-5.5`; không in token đầy đủ.

## Xử lý lỗi thường gặp

- `Profiles: (none)`: OAuth chưa lưu vào agent auth store; chạy lại `openclaw models auth login --provider openai --profile-id openai:personal`.
- `status` không phải `usable`: kiểm tra lại OAuth profile, hạn token, và agent đang dùng đúng auth store.
- `Default model available ... use --set-default`: không cần dùng `--set-default` nếu mục tiêu là giữ 9router làm primary; chỉ dùng OpenAI làm fallback.
- OAuth URL bị xuống dòng trong terminal: copy nguyên URL từ thanh địa chỉ trình duyệt, không copy đoạn bị wrap từ terminal.
