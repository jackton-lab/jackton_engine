import redis
import json
import os
from pathlib import Path

def collect_to_json():
    """
    Menarik semua hasil dari Redis (yang dikumpulkan oleh Worker)
    dan menyimpannya menjadi satu file properti_mentah.json.
    """
    r = redis.Redis(host=os.getenv('REDIS_HOST', 'redis'), port=6379, db=0)
    
    items = []
    print("[*] FINAL COLLECTOR: Menarik data dari Redis...")
    
    # Ambil semua data dari list rumah123:results
    while True:
        raw_data = r.lpop("rumah123:results")
        if not raw_data:
            break
        items.append(json.loads(raw_data))
    
    if not items:
        print("[!] ERROR: Tidak ada data ditemukan di Redis.")
        return

    # Pastikan folder brankas_data ada
    output_path = Path("/app/brankas_data/mentah/properti_mentah.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(items, f, indent=4)
        
    print(f"[OK] {len(items)} data BERHASIL disatukan di {output_path}")

if __name__ == "__main__":
    collect_to_json()
