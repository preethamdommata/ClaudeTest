from rich.console import Console
from rich.theme import Theme

_theme = Theme({
    "info":    "cyan",
    "success": "bold green",
    "warning": "bold yellow",
    "error":   "bold red",
    "stage":   "bold magenta",
    "gate":    "bold blue",
})

console = Console(theme=_theme)


def info(msg: str):
    console.print(f"[info][ATF][/info] {msg}")


def success(msg: str):
    console.print(f"[success][ATF] ✔ {msg}[/success]")


def warning(msg: str):
    console.print(f"[warning][ATF] ⚠ {msg}[/warning]")


def error(msg: str):
    console.print(f"[error][ATF] ✖ {msg}[/error]")


def stage(name: str):
    console.rule(f"[stage] STAGE: {name} [/stage]")


def gate(name: str):
    console.rule(f"[gate] ◆ HUMAN GATE: {name} ◆ [/gate]")
