import json
import csv
import re
from pathlib import Path

# BRUTAL DYNAMIC REPORTER V2
# Otomatis mendeteksi lokasi tanpa hardcoded district.

def generate_global_report():
    script_dir = Path(__file__).resolve().parent
    input_path = script_dir / 'brankas_data' / 'bersih' / 'properti_analisis.json'
    csv_output_path = script_dir / 'Laporan_Investasi_Global.csv'
    
    if not input_path.exists():
        print("[!] Data analisis tidak ditemukan.")
        return

    with open(input_path, 'r') as f:
        data = json.load(f)

    print(f"[*] Membuat Laporan Global untuk {len(data)} properti...")

    report_list = []
    for item in data:
        ai = item.get('analisis_ai', {})
        
        # Formatting data untuk CSV
        price_val = int(item.get('harga', 0))
        p_human = f"Rp {price_val/1e9:.1f}M" if price_val >= 1e9 else f"Rp {price_val/1e6:.0f}jt"
        
        row = {
            "SKOR": ai.get('skor_investasi', 0),
            "KLASIFIKASI": ai.get('klasifikasi', 'REGULAR'),
            "LOKASI": item.get('lokasi', 'N/A')[:30],
            "JUDUL": item.get('judul', 'N/A')[:50],
            "HARGA": p_human,
            "M2": f"Rp {int(ai.get('harga_per_m2', 0)):,}",
            "SPECS": f"LT:{item.get('lt')} LB:{item.get('lb')} KT:{item.get('kt')} KM:{item.get('km')}",
            "URL": item.get('url_properti')
        }
        report_list.append(row)

    # Sort berdasarkan Skor Tertinggi
    report_list.sort(key=lambda x: x['SKOR'], reverse=True)

    if report_list:
        with open(csv_output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=report_list[0].keys())
            writer.writeheader()
            writer.writerows(report_list)
        
        print(f"[SUCCESS] Laporan diekspor ke: {csv_output_path}")
        
        # Tampilkan Top 10 di Terminal
        print("\n" + "="*120)
        print(f"{'SKOR':<5} | {'KLASIFIKASI':<12} | {'HARGA':<10} | {'LOKASI':<20} | {'JUDUL'}")
        print("-" * 120)
        for r in report_list[:10]:
            print(f"{r['SKOR']:<5} | {r['KLASIFIKASI']:<12} | {r['HARGA']:<10} | {r['LOKASI']:<20} | {r['JUDUL']}")
        print("="*120)

if __name__ == "__main__":
    generate_global_report()
