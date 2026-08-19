from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any, Awaitable, Callable

import db


TaskHandler = Callable[[dict[str, Any]], Awaitable[dict[str, Any] | Any]]
logger = logging.getLogger(__name__)


class TaskManager:
    def __init__(self, poll_seconds: float = 0.5, max_attempts: int = 3, lease_seconds: int = 300):
        self.poll_seconds = poll_seconds
        self.max_attempts = max_attempts
        self.lease_seconds = lease_seconds
        self.handlers: dict[str, TaskHandler] = {}
        self.worker_id = f"worker_{uuid.uuid4().hex[:10]}"
        self._worker_task: asyncio.Task | None = None
        self._wake_event = asyncio.Event()

    def register(self, task_type: str, handler: TaskHandler) -> None:
        self.handlers[task_type] = handler

    async def start(self) -> None:
        if self._worker_task and not self._worker_task.done():
            return
        db.recover_stale_tasks()
        self._worker_task = asyncio.create_task(self._run(), name="skyt-task-worker")

    async def stop(self) -> None:
        if not self._worker_task:
            return
        self._worker_task.cancel()
        await asyncio.gather(self._worker_task, return_exceptions=True)
        self._worker_task = None

    async def _heartbeat(self, task_id: str) -> None:
        interval = max(1.0, self.lease_seconds / 3)
        while True:
            await asyncio.sleep(interval)
            db.heartbeat_task(task_id, self.worker_id, lease_seconds=self.lease_seconds)

    async def submit(self, task_type: str, payload: dict[str, Any], *, session_id: str | None = None, run_id: str | None = None) -> dict[str, Any]:
        if task_type not in self.handlers:
            raise ValueError(f"未知任务类型：{task_type}")
        task_id = f"TASK_{uuid.uuid4().hex[:12].upper()}"
        db.create_task(task_id, task_type, payload, session_id=session_id, run_id=run_id, max_attempts=self.max_attempts)
        db.save_task_event(task_id, "queued", {"task_type": task_type})
        self._wake_event.set()
        return db.get_task(task_id) or {"task_id": task_id, "status": "queued"}

    async def _run(self) -> None:
        while True:
            task = db.claim_next_task(self.worker_id, lease_seconds=self.lease_seconds)
            if not task:
                self._wake_event.clear()
                try:
                    await asyncio.wait_for(self._wake_event.wait(), timeout=self.poll_seconds)
                except asyncio.TimeoutError:
                    pass
                continue

            task_id = task["task_id"]
            handler = self.handlers.get(task["task_type"])
            if not handler:
                db.fail_task(task_id, f"未注册任务处理器：{task['task_type']}", retry=False)
                continue
            try:
                if db.is_task_cancel_requested(task_id):
                    db.mark_task_cancelled(task_id)
                    db.save_task_event(task_id, "cancelled", {"worker_id": self.worker_id})
                    continue
                payload = dict(task.get("payload") or {})
                payload["_task_id"] = task_id
                db.save_task_event(task_id, "running", {"worker_id": self.worker_id})
                heartbeat_task = asyncio.create_task(self._heartbeat(task_id), name=f"heartbeat-{task_id}")
                try:
                    result = await handler(payload)
                finally:
                    heartbeat_task.cancel()
                    await asyncio.gather(heartbeat_task, return_exceptions=True)
                result_payload = result if isinstance(result, dict) else {"value": result}
                if result_payload.get("success") is False or result_payload.get("status") == "failed":
                    # A handler may finish cleanly while reporting a domain
                    # failure. Do not mark such work as an infrastructure
                    # success, and allow the handler to opt out of retries.
                    db.fail_task(
                        task_id,
                        str(result_payload.get("error") or "任务执行失败"),
                        retry=not bool(result_payload.get("non_retryable")),
                    )
                else:
                    db.complete_task(task_id, result_payload)
                final_task = db.get_task(task_id) or {}
                final_status = final_task.get("status")
                db.save_task_event(task_id, final_status or "succeeded", {"worker_id": self.worker_id})
            except asyncio.CancelledError:
                if db.is_task_cancel_requested(task_id):
                    db.mark_task_cancelled(task_id)
                    db.save_task_event(task_id, "cancelled", {"worker_id": self.worker_id})
                    continue
                raise
            except Exception as exc:
                logger.exception("Task failed task_id=%s type=%s", task_id, task.get("task_type"))
                retry = int(task.get("attempt") or 1) < int(task.get("max_attempts") or self.max_attempts)
                db.fail_task(task_id, str(exc), retry=retry)
                db.save_task_event(task_id, "retrying" if retry else "failed", {"error": str(exc)})

    async def cancel(self, task_id: str) -> dict[str, Any] | None:
        db.request_task_cancel(task_id)
        self._wake_event.set()
        return db.get_task(task_id)


from skyt_platform.config import settings

task_manager = TaskManager(
    poll_seconds=settings.task_poll_seconds,
    max_attempts=settings.task_max_attempts,
    lease_seconds=settings.task_lease_seconds,
)
