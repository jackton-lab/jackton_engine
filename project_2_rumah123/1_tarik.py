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

def extract_specs_smart(card_soup):
    lt = lb = kt = km = 0
    spec_container = card_soup.find("div", class_=re.compile(r"flex.*gap-x-2.*text-sm"))
    text_content = spec_container.get_text(" ").replace("\n", " ") if spec_container else card_soup.get_text(" ")
    
    m_lt = re.search(r"LT\s*:?\s*(\d+)", text_content)
    m_lb = re.search(r"LB\s*:?\s*(\d+)", text_content)
    if m_lt: lt = int(m_lt.group(1))
    if m_lb: lb = int(m_lb.group(1))
    
    kt_el = card_soup.find("use", attrs={"xlink:href": re.compile(r"bedroom-icon")})
    if kt_el:
        kt_text = kt_el.find_parent("span").get_text(strip=True)
        kt_match = re.search(r"(\d+)", kt_text)
        if kt_match: kt = int(kt_match.group(1))
    
    km_el = card_soup.find("use", attrs={"xlink:href": re.compile(r"bathroom-icon")})
    if km_el:
        km_text = km_el.find_parent("span").get_text(strip=True)
        km_match = re.search(r"(\d+)", km_text)
        if km_match: km = int(km_match.group(1))
        
    return lt, lb, kt, km

def scrape_rumah123_v55():
    script_dir = Path(__file__).resolve().parent
    output_path = script_dir / 'brankas_data' / 'mentah' / 'properti_mentah.json'
    config_path = script_dir / 'config.json'
    
    with open(config_path, 'r') as f:
        config = json.load(f)
        cities = config.get("cities", [])
        max_pages = config.get("max_pages_per_city", 1)

    print(f"[*] SPEED-ENGINE V55: High-Speed Precision Extraction Aktif...")
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
                time.sleep(5)
                
                # Sikat data dari kartu secara langsung (Cepat & Akurat)
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                cards = soup.find_all("div", attrs={"data-name": "ldp-listing-card"})
                
                if not cards:
                    print("    [!] Tidak ada kartu ditemukan.")
                    break
                    
                added = 0
                for card in cards:
                    try:
                        link_el = card.find("a", href=re.compile(r"hos\d+"))
                        if not link_el: continue
                        url_prop = link_el['href']
                        if url_prop.startswith("/"): url_prop = f"https://www.rumah123.com{url_prop}"
                        
                        id_match = re.search(r"-(hos\d+)/?$", url_prop)
                        prop_id = id_match.group(1) if id_match else url_prop
                        if prop_id in seen_ids: continue

                        price_el = card.find("span", attrs={"data-testid": "ldp-text-price"})
                        price_text = price_el.get_text(strip=True) if price_el else ""
                        price_val = parse_price_smart(price_text)
                        if price_val == 0: continue

                        # Ambil spesifikasi fisik
                        lt, lb, kt, km = extract_specs_smart(card)
                        
                        # Ambil "Kategori" atau "Tag" jika ada (misal: 'KPR', 'Baru', dll)
                        tags = [t.get_text(strip=True) for t in card.find_all("span", class_=re.compile(r"badge|tag"))]
                        
                        entry = {
                            "id": prop_id,
                            "judul": card.find("h2").get_text(strip=True) if card.find("h2") else "N/A",
                            "harga": str(price_val),
                            "lokasi": city_name,
                            "lt": lt, "lb": lb, "kt": kt, "km": km,
                            "tags": tags,
                            "url_properti": url_prop,
                            "waktu_tarik": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
                        total_results.append(entry)
                        seen_ids.add(prop_id)
                        added += 1
                        print(f"    [OK] {price_val/1e9:.1f}M | LT:{lt:3} LB:{lb:3} | {entry['judul'][:30]}...")

                    except: continue
                
                print(f"--- Selesai Hal {page_num} | Berhasil: {added} ---")
                with open(output_path, 'w') as f: json.dump(total_results, f, indent=4)

    finally:
        driver.quit()
        print(f"\n[*] TOTAL BERHASIL DITARIK: {len(total_results)}")

if __name__ == "__main__":
    scrape_rumah123_v55()
