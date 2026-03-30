"""
Stage 3 — Author a structured test case from a single scenario.
One Claude call per scenario.
"""
from core.claude_runner import ClaudeRunner
from utils.file_utils import save_json
from utils import logger


class TestCaseAuthor:
    def __init__(self, runner: ClaudeRunner, testcases_dir: str):
        self.runner = runner
        self.testcases_dir = testcases_dir

    def author(self, scenario: dict) -> dict:
        sc_id = scenario.get("id", "SC-000")
        tc_id = sc_id.replace("SC-", "TC-")
        logger.stage(f"TEST CASE AUTHORING — {sc_id}")

        testcase = self.runner.author_testcase(scenario)
        testcase["id"] = tc_id
        testcase["scenario_id"] = sc_id

        path = f"{self.testcases_dir.rstrip('/')}/{tc_id.lower()}.json"
        save_json(path, testcase)
        logger.success(f"Test case saved → {path}")
        return testcase
