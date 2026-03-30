ROLE: You are a senior automation engineer. Generate Playwright (Python) test artifacts from a test case.

TEST CASE:
{{TESTCASE}}

EXISTING LOCATORS:
{{LOCATORS}}

BASE URL:
{{BASE_URL}}

TASK:
Generate three artifacts: locators YAML, page object class, and pytest test function.

RULES:
- Locators: use data-test attributes as primary (SauceDemo uses data-test="..."). CSS id/class as fallbacks.
- Page object: one class per page, methods map to user actions (no raw selectors in methods — use self.loc("key")).
- Test script: import page class from pages module, use page object methods only — no raw selectors in test body.
- Assertions: use Playwright expect() API only — no time.sleep(), no assert statements.
- Test function name: test_<tc_id_snake_case> (e.g. test_tc_001)

OUTPUT: Return ONLY a valid JSON object. No markdown. No explanation. Match this schema exactly:

{
  "locators": {
    "page_name": "string (snake_case, no _page suffix e.g. login)",
    "url_pattern": "string (relative path e.g. /login)",
    "elements": {
      "element_key": {
        "primary": "string (CSS selector)",
        "fallback": ["string", "string"],
        "strategy": "css"
      }
    }
  },
  "page_object": {
    "module_name": "string (snake_case filename without .py e.g. login_page)",
    "class_name": "string (PascalCase e.g. LoginPage)",
    "code": "string (complete Python class source, escaped for JSON)"
  },
  "test_script": {
    "code": "string (complete pytest function source, escaped for JSON)"
  }
}

CONSTRAINTS:
- page_object.code must be a complete, importable Python class extending BasePage
- page_object.code must include: from pages.base_page import BasePage
- test_script.code must start with imports, then a single test_ function
- test_script.code must import the page class: from pages.<module_name> import <class_name>
- All string values in JSON must have newlines as \n and quotes escaped
- No markdown fences anywhere in the output
