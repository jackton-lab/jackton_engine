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
            # STRATEGI GOTONG ROYONG (MULTI-SELECTOR BACKUP)
            # Mencari elemen kartu properti dari berbagai pola class yang pernah ada
            cards = await page.query_selector_all(".ui-organism-intersection-observer-wrapper, .ui-molecule-property-card, [data-name='ldp-listing-card']")
            
            for card in cards:
                try:
                    # Alternatif Selector Judul
                    title_el = await card.query_selector("h2, .ui-molecule-property-card__title, [data-testid='ldp-title']")
                    title = await title_el.inner_text() if title_el else "No Title"
                    
                    # Alternatif Selector Harga
                    price_el = await card.query_selector(".ui-molecule-property-card__price, [data-testid='ldp-text-price'], *:has-text('Rp')")
                    price_raw = await price_el.inner_text() if price_el else ""
                    
                    link_el = await card.query_selector("a[href*='hos'], a[href*='properti']")
                    raw_url = await link_el.get_attribute("href") if link_el else ""
                    if not raw_url: continue
                    
                    url_prop = f"https://www.rumah123.com{raw_url}" if raw_url.startswith("/") else raw_url
                    id_match = re.search(r"-(hos\d+)/?$", url_prop)
                    prop_id = id_match.group(1) if id_match else url_prop

                    # Alternatif Selector Lokasi
                    location_el = await card.query_selector(".ui-molecule-property-card__location, [class*='text-greyText'], .ui-atomic-text")
                    location = await location_el.inner_text() if location_el else ""

                    # Ekstraksi Spesifikasi dengan Logika 'Mancing' (Cari teks m2 atau icon)
                    spec_container = await card.query_selector(".ui-molecule-property-card__facilities-list, [class*='facilities']")
                    spec_text = await spec_container.inner_text() if spec_container else ""
                    
                    # Fallback KT/KM via Icon atau Teks Langsung
                    kt_el = await card.query_selector("use[*|href*='bedroom-icon'], [class*='bedroom']")
                    km_el = await card.query_selector("use[*|href*='bathroom-icon'], [class*='bathroom']")
                    
                    kt_val = "0"
                    km_val = "0"
                    
                    if kt_el:
                        try: kt_val = await kt_el.evaluate("el => el.closest('span').innerText")
                        except: pass
                    if km_el:
                        try: km_val = await km_el.evaluate("el => el.closest('span').innerText")
                        except: pass

                    yield {
                        "id": prop_id, "judul": title.strip(), "url_properti": url_prop,
                        "harga_raw": price_raw.strip(), "lokasi": location.strip(),
                        "spec_text": spec_text.strip(), "kt_raw": kt_val, "km_raw": km_val
                    }
                except Exception as e:
                    continue
        finally:
            await page.close()
