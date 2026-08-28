import pytest

from workers.job_runner import process_queued_jobs


@pytest.mark.asyncio
async def test_worker_task_shell():
    await process_queued_jobs()
    assert True
