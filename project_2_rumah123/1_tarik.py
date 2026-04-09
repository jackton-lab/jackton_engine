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

def extract_specs_v61(card_soup):
    lt = lb = kt = km = 0
    text_full = card_soup.get_text(" ").lower()
    m_lt = re.search(r"lt\s*:?\s*(\d+)", text_full)
    m_lb = re.search(r"lb\s*:?\s*(\d+)", text_full)
    if m_lt: lt = int(m_lt.group(1))
    if m_lb: lb = int(m_lb.group(1))
    
    # Ekstraksi KT/KM dengan logika yang lebih aman
    kt_el = card_soup.find("use", attrs={"xlink:href": re.compile(r"bedroom-icon")})
    if kt_el:
        try:
            parent_span = kt_el.find_parent("span")
            if parent_span:
                kt_t = parent_span.get_text(strip=True)
                m = re.search(r"(\d+)", kt_t)
                if m: kt = int(m.group(1))
        except: pass
    
    km_el = card_soup.find("use", attrs={"xlink:href": re.compile(r"bathroom-icon")})
    if km_el:
        try:
            parent_span = km_el.find_parent("span")
            if parent_span:
                km_t = parent_span.get_text(strip=True)
                m = re.search(r"(\d+)", km_t)
                if m: km = int(m.group(1))
        except: pass
    return lt, lb, kt, km

def extract_from_next_data_v80(soup):
    script_tag = soup.find("script", id="__NEXT_DATA__")
    if not script_tag: return []
    try:
        data = json.loads(script_tag.string)
        listings = data.get("props", {}).get("pageProps", {}).get("initialValue", {}).get("search", {}).get("res", [])
        results = []
        for item in listings:
            try:
                prop_id = item.get("id")
                title = item.get("title")
                price_val = item.get("prices", [{}])[0].get("value", 0)
                lt = item.get("attributes", {}).get("landSize", 0)
                lb = item.get("attributes", {}).get("builtUpSize", 0)
                kt = item.get("attributes", {}).get("bedroom", 0)
                km = item.get("attributes", {}).get("bathroom", 0)
                lokasi = item.get("location", {}).get("city", {}).get("name", "N/A")
                district = item.get("location", {}).get("district", {}).get("name", "")
                lokasi_full = f"{district}, {lokasi}" if district else lokasi
                if price_val == 0 or lt == 0: continue
                results.append({
                    "id": prop_id, "judul": title,
                    "harga": str(int(price_val)), "lokasi": lokasi_full,
                    "lt": int(lt), "lb": int(lb), "kt": int(kt), "km": int(km),
                    "harga_m2": int(price_val / lt) if lt > 0 else 0,
                    "url_properti": f"https://www.rumah123.com{item.get('url')}",
                    "waktu_tarik": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
            except: continue
        return results
    except: return []

def scrape_rumah123_v61():
    script_dir = Path(__file__).resolve().parent
    output_path = script_dir / 'brankas_data' / 'mentah' / 'properti_mentah.json'
    config_path = script_dir / 'config.json'
    
    with open(config_path, 'r') as f:
        config = json.load(f)
        cities = config.get("cities", [])
        max_pages = config.get("max_pages_per_city", 1)

    print(f"[*] PRECISION-ENGINE V61: JSON Surgeon + Card Fallback Aktif...")
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
                time.sleep(6)
                
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                listings = extract_from_next_data_v80(soup)
                
                if listings:
                    added = 0
                    for item in listings:
                        if item['id'] not in seen_ids:
                            total_results.append(item)
                            seen_ids.add(item['id'])
                            added += 1
                    print(f"    [OK] Berhasil menarik {added} data via JSON Surgeon.")
                else:
                    print("    [!] JSON Method failed, falling back to Card Parsing...")
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
                            price_val = parse_price_smart(card.find("span", attrs={"data-testid": "ldp-text-price"}).get_text(strip=True))
                            if price_val == 0: continue
                            lt, lb, kt, km = extract_specs_v61(card)
                            loc_el = card.find("p", class_=re.compile(r"text-greyText"))
                            lokasi = loc_el.get_text(strip=True) if loc_el else city_name
                            harga_m2 = int(price_val / lt) if lt > 0 else 0
                            entry = {
                                "id": prop_id, "judul": card.find("h2").get_text(strip=True),
                                "harga": str(price_val), "lokasi": lokasi,
                                "lt": lt, "lb": lb, "kt": kt, "km": km,
                                "harga_m2": harga_m2,
                                "url_properti": url_prop,
                                "waktu_tarik": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            }
                            total_results.append(entry)
                            seen_ids.add(prop_id)
                            added += 1
                        except: continue
                    print(f"    [OK] Berhasil menarik {added} data via Card Parsing.")
                
                with open(output_path, 'w') as f: json.dump(total_results, f, indent=4)
    finally:
        driver.quit()

if __name__ == "__main__":
    scrape_rumah123_v61()
