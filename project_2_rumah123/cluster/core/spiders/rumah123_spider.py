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
                    if not raw_url: continue
                    
                    url_prop = f"https://www.rumah123.com{raw_url}" if raw_url.startswith("/") else raw_url
                    id_match = re.search(r"-(hos\d+)/?$", url_prop)
                    prop_id = id_match.group(1) if id_match else url_prop

                    # Tambahan: Ambil Lokasi/Kota
                    location_el = await card.query_selector(".ui-molecule-property-card__location, .ui-atomic-text")
                    location = await location_el.inner_text() if location_el else ""

                    # Tambahan: Ambil Spesifikasi Detail (KT, KM, LT, LB)
                    # Kita cari berdasarkan teks m² dan icon
                    spec_container = await card.query_selector(".ui-molecule-property-card__facilities-list, .ui-organism-property-card__facilities")
                    spec_text = await spec_container.inner_text() if spec_container else ""
                    
                    # Mencari KT/KM via icon (Sesuai logika 1_tarik.py)
                    kt_el = await card.query_selector("use[*|href*='bedroom-icon']")
                    km_el = await card.query_selector("use[*|href*='bathroom-icon']")
                    
                    kt_val = await kt_el.evaluate("el => el.closest('span').innerText") if kt_el else "0"
                    km_val = await km_el.evaluate("el => el.closest('span').innerText") if km_el else "0"

                    if not raw_url: continue

                    # Lempar data yang lebih kaya ke Pipeline
                    yield {
                        "id": prop_id,
                        "judul": title.strip(),
                        "url_properti": url_prop,
                        "harga_raw": price_raw.strip(),
                        "lokasi": location.strip(),
                        "spec_text": spec_text.strip(),
                        "kt_raw": kt_val,
                        "km_raw": km_val
                    }
                except Exception as e:
                    self.logger.error(f"Error parsing card: {e}")
                    continue
        finally:
            await page.close()
