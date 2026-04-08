import os
import json
import requests
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

def pull_winning_ads():
    # 1. Setup Path & Load Env
    script_path = Path(__file__).resolve()
    root_dir = script_path.parent.parent
    env_path = root_dir / '.env'
    
    print(f"[*] Memulai proses penarikan iklan...")
    
    load_dotenv(dotenv_path=env_path)
    access_token = os.getenv("FB_ACCESS_TOKEN")
    
    target_json_path = script_path.parent / 'target.json'
    output_path = script_path.parent / 'brankas_data' / 'mentah' / 'ads_mentah.json'
    
    if not access_token:
        print("[!] ERROR: FB_ACCESS_TOKEN tidak ditemukan di file .env root.")
        return

    # 2. Load Search Terms
    print(f"[*] Membaca parameter dari: {target_json_path}")
    try:
        with open(target_json_path, 'r') as f:
            targets = json.load(f)
            search_terms = targets.get("search_terms", [])
            print(f"[OK] Berhasil memuat {len(search_terms)} search terms.")
    except Exception as e:
        print(f"[!] ERROR: Gagal membaca target.json: {e}")
        return

    # 3. API Configuration
    API_VERSION = "v19.0"
    URL = f"https://graph.facebook.com/{API_VERSION}/ads_archive"
    winning_ads = []
    now = datetime.now(timezone.utc)
    
    total_raw_count = 0
    total_winning_count = 0

    # 4. Processing Search Terms
    for term in search_terms:
        print(f"[*] Menghubungkan ke API Meta untuk term: '{term}'...")
        params = {
            "access_token": access_token,
            "ad_active_status": "ACTIVE",
            "ad_reached_countries": "['ID']",
            "search_terms": term,
            "fields": "ad_creation_time,ad_creative_bodies,page_name,ad_delivery_start_time",
            "limit": 100
        }

        try:
            response = requests.get(URL, params=params, timeout=30)
            response.raise_for_status()
            print(f"[OK] Koneksi sukses (Status: {response.status_code})")
            
            data = response.json().get('data', [])
            term_raw_count = len(data)
            term_winning_count = 0
            total_raw_count += term_raw_count

            for ad in data:
                start_time_str = ad.get('ad_delivery_start_time')
                if not start_time_str:
                    continue
                
                # Filter Logic: Duration >= 14 days
                start_date = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                duration = (now - start_date).days

                if duration >= 14:
                    ad['winning_duration_days'] = duration
                    winning_ads.append(ad)
                    term_winning_count += 1
            
            total_winning_count += term_winning_count
            print(f"    -> Ditemukan: {term_raw_count} iklan | Lolos (>=14 hari): {term_winning_count}")

        except requests.exceptions.RequestException as e:
            print(f"[!] ERROR: Masalah API untuk term '{term}': {e}")
            continue

    # 5. Save to JSON
    print(f"[*] Menyimpan data ke: {output_path}")
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(winning_ads, f, indent=4)
        print(f"[OK] Final: {total_winning_count} winning ads berhasil disimpan.")
    except Exception as e:
        print(f"[!] ERROR: Gagal menyimpan file: {e}")

if __name__ == "__main__":
    pull_winning_ads()
