import os
import json
import time
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from google import genai

# NEURAL PROCESSOR V50 - GENAI SDK VERSION
# Menggunakan SDK google.genai yang terbaru untuk performa maksimal

async def analyze_batch_with_retry(batch, client, retries=3):
    """Menganalisis batch dengan logika retry jika kena rate limit."""
    prompt_data = []
    for item in batch:
        prompt_data.append({
            "id": item.get('id'),
            "judul": item.get('judul'),
            "harga": int(item.get('harga', 0)),
            "lt": item.get('lt', 0),
            "lb": item.get('lb', 0),
            "lokasi": item.get('lokasi')
        })

    prompt = f"""
    Bertindaklah sebagai Senior Property Auditor. Audit data batch properti berikut dari Rumah123.
    DATA: {json.dumps(prompt_data)}
    
    Untuk SETIAP item, berikan analisis dalam format JSON ARRAY:
    [
      {{
        "id": "hos...",
        "skor_investasi": 0-100,
        "klasifikasi": "HOT DEAL" / "REGULAR",
        "harga_per_m2": int,
        "analisis_singkat": "1 kalimat tajam"
      }},
      ...
    ]
    HANYA keluarkan JSON, jangan ada teks lain.
    """

    for attempt in range(retries):
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config={'response_mime_type': 'application/json'}
            )
            # Karena mime_type json, response.text harusnya sudah JSON murni
            return json.loads(response.text)
        except Exception as e:
            wait_time = (attempt + 1) * 15 
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                print(f"\n    [!] Rate Limit! Menunggu {wait_time} detik (Attempt {attempt+1}/{retries})...")
                await asyncio.sleep(wait_time)
            else:
                print(f"\n    [!] Error: {e}")
                break
    return None

async def run_ai_analysis():
    load_dotenv()
    script_dir = Path(__file__).resolve().parent
    input_path = script_dir / 'brankas_data' / 'mentah' / 'properti_mentah.json'
    output_path = script_dir / 'brankas_data' / 'bersih' / 'properti_analisis.json'
    
    if not input_path.exists():
        print("[!] Data mentah tidak ditemukan.")
        return

    with open(input_path, 'r') as f:
        raw_data = json.load(f)

    print(f"[*] NEURAL PROCESSOR V50: Memulai analisis {len(raw_data)} data...")
    
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("[!] GOOGLE_API_KEY tidak ditemukan di .env")
        return
        
    client = genai.Client(api_key=api_key)

    analyzed_data = []
    batch_size = 5 # Batch kecil untuk free tier agar tidak kena limit besar
    
    for i in range(0, len(raw_data), batch_size):
        batch = raw_data[i:i+batch_size]
        print(f"    [>] Memproses Batch {i//batch_size + 1} / {-(len(raw_data)//-batch_size)}...", end="\r")
        
        results = await analyze_batch_with_retry(batch, client)
        
        if results:
            results_dict = {res['id']: res for res in results if 'id' in res}
            for item in batch:
                res_ai = results_dict.get(item['id'])
                if res_ai:
                    item.update({
                        "skor_investasi": res_ai.get('skor_investasi', 0),
                        "klasifikasi": res_ai.get('klasifikasi', 'REGULAR'),
                        "harga_per_m2": res_ai.get('harga_per_m2', 0),
                        "analisis_ai": res_ai.get('analisis_singkat', "")
                    })
                    analyzed_data.append(item)
        
        await asyncio.sleep(2)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(analyzed_data, f, indent=4)
        
    print(f"\n[SUCCESS] ANALISIS SELESAI! {len(analyzed_data)} Data siap dikirim ke Supabase.")

if __name__ == "__main__":
    asyncio.run(run_ai_analysis())
