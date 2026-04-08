import os
import json
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

# SMART CLOUD SYNC V49
# Sinkronisasi Data Hasil Analisis AI ke Supabase

def upload_to_supabase():
    load_dotenv()
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    script_dir = Path(__file__).resolve().parent
    input_path = script_dir / 'brankas_data' / 'bersih' / 'properti_analisis.json'
    
    if not url or not key:
        print("[!] SUPABASE_URL atau SUPABASE_KEY tidak ditemukan di .env")
        return
    if not input_path.exists():
        print(f"[!] Data analisis tidak ditemukan di {input_path}")
        return

    supabase: Client = create_client(url, key)
    with open(input_path, 'r') as f:
        data = json.load(f)

    print(f"[*] Menyiapkan sinkronisasi {len(data)} data ke Supabase...")

    payloads = []
    for item in data:
        # Menyiapkan payload sesuai struktur tabel 'investments'
        # Sesuaikan nama kolom jika berbeda di database Anda
        payloads.append({
            "id_properti": item.get('id'),
            "judul": item.get('judul', 'N/A')[:255],
            "url_asli": item.get('url_properti'),
            "lokasi": item.get('lokasi', 'N/A')[:100],
            "harga_total": int(item.get('harga', 0)),
            "lt": int(item.get('lt', 0)),
            "lb": int(item.get('lb', 0)),
            "kt": int(item.get('kt', 0)),
            "km": int(item.get('km', 0)),
            "harga_m2": int(item.get('harga_per_m2', 0)),
            "skor": int(item.get('skor_investasi', 0)),
            "klasifikasi": item.get('klasifikasi', 'REGULAR'),
            "summary": item.get('analisis_ai', 'No summary.')
        })

    if not payloads:
        print("[!] Tidak ada data untuk diunggah.")
        return

    # Upload dalam batch 50 per kiriman agar stabil
    batch_size = 50
    success_count = 0
    
    for i in range(0, len(payloads), batch_size):
        batch = payloads[i:i+batch_size]
        print(f"    [>] Mengunggah Batch {i//batch_size + 1}...", end="\r")
        try:
            # Gunakan upsert agar tidak ganda (berdasarkan id_properti atau url_asli)
            # Pastikan kolom 'url_asli' atau 'id_properti' unik di Supabase
            supabase.table('investments').upsert(batch, on_conflict="url_asli").execute()
            success_count += len(batch)
        except Exception as e:
            print(f"\n[!] Batch Error: {e}")

    print(f"\n[SUCCESS] Sinkronisasi Selesai! {success_count} data tersimpan di Supabase.")

if __name__ == "__main__":
    upload_to_supabase()
