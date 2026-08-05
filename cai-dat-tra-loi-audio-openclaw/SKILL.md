---
name: cai-dat-tra-loi-audio-openclaw
description: "Bật, kiểm tra, sửa hoặc rollback phản hồi đồng thời bằng text và voice cho một Telegram bot OpenClaw. Use khi cần Microsoft Edge TTS miễn phí, chế độ inbound hoặc always, giới hạn agent/account cụ thể để không ảnh hưởng Zalo hoặc bot khác, cùng backup, dry-run và validation."
---

# Cài Trả Lời Audio OpenClaw

## Hai Trường Hợp Cài Đặt

1. **VPS riêng hoặc config nằm trên host:** dùng `enable_edge_tts_agent.sh` với đường dẫn `openclaw.json` trực tiếp. Dùng agent override để chỉ bật đúng Telegram bot cần thiết.
2. **VPS thành viên legacy, config nằm trong container:** dùng `enable_edge_tts_container.sh`. Script `docker cp` config ra host, backup trước/sau, bật Microsoft plugin, copy lại và respawn riêng tmux gateway nếu có.

## Mục Tiêu

- Người dùng gửi chữ: bot trả chữ.
- Người dùng gửi mic Telegram: bot trả text đầy đủ và đính kèm voice đọc câu trả lời.
- Chỉ agent Telegram được chọn có `tts.auto=inbound`; global TTS giữ `auto=off` để Zalo và bot khác không bị ảnh hưởng.
- Provider mặc định: Microsoft Edge TTS, không cần API key; cần Internet và không có SLA.

## Dry-run

```bash
bash /root/.agents/skills/cai-dat-tra-loi-audio-openclaw/scripts/enable_edge_tts_agent.sh \
  --config /root/.openclaw/openclaw.json \
  --agent main \
  --voice vi-VN-NamMinhNeural \
  --auto-mode inbound \
  --dry-run
```

Member container legacy:

```bash
bash /root/.agents/skills/cai-dat-tra-loi-audio-openclaw/scripts/enable_edge_tts_container.sh \
  --container user-member \
  --auto-mode always \
  --dry-run
```

## Apply

Đổi `--dry-run` thành `--apply`. Script backup config vào `/root/_Backups`, cấu hình provider global ở trạng thái off và chỉ bật `inbound` cho agent đã chọn. Restart gateway bằng service method hiện có sau khi apply.

Với container không có `agents.list`, installer container bật `messages.tts.auto` toàn runtime. Chỉ làm vậy khi runtime đó chỉ có Telegram cần trả audio. Nếu có agent cụ thể trong `agents.list`, truyền `--agent ID` để global giữ `off` và chỉ agent đó được bật.

## Cấu Hình Chuẩn

- `messages.tts.auto=off`
- `messages.tts.mode=final`
- `messages.tts.provider=microsoft`
- `messages.tts.maxTextLength=800`
- `plugins.entries.microsoft.enabled=true`
- `agents.list[id=<agent>].tts.auto=inbound`
- Dùng `auto=always` nếu cả tin nhắn chữ và mic đều phải trả text + voice.
- Giọng nam: `vi-VN-NamMinhNeural`
- Giọng nữ: `vi-VN-HoaiMyNeural`

## Kiểm Tra

```bash
/usr/lib/node_modules/openclaw/node_modules/.bin/node-edge-tts \
  -t 'Đây là bài kiểm tra giọng đọc tiếng Việt.' \
  -v vi-VN-NamMinhNeural \
  -f /tmp/openclaw-edge-tts-test.mp3
```

Sau restart, gửi mic thật vào đúng Telegram account của agent. Xác nhận bot gửi text và voice; kiểm tra các bot khác và Zalo không tự tạo voice.

## Rollback Và An Toàn

- Phục hồi `openclaw.json` từ backup rồi restart gateway.
- Không bật `messages.tts.auto=always` toàn cục khi chỉ thử Telegram.
- Không gửi tin test thật nếu chưa được phép.
- Không ghi token/API key vào skill; Microsoft provider không cần key.
- Nếu TTS lỗi, text reply vẫn phải là đường fallback chính.
- Sau restart, kiểm tra dòng `http server listening` phải có plugin `microsoft`; CLI `plugins list` thấy plugin stock chưa đủ để chứng minh gateway đã load provider.

## Member Legacy Có Config Trong Container

Một số member cũ mount dữ liệu vào `/home/<member>` nhưng gateway lại chạy với `HOME=/root`, nên config thật là `/root/.openclaw/openclaw.json` bên trong container. Với trường hợp này:

1. Ưu tiên dùng `scripts/enable_edge_tts_container.sh` thay vì patch thủ công.
2. Dùng `docker cp` đưa config ra `/root/_Backups` và một file tạm trên host.
3. Patch/validate file tạm, rồi `docker cp` trở lại container.
4. Explicit bật `plugins.entries.microsoft.enabled=true`; sau respawn, dòng `http server listening` phải chứa `microsoft`.
5. Không restart Docker nếu gateway chạy thủ công bằng tmux; respawn riêng session `openclaw`.
6. Lưu cả bản config trước và sau sửa trong backup vì config có thể mất khi container bị recreate.
7. Không in nội dung config vì có thể chứa token hoặc credential.
