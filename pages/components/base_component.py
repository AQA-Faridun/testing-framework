from playwright.sync_api import Page


class BaseComponent[TParent]:
    """
    Base class for reusable UI components (a sidebar, a toolbar, etc.) embedded into different
    Page objects. Unlike BasePage, it doesn't open or reload the page — it only holds page for
    locators.

    parent is the Page object the component is embedded into. It's needed for actions that
    trigger a reload/relocalization of the whole page (e.g. switching the interface language) —
    such methods wait for the reload to finish and return parent instead of self, so the test
    keeps working with the same page rather than getting stuck inside the component. Components
    that don't need that return value can leave parent unused — it defaults to None.
    """

    def __init__(self, page: Page, parent: TParent | None = None) -> None:
        self.page = page
        self.parent = parent
