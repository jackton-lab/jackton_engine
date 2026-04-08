from seleniumbase import Driver
import time
from bs4 import BeautifulSoup
import re

def capture_card():
    driver = Driver(uc=True, headless=True)
    try:
        url = "https://www.rumah123.com/jual/jakarta-selatan/rumah/?sort=posted-desc"
        driver.uc_open_with_reconnect(url, 5)
        time.sleep(10)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Cari anchor properti
        anchors = soup.find_all('a', href=re.compile(r"hos\d+"))
        if anchors:
            a = anchors[0]
            # Go up to find something that looks like a card
            current = a
            for i in range(12):
                current = current.parent
                if not current: break
                # Biasanya kartu punya class yang mengandung 'card' atau 'listing'
                classes = current.get('class', [])
                if any('card' in str(c).lower() or 'item' in str(c).lower() for c in classes):
                    print(f"[OK] Menemukan kemungkinan kartu di level {i}")
                    with open('debug_single_card.html', 'w') as f:
                        f.write(current.prettify())
                    break
        else:
            print("[!] Tidak menemukan anchor properti.")

    finally:
        driver.quit()

if __name__ == "__main__":
    capture_card()
