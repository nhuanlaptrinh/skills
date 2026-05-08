#!/usr/bin/env python3
"""
Cloudflare DNS Record Creator
Tự động tạo A record cho tên miền con trên Cloudflare
"""

import requests
import sys
import re
from typing import Optional, Tuple

# Cấu hình mặc định
DEFAULT_API_KEY = "JWqJlR2cFxzDt6U0_hhGeEn6kpNepgk6cwVKWHv8"
DEFAULT_IP = "194.59.165.104"
DEFAULT_RECORD_TYPE = "A"
CLOUDFLARE_API_URL = "https://api.cloudflare.com/client/v4"

class CloudflareDNS:
    def __init__(self, api_key: str = DEFAULT_API_KEY):
        """Khởi tạo kết nối với Cloudflare API"""
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def parse_subdomain(self, subdomain: str) -> Tuple[str, str]:
        """
        Phân tích subdomain để lấy tên và domain
        Ví dụ: vps7.anhlaptrinh.vn -> (vps7, anhlaptrinh.vn)
        """
        parts = subdomain.split('.')
        if len(parts) < 2:
            raise ValueError(f"Subdomain không hợp lệ: {subdomain}")
        
        name = parts[0]
        domain = '.'.join(parts[1:])
        return name, domain
    
    def get_zone_id(self, domain: str) -> Optional[str]:
        """Lấy Zone ID của domain từ Cloudflare"""
        try:
            url = f"{CLOUDFLARE_API_URL}/zones"
            params = {"name": domain}
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and data.get("result") and len(data["result"]) > 0:
                    return data["result"][0]["id"]
            return None
        except Exception as e:
            print(f"Lỗi khi lấy Zone ID: {e}")
            return None
    
    def check_existing_record(self, zone_id: str, subdomain: str, record_type: str) -> bool:
        """Kiểm tra xem record đã tồn tại chưa"""
        try:
            url = f"{CLOUDFLARE_API_URL}/zones/{zone_id}/dns_records"
            params = {"name": subdomain, "type": record_type}
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and data.get("result") and len(data["result"]) > 0:
                    return True
            return False
        except:
            return False
    
    def create_a_record(self, subdomain: str, ip: str = DEFAULT_IP, 
                       record_type: str = DEFAULT_RECORD_TYPE) -> dict:
        """
        Tạo A record trên Cloudflare
        
        Args:
            subdomain: Tên miền con (ví dụ: vps7.anhlaptrinh.vn)
            ip: Địa chỉ IP (mặc định: 194.59.165.104)
            record_type: Loại record (mặc định: A)
        
        Returns:
            dict: Thông tin record đã tạo hoặc lỗi
        """
        try:
            # Phân tích subdomain
            name, domain = self.parse_subdomain(subdomain)
            
            # Lấy Zone ID
            zone_id = self.get_zone_id(domain)
            if not zone_id:
                return {
                    'success': False,
                    'error': f'Không tìm thấy domain {domain} trong Cloudflare. Vui lòng kiểm tra domain đã được thêm vào Cloudflare chưa.'
                }
            
            # Kiểm tra record đã tồn tại chưa
            if self.check_existing_record(zone_id, subdomain, record_type):
                return {
                    'success': False,
                    'error': f'Record {subdomain} đã tồn tại trong Cloudflare'
                }
            
            # Tạo record mới
            url = f"{CLOUDFLARE_API_URL}/zones/{zone_id}/dns_records"
            data = {
                "type": record_type,
                "name": name,
                "content": ip,
                "ttl": 1  # Auto TTL
            }
            
            response = requests.post(url, headers=self.headers, json=data)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    record_data = result["result"]
                    # Cloudflare trả về name có thể là subdomain hoặc FQDN
                    record_name = record_data['name']
                    # Nếu name không kết thúc bằng domain, thêm domain vào
                    if not record_name.endswith(domain):
                        full_domain = f"{record_name}.{domain}" if record_name != domain else domain
                    else:
                        full_domain = record_name
                    
                    return {
                        'success': True,
                        'record': {
                            'id': record_data['id'],
                            'name': record_data['name'],
                            'type': record_data['type'],
                            'content': record_data['content'],
                            'full_domain': full_domain,
                            'zone_id': zone_id
                        }
                    }
                else:
                    errors = result.get("errors", [])
                    error_msg = errors[0].get("message", "Lỗi không xác định") if errors else "Lỗi không xác định"
                    return {
                        'success': False,
                        'error': f'Lỗi Cloudflare API: {error_msg}'
                    }
            else:
                error_data = response.json() if response.text else {}
                errors = error_data.get("errors", [])
                error_msg = errors[0].get("message", f"HTTP {response.status_code}") if errors else f"HTTP {response.status_code}"
                return {
                    'success': False,
                    'error': f'Lỗi Cloudflare API: {error_msg}'
                }
            
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'Lỗi kết nối: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Lỗi: {str(e)}'
            }

def main():
    """Hàm main cho CLI"""
    if len(sys.argv) < 2:
        print("Cách sử dụng: python cloudflare_dns.py <subdomain> [ip]")
        print("Ví dụ: python cloudflare_dns.py vps7.anhlaptrinh.vn")
        print("Ví dụ: python cloudflare_dns.py vps7.anhlaptrinh.vn 194.59.165.104")
        sys.exit(1)
    
    subdomain = sys.argv[1]
    ip = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_IP
    
    print(f"Đang tạo A record cho {subdomain} với IP {ip}...")
    
    dns = CloudflareDNS()
    result = dns.create_a_record(subdomain, ip)
    
    if result['success']:
        print(f"✓ Thành công! Đã tạo record:")
        print(f"  - Tên miền: {result['record']['full_domain']}")
        print(f"  - Loại: {result['record']['type']}")
        print(f"  - IP: {result['record']['content']}")
        print(f"  - ID: {result['record']['id']}")
    else:
        print(f"✗ Lỗi: {result['error']}")
        sys.exit(1)

if __name__ == "__main__":
    main()
