import time


def test_scheduler_runs_once():
    from chaos_negotiator.scheduler.weight_scheduler import (
        WeightTuningScheduler,
    )

    class DummyPredictor:
        def __init__(self):
            self.called = False

        def tune_weights(self):
            self.called = True

    predictor = DummyPredictor()
    scheduler = WeightTuningScheduler(predictor)

    # shorten interval for test
    scheduler.interval_seconds = 1
    scheduler.start()

    time.sleep(1.5)
    scheduler.stop()

    assert predictor.called is True
