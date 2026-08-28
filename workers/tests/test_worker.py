import pytest


@pytest.mark.asyncio
async def test_worker_task_shell():
    from workers.tasks import process_queued_jobs
    await process_queued_jobs()
    assert True
