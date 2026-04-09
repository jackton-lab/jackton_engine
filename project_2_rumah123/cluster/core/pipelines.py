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

    def clean_title(self, text):
        # Anti-Clickbait: Hapus simbol berlebihan dan kata sampah
        text = re.sub(r'[!@#$%^&*()_+={}\[\]|\\:;"\'<>,.?/~`]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        # Batasi panjang agar elegan
        return text[:100]

    def parse_specs(self, text):
        lt = lb = kt = km = 0
        text = text.lower()
        # Cari angka di depan satuan spesifik
        m_lt = re.search(r"(\d+)\s*m²\s*lt|lt\s*:?\s*(\d+)", text)
        m_lb = re.search(r"(\d+)\s*m²\s*lb|lb\s*:?\s*(\d+)", text)
        
        # Ekstraksi Kamar (Format umum: 3KT, 2KM atau icon teks)
        m_kt = re.search(r"(\d+)\s*(?:kt|kamar tidur|bed)", text)
        m_km = re.search(r"(\d+)\s*(?:km|kamar mandi|bath)", text)


        if m_lt:
            lt = int(m_lt.group(1) or m_lt.group(2))
        if m_lb:
            lb = int(m_lb.group(1) or m_lb.group(2))

        if m_kt: kt = int(m_kt.group(1))
        if m_km: km = int(m_km.group(1))
        
        return lt, lb, kt, km

    def process_item(self, item, spider):
        if not self.connected:
            return item
            
        # Transformasi Data Kotor Menjadi Emas (ETL)
        price_clean = self.parse_price(item.get("harga_raw", ""))
        if price_clean == 0:
            return item # Buang jika harga tidak valid
            
        # Ekstrak Spek Lengkap
        lt, lb, kt, km = self.parse_specs(item.get("spec_raw", ""))
        
        payload = {
            "judul": self.clean_title(item["judul"]),
            "url_asli": item["url_asli"],
            "harga_total": price_clean,
            "kota": item.get("lokasi", "")[:100],
            "lt": lt,
            "lb": lb,
            "kt": kt,
            "km": km,
            "klasifikasi": "CLUSTER_RAW_DATA", 
        }
        
        # High Volume Upsert (Insert or Update berdasarkan url_asli)
        try:
            self.supabase.table('investments').upsert(payload, on_conflict='url_asli').execute()
        except Exception as e:
            spider.logger.error(f"Supabase Warehouse Error: {e}")

        return item
