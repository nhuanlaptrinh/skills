---
name: "tao-tro-ly-openclaw-member-vps-shared-proxy-update"
description: "Bổ sung quy tắc proxy, Second AI Brain và bàn giao Codex cho skill tạo trợ lý OpenClaw đa nền tảng hiện hành."
---

# Bổ sung cho `tao-tro-ly-openclaw-windows-macos-linux`

Giữ nguyên toàn bộ nội dung skill live hiện hành và bổ sung các quy tắc bắt buộc dưới đây.

## 1. Shared Fallback Proxy

Mỗi khi sử dụng `tao-tro-ly-openclaw-windows-macos-linux` để tạo, cấu hình hoặc vận hành trợ lý OpenClaw trong member VPS, phải đọc và áp dụng:

`/root/AI_Runtime/openclaw/.openclaw/workspace/skills/shared-fallback-proxy-vps/SKILL.md`

Quy tắc:

1. Luôn thử kết nối trực tiếp trước; proxy chỉ là fallback khi direct thất bại.
2. Không bật proxy toàn hệ thống; không sửa `/etc/environment`, shell rc, Docker daemon, systemd global environment hoặc luồng mạng mặc định.
3. Trong member VPS, lưu bí mật tại `/root/.config/openclaw/fallback-proxy.env`, owner `root`, quyền `600`.
4. Kiểm tra file hiện có trước; không ghi đè bí mật nếu chủ hệ thống chưa yêu cầu thay thế.
5. Truyền bí mật qua stdin hoặc kênh quản trị bảo mật; không để URL, username hoặc password proxy xuất hiện trong command line, log, Git, skill hoặc câu trả lời.
6. Kiểm tra riêng quyền file, direct mặc định và một HTTPS URL qua nhánh fallback; chỉ báo kết quả đã che credential.
7. Nếu skill phụ không tồn tại hoặc không đọc được, dừng riêng phần proxy và báo lỗi; không tự suy đoán cấu hình.

## 2. Second AI Brain VPS Structure

Mỗi khi **tạo VPS thành viên mới**, phải đọc và thực hiện thêm skill local:

`/root/.agents/skills/second-ai-brain-vps-structure/SKILL.md`

Nguồn tham chiếu:

`https://github.com/nhuanlaptrinh/second-ai-brain-vps-structure`

Quy tắc triển khai trong VPS/container thành viên:

1. Kiểm tra hiện trạng trước, không ghi đè file hoặc thư mục đã tồn tại.
2. Chạy bootstrap ở chế độ `--dry-run` trước, sau đó mới tạo thật khi kết quả an toàn.
3. Tạo hoặc bảo toàn các thư mục chuẩn: `/root/_Second_AI_Brain`, `/root/Apps`, `/root/Automation`, `/root/Data`, `/root/AI_Runtime`, `/root/_Infra`, `/root/_Backups`, `/root/_Archive`.
4. Tạo hoặc bảo toàn `/root/AGENTS.md` làm entrypoint, yêu cầu AI đọc `_Second_AI_Brain` trước khi sửa project.
5. Bảo đảm bộ file tối thiểu gồm `START_HERE.md`, bản đồ VPS, danh sách project, dịch vụ đang chạy, lệnh vận hành, cảnh báo bảo mật, nhật ký thay đổi, sự cố, quy ước làm việc, workflow AI, checklist production, cùng các thư mục `projects`, `services`, `templates`, `inventories`, `backups`.
6. Ghi thông tin thực tế đã được làm sạch vào bản đồ, project registry và service notes; không chép secret, token, cookie, password, private key hoặc credential.
7. Không đụng vào `/root/.ssh`, `/root/.codex`, `/root/.agents` hay provider credentials nếu người dùng không yêu cầu rõ.
8. Sau khi tạo, cập nhật `/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md` và kiểm tra đủ cấu trúc.
9. Nếu VPS thành viên là container, mọi đường dẫn `/root/...` nêu trên được hiểu là bên trong đúng container `user-<ten_user>`, không phải host chính.

## 3. Chuẩn hóa tên Codex và API Base URL trong kết quả bàn giao

Khi trả kết quả hoặc soạn nội dung bàn giao cho khách hàng:

1. Luôn dùng API Base URL: `https://codex.anhlaptrinh.vn/v1`.
2. Không được hiển thị API Base URL cũ `https://9router.anhlaptrinh.vn/v1`.
3. Không dùng tên “9Router” trong tiêu đề, mô tả tài khoản, tên provider hoặc nội dung bàn giao cho khách hàng. Dùng “Codex” hoặc “Tài khoản API Codex”.
4. Nếu cần nêu provider/model đã cấu hình, ưu tiên tên hiển thị trung lập theo cấu hình thực tế, ví dụ `Codex/codex`; không ghi `9rt/codex` hoặc tên có chữ `9router` trong phần bàn giao.
5. Quy tắc này áp dụng cho mọi mẫu bàn giao VPS, tài khoản API và kết quả tạo/cấu hình trợ lý về sau.
6. Không làm lộ API key; chỉ thông báo API key đã được cài sẵn nếu đúng thực tế.

## Thứ tự workflow bắt buộc khi tạo VPS thành viên

1. Đọc skill chính `tao-tro-ly-openclaw-windows-macos-linux` trong workspace.
2. Đọc `shared-fallback-proxy-vps`.
3. Đọc `second-ai-brain-vps-structure`.
4. Dry-run automation tạo member VPS.
5. Tạo và cấu hình OpenClaw member VPS.
6. Dry-run rồi bootstrap Second AI Brain bên trong member VPS.
7. Cài shared fallback proxy theo nguyên tắc direct-first.
8. Validate OpenClaw, gateway/channel, cấu trúc Second AI Brain và proxy fallback.
9. Báo kết quả đã che toàn bộ credential và dùng chuẩn Codex nêu trên.
