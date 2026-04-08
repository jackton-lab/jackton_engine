import json
from curl_cffi import requests
from bs4 import BeautifulSoup
from seleniumbase import Driver
import time

def debug_structure():
    print("[*] DEBUG: Menyelidiki Struktur HTML Rumah123...")
    driver = Driver(uc=True, headless=True)
    try:
        url = "https://www.rumah123.com/jual/jakarta-selatan/rumah/?sort=posted-desc"
        driver.uc_open_with_reconnect(url, 5)
        
        cookies = driver.get_cookies()
        cookie_dict = {c['name']: c['value'] for c in cookies}
        ua = driver.execute_script("return navigator.userAgent")
        
        resp = requests.get(url, impersonate="chrome110", cookies=cookie_dict, headers={"User-Agent": ua})
        print(f"[DEBUG] Status Code: {resp.status_code}")
        print(f"[DEBUG] HTML Length: {len(resp.text)}")
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Cek apakah ada JSON __NEXT_DATA__
        next_data = soup.find('script', id='__NEXT_DATA__')
        if next_data:
            print("[DEBUG] Menemukan __NEXT_DATA__! Ukuran JSON:", len(next_data.string))
            with open('debug_next_data.json', 'w') as f:
                f.write(next_data.string)
        else:
            print("[DEBUG] Tidak menemukan __NEXT_DATA__. Mencoba mencari elemen kartu manual...")
            # Cari semua div untuk melihat pola class
            divs = soup.find_all('div', limit=50)
            with open('debug_divs.txt', 'w') as f:
                for d in divs:
                    f.write(f"Class: {d.get('class')} | ID: {d.get('id')}\n")

    finally:
        driver.quit()

if __name__ == "__main__":
    debug_structure()
