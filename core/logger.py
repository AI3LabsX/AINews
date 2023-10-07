import logging
import sys

from core.config import DEBUG, LOG_FILE

if not DEBUG:
    sys.tracebacklimit = 0

# logger config
logger: logging.Logger = logging.getLogger(__name__)
logging.basicConfig(
    filename=None if DEBUG else LOG_FILE,
    encoding="utf-8",
    format=f"[%(asctime)s] %(levelname)-8s {'%(filename)s:%(lineno)d - ' if DEBUG else ''}%(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)