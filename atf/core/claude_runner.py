"""
Wraps the Claude CLI binary. No API key needed — uses local `claude` binary.
Each call is stateless: prompt template + injected context = one CLI invocation.
"""
import json
import subprocess
import re
from pathlib import Path
from string import Template

from utils.file_utils import load_text
from utils import logger


class ClaudeRunner:
    def __init__(self, config: dict):
        self.config  = config
        self.binary  = config["claude"]["cli_binary"]
        self.models  = config["claude"]["models"]
        self.limits  = config["claude"]["max_tokens"]
        self.prompts_dir = config["paths"]["prompts"]

    # ------------------------------------------------------------------
    # Public: one method per pipeline stage
    # ------------------------------------------------------------------

    def analyze(self, raw_input: str) -> dict:
        prompt = self._build_prompt("analyzer", {"INPUT": raw_input})
        return self._call_json(prompt, stage="analyze")

    def generate_scenarios(self, app_summary: dict) -> list:
        prompt = self._build_prompt(
            "scenario_gen",
            {"APP_SUMMARY": json.dumps(app_summary, indent=2)},
        )
        result = self._call_json(prompt, stage="scenarios")
        return result if isinstance(result, list) else result.get("scenarios", [])

    def author_testcase(self, scenario: dict) -> dict:
        prompt = self._build_prompt(
            "testcase_author",
            {"SCENARIO": json.dumps(scenario, indent=2)},
        )
        return self._call_json(prompt, stage="testcase")

    def generate_automation(self, testcase: dict, locators: dict,
                            base_url: str) -> dict:
        prompt = self._build_prompt(
            "automation_gen",
            {
                "TESTCASE":  json.dumps(testcase, indent=2),
                "LOCATORS":  json.dumps(locators, indent=2),
                "BASE_URL":  base_url,
            },
        )
        return self._call_json(prompt, stage="automate")

    def heal_locator(self, page_name: str, element_name: str,
                     broken_locator: str, dom_snapshot: str) -> dict:
        prompt = self._build_prompt(
            "healer",
            {
                "PAGE_NAME":       page_name,
                "ELEMENT_NAME":    element_name,
                "BROKEN_LOCATOR":  broken_locator,
                "DOM_SNAPSHOT":    dom_snapshot[:8000],   # cap DOM size
            },
        )
        return self._call_json(prompt, stage="heal")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_prompt(self, template_name: str, variables: dict) -> str:
        path = Path(self.prompts_dir) / f"{template_name}.md"
        template_text = load_text(str(path))
        for key, value in variables.items():
            template_text = template_text.replace(f"{{{{{key}}}}}", value)
        return template_text

    def _call_json(self, prompt: str, stage: str) -> dict | list:
        raw = self._run(prompt, stage)
        return self._parse_json(raw, stage)

    def _call_text(self, prompt: str, stage: str) -> str:
        return self._run(prompt, stage)

    def _run(self, prompt: str, stage: str) -> str:
        model      = self.models.get(stage, "claude-sonnet-4-6")
        max_tokens = self.limits.get(stage, 1000)

        cmd = [
            self.binary,
            "--model",          model,
            "--output-format",  "text",
            "-p",               prompt,
        ]

        logger.info(f"Claude CLI → stage={stage} model={model}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode != 0:
                logger.error(f"Claude CLI error:\n{result.stderr}")
                raise RuntimeError(f"Claude CLI failed at stage '{stage}'")
            return result.stdout.strip()
        except FileNotFoundError:
            raise EnvironmentError(
                f"Claude CLI binary '{self.binary}' not found. "
                "Ensure `claude` is installed and on your PATH."
            )

    def _parse_json(self, raw: str, stage: str) -> dict | list:
        # Strip markdown code fences if present
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
        cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse failed at stage '{stage}': {e}")
            logger.error(f"Raw output:\n{raw[:500]}")
            raise
