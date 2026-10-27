import json
from pathlib import Path

CONFIG = Path.home() / ".config/pccooler-lcd/config.json"

DEFAULT = {
    "clock": {"x": 85, "y": 28, "size": 32, "color": "#b4dcff"},
    "cpu_label": {"x": 35, "y": 255, "size": 19, "color": "#64beff"},
    "cpu_value": {"x": 20, "y": 280, "size": 32, "color": "#ffffff"},
    "gpu_label": {"x": 155, "y": 255, "size": 19, "color": "#ff8c46"},
    "gpu_value": {"x": 140, "y": 280, "size": 32, "color": "#ffffff"}
}


def load_config():
    if CONFIG.exists():
        try:
            return json.loads(CONFIG.read_text())
        except Exception:
            pass
    return json.loads(json.dumps(DEFAULT))


def save_config(config):
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(
        json.dumps(config, indent=2, ensure_ascii=False)
    )
