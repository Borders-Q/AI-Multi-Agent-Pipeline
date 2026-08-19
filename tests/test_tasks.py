import asyncio

from skyt_platform import tasks as tasks_module


def test_task_manager_completes_with_heartbeat(monkeypatch):
    records = {}
    events = []

    def create_task(task_id, task_type, payload, **kwargs):
        records[task_id] = {
            "task_id": task_id,
            "task_type": task_type,
            "payload": payload,
            "status": "queued",
            "attempt": 0,
            "max_attempts": kwargs.get("max_attempts", 3),
        }

    def get_task(task_id):
        return dict(records[task_id]) if task_id in records else None

    def claim_next_task(worker_id, lease_seconds=300):
        for record in records.values():
            if record["status"] == "queued":
                record["status"] = "running"
                record["attempt"] += 1
                record["worker_id"] = worker_id
                return dict(record)
        return None

    monkeypatch.setattr(tasks_module.db, "create_task", create_task)
    monkeypatch.setattr(tasks_module.db, "get_task", get_task)
    monkeypatch.setattr(tasks_module.db, "claim_next_task", claim_next_task)
    monkeypatch.setattr(tasks_module.db, "recover_stale_tasks", lambda: None)
    monkeypatch.setattr(tasks_module.db, "save_task_event", lambda task_id, event, detail=None: events.append(event))
    monkeypatch.setattr(tasks_module.db, "heartbeat_task", lambda *args, **kwargs: events.append("heartbeat"))
    monkeypatch.setattr(tasks_module.db, "is_task_cancel_requested", lambda task_id: False)
    monkeypatch.setattr(tasks_module.db, "complete_task", lambda task_id, result: records[task_id].update(status="succeeded", result=result))
    monkeypatch.setattr(tasks_module.db, "fail_task", lambda *args, **kwargs: None)

    async def run():
        manager = tasks_module.TaskManager(poll_seconds=0.01, lease_seconds=1)
        manager.register("unit", lambda payload: asyncio.sleep(0, result={"ok": True}))
        task = await manager.submit("unit", {"value": 1})
        await manager.start()
        for _ in range(50):
            if records[task["task_id"]]["status"] == "succeeded":
                break
            await asyncio.sleep(0.01)
        await manager.stop()
        return task["task_id"]

    task_id = asyncio.run(run())

    assert records[task_id]["status"] == "succeeded"
    assert "running" in events
    assert "succeeded" in events


def test_task_manager_cancel_request_converges(monkeypatch):
    records = {}

    def create_task(task_id, task_type, payload, **kwargs):
        records[task_id] = {"task_id": task_id, "task_type": task_type, "payload": payload, "status": "queued", "attempt": 0, "max_attempts": 3}

    monkeypatch.setattr(tasks_module.db, "create_task", create_task)
    monkeypatch.setattr(tasks_module.db, "get_task", lambda task_id: dict(records[task_id]))
    monkeypatch.setattr(tasks_module.db, "save_task_event", lambda *args, **kwargs: None)
    monkeypatch.setattr(tasks_module.db, "request_task_cancel", lambda task_id: records[task_id].update(status="cancelled"))

    async def run():
        manager = tasks_module.TaskManager()
        manager.register("unit", lambda payload: asyncio.sleep(0))
        task = await manager.submit("unit", {})
        return await manager.cancel(task["task_id"])

    cancelled = asyncio.run(run())

    assert cancelled["status"] == "cancelled"
