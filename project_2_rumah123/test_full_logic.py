import json
import os
from pathlib import Path

def test_logic_flow():
    print("[*] MEMULAI TEST LOGIKA PROJECT...")
    script_dir = Path(__file__).resolve().parent
    
    # 1. MOCK DATA (Simulasi hasil 1_tarik.py)
    mock_raw = [
        {
            "judul": "Rumah Murah di Tembalang Semarang BU",
            "harga": "1200000000",
            "lokasi": "Tembalang, Semarang",
            "url_properti": "https://rumah123.com/test-1"
        },
        {
            "judul": "Rumah Mewah Simpang Lima Semarang",
            "harga": "5000000000",
            "lokasi": "Semarang Tengah",
            "url_properti": "https://rumah123.com/test-2"
        }
    ]
    
    mentah_path = script_dir / 'brankas_data' / 'mentah' / 'properti_mentah.json'
    mentah_path.parent.mkdir(parents=True, exist_ok=True)
    with open(mentah_path, 'w') as f:
        json.dump(mock_raw, f)
    print("[OK] Tahap 1: Simulasi data mentah berhasil.")

    # 2. MOCK ANALYSIS (Simulasi hasil 2_ai.py)
    mock_analyzed = []
    for item in mock_raw:
        item["analisis_ai"] = {
            "skor_investasi": 85 if "BU" in item["judul"] else 65,
            "klasifikasi": "HOT DEAL" if "BU" in item["judul"] else "REGULAR",
            "harga_per_m2": 7000000,
            "summary_analis": "Analisis simulasi: Harga masuk akal."
        }
        mock_analyzed.append(item)
    
    bersih_path = script_dir / 'brankas_data' / 'bersih' / 'properti_analisis.json'
    bersih_path.parent.mkdir(parents=True, exist_ok=True)
    with open(bersih_path, 'w') as f:
        json.dump(mock_analyzed, f)
    print("[OK] Tahap 2: Simulasi analisis AI berhasil.")

    # 3. TEST LAPORAN (Menjalankan 3_laporan.py)
    print("[*] Tahap 3: Menguji pembuatan laporan...")
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("laporan", str(script_dir / "3_laporan.py"))
        laporan = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(laporan)
        laporan.generate_clean_report()
        
        csv_path = script_dir / "Laporan_Investasi_Semarang.csv"
        if csv_path.exists():
            print(f"[SUCCESS] File laporan ditemukan: {csv_path}")
            # Tampilkan isi CSV sedikit untuk verifikasi
            with open(csv_path, 'r') as f:
                print("--- ISI CSV (3 baris pertama) ---")
                for _ in range(3):
                    print(f.readline().strip())
        else:
            print("[!] ERROR: Laporan CSV tidak terbentuk.")
    except Exception as e:
        print(f"[!] ERROR saat menjalankan 3_laporan.py: {e}")

if __name__ == "__main__":
    test_logic_flow()
