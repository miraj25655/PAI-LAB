import csv
import json
import re
from pathlib import Path
from urllib.parse import urlparse


class ValidationPipeline:
    def process_item(self, item, spider):
        if not item.get("url"):
            return None
        return item


class HtmlSaverPipeline:
    def open_spider(self, spider):
        self.html_dir = Path(spider.settings.get("HTML_DIR", "scraped_output/html_pages"))
        self.html_dir.mkdir(parents=True, exist_ok=True)

    def process_item(self, item, spider):
        if item is None:
            return item
        fname = re.sub(r"[^\w\-]", "_", urlparse(item.get("url", "unknown")).netloc + urlparse(item.get("url", "")).path).strip("_")[:180] + ".html"
        (self.html_dir / fname).write_text(item.get("full_html", ""), encoding="utf-8")
        return item


class JsonExportPipeline:
    def open_spider(self, spider):
        out = Path(spider.settings.get("OUTPUT_DIR", "scraped_output"))
        out.mkdir(parents=True, exist_ok=True)
        self.filepath = out / "results.json"
        self.items = []

    def process_item(self, item, spider):
        if item is None:
            return item
        row = dict(item)
        row["full_html_length"] = len(row.get("full_html", ""))
        row["full_html_preview"] = row.get("full_html", "")[:500] + "..."
        row.pop("full_html", None)
        self.items.append(row)
        return item

    def close_spider(self, spider):
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(self.items, f, indent=2, ensure_ascii=False)


class CsvExportPipeline:
    FIELDNAMES = ["url", "page_title", "scraped_at", "meta_desc", "headings_count",
                  "internal_links_count", "external_links_count", "images_count",
                  "phone_numbers", "emails", "html_length"]

    def open_spider(self, spider):
        out = Path(spider.settings.get("OUTPUT_DIR", "scraped_output"))
        out.mkdir(parents=True, exist_ok=True)
        self.file = open(out / "results.csv", "w", newline="", encoding="utf-8")
        self.writer = csv.DictWriter(self.file, fieldnames=self.FIELDNAMES)
        self.writer.writeheader()

    def process_item(self, item, spider):
        if item is None:
            return item
        self.writer.writerow({
            "url":                  item.get("url", ""),
            "page_title":           item.get("page_title", ""),
            "scraped_at":           item.get("scraped_at", ""),
            "meta_desc":            item.get("meta_desc", ""),
            "headings_count":       len(item.get("headings", [])),
            "internal_links_count": len(item.get("internal_links", [])),
            "external_links_count": len(item.get("external_links", [])),
            "images_count":         len(item.get("images", [])),
            "phone_numbers":        " | ".join(item.get("phone_numbers", [])),
            "emails":               " | ".join(item.get("emails", [])),
            "html_length":          len(item.get("full_html", "")),
        })
        return item

    def close_spider(self, spider):
        self.file.close()
