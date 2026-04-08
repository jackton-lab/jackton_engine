import os
import json
import time
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq

# NEURAL ENGINE V59 - STABLE AUDITOR
# Fokus murni pada Audit Statistik: Harga/m2 vs Rata-rata Pasar.

async def analyze_batch_v59(batch, client):
    """Audit ekonomi berbasis data pasar Jakarta Selatan."""
    prompt = f"""
    Anda adalah Auditor Ekonomi Properti Jakarta Selatan. 
    Auditlah data berikut berdasarkan perbandingan Harga/m2 terhadap pasar lokal.

    REFERENSI PASAR (TANAH m2):
    - Kebayoran Baru/Senopati: 50jt - 80jt
    - Pondok Indah/Kemang: 30jt - 50jt
    - Cilandak/Tebet: 20jt - 30jt
    - Jagakarsa/Pasar Minggu: 10jt - 18jt

    DATA: {json.dumps(batch)}

    INSTRUKSI:
    1. Hitung Harga/m2 (Harga / LT).
    2. Beri skor investasi (0-100) murni dari efisiensi harga vs pasar lokal.
    3. Klasifikasi: 'SUPER HOT', 'HOT DEAL', 'REGULAR', 'OVERPRICED'.
    4. Analisis Audit: Jelaskan fakta angka perbandingan harga tersebut.

    OUTPUT JSON ARRAY:
    [
      {{
        "id": "...",
        "skor_investasi": int,
        "klasifikasi": "...",
        "harga_per_m2": int,
        "analisis_audit": "Fakta Audit: [Angka Perbandingan]"
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

    print(f"[*] NEURAL ENGINE V59: Memulai Audit Ekonomi Stabil...")
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    analyzed_data = []
    
    for i in range(0, len(raw_data), 10):
        batch = raw_data[i:i+10]
        print(f"    [>] Audit Batch {i//10 + 1}...", end="\r")
        results = await analyze_batch_v59(batch, client)
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
    print(f"\n[SUCCESS] AUDIT SELESAI!")

if __name__ == "__main__":
    asyncio.run(run_ai_analysis())
