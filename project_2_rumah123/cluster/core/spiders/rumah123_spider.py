import scrapy
from scrapy_redis.spiders import RedisSpider
from playwright.async_api import Page
from bs4 import BeautifulSoup
import json
import re

class Rumah123ClusterSpider(RedisSpider):
    name = "rumah123_spider"
    redis_key = "rumah123:start_urls"

    def start_requests(self):
        for url in self.next_requests():
            yield scrapy.Request(
                url.url, 
                meta={
                    "playwright": True, 
                    "playwright_include_page": True,
                    "playwright_page_methods": [
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
                        return
                except Exception as e:
                    self.logger.error(f"JSON Surgeon Error: {e}")

            # FALLBACK: Jika JSON tidak ditemukan, gunakan selector kartu (Gotong Royong)
            cards = await page.query_selector_all(".ui-organism-intersection-observer-wrapper, .ui-molecule-property-card, [data-name='ldp-listing-card']")
            for card in cards:
                try:
                    title_el = await card.query_selector("h2, .ui-molecule-property-card__title, [data-testid='ldp-title']")
                    title = await title_el.inner_text() if title_el else "No Title"
                    
                    price_el = await card.query_selector(".ui-molecule-property-card__price, [data-testid='ldp-text-price'], *:has-text('Rp')")
                    price_raw = await price_el.inner_text() if price_el else ""
                    
                    link_el = await card.query_selector("a[href*='hos'], a[href*='properti']")
                    raw_url = await link_el.get_attribute("href") if link_el else ""
                    if not raw_url: continue
                    
                    url_prop = f"https://www.rumah123.com{raw_url}" if raw_url.startswith("/") else raw_url
                    id_match = re.search(r"-(hos\d+)/?$", url_prop)
                    prop_id = id_match.group(1) if id_match else url_prop

                    location_el = await card.query_selector(".ui-molecule-property-card__location, [class*='text-greyText'], .ui-atomic-text")
                    location = await location_el.inner_text() if location_el else ""

                    spec_container = await card.query_selector(".ui-molecule-property-card__facilities-list, [class*='facilities']")
                    spec_text = await spec_container.inner_text() if spec_container else ""
                    
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
                except:
                    continue
        finally:
            await page.close()
