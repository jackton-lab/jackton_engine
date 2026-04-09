import redis
import os
import json
from pathlib import Path
from dotenv import load_dotenv

def queue_massive_urls():
    """
    Sistem Otak Pusat yang bertugas mengantrekan target 
    ke mesin Redis. Begitu antrean masuk, ribuan Worker akan
    langsung memperebutkan URL ini secara serentak.
    """
    load_dotenv()
    
    script_dir = Path(__file__).resolve().parent
    # Di Docker, script_dir adalah /app/core, maka parent-nya adalah /app
    config_path = script_dir.parent / 'config.json'
    
    if not config_path.exists():
        print(f"[!] ERROR: config.json tidak ditemukan di {config_path}")
        return

    with open(config_path, 'r') as f:
        config = json.load(f)
        cities = [c['slug'] for c in config.get("cities", [])]
        max_pages = config.get("cluster_max_pages", 100)

    # Retry mechanism untuk koneksi Redis
    import time
    r = None
    for i in range(10):
        try:
            r = redis.Redis(host=os.getenv('REDIS_HOST', 'redis'), port=6379, db=0)
            r.ping()
            print(f"[*] Terhubung ke Redis pada percobaan ke-{i+1}")
            break
        except:
            print(f"[!] Redis belum siap, mencoba lagi dalam 2 detik... ({i+1}/10)")
            time.sleep(2)
    
    if not r:
        print("[!] GAGAL: Tidak bisa terhubung ke Redis.")
        return

    print(f"[*] MASTER ORCHESTRATOR: Menginjeksi {len(cities)} Kota ke Redis...")
    
    for city in cities:
        url_base = f"https://www.rumah123.com/jual/{city}/rumah/?sort=posted-desc"
        # Injeksi Halaman sesuai Config (Volume Industri)
        for i in range(1, max_pages + 1):
            target_url = f"{url_base}&page={i}"
            r.lpush("rumah123:start_urls", target_url)
            
    print(f"[OK] Reservoir URL penuh ({len(cities) * max_pages} URL). Worker siap dieksekusi secara masif.")

if __name__ == "__main__":
    queue_massive_urls()
