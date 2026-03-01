import scrapy


class RestaurantPageItem(scrapy.Item):
    url            = scrapy.Field()
    page_title     = scrapy.Field()
    scraped_at     = scrapy.Field()
    full_html      = scrapy.Field()
    internal_links = scrapy.Field()
    external_links = scrapy.Field()
    images         = scrapy.Field()
    headings       = scrapy.Field()
    meta_desc      = scrapy.Field()
    phone_numbers  = scrapy.Field()
    emails         = scrapy.Field()
