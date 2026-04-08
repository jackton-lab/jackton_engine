import json
import csv
import re
from pathlib import Path

def generate_clean_report():
    # 1. Setup Path
    script_path = Path(__file__).resolve()
    input_path = script_path.parent / 'brankas_data' / 'bersih' / 'properti_analisis.json'
    csv_output_path = script_path.parent / 'Laporan_Investasi_Semarang.csv'
    
    print("[*] Memulai pembersihan data & pembuatan Laporan Semarang...")

    if not input_path.exists():
        print(f"[!] ERROR: File {input_path} tidak ditemukan.")
        return

    with open(input_path, 'r') as f:
        data = json.load(f)

    # Nama-nama kecamatan utama di Semarang untuk Regex
    semarang_districts = [
        "Tembalang", "Banyumanik", "Gunungpati", "Pedurungan", "Mijen", 
        "Ngaliyan", "Tugu", "Gayamsari", "Genuk", "Semarang Barat", 
        "Semarang Timur", "Semarang Utara", "Semarang Selatan", "Semarang Tengah",
        "Gajahmungkur", "Candisari", "Simpang Lima", "Tlogosari"
    ]

    cleaned_data = []
    
    for item in data:
        # A. Kunci LOKASI (Anti-Bocor Deskripsi)
        raw_loc = str(item.get('lokasi', 'N/A')).strip()
        final_loc = "N/A"
        
        # Jika lokasi bawaan valid (pendek dan bukan N/A), gunakan itu
        if raw_loc != "N/A" and len(raw_loc) < 35:
            final_loc = raw_loc
        else:
            # Fallback: HANYA cari di string JUDUL menggunakan Regex nama kecamatan
            judul = item.get('judul', '')
            for district in semarang_districts:
                if re.search(rf"\b{district}\b", judul, re.IGNORECASE):
                    final_loc = district
                    break
        
        # Batasi panjang lokasi (Max 30 Karakter)
        final_loc = final_loc[:30]

        # B. Ekstrak Data Analisis
        ai = item.get('analisis_ai', {})
        skor = ai.get('skor_investasi', 0)
        
        # Robust Harga Per M2 Formatting
        raw_h2 = ai.get('harga_per_m2', 0)
        try:
            h2_val = int(re.sub(r'\D', '', str(raw_h2))) if raw_h2 else 0
            harga_m2_str = f"Rp {h2_val:,}" if h2_val > 0 else "N/A"
        except:
            harga_m2_str = "N/A"

        label = ai.get('klasifikasi', 'REGULAR')
        summary = ai.get('summary_analis', '')

        # C. Formating Harga Total
        price_val = str(item.get('harga', '0'))
        price_str = f"Rp {int(price_val):,}" if price_val.isdigit() else "N/A"

        cleaned_item = {
            "SKOR": skor,
            "KLASIFIKASI": label,
            "LOKASI": final_loc,
            "JUDUL": item.get('judul', '')[:60],
            "HARGA_TOTAL": price_str,
            "HARGA_M2": harga_m2_str,
            "SUMMARY": summary
        }
        cleaned_data.append(cleaned_item)

    # 4. Sorting Descending by Skor
    cleaned_data.sort(key=lambda x: x['SKOR'], reverse=True)

    # 5. Export to CSV
    if cleaned_data:
        keys = cleaned_data[0].keys()
        with open(csv_output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(cleaned_data)
        print(f"[OK] Laporan final aman bocor diekspor ke: {csv_output_path}")

    # 6. Terminal Summary
    print("\n" + "="*115)
    print(f"{'SKOR':<5} | {'KLASIFIKASI':<12} | {'LOKASI':<15} | {'HARGA':<15} | {'HARGA_M2':<15} | {'JUDUL':<30}")
    print("-" * 115)
    for row in cleaned_data[:10]:
        print(f"{row['SKOR']:<5} | {row['KLASIFIKASI']:<12} | {row['LOKASI']:<15} | {row['HARGA_TOTAL']:<15} | {row['HARGA_M2']:<15} | {row['JUDUL']:<30}")
    print("="*115)

if __name__ == "__main__":
    generate_clean_report()
