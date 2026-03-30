"""
Runs a generated test file with pytest and reports the result.
If the test fails, sends the error to Claude for a fix (up to MAX_RETRIES).
Must pass before the scenario is committed.
"""
import subprocess
import sys
from pathlib import Path

from core.claude_runner import ClaudeRunner
from utils.file_utils import load_text, save_text
from utils import logger

MAX_RETRIES = 3
PYTHON = sys.executable


class TestValidator:
    def __init__(self, runner: ClaudeRunner):
        self.runner = runner

    def validate(self, test_file: str, page_file: str) -> bool:
        """
        Run the test. If it fails, ask Claude to fix it and retry.
        Returns True if test passes, False if all retries exhausted.
        """
        logger.stage(f"TEST VALIDATION — {Path(test_file).name}")

        for attempt in range(1, MAX_RETRIES + 1):
            logger.info(f"Running test (attempt {attempt}/{MAX_RETRIES})...")
            passed, output = self._run_pytest(test_file)

            if passed:
                logger.success(f"Test passed on attempt {attempt}.")
                return True

            logger.warning(f"Test failed on attempt {attempt}.")
            logger.console.print(output[-3000:])   # show last 3000 chars of output

            if attempt < MAX_RETRIES:
                logger.info("Asking Claude to fix the test script...")
                self._fix_script(test_file, page_file, output)
            else:
                logger.error(
                    f"Test still failing after {MAX_RETRIES} attempts.\n"
                    f"Fix manually: {test_file}\n"
                    f"Then re-run: ./run.sh --resume --url <url>"
                )

        return False

    # ------------------------------------------------------------------

    def _run_pytest(self, test_file: str) -> tuple[bool, str]:
        result = subprocess.run(
            [PYTHON, "-m", "pytest", test_file, "-v", "--tb=short", "--no-header"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        output = result.stdout + result.stderr
        return result.returncode == 0, output

    def _fix_script(self, test_file: str, page_file: str, error_output: str):
        test_code = load_text(test_file)
        page_code = load_text(page_file) if Path(page_file).exists() else ""

        prompt = self._build_fix_prompt(test_code, page_code, error_output)
        fixed  = self.runner._call_text(prompt, stage="automate")
        fixed  = self._clean_code(fixed)

        if fixed.strip():
            save_text(test_file, fixed)
            logger.info(f"Test script updated with fix → {test_file}")

    def _build_fix_prompt(self, test_code: str, page_code: str,
                          error: str) -> str:
        return f"""ROLE: You are a senior automation engineer fixing a failing Playwright pytest test.

FAILING TEST:
{test_code}

PAGE OBJECT:
{page_code}

PYTEST ERROR OUTPUT:
{error[-2000:]}

TASK:
Fix the test script so it passes. Common issues to check:
- Wrong locator keys (must match what is in the page object / locators YAML)
- Missing imports
- Wrong expect() usage
- Incorrect URL patterns
- Page object method names that don't exist

OUTPUT: Return ONLY the corrected Python test script. No markdown fences. No explanation."""

    def _clean_code(self, raw: str) -> str:
        import re
        cleaned = re.sub(r"^```(?:python)?\s*", "", raw.strip(), flags=re.MULTILINE)
        cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)
        return cleaned
