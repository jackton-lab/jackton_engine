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
            # Mencari teks angka di dalam span yang membungkus icon
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
    """
    LOGIKA DEWA: Mengambil data langsung dari payload JSON internal Next.js.
    Tidak peduli CSS selector berubah, selama data ada di server, kita dapat.
    """
    script_tag = soup.find("script", id="__NEXT_DATA__")
    if not script_tag: return []
    
    try:
        data = json.loads(script_tag.string)
        # Navigasi ke dalam struktur JSON Rumah123 (Search Results)
        # Struktur biasanya: props -> pageProps -> initialValue -> search -> res
        listings = data.get("props", {}).get("pageProps", {}).get("initialValue", {}).get("search", {}).get("res", [])
        
        results = []
        for item in listings:
            try:
                # Ambil data murni tanpa BeautifulSoup
                prop_id = item.get("id")
                title = item.get("title")
                price_val = item.get("prices", [{}])[0].get("value", 0)
                
                # Spesifikasi
                lt = item.get("attributes", {}).get("landSize", 0)
                lb = item.get("attributes", {}).get("builtUpSize", 0)
                kt = item.get("attributes", {}).get("bedroom", 0)
                km = item.get("attributes", {}).get("bathroom", 0)
                
                # Lokasi
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
    # ... (rest of setup)
    driver = Driver(uc=True, headless=True)
    try:
        for city in cities:
            # ... (page loop)
            driver.uc_open_with_reconnect(page_url, 6)
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # GUNAKAN METODE PEMBEDAH JSON
            listings = extract_from_next_data_v80(soup)
            
            if not listings:
                # FALLBACK: Jika JSON gagal, gunakan metode kartu (Gotong Royong)
                print("    [!] JSON Method failed, falling back to Card Parsing...")
                # ... (logika ldp-listing-card yang lama)
            else:
                total_results.extend(listings)
                print(f"    [OK] Berhasil menarik {len(listings)} data via JSON Surgeon.")
    finally:
        driver.quit()
if __name__ == "__main__":
    scrape_rumah123_v61()
