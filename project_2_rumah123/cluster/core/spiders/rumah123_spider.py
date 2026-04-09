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
        if not page:
            return

        try:
            # Penjaring Rakus (Greedy Collector)
            # Mencari elemen kartu properti yang umum di Rumah123
            cards = await page.query_selector_all(".ui-organism-intersection-observer-wrapper, .ui-molecule-property-card")
            
            for card in cards:
                try:
                    title_el = await card.query_selector("h2, .ui-molecule-property-card__title")
                    title = await title_el.inner_text() if title_el else "No Title"
                    
                    price_el = await card.query_selector(".ui-molecule-property-card__price, *:has-text('Rp')")
                    price_raw = await price_el.inner_text() if price_el else ""
                    
                    link_el = await card.query_selector("a")
                    raw_url = await link_el.get_attribute("href") if link_el else ""
                    
                    # Tambahan: Ambil Lokasi/Kota
                    location_el = await card.query_selector(".ui-molecule-property-card__location, .ui-atomic-text")
                    location = await location_el.inner_text() if location_el else ""

                    # Tambahan: Ambil Spesifikasi (LT, LB, KT, KM)
                    # Kita ambil seluruh teks di dalam card untuk diproses di pipeline
                    spec_el = await card.query_selector(".ui-molecule-property-card__facilities-list, .ui-organism-property-card__facilities")
                    spec_raw = await spec_el.inner_text() if spec_el else ""
                    
                    if not raw_url: continue

                    # Lempar ke Pipeline agar mesin Scrapy tidak terbeban pengolahan string
                    yield {
                        "judul": title.strip(),
                        "url_asli": f"https://www.rumah123.com{raw_url}" if raw_url.startswith("/") else raw_url,
                        "harga_raw": price_raw.strip(),
                        "lokasi": location.strip(),
                        "spec_raw": spec_raw.strip()
                    }
                except Exception as e:
                    self.logger.error(f"Error parsing card: {e}")
                    continue
        finally:
            await page.close()
