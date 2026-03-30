from pages.base_page import BasePage
from playwright.sync_api import Page, expect


class LoginPage(BasePage):

    PAGE_NAME = "login_page"
    URL_PATH = "/"

    def __init__(self, page: Page, base_url: str):
        super().__init__(page, base_url)

    def _loc_safe(self, key: str):
        """Return locator for optional/conditional elements, bypassing the DOM-count
        guard in BasePage.loc(). Use this only with not_to_be_visible() assertions
        where the element may be absent from the DOM entirely.
        """
        entry = self._locators.get(key, {})
        return self.page.locator(entry.get("primary", "nonexistent-selector"))

    def verify_page_elements_visible(self):
        expect(self.loc("username_input")).to_be_visible()
        expect(self.loc("password_input")).to_be_visible()
        expect(self.loc("login_button")).to_be_visible()
        expect(self.loc("login_button")).to_be_enabled()

    def verify_no_error_visible(self):
        expect(self._loc_safe("error_message")).not_to_be_visible()

    def enter_username(self, username: str):
        self.loc("username_input").fill(username)

    def enter_password(self, password: str):
        self.loc("password_input").fill(password)

    def click_login(self):
        self.loc("login_button").click()

    def login(self, username: str, password: str):
        self.enter_username(username)
        self.enter_password(password)
        self.click_login()

    def verify_redirect_to_inventory(self, expected_path: str = "/inventory.html"):
        expect(self.page).to_have_url(self.base_url + expected_path)

    def verify_products_page_title(self, expected_title: str = "Products"):
        expect(self.loc("products_title")).to_have_text(expected_title)

    def verify_inventory_grid_visible(self):
        expect(self.loc("inventory_container")).to_be_visible()

    def verify_cart_icon_visible(self):
        expect(self.loc("shopping_cart")).to_be_visible()

    def verify_no_errors_on_page(self):
        expect(self._loc_safe("error_message")).not_to_be_visible()
