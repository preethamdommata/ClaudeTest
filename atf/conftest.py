"""
Pytest configuration and shared fixtures for ATF.
"""
import pytest
from playwright.sync_api import Browser, BrowserContext, Page

from utils.file_utils import load_yaml

CONFIG_PATH = "config/settings.yaml"


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "smoke: fast sanity checks"
    )
    config.addinivalue_line(
        "markers", "regression: full regression suite"
    )
    config.addinivalue_line(
        "markers", "negative: negative/error path tests"
    )


@pytest.fixture(scope="session")
def atf_config() -> dict:
    return load_yaml(CONFIG_PATH)


@pytest.fixture(scope="session")
def base_url(atf_config) -> str:
    return atf_config["playwright"]["base_url"]


@pytest.fixture(scope="session")
def browser_instance(playwright, atf_config):
    cfg      = atf_config["playwright"]
    headless = cfg.get("headless", True)
    slow_mo  = cfg.get("slow_mo", 0)
    browser_name = cfg.get("browser", "chromium")

    browser_launcher = getattr(playwright, browser_name)
    browser = browser_launcher.launch(headless=headless, slow_mo=slow_mo)
    yield browser
    browser.close()


@pytest.fixture(scope="function")
def context(browser_instance, atf_config) -> BrowserContext:
    ctx = browser_instance.new_context(
        base_url=atf_config["playwright"]["base_url"],
        viewport={"width": 1280, "height": 720},
    )
    yield ctx
    ctx.close()


@pytest.fixture(scope="function")
def page(context) -> Page:
    pg = context.new_page()
    yield pg
    pg.close()
