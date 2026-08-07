# Checklist SVG/PNG và lỗi shell approvals path

Dùng checklist này khi tạo trợ lý OpenClaw member VPS hoặc khi user báo lỗi kiểu:

- `Refusing to traverse symlink in exec approvals path...`
- Không chạy được `convert`, `python`, `rsvg-convert`.
- Không convert được SVG sang PNG/JPG.

## 1. Kiểm tra shell có chạy được không

```bash
pwd
readlink -f .
python3 --version
command -v convert || true
command -v rsvg-convert || true
```

Nếu lỗi liên quan `Refusing to traverse symlink in exec approvals path`, tránh chạy trong đường dẫn symlink. Chuyển sang đường dẫn thật:

```bash
cd "$(readlink -f .)"
```

Trong member container, chuẩn bắt buộc là `HOME=/root` và `/root/.openclaw` phải là thư mục thật trên volume persistent. Kiểm tra:

```bash
docker exec -e HOME=/root user-<ten_user> sh -lc 'readlink -f /root/.openclaw; p=$(pgrep -f "^openclaw$" | head -1); tr "\0" "\n" </proc/$p/environ | grep "^HOME="'
```

Nếu `HOME` khác `/root` hoặc `/root/.openclaw` là symlink, dừng Gateway, sửa volume/runtime về root thật rồi restart:

```bash
docker exec user-<ten_user> sh -lc 'test ! -L /root/.openclaw; HOME=/root tmux kill-session -t openclaw 2>/dev/null || true; HOME=/root tmux new-session -d -s openclaw "HOME=/root openclaw skills check && HOME=/root openclaw gateway run"'
```

Không dùng `chmod 777`. Nếu `/root/.openclaw` đang là symlink cũ, backup dữ liệu rồi migrate sang thư mục thật trên volume `/root`; không xóa symlink khi chưa có bản sao và kế hoạch phục hồi.

Nếu đang làm trong project member VPS, ưu tiên đường dẫn thật trên host:

```bash
cd /root/Apps/member_vps/docker-users
```

## 2. Kiểm tra `/tmp`

`apt`, ImageMagick, Python và nhiều tool cần `/tmp` có sticky bit `1777`.

```bash
stat -c '%a %U:%G %n' /tmp
touch /tmp/codex_tmp_check && rm /tmp/codex_tmp_check
```

Nếu không phải `1777`, sửa:

```bash
chmod 1777 /tmp
```

## 3. Cài tool chuyển SVG sang PNG/JPG nếu thiếu

Trên Ubuntu/Debian:

```bash
apt-get update
apt-get install -y imagemagick librsvg2-bin python3
```

- `convert`: ImageMagick, dùng được cho nhiều định dạng.
- `rsvg-convert`: fallback tốt cho SVG thuần.
- `python3`: dùng script kiểm tra hoặc fallback xử lý file.

## 4. Test convert SVG sang PNG

```bash
tmpdir=$(mktemp -d /tmp/svg_convert_check.XXXXXX)
cat > "$tmpdir/check.svg" <<'SVG'
<svg xmlns="http://www.w3.org/2000/svg" width="160" height="80"><rect width="160" height="80" fill="#22c55e"/><text x="20" y="50" font-size="24" fill="white">OK</text></svg>
SVG
convert "$tmpdir/check.svg" "$tmpdir/convert.png"
rsvg-convert "$tmpdir/check.svg" -o "$tmpdir/rsvg.png"
file "$tmpdir/convert.png" "$tmpdir/rsvg.png"
rm -rf "$tmpdir"
```

Kết quả mong muốn: cả hai file là `PNG image data`.

## 5. Khi áp dụng trong container member VPS

Chạy cùng checklist bên trong container:

```bash
docker exec -e HOME=/root user-<ten_user> sh -lc 'stat -c "%a %U:%G %n" /tmp; command -v convert || true; command -v rsvg-convert || true; python3 --version || true'
docker exec -e HOME=/root user-<ten_user> sh -lc 'chmod 1777 /tmp; apt-get update; apt-get install -y imagemagick librsvg2-bin python3'
```

Không tự sửa/xóa file project nếu user chỉ yêu cầu kiểm tra/cài tool.
