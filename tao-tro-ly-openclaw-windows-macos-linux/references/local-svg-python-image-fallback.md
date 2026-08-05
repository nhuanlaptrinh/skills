# Fallback tạo ảnh local bằng SVG/Python

Dùng checklist này khi user yêu cầu tạo ảnh/poster/banner nhưng OpenClaw hoặc bot báo thiếu API key cho OpenAI/Gemini/Fal/OpenRouter image provider.

## Nguyên tắc

- Không dừng ở lỗi thiếu image provider key nếu ảnh có thể là poster, banner, thumbnail, infographic, cover khóa học, ảnh chữ, ảnh quảng bá đơn giản.
- Ưu tiên tạo bằng SVG/Python local giống member mẫu `anhlaptrinh`.
- Chỉ cần AI image provider khi user yêu cầu ảnh photorealistic, minh họa phức tạp, style nghệ thuật sinh ảnh, hoặc ảnh cần model diffusion.
- Lưu output trong workspace OpenClaw của member VPS, ví dụ `/root/.openclaw/workspace/<ten_file>.svg` và `.png` bên trong container.

## Kiểm tra/cài công cụ

Trên host hoặc trong container member VPS:

```bash
python3 --version
command -v convert || true
command -v rsvg-convert || true
stat -c '%a %U:%G %n' /tmp
```

Nếu thiếu hoặc `/tmp` sai quyền:

```bash
chmod 1777 /tmp
apt-get update
apt-get install -y imagemagick librsvg2-bin python3
```

## Cách tạo poster bằng SVG rồi xuất PNG

Chạy trong container member VPS:

```bash
docker exec -e HOME=/root user-<ten_user> sh -lc 'mkdir -p /root/.openclaw/workspace'
docker exec -i -e HOME=/root user-<ten_user> python3 - <<'PY'
from pathlib import Path
workspace = Path('/root/.openclaw/workspace')
svg_path = workspace / 'poster_demo.svg'
png_path = workspace / 'poster_demo.png'
svg = '''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="800" viewBox="0 0 1200 800">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#102a43"/><stop offset="1" stop-color="#0ea5e9"/></linearGradient>
    <style>.font{font-family:Arial,Helvetica,sans-serif}.title{font-size:72px;font-weight:900;fill:#fff}.sub{font-size:34px;font-weight:700;fill:#fde68a}.txt{font-size:30px;fill:#e0f2fe}</style>
  </defs>
  <rect width="1200" height="800" fill="url(#bg)"/>
  <circle cx="1010" cy="130" r="150" fill="#ffffff" opacity="0.12"/>
  <text class="font title" x="80" y="170">TỰ ĐỘNG HÓA CÔNG VIỆC</text>
  <text class="font sub" x="80" y="235">với A.I và trợ lý ảo</text>
  <rect x="80" y="310" width="680" height="270" rx="32" fill="#ffffff" opacity="0.13"/>
  <text class="font txt" x="125" y="380">✓ Tạo trợ lý làm việc qua Telegram</text>
  <text class="font txt" x="125" y="440">✓ Xử lý file, nội dung, báo cáo</text>
  <text class="font txt" x="125" y="500">✓ Tự động hóa workflow hằng ngày</text>
  <rect x="80" y="650" width="360" height="70" rx="35" fill="#22c55e"/>
  <text class="font" x="260" y="696" text-anchor="middle" font-size="30" font-weight="900" fill="#fff">BẮT ĐẦU NGAY</text>
</svg>'''
svg_path.write_text(svg, encoding='utf-8')
print(svg_path)
print(png_path)
PY
# Ưu tiên rsvg-convert cho SVG; fallback convert nếu cần
docker exec -e HOME=/root user-<ten_user> sh -lc 'rsvg-convert /root/.openclaw/workspace/poster_demo.svg -o /root/.openclaw/workspace/poster_demo.png || convert /root/.openclaw/workspace/poster_demo.svg /root/.openclaw/workspace/poster_demo.png; file /root/.openclaw/workspace/poster_demo.png'
```

## Quy tắc thiết kế nhanh

- Dùng SVG cho poster chữ, banner khóa học, infographic đơn giản.
- Kích thước phổ biến: `1200x800`, `1080x1080`, `1080x1920`.
- Font an toàn: `Arial`, `Helvetica`, `DejaVu Sans`.
- Dùng gradient, card bo góc, icon vector, CTA rõ.
- Tránh text quá dài; chia thành headline, subtitle, 3-5 bullet, CTA.
- Nếu cần ảnh chân dung/thật, có thể chèn file ảnh có sẵn bằng tag `<image href="...">`, nhưng phải đảm bảo file tồn tại trong workspace.

## Câu trả lời đúng khi thiếu provider key

Không trả lời kiểu “em chưa thể tạo ảnh vì thiếu API key” nếu có thể làm bằng code. Trả lời và hành động như sau:

> Provider tạo ảnh AI chưa có key, nên em sẽ tạo poster dạng thiết kế SVG/Python local trước, giống workflow member `anhlaptrinh`, rồi xuất PNG trong workspace.

Sau khi tạo xong, báo đường dẫn `.svg` và `.png`.
