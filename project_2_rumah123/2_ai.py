import os
import json
import time
from pathlib import Path
from dotenv import load_dotenv

# SDK Imports
from groq import Groq
from openai import OpenAI
from google import genai

def analyze_properti_with_fallback_bs_detector():
    # 1. Setup Path & Load Env
    script_path = Path(__file__).resolve()
    root_dir = script_path.parent.parent
    env_path = root_dir / '.env'
    load_dotenv(dotenv_path=env_path)
    
    input_path = script_path.parent / 'brankas_data' / 'mentah' / 'properti_mentah.json'
    output_path = script_path.parent / 'brankas_data' / 'bersih' / 'properti_analisis.json'
    
    # 2. Define Providers & Models (Update 2026 Models)
    providers = [
        {"name": "Groq", "type": "groq", "model": "llama-3.3-70b-versatile", "key": os.getenv("GROQ_API_KEY")},
        {"name": "SambaNova", "type": "openai_compat", "model": "Meta-Llama-3.1-70B-Instruct", "url": "https://api.sambanova.ai/v1", "key": os.getenv("SAMBANOVA_API_KEY")},
        {"name": "OpenRouter", "type": "openai_compat", "model": "meta-llama/llama-3.1-70b-instruct", "url": "https://openrouter.ai/api/v1", "key": os.getenv("OPENROUTER_API_KEY")},
        {"name": "Gemini", "type": "gemini", "model": "gemini-2.0-flash", "key": os.getenv("GOOGLE_API_KEY")}
    ]

    # 3. Load Raw Data
    if not input_path.exists():
        print(f"[!] ERROR: File mentah tidak ditemukan.")
        return
    with open(input_path, 'r') as f:
        raw_data = json.load(f)

    analyzed_results = []

    # 4. System Prompt: Evaluator dengan "Mathematical BS Detector"
    SYSTEM_INSTRUCTION = """
    Bertindaklah sebagai Senior Property Auditor & Investment Analyst dengan fitur "MATHEMATICAL BS DETECTOR". 
    Tugas Anda adalah membedah apakah listing ini benar-benar peluang emas atau hanya clickbait marketing.

    AUDIT MATEMATIS WAJIB:
    1. Hitung 'harga_per_m2' (Harga Total / Luas Tanah). Jika Luas Tanah (lt) tidak valid atau 0, skor otomatis < 70.
    2. BANDINGKAN klaim di judul dengan angka. Jangan percaya klaim "Murah", "BU", atau "Bawah Appraisal" JIKA harga per m2 masih tergolong mahal atau di atas standar pasar daerah tersebut.

    ATURAN SKORING KETAT:
    - Skor 80-100 (HOT DEAL): SANGAT LANGKA. Wajib memiliki indikator urgensi di judul (BU, Jual Cepat, Turun Harga) DAN tervalidasi secara matematis (Harga per m2 sangat rendah/dibawah pasar daerah).
    - Skor 70-79 (GOOD DEAL): Harga per m2 masuk akal/standar pasar, lokasi strategis (dekat kampus/pusat kota), atau kondisi bangunan sangat premium.
    - Skor < 70 (REGULAR): Klaim judul berlebihan tapi harga per m2 mahal, atau tidak ada informasi LT/LB yang cukup untuk dihitung secara akurat.

    KLASIFIKASI:
    - Jika Skor < 80: Beri label "REGULAR".
    - Jika Skor 80-100: Beri label "HOT DEAL".
    """

    # 5. Fallback Logic Function
    def get_ai_completion(prompt_content, provider):
        p_name = provider["name"]
        p_type = provider["type"]
        p_model = provider["model"]
        p_key = provider["key"]

        if not p_key: return None

        full_prompt = f"{SYSTEM_INSTRUCTION}\n\nDATA UNTUK DIAUDIT:\n{prompt_content}\n\nHasilkan output JSON murni dengan kunci: judul, harga_per_m2 (WAJIB INTEGER MURNI, contoh: 5000000. Jika Luas Tanah 0 isi 0), indikasi_urgensi (array), skor_investasi (int), klasifikasi (string), summary_analis (1 kalimat tajam yang menjelaskan hasil audit matematis Anda)."

        try:
            if p_type == "groq":
                client = Groq(api_key=p_key)
                response = client.chat.completions.create(
                    messages=[{"role": "user", "content": full_prompt}],
                    model=p_model,
                    response_format={"type": "json_object"}
                )
                return json.loads(response.choices[0].message.content)

            elif p_type == "openai_compat":
                client = OpenAI(api_key=p_key, base_url=provider["url"])
                response = client.chat.completions.create(
                    model=p_model,
                    messages=[{"role": "user", "content": full_prompt}]
                )
                content = response.choices[0].message.content
                clean_content = content.replace("```json", "").replace("```", "").strip()
                return json.loads(clean_content)

            elif p_type == "gemini":
                client = genai.Client(api_key=p_key)
                response = client.models.generate_content(
                    model=p_model,
                    contents=full_prompt,
                    config={'response_mime_type': 'application/json'}
                )
                return json.loads(response.text)

        except Exception as e:
            err_str = str(e).lower()
            if "401" in err_str or "402" in err_str:
                print(f"    [!] {p_name}: Masalah Saldo/Key. Lewati.")
            elif "429" in err_str or "rate limit" in err_str or "500" in err_str:
                print(f"    [!] {p_name} Limit/Error. Beralih...")
            else:
                print(f"    [!] Error pada {p_name}: {e}")
            return None

    # 6. Pipeline Execution
    print(f"[*] Memulai Audit Matematis Multi-API ({len(raw_data)} listing)...")
    
    for i, item in enumerate(raw_data):
        print(f"    -> Audit Listing [{i+1}/{len(raw_data)}]: {item.get('judul', 'N/A')[:35]}...")
        
        listing_info = json.dumps(item)
        analysis_done = False
        
        for provider in providers:
            if analysis_done: break
            
            result = get_ai_completion(listing_info, provider)
            if result:
                final_item = {**item, "analisis_ai": result, "provider_used": provider["name"]}
                analyzed_results.append(final_item)
                print(f"       [OK] Audit sukses via {provider['name']} (Skor: {result.get('skor_investasi')}).")
                analysis_done = True
                time.sleep(1) # Jeda tipis
            
        if not analysis_done:
            print(f"       [!] Gagal total memproses listing ini di semua provider.")

    # 7. Save Results
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(analyzed_results, f, indent=4)
    print(f"[SUCCESS] Pipeline Audit Matematis Selesai. Hasil disimpan ke {output_path}")

if __name__ == "__main__":
    analyze_properti_with_fallback_bs_detector()
