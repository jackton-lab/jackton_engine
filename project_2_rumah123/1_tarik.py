import json
import re
from pathlib import Path
from playwright.sync_api import sync_playwright

def parse_price(price_str):
    if not price_str or "Rp" not in price_str: return 0
    pattern_unit = r"Rp\s*(\d+(?:[.,]\d+)?)\s*(miliar|juta|jt|m)"
    match_unit = re.search(pattern_unit, price_str, re.IGNORECASE)
    if match_unit:
        num_str = match_unit.group(1).replace(",", ".")
        unit = match_unit.group(2).lower()
        val = float(num_str)
        if "miliar" in unit or unit == "m": val *= 1_000_000_000
        elif "juta" in unit or unit == "jt": val *= 1_000_000
        return int(val)
    pattern_long = r"Rp\s*([\d.]+)"
    match_long = re.search(pattern_long, price_str, re.IGNORECASE)
    if match_long:
        num_str = match_long.group(1).replace(".", "")
        if num_str.isdigit(): return int(num_str)
    return 0

def scrape_rumah123_revised():
    script_path = Path(__file__).resolve()
    output_path = script_path.parent / 'brankas_data' / 'mentah' / 'properti_mentah.json'
    
    targets = [
        {"kota": "Semarang", "url_base": "https://www.rumah123.com/jual/semarang/rumah/?sort=posted-desc&harga-min=500000000", "pages": 2},
        {"kota": "Solo", "url_base": "https://www.rumah123.com/jual/surakarta/rumah/?sort=posted-desc&harga-min=500000000", "pages": 2}
    ]

    print("[*] REVISED ENGINE V3: Memulai penarikan data Multi-Kota (Listing Terbaru)...")
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        context = browser.new_context(user_agent=user_agent, viewport={'width': 1280, 'height': 800})
        page = context.new_page()
        page.route("**/*.{png,jpg,jpeg,svg,webp,gif}", lambda route: route.abort())

        for target in targets:
            kota = target["kota"]
            for i in range(1, target["pages"] + 1):
                page_url = f"{target['url_base']}&page={i}" if i > 1 else target['url_base']
                print(f"[*] Mengekstraksi {kota} - Halaman {i}: {page_url}")

                try:
                    page.goto(page_url, wait_until="domcontentloaded", timeout=45000)
                    page.wait_for_timeout(5000) 
                    
                    cards = page.query_selector_all("div[class*='card'], div[class*='listing'], article")
                    print(f"    -> Ditemukan {len(cards)} elemen properti.")

                    for card in cards:
                        try:
                            title_el = card.query_selector("h2, h3, a[title]")
                            title = title_el.inner_text().strip() if title_el else ""
                            link_el = card.query_selector("a[href]")
                            raw_url = link_el.get_attribute("href") if link_el else "#"
                            final_url = f"https://www.rumah123.com{raw_url}" if raw_url.startswith("/") else raw_url
                            
                            if not title or len(title) < 10: continue

                            price_el = card.query_selector("span:has-text('Rp'), div:has-text('Rp'), p:has-text('Rp')")
                            price_raw = price_el.inner_text().strip() if price_el else ""
                            price_final = parse_price(price_raw)
                            
                            if price_final == 0: continue

                            loc_selectors = [".ui-organism-property-card__location", ".ui-molecule-property-card__location", "[class*='location']"]
                            location = kota
                            for sel in loc_selectors:
                                loc_el = card.query_selector(sel)
                                if loc_el:
                                    loc_text = loc_el.inner_text().strip()
                                    if len(loc_text) > 3:
                                        location = loc_text
                                        break

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
                            
                            if not any(r['url_properti'] == item['url_properti'] for r in results):
                                results.append(item)
                        except Exception as e:
                            continue
                except Exception as e:
                    print(f"[!] ERROR di {kota} hal {i}: {e}")

        print(f"[*] Menyimpan {len(results)} data mentah ke: {output_path}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=4)
        browser.close()

if __name__ == "__main__":
    scrape_rumah123_revised()
