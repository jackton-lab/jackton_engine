import json
import re
import os
import time
from datetime import datetime
from pathlib import Path
from seleniumbase import Driver

def scrape_rumah123_v57_stable():
    script_dir = Path(__file__).resolve().parent
    output_path = script_dir / 'brankas_data' / 'mentah' / 'properti_mentah.json'
    config_path = script_dir / 'config.json'
    
    with open(config_path, 'r') as f:
        config = json.load(f)
        cities = config.get("cities", [])
        max_pages = config.get("max_pages_per_city", 1)

    print(f"[*] TRUTH-ENGINE V57 (STABLE): Memory JSON Extraction Aktif...")
    total_results = []
    seen_ids = set()
    driver = Driver(uc=True, headless=True)

    try:
        for city in cities:
            city_name = city["nama"]
            url_base = f"https://www.rumah123.com/jual/{city['slug']}/rumah/?sort=posted-desc"
            
            for page_num in range(1, max_pages + 1):
                page_url = f"{url_base}&page={page_num}"
                print(f"\n>>> {city_name} | HAL {page_num}")
                
                driver.uc_open_with_reconnect(page_url, 6)
                time.sleep(8) # Waktu untuk inisialisasi window.__NEXT_DATA__
                
                # AMBIL LANGSUNG DARI MEMORY BROWSER
                try:
                    data_json = driver.execute_script("return window.__NEXT_DATA__")
                    if not data_json:
                        print("    [!] window.__NEXT_DATA__ tidak ditemukan di memori.")
                        continue
                    
                    # Path baru untuk App Router/Pages Router di Rumah123
                    listings = None
                    # Coba beberapa kemungkinan path JSON
                    try:
                        listings = data_json['props']['pageProps']['initialState']['listing']['properties']
                    except:
                        try:
                            listings = data_json['props']['pageProps']['searchResult']['properties']
                        except:
                            print("    [!] Gagal menemukan path listing di JSON.")
                            continue
                    
                    if not listings: continue

                    added = 0
                    for item in listings:
                        prop_id = str(item.get('id'))
                        if not prop_id or prop_id in seen_ids: continue

                        attrs = item.get('attributes', {})
                        price_val = item.get('price', {}).get('value', 0)
                        if price_val == 0: continue

                        # DATA BAKU (Carport, LT, LB, dll)
                        entry = {
                            "id": prop_id,
                            "judul": item.get('title', 'N/A'),
                            "harga": str(price_val),
                            "lokasi": f"{item.get('location', {}).get('district', '')}, {city_name}",
                            "lt": int(attrs.get('landSize', 0)) if attrs.get('landSize') else 0,
                            "lb": int(attrs.get('buildingSize', 0)) if attrs.get('buildingSize') else 0,
                            "kt": int(attrs.get('bedrooms', 0)) if attrs.get('bedrooms') else 0,
                            "km": int(attrs.get('bathrooms', 0)) if attrs.get('bathrooms') else 0,
                            "carport": int(attrs.get('carports', 0)) if attrs.get('carports') else 0,
                            "url_properti": f"https://www.rumah123.com{item.get('url')}",
                            "waktu_tarik": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
                        
                        total_results.append(entry)
                        seen_ids.add(prop_id)
                        added += 1
                        print(f"    [OK] {price_val/1e9:.1f}M | LT:{entry['lt']:3} CP:{entry['carport']} | {entry['judul'][:35]}...")

                    print(f"--- Selesai Hal {page_num} | Berhasil: {added} ---")
                    with open(output_path, 'w') as f: json.dump(total_results, f, indent=4)
                    
                except Exception as e:
                    print(f"    [!] Error saat ambil JSON: {e}")

    finally:
        driver.quit()
        print(f"\n[*] TOTAL DATA ASLI BERHASIL DITARIK: {len(total_results)}")

if __name__ == "__main__":
    scrape_rumah123_v57_stable()
