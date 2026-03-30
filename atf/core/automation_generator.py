"""
Stage 4 — Generate Playwright (Python) test artifacts from a test case.

Claude returns a single JSON object with three sections:
  - locators  → locators/<page_name>_page.yaml
  - page_object → pages/<module_name>.py
  - test_script → output/tests/test_tc_NNN.py

One Claude call per test case.
"""
import re
from pathlib import Path

from core.claude_runner import ClaudeRunner
from utils.file_utils import save_text, load_yaml, save_yaml
from utils.locator_store import LocatorStore
from utils import logger


class AutomationGenerator:
    def __init__(self, runner: ClaudeRunner, tests_dir: str,
                 locator_store: LocatorStore, pages_dir: str, base_url: str):
        self.runner        = runner
        self.tests_dir     = tests_dir.rstrip("/")
        self.locator_store = locator_store
        self.pages_dir     = pages_dir.rstrip("/")
        self.base_url      = base_url

    def generate(self, testcase: dict) -> tuple[str, str, str]:
        """
        Returns (test_file_path, locator_file_path, page_file_path).
        """
        tc_id = testcase.get("id", "TC-000")
        logger.stage(f"AUTOMATION GENERATION — {tc_id}")

        page_name = self._infer_page_name(testcase)
        existing_locators = self.locator_store.load_page(page_name)

        result = self.runner.generate_automation(
            testcase, existing_locators, self.base_url
        )

        locator_file = self._write_locators(result.get("locators", {}))
        page_file    = self._write_page_object(result.get("page_object", {}))
        test_file    = self._write_test_script(result.get("test_script", {}), tc_id)

        return test_file, locator_file, page_file

    # ------------------------------------------------------------------
    # Writers
    # ------------------------------------------------------------------

    def _write_locators(self, locators_data: dict) -> str:
        page_name    = locators_data.get("page_name", "unknown")
        page_key     = f"{page_name}_page"
        url_pattern  = locators_data.get("url_pattern", "/")
        elements     = locators_data.get("elements", {})

        existing = self.locator_store.load_page(page_key)
        merged   = existing.get("locators", {})
        for key, val in elements.items():
            if key not in merged:
                merged[key] = {
                    "primary":  val.get("primary", ""),
                    "fallback": val.get("fallback", []),
                    "strategy": val.get("strategy", "css"),
                    "healed":   False,
                }

        data = {
            **existing,
            "page":        page_key,
            "url_pattern": url_pattern,
            "version":     existing.get("version", 1),
            "last_healed": existing.get("last_healed"),
            "locators":    merged,
        }
        self.locator_store.save_page(page_key, data)
        path = self.locator_store.page_path(page_key)
        logger.success(f"Locators saved → {path}")
        return path

    def _write_page_object(self, page_obj: dict) -> str:
        module_name = page_obj.get("module_name", "unknown_page")
        code        = page_obj.get("code", "")
        code        = self._unescape(code)

        path = f"{self.pages_dir}/{module_name}.py"
        # Only write if file doesn't exist — don't overwrite user edits
        if not Path(path).exists():
            save_text(path, code)
            logger.success(f"Page object saved → {path}")
        else:
            logger.info(f"Page object already exists, skipping → {path}")
        return path

    def _write_test_script(self, test_script: dict, tc_id: str) -> str:
        code = test_script.get("code", "")
        code = self._unescape(code)

        filename  = f"test_{tc_id.lower().replace('-', '_')}.py"
        test_file = f"{self.tests_dir}/{filename}"
        save_text(test_file, code)
        logger.success(f"Test script saved → {test_file}")
        return test_file

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _infer_page_name(self, testcase: dict) -> str:
        name = testcase.get("page", "") or testcase.get("name", "unknown")
        slug = re.sub(r"\s+", "_", name.lower().strip())
        if not slug.endswith("_page"):
            slug += "_page"
        return slug

    def _unescape(self, code: str) -> str:
        """Restore escaped newlines/tabs that JSON encoding may produce."""
        return code.replace("\\n", "\n").replace("\\t", "    ")
