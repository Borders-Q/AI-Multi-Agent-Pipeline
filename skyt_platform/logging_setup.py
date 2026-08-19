from __future__ import annotations

import logging
import sys
from contextvars import ContextVar


request_id_var: ContextVar[str] = ContextVar("request_id", default="-")
task_id_var: ContextVar[str] = ContextVar("task_id", default="-")


class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        record.task_id = task_id_var.get()
        return True


def configure_logging() -> None:
    root = logging.getLogger()
    if getattr(root, "_skyt_configured", False):
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(ContextFilter())
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s request_id=%(request_id)s task_id=%(task_id)s %(name)s: %(message)s"
    ))
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    root._skyt_configured = True
