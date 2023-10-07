from os.path import join, normpath
from pathlib import Path

# Change DEBUG to False when running on a production server
DEBUG: bool = True

# Path settings
_BASE_DIR: Path = Path(__file__).resolve().parent.parent
ENV_FILE: str = normpath(join(_BASE_DIR, ".env"))
LOG_FILE: str = normpath(join(_BASE_DIR, "utils.log"))





