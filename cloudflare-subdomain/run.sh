#!/bin/bash
# Script chạy ứng dụng Streamlit

cd /root/.agents/skills/cloudflare-subdomain
streamlit run app.py --server.port 8501 --server.address 0.0.0.0

