import os
import json
from pathlib import Path
from dotenv import load_dotenv

def send_notifications():
    """
    Placeholder untuk mengirim notifikasi (WhatsApp/Email/Telegram)
    dari hasil analisis terbaru yang berlabel 'HOT DEAL'.
    """
    load_dotenv()
    
    script_dir = Path(__file__).resolve().parent
    input_path = script_dir / 'brankas_data' / 'bersih' / 'properti_analisis.json'
    
    if not input_path.exists():
        print(f"[!] ERROR: File {input_path} tidak ditemukan.")
        return

    with open(input_path, 'r') as f:
        data = json.load(f)

    hot_deals = [item for item in data if item.get('analisis_ai', {}).get('klasifikasi') == 'HOT DEAL']

    if not hot_deals:
        print("[*] Tidak ada HOT DEAL baru untuk dikirim hari ini.")
        return

    print(f"[*] Menemukan {len(hot_deals)} HOT DEAL. Menyiapkan pengiriman...")
    
    for deal in hot_deals:
        # Implementasi pengiriman di sini (contoh: Telegram API atau Email)
        print(f"    -> [READY TO SEND] {deal.get('judul')} - Skor: {deal.get('analisis_ai', {}).get('skor_investasi')}")

if __name__ == "__main__":
    send_notifications()
