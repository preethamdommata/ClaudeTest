"""
ATF Healer — Standalone CLI tool.

Called EXPLICITLY by the user when locators are broken.
NOT part of the generation or test execution workflow.

Usage:
  python healer.py --page login_page --element email_input --url https://app.com/login
  python healer.py --page login_page --url https://app.com/login   # heal ALL on page
  python healer.py --scan --url https://app.com/login              # detect broken locators
"""
import sys
from pathlib import Path

import click
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
from rich.console import Console
from rich.table import Table

# Ensure imports work from project root
sys.path.insert(0, str(Path(__file__).parent))

from core.claude_runner import ClaudeRunner
from core.git_manager import GitManager
from utils.file_utils import load_yaml
from utils.locator_store import LocatorStore
from utils import logger

console = Console()
CONFIG_PATH = "config/settings.yaml"


def load_config() -> dict:
    return load_yaml(CONFIG_PATH)


# ------------------------------------------------------------------
# Playwright helpers
# ------------------------------------------------------------------

def get_dom_snapshot(url: str, headless: bool = False) -> str:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=headless)
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        dom = page.content()
        browser.close()
    # Return a trimmed version — healer prompt caps at 8000 chars
    return dom[:10000]


def check_locator_alive(url: str, selector: str, headless: bool = False) -> bool:
    """Return True if the primary locator resolves to at least one element."""
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=headless)
            page = browser.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            count = page.locator(selector).count()
            browser.close()
        return count > 0
    except Exception:
        return False


def try_fallbacks(url: str, fallbacks: list[str],
                  headless: bool = False) -> str | None:
    """Return the first fallback selector that resolves on the page."""
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=headless)
            page = browser.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            for fb in fallbacks:
                try:
                    if page.locator(fb).count() > 0:
                        browser.close()
                        return fb
                except Exception:
                    continue
            browser.close()
    except Exception:
        pass
    return None


# ------------------------------------------------------------------
# Core healing logic
# ------------------------------------------------------------------

def heal_element(page_name: str, element_name: str, url: str,
                 store: LocatorStore, runner: ClaudeRunner,
                 git_mgr: GitManager, config: dict):
    """Heal a single element locator."""
    locator_data = store.get_locator(page_name, element_name)
    if not locator_data:
        logger.error(f"No locator found for '{element_name}' on '{page_name}'")
        return

    primary   = locator_data.get("primary", "")
    fallbacks = locator_data.get("fallback", [])
    headless  = config["playwright"]["headless"]

    console.rule(f"[bold cyan]Healing: {page_name}.{element_name}[/bold cyan]")
    logger.info(f"Current primary locator: {primary}")

    # Step 1: Check if primary still works
    if check_locator_alive(url, primary, headless):
        logger.success("Primary locator is still alive — no healing needed.")
        return

    logger.warning("Primary locator is broken. Trying fallbacks...")

    # Step 2: Try fallbacks before calling Claude
    working_fallback = try_fallbacks(url, fallbacks, headless)
    if working_fallback:
        logger.success(f"Fallback works: {working_fallback}")
        _apply_heal(page_name, element_name, primary,
                    working_fallback, fallbacks, store, git_mgr)
        return

    # Step 3: All fallbacks exhausted — ask Claude to find new locator
    logger.warning("All fallbacks broken. Asking Claude to find new locator...")
    dom_snapshot = get_dom_snapshot(url, headless)

    result = runner.heal_locator(
        page_name, element_name, primary, dom_snapshot
    )

    new_primary   = result.get("primary", "")
    new_fallbacks = result.get("fallbacks", [])

    if not new_primary:
        logger.error("Claude could not find a new locator. Manual fix required.")
        return

    # Step 4: Verify Claude's suggestion works
    if not check_locator_alive(url, new_primary, headless):
        logger.error(f"Claude suggestion also failed: {new_primary}")
        return

    logger.success(f"New locator verified: {new_primary}")
    _apply_heal(page_name, element_name, primary,
                new_primary, new_fallbacks, store, git_mgr)


def _apply_heal(page_name: str, element_name: str, old_primary: str,
                new_primary: str, new_fallbacks: list,
                store: LocatorStore, git_mgr: GitManager):
    store.update_locator(page_name, element_name, new_primary, new_fallbacks)
    store.log_healing(
        page_name, element_name, old_primary, new_primary,
        report_path="reports/healing_log.json"
    )
    logger.success(f"Locator updated: {old_primary}  →  {new_primary}")

    locator_file = store.page_path(page_name)
    git_mgr.commit_healed_locator(page_name, element_name, locator_file)


# ------------------------------------------------------------------
# CLI entry point
# ------------------------------------------------------------------

@click.command()
@click.option("--page",    "-p", default=None, help="Page name (e.g. login_page)")
@click.option("--element", "-e", default=None, help="Element name to heal. Omit to heal all on page.")
@click.option("--url",     "-u", required=True, help="URL of the page to inspect")
@click.option("--scan",    "-s", is_flag=True,  help="Scan all locators on a page and report broken ones")
def main(page, element, url, scan):
    config    = load_config()
    store     = LocatorStore(config["paths"]["locators"])
    runner    = ClaudeRunner(config)
    git_mgr   = GitManager(config)

    if scan:
        _scan_mode(url, page, store, config)
        return

    if not page:
        logger.error("--page is required unless using --scan")
        sys.exit(1)

    if element:
        # Heal a single element
        heal_element(page, element, url, store, runner, git_mgr, config)
    else:
        # Heal all elements on the page
        page_data = store.load_page(page)
        if not page_data:
            logger.error(f"No locator file found for page: {page}")
            sys.exit(1)
        for elem_name in page_data.get("locators", {}):
            heal_element(page, elem_name, url, store, runner, git_mgr, config)


def _scan_mode(url: str, page_name: str | None,
               store: LocatorStore, config: dict):
    """Scan locators and report which are broken — no healing."""
    headless = config["playwright"]["headless"]
    pages = [page_name] if page_name else store.list_pages()

    table = Table(title="Locator Health Scan", show_lines=True)
    table.add_column("Page",     style="cyan")
    table.add_column("Element",  style="white")
    table.add_column("Locator",  style="dim")
    table.add_column("Status",   style="bold")

    for pg in pages:
        data = store.load_page(pg)
        for elem, info in data.get("locators", {}).items():
            primary = info.get("primary", "")
            alive   = check_locator_alive(url, primary, headless)
            status  = "[green]OK[/green]" if alive else "[red]BROKEN[/red]"
            table.add_row(pg, elem, primary, status)

    console.print(table)
    console.print(
        "\n[bold]To heal broken locators run:[/bold]\n"
        "  python healer.py --page <page_name> --url <url>"
    )


if __name__ == "__main__":
    main()
