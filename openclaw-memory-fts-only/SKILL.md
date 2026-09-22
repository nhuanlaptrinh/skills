---
name: openclaw-memory-fts-only
description: Chẩn đoán và chuyển Memory Search của một member/agent OpenClaw sang FTS-only khi embedding provider thiếu credential hoặc không cần tìm kiếm ngữ nghĩa, kèm backup, reindex, kiểm tra và rollback. Không dùng để bật embedding/vector hoặc đổi cả fleet.
---

# OpenClaw Memory FTS-only

## Khi dùng

Dùng skill này cho một container/member và một agent cụ thể khi `openclaw memory status --deep` báo embedding provider không khả dụng (thường là thiếu credential OpenAI) nhưng tìm kiếm theo từ khóa vẫn là đủ. FTS-only giữ tìm kiếm văn bản bằng SQLite FTS và ngừng mọi lời gọi embedding.

Không dùng skill này để sửa lỗi chat/9Router, để cấp API key, để xóa memory, hoặc để áp dụng hàng loạt cho mọi VPS. Mỗi member là một lần thay đổi độc lập; fleet chỉ được làm tuần tự sau khi có yêu cầu rõ ràng.

## Kết quả và giới hạn

- Cấu hình của agent có `memory.search.provider: "none"` và `memory.search.fallback: "none"`.
- Chỉ mục FTS vẫn hoạt động; vector store/semantic search được tắt.
- `embeddingProbe.ok: false` với lý do `No embedding provider available (FTS-only mode)` trong status là trạng thái dự kiến, không phải lỗi mới.
- Tìm kiếm theo từ khóa/chính tả gần đúng có thể kém hơn tìm kiếm ngữ nghĩa. Không đổi model chat, provider chat, transcript, workspace memory hoặc credential.

## Mẫu lỗi đã xác nhận: fallback “previous reply” trên Zalo

Nếu log của member có nhiều dòng `memory embeddings retryable error` trong cùng
lượt Zalo mà model vẫn trả HTTP 200, model có thể tự sinh câu “I couldn't
confirm whether my previous reply reached this chat...” dù transport không hề
báo gửi thất bại. Đây là lỗi nhiễu ngữ cảnh do embedding retry, không phải bằng
chứng Zalo mất liên kết. Với incident này:

1. Ghi lại mốc inbound/outbound và kiểm tra `OutboundDeliveryError` trước khi
   kết luận delivery hỏng.
2. Nếu embedding probe treo hoặc retry liên tục, ưu tiên FTS-only cho đúng
   agent đang nhận Zalo; không đổi model chat hay QR login.
3. Sau apply, `memory status --deep` phải trả nhanh, `provider=none`,
   `fts.available=true`, `vector.enabled=false`, và không còn vòng lặp retry
   trong log mới.
4. Chỉ cho phép runtime sinh thông báo “previous reply” khi delivery state thực
   sự là `unknown`/`send_attempt_started`; không dùng câu đó để suy đoán khi
   chỉ Memory Search bị lỗi.

## Chuẩn bị bắt buộc

Trước khi sửa production, đọc:

1. `/root/_Second_AI_Brain/START_HERE.md`
2. `/root/_Second_AI_Brain/01_Ban_Do_VPS.md`
3. `/root/_Second_AI_Brain/02_Danh_Sach_Project.md`
4. `AGENTS.md` và project note gần member (nếu có)
5. `/root/_Second_AI_Brain/checklists/truoc_khi_sua_production.md`

Chỉ apply khi chủ hệ thống đã yêu cầu/cho phép. Không in toàn bộ `openclaw.json`, token Telegram, API key, cookie, prompt hay nội dung chat vào terminal, log hoặc skill.

## Xác định đúng member và agent

Không đoán host path. Xác định container và agent trước:

```bash
container='user-member-name'
agent='main'
docker inspect "$container" --format '{{.Name}}'
docker exec "$container" openclaw config file
docker exec "$container" openclaw config validate
docker exec "$container" openclaw config get memory.search --json
docker exec "$container" openclaw config get "agents.entries.$agent.memory.search" --json || true
docker exec "$container" openclaw memory status --deep --agent "$agent" --json
```

OpenClaw kế thừa `memory.search` ở root; `agents.entries.<agent>.memory.search` có thể ghi đè riêng cho agent. Nếu có override, phải patch đúng override đó. Nếu container có nhiều agent mà không có override, không đổi root cho tất cả nếu chưa được chấp thuận; tạo override cho agent đích. Không đặt `memory.search.enabled` thành `false` vì sẽ tắt cả indexing/retrieval.

Ghi lại `dbPath` từ status JSON. Với các member hiện tại, config thường ở `/root/.openclaw/openclaw.json` trong container và database ở `/root/.openclaw/agents/<agent>/agent/openclaw-agent.sqlite`, nhưng phải dùng đường dẫn thực tế mà lệnh trả về. Kiểm tra mount bằng `docker inspect`; nếu config nằm trong writable layer thì thay đổi có thể mất khi container bị recreate, nên đưa patch này vào quy trình provisioning hoặc reapply sau recreate.

Chỉ tiếp tục nếu lỗi là embedding/provider (ví dụ thiếu credential), Telegram/Gateway còn bình thường, và người vận hành chấp nhận mất semantic search. Nếu FTS cũng hỏng hoặc database lỗi, chuyển sang quy trình sửa database/compaction phù hợp.

## Dry-run và backup

Tạo thư mục backup riêng, quyền hạn chế, trước mọi ghi production:

```bash
backup='/root/_Backups/YYYYMMDDTHHMMSSZ_member_memory_fts_only'
umask 077
install -d -m 700 "$backup"
```

Sao lưu config bằng đúng đường dẫn lấy từ `openclaw config file`:

```bash
config_path=/path/reported/by/openclaw-config-file
docker cp "$container:$config_path" "$backup/openclaw.json.before"
chmod 600 "$backup/openclaw.json.before"
```

Sao lưu SQLite bằng SQLite Backup API; không `cp` thẳng database đang được ghi. Thay `db_path` bằng `dbPath` lấy từ status:

```bash
db_path=/path/reported/by/memory-status
db_tmp=/tmp/openclaw-agent-before-fts-index.sqlite

docker exec -i "$container" python3 - "$db_path" "$db_tmp" <<'PY'
import pathlib
import sqlite3
import sys

source_path, target_path = sys.argv[1:3]
pathlib.Path(target_path).unlink(missing_ok=True)
source = sqlite3.connect(f"file:{source_path}?mode=ro", uri=True)
target = sqlite3.connect(target_path)
with target:
    source.backup(target)
check = target.execute("PRAGMA quick_check").fetchone()
source.close()
target.close()
pathlib.Path(target_path).chmod(0o600)
if not check or check[0] != "ok":
    raise SystemExit("SQLite snapshot quick_check failed")
PY

docker cp "$container:$db_tmp" "$backup/openclaw-agent.sqlite.before-index"
chmod 600 "$backup/openclaw-agent.sqlite.before-index"
docker exec "$container" python3 -c \
  'import pathlib,sys; pathlib.Path(sys.argv[1]).unlink(missing_ok=True)' "$db_tmp"
```

Snapshot phải nằm trong backup directory, có quyền `600`, tồn tại và khác rỗng trước khi reindex. Không cần khôi phục database chỉ vì đổi sang FTS-only; snapshot dùng cho rollback có kiểm soát. Nếu container thiếu Python `sqlite3`, quiesce riêng Gateway rồi tạo snapshot bằng công cụ SQLite có sẵn; không recreate container.

Kiểm tra patch mà không ghi:

```bash
printf '%s\n' '{"memory":{"search":{"provider":"none","fallback":"none"}}}' \
  | docker exec -i "$container" openclaw config patch --stdin --dry-run
```

Payload trên áp dụng cho root `memory.search` khi member chỉ có một agent hoặc đã chấp thuận áp dụng chung. Nếu chỉ áp dụng cho agent có override, dùng payload tương ứng sau (thay `main` bằng ID đã kiểm tra):

```json
{"agents":{"entries":{"main":{"memory":{"search":{"provider":"none","fallback":"none"}}}}}}
```

Lệnh dry-run phải xác nhận patch hợp lệ. Nếu phiên bản OpenClaw không có `config patch`, đọc `openclaw config --help` rồi dùng `config set` tương đương; không tự sửa JSON bằng cách thay chuỗi mù quáng.

## Apply

Áp dụng patch đã dry-run, rồi validate trước khi reindex:

```bash
printf '%s\n' '{"memory":{"search":{"provider":"none","fallback":"none"}}}' \
  | docker exec -i "$container" openclaw config patch --stdin
docker exec "$container" openclaw config validate
```

Khi chọn per-agent scope, thay payload root trong ví dụ bằng payload `agents.entries.<agent>.memory.search` ở phần dry-run. Chỉ thay hai khóa `provider` và `fallback`; giữ nguyên các khóa search khác.

Reindex đúng agent sau khi đã có SQLite snapshot:

```bash
docker exec "$container" openclaw memory index --force --agent "$agent" --verbose
```

Config watcher thường tự reload Gateway. Nếu không reload, chỉ restart/quiesce Gateway của member theo process manager đã xác định; không recreate container và không restart toàn VPS. Không gửi tin Telegram thật để thử nếu chưa được yêu cầu.

## Kiểm tra sau apply

```bash
docker exec "$container" openclaw config get memory.search --json
docker exec "$container" openclaw memory status --deep --agent "$agent" --json
docker exec "$container" openclaw memory search \
  --agent "$agent" --query '<từ khóa an toàn đã biết trong workspace>' \
  --max-results 3 --json
docker exec "$container" openclaw channels status --channel telegram --probe --json
```

Đạt khi:

- `provider` và `requestedProvider` là `none`;
- `custom.searchMode` là `fts-only`, `fts.enabled` và `fts.available` là `true`;
- `dirty` là `false`, số file/chunk đã index không thiếu, `scan.issues` rỗng;
- vector/semantic store bị disabled;
- truy vấn trả về kết quả FTS;
- Gateway/Telegram vẫn `connected`/`ready`, `lastError` không có lỗi mới;
- log sau thời điểm apply không còn vòng lặp `embedding provider ... unavailable` hoặc thiếu credential.

Không coi dòng `Embeddings unavailable (FTS-only mode)` trong status là incident sau khi các điều kiện trên đạt. Không dùng `memory forget` để “sửa” lỗi.

## Rerun và rollback

Patch là idempotent. Có thể chạy lại `config patch` và `memory index --force` khi index dirty hoặc sau khi file memory thay đổi; mỗi lần apply production vẫn phải có backup và kiểm tra lại.

Rollback có kiểm soát:

1. Quiesce/stop riêng Gateway để nó không ghi config hoặc session.
2. Khôi phục `openclaw.json.before` vào đúng `<CONFIG_PATH>`, đặt owner/quyền như file gốc.
3. Chạy `openclaw config validate`, rồi khởi động lại Gateway.
4. Nếu khôi phục provider embedding, chỉ reindex sau khi credential đã được cấu hình hợp lệ.

Chỉ khôi phục `openclaw-agent.sqlite.before-index` khi cần trạng thái lịch sử chính xác và chắc chắn không có memory mới sau snapshot; nếu không, giữ database hiện tại và reindex từ các file memory để tránh làm mất dữ liệu phát sinh sau đó. Không xóa database, transcript hoặc workspace.

## Bàn giao

Ghi vào `/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md`: member/agent (không ghi token), nguyên nhân thiếu embedding credential, backup directory, kết quả reindex/status/search và caveat writable-layer nếu có. Skill này phải được đồng bộ vào skill root của OpenClaw nếu agent OpenClaw cần gọi trực tiếp; bản global tại `/root/.agents/skills/openclaw-memory-fts-only/SKILL.md` là bản dùng chung.

Các lệnh trên đã được kiểm tra với OpenClaw 2026.8.2; trên bản khác phải xem `openclaw config --help` và `openclaw memory --help` trước khi apply.
