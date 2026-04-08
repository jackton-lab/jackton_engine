import json
import re
import os
import time
from datetime import datetime
from pathlib import Path
from seleniumbase import Driver
from bs4 import BeautifulSoup

def extract_json_from_html(html):
    """Mengekstrak data JSON listing dari script tag Rumah123."""
    # Cari semua script tag
    soup = BeautifulSoup(html, 'html.parser')
    scripts = soup.find_all('script')
    
    for s in scripts:
        content = s.string if s.string else ""
        if 'props' in content and 'initialState' in content and 'listing' in content:
            try:
                # Bersihkan jika ada penugasan variabel (misal window.__DATA__ = {...})
                json_str = re.search(r'({.*})', content).group(1)
                return json.loads(json_str)
            except: continue
    return None

def scrape_rumah123_v57_final():
    script_dir = Path(__file__).resolve().parent
    output_path = script_dir / 'brankas_data' / 'mentah' / 'properti_mentah.json'
    config_path = script_dir / 'config.json'
    
    with open(config_path, 'r') as f:
        config = json.load(f)
        cities = config.get("cities", [])
        max_pages = config.get("max_pages_per_city", 1)

    print(f"[*] TRUTH-ENGINE V57 (FINAL): Deep Script Extraction Aktif...")
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
                time.sleep(8)
                
                # SIKAT DARI HTML SCRIPTS
                data_json = extract_json_from_html(driver.page_source)
                
                listings = []
                if data_json:
                    try:
                        # Jalur 1: initialState
                        listings = data_json['props']['pageProps']['initialState']['listing']['properties']
                    except:
                        try:
                            # Jalur 2: searchResult
                            listings = data_json['props']['pageProps']['searchResult']['properties']
                        except: pass
                
                # FALLBACK: Jika JSON gagal, gunakan CSS Selector Presisi (V48)
                if not listings:
                    print("    [!] JSON gagal, menggunakan Fallback Precision Selectors...")
                    soup = BeautifulSoup(driver.page_source, 'html.parser')
                    cards = soup.find_all("div", attrs={"data-name": "ldp-listing-card"})
                    
                    added = 0
                    for card in cards:
                        try:
                            link_el = card.find("a", href=re.compile(r"hos\d+"))
                            if not link_el: continue
                            url_prop = f"https://www.rumah123.com{link_el['href']}" if link_el['href'].startswith("/") else link_el['href']
                            
                            id_match = re.search(r"-(hos\d+)/?$", url_prop)
                            prop_id = id_match.group(1) if id_match else url_prop
                            if prop_id in seen_ids: continue

                            # Harga (Selector Asli)
                            price_el = card.find("span", attrs={"data-testid": "ldp-text-price"})
                            price_raw = price_el.get_text(strip=True) if price_el else ""
                            
                            # Spesifikasi (Selector Asli)
                            # Carport di Rumah123 SRP biasanya ada di dalam tag 'use' car-icon
                            carport = 0
                            cp_el = card.find("use", attrs={"xlink:href": re.compile(r"car-icon|garage-icon")})
                            if cp_el:
                                cp_text = cp_el.find_parent("span").get_text(strip=True)
                                cp_m = re.search(r"(\d+)", cp_text)
                                if cp_m: carport = int(cp_m.group(1))

                            entry = {
                                "id": prop_id,
                                "judul": card.find("h2").get_text(strip=True) if card.find("h2") else "N/A",
                                "harga": str(re.sub(r"\D", "", price_raw)) if "jt" not in price_raw.lower() else "0", # Handle simple
                                "url_properti": url_prop,
                                "carport": carport,
                                "waktu_tarik": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            }
                            # ... (sisanya menggunakan fungsi ekstraksi yang sudah teruji)
                            total_results.append(entry)
                            seen_ids.add(prop_id)
                            added += 1
                        except: continue
                else:
                    # PROSES DARI JSON (DATA TERBAIK)
                    added = 0
                    for item in listings:
                        prop_id = str(item.get('id'))
                        if prop_id in seen_ids: continue
                        
                        attrs = item.get('attributes', {})
                        entry = {
                            "id": prop_id,
                            "judul": item.get('title', 'N/A'),
                            "harga": str(item.get('price', {}).get('value', 0)),
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
                        print(f"    [OK-JSON] {int(entry['harga'])/1e9:.1f}M | CP:{entry['carport']} | {entry['judul'][:30]}...")

                print(f"--- Selesai Hal {page_num} | Berhasil: {added} ---")
                with open(output_path, 'w') as f: json.dump(total_results, f, indent=4)

    finally:
        driver.quit()
        print(f"\n[*] SELESAI. Total unik: {len(total_results)}")

if __name__ == "__main__":
    scrape_rumah123_v57_final()
