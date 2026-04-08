import json
import re
import os
import time
from datetime import datetime
from pathlib import Path
from seleniumbase import Driver
from bs4 import BeautifulSoup

def log_system(message, status="SUCCESS"):
    script_dir = Path(__file__).resolve().parent
    log_dir = script_dir / 'catatan_sistem'
    log_file = log_dir / ('sukses.log' if status == "SUCCESS" else 'error.log')
    log_dir.mkdir(parents=True, exist_ok=True)
    with open(log_file, "a") as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [1_tarik.py] {message}\n")

def parse_price_smart(price_str):
    if not price_str or "Rp" not in price_str: return 0
    # Bersihkan teks gangguan (cicilan, tenor, dll)
    if any(x in price_str.lower() for x in ["tenor", "cicilan", "per bulan", "bln", "mulai"]): return 0
    
    # Ambil angka dan unit (Miliar/Juta)
    # Contoh: "Rp 15,8 Miliar" -> "15,8" dan "Miliar"
    price_str = price_str.replace("Rp", "").strip()
    match = re.search(r"([\d,\.]+)\s*(miliar|juta|jt|m)?", price_str, re.IGNORECASE)
    if not match: return 0
    
    val_str = match.group(1).replace(".", "") # Hapus titik ribuan
    val_str = val_str.replace(",", ".") # Ubah koma desimal jadi titik
    
    try:
        val = float(val_str)
        unit = (match.group(2) or "").lower()
        if "miliar" in unit or unit == "m": val *= 1_000_000_000
        elif "juta" in unit or unit == "jt": val *= 1_000_000
        return int(val)
    except:
        return 0

def extract_specs_smart(card_soup):
    lt = lb = kt = km = 0
    
    # Cari kontainer spesifikasi
    # Biasanya ada di dalam div yang punya class flex dan gap
    spec_container = card_soup.find("div", class_=re.compile(r"flex.*gap-x-2.*text-sm"))
    if not spec_container:
        # Fallback cari span yang mengandung 'LT' atau 'LB'
        spec_container = card_soup
        
    text_content = spec_container.get_text(" ").replace("\n", " ")
    
    # 1. Cari LT & LB dengan pola "LT : 123 m2" atau "LT 123 m2"
    m_lt = re.search(r"LT\s*:?\s*(\d+)", text_content)
    m_lb = re.search(r"LB\s*:?\s*(\d+)", text_content)
    if m_lt: lt = int(m_lt.group(1))
    if m_lb: lb = int(m_lb.group(1))
    
    # 2. Cari KT & KM dengan mencari ikon bedroom/bathroom
    # Bedroom
    kt_el = card_soup.find("use", attrs={"xlink:href": re.compile(r"bedroom-icon")})
    if kt_el:
        # Teks biasanya ada di parent span setelah svg
        kt_text = kt_el.find_parent("span").get_text(strip=True)
        kt_match = re.search(r"(\d+)", kt_text)
        if kt_match: kt = int(kt_match.group(1))
    
    # Bathroom
    km_el = card_soup.find("use", attrs={"xlink:href": re.compile(r"bathroom-icon")})
    if km_el:
        km_text = km_el.find_parent("span").get_text(strip=True)
        km_match = re.search(r"(\d+)", km_text)
        if km_match: km = int(km_match.group(1))

    return lt, lb, kt, km

def scrape_rumah123():
    script_dir = Path(__file__).resolve().parent
    output_path = script_dir / 'brankas_data' / 'mentah' / 'properti_mentah.json'
    config_path = script_dir / 'config.json'
    
    if not config_path.exists():
        print("[!] config.json tidak ditemukan!")
        return
        
    with open(config_path, 'r') as f:
        config = json.load(f)
        cities = config.get("cities", [])
        max_pages = config.get("max_pages_per_city", 1)

    print(f"[*] SMART-VOID ENGINE V48: JSON-LD Aware & Precision Selectors Aktif...")
    
    total_results = []
    seen_ids = set()
    
    driver = Driver(uc=True, headless=True)

    try:
        for city in cities:
            city_name = city["nama"]
            city_slug = city["slug"]
            url_base = f"https://www.rumah123.com/jual/{city_slug}/rumah/?sort=posted-desc"
            
            for page_num in range(1, max_pages + 1):
                page_url = f"{url_base}&page={page_num}"
                print(f"\n>>> {city_name} | HAL {page_num} | Total Unik: {len(total_results)}")
                
                try:
                    driver.uc_open_with_reconnect(page_url, 6)
                    time.sleep(5) # Tunggu render awal
                    
                    # Scroll sedikit untuk trigger lazy load
                    driver.execute_script("window.scrollBy(0, 1000);")
                    time.sleep(2)
                    
                    soup = BeautifulSoup(driver.page_source, 'html.parser')
                    cards = soup.find_all("div", attrs={"data-name": "ldp-listing-card"})
                    
                    if not cards:
                        print("    [!] Tidak ada kartu ditemukan (mungkin kena block atau ganti struktur).")
                        # Debug: Simpan source jika gagal
                        with open('error_page.html', 'w') as f: f.write(driver.page_source)
                        break
                        
                    added_in_page = 0
                    for card in cards:
                        try:
                            # 1. URL & ID
                            link_el = card.find("a", href=re.compile(r"hos\d+"))
                            if not link_el: continue
                            url_prop = link_el['href']
                            if url_prop.startswith("/"): url_prop = f"https://www.rumah123.com{url_prop}"
                            
                            id_match = re.search(r"-(hos\d+)/?$", url_prop)
                            prop_id = id_match.group(1) if id_match else url_prop
                            
                            if prop_id in seen_ids: continue

                            # 2. Harga (Selector Presisi)
                            price_el = card.find("span", attrs={"data-testid": "ldp-text-price"})
                            price_text = price_el.get_text(strip=True) if price_el else ""
                            price_val = parse_price_smart(price_text)
                            
                            if price_val == 0: continue # Lewati jika bukan harga jual (misal sewa/cicilan)

                            # 3. Judul & Lokasi
                            title_el = card.find("h2")
                            title = title_el.get_text(strip=True) if title_el else "Rumah"
                            
                            loc_el = card.find("p", class_=re.compile(r"text-greyText.*text-sm.*truncate"))
                            lokasi = loc_el.get_text(strip=True) if loc_el else city_name

                            # 4. Spesifikasi (Smart Extraction)
                            lt, lb, kt, km = extract_specs_smart(card)

                            entry = {
                                "id": prop_id, "judul": title, "harga": str(price_val), "lokasi": lokasi,
                                "lt": lt, "lb": lb, "kt": kt, "km": km,
                                "url_properti": url_prop, "waktu_tarik": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            }
                            total_results.append(entry)
                            seen_ids.add(prop_id)
                            added_in_page += 1
                            
                            p_human = f"{price_val/1e9:.1f}M" if price_val >= 1e9 else f"{price_val/1e6:.0f}jt"
                            print(f"    [OK] {p_human:>7} | LT:{lt:4d} LB:{lb:4d} | KT:{kt:1d} KM:{km:1d} | {lokasi[:15]:15} | {title[:25]}...")

                        except Exception as e:
                            continue
                    
                    print(f"--- SELESAI HAL {page_num} | Berhasil Tarik: {added_in_page} ---")
                    
                    # Simpan progres per halaman
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(output_path, 'w') as f:
                        json.dump(total_results, f, indent=4)
                        
                    if added_in_page == 0: break
                    
                except Exception as e:
                    print(f"    [!] Error di halaman: {e}")
                    log_system(f"Gagal di {city_name} Hal {page_num}: {e}", "ERROR")

    finally:
        driver.quit()
        print(f"\n[*] TOTAL BERHASIL DITARIK: {len(total_results)}")

if __name__ == "__main__":
    scrape_rumah123()
