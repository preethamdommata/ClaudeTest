import json
import os
import subprocess
from pathlib import Path

import yaml


def load_yaml(path: str) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f) or {}


def save_yaml(path: str, data: dict):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)


def load_json(path: str) -> dict:
    with open(path, "r") as f:
        return json.load(f)


def save_json(path: str, data: dict | list):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def load_text(path: str) -> str:
    with open(path, "r") as f:
        return f.read()


def save_text(path: str, content: str):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        f.write(content)


def open_in_editor(path: str, editor: str = ""):
    editor = editor or os.environ.get("EDITOR", "nano")
    subprocess.call([editor, path])


def ensure_dirs(*paths: str):
    for p in paths:
        Path(p).mkdir(parents=True, exist_ok=True)


def list_files(directory: str, pattern: str = "*") -> list[str]:
    return sorted(str(p) for p in Path(directory).glob(pattern))
