import os
import json
import re
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

def upload_to_supabase():
    # 1. Setup Path & Load Env
    script_path = Path(__file__).resolve()
    root_dir = script_path.parent.parent
    env_path = root_dir / '.env'
    load_dotenv(dotenv_path=env_path)
    
    url: str = os.getenv("SUPABASE_URL")
    key: str = os.getenv("SUPABASE_KEY")
    input_path = script_path.parent / 'brankas_data' / 'bersih' / 'properti_analisis.json'
    
    if not url or not key:
        print("[!] ERROR: Kredensial Supabase tidak ditemukan di .env root.")
        return

    # 2. Initialize Supabase Client
    supabase: Client = create_client(url, key)
    print(f"[*] Menghubungkan ke Cloud Supabase: {url}")

    # 3. Load Analysis Data
    if not input_path.exists():
        print(f"[!] ERROR: File {input_path} tidak ditemukan.")
        return

    with open(input_path, 'r') as f:
        data = json.load(f)
        print(f"[OK] Memuat {len(data)} listing untuk diunggah.")

    # 4. Final Sanitization & Formatting
    formatted_data = []
    for item in data:
        try:
            # Ekstrak AI data
            ai = item.get('analisis_ai', {})
            
            # Sanitasi Harga Total (Integer)
            raw_price = str(item.get('harga', '0'))
            clean_price = int(re.sub(r'\D', '', raw_price)) if raw_price.isdigit() or re.sub(r'\D', '', raw_price) else 0
            
            # Sanitasi Harga per m2 (Integer)
            raw_m2 = str(ai.get('harga_per_m2', '0'))
            clean_m2 = int(re.sub(r'\D', '', raw_m2)) if raw_m2.isdigit() or re.sub(r'\D', '', raw_m2) else 0

            # Strukturisasi Data sesuai Kolom Tabel Supabase
            payload = {
                "judul": item.get('judul', 'N/A')[:255],
                "url_asli": item.get('url_properti', '#'),
                "lokasi": item.get('lokasi', 'N/A')[:100],
                "harga_total": clean_price,
                "harga_m2": clean_m2,
                "skor": ai.get('skor_investasi', 0),
                "klasifikasi": ai.get('klasifikasi', 'REGULAR'),
                "summary": ai.get('summary_analis', 'No summary available.')
            }
            formatted_data.append(payload)
        except Exception as e:
            print(f"    [!] Melewati 1 baris karena error sanitasi: {e}")
            continue

    # 5. Bulk Insert to Supabase
    if not formatted_data:
        print("[!] Tidak ada data valid untuk diunggah.")
        return

    print(f"[*] Sedang mengirim {len(formatted_data)} data ke tabel 'investments'...")
    try:
        response = supabase.table('investments').insert(formatted_data).execute()
        # Supabase-py version check (response usually has 'data' or is the data itself)
        if response:
            print(f"[SUCCESS] Sinkronisasi Cloud Berhasil! {len(formatted_data)} listing tersimpan di Supabase.")
    except Exception as e:
        print(f"[!] ERROR: Gagal mengunggah data ke Supabase: {e}")
        print("[*] TIPS: Pastikan tabel 'investments' sudah ada di database Supabase Anda.")

if __name__ == "__main__":
    upload_to_supabase()
