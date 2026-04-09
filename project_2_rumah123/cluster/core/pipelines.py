import os
import json
import re
import redis
from datetime import datetime

class RedisResultsPipeline:
    """
    Pipeline ini mengumpulkan hasil dari banyak Worker ke satu 
    list di Redis agar tidak terjadi tabrakan file (overwriting).
    """
    
    def __init__(self):
        self.r = redis.Redis(host=os.getenv('REDIS_HOST', 'redis'), port=6379, db=0)

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

    def parse_area(self, text):
        lt = lb = 0
        text = text.lower()
        m_lt = re.search(r"(\d+)\s*m²\s*(?:lt|luas tanah)|lt\s*:?\s*(\d+)", text)
        m_lb = re.search(r"(\d+)\s*m²\s*(?:lb|luas bangunan)|lb\s*:?\s*(\d+)", text)
        if m_lt: lt = int(m_lt.group(1) or m_lt.group(2))
        if m_lb: lb = int(m_lb.group(1) or m_lb.group(2))
        
        # Fallback jika format teks berbeda
        if lt == 0 or lb == 0:
            all_m2 = re.findall(r"(\d+)\s*m²", text)
            if len(all_m2) >= 2:
                lt = int(all_m2[0]); lb = int(all_m2[1])
            elif len(all_m2) == 1:
                lt = lb = int(all_m2[0])
        return lt, lb

    def process_item(self, item, spider):
        price_val = self.parse_price(item.get("harga_raw", ""))
        lt, lb = self.parse_area(item.get("spec_text", ""))
        
        # Ekstraksi KT/KM dari teks mentah jika icon gagal
        try:
            kt = int(re.search(r"(\d+)", item.get("kt_raw", "0")).group(1))
            km = int(re.search(r"(\d+)", item.get("km_raw", "0")).group(1))
        except:
            kt = km = 0
            
        # Perhitungan harga_m2 (Esensial untuk AI Audit)
        harga_m2 = int(price_val / lt) if lt > 0 else 0
        
        # Format Identik dengan 1_tarik.py (Original Logic)
        entry = {
            "id": item["id"],
            "judul": item["judul"][:100],
            "harga": str(price_val),
            "lokasi": item["lokasi"],
            "lt": lt,
            "lb": lb,
            "kt": kt,
            "km": km,
            "harga_m2": harga_m2,
            "url_properti": item["url_properti"],
            "waktu_tarik": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Kirim ke list pusat di Redis
        self.r.rpush("rumah123:results", json.dumps(entry))
        return item
