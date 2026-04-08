import json
import re
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

def parse_price(price_str):
    """
    Parser harga presisi untuk format properti Indonesia.
    Mengatasi bug angka jumlah foto dengan mencari pola 'Rp' yang diikuti angka dan satuan.
    """
    if not price_str or "Rp" not in price_str:
        return 0
    
    # 1. Taktik Utama: Cari pola Rp <angka> <satuan>
    # Contoh: 'Rp 2,5 Miliar', 'Rp 850 Juta', 'Rp 1,2 M'
    pattern_unit = r"Rp\s*(\d+(?:[.,]\d+)?)\s*(miliar|juta|jt|m)"
    match_unit = re.search(pattern_unit, price_str, re.IGNORECASE)
    
    if match_unit:
        num_str = match_unit.group(1).replace(",", ".")
        unit = match_unit.group(2).lower()
        val = float(num_str)
        
        if "miliar" in unit or unit == "m":
            val *= 1_000_000_000
        elif "juta" in unit or unit == "jt":
            val *= 1_000_000
        return int(val)
    
    # 2. Taktik Fallback: Cari pola Rp <angka_panjang>
    # Contoh: 'Rp 1.250.000.000'
    pattern_long = r"Rp\s*([\d.]+)"
    match_long = re.search(pattern_long, price_str, re.IGNORECASE)
    
    if match_long:
        # Hapus titik ribuan
        num_str = match_long.group(1).replace(".", "")
        if num_str.isdigit():
            return int(num_str)
            
    return 0

def scrape_rumah123_revised():
    # 1. Setup Path
    script_path = Path(__file__).resolve()
    target_json_path = script_path.parent / 'target.json'
    output_path = script_path.parent / 'brankas_data' / 'mentah' / 'properti_mentah.json'
    screenshot_path = script_path.parent / 'debug_rumah123.png'
    
    print("[*] REVISED ENGINE V2: Memulai penarikan data Rumah123 (Precise Price Extraction)...")

    # 2. Load Target URL
    try:
        with open(target_json_path, 'r') as f:
            config = json.load(f)
            url = config.get("target_url")
            print(f"[OK] Target URL: {url}")
    except Exception as e:
        print(f"[!] ERROR: Gagal membaca target.json: {e}")
        return

    # 3. Playwright Execution
    with sync_playwright() as p:
        print("[*] Meluncurkan browser (Headless)...")
        browser = p.chromium.launch(headless=True)
        
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        context = browser.new_context(user_agent=user_agent, viewport={'width': 1280, 'height': 800})
        page = context.new_page()

        # Fast-Grab: Blokir Gambar
        page.route("**/*.{png,jpg,jpeg,svg,webp,gif}", lambda route: route.abort())

        print(f"[*] Membuka halaman...")
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            print("[*] Menunggu 10 detik agar data ter-render sempurna...")
            page.wait_for_timeout(10000)
            page.screenshot(path=str(screenshot_path))
        except Exception as e:
            print(f"[!] ERROR: Gagal memuat halaman: {e}")
            browser.close()
            return

        # 4. Extract Data (Greedy & Precise)
        print("[*] Mengekstraksi 10 listing pertama...")
        
        # Greedy Card Selector
        cards = page.query_selector_all("div[class*='card'], div[class*='listing'], article")
        
        results = []
        count = 0

        for card in cards:
            if count >= 10:
                break
            
            try:
                # A. Judul & URL
                title_el = card.query_selector("h2, h3, a[title]")
                title = title_el.inner_text().strip() if title_el else ""
                
                # Ekstrak URL (Cari tag 'a' di dalam card)
                link_el = card.query_selector("a[href]")
                raw_url = link_el.get_attribute("href") if link_el else "#"
                # Pastikan URL absolut
                final_url = f"https://www.rumah123.com{raw_url}" if raw_url.startswith("/") else raw_url
                
                # Validasi Judul
                if not title or len(title) < 10:
                    continue

                # B. Harga (REVISED PRECISE EXTRACTION)
                # Cari elemen yang mengandung teks "Rp" secara spesifik dalam card
                price_el = card.query_selector("span:has-text('Rp'), div:has-text('Rp'), p:has-text('Rp')")
                price_raw = price_el.inner_text().strip() if price_el else ""
                price_final = parse_price(price_raw)
                
                if price_final == 0:
                    continue

                # C. Lokasi (Targeting Location Selectors)
                loc_selectors = [
                    ".ui-organism-property-card__location", 
                    ".ui-molecule-property-card__location",
                    "[class*='location']",
                    "[class*='address']",
                    "p:has-text('Semarang')" 
                ]
                
                location = "N/A"
                for sel in loc_selectors:
                    loc_el = card.query_selector(sel)
                    if loc_el:
                        loc_text = loc_el.inner_text().strip()
                        if loc_text and len(loc_text) > 3:
                            location = loc_text
                            break

                # D. Spesifikasi
                specs_data = {}
                attr_els = card.query_selector_all("[class*='attribute'], [class*='facility']")
                for attr in attr_els:
                    text = attr.inner_text().lower()
                    val = attr.inner_text().strip()
                    if "kt" in text or "kamar tidur" in text: specs_data["kt"] = val
                    elif "km" in text or "kamar mandi" in text: specs_data["km"] = val
                    elif "lt" in text: specs_data["lt"] = val
                    elif "lb" in text: specs_data["lb"] = val

                item = {
                    "judul": title,
                    "url_properti": final_url,
                    "harga": price_final,
                    "harga_label": price_raw, 
                    "lokasi": location,
                    "spesifikasi": specs_data
                }
                
                if not any(r['judul'] == item['judul'] for r in results):
                    results.append(item)
                    count += 1
                    print(f"    -> Listing {count}: {title[:30]}... | {price_raw} -> {price_final}")

            except Exception as e:
                continue

        # 5. Save Results
        print(f"[*] Menyimpan {len(results)} data bersih ke: {output_path}")
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump(results, f, indent=4)
            print("[OK] Selesai! Data mentah berhasil diperbaiki (V2).")
        except Exception as e:
            print(f"[!] ERROR: Gagal menyimpan file: {e}")

        browser.close()

if __name__ == "__main__":
    scrape_rumah123_revised()
