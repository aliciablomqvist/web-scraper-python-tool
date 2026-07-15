import json
from dataclasses import dataclass, field


@dataclass
class SiteConfig:
    key: str
    name: str
    base_url: str
    link_selector: str
    extractor: str = "generic"
    fieldnames: list = None
    pagination: dict = field(default_factory=lambda: {"type": "single_page"})
    render_js: bool = False
    request_delay_range: tuple = (2, 5)
    title_field: str = None

    @property
    def data_dir(self):
        return f"data/{self.key}"

    @property
    def urls_file(self):
        return f"{self.data_dir}/urls.txt"

    @property
    def csv_file(self):
        return f"{self.data_dir}/data.csv"

    @property
    def xlsx_file(self):
        return f"{self.data_dir}/export.xlsx"

    @property
    def pdf_file(self):
        return f"{self.data_dir}/export.pdf"


DEFAULT_FIELDNAMES_GENERIC = [
    "Title", "Description", "Text excerpt", "Extra fields (JSON)", "Source URL",
]


def load_site(path):
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    fieldnames = raw.get("fieldnames")
    if fieldnames is None and raw.get("extractor", "generic") == "generic":
        fieldnames = DEFAULT_FIELDNAMES_GENERIC

    return SiteConfig(
        key=raw["key"],
        name=raw.get("name", raw["key"]),
        base_url=raw["base_url"],
        link_selector=raw["link_selector"],
        extractor=raw.get("extractor", "generic"),
        fieldnames=fieldnames,
        pagination=raw.get("pagination", {"type": "single_page"}),
        render_js=raw.get("render_js", False),
        request_delay_range=tuple(raw.get("request_delay_range", [2, 5])),
        title_field=raw.get("title_field"),
    )
