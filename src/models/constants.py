from pathlib import Path

SRC_ROOT = Path(__file__).parent.parent
REPO_ROOT = SRC_ROOT.parent
RESOURCES = SRC_ROOT / "resources"
APP_CONFIG = RESOURCES / "app_config.yaml"
SEARCH_TERMS = RESOURCES / "reddit" / "search_terms.yaml"
DATA_DIR = REPO_ROOT / "data"
