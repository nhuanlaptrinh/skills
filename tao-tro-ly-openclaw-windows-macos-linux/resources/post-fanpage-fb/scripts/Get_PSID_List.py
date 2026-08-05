import os
import requests
from dotenv import load_dotenv

from facebook_graph import graph_url, resolve_page_id, response_error

load_dotenv()

MESSENGER_TOKEN = (
    os.getenv("MESSENGER_TOKEN")
    or os.getenv("MESSENGER_PAGE_ACCESS_TOKEN")
    or os.getenv("FB_PAGE_ACCESS_TOKEN")
    or ""
).strip()

def get_recent_psids():
    if not MESSENGER_TOKEN:
        print("❌ Lỗi: Bạn chưa cấu hình MESSENGER_TOKEN trong file .env")
        return

    try:
        page_id = resolve_page_id(MESSENGER_TOKEN)
    except Exception as error:
        print(f"❌ {error}")
        return

    print("Đang quét danh sách khách hàng đã nhắn tin cho Fanpage...\n")
    url = graph_url("me/conversations")
    params = {
        "fields": "participants",
        "access_token": MESSENGER_TOKEN,
        "limit": 50  # Lấy 50 cuộc hội thoại gần nhất
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        data = response.json()

        if not response.ok:
            print(f"❌ Lỗi Graph API: {response_error(response)}")
            return

        conversations = data.get("data", [])
        if not conversations:
            print("Không tìm thấy cuộc hội thoại nào.")
            return

        print(f"{'TÊN KHÁCH HÀNG':<30} | {'MÃ PSID (Copy vào Google Sheet)'}")
        print("-" * 65)

        for conv in conversations:
            participants = conv.get("participants", {}).get("data", [])
            # Lọc ra participant không phải là Fanpage (thường Fanpage không có email/name rõ ràng như user hoặc có ID trùng với Page ID)
            # Tuy nhiên đơn giản nhất là in ra hết tên
            for p in participants:
                name = p.get("name", "Unknown")
                psid = p.get("id", "")
                if str(psid) == page_id:
                    continue
                print(f"{name:<30} | {psid}")
                
        print("-" * 65)
        print("Đã tự loại trừ ID của chính Fanpage.")
        
    except Exception as e:
        print(f"❌ Lỗi kết nối: {e}")

if __name__ == "__main__":
    get_recent_psids()
