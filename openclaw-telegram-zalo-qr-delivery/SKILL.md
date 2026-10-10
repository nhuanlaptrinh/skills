---
name: openclaw-telegram-zalo-qr-delivery
description: Tạo và gửi ảnh QR đăng nhập Zalo Personal trực tiếp qua bot Telegram OpenClaw khi owner yêu cầu kết nối zalouser, đăng nhập lại hoặc bot nói phải mở app/dashboard và nhập connect zalouser. Chẩn đoán đúng runtime, chọn đúng bot/account/agent, giữ tiến trình login sống và xác minh biên nhận gửi ảnh; không dùng cho OTP hay QR thanh toán.
---

# Gửi QR Zalo qua Telegram, không chuyển việc sang dashboard

Nếu runtime đã cài `telegram-zalo-owner-login`, ưu tiên tool `telegram_zalo_login_qr` cho owner yêu cầu login trong Telegram riêng, hoặc lệnh native `/zaloqr`. Tool xác minh owner từ cấu hình hiện tại và gửi ảnh riêng cho đúng sender. Để cài/nâng cấp luồng này trên một Docker member đã chọn, dùng skill `telegram-zalo-owner-login`; không tự rollout sang member khác.

## Kết quả cần đạt

Khi owner đã yêu cầu hoặc cho phép đăng nhập Zalo, tự khởi tạo login trong đúng OpenClaw runtime và gửi **ảnh QR còn hiệu lực** vào Telegram riêng của owner. Người dùng chỉ cần quét và xác nhận bằng Zalo trên điện thoại. Không kết luận “phải mở OpenClaw app/dashboard → nhập connect zalouser” chỉ vì công cụ chat trả về một hướng dẫn như vậy.

Phân biệt ba trạng thái: **chưa tạo QR**, **đã gửi QR có biên nhận**, **đăng nhập đã xác minh**. Tạo skill không có nghĩa đã sửa mọi bot hoặc đã đăng nhập thành công.

## Xác định đúng bot trước khi chạy

- Lấy Telegram account/bot, owner nhận QR, agent, Zalo account và runtime từ phiên yêu cầu và cấu hình/binding hiện có. Telegram account và Zalo account là hai giá trị khác nhau; không mặc định cả hai là `default`.
- Nếu là Docker/member/VPS khác, thực hiện kiểm tra và login trong đúng container/host, với HOME, state/config path của runtime đó. Không đăng nhập nhầm Zalo trên VPS chính. Không sao chép credential giữa các member.
- QR là dữ liệu xác thực: chỉ gửi DM cho owner đã xác minh. Nếu yêu cầu xuất phát từ group, gửi QR vào DM owner, không gửi vào group. Không lấy owner của member khác hoặc tự cấp quyền cho người nhận.
- Chỉ hỏi một câu xác định bot/runtime nếu ngữ cảnh thực sự không đủ. Lỗi thiếu quyền phải nêu quyền đang thiếu; sự cho phép của người dùng không tự mở khóa policy của công cụ.

## Quy trình ưu tiên

1. Báo ngắn: “Em đang tạo QR và sẽ gửi ngay tại Telegram; anh chỉ cần quét bằng Zalo.” Dùng công cụ gửi thực nếu cần báo tiến độ, không hứa gửi khi chưa có đường thực thi.
2. Đọc hướng dẫn VPS/project nếu có. Kiểm tra chỉ đọc: phiên Zalo hiện tại, Telegram account còn gửi được, plugin `zalouser` đã load và cú pháp CLI thực tế. Dùng `openclaw channels login --help`, `openclaw message send --help` và trợ giúp status/plugin theo phiên bản đã cài. Không in toàn bộ config hoặc log chứa secret.
3. Nếu Zalo đã kết nối tốt và người dùng không yêu cầu tạo phiên mới, thông báo trạng thái, không logout để ép sinh QR. Nếu cần dừng riêng Zalo account đang chạy để relogin, xác nhận việc gián đoạn nằm trong yêu cầu; backup cấu hình/credential tại nơi riêng tư trước khi thay đổi. Không restart toàn gateway hoặc dừng Telegram để tạo QR.
4. Khởi tạo login bằng CLI/runtime có hỗ trợ, không phụ thuộc chat thiết lập. Trên runtime đã kiểm tra hỗ trợ `--agent`, mẫu lệnh là:

   ```bash
   openclaw channels login --channel zalouser --account "$ZALO_ACCOUNT" --agent "$AGENT_ID" --verbose
   ```

   Kiểm tra `--help` trước khi áp dụng cho phiên bản khác; không truyền cờ không được hỗ trợ. `--agent` phải là owner thực tế của channel discovery, không đoán `main`. Giữ tiến trình sống bằng exec session/PTY có thể poll, **không chờ CLI kết thúc rồi mới tìm QR**. Không dùng timeout ngắn giết login ngay sau khi sinh ảnh. Giữ verbose output riêng tư.
5. Theo dõi stdout/stderr và đường dẫn QR mà runtime công bố, ví dụ `Scan QR image: ...`. Đọc file thực trong đúng runtime, xác minh ảnh không rỗng, đúng QR của lần login hiện tại và còn hiệu lực. Nếu runtime trả data URI/base64 hoặc payload QR, dùng bộ giải mã/render local đã có. Không chụp cả terminal có credential, không bịa ảnh từ lời hướng dẫn, không gửi ASCII QR như thể là ảnh.
6. Chép ảnh vào thư mục media outbound được runtime cho phép, với quyền riêng tư phù hợp. Nếu file ở container/remote, gửi từ runtime đó hoặc chuyển đúng ảnh về runtime gửi; đường dẫn host không tự tồn tại trong container. Không sửa rộng media allowlist, không đưa QR lên web/public CDN.
7. Gửi **ngay khi QR xuất hiện**, trong lúc login vẫn đang chờ quét. Ưu tiên công cụ message của phiên với account/target rõ ràng; nếu dùng CLI và phiên bản hỗ trợ cú pháp này:

   ```bash
   openclaw message send --channel telegram --account "$TELEGRAM_ACCOUNT" \
     --target "$OWNER_TELEGRAM_ID" --media "$QR_PATH" \
     --message "Anh quét QR bằng Zalo trên điện thoại và xác nhận đăng nhập. Mã có thời hạn ngắn." --json
   ```

   Đòi biên nhận có message ID thực, đúng Telegram destination và đúng bot/account đã chọn. Exit code 0 hoặc file ảnh tồn tại chưa đủ để nói “đã gửi”. Có thể đọc skill `reliable-media-delivery` nếu sẵn có.
8. Tiếp tục poll login tối đa khoảng 180 giây cho mỗi lượt, không kết thúc task ngay sau khi gửi ảnh. Xác minh CLI thành công và status/probe của **đúng Zalo account** đã kết nối; không suy ra từ ảnh đã gửi. Nếu QR hết hạn, báo rõ và chỉ tạo thêm tối đa một lượt QR mới trong cùng yêu cầu. Không login/retry vô hạn.
9. Sau thành công, xóa ảnh tạm do lượt này tạo nếu không còn cần, không xóa credential hoặc dữ liệu cũ. Nếu đã gửi thông báo hoàn tất bằng công cụ message trong OpenClaw, kết thúc bằng `NO_REPLY` để tránh phản hồi trùng. Khi hết thời gian quét, báo “QR đã gửi, nhưng chưa xác minh đăng nhập”, không gọi đó là thành công.

## Khi gặp câu “phải khởi tạo trong OpenClaw app”

- Xem đó là đầu mối chẩn đoán, không phải kết luận. Kiểm tra tool login có thực sự được expose cho agent hay chỉ có lời nhắc setup; chuyển sang exec/CLI hợp lệ nếu có.
- Nếu channel discovery báo nhiều agent/chưa có owner, xác định binding và thử `--agent` được phiên bản hỗ trợ. Không sửa `systemAgent`/ownership của toàn bộ runtime chỉ để né lỗi.
- Nếu CLI login không hỗ trợ phiên bản plugin hiện tại, kiểm tra giao diện login thực trong plugin/runtime đã cài. Chỉ dùng API/SDK được xác minh cùng môi trường và cùng state store; không tự chế RPC hay khởi chạy client Zalo thứ hai song song.
- Nếu thiếu exec/read/media/send, hết quyền hoặc không truy cập đúng runtime, dừng trước thao tác bị cấm. Báo lỗi đã kiểm tra và quyền/công cụ còn thiếu; không tuyên bố dashboard là bắt buộc khi chưa chứng minh, cũng không hứa skill vượt được policy.
- Với QR gửi thất bại: kiểm tra file, allowlist, bot/account, DM đã mở và biên nhận. Chỉ retry một lần sau khi sửa nguyên nhân; nếu kết quả mơ hồ, kiểm tra receipt/history trước để tránh gửi trùng.

## Cẩn trọng với helper cũ trên VPS

Nếu có `openclaw-zalo-qr-login`, đọc script trước khi chọn dùng. Bản helper được kiểm tra ngày 2026-10-09 có các giới hạn:

- `quick_send_zalo_qr.sh` có thao tác cấp quyền và dọn lock; **không chạy mặc định** cho yêu cầu gửi QR.
- `send_zalo_qr_to_telegram_owner.mjs --account` chọn **Zalo account**, không phải Telegram bot. Telegram account được suy ra từ approval targets và phải duy nhất; không phù hợp khi owner dùng nhiều bot hoặc bindings không khớp.
- Helper có thể chép QR sang `/var/www/html/openclaw-qr.png`; **không dùng apply nguyên bản** nếu có nguy cơ công khai ảnh. Ưu tiên CLI + gửi media riêng tư như quy trình trên; không sửa helper/production ngoài phạm vi được yêu cầu.
- Lock thuộc tiến trình đang sống phải được giữ. Không `rm` lock mù quáng hoặc chạy hai tiến trình login cùng account.

## Phạm vi cài đặt

Kho skill dùng lại trên VPS: `/root/.agents/skills/openclaw-telegram-zalo-qr-delivery`.
Để OpenClaw runtime khác sử dụng, cài/copy thư mục skill vào managed skills hoặc workspace skills của **runtime đó**, rồi kiểm tra `openclaw skills info` theo trợ giúp phiên bản. Với agent bị giới hạn workspace, dùng bản trong workspace được phép; không chỉ trỏ tới đường dẫn host ngoài sandbox. Không tự rollout sang mọi member hoặc sửa policy chỉ vì người dùng tạo skill.
