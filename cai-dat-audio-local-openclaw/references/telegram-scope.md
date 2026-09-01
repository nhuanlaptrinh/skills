# Telegram Scope

Use an agent that is bound only to the intended Telegram account. Confirm with `bindings[]` before apply. Keep global `tts.auto=off`; set only `agents.entries.<id>.tts.auto=inbound` on the selected agent. This prevents automatic voice replies on Zalo and unrelated Telegram bots.

Auto-TTS attaches generated audio to the normal final reply. Replies under 10 characters or replies already containing media may skip TTS. Long replies can be summarized or skipped according to effective TTS preferences; text remains the primary response.

For OpenClaw `2026.8.1+`, agent definitions live under `agents.entries`; do not write the retired `agents.list` or `messages.tts` schema. If a genuinely older single-channel runtime has no per-agent TTS support, global auto mode is acceptable only after validating its own schema. With multiple channels or agents, use per-agent overrides and keep global auto off.
