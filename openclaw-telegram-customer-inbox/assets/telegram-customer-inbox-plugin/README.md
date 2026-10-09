# Telegram Customer Inbox

This local OpenClaw plugin mirrors Telegram customer DMs into a staff group and routes staff replies back to the customer.

- Customer DMs and AI replies are mirrored with clear `🔵`, `🤖`, `🟢`, and `🟡` flow labels.
- Normal staff replies are sent directly to the customer while AI continues answering.
- `🟡 Tiếp quản khách này`, `/takeover`, or `Tiếp quản` pauses AI for only that customer.
- `🟢 Trả lại bot`, `/bot`, or `Trả lại bot` resumes AI.

The plugin uses OpenClaw's existing Telegram polling process and never creates a second polling worker.
