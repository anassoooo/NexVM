import json
import logging
from datetime import datetime, timezone


class StructuredLogger:
    def __init__(self, name: str) -> None:
        self._logger = logging.getLogger(name)
        if not self._logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(message)s"))
            self._logger.addHandler(handler)
            self._logger.setLevel(logging.INFO)

    def log(
        self,
        action: str,
        target: str,
        status: str,
        message: str,
        user_id: str | None = None,
    ) -> None:
        entry = {
            "user_id": user_id,
            "action": action,
            "target": target,
            "status": status,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._logger.info(json.dumps(entry))

    def error(
        self,
        action: str,
        target: str,
        message: str,
        user_id: str | None = None,
    ) -> None:
        self.log(action, target, "failure", message, user_id)


logger = StructuredLogger("myvms")
