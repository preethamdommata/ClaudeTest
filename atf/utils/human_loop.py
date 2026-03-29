"""
Human-in-the-loop gates. Each gate pauses execution, shows the artifact,
and waits for user decision before the pipeline continues.
"""
import sys
from pathlib import Path

from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from utils import logger
from utils.file_utils import load_json, load_yaml, load_text, open_in_editor


class HumanGate:
    def __init__(self, enabled: bool = True, editor: str = ""):
        self.enabled = enabled
        self.editor = editor

    # ------------------------------------------------------------------
    # Public gate methods — one per pipeline stage
    # ------------------------------------------------------------------

    def review_analysis(self, summary_path: str) -> dict:
        """Gate 1: Review app_summary.json after analysis."""
        return self._gate(
            name="ANALYSIS REVIEW",
            description="Review the extracted app summary before scenario generation.",
            artifact_path=summary_path,
            artifact_type="json",
            options={
                "A": "Approve and continue",
                "E": "Open in editor, then continue",
                "R": "Regenerate analysis",
                "Q": "Quit",
            },
        )

    def review_scenarios(self, scenarios_dir: str) -> dict:
        """Gate 2: Review all generated scenarios."""
        files = sorted(Path(scenarios_dir).glob("*.json"))
        self._print_scenario_table(files)
        return self._gate(
            name="SCENARIOS REVIEW",
            description=f"{len(files)} scenario(s) generated. Review before test case authoring.",
            artifact_path=scenarios_dir,
            artifact_type="dir",
            options={
                "A": "Approve all and continue",
                "E": "Edit a specific scenario file",
                "D": "Delete a scenario",
                "R": "Regenerate all scenarios",
                "Q": "Quit",
            },
        )

    def review_testcase(self, tc_path: str, scenario_name: str) -> dict:
        """Gate 3: Review a single generated test case."""
        return self._gate(
            name=f"TEST CASE REVIEW — {scenario_name}",
            description="Review steps, preconditions and expected results.",
            artifact_path=tc_path,
            artifact_type="json",
            options={
                "A": "Approve and continue",
                "E": "Open in editor, then continue",
                "R": "Regenerate this test case",
                "S": "Skip this scenario",
                "Q": "Quit",
            },
        )

    def review_automation(self, test_path: str, scenario_name: str) -> dict:
        """Gate 4: Review generated Playwright test before committing."""
        return self._gate(
            name=f"AUTOMATION REVIEW — {scenario_name}",
            description="Review the generated Playwright test script before git commit.",
            artifact_path=test_path,
            artifact_type="python",
            options={
                "A": "Approve and commit",
                "E": "Open in editor, then commit",
                "R": "Regenerate automation script",
                "S": "Skip (do not commit this scenario)",
                "Q": "Quit",
            },
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _gate(self, name: str, description: str, artifact_path: str,
              artifact_type: str, options: dict) -> dict:
        if not self.enabled:
            return {"action": "A"}

        logger.gate(name)
        logger.console.print(Panel(description, title=f"[gate]{name}[/gate]"))
        logger.console.print(f"\n[info]Artifact:[/info] {artifact_path}")

        self._preview(artifact_path, artifact_type)

        table = Table(show_header=False, box=None, padding=(0, 2))
        for key, label in options.items():
            table.add_row(f"[bold cyan][{key}][/bold cyan]", label)
        logger.console.print(table)

        valid = list(options.keys())
        while True:
            choice = Prompt.ask(
                "\n[gate]Your choice[/gate]",
                choices=valid,
                default="A",
            ).upper()

            if choice == "Q":
                logger.warning("User quit at gate: " + name)
                sys.exit(0)
            elif choice == "E":
                target = self._pick_file(artifact_path, artifact_type)
                open_in_editor(target, self.editor)
                logger.success("File saved. Continuing.")
                return {"action": "A", "edited": True}
            elif choice == "D" and "D" in options:
                target = self._pick_file(artifact_path, artifact_type)
                Path(target).unlink(missing_ok=True)
                logger.warning(f"Deleted: {target}")
                return {"action": "D", "deleted": target}
            else:
                return {"action": choice}

    def _preview(self, path: str, artifact_type: str):
        try:
            if artifact_type == "json":
                data = load_json(path)
                logger.console.print_json(data=data)
            elif artifact_type == "python":
                content = load_text(path)
                logger.console.print(
                    Panel(content, title="Generated Script", style="dim")
                )
            elif artifact_type == "dir":
                pass  # table already printed by caller
        except Exception:
            pass

    def _pick_file(self, path: str, artifact_type: str) -> str:
        if artifact_type == "dir":
            files = sorted(Path(path).glob("*.json"))
            for i, f in enumerate(files):
                logger.console.print(f"  [{i}] {f.name}")
            idx = int(Prompt.ask("Select file number", default="0"))
            return str(files[idx])
        return path

    def _print_scenario_table(self, files: list):
        table = Table(title="Generated Scenarios", show_lines=True)
        table.add_column("#", style="cyan", width=4)
        table.add_column("File", style="white")
        table.add_column("Name", style="green")
        table.add_column("Priority", style="yellow")
        for i, f in enumerate(files):
            try:
                data = load_json(str(f))
                table.add_row(str(i + 1), f.name,
                              data.get("name", "—"),
                              data.get("priority", "—"))
            except Exception:
                table.add_row(str(i + 1), f.name, "—", "—")
        logger.console.print(table)
