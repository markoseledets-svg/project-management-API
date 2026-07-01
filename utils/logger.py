import logging
import sys

log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

logging.basicConfig(
                    level=logging.INFO,
                    format=log_format,
                    handlers=[
                        logging.FileHandler("app.log", encoding="utf-8"),
                        logging.StreamHandler(sys.stdout)
                        ]
                    )

logger = logging.getLogger("TaskFlow_API")
