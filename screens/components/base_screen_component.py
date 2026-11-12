from appium.webdriver.webdriver import WebDriver


class BaseScreenComponent[TParent]:
    """
    Base class for reusable mobile UI components (a tab bar, a toolbar, etc.) embedded into
    different Screen objects. Unlike BaseScreen, it doesn't navigate — it only holds driver for
    locators.

    parent is the Screen object the component is embedded into. It's needed for actions that
    redraw the whole screen (e.g. switching the app language) — such methods wait for the redraw
    to finish and return parent instead of self, so the test keeps working with the same screen
    rather than getting stuck inside the component. Components that don't need that return value
    can leave parent unused — it defaults to None.
    """

    def __init__(self, driver: WebDriver, parent: TParent | None = None) -> None:
        self.driver = driver
        self.parent = parent
