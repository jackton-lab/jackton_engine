import os
import json
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

# EMERGENCY UPLOAD V51
# Sinkronisasi Data Mentah Berkualitas (Tanpa Tunggu AI)

def upload_to_supabase_direct():
    load_dotenv()
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    script_dir = Path(__file__).resolve().parent
    # Langsung ambil dari properti_mentah.json (V48 hasil scraper akurat)
    input_path = script_dir / 'brankas_data' / 'mentah' / 'properti_mentah.json'
    
    if not url or not key or not input_path.exists():
        print("[!] Konfigurasi atau data tidak lengkap.")
        return

    supabase: Client = create_client(url, key)
    with open(input_path, 'r') as f:
        data = json.load(f)

    print(f"[*] Menyiapkan sinkronisasi {len(data)} data mentah berkualitas ke Supabase...")

    payloads = []
    for item in data:
        harga = int(item.get('harga', 0))
        lt = int(item.get('lt', 0))
        # Hitung harga_per_m2 manual jika LT ada
        harga_m2 = int(harga / lt) if lt > 0 else 0
        
        payloads.append({
            "id_properti": item.get('id'),
            "judul": item.get('judul', 'N/A')[:255],
            "url_asli": item.get('url_properti'),
            "lokasi": item.get('lokasi', 'N/A')[:100],
            "harga_total": harga,
            "lt": lt,
            "lb": int(item.get('lb', 0)),
            "kt": int(item.get('kt', 0)),
            "km": int(item.get('km', 0)),
            "harga_m2": harga_m2,
            "skor": 0, # Placeholder sebelum AI
            "klasifikasi": "RAW DATA",
            "summary": "Data terekstraksi sempurna oleh V50 Scraper. Menunggu analisis AI malam ini."
        })

    batch_size = 50
    success_count = 0
    for i in range(0, len(payloads), batch_size):
        batch = payloads[i:i+batch_size]
        try:
            supabase.table('investments').upsert(batch, on_conflict="url_asli").execute()
            success_count += len(batch)
            print(f"    [OK] Terkirim {success_count} data...")
        except Exception as e:
            print(f"\n[!] Batch Error: {e}")

    print(f"\n[SUCCESS] Sinkronisasi Selesai! {success_count} data tersimpan di Supabase.")

if __name__ == "__main__":
    upload_to_supabase_direct()
