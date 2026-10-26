import sys
import qrcode

# Usage: python make_venue_qr.py http://192.168.1.50:8000
BASE_URL = (sys.argv[1] if len(sys.argv) > 1
            else "https://soberlink-api-timriddell4-cse7d6cwegdyh4fw.australiaeast-01.azurewebsites.net").rstrip("/")

for venue in ["VEN-001", "VEN-002", "VEN-003"]:
    url = f"{BASE_URL}/checkin.html?venue={venue}"
    qrcode.make(url).save(f"venue_qr_{venue}.png")
    print(f"{venue}: {url}")