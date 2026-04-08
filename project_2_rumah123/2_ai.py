import os
import json
import time
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq

# NEURAL PROCESSOR V53 - DATA-DRIVEN AUDITOR
# Fokus pada data fisik (LT/LB/KT/KM) daripada clickbait judul.

async def analyze_batch_with_groq(batch, client):
    """Menganalisis batch dengan fokus pada perbandingan data fisik."""
    prompt_data = []
    for item in batch:
        prompt_data.append({
            "id": item.get('id'),
            "judul": item.get('judul'), # Tetap dikirim sebagai konteks tambahan
            "harga": int(item.get('harga', 0)),
            "lt": item.get('lt', 0),
            "lb": item.get('lb', 0),
            "kt": item.get('kt', 0),
            "km": item.get('km', 0),
            "lokasi": item.get('lokasi')
        })

    prompt = f"""
    Bertindaklah sebagai Senior Real Estate Data Analyst. Abaikan janji manis atau clickbait di judul jika tidak sesuai dengan data angka.
    
    DATA PROPERTI: {json.dumps(prompt_data)}
    
    Tugas Anda:
    1. Hitung Harga/m2 secara objektif (Harga / LT).
    2. Bandingkan Harga/m2 dengan rata-rata lokasi (Jakarta Selatan: Premium 30jt+, Standard 15-25jt, Murah <15jt).
    3. Berikan 'skor_investasi' (0-100) berdasarkan:
       - 60% : Harga per m2 vs Lokasi.
       - 20% : Rasio LB/LT dan fasilitas KT/KM.
       - 20% : Potensi lokasi.
    4. Klasifikasi: 'SUPER HOT' (skor > 90), 'HOT DEAL' (80-89), 'REGULAR' (60-79), 'OVERPRICED' (<60).
    
    Hasilkan output JSON ARRAY:
    [
      {{
        "id": "hos...",
        "skor_investasi": int,
        "klasifikasi": "...",
        "harga_per_m2": int,
        "analisis_data": "Contoh: Harga 12jt/m2 di Kemang adalah anomali sangat murah, LT luas fasilitas lengkap."
      }}
    ]
    HANYA JSON murni.
    """

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a data-driven property auditor. You ignore clickbait and focus on price-to-area metrics."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        res_text = completion.choices[0].message.content
        res_json = json.loads(res_text)
        if isinstance(res_json, dict):
            for key in res_json:
                if isinstance(res_json[key], list): return res_json[key]
        return res_json
    except Exception as e:
        print(f"\n    [!] Groq Error: {e}")
        return None

async def run_ai_analysis():
    load_dotenv()
    script_dir = Path(__file__).resolve().parent
    input_path = script_dir / 'brankas_data' / 'mentah' / 'properti_mentah.json'
    output_path = script_dir / 'brankas_data' / 'bersih' / 'properti_analisis.json'
    
    if not input_path.exists(): return

    with open(input_path, 'r') as f:
        raw_data = json.load(f)

    print(f"[*] NEURAL ENGINE V53: Memulai Audit Data Objektif ({len(raw_data)} item)...")
    
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    analyzed_data = []
    batch_size = 10
    
    for i in range(0, len(raw_data), batch_size):
        batch = raw_data[i:i+batch_size]
        print(f"    [>] Audit Batch {i//batch_size + 1}...", end="\r")
        results = await analyze_batch_with_groq(batch, client)
        
        if results:
            results_dict = {res['id']: res for res in results if 'id' in res}
            for item in batch:
                res_ai = results_dict.get(item['id'])
                if res_ai:
                    item.update({
                        "skor_investasi": res_ai.get('skor_investasi', 0),
                        "klasifikasi": res_ai.get('klasifikasi', 'REGULAR'),
                        "harga_per_m2": res_ai.get('harga_per_m2', 0),
                        "analisis_ai": res_ai.get('analisis_data', "")
                    })
                    analyzed_data.append(item)
        await asyncio.sleep(0.5)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(analyzed_data, f, indent=4)
    print(f"\n[SUCCESS] AUDIT SELESAI! Data objektif siap diunggah.")

if __name__ == "__main__":
    asyncio.run(run_ai_analysis())
