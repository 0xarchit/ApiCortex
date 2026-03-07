from __future__ import annotations

import asyncio
import importlib

from app.config import get_settings
from workers.inference_worker import InferenceWorker, install_signal_handlers


def _configure_event_loop() -> None:
    try:
        uvloop = importlib.import_module("uvloop")

        uvloop.install()
    except Exception:
        
        return


async def _run() -> None:
    settings = get_settings()
    worker = InferenceWorker(settings)
    install_signal_handlers(worker)
    await worker.run()


def main() -> None:
    _configure_event_loop()
    asyncio.run(_run())


if __name__ == "__main__":
    main()
