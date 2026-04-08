import os
import json
import time
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq

# NEURAL ENGINE V62 - NATIONAL AUDITOR EDITION
# Menggunakan Database Benchmark Nasional 2024-2025

BENCHMARK_NASIONAL = {
    "JABODETABEK": {
        "Jakarta_Selatan": {
            "Menteng": "60jt - 100jt", "Kebayoran_Baru": "46jt - 90jt", "Pondok_Indah": "40jt - 75jt",
            "Cilandak": "18jt - 35jt", "Jagakarsa": "9.5jt - 22jt", "Tebet": "23jt - 64jt", "Pesanggrahan": "7jt - 25jt"
        },
        "Jakarta_Pusat": {
            "Tanah_Abang": "41jt - 84jt", "Gambir": "37jt - 60jt", "Menteng": "60jt - 100jt", "Cempaka_Putih": "28jt - 34jt"
        },
        "Jakarta_Barat": {
            "Kebon_Jeruk": "20jt - 68jt", "Kembangan": "16jt - 50jt", "Meruya": "15jt - 27jt", "Kalideres": "10jt - 20jt"
        },
        "Tangerang_Selatan": {
            "BSD_City": "12jt - 25jt", "Bintaro_Jaya": "14jt - 25jt", "Ciputat": "7jt - 12jt", "Pamulang": "5jt - 12jt", "Serpong": "9jt - 13jt"
        },
        "Bekasi": {
            "Bekasi_Barat": "10jt - 15jt", "Bekasi_Selatan": "8jt - 12jt", "Cikarang": "5jt - 11jt", "Cibubur": "7jt - 12jt"
        },
        "Bogor_Depok": {
            "Margonda": "10jt - 20jt", "Sentul_City": "8jt - 15jt", "Rancamaya": "6jt - 12jt", "Cibinong": "3.5jt - 7jt"
        }
    },
    "JAWA_BARAT": {
        "Bandung_Kota": {"Dago": "8jt - 30jt", "Pasteur": "10jt - 40jt", "Lengkong": "12jt - 18jt", "Gedebage": "3.5jt - 7.5jt", "Cibiru": "2.8jt - 7jt"},
        "Luar_Bandung": {"Karawang": "4jt - 8jt", "Cikarang_Pusat": "4.5jt - 9.5jt"}
    },
    "JAWA_TENGAH": {
        "Semarang": {"Simpang_Lima": "25jt - 45jt", "Candi_Elite": "10jt - 15jt", "Tembalang": "3jt - 10jt", "Ngaliyan": "2.5jt - 6.5jt", "Banyumanik": "3.5jt - 7jt"},
        "Solo": {"Slamet_Riyadi": "15jt - 25jt", "Colomadu": "3jt - 7jt"}
    },
    "JAWA_TIMUR": {
        "Surabaya": {"Pusat_Kota": "30jt - 50jt", "Surabaya_Barat": "12.5jt - 25jt", "Pakuwon_City": "15jt - 23jt", "Rungkut": "6jt - 10jt", "Medokan_Ayu": "6jt - 9jt"},
        "Malang": {"Lowokwaru": "5jt - 9.5jt", "Araya": "7jt - 10jt", "Batu": "3jt - 8.5jt"}
    },
    "BALI_DAN_NTB": {
        "Bali": {"Seminyak": "25jt - 60jt", "Canggu": "20jt - 60jt", "Kuta": "20jt - 70jt", "Uluwatu": "20jt - 60jt", "Jimbaran": "15jt - 40jt", "Sanur": "15jt - 50jt", "Ubud": "15jt - 50jt"}
    },
    "SUMATERA": {
        "Medan": {"Medan_Kota": "3.5jt - 5jt", "Polonia": "2.5jt - 38.5jt", "Medan_Area": "3jt - 4.5jt"},
        "Palembang": {"Bukit_Kecil": "5jt - 8.5jt", "Jakabaring": "3.5jt - 7jt"}
    },
    "KALIMANTAN_SULAWESI": {
        "Balikpapan": {"MT_Haryono": "5jt - 9jt", "Sudirman": "8jt - 14jt"},
        "Makassar": {"Pusat_Kota": "4.5jt - 6jt", "Tanjung_Bunga": "8jt - 28jt", "Panakkukang": "2.5jt - 4.2jt"}
    }
}

async def analyze_batch_v62(batch, client):
    prompt = f"""
    Anda adalah Auditor Properti Nasional Indonesia.
    Gunakan DATABASE BENCHMARK berikut untuk menilai kewajaran harga per m2:
    {json.dumps(BENCHMARK_NASIONAL)}

    DATA BATCH: {json.dumps(batch)}

    TUGAS:
    1. Cocokkan lokasi properti dengan Database Benchmark.
    2. Bandingkan 'harga_m2' (dari data) dengan range benchmark wilayah tersebut.
    3. Beri Skor (0-100):
       - 90+ (SUPER HOT): Harga/m2 minimal 20% DI BAWAH batas bawah benchmark wilayah tersebut.
       - 80-89 (HOT DEAL): Harga/m2 di batas bawah atau sedikit di bawah.
       - 60-79 (REGULAR): Harga/m2 masuk dalam range benchmark.
       - <60 (OVERPRICED): Harga/m2 DI ATAS batas atas benchmark.
    4. Analisis Audit: Sebutkan angka benchmark wilayahnya secara eksplisit dalam narasi.

    Hasilkan JSON ARRAY murni:
    [
      {{ "id": "...", "skor_investasi": int, "klasifikasi": "...", "harga_per_m2": int, "analisis_audit": "Audit: [Data vs Benchmark]" }}
    ]
    """

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        res_json = json.loads(completion.choices[0].message.content)
        # Handle if the LLM wraps the list in a key
        if isinstance(res_json, dict):
            for key in res_json:
                if isinstance(res_json[key], list): return res_json[key]
        return res_json
    except Exception as e:
        print(f"\n    [!] AI Error: {e}")
        return None

async def run_ai_analysis():
    load_dotenv()
    input_path = Path('brankas_data/mentah/properti_mentah.json')
    output_path = Path('brankas_data/bersih/properti_analisis.json')
    if not input_path.exists(): return
    with open(input_path, 'r') as f: raw_data = json.load(f)

    print(f"[*] NEURAL ENGINE V62: Memulai Audit Properti Nasional ({len(raw_data)} item)...")
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    analyzed_data = []
    
    for i in range(0, len(raw_data), 10):
        batch = raw_data[i:i+10]
        results = await analyze_batch_v62(batch, client)
        if results:
            results_dict = {res['id']: res for res in results if isinstance(res, dict) and 'id' in res}
            for item in batch:
                res_ai = results_dict.get(item['id'])
                if res_ai:
                    item.update({
                        "skor_investasi": res_ai.get('skor_investasi', 0),
                        "klasifikasi": res_ai.get('klasifikasi', 'REGULAR'),
                        "harga_per_m2": item.get('harga_m2', 0),
                        "analisis_ai": res_ai.get('analisis_audit', "")
                    })
                    analyzed_data.append(item)
        await asyncio.sleep(1)

    with open(output_path, 'w') as f: json.dump(analyzed_data, f, indent=4)
    print(f"\n[SUCCESS] AUDIT NASIONAL SELESAI!")

if __name__ == "__main__":
    asyncio.run(run_ai_analysis())
