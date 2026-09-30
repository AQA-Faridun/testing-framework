from typing import Self

from playwright.sync_api import Page


class BasePage:
    """
    Base class for all Page objects. PATH is the specific page's path relative to
    DEFAULT_BASE_URL (e.g. "/payments"); subclasses override it, and open() navigates to
    DEFAULT_BASE_URL + PATH. Like components, methods return self for chaining.
    """

    DEFAULT_BASE_URL: str = "http://localhost"
    PATH: str = ""

    def __init__(self, page: Page):
        self.page = page

    def open(self) -> Self:
        self.page.goto(f"{self.DEFAULT_BASE_URL}{self.PATH}")
        return self

    def reload(self) -> Self:
        self.page.reload()
        return self
