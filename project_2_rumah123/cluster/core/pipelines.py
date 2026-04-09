import os
from supabase import create_client, Client
import re
from datetime import datetime

class SupabaseWarehousePipeline:
    """
    Data Warehousing Pipeline. 
    Menerima data kotor dari ratusan Worker, membersihkannya, 
    dan menyuntikkannya secara simultan ke Supabase PostgreSQL.
    """
    
    def __init__(self):
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if url and key:
            self.supabase: Client = create_client(url, key)
            self.connected = True
        else:
            self.connected = False
            
    def parse_price(self, price_str):
        if not price_str or "Rp" not in price_str: return 0
        price_str = price_str.split('\n')[0] 
        pattern_unit = r"Rp\s*(\d+(?:[.,]\d+)?)\s*(miliar|juta|jt|m)"
        match_unit = re.search(pattern_unit, price_str, re.IGNORECASE)
        if match_unit:
            val = float(match_unit.group(1).replace(",", "."))
            unit = match_unit.group(2).lower()
            if "miliar" in unit or unit == "m": val *= 1_000_000_000
            elif "juta" in unit or unit == "jt": val *= 1_000_000
            return int(val)
        return 0

    def process_item(self, item, spider):
        if not self.connected:
            return item
            
        # Transformasi Data Kotor Menjadi Emas (ETL)
        price_clean = self.parse_price(item.get("harga_raw", ""))
        if price_clean == 0:
            return item # Buang jika harga tidak valid
            
        payload = {
            "judul": item["judul"][:255],
            "url_asli": item["url_asli"],
            "harga_total": price_clean,
            "kota": item.get("lokasi", "")[:100], # Ambil data lokasi dari spider
            "klasifikasi": "CLUSTER_RAW_DATA", 
        }
        
        # High Volume Upsert (Insert or Update berdasarkan url_asli)
        try:
            self.supabase.table('investments').upsert(payload, on_conflict='url_asli').execute()
        except Exception as e:
            spider.logger.error(f"Supabase Warehouse Error: {e}")

        return item
