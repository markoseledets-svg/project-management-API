import logging
import sys

log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
try:
    handlers.append(logging.FileHandler("app.log", encoding="utf-8"))
except (PermissionError, OSError):
    pass

logging.basicConfig(
    level=logging.INFO,
    format=log_format,
    handlers=handlers,
)

logger = logging.getLogger("TaskFlow_API")
