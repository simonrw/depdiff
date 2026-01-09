from dataclasses import dataclass
from importlib.metadata import version
from typing import Self

from requests import Session

MODULE_NAME = __name__.split(".")[0]
MODULE_VERSION = version(MODULE_NAME)


@dataclass
class Info:
    url: str
    "URL of package, either the GitHub repo or another URL"

    @classmethod
    def from_info(cls, info: dict) -> Self:
        url_candidates = filter(
            None,
            [
                info.get("home_page"),
                info.get("project_url"),
                info.get("project_urls", {}).get("Homepage"),
            ],
        )

        best = ""
        for candidate in url_candidates:
            if candidate.startswith("https://github.com/"):
                return cls(url=candidate)
            elif best == "":
                best = candidate
                break

        return cls(url=best)


@dataclass
class PackageMetadata:
    info: Info
    "Information about the package"

    urls: list[str]
    "List of URLs the package has, might be the sdist or wheel etc."

    @classmethod
    def from_request(cls, payload: dict) -> Self:
        info = Info.from_info(payload["info"])
        urls = [every["url"] for every in payload["urls"]]
        return cls(info=info, urls=urls)


class MetadataClient:
    def __init__(self):
        self._session = Session()
        self._session.headers.update(
            {
                "User-Agent": f"{MODULE_NAME}/{MODULE_VERSION}",
            }
        )

    def get(self, package: str, version: str) -> PackageMetadata:
        r = self._session.get(f"https://pypi.org/pypi/{package}/{version}/json")
        r.raise_for_status()
        return PackageMetadata.from_request(r.json())
