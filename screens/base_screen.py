import allure
from appium.webdriver.webdriver import WebDriver


class BaseScreen:
    """
    Base class for all Screen objects of the mobile app (Appium). Unlike a web page, a screen has
    no URL: the test reaches it through the app's own navigation, so there is no open(). Like
    components, methods return self for chaining when the test stays on the same screen.
    """

    def __init__(self, driver: WebDriver) -> None:
        self.driver = driver

    def back(self) -> None:
        """
        Press the system Back button. Returns nothing: which screen comes next depends on the flow,
        so the test creates the Screen object it expects.
        """
        with allure.step(f"Go back from {type(self).__name__}"):
            self.driver.back()
