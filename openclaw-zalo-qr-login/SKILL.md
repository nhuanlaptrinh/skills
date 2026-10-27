---
name: openclaw-zalo-qr-login
description: Hướng dẫn đăng nhập lại Zalo Personal cho OpenClaw bằng QR trên VPS/headless, gửi QR trực tiếp tới Telegram owner hoặc đồng bộ ra web, và giữ nguyên cấu hình không liên quan. Use when Codex needs to regenerate expired Zalo QR, authorize an owner-triggered Telegram QR workflow, onboard/re-login OpenClaw Zalo Personal, or configure dmPolicy/groupPolicy safely.
---

# OpenClaw Zalo QR Login (Quét Mã Zalo User)

Skill này dùng để đăng nhập hoặc kết nối lại kênh **Zalo Personal** (`zalouser`) của OpenClaw trên VPS không có màn hình (headless) hoặc trong Docker Member VPS, bằng cách tạo mã QR đăng nhập và **gửi ảnh QR trực tiếp vào Telegram của ID được chỉ định** để quét trên điện thoại.

---

## ⚡ CÁCH LÀM NHANH NHẤT (QUICKSTART - 1 LỆNH)

Hệ thống đã có sẵn script tự động kiểm tra, dọn dẹp lock, phân quyền owner (nếu chưa có) và gửi ảnh QR trực tiếp qua Telegram:

### 1. Trên VPS chính (hoặc chạy bên trong container member):
```bash
/root/.agents/skills/openclaw-zalo-qr-login/scripts/quick_send_zalo_qr.sh <TELEGRAM_USER_ID>
```

### 2. Từ Host VPS điều khiển Docker Member VPS:
*(Ví dụ với container `user-anhlaptrinhthu` và Telegram ID `<TELEGRAM_USER_ID>`)*:
```bash
/root/.agents/skills/openclaw-zalo-qr-login/scripts/quick_send_zalo_qr.sh --container user-<member> <TELEGRAM_USER_ID>
```

> **Sau khi chạy lệnh:**
> 1. Bot Telegram sẽ gửi trực tiếp ảnh QR vào tin nhắn riêng (DM) của Telegram ID đó.
> 2. Người dùng mở Zalo trên điện thoại -> Quét mã QR -> Bấm "Xác nhận đăng nhập" trên điện thoại.
> 3. CLI tự động nhận diện `Login successful`, kết nối lại Zalo Personal và gửi thông báo hoàn tất qua Telegram.

---

## 📋 QUY TRÌNH TỪNG BƯỚC CHI TIẾT (MANUAL STEPS)

Khi muốn chạy từng bước hoặc debug chi tiết, thực hiện theo thứ tự sau:

### Bước 1: Chuẩn bị ID Telegram người nhận và phân quyền Owner

ID Telegram nhận QR phải là số nguyên (ví dụ: `6980864856`).
Để gửi được tin nhắn ảnh trực tiếp từ bot qua CLI, ID Telegram cần có đầy đủ quyền Owner trong `openclaw.json`. 

Nếu ID Telegram chưa được cấp quyền, chạy đoạn script Python sau để tự động bổ sung quyền an toàn:
```bash
python3 - <<'PY'
import json, os, sys

target = "<TELEGRAM_USER_ID>"  # Thay bằng ID Telegram cần nhận QR
config_path = os.path.expanduser("~/.openclaw/openclaw.json")

with open(config_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# 1. Telegram allowFrom
tg = data.setdefault("channels", {}).setdefault("telegram", {})
allow_from = tg.setdefault("allowFrom", [])
if target not in [str(x) for x in allow_from]:
    allow_from.append(target)

# 2. commands.ownerAllowFrom
cmd = data.setdefault("commands", {})
owner_allow = cmd.setdefault("ownerAllowFrom", [])
if target not in [str(x) for x in owner_allow] and f"telegram:{target}" not in [str(x) for x in owner_allow]:
    owner_allow.append(f"telegram:{target}")

# 3. tools.elevated.allowFrom.telegram
elevated = data.setdefault("tools", {}).setdefault("elevated", {}).setdefault("allowFrom", {}).setdefault("telegram", [])
if target not in [str(x) for x in elevated]:
    elevated.append(target)

# 4. channels.telegram.execApprovals.approvers
exec_approvers = tg.setdefault("execApprovals", {}).setdefault("approvers", [])
if target not in [str(x) for x in exec_approvers]:
    exec_approvers.append(target)

# 5. approvals.plugin.targets
accounts = tg.get("accounts", {})
default_account = "default" if "default" in accounts else (list(accounts.keys())[0] if accounts else "default")
approvals = data.setdefault("approvals", {}).setdefault("plugin", {})
targets = approvals.setdefault("targets", [])
if not any(isinstance(t, dict) and t.get("channel") == "telegram" and str(t.get("to")) == target for t in targets):
    targets.append({"channel": "telegram", "to": target, "accountId": default_account})

# 6. Đảm bảo cấu hình Multi-agent hợp lệ
agents = data.get("agents", {})
if len(agents.get("entries", {})) > 1:
    agents.setdefault("defaults", {})["systemAgent"] = {"agentId": "main"}
    agents["ownership"] = "explicit"

with open(config_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("Đã xác thực và bổ sung đủ quyền Owner cho Telegram ID:", target)
PY
```

---

### Bước 2: Dọn dẹp lock cũ và kiểm tra điều kiện

Nếu lần chạy trước bị hủy ngang, file lock có thể làm chặn tiến trình mới:
```bash
# Xóa lock trên VPS:
rm -f ~/.openclaw/state/zalo-qr-owner-login.lock

# Hoặc trên Docker container member:
docker exec user-<member> rm -f /root/.openclaw/state/zalo-qr-owner-login.lock
```

---

### Bước 3: Chạy lệnh tạo QR và gửi qua Telegram

Sử dụng helper chính thức `send_zalo_qr_to_telegram_owner.mjs`:

#### A. Trên VPS chính:
```bash
# Chạy thử kiểm tra (Dry-run):
node /root/.agents/skills/openclaw-zalo-qr-login/scripts/send_zalo_qr_to_telegram_owner.mjs \
  --target <TELEGRAM_USER_ID> \
  --dry-run

# Chạy thật gửi QR tới Telegram (Apply):
node /root/.agents/skills/openclaw-zalo-qr-login/scripts/send_zalo_qr_to_telegram_owner.mjs \
  --target <TELEGRAM_USER_ID> \
  --apply
```

#### B. Trên Docker Container Member VPS:
```bash
docker exec -it user-<member> bash -lc "
set -a; [ -f /root/.openclaw/token-codex.env ] && . /root/.openclaw/token-codex.env; set +a
node /root/.agents/skills/openclaw-zalo-qr-login/scripts/send_zalo_qr_to_telegram_owner.mjs \
  --target <TELEGRAM_USER_ID> \
  --apply
"
```

Khi lệnh chạy:
- OpenClaw dừng kênh `zalouser` hiện tại (nếu đang chạy).
- CLI khởi tạo tiến trình đăng nhập chính thức `openclaw channels login --channel zalouser`.
- Khi ảnh QR được sinh ra, script lập tức gửi qua Telegram của `<TELEGRAM_USER_ID>` kèm thông báo.
- Đồng thời sao chép ảnh dự phòng vào `/var/www/html/openclaw-qr.png`.

---

### Bước 4: Người dùng quét mã trên điện thoại

1. Mở ứng dụng Zalo trên điện thoại.
2. Bấm vào biểu tượng quét mã QR ở góc trên bên phải.
3. Quét mã QR nhận được trên Telegram (hoặc từ màn hình web dự phòng).
4. Bấm **"Đăng nhập" / "Xác nhận"** trên điện thoại.

---

### Bước 5: Xác nhận và kiểm tra kết quả

Sau khi xác nhận trên điện thoại:
1. Script trong terminal sẽ hiển thị `Login successful.` và tự động gửi tin nhắn báo thành công tới Telegram:
   *"Đăng nhập Zalo Personal đã thành công. Kênh Zalo của OpenClaw đã được bật lại."*
2. Kiểm tra trạng thái hoạt động:
   ```bash
   openclaw status
   # hoặc trong container:
   docker exec -it user-<member> bash -lc "openclaw status"
   ```
   Kết quả kỳ vọng hiển thị:
   ```text
   Zalo Personal: ON | OK
   ```

---

## 🛠️ XỬ LÝ SỰ CỐ THƯỜNG GẶP (TROUBLESHOOTING)

### 1. Lỗi `A Zalo QR delivery workflow is already running`
- **Nguyên nhân:** File lock còn lưu lại từ lần chạy trước chưa kịp dọn dẹp.
- **Khắc phục:**
  ```bash
  rm -f ~/.openclaw/state/zalo-qr-owner-login.lock
  # hoặc trong Docker:
  docker exec user-<member> rm -f /root/.openclaw/state/zalo-qr-owner-login.lock
  ```

### 2. Lỗi `Multiple agents are configured, but channel plugin discovery has no explicit owner`
- **Nguyên nhân:** Có nhiều hơn 1 agent trong `openclaw.json` (ví dụ `main` và `messenger-anvi`), nhưng chưa chỉ định agent hệ thống chịu trách nhiệm plugin.
- **Khắc phục:** Thêm vào `agents.defaults`:
  ```json
  "agents": {
    "defaults": {
      "systemAgent": {
        "agentId": "main"
      }
    }
  }
  ```

### 3. Lỗi `Telegram target is missing required permissions`
- **Nguyên nhân:** Telegram ID chưa được cấp đủ 5 quyền: `telegramDm`, `commandOwner`, `elevated`, `execApprover`, `approvalTarget`.
- **Khắc phục:** Dùng script `quick_send_zalo_qr.sh` (tự động cấp) hoặc chạy đoạn Python ở Bước 1.

### 4. Link web dự phòng nếu không nhận được ảnh Telegram
Ảnh QR luôn được tự động đồng bộ sang thư mục web:
- Đường dẫn file: `/var/www/html/openclaw-qr.png`
- URL truy cập: `https://<domain>/openclaw-qr.png`
(Sau khi đăng nhập xong, có thể xóa file ảnh này: `rm -f /var/www/html/openclaw-qr.png`).

---

## 🔒 NGUYÊN TẮC AN TOÀN

- Không in mã Token, Cookie Zalo, Bot Token hay số điện thoại khách hàng ra tài liệu hoặc console công khai.
- Giữ nguyên toàn bộ cấu hình model AI, prompt, workspace training, tools và các kênh khác (Telegram, Messenger...).
- Sau khi Zalo Personal kết nối thành công, phiên đăng nhập được lưu an toàn tại `~/.openclaw/credentials/zalouser/`.

## Lỗi đã gặp / Checklist

- Sự cố `/zaloqr` ngày 26/10/2026: `package.json` phải dùng `pluginApi` range, không pin exact `2026.9.9`. Bundle hiện kiểm thử `>=2026.9.9 <=2026.10.6`; kiểm tra core thực tế trước khi nới giới hạn. Giữ plugin ID legacy, không đăng ký trùng tool/command.
- Parser receipt phải lấy từng dòng/khối JSON độc lập bằng `matchAll`, chịu được log thừa trước/sau (kể cả `[state/agent-db] ... clean-close receipt`); vẫn kiểm tra đúng owner/chat, `ok` và message ID. Timeout delivery `60000` ms; không parse toàn bộ phần stdout còn lại bằng `JSON.parse`.
- Khi CLI gửi ảnh đã exit 0 nhưng chỉ đọc receipt lỗi, giữ login sống đến khi hoàn tất/hết hạn (tối đa 180 giây), không để `finally` stop sớm. Báo delivery chưa xác minh (`qrSent: null`), không tự gửi lại hoặc báo giao ảnh/đăng nhập thành công.
- Trước cài: chạy `node --test scripts/test_receipt.mjs` và `python3 -B scripts/test_deploy.py` trong skill `telegram-zalo-owner-login` (offline, không tạo QR/gửi tin). Sau cài: `openclaw plugins list --json` và `openclaw plugins inspect <id> --runtime --json` phải thấy `loaded`, tool `telegram_zalo_login_qr` và command `zaloqr`; có config/doctor sạch không đủ chứng minh plugin load.
- Khi được phép apply runtime, backup từng file `<file>.bak-<timestamp>`, giữ watchdog lock đúng member rồi `openclaw plugins reload <id> --json`; `restartRequired=false` thì KHÔNG restart. Nếu `true` hoặc reload lỗi, dừng và hỏi owner, không tự restart gateway/container/service. Sửa kho skill/template không đồng nghĩa đã reload member; không chạy helper `--apply` có stop/start khi task cấm restart.
- Probe `zalouser` mỗi **30 phút**, lệch phút giữa member; không tự đổi cron production. Không logout, tạo/gửi QR hay gửi tin Telegram/Zalo trong lượt sửa/kiểm thử offline; live test chỉ khi owner yêu cầu riêng.
