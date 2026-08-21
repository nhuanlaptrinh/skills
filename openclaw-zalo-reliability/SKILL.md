---
name: openclaw-zalo-reliability
description: Vận hành và sửa độ ổn định Zalo Personal cho OpenClaw member VPS, gồm watchdog, phản hồi sớm, kiểm tra file, môi trường PDF/Excel, compact session và tách tác vụ nặng sang worker.
---

# OpenClaw Zalo Reliability

## Khi nào dùng

- Zalo lâu lâu không nhận hoặc không trả lời trong khi Telegram vẫn chạy.
- Tác vụ file/ảnh/video làm bot im lâu.
- File gửi qua Zalo lỗi, quá nặng hoặc không mở được trên điện thoại.
- Session Zalo quá dài hoặc worker không bàn giao ổn định.

## Đường dẫn

- Watchdog: `/root/Automation/watchdog/shared_self_healing/scripts/check_member_zalouser.sh`
- Wrapper cron: `/root/Automation/watchdog/shared_self_healing/run_project.sh member_anhlaptrinh_zalouser`
- Cài tool tài liệu: `/root/Automation/openclaw_member_assistant/scripts/setup_member_document_tools.sh`
- Kiểm tra file: `/root/Automation/openclaw_member_assistant/scripts/validate_zalo_file.py`
- Audit/compact session: `/root/Automation/openclaw_member_assistant/scripts/audit_member_sessions.sh`
- Vá retry/delay gửi nhiều đoạn: `/root/Automation/openclaw_member_assistant/scripts/patch_zalouser_send_reliability.sh`
- Vá lưu group im lặng: `/root/Automation/openclaw_member_assistant/scripts/patch_zalouser_silent_archive.py`
- Skill trong workspace: `/home/anhlaptrinh/.openclaw/workspace/skills/zalo-reliable-task-delivery/SKILL.md`
- Skill audio dùng chung: `/root/.agents/skills/cai-dat-audio-local-openclaw/SKILL.md`

## Dry-run

```bash
bash /root/Automation/watchdog/shared_self_healing/scripts/check_member_zalouser.sh --dry-run
bash /root/Automation/openclaw_member_assistant/scripts/audit_member_sessions.sh user-anhlaptrinhthu
MEMBER_DATA_DIR=/root/Apps/member_vps/docker-users/data/anhlaptrinhthu bash /root/Automation/openclaw_member_assistant/scripts/patch_zalouser_send_reliability.sh
CONTAINER=user-nguyendinhtan MEMBER_HOME=/root MEMBER_LABEL=nguyendinhtan PROJECT_KEY=member_nguyendinhtan_zalouser bash /root/Automation/watchdog/shared_self_healing/scripts/check_member_zalouser.sh --dry-run
MEMBER_HOME=/root SESSION_PATTERN='agent:main:zalouser:direct:<zalo-id>' COMPACTION_MODE=summary bash /root/Automation/openclaw_member_assistant/scripts/audit_member_sessions.sh user-nguyendinhtan
MEMBER_DATA_DIR=/root/Apps/member_vps/docker-users/data/nguyendinhtan/root bash /root/Automation/openclaw_member_assistant/scripts/patch_zalouser_send_reliability.sh
python3 /root/Automation/openclaw_member_assistant/scripts/validate_zalo_file.py /path/to/file.xlsx
```

## Chạy thật

```bash
bash /root/Automation/watchdog/shared_self_healing/run_project.sh member_anhlaptrinh_zalouser
/root/Automation/watchdog/shared_self_healing/run_project.sh member_nguyendinhtan_zalouser
/root/Automation/watchdog/shared_self_healing/run_project.sh member_nguyendinhtan_sessions
bash /root/Automation/openclaw_member_assistant/scripts/setup_member_document_tools.sh user-anhlaptrinhthu /home/anhlaptrinh
SESSION_PATTERN='agent:main:zalouser:' TOKEN_THRESHOLD_64K=18000 TOKEN_THRESHOLD_128K=40000 SESSION_IDLE_SECONDS=600 MAX_LINES=300 bash /root/Automation/openclaw_member_assistant/scripts/audit_member_sessions.sh user-anhlaptrinhthu --apply
MEMBER_DATA_DIR=/root/Apps/member_vps/docker-users/data/anhlaptrinhthu bash /root/Automation/openclaw_member_assistant/scripts/patch_zalouser_send_reliability.sh --apply
```

## Input/Output

- Watchdog đọc trạng thái channel và log `/tmp/openclaw/openclaw-*.log`, ghi log tập trung và chỉ gửi Telegram khi có sự cố/phục hồi.
- Validator nhận một đường dẫn file, trả JSON gồm dung lượng, MIME, trạng thái XLSX và mức phù hợp điện thoại.
- Session audit đọc store OpenClaw, liệt kê session vượt ngưỡng; `--apply` compact còn số dòng cấu hình.
- Shared watchdog chạy `member_anhlaptrinh_sessions` mỗi 2 giờ, compact session Zalo đã idle ít nhất 10 phút theo ngưỡng 18.000 token với context 64K và 40.000 token với context 128K.
- Member có HOME khác `/home/anhlaptrinh` phải truyền `MEMBER_HOME`; với transcript ít dòng nhưng tool output lớn, dùng `COMPACTION_MODE=summary` thay vì truncate theo `MAX_LINES`.
- `member_nguyendinhtan_zalouser` kiểm tra mỗi 5 phút và `member_nguyendinhtan_sessions` summary-compact riêng DM owner mỗi 2 giờ sau ít nhất 10 phút idle.
- Phản hồi Zalo thông thường giới hạn 1.800 ký tự; nội dung dài phải tóm tắt trước hoặc chuyển thành file.
- Plugin Zalo chia tin ở 2.000 ký tự, nghỉ 600 ms giữa các đoạn và retry tối đa 3 lần với backoff khi gửi lỗi.
- Với model/provider không tự bật session pruning, cấu hình `agents.defaults.contextPruning.mode=cache-ttl` và `ttl=5m` để soft-trim/hard-clear tool output cũ trong context gửi model; transcript trên đĩa vẫn được giữ nguyên.
- Cấu hình phòng ngừa compaction chuẩn cho member này là `mode=safeguard`, `reserveTokensFloor=40000` và `maxHistoryShare=0.5`.
- Bộ cài tạo venv tại `/home/anhlaptrinh/.openclaw/tools/document-venv`.
- Pipeline tạo member mới gọi bộ cài này mặc định, nên Python và document toolchain có sẵn ngay sau khi tạo VPS.
- Plugin `zalouser` có thể đưa voice Zalo vào session dưới dạng URL `zdn.vn/*.aac` thay vì media attachment, nên `tools.media.audio` không tự kích hoạt.
- Với voice AAC của Zalo, dùng luồng URL trong skill `cai-dat-audio-local-openclaw` để tải tạm AAC và gọi Shared Local STT. Không áp dụng yêu cầu này cho VPS chỉ dùng Telegram.

## Rerun

- Watchdog có cooldown 10 phút để tránh restart lặp; phải nạp `$MEMBER_HOME/.openclaw/gateway.env` nội bộ trước khi probe để không kết luận sai khi gateway auth dùng secret reference.
- Watchdog coi cả listener exit và `Zalouser final reply failed: OutboundDeliveryError` là lỗi cần phục hồi. Container chạy gateway bằng `supervisord`; gửi `SIGTERM` cho `openclaw-gateway` hoặc fallback `openclaw` để supervisor tự khởi động lại, không dùng `tmux` hoặc chạy thêm gateway trùng port.
- Validator có thể chạy lại nhiều lần sau mỗi lần tối ưu file.
- Session audit mặc định chỉ đọc; chỉ dùng `--apply` sau backup.
- Sau khi OpenClaw/plugin Zalo được cập nhật, chạy dry-run script patch; script chọn bundle tương thích mới nhất để không nhầm generation cũ. Đối chiếu target với source từ `openclaw plugins inspect zalouser`; nếu bundle active chưa có marker `ZALO_SEND_MAX_ATTEMPTS` thì chạy lại với `--apply` và restart gateway.
- Với group cần lưu tin nhưng không được phản hồi, dùng skill `zalo-silent-group-archive`; sau mỗi lần cập nhật plugin Zalo phải chạy lại dry-run patch silent archive.
- Nếu compact trả `No compaction needed` nhưng session vẫn gây lỗi, backup session index rồi tạo session mới; không xóa transcript cũ.

## Chẩn đoán listener Zalo dừng đột ngột

- Nếu log `/tmp/openclaw/openclaw-*.log` có `Zalo listener error: ZcaApiError: Invalid data length or missing cipher key` và `channel exited`, kiểm tra phiên bản core bằng `openclaw --version` và plugin bằng `openclaw plugins inspect zalouser`.
- Plugin `@openclaw/zalouser` phải cùng dòng phiên bản với OpenClaw core. Nếu core mới hơn plugin, chạy `openclaw plugins update @openclaw/zalouser@latest`, sau đó restart gateway; không xóa credential Zalo.
- Sau restart, xác minh `openclaw plugins doctor` và `openclaw channels status --probe`; phải thấy Zalo `running ... works` và không có lỗi cipher mới trong log.
- Nếu lỗi vẫn lặp lại sau khi plugin đã cùng phiên bản, mới xem xét phiên đăng nhập/cipher session và yêu cầu QR login lại; không xóa credential trước khi có backup.

## An toàn

- Backup config, skills, session index và cron trước khi sửa production.
- Không ghi token/API key/cookie vào script, skill hoặc log.
- Không xóa transcript; compact bằng CLI OpenClaw.
- Không gửi tin test thật khi chưa được phép; watchdog chỉ gửi cảnh báo khi phát hiện sự cố thật.
- Không tự logout hoặc xóa credential Zalo. Nếu phục hồi thất bại, yêu cầu quét QR lại.
