#!/usr/bin/env python3
"""
Streamlit App - Tạo tên miền con Cloudflare
Giao diện web để tạo A record trên Cloudflare
"""

import streamlit as st
from cloudflare_dns import CloudflareDNS, DEFAULT_API_KEY, DEFAULT_IP, DEFAULT_RECORD_TYPE
import re

# Cấu hình trang
st.set_page_config(
    page_title="Tạo Tên Miền Con Cloudflare",
    page_icon="🌐",
    layout="centered"
)

st.title("🌐 Tạo Tên Miền Con Cloudflare")
st.markdown("---")

# Sidebar với thông tin mặc định
with st.sidebar:
    st.header("⚙️ Cấu hình mặc định")
    st.info(f"**API Key:** `{DEFAULT_API_KEY[:20]}...`")
    st.info(f"**IP mặc định:** `{DEFAULT_IP}`")
    st.info(f"**Loại record:** `{DEFAULT_RECORD_TYPE}`")
    st.markdown("---")
    st.markdown("### 📝 Hướng dẫn")
    st.markdown("""
    Nhập tên miền con đầy đủ, ví dụ:
    - `vps7.anhlaptrinh.vn`
    - `test.example.com`
    
    Ứng dụng sẽ tự động:
    1. Phân tích tên miền
    2. Tạo A record trên Cloudflare
    3. Sử dụng IP mặc định nếu không nhập
    """)

# Form nhập liệu
st.subheader("📋 Thông tin tên miền")

col1, col2 = st.columns([2, 1])

with col1:
    subdomain = st.text_input(
        "Tên miền con (subdomain)",
        placeholder="vps7.anhlaptrinh.vn",
        help="Nhập tên miền con đầy đủ"
    )

with col2:
    ip_address = st.text_input(
        "Địa chỉ IP",
        value=DEFAULT_IP,
        help=f"IP mặc định: {DEFAULT_IP}"
    )

# Validate IP format
def is_valid_ip(ip):
    pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if not re.match(pattern, ip):
        return False
    parts = ip.split('.')
    return all(0 <= int(part) <= 255 for part in parts)

# Validate subdomain format
def is_valid_subdomain(subdomain):
    pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)+$'
    return re.match(pattern, subdomain) is not None

# Nút tạo record
if st.button("🚀 Tạo A Record", type="primary", use_container_width=True):
    if not subdomain:
        st.error("❌ Vui lòng nhập tên miền con!")
    elif not is_valid_subdomain(subdomain):
        st.error("❌ Định dạng tên miền không hợp lệ!")
    elif not ip_address:
        st.error("❌ Vui lòng nhập địa chỉ IP!")
    elif not is_valid_ip(ip_address):
        st.error("❌ Địa chỉ IP không hợp lệ!")
    else:
        with st.spinner(f"Đang tạo A record cho {subdomain}..."):
            try:
                dns = CloudflareDNS()
                result = dns.create_a_record(subdomain, ip_address)
                
                if result['success']:
                    st.success("✅ Tạo record thành công!")
                    
                    # Hiển thị thông tin record
                    st.markdown("### 📊 Thông tin record đã tạo:")
                    record = result['record']
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Tên miền", record['full_domain'])
                        st.metric("Loại", record['type'])
                    with col2:
                        st.metric("IP Address", record['content'])
                        st.metric("Record ID", record['id'])
                    
                    # Copy button
                    st.code(record['full_domain'], language=None)
                    
                    st.balloons()
                else:
                    st.error(f"❌ Lỗi: {result['error']}")
                    
            except Exception as e:
                st.error(f"❌ Lỗi không mong đợi: {str(e)}")

# Lịch sử tạo record (session state)
if 'history' not in st.session_state:
    st.session_state.history = []

if st.session_state.history:
    st.markdown("---")
    st.subheader("📜 Lịch sử")
    for i, item in enumerate(reversed(st.session_state.history[-5:]), 1):
        with st.expander(f"{i}. {item['subdomain']} - {item['ip']}"):
            st.json(item)

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray;'>"
    "Powered by Cloudflare API | Made with ❤️"
    "</div>",
    unsafe_allow_html=True
)

