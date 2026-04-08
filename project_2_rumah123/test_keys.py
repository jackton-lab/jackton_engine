import os
from dotenv import load_dotenv
import google.generativeai as genai
from supabase import create_client

def test_connections():
    load_dotenv()
    print("[*] Mengetes Koneksi...")
    
    # 1. Test Gemini
    api_key = os.getenv("GOOGLE_API_KEY")
    if api_key:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content("test")
            print("[OK] Koneksi Gemini Berhasil!")
        except Exception as e:
            print(f"[!] Gagal Koneksi Gemini: {e}")
    else:
        print("[!] GOOGLE_API_KEY tidak ditemukan.")

    # 2. Test Supabase
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if url and key:
        try:
            supabase = create_client(url, key)
            # Coba fetch 1 baris dari tabel investments
            supabase.table('investments').select("*").limit(1).execute()
            print("[OK] Koneksi Supabase Berhasil!")
        except Exception as e:
            print(f"[!] Gagal Koneksi Supabase: {e}")
    else:
        print("[!] SUPABASE_URL atau SUPABASE_KEY tidak ditemukan.")

if __name__ == "__main__":
    test_connections()
