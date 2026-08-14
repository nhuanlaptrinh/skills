---
name: ai-website-template-engine
description: Quản lý và sinh mẫu giao diện website đa dạng HTML5, Vanilla CSS3, Glassmorphism, Cyberpunk, Luxury, Clean Minimalist cho hệ thống AI Website Telegram. Dùng khi người dùng muốn thêm mẫu web mới, tùy biến theme hoặc điều chỉnh slug subdomain tên miền.
---

# Skill: Trình Sinh Mẫu Giao Diện Website Đa Dạng (HTML5 & CSS3)

## 🎯 Mục đích & Phạm vi
Skill này cung cấp các bộ mẫu giao diện phong phú và cơ chế tự động sinh subdomain tên miền đẹp cho hệ thống AI Website Telegram tại `/root/Apps/ai_website_telegram/hosting_manager.py`.

---

## 🎨 Danh sách 5 Phong cách Giao diện (Design Themes)

| Theme | Phong cách chủ đạo | Phông chữ | Phù hợp cho ngành |
| :--- | :--- | :--- | :--- |
| **Dark Glassmorphism** | Indigo & Pink Glow, Kính mờ, 3D cards | `Plus Jakarta Sans` | Bán hàng E-Commerce, Thời trang |
| **Cyber Neon Tech** | Cyan & Violet Cyberpunk, Đếm chỉ số | `Outfit` / `Roboto` | Công nghệ, AI, Phần mềm SaaS |
| **Golden Luxury** | Vàng kim & Amber sang trọng, Serif | `Playfair Display` | Bất động sản, Trang sức, Spa, VIP |
| **Fresh Minimal Light** | Trắng ngà & Xanh ngọc tươi sáng | `Montserrat` | Ẩm thực, Nhà hàng, Mỹ phẩm clean |
| **Creative Portfolio** | Mesh Gradient rực rỡ, Grid dự án | `Poppins` | Studio, Chụp ảnh, Cá nhân, Agency |

---

## ⚡ Quy Định Bắt Buộc Mọi Giao Diện (Mandatory Rules)

1. **MANDATORY SMOOTH SCROLLING**:
   - Tất cả mã CSS phải khai báo: `html, body { scroll-behavior: smooth !important; }`.
   - Tất cả liên kết neo `a[href^="#"]` và nút Scroll-To-Top phải được gắn sự kiện cuộn mượt bằng JavaScript `scrollIntoView({ behavior: 'smooth' })`.
2. **ACTIVE HOME MENU STATE**: Menu "Trang Chủ" có `class="active"` nổi bật mặc định và tự động thay đổi theo vị trí cuộn.
3. **FLOATING SCROLL-TO-TOP BUTTON**: Nút cuộn tròn cố định ở góc phải màn hình, tự động xuất hiện khi cuộn xuống quá 280px.
4. **MANDATORY AUTHENTICATION MODAL & GMAIL OTP REGISTRATION SYSTEM**:
   - Header navigation có nút "Đăng Nhập" (gọi `openAuthModal('login')`).
   - Pop-up Glassmorphism Modal `<div id="authModal" class="modal">` hỗ trợ 2 Tab: **Đăng Nhập** & **Tạo Tài Khoản**.
   - Nhập Email Gmail khi Đăng Ký sẽ gửi mã OTP 6 chữ số xác thực qua Gmail SMTP App Password (`kebanhay2011@gmail.com`).
   - Trạng thái đã đăng nhập (User Session State): Hiển thị Avatar & Tên (`Xin chào, Quốc Đạt!`) + Dropdown menu (Thông tin cá nhân, Lịch sử đơn hàng, Đăng xuất).

---


## 🛠️ Quy trình Sinh Tên Miền Subdomain Đẹp (Pretty Slugs)

Hệ thống tự động chuyển đổi yêu cầu ngôn ngữ tự nhiên của khách thành subdomain đẹp:
- *Yêu cầu:* `"Tạo website shop thời trang nam"`
- *Slug tự động:* `shopthoitrangnam`
- *Domain chính:* `shopthoitrangnam.devoverflow.xyz`
- *Routing:* Nginx + Traefik tự động chuyển tiếp cổng 80/443 không cần gõ cổng `:8088`.

---

## 💻 Cách gọi sinh mã nguồn qua Token Codex LLM

```python
from hosting_manager import HostingManager

# Sinh mã nguồn HTML5/CSS3 lộng lẫy bằng GPT-5.6-sol
html = HostingManager.generate_rich_html_css(
    specification="Tạo website shop giày thể thao sneaker",
    website_id="WEB-001",
    domain="giaythethao.devoverflow.xyz"
)

# Deploy trực tiếp lên hosting khách
HostingManager.deploy_website_code("HOST-001", "REV-00001", html)
HostingManager.link_domain_to_site("giaythethao.devoverflow.xyz", "HOST-001")
```
