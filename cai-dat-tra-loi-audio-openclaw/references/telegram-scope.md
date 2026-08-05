# Telegram Scope

Use an agent that is bound only to the intended Telegram account. Confirm with `bindings[]` before apply. Keep global `messages.tts.auto=off`; the selected agent deep-merges `tts.auto=inbound`. This prevents automatic voice replies on Zalo and unrelated Telegram bots.

Auto-TTS attaches generated audio to the normal final reply. Replies under 10 characters or replies already containing media may skip TTS. Long replies can be summarized or skipped according to effective TTS preferences; text remains the primary response.

For legacy member containers with no `agents.list` and only one Telegram account, global `messages.tts.auto=always` is acceptable. If the runtime has multiple channels or agents, use per-agent overrides and keep global auto off.
