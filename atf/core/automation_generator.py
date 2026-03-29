"""
Stage 4 — Generate Playwright (Python) test script from a test case.
Also extracts and saves element locators to locators/<page>.yaml.
One Claude call per test case.
"""
import re
from pathlib import Path

from core.claude_runner import ClaudeRunner
from utils.file_utils import save_text, load_yaml
from utils.locator_store import LocatorStore
from utils import logger


class AutomationGenerator:
    def __init__(self, runner: ClaudeRunner, tests_dir: str,
                 locator_store: LocatorStore, base_url: str):
        self.runner        = runner
        self.tests_dir     = tests_dir
        self.locator_store = locator_store
        self.base_url      = base_url

    def generate(self, testcase: dict) -> tuple[str, str]:
        """
        Returns (test_file_path, locator_file_path).
        """
        tc_id = testcase.get("id", "TC-000")
        page_name = self._infer_page_name(testcase)
        logger.stage(f"AUTOMATION GENERATION — {tc_id}")

        # Load existing locators for this page (if any) so Claude reuses them
        existing_locators = self.locator_store.load_page(page_name)

        raw_code = self.runner.generate_automation(
            testcase, existing_locators, self.base_url
        )

        # Strip markdown fences if present
        code = self._clean_code(raw_code)

        # Save test file
        test_file = f"{self.tests_dir}/test_{tc_id.lower().replace('-', '_')}.py"
        save_text(test_file, code)
        logger.success(f"Test script saved → {test_file}")

        # Extract and persist locators from the generated code
        locator_file = self._extract_and_save_locators(
            page_name, code, testcase
        )

        return test_file, locator_file

    # ------------------------------------------------------------------

    def _infer_page_name(self, testcase: dict) -> str:
        name = testcase.get("page", "") or testcase.get("name", "unknown")
        return re.sub(r"\s+", "_", name.lower().strip()) + "_page"

    def _clean_code(self, raw: str) -> str:
        cleaned = re.sub(r"^```(?:python)?\s*", "", raw.strip(), flags=re.MULTILINE)
        cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)
        return cleaned

    def _extract_and_save_locators(self, page_name: str,
                                   code: str, testcase: dict) -> str:
        """
        Parse locator strings from generated code and upsert into locators YAML.
        Looks for patterns like: page.locator("...") / page.get_by_role(...) etc.
        """
        existing = self.locator_store.load_page(page_name)
        locators = existing.get("locators", {})

        # Extract CSS/XPath selectors used in the script
        patterns = [
            r'page\.locator\(["\']([^"\']+)["\']\)',
            r'page\.get_by_test_id\(["\']([^"\']+)["\']\)',
            r'page\.fill\(["\']([^"\']+)["\']',
            r'page\.click\(["\']([^"\']+)["\']',
        ]
        found = set()
        for pat in patterns:
            found.update(re.findall(pat, code))

        for selector in found:
            key = re.sub(r"[^a-z0-9_]", "_", selector.lower().strip("[]#."))
            key = re.sub(r"_+", "_", key).strip("_")[:40]
            if key and key not in locators:
                locators[key] = {
                    "primary":  selector,
                    "fallback": [],
                    "strategy": "css",
                    "healed":   False,
                }

        url_pattern = testcase.get("url", testcase.get("page", "/"))
        self.locator_store.create_page(page_name, url_pattern, locators) \
            if not existing else \
            self.locator_store.save_page(page_name, {
                **existing,
                "locators": locators,
            })

        locator_file = self.locator_store.page_path(page_name)
        logger.success(f"Locators saved → {locator_file}")
        return locator_file
