import os
import json
import time
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq

# NEURAL ENGINE V57 - THE STATISTICAL AUDITOR
# Fokus murni pada perbandingan harga pasar per sub-daerah. 
# Menghapus asumsi kondisi fisik yang subjektif.

async def analyze_batch_v57(batch, client):
    """Audit ekonomi berbasis data pasar riil Jakarta Selatan."""
    prompt = f"""
    Anda adalah Auditor Ekonomi Properti Jakarta Selatan. 
    Tugas Anda adalah melakukan audit statistik antara data listing dengan rata-rata harga pasar.

    DAFTAR HARGA PASAR TANAH (m2) SEBAGAI REFERENSI:
    - Kebayoran Baru, Senopati, Dharmawangsa: 50jt - 90jt
    - Pondok Indah, Kemang: 30jt - 50jt
    - Cilandak, Tebet, Pancoran: 20jt - 30jt
    - Jagakarsa, Pasar Minggu, Lenteng Agung: 10jt - 18jt

    DATA UNTUK DIAUDIT: {json.dumps(batch)}

    INSTRUKSI AUDIT:
    1. Hitung Harga/m2 secara eksak (Harga / LT).
    2. Bandingkan dengan referensi sub-daerah di atas.
    3. Skor Investasi (0-100): 
       - 100: Sangat Murah (Harga/m2 jauh di bawah pasar).
       - 80: Harga Wajar (Sesuai pasar).
       - <60: Mahal (Overpriced).
    4. Analisis Audit: Berikan fakta perbandingan harga (Contoh: "Harga 15jt/m2 di Cilandak adalah 25% di bawah rata-rata pasar 20jt/m2"). 
    5. JANGAN berasumsi tentang kondisi rumah, kejujuran penjual, atau hal lain yang tidak ada dalam data angka.

    OUTPUT JSON ARRAY:
    [
      {{
        "id": "...",
        "skor_investasi": int,
        "klasifikasi": "SUPER HOT" / "HOT DEAL" / "REGULAR" / "OVERPRICED",
        "harga_per_m2": int,
        "analisis_audit": "Audit Ekonomi: [Fakta Angka]"
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

    print(f"[*] NEURAL ENGINE V57: Memulai Audit Ekonomi Jakarta Selatan...")
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    analyzed_data = []
    
    for i in range(0, len(raw_data), 10):
        batch = raw_data[i:i+10]
        print(f"    [>] Audit Market Batch {i//10 + 1}...", end="\r")
        results = await analyze_batch_v57(batch, client)
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
    print(f"\n[SUCCESS] AUDIT EKONOMI SELESAI!")

if __name__ == "__main__":
    asyncio.run(run_ai_analysis())
