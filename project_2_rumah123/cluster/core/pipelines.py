import os
import json
import re
from datetime import datetime
from pathlib import Path

class JsonArchivePipeline:
    def __init__(self):
        self.items = []
        self.seen_ids = set() # Sistem Keamanan Anti-Dobel
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

    def parse_area(self, text):
        lt = lb = 0
        text = text.lower()
        # Mencari pola: 120 m² (LT) atau LT: 120
        # Kadang LT dan LB ada di satu teks panjang
        m_lt = re.search(r"(\d+)\s*m²\s*(?:lt|luas tanah)|lt\s*:?\s*(\d+)", text)
        m_lb = re.search(r"(\d+)\s*m²\s*(?:lb|luas bangunan)|lb\s*:?\s*(\d+)", text)
        
        if m_lt: lt = int(m_lt.group(1) or m_lt.group(2))
        if m_lb: lb = int(m_lb.group(1) or m_lb.group(2))
        
        # Jika belum dapat, cari pola m² pertama dan kedua
        if lt == 0 or lb == 0:
            all_m2 = re.findall(r"(\d+)\s*m²", text)
            if len(all_m2) >= 2:
                lt = int(all_m2[0])
                lb = int(all_m2[1])
            elif len(all_m2) == 1:
                lt = lb = int(all_m2[0])
                
        return lt, lb

    def clean_title(self, text):
        # Anti-Clickbait: Hapus simbol berlebihan (!!!!, ****, $$$$)
        text = re.sub(r'[!@#$%^&*()_+={}\[\]|\\:;"\'<>,.?/~`]', ' ', text)
        # Hapus kata-kata marketing sampah (HANYA MINGGU INI, TURUN HARGA, BU!!)
        marketing_garbage = ["bu!!", "turun harga", "hanya minggu ini", "promo", "hot", "murah", "butuh uang"]
        for word in marketing_garbage:
            text = re.sub(word, "", text, flags=re.IGNORECASE)
        return re.sub(r'\s+', ' ', text).strip()[:100]

    def process_item(self, item, spider):
        # 1. Cek Duplikasi ID
        if item["id"] in self.seen_ids:
            return item
        
        # 2. Parsing Harga
        price_val = self.parse_price(item.get("harga_raw", ""))
        if price_val == 0: return item
        
        # 3. Parsing Luas (LT/LB)
        lt, lb = self.parse_area(item.get("spec_text", ""))
        if lt == 0: return item # Penting: Tanpa LT, AI tidak bisa hitung harga/m2
        
        # 4. Parsing Kamar (KT/KM)
        try:
            kt = int(re.search(r"(\d+)", item.get("kt_raw", "0")).group(1))
            km = int(re.search(r"(\d+)", item.get("km_raw", "0")).group(1))
        except:
            kt = km = 0
        
        # 5. Hitung harga_m2 (Makanan Pokok AI)
        harga_m2 = int(price_val / lt) if lt > 0 else 0
        
        entry = {
            "id": item["id"],
            "judul": self.clean_title(item["judul"]),
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
        self.seen_ids.add(item["id"])
        return item

    def close_spider(self, spider):
        if not self.output_dir.exists():
            self.output_dir.mkdir(parents=True, exist_ok=True)
            
        with open(self.output_file, 'w') as f:
            json.dump(self.items, f, indent=4)
        
        spider.logger.info(f"[*] ARSIP SELESAI: {len(self.items)} data BERKUALITAS disimpan di {self.output_file}")
