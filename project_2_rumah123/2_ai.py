import os
import json
import time
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq

# NEURAL ENGINE V61 - STRICT AUDITOR
# 1. Menggunakan Harga/m2 dari Python (Zero Hallucination).
# 2. Benchmark Area Lengkap.
# 3. Logika Perbandingan Ketat.

async def analyze_batch_v61(batch, client):
    prompt = f"""
    Anda adalah Auditor Properti Senior. DILARANG MENGHITUNG ULANG Harga/m2. Gunakan angka yang sudah disediakan.
    
    BENCHMARK HARGA TANAH (per m2) JAKARTA SELATAN:
    - Kebayoran Baru, Senopati, Dharmawangsa, Pakubuwono: 50jt - 90jt
    - Pondok Indah, Permata Hijau, Mega Kuningan: 40jt - 70jt
    - Kemang, Cipete, Cilandak, Dharmawangsa: 25jt - 45jt
    - Tebet, Pancoran, Mampang, TB Simatupang, Kuningan: 20jt - 35jt
    - Jagakarsa, Pasar Minggu, Lenteng Agung, Ciganjur, Cirendeu: 10jt - 18jt
    - Bintaro, Pesanggrahan: 12jt - 20jt

    DATA BATCH: {json.dumps(batch)}

    INSTRUKSI KETAT:
    1. Ambil 'harga_m2' dari data. 
    2. Bandingkan 'harga_m2' dengan BENCHMARK area yang sesuai.
    3. Beri Skor (0-100):
       - Skor 90+ (SUPER HOT): Harga/m2 minimal 20% DI BAWAH batas bawah benchmark.
       - Skor 80-89 (HOT DEAL): Harga/m2 pas di batas bawah atau sedikit di bawah benchmark.
       - Skor 60-79 (REGULAR): Harga/m2 di tengah range benchmark.
       - Skor <60 (OVERPRICED): Harga/m2 DI ATAS batas atas benchmark.
    4. Analisis Audit: Tulis perbandingan eksplisit. Misal: "Harga 36jt/m2 di TB Simatupang adalah OVERPRICED karena di atas range pasar 20-35jt/m2."

    OUTPUT JSON ARRAY:
    [
      {{
        "id": "...",
        "skor_investasi": int,
        "klasifikasi": "...",
        "analisis_audit": "Audit: [Fakta Angka vs Benchmark]"
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
        res_json = json.loads(completion.choices[0].message.content)
        return res_json.get('results', res_json) if isinstance(res_json, dict) else res_json
    except Exception as e:
        print(f"\n    [!] AI Error: {e}")
        return None

async def run_ai_analysis():
    load_dotenv()
    input_path = Path('brankas_data/mentah/properti_mentah.json')
    output_path = Path('brankas_data/bersih/properti_analisis.json')
    if not input_path.exists(): return
    with open(input_path, 'r') as f: raw_data = json.load(f)

    print(f"[*] NEURAL ENGINE V61: Memulai Audit Ketat...")
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    analyzed_data = []
    
    for i in range(0, len(raw_data), 10):
        batch = raw_data[i:i+10]
        results = await analyze_batch_v61(batch, client)
        if results:
            results_dict = {res['id']: res for res in results if isinstance(res, dict) and 'id' in res}
            for item in batch:
                res_ai = results_dict.get(item['id'])
                if res_ai:
                    item.update({
                        "skor_investasi": res_ai.get('skor_investasi', 0),
                        "klasifikasi": res_ai.get('klasifikasi', 'REGULAR'),
                        "analisis_ai": res_ai.get('analisis_audit', "")
                    })
                    analyzed_data.append(item)
        await asyncio.sleep(1)

    with open(output_path, 'w') as f: json.dump(analyzed_data, f, indent=4)
    print(f"\n[SUCCESS] AUDIT KETAT SELESAI!")

if __name__ == "__main__":
    asyncio.run(run_ai_analysis())
