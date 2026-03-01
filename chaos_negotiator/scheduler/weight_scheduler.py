from __future__ import annotations

import os
import threading
import time
import logging

logger = logging.getLogger(__name__)


class WeightTuningScheduler:
    """Background scheduler that periodically tunes ensemble weights."""

    def __init__(self, predictor) -> None:
        self.predictor = predictor
        # interval defaults to 5 minutes
        self.interval_seconds = int(os.getenv("CN_TUNING_INTERVAL_SEC", "300"))
        self.enabled = os.getenv("CN_ENABLE_TUNING", "true").lower() == "true"

        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    # -------------------------
    # Start scheduler
    # -------------------------
    def start(self) -> None:
        if not self.enabled:
            logger.info("Weight tuning scheduler disabled.")
            return

        if self._thread and self._thread.is_alive():
            return

        logger.info(
            "Starting weight tuning scheduler (interval=%ss)",
            self.interval_seconds,
        )

        self._thread = threading.Thread(
            target=self._run_loop,
            daemon=True,
        )
        self._thread.start()

    # -------------------------
    # Stop scheduler
    # -------------------------
    def stop(self) -> None:
        self._stop_event.set()

    # -------------------------
    # Loop
    # -------------------------
    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                logger.info("Running automatic weight tuning...")
                self.predictor.tune_weights()
            except Exception as exc:
                logger.exception("Weight tuning failed: %s", exc)

            # wait returns immediately if event is set
            self._stop_event.wait(self.interval_seconds)
