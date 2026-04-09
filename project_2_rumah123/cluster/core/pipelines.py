import os
import json
import re
from datetime import datetime
from pathlib import Path

class JsonArchivePipeline:
    """
    Pipeline Akhir: Tidak kirim ke DB, tapi kumpulkan data 
    dan simpan ke brankas_data/mentah/properti_mentah.json 
    agar bisa diolah oleh 2_ai.py selanjutnya.
    """
    
    def __init__(self):
        self.items = []
        # Gunakan path absolut agar aman di Docker
        self.output_dir = Path("/app/brankas_data/mentah")
        self.output_file = self.output_dir / "properti_mentah.json"

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

    def parse_specs(self, text):
        lt = lb = kt = km = 0
        text = text.lower()
        m_lt = re.search(r"(\d+)\s*m²\s*lt|lt\s*:?\s*(\d+)", text)
        m_lb = re.search(r"(\d+)\s*m²\s*lb|lb\s*:?\s*(\d+)", text)
        m_kt = re.search(r"(\d+)\s*(?:kt|kamar tidur|bed)", text)
        m_km = re.search(r"(\d+)\s*(?:km|kamar mandi|bath)", text)
        if m_lt: lt = int(m_lt.group(1) or m_lt.group(2))
        if m_lb: lb = int(m_lb.group(1) or m_lb.group(2))
        if m_kt: kt = int(m_kt.group(1))
        if m_km: km = int(m_km.group(1))
        return lt, lb, kt, km

    def process_item(self, item, spider):
        price_val = self.parse_price(item.get("harga_raw", ""))
        lt, lb, kt, km = self.parse_specs(item.get("spec_raw", ""))
        
        # Hitung harga_m2 (Kunci Penting untuk Audit AI di 2_ai.py)
        harga_m2 = int(price_val / lt) if lt > 0 else 0
        
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
        
        self.items.append(entry)
        return item

    def close_spider(self, spider):
        """Simpan ke file saat semua worker selesai"""
        if not self.output_dir.exists():
            self.output_dir.mkdir(parents=True, exist_ok=True)
            
        with open(self.output_file, 'w') as f:
            json.dump(self.items, f, indent=4)
        
        spider.logger.info(f"[*] ARSIP SELESAI: {len(self.items)} data mentah disimpan di {self.output_file}")
