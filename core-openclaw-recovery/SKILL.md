---
name: core-openclaw-recovery
description: Điều phối chẩn đoán và khôi phục Gateway, overload, compaction, upgrade và lỗi không phản hồi.
---

Đây là skill chính (entry point). Dùng nó để chọn và điều phối các skill chuyên biệt bên dưới; không tạo workflow trùng lặp khi skill phụ đã có hướng dẫn chi tiết.

Skill liên quan: openclaw-compaction-recovery, openclaw-9router-overload-recovery, recover-openclaw-member-gateway, openclaw-member-upgrade-telegram-recovery, openclaw-zalo-no-response, openclaw-telegram-group-recovery

Giữ nguyên nguyên tắc an toàn của project và đọc AGENTS.md, Second AI Brain, checklist production trước khi thay đổi hệ thống.
