import random
from scrapy import signals

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
]


class RotateUserAgentMiddleware:
    @classmethod
    def from_crawler(cls, crawler):
        m = cls()
        crawler.signals.connect(m.spider_opened, signal=signals.spider_opened)
        return m

    def process_request(self, request, spider):
        request.headers["User-Agent"] = random.choice(USER_AGENTS)

    def spider_opened(self, spider):
        spider.logger.info(f"RotateUserAgentMiddleware active for {spider.name}")


class ErrorLoggingMiddleware:
    def process_response(self, request, response, spider):
        if response.status >= 400:
            spider.logger.warning(f"HTTP {response.status} — {request.url}")
        return response

    def process_exception(self, request, exception, spider):
        spider.logger.error(f"{type(exception).__name__} — {request.url} — {exception}")
        return None
