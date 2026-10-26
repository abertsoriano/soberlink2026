"""SoberLink kiosk scanner.

Scans a patron's QR code with the camera and asks the API for their current
risk band.

The kiosk never connects to the database. It has no database password and no
database driver, so a kiosk stolen from a venue gives an attacker nothing
beyond a device that can call a public API, which anyone could do anyway.
Everything it needs comes back over HTTPS from the API.
"""
import os
import sys
import webbrowser
from urllib.parse import urlparse, parse_qs

import cv2
import requests

# The deployed API. Override on the Pi with:
#   export SOBERLINK_API_BASE="https://your-app.azurewebsites.net"
API_BASE = os.environ.get(
    "SOBERLINK_API_BASE",
    "https://soberlink-api-timriddell4-cse7d6cwegdyh4fw.australiaeast-01.azurewebsites.net",
).rstrip("/")

# Set to 0 to stay on the command line instead of opening the staff dashboard.
OPEN_DASHBOARD = os.environ.get("SOBERLINK_OPEN_DASHBOARD", "1") == "1"

REQUEST_TIMEOUT = 10


def extract_token(data: str) -> str:
    """Pulls the token out of whatever the QR code contained.

    Handles a bare token, a #token=... fragment, a ?token=... query, and the
    old style where the token was the last part of the path.
    """
    data = data.strip()
    if "://" not in data and "/" not in data and "?" not in data and "#" not in data:
        return data

    parsed = urlparse(data)

    fragment = parse_qs(parsed.fragment)
    if fragment.get("token"):
        return fragment["token"][0]

    query = parse_qs(parsed.query)
    if query.get("token"):
        return query["token"][0]

    return parsed.path.rstrip("/").rsplit("/", 1)[-1]


def fetch_risk(token: str):
    """Asks the API for this session's risk. Returns None if it isn't valid."""
    try:
        resp = requests.get(
            f"{API_BASE}/sessions/risk",
            headers={"Authorization": f"Bearer {token}"},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        print(f"ERROR: could not reach the API at {API_BASE} ({exc})")
        return None

    if resp.status_code == 404:
        print("No matching session. The code has expired or was never valid.")
        return None
    if resp.status_code == 401:
        print("The API rejected that token.")
        return None
    if not resp.ok:
        print(f"ERROR: API returned HTTP {resp.status_code}: {resp.text[:200]}")
        return None

    return resp.json()


def show_risk(risk: dict) -> None:
    print()
    print(f"  RISK LEVEL:        {risk['risk_level']}  (score {risk['risk_score']})")
    print(f"  Standard drinks 3h: {risk['standard_drinks_3h']}")
    print(f"  Venues visited:     {risk['unique_venues_visited']}")
    if risk.get("previous_refusal"):
        print("  Previously refused service this session")
    if risk.get("staff_concern"):
        print("  Staff concern recorded this session")
    print()
    print(f"  {risk['disclaimer']}")
    print()


def scan_once() -> None:
    detector = cv2.QRCodeDetector()
    cam = cv2.VideoCapture(0)
    if not cam.isOpened():
        print("ERROR: could not open the camera.")
        return

    print(f"Camera ready. API: {API_BASE}")
    print("Point a patron's QR code at the camera. Press 'q' to quit.")
    frame_count = 0

    try:
        while True:
            ok, frame = cam.read()
            if not ok:
                print("ERROR: failed to read a frame from the camera.")
                break

            frame_count += 1
            if frame_count % 60 == 0:
                print("Still scanning...")

            data, _points, _straight = detector.detectAndDecode(frame)
            if data:
                token = extract_token(data)
                print("QR scanned.")

                risk = fetch_risk(token)
                if risk:
                    show_risk(risk)
                    if OPEN_DASHBOARD:
                        # Token goes in the fragment, which browsers never send
                        # to the server, so it stays out of the Azure logs.
                        url = f"{API_BASE}/dashboard.html#token={token}"
                        print("Opening the staff dashboard...")
                        webbrowser.open(url)
                break

            cv2.imshow("SoberLink: scan QR", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                print("Stopped.")
                break
    finally:
        cam.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    scan_once()
