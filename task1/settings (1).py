BOT_NAME = "restaurant_scraper"
SPIDER_MODULES = ["restaurant_scraper.spiders"]
NEWSPIDER_MODULE = "restaurant_scraper.spiders"

ROBOTSTXT_OBEY = True
DOWNLOAD_DELAY = 1.5
RANDOMIZE_DOWNLOAD_DELAY = True
CONCURRENT_REQUESTS = 8
CONCURRENT_REQUESTS_PER_DOMAIN = 4

AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1
AUTOTHROTTLE_MAX_DELAY = 10
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.0

DEFAULT_REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
}

COOKIES_ENABLED = True
RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 429]

ITEM_PIPELINES = {
    "restaurant_scraper.pipelines.ValidationPipeline": 100,
    "restaurant_scraper.pipelines.HtmlSaverPipeline": 200,
    "restaurant_scraper.pipelines.JsonExportPipeline": 300,
    "restaurant_scraper.pipelines.CsvExportPipeline": 400,
}

OUTPUT_DIR = "scraped_output"
HTML_DIR = "scraped_output/html_pages"
LOG_LEVEL = "INFO"
