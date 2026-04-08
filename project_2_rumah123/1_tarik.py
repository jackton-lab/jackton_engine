import json
import re
import os
import time
from datetime import datetime
from pathlib import Path
from seleniumbase import Driver
from bs4 import BeautifulSoup

def parse_price_smart(price_str):
    if not price_str or "Rp" not in price_str: return 0
    price_str = price_str.replace("Rp", "").strip()
    match = re.search(r"([\d,\.]+)\s*(miliar|juta|jt|m)?", price_str, re.IGNORECASE)
    if not match: return 0
    val_str = match.group(1).replace(".", "").replace(",", ".")
    try:
        val = float(val_str)
        unit = (match.group(2) or "").lower()
        if "miliar" in unit or unit == "m": val *= 1_000_000_000
        elif "juta" in unit or unit == "jt": val *= 1_000_000
        return int(val)
    except: return 0

def extract_specs_v56(card_soup):
    lt = lb = kt = km = 0
    carport = 0
    spec_container = card_soup.find("div", class_=re.compile(r"flex.*gap-x-2.*text-sm"))
    text_full = card_soup.get_text(" ").lower()
    
    # LT/LB/KT/KM extraction
    m_lt = re.search(r"lt\s*:?\s*(\d+)", text_full)
    m_lb = re.search(r"lb\s*:?\s*(\d+)", text_full)
    if m_lt: lt = int(m_lt.group(1))
    if m_lb: lb = int(m_lb.group(1))
    
    # Carport detection (mencari angka di depan kata carport/garasi)
    m_cp = re.search(r"(\d+)\s*(carport|garasi|parkir)", text_full)
    if m_cp: carport = int(m_cp.group(1))
    elif "carport" in text_full or "garasi" in text_full: carport = 1 # Minimal 1 jika ada kata tersebut
        
    # KT/KM Icons
    kt_el = card_soup.find("use", attrs={"xlink:href": re.compile(r"bedroom-icon")})
    if kt_el:
        kt_t = kt_el.find_parent("span").get_text(strip=True)
        km_match = re.search(r"(\d+)", kt_t)
        if km_match: kt = int(km_match.group(1))
    
    km_el = card_soup.find("use", attrs={"xlink:href": re.compile(r"bathroom-icon")})
    if km_el:
        km_t = km_el.find_parent("span").get_text(strip=True)
        km_match = re.search(r"(\d+)", km_t)
        if km_match: km = int(km_match.group(1))
        
    return lt, lb, kt, km, carport

def scrape_rumah123_v56():
    script_dir = Path(__file__).resolve().parent
    output_path = script_dir / 'brankas_data' / 'mentah' / 'properti_mentah.json'
    config_path = script_dir / 'config.json'
    
    with open(config_path, 'r') as f:
        config = json.load(f)
        cities = config.get("cities", [])
        max_pages = config.get("max_pages_per_city", 1)

    print(f"[*] SMART-ENGINE V56: Carport & Access Detection Enabled...")
    total_results = []
    seen_ids = set()
    driver = Driver(uc=True, headless=True)

    try:
        for city in cities:
            city_name = city["nama"]
            url_base = f"https://www.rumah123.com/jual/{city['slug']}/rumah/?sort=posted-desc"
            
            for page_num in range(1, max_pages + 1):
                driver.uc_open_with_reconnect(f"{url_base}&page={page_num}", 6)
                time.sleep(5)
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                cards = soup.find_all("div", attrs={"data-name": "ldp-listing-card"})
                
                added = 0
                for card in cards:
                    try:
                        link_el = card.find("a", href=re.compile(r"hos\d+"))
                        if not link_el: continue
                        url_prop = link_el['href']
                        id_match = re.search(r"-(hos\d+)/?$", url_prop)
                        prop_id = id_match.group(1) if id_match else url_prop
                        if prop_id in seen_ids: continue

                        price_el = card.find("span", attrs={"data-testid": "ldp-text-price"})
                        price_val = parse_price_smart(price_el.get_text(strip=True)) if price_el else 0
                        if price_val == 0: continue

                        lt, lb, kt, km, carport = extract_specs_v56(card)
                        judul = card.find("h2").get_text(strip=True) if card.find("h2") else ""
                        
                        # Lokasi Mikro (mencari kelurahan/kecamatan di teks)
                        lokasi_el = card.find("p", class_=re.compile(r"text-greyText"))
                        lokasi_mikro = lokasi_el.get_text(strip=True) if lokasi_el else city_name

                        entry = {
                            "id": prop_id, "judul": judul, "harga": str(price_val),
                            "lokasi": lokasi_mikro, "lt": lt, "lb": lb, "kt": kt, "km": km,
                            "carport": carport, "url_properti": url_prop,
                            "waktu_tarik": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
                        total_results.append(entry)
                        seen_ids.add(prop_id)
                        added += 1
                        print(f"    [OK] {price_val/1e9:.1f}M | LT:{lt:3} CP:{carport} | {lokasi_mikro[:15]} | {judul[:20]}...")

                    except: continue
                
                with open(output_path, 'w') as f: json.dump(total_results, f, indent=4)

    finally:
        driver.quit()
        print(f"\n[*] TOTAL BERHASIL DITARIK: {len(total_results)}")

if __name__ == "__main__":
    scrape_rumah123_v56()
