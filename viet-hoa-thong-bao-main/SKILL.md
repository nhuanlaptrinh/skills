---
name: viet-hoa-thong-bao
description: Chuyển thông báo, ghi chú, lỗi hệ thống, email ngắn, tin nhắn nội bộ hoặc nội dung thô sang tiếng Việt rõ ràng, thân thiện, dễ hiểu. Use when the user asks to "viết lại thông báo", "Việt hóa", "làm cho dễ hiểu", "chuyển lỗi này thành lời nhắn cho người dùng", or wants a reusable demo skill for project-level and global skill usage.
---

# Việt Hóa Thông Báo

## Overview

Biến nội dung thô thành một thông báo tiếng Việt ngắn gọn, lịch sự và dễ hành động. Đây là skill demo tối giản để giảng cách tái sử dụng skill trong một dự án hoặc dùng global cho mọi dự án.

## Workflow

1. Xác định người nhận thông báo: khách hàng, học viên, nhân viên nội bộ, người dùng phần mềm, hoặc đội kỹ thuật.
2. Viết lại nội dung theo giọng rõ ràng, thân thiện, không đổ lỗi, không dùng thuật ngữ khó nếu không cần.
3. Nếu nội dung là lỗi kỹ thuật, thêm hành động tiếp theo mà người nhận có thể làm.

## Output Style

- Ưu tiên 1 đến 3 câu.
- Dùng tiếng Việt tự nhiên, có dấu.
- Tránh câu quá dài.
- Tránh các từ nặng như "bắt buộc", "sai", "lỗi của bạn" nếu có thể thay bằng cách nói mềm hơn.
- Giữ lại thông tin quan trọng như thời gian, tên tính năng, mã lỗi, đường dẫn, số tiền hoặc hạn chót.

## Examples

Input:

```text
Payment failed. Try again later.
```

Output:

```text
Thanh toán chưa hoàn tất. Anh/chị vui lòng thử lại sau ít phút.
```

Input:

```text
User not found in database.
```

Output:

```text
Không tìm thấy tài khoản phù hợp trong hệ thống. Vui lòng kiểm tra lại thông tin đăng nhập hoặc liên hệ bộ phận hỗ trợ.
```

## Demo Teaching Notes

Giải thích cho học viên:

- Project skill: đặt skill trong `.agents/skills/viet-hoa-thong-bao/` của dự án hiện tại để chỉ dự án này dùng.
- Global skill: copy thư mục `viet-hoa-thong-bao` vào `C:\Users\nhuan\.codex\skills\` để Codex có thể dùng trong mọi dự án.
- Điểm khác nhau nằm ở vị trí đặt skill: project thì đi theo từng thư mục dự án, global thì nằm trong thư mục người dùng.
- Khi skill được kích hoạt, Codex đọc `description` trước, sau đó mới đọc hướng dẫn chi tiết trong `SKILL.md`.

Prompt demo:

```text
Dùng skill viet-hoa-thong-bao để viết lại câu này cho học viên dễ hiểu: Class cancelled due to instructor unavailable.
```
