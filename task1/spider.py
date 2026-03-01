import re
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

import scrapy
from items import RestaurantPageItem

START_URLS = [
    "https://www.allrecipes.com/recipes/84/healthy-recipes/",
    "https://www.bbcgoodfood.com/recipes/collection/healthy-recipes",
    "https://books.toscrape.com/",
]

MAX_DEPTH = 2
ALLOWED_DOMAINS_OVERRIDE = []


def _extract_domain(url):
    return urlparse(url).netloc.lstrip("www.")


class RestaurantsSpider(scrapy.Spider):
    name = "restaurants"
    allowed_domains = ALLOWED_DOMAINS_OVERRIDE or [_extract_domain(u) for u in START_URLS]
    start_urls = START_URLS
    custom_settings = {"DEPTH_LIMIT": MAX_DEPTH}

    PHONE_RE = re.compile(r"(\+?\d[\d\s\-().]{7,}\d)")
    EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")

    def parse(self, response):
        item = RestaurantPageItem()
        item["url"]        = response.url
        item["page_title"] = response.css("title::text").get("").strip()
        item["scraped_at"] = datetime.now(timezone.utc).isoformat()
        item["full_html"]  = response.text
        item["meta_desc"]  = response.css('meta[name="description"]::attr(content)').get("").strip()
        item["headings"]   = [h.strip() for h in response.css("h1::text, h2::text, h3::text").getall() if h.strip()]

        internal, external = self._extract_links(response)
        item["internal_links"] = internal
        item["external_links"] = external
        item["images"]         = self._extract_images(response)

        page_text = " ".join(response.css("body *::text").getall())
        item["phone_numbers"] = list({m.strip() for m in self.PHONE_RE.findall(page_text)})
        item["emails"]        = list({e.lower() for e in self.EMAIL_RE.findall(page_text)})

        yield item

        for link in internal:
            yield response.follow(link, callback=self.parse)

    def _extract_links(self, response):
        base_domain = _extract_domain(response.url)
        internal, external = [], []
        for href in response.css("a::attr(href)").getall():
            full = urljoin(response.url, href)
            parsed = urlparse(full)
            if not parsed.scheme.startswith("http"):
                continue
            link_domain = parsed.netloc.lstrip("www.")
            if link_domain == base_domain or link_domain in self.allowed_domains:
                if full not in internal:
                    internal.append(full)
            else:
                if full not in external:
                    external.append(full)
        return internal, external

    def _extract_images(self, response):
        images = []
        for img in response.css("img"):
            src = img.attrib.get("src", "") or img.attrib.get("data-src", "")
            if src:
                images.append({
                    "src":    urljoin(response.url, src),
                    "alt":    img.attrib.get("alt", "").strip(),
                    "width":  img.attrib.get("width", ""),
                    "height": img.attrib.get("height", ""),
                })
        return images
