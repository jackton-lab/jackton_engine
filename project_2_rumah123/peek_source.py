from seleniumbase import Driver
import time
from bs4 import BeautifulSoup

def peek_source():
    print("[*] Mengintip Source Code...")
    driver = Driver(uc=True, headless=True)
    try:
        url = "https://www.rumah123.com/jual/jakarta-selatan/rumah/?sort=posted-desc"
        driver.uc_open_with_reconnect(url, 5)
        time.sleep(5)
        source = driver.page_source
        
        # Cari __NEXT_DATA__
        if "__NEXT_DATA__" in source:
            print("[OK] Menemukan __NEXT_DATA__ di source!")
            start = source.find("__NEXT_DATA__")
            print(f"Context around __NEXT_DATA__: {source[start-20:start+200]}")
        else:
            print("[!] __NEXT_DATA__ TIDAK DITEMUKAN di source.")
            # Cari script tags lainnya
            soup = BeautifulSoup(source, 'html.parser')
            scripts = soup.find_all('script')
            print(f"Jumlah script tags: {len(scripts)}")
            for s in scripts:
                if s.get('id'):
                    print(f"Script ID: {s.get('id')}")
                content = s.string if s.string else ""
                if len(content) > 1000:
                    print(f"Script besar ditemukan (len={len(content)}), cuplikan: {content[:100]}...")

    finally:
        driver.quit()

if __name__ == "__main__":
    peek_source()
