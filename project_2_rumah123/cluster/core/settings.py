BOT_NAME = 'jackton_cluster'
SPIDER_MODULES = ['core.spiders']
NEWSPIDER_MODULE = 'core.spiders'

# ==========================================
# 1. MESSAGE BROKER SETUP (REDIS CLUSTER)
# ==========================================
# Memungkinkan Spider di-pause/resume dan membagi beban ke ratusan Worker
SCHEDULER = "scrapy_redis.scheduler.Scheduler"
DUPEFILTER_CLASS = "scrapy_redis.dupefilter.RFPDupeFilter"
SCHEDULER_PERSIST = False # Matikan persist agar antrean bersih setelah selesai
REDIS_URL = 'redis://redis:6379'

# Matikan Worker jika antrean kosong (5 menit idle)
SCHEDULER_IDLE_BEFORE_CLOSE = 300
CLOSESPIDER_IDLE_TIMEOUT = 300
CLOSESPIDER_TIMEOUT = 3600 # Maksimal 1 jam per sesi agar tidak over-run

# ==========================================
# 2. BEHAVIORAL SIMULATION (STEALTH)
# ==========================================
# Mesin akan beradaptasi secara dinamis dengan kecepatan server.
# Jika server berat, mesin melambat seperti manusia membaca. Jika cepat, ngebut.
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 3.0
AUTOTHROTTLE_MAX_DELAY = 10.0
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0 # 1 Request/detik/IP
RANDOMIZE_DOWNLOAD_DELAY = True

# Custom User-Agents Manager & Politeness
DOWNLOADER_MIDDLEWARES = {
    'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
    'scrapy_user_agents.middlewares.RandomUserAgentMiddleware': 400,
    # Inject Smart Proxy Middleware Here for IP Rotation
}

# ==========================================
# 3. CONCURRENCY LIMITS
# ==========================================
CONCURRENT_REQUESTS = 16 # Tingkatkan jika Proxy Rotator terpasang
CONCURRENT_REQUESTS_PER_DOMAIN = 4
CONCURRENT_REQUESTS_PER_IP = 2

# ==========================================
# 4. HEADLESS BROWSER (PLAYWRIGHT)
# ==========================================
DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"

PLAYWRIGHT_LAUNCH_OPTIONS = {
    "headless": True,
    "args": [
        "--disable-blink-features=AutomationControlled",
        "--no-sandbox"
    ]
}

# ==========================================
# 5. DATA WAREHOUSING (SUPABASE)
# ==========================================
ITEM_PIPELINES = {
    'core.pipelines.SupabaseWarehousePipeline': 300,
}

REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
