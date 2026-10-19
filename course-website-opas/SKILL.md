---
name: course-website-opas
description: Vận hành, kiểm tra và triển khai website khóa học OPAS tại opas.anhlaptrinh.vn, bản copy độc lập của mẫu OPLW. Dùng khi sửa nội dung, chatbot, static, Docker, domain hoặc kiểm tra đăng ký và thanh toán của riêng OPAS.
---

# Website Khóa Học OPAS

## Phạm vi và đường dẫn

- Project: `/root/Apps/course_websites/10Web_BH/37_domain_opas`.
- Website: `https://opas.anhlaptrinh.vn/`.
- Tên chương trình: **TẠO NHÂN VIÊN AI NHƯ NGƯỜI THẬT – BIẾT SỬ DỤNG MÁY TÍNH, TỰ LÀM VIỆC!**.
- Nguồn copy: `/root/Apps/course_websites/10Web_BH/03_domain_oplw`; không sửa bản gốc khi vận hành OPAS.
- Container `opas-django`, port `127.0.0.1:8023 -> 8000`.
- Nginx: `/etc/nginx/sites-available/opas.anhlaptrinh.vn`; HTTPS Let's Encrypt, Certbot tự gia hạn.
- Knowledge: `/root/Data/second_brain/Second_Brain/01_chuong_trinh_dao_tao/37_domain_opas`.
- Project note: `/root/_Second_AI_Brain/projects/opas_website.md`.

## Khi nào dùng

Dùng để kiểm tra website OPAS, sửa template `trolyai/templates/trolyai/index.html`, cập nhật tri thức chatbot, restart/rebuild container hoặc chẩn đoán đăng ký/thanh toán. Đây không phải yêu cầu sửa website OPLW, portal ALT, agent OpenClaw hay tự chạy chiến dịch quảng cáo.

## Nhận diện và nội dung đầu trang

- Từ 2026-10-15, dùng tên khóa hiện hành ở phần phạm vi cho title, H1, footer, đăng ký/thanh toán và chatbot; không khôi phục tên khóa cũ khi sửa nội dung khác.
- Khối `#before-registration` nằm ngay sau hero và trước `#autonomous-ai`, luôn mở để người xem đọc ngay: khóa có thu phí từ năm 2020; cách học thực chiến, vướng đâu gỡ đó; cân nhắc sự phù hợp trước khi trả tiền.
- Khi đổi tên, đồng bộ `COURSE_NAME` trong `trolyai/views.py`, tên trong template, `COURSE_TITLE` mặc định trong `trolyai/course_advisor.py`, dòng metadata không nhạy cảm `COURSE_TITLE` trong `.env`/`.env.example` và Markdown knowledge đang nạp. Chỉ sửa đúng metadata được yêu cầu, không in hoặc thay credential; phải recreate container để nạp env mới.
- Giữ học phí, VAT, ưu đãi và chính sách hoàn tiền hiện hành; không thêm cam kết kết quả hoặc tự gửi thông báo thật.

## Định vị chương trình và vai trò công cụ

- OPAS dạy tạo đội nhân viên AI, không phải khóa học chỉ về OpenClaw. Không dùng “chương trình OpenClaw” hoặc gọi OpenClaw là toàn bộ khóa học trong nội dung OPAS.
- OpenClaw là một công cụ triển khai/vận hành; Antigravity như “giám đốc kỹ thuật” hỗ trợ học viên; Codex hoặc Claude làm “bộ não” cho trợ lý. Các vai trò là cách diễn giải công cụ, không phải nhân sự thật đi kèm khóa học.
- Giữ khối `#tool-ecosystem` trong phần giới thiệu; đồng bộ vai trò trên hero/meta, Q&A, nội dung bài học, dữ liệu khóa trong JavaScript, prompt chatbot, Markdown và FAQ CSV/XLSX.
- Không thay tên biến `OPENCLAW_BRIDGE_*`, URL kỹ thuật, mã project hoặc backend `oplw` chỉ vì chỉnh định vị nội dung. Đây không phải yêu cầu đổi cấu hình runtime, tài khoản AI hoặc model.
- Test `trolyai.test_opas` bao gồm vai trò công cụ và prompt chatbot mock, không phát sinh request AI/thông báo thật. Kiểm tra `_read_course_context('37_domain_opas')` vẫn có đủ ba vai trò sau giới hạn context 32.000 ký tự.
- Với thay đổi chỉ template/Python/knowledge đang bind-mount, có thể `docker compose restart opas-django` rồi kiểm tra lại. Nếu đổi dependency/image/static, dùng workflow rebuild đang ghi bên dưới. Không restart OpenClaw dùng chung.

## Dry-run và kiểm tra an toàn

```bash
cd /root/Apps/course_websites/10Web_BH/37_domain_opas
docker compose config --quiet
docker compose run --rm --no-deps opas-django python manage.py check
docker compose run --rm --no-deps opas-django python manage.py test trolyai.test_opas --noinput
nginx -t
```

Không dùng `docker compose config` không có `--quiet`, không in `.env`. Bộ `trolyai.test_opas` mock email, webhook và thanh toán, dùng database test riêng; không gửi tin hoặc tạo membership thật.

## Chạy thật và rerun

```bash
cd /root/Apps/course_websites/10Web_BH/37_domain_opas
docker compose up -d --build
docker compose ps
curl -I -H 'Host: opas.anhlaptrinh.vn' http://127.0.0.1:8023/
curl -I https://opas.anhlaptrinh.vn/
```

Entrypoint migrate, collectstatic rồi chạy Gunicorn. WhiteNoise phục vụ static khi `DEBUG=False`. Rerun cùng lệnh sau khi cập nhật code/static; không xóa database. Backup compose/nginx trước khi sửa, dùng SQLite backup API nếu cần snapshot database đang hoạt động. Không có render/video/upload/post hoặc cron riêng trong workflow này.

## Input và output

- Nội dung public: template và static trong project; bộ não Markdown trong thư mục knowledge riêng.
- Form đăng ký nhận tên, email, điện thoại; tạo `Registration` và `Order` trong `db.sqlite3` riêng, mã chuyển khoản `OPAS<digits>`.
- Học phí, VAT, coupon, tài khoản ngân hàng, video, logo và Whop plan giữ theo mẫu khi tạo bản copy. OPAS không tặng tài khoản Google AI Pro/Gemini; các mention Gemini còn lại chỉ là mô tả lựa chọn API kỹ thuật. Không đổi giá hoặc ưu đãi nếu chưa được yêu cầu rõ.
- Chatbot `/api/course-advisor/` dùng `COURSE_CODE=37_domain_opas`; đọc knowledge OPAS nhưng tái sử dụng Bridge backend `oplw` của mẫu, không có agent mới.
- Docker Compose chỉ đọc `.env` riêng của OPAS. Credential là placeholder an toàn cho tới khi chủ VPS cấp cấu hình riêng; không copy/in secret và không sửa `.env` nguồn.
- Các thông báo đăng ký/kích hoạt gọi webhook n8n giống mẫu. Email/Zalo/Sheet được xử lý downstream; website không ghi trực tiếp Google Sheet. Không suy luận đã ghi Sheet/gửi tin thành công chỉ vì n8n nhận request.

## Callback và giới hạn nghiệm thu

- Payment IPN mới: `/payment/ipn/`, chỉ nhận sự kiện có `X-Secret-Key` đúng cấu hình; cần SePay/Bank Hub chuyển giao dịch prefix OPAS tới domain mới.
- Whop webhook: `/api/whop/webhook/`; muốn xác nhận kích hoạt bằng webhook phải cấu hình endpoint và secret tương ứng ở provider.
- Khi tạo website chưa thay đổi cấu hình SePay/Bank Hub/Whop ở bên ngoài và không thực hiện thanh toán thật. Xem project note trước khi thông báo auto-confirm/kích hoạt đã hoạt động end-to-end.
- Bộ test kế thừa từ mẫu có hai assertion không khớp template hiện hành: kỳ vọng đếm ngược tự redirect và kỳ vọng trang payment success trả 200 thay vì redirect. Không sửa logic khóa học chỉ để làm các test cũ xanh; các test mới OPAS phải qua.

## An toàn và bàn giao

- Đọc tài liệu bắt buộc của `/root/_Second_AI_Brain` và checklist production trước khi sửa.
- Không copy customer history/database/log, không lộ API key, cookie, token, secret hoặc nội dung `.env` vào tài liệu/log/câu trả lời.
- Không gửi webhook, Telegram/Zalo/email thật, tạo đơn hàng thật, membership hoặc giao dịch thật để test nếu chưa được phép rõ ràng.
- Khi tạo khóa đã bổ sung OPAS vào danh mục portal ALT, nhưng những lần sửa riêng OPAS sau này không được tự sửa portal ALT, website OPLW, DNS wildcard hoặc restart OpenClaw/N8N dùng chung ngoài phạm vi yêu cầu.
- Sau thay đổi đường dẫn, cách chạy, input/output hoặc logic workflow, cập nhật skill này, project note và `/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md`.
