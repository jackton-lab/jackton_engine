import os
import json
import time
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq

# NEURAL ENGINE V56 - MULTI-FACTOR MARKET AUDITOR
# Menilai berdasarkan perbandingan sub-daerah, akses, dan kapasitas parkir.

async def analyze_batch_v56(batch, client):
    """Menganalisis batch dengan Kamus Harga Pasar Jakarta Selatan."""
    prompt = f"""
    Anda adalah Senior Real Estate Appraiser di Jakarta Selatan.
    Gunakan referensi harga pasar tanah per m2 ini sebagai dasar:
    - Kebayoran Baru / Pondok Indah / Senopati: 45jt - 80jt /m2
    - Kemang / Dharmawangsa / Cilandak: 25jt - 40jt /m2
    - Tebet / Pancoran / Mampang: 20jt - 30jt /m2
    - Jagakarsa / Pasar Minggu / Lenteng Agung: 12jt - 18jt /m2
    
    DATA BATCH: {json.dumps(batch)}
    
    Tugas:
    1. Hitung Harga/m2 Properti.
    2. Audit Akses & Fasilitas: 
       - Beri nilai tinggi jika judul/lokasi mengandung "MRT", "Tol", "Dekat Mall".
       - Carport > 1 adalah nilai tambah besar.
    3. Skor Investasi (0-100):
       - Bobot: 40% Harga vs Pasar Sub-Daerah, 30% Akses, 20% Kapasitas Parkir (Carport), 10% Kondisi Fisik (KT/KM).
    4. Klasifikasi: 'SUPER HOT' (>90), 'HOT DEAL' (80-89), 'REGULAR' (60-79), 'OVERPRICED' (<60).
    
    Hasilkan JSON ARRAY:
    [
      {{
        "id": "hos...",
        "skor_investasi": int,
        "klasifikasi": "...",
        "harga_per_m2": int,
        "analisis_audit": "Analisis teknis: Harga 15jt/m2 di Tebet dengan Carport 2 adalah Underpriced, sangat layak audit."
      }}
    ]
    HANYA JSON murni.
    """

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        res_text = completion.choices[0].message.content
        res_json = json.loads(res_text)
        if isinstance(res_json, dict):
            for key in res_json:
                if isinstance(res_json[key], list): return res_json[key]
        return res_json
    except Exception as e:
        print(f"\n    [!] Error: {e}")
        return None

async def run_ai_analysis():
    load_dotenv()
    input_path = Path('brankas_data/mentah/properti_mentah.json')
    output_path = Path('brankas_data/bersih/properti_analisis.json')
    if not input_path.exists(): return
    with open(input_path, 'r') as f: raw_data = json.load(f)

    print(f"[*] NEURAL ENGINE V56: Memulai Audit Pasar Jakarta Selatan...")
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    analyzed_data = []
    batch_size = 10
    
    for i in range(0, len(raw_data), batch_size):
        batch = raw_data[i:i+batch_size]
        print(f"    [>] Audit Market Batch {i//batch_size + 1}...", end="\r")
        results = await analyze_batch_v56(batch, client)
        if results:
            results_dict = {res['id']: res for res in results if 'id' in res}
            for item in batch:
                res_ai = results_dict.get(item['id'])
                if res_ai:
                    item.update({
                        "skor_investasi": res_ai.get('skor_investasi', 0),
                        "klasifikasi": res_ai.get('klasifikasi', 'REGULAR'),
                        "harga_per_m2": res_ai.get('harga_per_m2', 0),
                        "analisis_ai": res_ai.get('analisis_audit', "")
                    })
                    analyzed_data.append(item)
        await asyncio.sleep(1)

    with open(output_path, 'w') as f: json.dump(analyzed_data, f, indent=4)
    print(f"\n[SUCCESS] AUDIT MARKET SELESAI!")

if __name__ == "__main__":
    asyncio.run(run_ai_analysis())
