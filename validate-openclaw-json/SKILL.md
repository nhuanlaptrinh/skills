---
name: validate-openclaw-json
description: Kiểm tra, sửa và mở rộng file openclaw.json cho hệ thống OpenClaw (Trợ Lý AI Telegram), gồm thêm bot/account/workspace, cấu hình group không cần mention, và đối chiếu các file mẫu tham khảo đã khử secret.
---

# Skill: Kiểm Tra & Sửa File openclaw.json

## Mục đích
Khi user yêu cầu kiểm tra hoặc sửa file `openclaw.json`, hãy đọc skill này và các file mẫu tham khảo để hiểu cấu trúc đúng, sau đó kiểm tra file của user và sửa theo yêu cầu.

## File mẫu tham khảo (BẮT BUỘC ĐỌC TRƯỚC)

**Bước đầu tiên:** Liệt kê tất cả file trong thư mục `examples/` của skill này, rồi đọc **TỪNG file** để nắm được các mẫu cấu hình khác nhau.

```
/root/.agents/skills/validate-openclaw-json/examples/
```

User có thể bổ sung thêm file mẫu vào thư mục `examples/` bất cứ lúc nào. Không giới hạn số lượng file mẫu. Luôn đọc TẤT CẢ file có trong folder này để có cái nhìn toàn diện nhất về các kiểu cấu hình hợp lệ.

> **Lưu ý:** Các token/key/user ID/group ID riêng tư trong file mẫu phải được thay bằng placeholder như `Nhap_API_Cua_Ban`, `telegram:Nhap_User_ID_Cua_Ban`, `Nhap_Group_ID_Khong_Can_Mention_1`. File thực tế của user có thể có token thật — không báo lỗi nếu token có giá trị thực, nhưng không được copy token thật vào skill hoặc ví dụ.

Mẫu mới nhất nên đọc khi cần cấu hình nhiều bot Telegram và group không cần mention:

```
/root/.agents/skills/validate-openclaw-json/examples/openclaw_current_sanitized_sample.json
```

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
│           ├── accountId        (string, phải khớp account trong channels)
│           └── peer             (object, tùy chọn nhưng nên dùng khi bind group cụ thể)
│               ├── kind         (string: "direct"|"group"|"channel"|"dm"|"acp")
│               └── id           (string, ID group/channel/peer cụ thể)
├── channels
│   └── telegram
│       ├── enabled              (boolean: true)
│       ├── dmPolicy             (string: "pairing"|"open")
│       ├── groupPolicy          (string: "open"|"closed")
│       ├── streaming.mode       (string: "off"|"on")
│       ├── proxy                (string, tùy chọn)
│       ├── groups               (object, tùy chọn)
│       │   ├── "*".requireMention          (boolean: true để mặc định group cần mention)
│       │   └── "<group_id>".requireMention (boolean: false để group cụ thể không cần mention)
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
- `botToken` phải có format: `số:chuỗi` (VD: `Nhap_API_Cua_Ban`)
- Account `default` KHÔNG cần botToken.

#### Quy tắc 5: Không có account mồ côi
- Mỗi account Telegram (trừ `default`) nên có ít nhất 1 binding trỏ đến.
- Nếu account Telegram đặt tên riêng/không phải `default` dùng trong group chat mà không có binding, OpenClaw có thể tự động drop/bỏ qua tin nhắn group để tránh nhận diện sai khi chạy nhiều bot.
- Khi user báo "bot đã vào group/admin nhưng nhắn không phản hồi", phải ưu tiên kiểm tra `bindings[].match.accountId` đã ánh xạ đúng account bot đó tới `agentId` xử lý chưa.

#### Quy tắc 6: Mỗi bot token phải có workspace riêng (BẮT BUỘC)
- Mỗi Telegram bot token (mỗi account có botToken) **PHẢI** ứng với một agent có **workspace riêng biệt**.
- KHÔNG được dùng chung workspace giữa các bot token khác nhau — sẽ gây xung đột dữ liệu.
- Workspace nên đặt theo convention: `workspace_<agent_id>` (VD: `workspace_trolyai`, `workspace_laptrinh121`).
- Nếu phát hiện 2 agent trở lên dùng chung workspace → báo lỗi.

#### Quy tắc 7: Một bot chỉ dùng một agent/workspace cho cả DM và group
- Mỗi Telegram `accountId` phải có đúng một account-level binding không chứa `match.peer`.
- Không tạo peer-specific binding để đưa DM owner sang agent/workspace khác.
- Owner là quyền sender trên canonical agent, khai báo bằng `commands.ownerAllowFrom`; owner không phải một agent riêng.
- Chỉ tạo agent/workspace mới khi thêm một bot/account mới thật sự.
- `channels.telegram.commands` chỉ dùng các field được schema hiện hành chấp nhận; luôn chạy `openclaw config validate` và không tự thêm field không có trong schema.

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
  "botToken": "Nhap_API_Cua_Ban",
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

### Thêm group Telegram không cần mention bot
Khi user muốn bot trả lời trong group mà không cần mention, sửa trong `channels.telegram.groups`:

```json
"groups": {
  "*": {
    "requireMention": true
  },
  "Nhap_Group_ID_Khong_Can_Mention_1": {
    "requireMention": false
  }
}
```

Quy tắc:
- Giữ `"*": { "requireMention": true }` để các group khác vẫn cần mention, tránh bot trả lời tràn lan.
- Thêm từng group ID riêng với `requireMention: false` nếu group đó được phép gọi bot không cần mention.
- Group ID Telegram thường là số âm; supergroup có thể có dạng `-100...`. Nếu bot không phản hồi, phải xác nhận đúng chat ID từ log inbound.
- Sau khi sửa, kiểm tra log OpenClaw có dòng `config hot reload applied` hoặc restart gateway nếu hot reload không chạy.

### Khi group đã cấu hình nhưng bot vẫn không trả lời
Kiểm tra theo thứ tự:

1. Xác nhận `channels.telegram.groups["<group_id>"].requireMention` là `false` trong file active, thường là `/root/.openclaw/openclaw.json` khi service chạy với `HOME=/root`.
2. Xem log gateway có inbound group message không:
   ```bash
   journalctl --user -u openclaw-gateway.service --since '30 minutes ago' --no-pager -o cat | rg -i 'Inbound message|outbound send ok|<group_id>|telegram|group'
   ```
3. Nếu không thấy inbound group message, thường là do Telegram chưa gửi tin nhắn thường về bot: kiểm tra bot đã ở đúng group, bot có quyền đọc message, và BotFather `Group Privacy` đã tắt.
4. Nếu cần tắt privacy: BotFather → chọn bot → `Bot Settings` → `Group Privacy` → `Turn off`, rồi remove/add lại bot hoặc cho bot làm admin.
5. Nhắn thử bằng mention bot một lần để log lộ đúng group ID, sau đó dùng đúng ID đó trong `channels.telegram.groups`.

### Trường hợp bot phụ/đặt tên riêng trong group bị drop do thiếu binding
Triệu chứng:
- Bot đã được thêm vào group và có thể đã được cấp quyền admin.
- `channels.telegram.groups["<group_id>"].requireMention` đã là `false` hoặc đã mention đúng bot.
- Log có thể thấy tin nhắn group đi vào nhưng OpenClaw không chuyển cho agent, hoặc bot không phản hồi dù cấu hình token/account nhìn đúng.

Nguyên nhân thường gặp:
- Bot đang dùng `accountId` đặt tên riêng, không phải `default`.
- OpenClaw chạy nhiều Telegram bot cùng lúc nên cần ánh xạ rõ `accountId` → `agentId` trong `bindings`.
- Nếu thiếu binding cho account đó, hệ thống có thể drop/bỏ qua tin nhắn group theo cơ chế an toàn để tránh định tuyến nhầm bot/agent.

Cách kiểm tra:
1. Xác định đúng `accountId` của bot trong `channels.telegram.accounts`, ví dụ `ten_bot_phu`.
2. Kiểm tra có binding nào trỏ tới account đó chưa:
   ```bash
   jq '.bindings[] | select(.match.channel == "telegram") | {agentId, accountId: .match.accountId}' /root/.openclaw/openclaw.json
   ```
3. Nếu không thấy `accountId` của bot phụ, thêm binding ánh xạ tới agent xử lý phù hợp.

Ví dụ sửa:
```json
{
  "agentId": "main",
  "match": {
    "channel": "telegram",
    "accountId": "ten_bot_phu"
  }
}
```

Nếu binding dành riêng cho group chat, phải khai báo rõ `peer.kind`. OpenClaw validate schema rất chặt; thiếu/sai `kind` có thể làm gateway không khởi động và báo lỗi dạng `Invalid input (allowed: "direct", "group", "channel", "dm", "acp")`.

Ví dụ binding group hợp lệ:
```json
{
  "agentId": "main",
  "match": {
    "channel": "telegram",
    "accountId": "ten_bot_phu",
    "peer": {
      "kind": "group",
      "id": "Nhap_Group_ID_Cua_Ban"
    }
  }
}
```

Nếu bot phụ cần trả lời nhiều group, thêm nhiều binding riêng, mỗi binding có một `peer.kind = "group"` và một `peer.id` tương ứng.

Lưu ý khi sửa:
- Thay `ten_bot_phu` bằng đúng key account trong `channels.telegram.accounts`.
- Thay `main` bằng agent thật cần xử lý tin nhắn, nếu không muốn dùng agent chính.
- Với group chat cụ thể, luôn đặt `match.peer.kind` là `"group"` và `match.peer.id` là đúng group ID dạng string.
- Không đưa token Telegram thật vào ví dụ hoặc tài liệu skill.
- Sau khi sửa, chạy validator/hot reload hoặc restart OpenClaw; nếu lỗi schema, sửa config trước khi khởi động lại tiếp.

## Lưu ý đặc biệt
- **⚠️ 1 Bot Token = 1 Workspace RIÊNG (BẮT BUỘC)**: Mỗi Telegram bot token phải có một workspace riêng biệt. KHÔNG BAO GIỜ dùng chung workspace giữa các bot khác nhau. Convention đặt tên: `workspace_<agent_id>`.
- **⚠️ Owner không tạo workspace**: DM owner và group của cùng bot phải cùng route vào canonical agent/workspace. Bot thứ hai mới tạo workspace thứ hai.
- **Workspace trên Windows**: Dùng `\\` (double backslash), VD: `C:\\Users\\user\\.openclaw\\workspace_agentname`
- **Workspace trên Linux**: Dùng `/`, VD: `/root/.openclaw/workspace_agentname`
- **Account `default`** là cấu hình fallback, luôn giữ và KHÔNG cần botToken
- **`plugins.entries.telegram.enabled`** phải là `true` để Telegram hoạt động
- **Không copy secret vào skill/examples**: token Telegram, API key, owner user ID riêng và group ID riêng trong file mẫu phải dùng placeholder.
- Khi sửa file, luôn đảm bảo JSON hợp lệ (dùng indent 2 spaces)
