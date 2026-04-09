import os
import json
import re
import redis
from datetime import datetime

class RedisResultsPipeline:
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
        # Logika ekstraksi Rumah123 modern: LT biasanya di kiri, LB di kanan atau ada label m2
        # Contoh: "189 m² / 250 m²"
        m2_matches = re.findall(r"(\d+)\s*m²", text)
        if len(m2_matches) >= 2:
            lt = int(m2_matches[0]) # Angka m2 pertama biasanya LT
            lb = int(m2_matches[1]) # Angka m2 kedua biasanya LB
        elif len(m2_matches) == 1:
            lt = lb = int(m2_matches[0])
            
        # Jika ada label eksplisit, timpa datanya
        m_lt = re.search(r"lt\s*:?\s*(\d+)", text)
        m_lb = re.search(r"lb\s*:?\s*(\d+)", text)
        if m_lt: lt = int(m_lt.group(1))
        if m_lb: lb = int(m_lb.group(1))
        
        return lt, lb

    def process_item(self, item, spider):
        price_val = self.parse_price(item.get("harga_raw", ""))
        lt, lb = self.parse_area(item.get("spec_text", ""))
        
        # LOGIKA ANTI-SAMPAH: Jika harga 0 atau LT 0, jangan masukkan ke database
        if price_val == 0 or lt == 0:
            spider.logger.warning(f"Skipping item {item['id']} due to missing price or area.")
            return item

        # Ekstraksi KT/KM (Kamar Tidur / Kamar Mandi)
        try:
            kt = int(re.search(r"(\d+)", item.get("kt_raw", "0")).group(1))
            km = int(re.search(r"(\d+)", item.get("km_raw", "0")).group(1))
        except:
            kt = km = 0
            
        # Hitung harga_m2 sesuai contoh Bapak (Integer)
        harga_m2 = int(price_val / lt) if lt > 0 else 0
        
        # STRUKTUR IDENTIK DENGAN CONTOH BAPAK
        entry = {
            "id": item["id"],                     # Contoh: "hos40440919"
            "judul": item["judul"][:255],         # Judul lengkap
            "harga": str(price_val),             # String angka: "3490000000"
            "lokasi": item["lokasi"],             # Contoh: "Galaxy, Bekasi"
            "lt": lt,                             # Integer: 189
            "lb": lb,                             # Integer: 250
            "kt": kt,                             # Integer: 5
            "km": km,                             # Integer: 3
            "harga_m2": harga_m2,                 # Integer: 18465608
            "url_properti": item["url_properti"], # URL lengkap
            "waktu_tarik": datetime.now().strftime('%Y-%m-%d %H:%M:%S') # Format contoh
        }
        
        self.r.rpush("rumah123:results", json.dumps(entry))
        return item
