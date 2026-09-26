---
name: core-openclaw-runtime
description: Điều phối cấu hình runtime, model, timeout, memory, workspace, session và policy OpenClaw.
---

Đây là skill chính (entry point). Dùng nó để chọn và điều phối các skill chuyên biệt bên dưới; không tạo workflow trùng lặp khi skill phụ đã có hướng dẫn chi tiết.

Skill liên quan: validate-openclaw-json, openclaw-member-model-switch, openclaw-timeout-guard, openclaw-memory-fts-only, openclaw-session-token-rotation, set-openclaw-thinking-levels, unify-openclaw-bot-workspace

Giữ nguyên nguyên tắc an toàn của project và đọc AGENTS.md, Second AI Brain, checklist production trước khi thay đổi hệ thống.
