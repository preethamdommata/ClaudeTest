"""
Git operations per scenario: stage → commit → push.
Uses GitPython. Operates on the atf/ directory repo.
"""
from pathlib import Path

import git

from utils import logger


class GitManager:
    def __init__(self, config: dict, repo_path: str = "."):
        self.remote  = config["git"]["remote"]
        self.branch  = config["git"]["branch"]
        self.auto_push = config["git"]["auto_push"]
        self.prefix  = config["git"]["commit_prefix"]
        try:
            self.repo = git.Repo(repo_path, search_parent_directories=True)
        except git.InvalidGitRepositoryError:
            logger.warning("No git repo found. Initializing one.")
            self.repo = git.Repo.init(repo_path)

    def commit_scenario(self, scenario_id: str, scenario_name: str,
                        files: list[str]):
        """Stage given files, commit with a structured message, optionally push."""
        if not files:
            logger.warning("No files to commit.")
            return

        existing = [str(Path(f).resolve()) for f in files if Path(f).exists()]
        if not existing:
            logger.warning("None of the listed files exist — skipping commit.")
            return

        self.repo.index.add(existing)

        if not self.repo.index.diff("HEAD") and not self.repo.untracked_files:
            logger.info("Nothing new to commit.")
            return

        msg = f"{self.prefix}({scenario_id}): {scenario_name}"
        self.repo.index.commit(msg)
        logger.success(f"Committed: {msg}")

        if self.auto_push:
            self._push()

    def commit_healed_locator(self, page_name: str, element_name: str,
                               locator_file: str):
        """Dedicated commit for a healed locator."""
        if not Path(locator_file).exists():
            return

        self.repo.index.add([str(Path(locator_file).resolve())])
        msg = f"heal(locator): {page_name}.{element_name}"
        self.repo.index.commit(msg)
        logger.success(f"Healed locator committed: {msg}")

        if self.auto_push:
            self._push()

    def _push(self):
        try:
            origin = self.repo.remote(name=self.remote)
            origin.push(self.branch)
            logger.success(f"Pushed to {self.remote}/{self.branch}")
        except Exception as e:
            logger.warning(f"Push failed (continuing): {e}")
