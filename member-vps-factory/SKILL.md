---
name: member-vps-factory
description: Tạo và kiểm tra Member VPS OpenClaw từ template sạch bằng một lệnh, gồm host Linux local/remote được điều khiển từ Windows, macOS hoặc Linux qua OpenSSH; dùng khi cần provision member mới, chạy dry-run, kiểm tra host, cấu hình profile openclaw-standard hoặc vận hành pipeline Member VPS Factory.
---

# ALT Member VPS Factory

## Khi dùng

Dùng skill này khi cần tạo member OpenClaw mới theo template chuẩn mà không
clone dữ liệu hoặc credential của member khác. Factory hiện điều phối pipeline
đã kiểm tra:

```text
/root/Automation/openclaw_member_assistant/scripts/create_member_openclaw_assistant.sh
```

CLI điều khiển nằm tại:

```text
/root/Apps/member_vps_factory/bin/member-vps-factory
```

## Mô hình host

- Linux VPS là member host production.
- Windows/macOS/Linux là control machine qua OpenSSH sau khi host đã cài Factory.
- Docker Desktop trên Windows/macOS chỉ nên dùng development/test; không coi
  máy laptop sleep là host production 24/7.
- Target SSH phải được cài pipeline core, Docker image, manager và global
  skills trước khi tạo member.

## Lệnh kiểm tra

```bash
python3 /root/Apps/member_vps_factory/bin/member-vps-factory doctor
python3 /root/Apps/member_vps_factory/bin/member-vps-factory doctor --target root@<HOST>
```

`doctor` chỉ đọc trạng thái; không sửa host và không tạo container.

## Cài host từ Windows/macOS/Linux

Trên control machine có OpenSSH, tar và Docker image local:

```bash
python3 /root/Apps/member_vps_factory/bin/member-vps-factory \
  host-install --target root@<HOST> --include-image --include-skills
```

Lệnh này truyền Factory, pipeline core, manager, entrypoint và tùy chọn image
sang host Linux. Nó không tạo member và không truyền secret. `--include-skills`
lọc `.env`, `.token`, `.key`, credential, log, backup và cache; chỉ dùng khi
host cần nhận global skills từ control machine.

`host-install` hiện cần chạy từ Linux control machine vì nó đóng gói source
chuẩn dưới `/root`; từ Windows/macOS dùng WSL hoặc cài host một lần trên Linux,
sau đó điều khiển remote bằng OpenSSH. Sau đó bắt buộc chạy `doctor --target
root@<HOST>`. Host phải có Docker daemon
đang chạy và outbound network để cài runtime bên trong member.

## Lệnh dry-run

```bash
python3 /root/Apps/member_vps_factory/bin/member-vps-factory create \
  --target local \
  --name <member_name> \
  --profile openclaw-standard \
  --owner-id <verified_owner_id> \
  --dry-run
```

Dry-run không gọi Docker, Telegram/provider hoặc ghi filesystem.

## Lệnh chạy thật

Chuẩn bị trên host đích ba file mode `600`:

- Provider env chứa một assignment `TOKEN_CODEX_API_KEY=...`.
- Telegram token file chứa một token BotFather.
- Member password file chứa một mật khẩu bootstrap.

Không đặt secret trong argv, skill, log hoặc image. Chạy:

```bash
python3 /root/Apps/member_vps_factory/bin/member-vps-factory create \
  --target local \
  --name <member_name> \
  --profile openclaw-standard \
  --provider-env-file /root/private/member-token-codex.env \
  --telegram-token-file /root/private/member-telegram.token \
  --member-password-file /root/private/member-password \
  --owner-id <verified_owner_id> \
  --allow-insecure-dashboard
```

Với target remote, file secret phải tồn tại trên remote host; không dùng path
local và không truyền giá trị secret qua SSH command line.

## Input/output

Input gồm tên member hợp lệ, profile, owner Telegram đã xác minh, tùy chọn
group/chat/display name, public IP và ba secret file root-only.

Output là log không chứa secret, container `user-<name>`, root/home volume
riêng, OpenClaw workspace riêng, Telegram account riêng, Gateway dưới
Supervisor, thông tin SSH/web và các healthcheck của pipeline core. Pipeline
áp dụng `cap-quyen-telegram-admin-openclaw` cho từng owner đã xác minh, sau đó
unify về `main` và bật Full Exec ở bước cuối.

Profile hiện tại:

```text
/root/Apps/member_vps_factory/profiles/openclaw-standard.json
```

Profile giữ CPU `2`, RAM `4g`, swap `6g`, PID `1024`, OpenClaw `2026.9.5` với
Node.js `>=24.16.0 <25` (hoặc `>=26.1.0`),
endpoint mặc định `https://codex.anhlaptrinh.vn/v1`, model `GPT-5.6-sol` và
image hiện hành. Profile được chuẩn hóa từ runtime sạch của
`/root/Apps/member_vps/docker-users/data/minhvuong`; không sao chép volume,
session, workspace cá nhân hoặc credential. Chỉ đổi image sau khi đã
build/kiểm tra image versioned.

Factory CLI hỗ trợ thêm `--provider-base-url` và `--primary-model`; endpoint
chỉ nhận HTTPS, còn API key vẫn phải đi qua file root-only mode `600`.

## Rerun và rollback

- Chạy `doctor` rồi `--dry-run` trước mỗi apply.
- Không reuse root volume của member khác.
- Nếu apply lỗi, đọc log trong
  `/root/Automation/openclaw_member_assistant/logs/` và backup trong
  `/root/_Backups/openclaw-member-assistant/<name>`.
- Không tự xóa container/data; dừng Gateway, sửa nguyên nhân rồi rerun có
  kiểm tra.
- Không clone `/root/Apps/member_vps/docker-users/data/minhcuong` vì có thể
  chứa token, identity, session, memory, media và lịch sử riêng.

## An toàn

- Dashboard token-only chỉ bật với `--allow-insecure-dashboard`; ưu tiên HTTPS.
- Không báo hoàn tất nếu `openclaw config validate`, `openclaw skills check`,
  owner check, Full Exec check, Gateway status hoặc Telegram probe chưa đạt.
- Không gửi Telegram test thật tự động.
- Không sửa production `docker-users` khi chỉ cần dùng Factory.
