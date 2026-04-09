import os
import json
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

# SMART CLOUD SYNC V60 - SINKRONISASI TOTAL
# Memastikan payload data bersih 100% cocok dengan skema Supabase

def upload_to_supabase():
    load_dotenv()
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    script_dir = Path(__file__).resolve().parent
    input_path = script_dir / 'brankas_data' / 'bersih' / 'properti_analisis.json'
    
    if not url or not key or not input_path.exists():
        print("[!] Konfigurasi atau data analisis tidak ditemukan.")
        return

    supabase: Client = create_client(url, key)
    with open(input_path, 'r') as f:
        data = json.load(f)

    print(f"[*] Menyiapkan sinkronisasi {len(data)} data bersih ke Supabase...")

    payloads = []
    for item in data:
        # EKSTRAKSI KOTA: Mengambil bagian terakhir setelah koma (Contoh: "Galaxy, Bekasi" -> "Bekasi")
        lokasi_full = item.get('lokasi', 'N/A')
        parts = [p.strip() for p in lokasi_full.split(',')]
        kota = parts[-1] if len(parts) > 1 else lokasi_full
        
        # Sinkronisasi field dengan skema tabel 'investments'
        # Memastikan analisis_ai (string) masuk ke kolom 'summary'
        payloads.append({
            "id_properti": item.get('id'),
            "judul": item.get('judul', 'N/A')[:255],
            "url_asli": item.get('url_properti'),
            "lokasi": lokasi_full[:100],
            "kota": kota[:50], # Kolom baru untuk Frontend
            "harga_total": int(item.get('harga', 0)),
            "lt": int(item.get('lt', 0)),
            "lb": int(item.get('lb', 0)),
            "kt": int(item.get('kt', 0)),
            "km": int(item.get('km', 0)),
            "harga_m2": int(item.get('harga_per_m2', 0)),
            "skor": int(item.get('skor_investasi', 0)),
            "klasifikasi": item.get('klasifikasi', 'REGULAR'),
            "summary": str(item.get('analisis_ai', 'No summary provided.'))
        })

    if not payloads:
        print("[!] Tidak ada payload untuk diunggah.")
        return

    # Upload dalam batch 100 agar efisien
    batch_size = 100
    success_count = 0
    
    for i in range(0, len(payloads), batch_size):
        batch = payloads[i:i+batch_size]
        print(f"    [>] Mengunggah Batch {i//batch_size + 1}...", end="\r")
        try:
            # Gunakan upsert berbasis url_asli (Unique Constraint)
            supabase.table('investments').upsert(batch, on_conflict="url_asli").execute()
            success_count += len(batch)
        except Exception as e:
            print(f"\n[!] Batch Error: {e}")

    print(f"\n[SUCCESS] Sinkronisasi V60 Berhasil! {success_count} data terbaru tersaji di Cloud.")

if __name__ == "__main__":
    upload_to_supabase()
