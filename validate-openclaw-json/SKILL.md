---
name: validate-openclaw-json
description: Kiểm tra cú pháp, cấu trúc và tính hợp lệ của file openclaw.json cho hệ thống OpenClaw (Trợ Lý AI Telegram). Dựa trên 2 file mẫu tham khảo để phát hiện lỗi và sửa file theo yêu cầu.
---

# Skill: Kiểm Tra & Sửa File openclaw.json

## Mục đích
Khi user yêu cầu kiểm tra hoặc sửa file `openclaw.json`, hãy đọc skill này và các file mẫu tham khảo để hiểu cấu trúc đúng, sau đó kiểm tra file của user và sửa theo yêu cầu.

## File mẫu tham khảo (BẮT BUỘC ĐỌC TRƯỚC)

**Bước đầu tiên:** Liệt kê tất cả file trong thư mục `examples/` của skill này, rồi đọc **TỪNG file** để nắm được các mẫu cấu hình khác nhau.

```
d:\10.Da_Tro_Ly_Openclaw\validate-openclaw-json\examples\
```

User có thể bổ sung thêm file mẫu vào thư mục `examples/` bất cứ lúc nào. Không giới hạn số lượng file mẫu. Luôn đọc TẤT CẢ file có trong folder này để có cái nhìn toàn diện nhất về các kiểu cấu hình hợp lệ.

> **Lưu ý:** Các token/key trong file mẫu đã được thay bằng placeholder (`YOUR_BOT_TOKEN_HERE`, `YOUR_API_KEY_HERE`, `YOUR_AUTH_TOKEN_HERE`). File thực tế của user sẽ có token thật — không báo lỗi nếu token có giá trị thực.

## Quy trình kiểm tra

### Bước 1: Đọc file cần kiểm tra
Đọc file `openclaw.json` mà user cung cấp (hoặc file ở đường dẫn user chỉ định).

### Bước 2: Kiểm tra JSON Syntax
- File phải parse được thành JSON hợp lệ
- Không có dấu phẩy thừa (trailing comma)
- Không thiếu dấu ngoặc `{}` hoặc `[]`
- Không có comment (JSON không hỗ trợ comment)
- String phải dùng dấu ngoặc kép `""`, không dùng ngoặc đơn

### Bước 3: Kiểm tra cấu trúc bắt buộc
File **BẮT BUỘC** phải có các section sau:

```
openclaw.json
├── agents
│   ├── defaults
│   │   ├── model
│   │   │   ├── primary          (string, bắt buộc)
│   │   │   └── fallbacks        (array of string, tùy chọn)
│   │   ├── models               (object, tùy chọn - alias cho models)
│   │   ├── workspace            (string, bắt buộc - đường dẫn mặc định)
│   │   ├── compaction.mode      (string: "default"|"safeguard")
│   │   ├── maxConcurrent        (integer, mặc định 4)
│   │   └── subagents.maxConcurrent (integer, mặc định 8)
│   └── list                     (array, bắt buộc - danh sách agents)
│       └── [mỗi agent]
│           ├── id               (string, bắt buộc, unique)
│           ├── workspace        (string, bắt buộc)
│           └── identity.name    (string, bắt buộc)
├── bindings                     (array, bắt buộc)
│   └── [mỗi binding]
│       ├── agentId              (string, phải khớp agent id)
│       └── match
│           ├── channel          (string: "telegram")
│           └── accountId        (string, phải khớp account trong channels)
├── channels
│   └── telegram
│       ├── enabled              (boolean: true)
│       ├── dmPolicy             (string: "pairing"|"open")
│       ├── groupPolicy          (string: "open"|"closed")
│       ├── streaming.mode       (string: "off"|"on")
│       └── accounts             (object, bắt buộc)
│           ├── [account_name]   (phải khớp binding accountId)
│           │   ├── dmPolicy     (string)
│           │   ├── botToken     (string, format: "số:chuỗi", VD: "123456:ABCdef...")
│           │   ├── groupPolicy  (string)
│           │   └── streaming.mode (string)
│           └── default          (account mặc định, KHÔNG cần botToken)
├── gateway
│   ├── port                     (integer: 1-65535, thường 18789)
│   ├── mode                     (string: "local"|"cloud")
│   ├── bind                     (string: "lan"|"localhost")
│   ├── trustedProxies           (array of string)
│   ├── controlUi.allowedOrigins (array of string)
│   ├── auth
│   │   ├── mode                 (string: "token")
│   │   └── token                (string, bắt buộc)
│   ├── tailscale                (object, tùy chọn)
│   ├── http.endpoints           (object, tùy chọn)
│   └── nodes.denyCommands       (array of string, tùy chọn)
├── plugins
│   └── entries
│       ├── telegram.enabled     (boolean: true, bắt buộc)
│       └── google.enabled       (boolean, tùy chọn)
├── messages                     (object, nên có)
│   └── ackReactionScope         (string: "group-mentions")
├── commands                     (object, nên có)
│   ├── native                   (string: "auto")
│   ├── nativeSkills             (string: "auto")
│   ├── restart                  (boolean: true)
│   └── ownerDisplay             (string: "raw")
├── session                      (object, nên có)
│   └── dmScope                  (string: "per-channel-peer")
├── meta                         (object, tự động tạo)
├── wizard                       (object, tự động tạo)
├── auth                         (object, tùy chọn)
├── tools                        (object, tùy chọn)
│   └── profile                  (string: "coding"|"default")
└── models                       (object, tùy chọn - custom model providers)
    ├── mode                     (string: "merge")
    └── providers                (object - danh sách providers)
```

### Bước 4: Kiểm tra tính nhất quán (QUAN TRỌNG)
Đây là bước quan trọng nhất. Kiểm tra 3 phần phải **khớp nhau**:

#### Quy tắc 1: Mỗi agent phải có binding
- Với mỗi agent trong `agents.list` (theo `id`), phải tồn tại 1 binding trong `bindings` có `agentId` khớp.

#### Quy tắc 2: Mỗi binding phải trỏ đến agent hợp lệ
- Với mỗi binding, `agentId` phải tồn tại trong `agents.list`.

#### Quy tắc 3: Mỗi binding accountId phải có account Telegram
- Với mỗi binding, `match.accountId` phải tồn tại trong `channels.telegram.accounts`.

#### Quy tắc 4: Mỗi account Telegram (trừ "default") phải có botToken
- `botToken` phải có format: `số:chuỗi` (VD: `8757290804:AAEkdsw3bwQJT-A_o6Uwsj8HXUVaX2phkm4`)
- Account `default` KHÔNG cần botToken.

#### Quy tắc 5: Không có account mồ côi
- Mỗi account Telegram (trừ `default`) nên có ít nhất 1 binding trỏ đến.

#### Quy tắc 6: Mỗi bot token phải có workspace riêng (BẮT BUỘC)
- Mỗi Telegram bot token (mỗi account có botToken) **PHẢI** ứng với một agent có **workspace riêng biệt**.
- KHÔNG được dùng chung workspace giữa các bot token khác nhau — sẽ gây xung đột dữ liệu.
- Workspace nên đặt theo convention: `workspace_<agent_id>` (VD: `workspace_trolyai`, `workspace_laptrinh121`).
- Nếu phát hiện 2 agent trở lên dùng chung workspace → báo lỗi.

### Bước 5: Báo cáo kết quả
Báo cáo cho user theo format:

```
✅ FILE HỢP LỆ / ❌ FILE CÓ LỖI

📊 Tóm tắt:
- Số agents: X
- Số bindings: X
- Số accounts Telegram: X
- Model chính: xxx
- Gateway port: xxx

❌ Lỗi (cần sửa):
1. ...
2. ...

⚠️ Cảnh báo (nên sửa):
1. ...
2. ...
```

## Cách sửa file

### Thêm agent mới
Khi user muốn thêm agent mới, cần sửa **3 chỗ đồng thời**:

1. Thêm vào `agents.list`:
```json
{
  "id": "agent_id_moi",
  "workspace": "/root/.openclaw/workspace_agent_id_moi",
  "identity": {
    "name": "Tên hiển thị Agent"
  }
}
```

2. Thêm vào `bindings`:
```json
{
  "agentId": "agent_id_moi",
  "match": {
    "channel": "telegram",
    "accountId": "agent_id_moi"
  }
}
```

3. Thêm vào `channels.telegram.accounts`:
```json
"agent_id_moi": {
  "dmPolicy": "pairing",
  "botToken": "BOT_TOKEN_TỪ_BOTFATHER",
  "groupPolicy": "open",
  "streaming": {
    "mode": "off"
  }
}
```

### Xóa agent
Xóa khỏi cả 3 chỗ: `agents.list`, `bindings`, `channels.telegram.accounts`.

### Đổi model
Sửa `agents.defaults.model.primary` và có thể cập nhật `fallbacks`.

### Đổi port gateway
Sửa `gateway.port` (phải 1-65535).

## Lưu ý đặc biệt
- **⚠️ 1 Bot Token = 1 Workspace RIÊNG (BẮT BUỘC)**: Mỗi Telegram bot token phải có một workspace riêng biệt. KHÔNG BAO GIỜ dùng chung workspace giữa các bot khác nhau. Convention đặt tên: `workspace_<agent_id>`.
- **Workspace trên Windows**: Dùng `\\` (double backslash), VD: `C:\\Users\\user\\.openclaw\\workspace_agentname`
- **Workspace trên Linux**: Dùng `/`, VD: `/root/.openclaw/workspace_agentname`
- **Account `default`** là cấu hình fallback, luôn giữ và KHÔNG cần botToken
- **`plugins.entries.telegram.enabled`** phải là `true` để Telegram hoạt động
- Khi sửa file, luôn đảm bảo JSON hợp lệ (dùng indent 2 spaces)
