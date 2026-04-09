import scrapy
from scrapy_redis.spiders import RedisSpider
from playwright.async_api import Page
import json
import re

class Rumah123ClusterSpider(RedisSpider):
    name = "rumah123_spider"
    redis_key = "rumah123:start_urls"
    
    # URL diinjeksikan dari Master Orchestrator ke Redis (tidak statis)
    # Master Orchestrator yang akan membuat antrean jutaan URL Halaman.

    def start_requests(self):
        # Override start_requests bawaan Scrapy-Redis agar pakai Playwright
        for url in self.next_requests():
            yield scrapy.Request(
                url.url, 
                meta={
                    "playwright": True, 
                    "playwright_include_page": True,
                    "playwright_page_methods": [
                        # Simulasi baca halaman ala manusia sebelum ekstrak data
                        ("evaluate", "window.scrollBy(0, 1000)"),
                        ("wait_for_timeout", 1500)
                    ]
                },
                callback=self.parse
            )

    async def parse(self, response):
        page: Page = response.meta.get("playwright_page")
        if not page: return

        try:
            # METODE DEWA: AMBIL LANGSUNG DARI PAYLOAD JSON INTERNAL
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            script_tag = soup.find("script", id="__NEXT_DATA__")
            
            if script_tag:
                try:
                    data = json.loads(script_tag.string)
                    listings = data.get("props", {}).get("pageProps", {}).get("initialValue", {}).get("search", {}).get("res", [])
                    
                    if listings:
                        self.logger.info(f"[*] JSON Surgeon: Mengekstrak {len(listings)} data murni...")
                        for item in listings:
                            # Mapping data JSON ke format Pipeline
                            yield {
                                "id": item.get("id"),
                                "judul": item.get("title"),
                                "url_properti": f"https://www.rumah123.com{item.get('url')}",
                                "harga_raw": f"Rp {item.get('prices', [{}])[0].get('value', 0)}",
                                "lokasi": f"{item.get('location', {}).get('district', {}).get('name', '')}, {item.get('location', {}).get('city', {}).get('name', '')}",
                                "spec_text": f"LT {item.get('attributes', {}).get('landSize', 0)} m2 / LB {item.get('attributes', {}).get('builtUpSize', 0)} m2",
                                "kt_raw": str(item.get("attributes", {}).get("bedroom", 0)),
                                "km_raw": str(item.get("attributes", {}).get("bathroom", 0))
                            }
                        return # Selesai jika JSON berhasil
                except Exception as e:
                    self.logger.error(f"JSON Surgeon Error: {e}")

            # FALLBACK: Jika JSON tidak ditemukan, gunakan selector lama (Gotong Royong)
            cards = await page.query_selector_all(".ui-organism-intersection-observer-wrapper, .ui-molecule-property-card, [data-name='ldp-listing-card']")
            # ... (rest of old card logic)
