import os
from supabase import create_client, Client
import re
import json
from groq import Groq

class SupabaseWarehousePipeline:
    def __init__(self):
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        self.groq_key = os.getenv("GROQ_API_KEY")

        if url and key:
            self.supabase: Client = create_client(url, key)
            self.connected = True
        else:
            self.connected = False

        if self.groq_key:
            self.ai_client = Groq(api_key=self.groq_key)
        else:
            self.ai_client = None

    def analyze_with_ai(self, item):
        if not self.ai_client:
            return "No Analysis", 50

        prompt = f"""
        Analisa data properti berikut:
        Judul: {item['judul']}
        Harga: {item['harga_raw']}
        Lokasi: {item.get('lokasi', 'Unknown')}
        Spek: {item.get('spec_raw', '')}

        Berikan JSON singkat:
        {{
          "clean_title": "Judul profesional tanpa clickbait",
          "investment_score": 0-100,
          "summary": "Analisa singkat max 15 kata"
        }}
        """
        try:
            chat = self.ai_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",
                response_format={"type": "json_object"}
            )
            res = json.loads(chat.choices[0].message.content)
            return res.get("summary", "N/A"), res.get("investment_score", 50), res.get("clean_title", item['judul'])
        except:
            return "Analysis Failed", 50, item['judul']

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
        if not self.connected:
            return item

        price_clean = self.parse_price(item.get("harga_raw", ""))
        if price_clean == 0: return item

        lt, lb, kt, km = self.parse_specs(item.get("spec_raw", ""))

        # PROSES PEMATANGAN AI
        summary, score, clean_title = self.analyze_with_ai(item)

        payload = {
            "judul": clean_title[:255],
            "url_asli": item["url_asli"],
            "harga_total": price_clean,
            "kota": item.get("lokasi", "")[:100],
            "lt": lt, "lb": lb, "kt": kt, "km": km,
            "klasifikasi": f"AI_SCORED: {score}",
            "catatan_ai": summary 
        }

        try:
            self.supabase.table('investments').upsert(payload, on_conflict='url_asli').execute()
        except Exception as e:
            spider.logger.error(f"Supabase Error: {e}")

        return item

