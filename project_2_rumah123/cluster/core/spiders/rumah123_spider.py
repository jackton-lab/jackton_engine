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
        page: Page = response.meta["playwright_page"]
        
        # Penjaring Rakus (Greedy Collector)
        cards = await page.query_selector_all("div[class*='card'], div[class*='listing'], article")
        
        for card in cards:
            title_el = await card.query_selector("h2, h3")
            title = await title_el.inner_text() if title_el else ""
            
            price_el = await card.query_selector("*:has-text('Rp')")
            price_raw = await price_el.inner_text() if price_el else ""
            
            link_el = await card.query_selector("a[href]")
            raw_url = await link_el.get_attribute("href") if link_el else ""
            
            # Lempar ke Pipeline agar mesin Scrapy tidak terbeban pengolahan string
            yield {
                "judul": title.strip(),
                "url_asli": f"https://www.rumah123.com{raw_url}" if raw_url.startswith("/") else raw_url,
                "harga_raw": price_raw.strip(),
                "spesifikasi_raw": await card.inner_text()
            }
            
        await page.close()
