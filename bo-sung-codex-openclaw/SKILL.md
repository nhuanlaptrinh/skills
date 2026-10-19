---
name: bo-sung-codex-openclaw
description: Cấu hình primary/fallback Codex cho OpenClaw chỉ với GPT-6.1-sol, GPT-6-terra, GPT-6-luna, GPT-6-astra; giữ provider hiện có. Chỉ bổ sung OpenAI OAuth làm fallback khi provider đó thực sự công bố model được phép, không tự dùng model ngoài danh sách.
---

# Bổ sung Codex/OpenAI fallback cho OpenClaw

## Chính sách model — 2026-10-19

- Chỉ dùng đúng bốn model hội thoại/suy luận: `GPT-6.1-sol`, `GPT-6-terra`, `GPT-6-luna`, `GPT-6-astra`. Mặc định khi cài mới hoặc không chỉ định model là `GPT-6.1-sol`.
- Primary, fallback và lựa chọn trong wizard chỉ lấy từ danh sách này; không tự dùng alias/model cũ hoặc bật DeepSeek dù môi trường có key. Giữ provider hiện có và ghép `<provider>/<model-id>` đúng case.
- Trước khi apply, xác minh model đích trong `/v1/models` của provider thực tế; nếu không có thì dừng, không tự đổi tên hay chọn model ngoài danh sách. Chỉ cấu hình hiểu ảnh khi đã kiểm tra backend hỗ trợ.
- Đây là chính sách chọn model, không phải quyền tự đổi runtime đang chạy. Không đổi model STT/TTS/tạo ảnh thành model chat; các tính năng media chuyên dụng giữ workflow và kiểm tra riêng.

## Mục tiêu

Giữ provider chính đang dùng và chọn primary/fallback từ đúng bốn model được phép. Mặc định cho cấu hình mới là `GPT-6.1-sol`. OAuth đăng nhập thành công không đồng nghĩa provider OpenAI có các model alias của gateway; nếu catalog không công bố đúng ID được phép thì không thêm OpenAI fallback.

## An toàn và input/output

- Input: config active, provider đã xác minh, model đích trong danh sách và credential hiện có. Không đổi `.env`, workspace, session hoặc provider key khi không được yêu cầu.
- Trước khi ghi, backup config active dưới `/root/_Backups/openclaw-model-fallback/<UTC timestamp>/` với quyền riêng tư. Không ghi token, OAuth code, redirect URL thật, cookie hoặc toàn bộ config vào log/skill.
- Output: phần primary/fallback và model allowlist trong config active; không ghi Sheet/API nghiệp vụ hoặc gửi tin Telegram/Zalo.
- Rerun: kiểm tra trạng thái và catalog trước, chỉ đổi phần model cần thiết. Rollback: khôi phục đúng config đã backup, validate rồi reload đúng Gateway khi được phép.

## 1. Kiểm tra trước khi thay đổi

```bash
openclaw models status
openclaw models auth list
openclaw config validate
```

Xác định config active từ `OPENCLAW_CONFIG_PATH` hoặc `${HOME}/.openclaw/openclaw.json`, provider chính và agent đích. Dùng credential trong bộ nhớ để kiểm tra `/v1/models` của đúng provider; chỉ báo HTTP status và model có/không, không in key hoặc toàn bộ phản hồi.

Dry-run là đối chiếu config/catalog và báo các đường dẫn model dự kiến thay đổi, chưa ghi file hoặc reload. Script test ở bước 4 gọi inference thật, không phải dry-run.

## 2. Cấu hình primary/fallback đã được xác minh

Ví dụ dưới đây chỉ dùng khi provider thực tế là `9r` và đã công bố đủ model tương ứng. Nếu provider có ID khác, giữ nguyên ID đó trong mọi tham chiếu:

```json
{
  "agents": {
    "defaults": {
      "model": {
        "primary": "9r/GPT-6.1-sol",
        "fallbacks": ["9r/GPT-6-terra", "9r/GPT-6-luna", "9r/GPT-6-astra"]
      },
      "models": {
        "9r/GPT-6.1-sol": {},
        "9r/GPT-6-terra": {},
        "9r/GPT-6-luna": {},
        "9r/GPT-6-astra": {}
      }
    }
  }
}
```

Không thêm wildcard model để lách danh sách, không đổi endpoint/key hiện có. Nếu được yêu cầu bổ sung provider OpenAI thì phải xác minh đúng model được phép ở provider đó trước khi thêm vào `fallbacks`; không suy ra model OAuth từ tên model gateway.

## 3. OAuth chỉ khi thật sự cần provider OpenAI

Chỉ chạy khi người dùng yêu cầu bổ sung OAuth và bước catalog/provider đã đáp ứng chính sách:

```bash
openclaw models auth login --provider openai
```

Trên VPS/headless, mở URL OAuth bằng trình duyệt local rồi paste redirect URL trực tiếp vào phiên terminal đang chờ. Không lưu URL/code/token vào tài liệu hoặc log. Không thay primary chỉ vì vừa đăng nhập OAuth.

## 4. Kiểm tra sau khi thay đổi

```bash
openclaw config validate
openclaw models status
bash /root/.agents/skills/bo-sung-codex-openclaw/scripts/test_openclaw_codex_fallback.sh 9r/GPT-6-terra
```

Thay `9r/GPT-6-terra` bằng tham chiếu provider/model đã xác minh. Script bắt buộc nhận tham chiếu rõ ràng, từ chối ID ngoài danh sách và không tự chọn model OpenAI cũ. Test inference có thể tiêu tốn quota nhưng không gửi tin nhắn qua channel.

Chỉ báo hoàn tất khi config hợp lệ, primary/fallback đúng model được phép, auth usable cho route cần dùng và inference trả `OpenAI fallback OK`. Nếu provider không có model phù hợp hoặc auth không usable thì dừng và báo đúng nguyên nhân, không tự đổi sang model khác.
