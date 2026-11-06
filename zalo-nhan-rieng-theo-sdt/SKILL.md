---
name: Zalo nhắn riêng theo SĐT
description: >-
  Dùng khi cần bật hoặc sao chép tính năng nhắn riêng Zalo theo số điện thoại
  cho một member OpenClaw trên bất kỳ VPS nào: tích hợp tool tìm theo SĐT, gán
  chủ sở hữu, rồi tra số trước khi gửi tin nhắn riêng.
---
# Zalo nhắn riêng theo SĐT

Bật cho một member OpenClaw khả năng tìm tài khoản Zalo theo số điện thoại rồi nhắn riêng. Áp dụng cho mọi VPS/member có plugin Zalo (`@openclaw/zalouser` / `zca-js`). Chỉ sửa member được chỉ định.

## Nguyên tắc an toàn

- Backup mọi file trước khi sửa. Mỗi thay đổi cần rollback. Ghi nhật ký thay đổi nếu VPS có sổ nhật ký.
- Không in secret, token, `.env`, cookie, QR.
- Không gửi tin thử, không đăng xuất Zalo, không tạo QR, không tạo phiên Zalo mới.
- Không sửa Docker image dùng chung, template hay member khác. Nếu plugin nằm trong image chung: chỉ override trong volume dữ liệu của member đó. Không làm được thì dừng và báo.
- Không `docker restart`/`docker stop` container. Chỉ reload process `openclaw-gateway` bên trong container (ví dụ `supervisorctl restart openclaw-gateway`). Nạp lại plugin/gateway có thể gián đoạn phiên Zalo: hỏi người dùng trước khi reload, trừ khi họ đã chấp nhận.
- Lệnh docker phải có timeout.
- Không gọi `api.findUser` với số ngẫu nhiên. Chỉ test số thật khi người dùng cho một số đã biết.

## 1. Khảo sát

1. Xác định container và thư mục dữ liệu OpenClaw của member.
2. Tìm plugin `@openclaw/zalouser` trong volume riêng của member. Xác nhận thư viện `zca-js` có `api.findUser(phoneNumber)`.
3. Xem catalog tool: đã có tool tra số chưa (tên thường là `zalouser_find_user_by_phone`).
4. Xem `openclaw.json`: `commands.ownerAllowFrom`, kênh `zalouser`, `approvals.exec` và `approvals.plugin`. Không in token.
5. Kiểm tra Zalo profile `default` còn linked/running/connected không (chỉ xem status, không probe/QR).

## 2. Thêm tool tìm theo SĐT

Nếu chưa có tool:

1. Thêm công cụ OpenClaw `zalouser_find_user_by_phone` (hoặc tên khớp convention plugin).
2. Đầu vào: một `phoneNumber`. Chuẩn hóa `0xxx` và `+84`.
3. Dùng phiên Zalo đang kết nối: `const result = await api.findUser(phoneNumber);`. Đây là lời gọi thư viện, không phải lệnh gõ trong Zalo, không tạo phiên mới.
4. API phiên đang chạy thường nằm trong cache nội bộ (`apiByProfile`) không có getter công khai. Lấy api cùng cách các tool gửi tin hiện có đang lấy, hoặc thêm getter an toàn. Không tự login/QR.
5. Trả về mã tài khoản (user id) và tên hiển thị. Xử lý rõ: không tìm thấy, Zalo từ chối, chưa đăng nhập/mất phiên.
6. Phân quyền: chỉ owner trong `commands.ownerAllowFrom`, chỉ hội thoại riêng (DM). Không tìm hàng loạt, không loop nhiều số. Nên giới hạn tốc độ (ví dụ 30 giây/lần, tối đa 10 lần/giờ).
7. Mô tả tool phải nêu: tìm được tài khoản không đảm bảo nhắn được (quyền riêng tư / chặn người lạ).

Sau khi sửa, nạp lại gateway bên trong container (khi đã được phép). Kiểm tra catalog có tool mới và Zalo vẫn connected.

## 3. Gán chủ sở hữu Zalo (nếu được cung cấp ID)

Khi người dùng đưa Zalo ID để làm chủ, toàn quyền:

1. Backup `openclaw.json` của member.
2. Thêm `zalouser:<ZALO_ID>` vào `commands.ownerAllowFrom`. Giữ các owner Telegram/Zalo đang có, trừ khi họ bảo gỡ.
3. Thêm target duyệt để chủ có quyền duyệt exec/plugin:
   - `approvals.exec.targets`: `{ "channel": "zalouser", "accountId": "default", "to": "<ZALO_ID>" }`
   - `approvals.plugin.targets`: cùng channel/account/to
   - `accountId` lấy theo tên account Zalo thực tế của member (thường là `default`).
4. Nạp lại gateway trong container để cấu hình có hiệu lực.
5. Báo cho họ nhắn riêng bot bằng đúng tài khoản Zalo đó để dùng quyền chủ.

Không thay `allowFrom: ["*"]` của kênh, trừ khi họ yêu cầu thu hẹp.

## 4. Luồng nhắn riêng theo SĐT

Khi người dùng (owner) nhắn riêng và yêu cầu nhắn cho một số điện thoại:

1. Tra số bằng `zalouser_find_user_by_phone`.
2. Báo tên và mã tài khoản tìm được.
3. Xác nhận đúng người rồi mới gửi nội dung qua kênh Zalo đang có (tool gửi tin sẵn có).
4. Kiểm tra kết quả gửi và báo lại. Nếu không tìm thấy, Zalo từ chối, hoặc đối phương chặn tin người lạ thì nói rõ, không thử lại hàng loạt.

Không tự gửi tin khi chỉ được yêu cầu tích hợp/cấu hình.

## 5. Báo cáo

Báo: file đã sửa, đường dẫn backup và rollback, tool đã đăng ký chưa, đã reload chưa, Zalo còn connected không, owner nào đã thêm (không in secret). Nhắc: tìm được không đồng nghĩa nhắn được; nâng cấp plugin có thể ghi đè bản tích hợp.
