"""
CRUD operations for locator YAML files.
Each page has its own YAML under locators/<page_name>.yaml
"""
from datetime import datetime
from pathlib import Path

from utils.file_utils import load_yaml, save_yaml, load_json, save_json


REGISTRY_PATH = "locators/_registry.yaml"


class LocatorStore:
    def __init__(self, locators_dir: str = "locators"):
        self.locators_dir = locators_dir
        Path(locators_dir).mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Page locator file operations
    # ------------------------------------------------------------------

    def page_path(self, page_name: str) -> str:
        return f"{self.locators_dir}/{page_name}.yaml"

    def load_page(self, page_name: str) -> dict:
        path = self.page_path(page_name)
        if not Path(path).exists():
            return {}
        return load_yaml(path)

    def save_page(self, page_name: str, data: dict):
        save_yaml(self.page_path(page_name), data)
        self._update_registry(page_name, data)

    def create_page(self, page_name: str, url_pattern: str, locators: dict) -> dict:
        """Create a new locator file for a page."""
        data = {
            "page": page_name,
            "url_pattern": url_pattern,
            "version": 1,
            "last_healed": None,
            "locators": locators,
        }
        self.save_page(page_name, data)
        return data

    def get_locator(self, page_name: str, element_name: str) -> dict | None:
        data = self.load_page(page_name)
        return data.get("locators", {}).get(element_name)

    def update_locator(self, page_name: str, element_name: str,
                       primary: str, fallbacks: list[str]):
        """Update a single locator — used by healer."""
        data = self.load_page(page_name)
        if not data:
            raise FileNotFoundError(f"No locator file for page: {page_name}")

        data["locators"][element_name]["primary"] = primary
        data["locators"][element_name]["fallback"] = fallbacks
        data["locators"][element_name]["healed"] = True
        data["version"] = data.get("version", 1) + 1
        data["last_healed"] = datetime.utcnow().isoformat()

        self.save_page(page_name, data)

    def list_pages(self) -> list[str]:
        return [p.stem for p in Path(self.locators_dir).glob("*.yaml")
                if p.stem != "_registry"]

    # ------------------------------------------------------------------
    # Registry — master index of all pages
    # ------------------------------------------------------------------

    def _update_registry(self, page_name: str, data: dict):
        registry = {}
        if Path(REGISTRY_PATH).exists():
            registry = load_yaml(REGISTRY_PATH) or {}

        registry[page_name] = {
            "url_pattern": data.get("url_pattern", ""),
            "version":     data.get("version", 1),
            "last_healed": data.get("last_healed"),
            "locator_count": len(data.get("locators", {})),
        }
        save_yaml(REGISTRY_PATH, registry)

    # ------------------------------------------------------------------
    # Healing log
    # ------------------------------------------------------------------

    def log_healing(self, page_name: str, element_name: str,
                    old_locator: str, new_locator: str, report_path: str):
        log = []
        try:
            log = load_json(report_path) if Path(report_path).exists() else []
        except Exception:
            pass

        log.append({
            "timestamp":    datetime.utcnow().isoformat(),
            "page":         page_name,
            "element":      element_name,
            "old_locator":  old_locator,
            "new_locator":  new_locator,
        })
        save_json(report_path, log)
