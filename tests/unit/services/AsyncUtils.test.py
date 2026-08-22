import asyncio
import threading

from src.infrastructure.database.async_utils import offload_db


def test_offload_db_runs_outside_the_event_loop_thread():
    event_loop_thread = threading.get_ident()

    @offload_db
    def get_worker_thread():
        return threading.get_ident()

    async def run():
        return await get_worker_thread()

    assert asyncio.run(run()) != event_loop_thread
