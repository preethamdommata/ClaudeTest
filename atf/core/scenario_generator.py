"""
Stage 2 — Generate test scenarios from app_summary.json.
One Claude call produces all scenario stubs; saved individually.
"""
import re
from pathlib import Path

from core.claude_runner import ClaudeRunner
from utils.file_utils import save_json
from utils import logger


class ScenarioGenerator:
    def __init__(self, runner: ClaudeRunner, scenarios_dir: str):
        self.runner = runner
        self.scenarios_dir = scenarios_dir

    def generate(self, app_summary: dict) -> list[dict]:
        logger.stage("SCENARIO GENERATION")
        scenarios = self.runner.generate_scenarios(app_summary)

        saved = []
        for i, sc in enumerate(scenarios, start=1):
            sc_id = f"SC-{i:03d}"
            sc["id"] = sc_id
            path = f"{self.scenarios_dir.rstrip('/')}/{sc_id.lower()}.json"
            save_json(path, sc)
            logger.info(f"Saved scenario: {path}")
            saved.append(sc)

        logger.success(f"Generated {len(saved)} scenario(s).")
        return saved
