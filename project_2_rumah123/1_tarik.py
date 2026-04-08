import json
import re
import os
import time
from datetime import datetime
from pathlib import Path
from seleniumbase import Driver
from bs4 import BeautifulSoup

def scrape_rumah123_v57():
    script_dir = Path(__file__).resolve().parent
    output_path = script_dir / 'brankas_data' / 'mentah' / 'properti_mentah.json'
    config_path = script_dir / 'config.json'
    
    with open(config_path, 'r') as f:
        config = json.load(f)
        cities = config.get("cities", [])
        max_pages = config.get("max_pages_per_city", 1)

    print(f"[*] TRUTH-ENGINE V57: JSON Data Extraction (Zero Guessing) Aktif...")
    total_results = []
    seen_ids = set()
    driver = Driver(uc=True, headless=True)

    try:
        for city in cities:
            city_name = city["nama"]
            url_base = f"https://www.rumah123.com/jual/{city['slug']}/rumah/?sort=posted-desc"
            
            for page_num in range(1, max_pages + 1):
                driver.uc_open_with_reconnect(f"{url_base}&page={page_num}", 6)
                time.sleep(7) # Tunggu JSON Load
                
                # AMBIL DATA DARI __NEXT_DATA__ (Ini data asli dari server Rumah123)
                source = driver.page_source
                soup = BeautifulSoup(source, 'html.parser')
                script_tag = soup.find('script', id='__NEXT_DATA__')
                
                if not script_tag:
                    print(f"    [!] Gagal mengambil JSON di Hal {page_num}")
                    continue
                
                try:
                    data_json = json.loads(script_tag.string)
                    # Navigasi ke list properti (struktur Next.js Rumah123)
                    listings = data_json['props']['pageProps']['initialState']['listing']['properties']
                except Exception as e:
                    print(f"    [!] Struktur JSON berubah: {e}")
                    continue

                added = 0
                for item in listings:
                    try:
                        prop_id = item.get('id')
                        if not prop_id or prop_id in seen_ids: continue

                        # DATA BAKU (Tanpa Menebak)
                        # Harga
                        price_val = item.get('price', {}).get('value', 0)
                        if price_val == 0: continue

                        # Spesifikasi Fisik
                        lt = item.get('attributes', {}).get('landSize', 0)
                        lb = item.get('attributes', {}).get('buildingSize', 0)
                        kt = item.get('attributes', {}).get('bedrooms', 0)
                        km = item.get('attributes', {}).get('bathrooms', 0)
                        carport = item.get('attributes', {}).get('carports', 0)
                        
                        # Lokasi Mikro
                        district = item.get('location', {}).get('district', "")
                        city_loc = item.get('location', {}).get('city', "")
                        full_loc = f"{district}, {city_loc}" if district else city_name

                        entry = {
                            "id": str(prop_id),
                            "judul": item.get('title', 'N/A'),
                            "harga": str(price_val),
                            "lokasi": full_loc,
                            "lt": int(lt) if lt else 0,
                            "lb": int(lb) if lb else 0,
                            "kt": int(kt) if kt else 0,
                            "km": int(km) if km else 0,
                            "carport": int(carport) if carport else 0,
                            "url_properti": f"https://www.rumah123.com{item.get('url')}",
                            "waktu_tarik": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
                        
                        total_results.append(entry)
                        seen_ids.add(prop_id)
                        added += 1
                        print(f"    [OK] {price_val/1e9:.1f}M | LT:{entry['lt']:3} CP:{entry['carport']} | {district[:12]:12} | {entry['judul'][:25]}...")

                    except: continue
                
                print(f"--- Selesai Hal {page_num} | Berhasil: {added} ---")
                with open(output_path, 'w') as f: json.dump(total_results, f, indent=4)

    finally:
        driver.quit()
        print(f"\n[*] TOTAL DATA ASLI BERHASIL DITARIK: {len(total_results)}")

if __name__ == "__main__":
    scrape_rumah123_v57()
