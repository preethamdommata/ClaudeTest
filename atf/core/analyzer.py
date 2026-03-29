"""
Stage 1 — Analyze BRD text or crawl a URL to produce app_summary.json.
Runs once per project. Output is reused by all downstream stages.
"""
import re
from pathlib import Path

from core.claude_runner import ClaudeRunner
from utils.file_utils import save_json, load_text
from utils import logger


class Analyzer:
    def __init__(self, runner: ClaudeRunner, output_path: str):
        self.runner = runner
        self.output_path = output_path

    def from_brd(self, brd_path: str) -> dict:
        logger.stage("ANALYZE — BRD")
        raw = load_text(brd_path)
        return self._analyze(raw)

    def from_url(self, url: str) -> dict:
        logger.stage("ANALYZE — URL")
        raw = self._crawl(url)
        return self._analyze(raw)

    def from_text(self, text: str) -> dict:
        logger.stage("ANALYZE — TEXT")
        return self._analyze(text)

    # ------------------------------------------------------------------

    def _analyze(self, raw_input: str) -> dict:
        summary = self.runner.analyze(raw_input)
        save_json(self.output_path, summary)
        logger.success(f"App summary saved → {self.output_path}")
        return summary

    def _crawl(self, url: str) -> str:
        """Crawl a URL using Playwright and return visible text content."""
        from playwright.sync_api import sync_playwright

        logger.info(f"Crawling: {url}")
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=30000)

            # Extract visible text + page structure hints
            title   = page.title()
            content = page.evaluate("() => document.body.innerText")
            links   = page.eval_on_selector_all(
                "a[href]", "els => els.map(e => e.innerText + ':' + e.href)"
            )
            forms   = page.eval_on_selector_all(
                "form", "els => els.map(e => e.outerHTML.slice(0, 300))"
            )
            browser.close()

        parts = [
            f"PAGE TITLE: {title}",
            f"URL: {url}",
            "VISIBLE TEXT:",
            content[:4000],
            "LINKS FOUND:",
            "\n".join(links[:30]),
            "FORMS FOUND:",
            "\n".join(forms[:5]),
        ]
        return "\n\n".join(parts)
