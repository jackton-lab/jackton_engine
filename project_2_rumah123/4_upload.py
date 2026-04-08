import os
import json
import re
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

def upload_to_supabase():
    script_path = Path(__file__).resolve()
    root_dir = script_path.parent.parent
    env_path = root_dir / '.env'
    load_dotenv(dotenv_path=env_path)
    
    url: str = os.getenv("SUPABASE_URL")
    key: str = os.getenv("SUPABASE_KEY")
    input_path = script_path.parent / 'brankas_data' / 'bersih' / 'properti_analisis.json'
    
    if not url or not key:
        print("[!] ERROR: Kredensial Supabase tidak ditemukan.")
        return

    supabase: Client = create_client(url, key)
    print(f"[*] Menghubungkan ke Cloud Supabase: {url}")

    if not input_path.exists():
        print(f"[!] ERROR: File {input_path} tidak ditemukan.")
        return

    with open(input_path, 'r') as f:
        data = json.load(f)

    print("[*] Mengecek data duplikat di database...")
    existing_urls = set()
    try:
        response = supabase.table('investments').select('url_asli').limit(5000).execute()
        if hasattr(response, 'data') and response.data:
            existing_urls = {row['url_asli'] for row in response.data}
    except Exception as e:
        print(f"[!] Peringatan: Gagal mengecek data lama. Melanjutkan tanpa filter. Error: {e}")

    new_data = []
    skipped_count = 0

    for item in data:
        url_properti = item.get('url_properti', '#')
        
        if url_properti in existing_urls:
            skipped_count += 1
            continue

        try:
            ai = item.get('analisis_ai', {})
            raw_price = str(item.get('harga', '0'))
            clean_price = int(re.sub(r'\D', '', raw_price)) if re.sub(r'\D', '', raw_price) else 0
            raw_m2 = str(ai.get('harga_per_m2', '0'))
            clean_m2 = int(re.sub(r'\D', '', raw_m2)) if re.sub(r'\D', '', raw_m2) else 0

            payload = {
                "judul": item.get('judul', 'N/A')[:255],
                "url_asli": url_properti,
                "lokasi": item.get('lokasi', 'N/A')[:100],
                "harga_total": clean_price,
                "harga_m2": clean_m2,
                "skor": ai.get('skor_investasi', 0),
                "klasifikasi": ai.get('klasifikasi', 'REGULAR'),
                "summary": ai.get('summary_analis', 'No summary available.')
            }
            new_data.append(payload)
        except Exception as e:
            continue

    print(f"[*] Analisis Duplikat: {len(new_data)} data baru siap diunggah, {skipped_count} data duplikat dilewati.")

    if not new_data:
        print("[OK] Tidak ada data properti baru hari ini. Semua sudah tersimpan sebelumnya.")
        return

    print(f"[*] Sedang mengirim {len(new_data)} data baru ke tabel 'investments'...")
    try:
        response = supabase.table('investments').insert(new_data).execute()
        if response:
            print(f"[SUCCESS] Sinkronisasi Berhasil! {len(new_data)} listing baru tersimpan di Supabase.")
    except Exception as e:
        print(f"[!] ERROR: Gagal mengunggah data ke Supabase: {e}")

if __name__ == "__main__":
    upload_to_supabase()
