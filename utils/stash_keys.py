import pytest

# Facts about the run (stand, Python, browser, ...) that tests/conftest.py writes to environment.properties.
ALLURE_ENVIRONMENT_KEY = pytest.StashKey[dict[str, str]]()
