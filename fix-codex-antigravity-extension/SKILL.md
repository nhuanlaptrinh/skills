---
name: fix-codex-antigravity-extension
description: Khắc phục lỗi "command 'chatgpt.openSidebar' not found" hoặc lỗi SyntaxError 'Unexpected identifier p' khi cài đặt hoặc cập nhật extension OpenAI Codex trong Antigravity IDE. Dùng khi extension Codex không mở được sidebar hoặc fail khi kích hoạt trên Antigravity IDE server.
---

# Hướng Dẫn Sửa Lỗi Extension Codex Trong Antigravity IDE

Skill này hướng dẫn cách chẩn đoán và sửa triệt để lỗi extension Codex (`openai.chatgpt`) không kích hoạt được trên Antigravity IDE, dẫn đến lỗi:
`command 'chatgpt.openSidebar' not found`

## 1. Nguyên nhân kỹ thuật

- Extension OpenAI Codex phiên bản mới (từ `26.901.x` trở đi) biên dịch có sử dụng cú pháp Stage 3 Explicit Resource Management:
  `using p = n(u)`
- Antigravity IDE Server (dựa trên VS Code 1.96 - 1.107) sử dụng embedded Node.js phiên bản `v22.21.1`.
- Ở Node 22, từ khóa `using` chưa được bật mặc định và Node không cho phép bật cờ `--js-explicit-resource-management` thông qua `NODE_OPTIONS`.
- Hậu quả: Khi Extension Host nạp file `out/extension.js`, Node 22 văng lỗi:
  `SyntaxError: Unexpected identifier 'p'` tại dòng `if(i&&l===o){using p=n(u)}}`.
- Lỗi cú pháp này khiến extension fail lúc kích hoạt (`Activating extension openai.chatgpt failed`), do đó toàn bộ command (`chatgpt.openSidebar`, `chatgpt.newCodexPanel`, ...) không được đăng ký vào IDE.

## 2. Cách khắc phục nhanh bằng Script

Chạy script tự động đã được tích hợp sẵn trên VPS:

```bash
/root/_Infra/scripts/patch_codex_antigravity.sh
```

Script sẽ:
1. Tự động tìm thư mục extension `openai.chatgpt*` trong `/root/.antigravity-ide-server/extensions/`.
2. Tạo bản sao lưu dự phòng vào `/root/_Backups/antigravity_openai_chatgpt/extension.js.bak_<timestamp>`.
3. Thay thế cú pháp `using p=n(u)` thành cú pháp tương thích tiêu chuẩn:
   `let p=n(u);p?.[Symbol.dispose]?.()`
4. Kiểm tra lại cú pháp bằng chính Node binary của Antigravity Server.

## 3. Cách sửa thủ công (nếu cần)

File mục tiêu:
`/root/.antigravity-ide-server/extensions/openai.chatgpt-<version>-linux-x64/out/extension.js`

1. Backup file gốc:
   ```bash
   cp /root/.antigravity-ide-server/extensions/openai.chatgpt-*/out/extension.js /root/_Backups/extension.js.bak
   ```
2. Thay thế:
   - Tìm chuỗi: `if(i&&l===o){using p=n(u)}}`
   - Đổi thành: `if(i&&l===o){let p=n(u);p?.[Symbol.dispose]?.()}}`
3. Kiểm tra cú pháp bằng Node của Antigravity:
   ```bash
   /root/.antigravity-ide-server/bin/*/node --check /root/.antigravity-ide-server/extensions/openai.chatgpt-*/out/extension.js
   ```

## 4. Áp dụng thay đổi vào Antigravity IDE

Sau khi file đã được patch:
1. Trong cửa sổ Antigravity IDE, nhấn `Ctrl + Shift + P` (hoặc `F1`).
2. Gõ và chọn: **Developer: Reload Window** (hoặc **Developer: Restart Extension Host**).
3. Sau khi reload, click vào icon Codex ở sidebar hoặc bấm vào lệnh của Codex, sidebar sẽ mở bình thường.
