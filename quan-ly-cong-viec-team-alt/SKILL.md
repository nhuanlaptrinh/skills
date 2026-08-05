---
name: quan-ly-cong-viec-team-alt
description: Quản lý, nhập mới, cập nhật, tra cứu và tổng hợp công việc hằng ngày của team ALT từ kho dữ liệu Markdown tại /root/Data/team_alt/cong_viec. Use khi người dùng hỏi về công việc của Nhuần, Đạt, Nhi, muốn thêm task, xem task chưa xong/bị kẹt, hoặc tổng hợp ngày/tuần/tháng cho team ALT.
---

# Skill: Quản Lý Công Việc Team ALT

## Khi Nào Dùng

Dùng skill này khi người dùng muốn:

- Thêm, sửa, xem hoặc tổng hợp công việc của team ALT.
- Tra cứu công việc của Nhuần, Đạt, Nhi theo ngày.
- Xem việc chưa làm, đang làm, đã xong, bị kẹt hoặc cần hỗ trợ.
- Tạo file công việc ngày mới hoặc file tổng hợp team.
- Hỏi bot quản lý công việc team ALT trên Telegram/OpenClaw.

## Kho Dữ Liệu Chính

- Root dữ liệu: `/root/Data/team_alt/cong_viec/`
- Workspace bot tham chiếu: `/root/.openclaw/workspace_quanlycongviecteamalt/`
- Hướng dẫn trong workspace: `/root/.openclaw/workspace_quanlycongviecteamalt/DATA_SOURCE.md`

Không lưu dữ liệu công việc lâu dài trực tiếp trong workspace bot. Workspace chỉ chứa hướng dẫn/nhận diện bot.

## Nhân Viên Hiện Có

| Tên | Mã nhân viên | Folder |
|---|---|---|
| Nhuần | `nhuan` | `/root/Data/team_alt/cong_viec/nhan_vien/nhuan/` |
| Đạt | `dat` | `/root/Data/team_alt/cong_viec/nhan_vien/dat/` |
| Nhi | `nhi` | `/root/Data/team_alt/cong_viec/nhan_vien/nhi/` |

Nếu người dùng thêm nhân viên mới, tạo folder theo mã không dấu, lowercase, ví dụ `tran_van_a` hoặc `vana` tùy cách đặt ngắn gọn nhất quán.

## Cấu Trúc Dữ Liệu

```text
/root/Data/team_alt/cong_viec/
├── README.md
├── nhan_vien/
│   └── <ma_nhan_vien>/
│       ├── thong_tin.md
│       └── cong_viec/
│           └── YYYY/
│               └── MM/
│                   └── YYYY-MM-DD.md
├── tong_hop/
│   ├── theo_ngay/YYYY/MM/YYYY-MM-DD.md
│   ├── theo_tuan/YYYY/YYYY-Www.md
│   └── theo_thang/YYYY/MM.md
└── mau_nhap_lieu/
    ├── mau_cong_viec_ngay.md
    ├── mau_tong_hop_ngay.md
    └── mau_thong_tin_nhan_vien.md
```

## Quy Tắc File Công Việc Ngày

- Mỗi nhân viên mỗi ngày có một file riêng: `nhan_vien/<ma_nhan_vien>/cong_viec/YYYY/MM/YYYY-MM-DD.md`.
- Một ngày có thể có nhiều việc, dùng mã `CV001`, `CV002`, `CV003`...
- Nếu file ngày chưa tồn tại, tạo từ mẫu: `/root/Data/team_alt/cong_viec/mau_nhap_lieu/mau_cong_viec_ngay.md`.
- Khi thêm việc mới, tìm mã `CVxxx` lớn nhất hiện có trong file ngày rồi tăng thêm 1.
- Không xóa nội dung cũ nếu người dùng chỉ yêu cầu thêm việc.

## Trạng Thái Chuẩn

Chỉ dùng các trạng thái sau để dễ truy xuất:

- `Chưa làm`
- `Đang làm`
- `Đã xong`
- `Bị kẹt`
- `Hủy`

Ưu tiên chuẩn:

- `Cao`
- `Trung bình`
- `Thấp`

## Quy Trình Thêm Việc

1. Xác định nhân viên, ngày, tên công việc, deadline, ưu tiên, người giao nếu có.
2. Mở hoặc tạo file ngày đúng đường dẫn.
3. Thêm một dòng vào mục `Bảng nhanh`.
4. Thêm block chi tiết tương ứng trong mục `Chi tiết công việc`.
5. Giữ nguyên các việc cũ.
6. Nếu người dùng yêu cầu tổng hợp team, cập nhật thêm file `tong_hop/theo_ngay/YYYY/MM/YYYY-MM-DD.md`.

Mẫu block chi tiết:

```markdown
### CV001 - Tên công việc

- Người giao:
- Dự án/liên quan:
- Mô tả:
- Kết quả mong muốn:
- Kết quả thực tế:
- Link/file liên quan:
- Vấn đề bị kẹt:
- Cần hỗ trợ:
- Ghi chú:
```

## Quy Trình Tra Cứu

- Hỏi công việc của một người trong ngày: đọc file ngày của người đó.
- Hỏi toàn team trong ngày: đọc cả 3 file ngày của `nhuan`, `dat`, `nhi`, sau đó nếu có file tổng hợp thì đối chiếu.
- Hỏi việc chưa xong: lọc trạng thái `Chưa làm`, `Đang làm`, `Bị kẹt`.
- Hỏi việc bị kẹt: tìm `Bị kẹt`, `Vấn đề bị kẹt`, hoặc `Cần hỗ trợ`.
- Hỏi theo tháng/tuần: duyệt các file trong folder `YYYY/MM` hoặc file tổng hợp tương ứng nếu đã có.

## Quy Trình Tổng Hợp Ngày

1. Đọc file ngày của từng nhân viên.
2. Đếm số việc theo trạng thái.
3. Ghi/tạo file tổng hợp tại `tong_hop/theo_ngay/YYYY/MM/YYYY-MM-DD.md`.
4. Nêu rõ việc cần quản lý xử lý và việc chuyển sang ngày tiếp theo.

## Lệnh Kiểm Tra Nhanh

Liệt kê dữ liệu:

```bash
find /root/Data/team_alt/cong_viec -type f | sort
```

Tìm việc bị kẹt:

```bash
rg -n "Bị kẹt|Vấn đề bị kẹt|Cần hỗ trợ" /root/Data/team_alt/cong_viec/nhan_vien
```

Tìm việc chưa xong:

```bash
rg -n "Chưa làm|Đang làm|Bị kẹt" /root/Data/team_alt/cong_viec/nhan_vien
```

## Quy Tắc An Toàn

- Không ghi API key, bot token, mật khẩu, cookie, private key hoặc nội dung `.env` vào dữ liệu công việc.
- Không xóa file/folder công việc nếu chưa có yêu cầu rõ ràng.
- Khi sửa hàng loạt hoặc đổi cấu trúc, backup trước vào `/root/_Backups`.
- Sau thay đổi quan trọng, cập nhật `/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md`.
- Nếu cập nhật workflow/cách lưu dữ liệu, cập nhật lại skill này.
