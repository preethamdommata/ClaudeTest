"""
Base page object. All generated page classes inherit from this.
Loads locators from YAML — no hardcoded selectors in page classes.
"""
from pathlib import Path

from playwright.sync_api import Page, Locator, expect

from utils.file_utils import load_yaml
from utils import logger


class BasePage:
    # Subclasses must set these
    PAGE_NAME: str = ""
    URL_PATH:  str = "/"

    def __init__(self, page: Page, base_url: str, locators_dir: str = "locators"):
        self.page         = page
        self.base_url     = base_url.rstrip("/")
        self.locators_dir = locators_dir
        self._locators    = self._load_locators()

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def navigate(self):
        url = self.base_url + self.URL_PATH
        logger.info(f"Navigating to: {url}")
        self.page.goto(url, wait_until="domcontentloaded")

    def get_title(self) -> str:
        return self.page.title()

    # ------------------------------------------------------------------
    # Locator resolution
    # ------------------------------------------------------------------

    def loc(self, element_name: str) -> Locator:
        """
        Resolve an element locator by name from the YAML store.
        Tries primary first, then fallbacks in order.
        """
        entry = self._locators.get(element_name)
        if not entry:
            raise KeyError(
                f"[{self.PAGE_NAME}] No locator defined for '{element_name}'. "
                f"Add it to locators/{self.PAGE_NAME}.yaml"
            )

        primary   = entry.get("primary", "")
        fallbacks = entry.get("fallback", [])

        # Try primary
        locator = self.page.locator(primary)
        if locator.count() > 0:
            return locator

        # Try fallbacks
        for fb in fallbacks:
            fb_locator = self.page.locator(fb)
            if fb_locator.count() > 0:
                logger.warning(
                    f"[{self.PAGE_NAME}] Primary locator broken for '{element_name}'. "
                    f"Using fallback: {fb}\n"
                    f"  Run: python healer.py --page {self.PAGE_NAME} "
                    f"--element {element_name} --url <page_url>"
                )
                return fb_locator

        # Nothing worked — raise with healer hint
        raise RuntimeError(
            f"[{self.PAGE_NAME}] All locators broken for '{element_name}'.\n"
            f"  Primary:   {primary}\n"
            f"  Fallbacks: {fallbacks}\n"
            f"  Run:  python healer.py --page {self.PAGE_NAME} "
            f"--element {element_name} --url <page_url>"
        )

    # ------------------------------------------------------------------
    # Common interactions (use self.loc() internally)
    # ------------------------------------------------------------------

    def fill(self, element_name: str, value: str):
        self.loc(element_name).fill(value)

    def click(self, element_name: str):
        self.loc(element_name).click()

    def get_text(self, element_name: str) -> str:
        return self.loc(element_name).inner_text()

    def is_visible(self, element_name: str) -> bool:
        return self.loc(element_name).is_visible()

    def assert_visible(self, element_name: str):
        expect(self.loc(element_name)).to_be_visible()

    def assert_text(self, element_name: str, text: str):
        expect(self.loc(element_name)).to_have_text(text)

    def assert_url_contains(self, path: str):
        expect(self.page).to_have_url(lambda u: path in u)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _load_locators(self) -> dict:
        path = Path(self.locators_dir) / f"{self.PAGE_NAME}.yaml"
        if not path.exists():
            logger.warning(f"No locator file found: {path}")
            return {}
        data = load_yaml(str(path))
        return data.get("locators", {})
