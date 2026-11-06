---
name: Zalo lấy thành viên nhóm
description: >-
  Dùng khi cần bổ sung công cụ lấy thành viên một nhóm Zalo cho member OpenClaw
  có plugin zalouser, cho phép owner ra lệnh trong nhóm hoặc chat riêng, rồi
  nhắn riêng từng thành viên bằng tool gửi tin sẵn có.
---
Bật cho một member OpenClaw khả năng lấy danh sách thành viên một nhóm Zalo, rồi owner có thể ra lệnh trong chính nhóm đó (hoặc chat riêng) để xem danh sách và nhắn riêng từng người. Áp dụng cho mọi VPS/member có plugin Zalo (`@openclaw/zalouser` / `zca-js`). Chỉ sửa member được chỉ định.

Không nhầm với skill [Zalo nhắn riêng theo SĐT](sand-workflow:zalo-nh-n-ri-ng-theo-s-t): skill đó lo tra cứu theo số điện thoại và chỉ dùng trong chat riêng. Skill này không nới quyền tra số ra group, không ghi đè tool `zalouser_find_user_by_phone` nếu đã có.

## Nguyên tắc an toàn

- Backup mọi file trước khi sửa. Mỗi thay đổi cần rollback riêng; không xóa hay ghi đè rollback cũ (kể cả rollback tool SĐT). Ghi nhật ký thay đổi nếu VPS có sổ nhật ký.
- Không in secret, token, `.env`, cookie, QR.
- Không gửi tin thử, không đăng xuất Zalo, không tạo QR, không tạo phiên Zalo mới.
- Không sửa Docker image dùng chung, template hay member khác. Nếu plugin nằm trong image chung: chỉ override trong volume dữ liệu của member đó. Không làm được thì dừng và báo.
- Không `docker restart`/`docker stop` container. Chỉ reload process `openclaw-gateway` bên trong container (ví dụ `supervisorctl restart openclaw-gateway`). Nạp lại plugin/gateway có thể gián đoạn phiên Zalo: hỏi người dùng trước khi reload, trừ khi họ đã chấp nhận cho member đó.
- Lệnh docker phải có timeout.
- Không gọi `api.getGroupInfo` với groupId thật hay ngẫu nhiên khi đang tích hợp. Chỉ test offline bằng API giả.

## 1. Khảo sát

1. Xác định container `user-<tên>` và thư mục dữ liệu OpenClaw của member.
2. Tìm plugin `@openclaw/zalouser` trong volume riêng của member. Xác nhận thư viện `zca-js` có `api.getGroupInfo(groupId)`.
3. Xem catalog tool: đã có `zalouser_get_group_members` chưa; `zalouser_find_user_by_phone` và tool gửi tin `zalouser` có không. Nếu `tools.catalog` hoặc `channels status` lỗi secret-reference thì đừng trích token, kiểm tra file plugin/local info thay thế.
4. Xem `openclaw.json`: `commands.ownerAllowFrom` (cần có `zalouser:<ZALO_ID>` của chủ), kênh `zalouser` (`groupPolicy`, `groupAllowFrom`). Không in token.
5. Kiểm tra Zalo profile `default` còn linked/running/connected không (chỉ xem status, không probe/QR).

## 2. Thêm tool lấy thành viên

Nếu chưa có tool:

1. Thêm công cụ OpenClaw `zalouser_get_group_members` (hoặc tên khớp convention plugin). Đăng ký trong `dist/index.js` và `openclaw.plugin.json` (`contracts.tools`) cạnh các tool zalouser hiện có, không xóa tool SĐT.
2. Đầu vào: `groupId` là chuỗi chữ số. Khi owner đang ở trong một nhóm mà không truyền `groupId`, suy ra ID nhóm từ session/route hiện tại. Khi gọi từ chat riêng thì bắt buộc có `groupId`. Nếu có `groupId` hợp lệ thì dùng ID đó.
3. Dùng phiên Zalo đang kết nối: `const result = await api.getGroupInfo(groupId);`. Đây là lời gọi thư viện, không tạo phiên mới. Lấy API cùng cách tool gửi tin hiện có đang lấy (thường cache `apiByProfile`); không tự login/QR.
4. Đọc thành viên từ thông tin nhóm (thường `gridInfoMap[groupId]`, các list như `memberIds`, `memVerList`, `currentMems`). Trả về ID và tên hiển thị. Lọc ID bot (`api.getOwnId`) và ID trùng. Xử lý rõ: không tìm thấy nhóm, không có quyền xem, Zalo từ chối, chưa đăng nhập/mất phiên.
5. Giới hạn tốc độ: ví dụ 30 giây/lần, tối đa 10 lần/giờ. Không quét hàng loạt, không lấy nhiều nhóm một lần. Tool này chỉ đọc, không gửi tin.
6. Mô tả tool phải nêu: cùng nhóm không đảm bảo nhắn riêng được (quyền riêng tư / chặn người lạ).

## 3. Cho phép owner ra lệnh trong nhóm

Đây là phần dễ sai. Không dùng lại hàm ủy quyền của tool tra SĐT nếu hàm đó bắt buộc chat riêng.

1. Tạo hàm kiểm tra owner riêng cho tool thành viên nhóm:
   - Kênh `zalouser`.
   - ID người gửi khớp một mục `commands.ownerAllowFrom` dạng `zalouser:<id>`.
   - Cho phép cả hội thoại riêng và group/channel/room.
   - Người không phải owner bị từ chối.
2. Không từ chối chỉ vì `context.sessionKey` khớp `:(group|channel|room)`.
3. Không yêu cầu sender === target: điều kiện đó chỉ đúng với DM; trong nhóm `route.to` là ID nhóm còn sender là ID owner.
4. Tool tra SĐT (`zalouser_find_user_by_phone`) vẫn chỉ owner trong hội thoại riêng. Đừng nới quyền đó ra group.
5. Cập nhật mô tả/lỗi của tool thành viên: owner dùng được trong chat riêng hoặc trong nhóm.

Sau khi sửa, nạp lại gateway bên trong container (khi đã được phép). Kiểm tra catalog/file plugin có tool mới và Zalo vẫn connected.

## 4. Nhắn riêng từ lệnh nhóm

Dùng tool gửi tin sẵn có (`zalouser`) với `isGroup: false` tới ID thành viên cụ thể. Không tự gửi tin khi chỉ được yêu cầu tích hợp/cấu hình.

1. Kiểm tra cách tool gửi đang chọn người nhận (`resolveZalouserSendTarget` hoặc tương đương).
2. Nếu owner ra lệnh từ nhóm đã gửi được tin 1-1 tới một user ID (`isGroup: false`, `threadId` tường minh) thì giữ nguyên, không sửa tool gửi.
3. Nếu tool bám nhóm hiện tại hoặc chặn gửi lệch ngữ cảnh, chỉ nới cho owner: được chỉ định người nhận 1-1 và `isGroup: false`. Không cho non-owner gửi hàng loạt. Không đổi hành vi gửi vào chính nhóm nếu không cần.
4. Tool gửi sẵn có có thể không tự kiểm tra owner; ghi rõ hạn chế này khi báo cáo, đừng mở rộng trừ khi người dùng yêu cầu.

## 5. Gán chủ sở hữu Zalo nếu chưa có

Nếu người dùng đưa Zalo ID để làm chủ mà member chưa có `zalouser:<id>` trong `commands.ownerAllowFrom`, làm theo skill [Zalo nhắn riêng theo SĐT](sand-workflow:zalo-nh-n-ri-ng-theo-s-t) phần gán chủ: thêm owner, thêm target duyệt exec/plugin, giữ owner cũ, nạp lại gateway. Không thu hẹp `allowFrom` của kênh trừ khi họ yêu cầu.

## 6. Luồng dùng sau khi tích hợp

Khi owner ra lệnh trong nhóm hoặc chat riêng để lấy thành viên rồi nhắn riêng:

1. Gọi `zalouser_get_group_members` (ở trong nhóm thì có thể bỏ `groupId`).
2. Báo danh sách đã lọc (ID + tên) để người dùng xem lại.
3. Xác nhận rồi mới gửi nội dung qua tool gửi tin sẵn có, `isGroup: false`, từng người.
4. Kiểm tra kết quả từng tin và báo lại. Nếu Zalo từ chối hoặc đối phương chặn tin người lạ thì nói rõ, không thử lại hàng loạt.

Không tự gửi tin khi chỉ được yêu cầu tích hợp.

Kiểm thử offline nên gồm: owner trong DM cần `groupId`; owner trong group suy ra nhóm hiện tại; owner trong group có `groupId` tường minh; non-owner bị từ chối; tool SĐT vẫn từ chối khi session là group; lọc bot/trùng và rate limit vẫn đúng.

## 7. Báo cáo

Báo: file đã sửa, đường dẫn backup và rollback, tool đã đăng ký chưa, đã reload chưa, Zalo còn connected không, owner ra lệnh trong nhóm được chưa, gửi 1-1 từ lệnh nhóm đã được phép chưa, tool SĐT còn nguyên hành vi chat riêng (không in secret). Nhắc: cùng nhóm không đồng nghĩa nhắn được; nâng cấp plugin có thể ghi đè bản tích hợp.
