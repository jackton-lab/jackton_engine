from seleniumbase import Driver
import time
import json

def find_selectors():
    print("[*] Mencari Selector dengan Driver Visual...")
    driver = Driver(uc=True, headless=True)
    try:
        url = "https://www.rumah123.com/jual/jakarta-selatan/rumah/?sort=posted-desc"
        driver.uc_open_with_reconnect(url, 5)
        time.sleep(10) # Tunggu render sempurna
        
        # Cari elemen yang mengandung harga 'Rp'
        print("[*] Mencari elemen harga...")
        price_elements = driver.find_elements("xpath", "//*[contains(text(), 'Rp')]")
        for i, el in enumerate(price_elements[:5]):
            print(f"Price {i}: Text='{el.text}' | Tag='{el.tag_name}' | Class='{el.get_attribute('class')}'")
            
        # Cari elemen judul (biasanya h2 atau h3)
        print("\n[*] Mencari elemen judul...")
        titles = driver.find_elements("xpath", "//h2 | //h3")
        for i, el in enumerate(titles[:5]):
            print(f"Title {i}: Text='{el.text}' | Class='{el.get_attribute('class')}'")

        # Cari kontainer kartu
        print("\n[*] Mencari kontainer kartu...")
        # Coba beberapa pola umum
        containers = driver.find_elements("css selector", "div[class*='card'], div[class*='listing'], div[class*='item']")
        for i, el in enumerate(containers[:5]):
            print(f"Container {i}: Class='{el.get_attribute('class')}'")

    finally:
        driver.quit()

if __name__ == "__main__":
    find_selectors()
