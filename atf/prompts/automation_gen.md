ROLE: You are a senior automation engineer. Generate a Playwright (Python) test from a test case.

TEST CASE:
{{TESTCASE}}

EXISTING LOCATORS:
{{LOCATORS}}

BASE URL:
{{BASE_URL}}

TASK:
- Generate a complete pytest + Playwright test function
- Use Page Object pattern: import the page class, call methods (do NOT inline raw locators in the test)
- Use existing locators from EXISTING LOCATORS where available
- Define new locators only when not already present in EXISTING LOCATORS
- Use pytest fixtures: `page` from conftest.py
- Include assertions matching the expected results in test steps
- Handle waits correctly: use `expect(locator)` assertions, not `time.sleep`
- Add a descriptive docstring to the test function

OUTPUT: Return ONLY valid Python code. No markdown fences. No explanation.

RULES:
- Test function name: test_<tc_id_snake_case> (e.g. test_tc_001)
- Import only: pytest, re, from playwright.sync_api import expect
- Import page object: from pages.<page_module> import <PageClass>
- Do not hardcode base_url — use the `base_url` fixture or config
- Each assertion must use Playwright's expect() API
- Use data-testid selectors as primary; CSS id/class as fallback
