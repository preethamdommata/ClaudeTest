"""
ATF Runner — Main orchestrator.

Usage:
  python runner.py --brd docs/requirements.txt --url https://app.com
  python runner.py --brd docs/brd.pdf
  python runner.py --url https://app.com
  python runner.py --resume                        # resume from existing app_summary
  python runner.py --url https://app.com --no-human  # CI mode, no gates
"""
import sys
from pathlib import Path

import click

sys.path.insert(0, str(Path(__file__).parent))

from core.analyzer import Analyzer
from core.scenario_generator import ScenarioGenerator
from core.testcase_author import TestCaseAuthor
from core.automation_generator import AutomationGenerator
from core.claude_runner import ClaudeRunner
from core.git_manager import GitManager
from utils.file_utils import load_yaml, load_json, list_files
from utils.human_loop import HumanGate
from utils.locator_store import LocatorStore
from utils import logger

CONFIG_PATH = "config/settings.yaml"


def load_config() -> dict:
    return load_yaml(CONFIG_PATH)


# ------------------------------------------------------------------
# Pipeline stages
# ------------------------------------------------------------------

def run_analysis(runner, config, brd_path, url, resume) -> dict:
    summary_path = config["paths"]["output"]["root"] + "app_summary.json"

    if resume and Path(summary_path).exists():
        logger.info(f"Resuming — loading existing summary: {summary_path}")
        return load_json(summary_path)

    analyzer = Analyzer(runner, summary_path)

    if brd_path:
        return analyzer.from_brd(brd_path)
    elif url:
        return analyzer.from_url(url)
    else:
        click.echo("Provide --brd or --url", err=True)
        sys.exit(1)


def run_scenario_generation(runner, config, app_summary) -> list:
    gen = ScenarioGenerator(runner, config["paths"]["output"]["scenarios"])
    return gen.generate(app_summary)


def run_testcase_authoring(runner, config, scenario) -> dict:
    author = TestCaseAuthor(runner, config["paths"]["output"]["testcases"])
    return author.author(scenario)


def run_automation_generation(runner, config, testcase,
                               locator_store, base_url) -> tuple[str, str]:
    gen = AutomationGenerator(
        runner,
        config["paths"]["output"]["tests"],
        locator_store,
        base_url,
    )
    return gen.generate(testcase)


# ------------------------------------------------------------------
# Main entry point
# ------------------------------------------------------------------

@click.command()
@click.option("--brd",       "-b", default=None, help="Path to BRD file (txt/pdf/md)")
@click.option("--url",       "-u", default=None, help="URL of the web application")
@click.option("--resume",    "-r", is_flag=True,  help="Resume using existing app_summary.json")
@click.option("--no-human",        is_flag=True,  help="Skip all human gates (CI mode)")
@click.option("--base-url",        default=None,  help="Base URL for Playwright tests (overrides config)")
def main(brd, url, resume, no_human, base_url):
    config = load_config()

    # Override base_url if provided via CLI
    if base_url:
        config["playwright"]["base_url"] = base_url
    elif url and not config["playwright"]["base_url"]:
        config["playwright"]["base_url"] = url

    hl_cfg = config.get("human_loop", {})
    gate   = HumanGate(
        enabled=hl_cfg.get("enabled", True) and not no_human,
        editor=hl_cfg.get("editor", ""),
    )

    runner       = ClaudeRunner(config)
    git_mgr      = GitManager(config)
    locator_store = LocatorStore(config["paths"]["locators"])

    # ==================================================================
    # STAGE 1: ANALYZE
    # ==================================================================
    app_summary = run_analysis(runner, config, brd, url, resume)
    summary_path = config["paths"]["output"]["root"] + "app_summary.json"

    decision = gate.review_analysis(summary_path)
    while decision["action"] == "R":
        app_summary = run_analysis(runner, config, brd, url, resume=False)
        decision = gate.review_analysis(summary_path)

    # ==================================================================
    # STAGE 2: SCENARIO GENERATION
    # ==================================================================
    scenarios = run_scenario_generation(runner, config, app_summary)
    scenarios_dir = config["paths"]["output"]["scenarios"]

    decision = gate.review_scenarios(scenarios_dir)
    while decision["action"] == "R":
        scenarios = run_scenario_generation(runner, config, app_summary)
        decision = gate.review_scenarios(scenarios_dir)

    # Reload scenarios from disk (user may have edited files)
    scenario_files = list_files(scenarios_dir, "*.json")
    scenarios = [load_json(f) for f in scenario_files]
    logger.info(f"Processing {len(scenarios)} scenario(s).")

    # ==================================================================
    # STAGE 3 + 4: PER-SCENARIO LOOP
    # ==================================================================
    for scenario in scenarios:
        sc_id   = scenario.get("id", "SC-???")
        sc_name = scenario.get("name", "unnamed")
        logger.console.rule(f"[bold]Processing: {sc_id} — {sc_name}[/bold]")

        # --- Stage 3: Test Case Authoring ---
        testcase = run_testcase_authoring(runner, config, scenario)
        tc_id    = testcase.get("id", "TC-???")
        tc_path  = f"{config['paths']['output']['testcases']}/{tc_id.lower()}.json"

        decision = gate.review_testcase(tc_path, sc_name)
        while decision["action"] == "R":
            testcase = run_testcase_authoring(runner, config, scenario)
            decision = gate.review_testcase(tc_path, sc_name)

        if decision["action"] == "S":
            logger.warning(f"Skipped: {sc_id}")
            continue

        # Reload in case user edited
        testcase = load_json(tc_path)

        # --- Stage 4: Automation Generation ---
        test_path, locator_path = run_automation_generation(
            runner, config, testcase, locator_store,
            config["playwright"]["base_url"]
        )

        decision = gate.review_automation(test_path, sc_name)
        while decision["action"] == "R":
            test_path, locator_path = run_automation_generation(
                runner, config, testcase, locator_store,
                config["playwright"]["base_url"]
            )
            decision = gate.review_automation(test_path, sc_name)

        if decision["action"] == "S":
            logger.warning(f"Skipped commit for: {sc_id}")
            continue

        # --- Git Commit + Push ---
        files_to_commit = [
            f"{config['paths']['output']['scenarios']}/{sc_id.lower()}.json",
            tc_path,
            test_path,
            locator_path,
        ]
        git_mgr.commit_scenario(sc_id, sc_name, files_to_commit)
        logger.success(f"Committed and pushed: {sc_id}")

    logger.console.rule("[bold green] ATF Pipeline Complete [/bold green]")
    logger.success(
        f"All scenarios processed. Run tests with:\n"
        f"  pytest output/tests/ --html=reports/test_report.html"
    )


if __name__ == "__main__":
    main()
