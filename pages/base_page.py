from typing import Self

import allure
from playwright.sync_api import Page


class BasePage:
    """
    Base class for all Page objects. PATH is the specific page's path (e.g. "/payments");
    subclasses override it. The browser context gets WEB_BASE_URL from config.Settings as its
    base_url, so open() navigates to PATH resolved against it. Like components, methods return
    self for chaining.
    """

    PATH: str = "/"

    def __init__(self, page: Page) -> None:
        self.page = page

    def open(self) -> Self:
        with allure.step(f"Open page {self.PATH}"):
            self.page.goto(self.PATH)
        return self

    def reload(self) -> Self:
        self.page.reload()
        return self
