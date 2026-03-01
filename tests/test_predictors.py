from chaos_negotiator.models import DeploymentContext, DeploymentChange
from chaos_negotiator.predictors.ml_predictor import MLRiskPredictor
from chaos_negotiator.predictors.ensemble import EnsembleRiskPredictor
from chaos_negotiator.predictors.history_store import DeploymentHistoryStore
from chaos_negotiator.models.outcome import DeploymentOutcome


def test_ml_predictor_returns_probability():
    predictor = MLRiskPredictor()
    context = DeploymentContext(
        deployment_id="ml-001",
        service_name="svc",
        environment="staging",
        version="0.1",
        changes=[
            DeploymentChange(
                file_path="a/b.py",
                change_type="modify",
                lines_changed=10,
                description="simple change",
            )
        ],
        total_lines_changed=10,
    )
    score = predictor.predict(context)

    assert 0.0 <= score <= 1.0
    assert isinstance(score, float)


def test_ensemble_predictor_combines_scores():
    predictor = EnsembleRiskPredictor(heuristic_weight=0.5, ml_weight=0.5)
    context = DeploymentContext(
        deployment_id="ens-001",
        service_name="svc",
        environment="production",
        version="1.0",
        changes=[
            DeploymentChange(
                file_path="db/migrate.sql",
                change_type="add",
                lines_changed=500,
                description="Database schema migration",
            )
        ],
        total_lines_changed=500,
    )

    assessment = predictor.predict(context)

    assert assessment.risk_score >= 0
    assert assessment.risk_score <= 100
    assert assessment.risk_level in ["low", "medium", "high", "critical"]
    assert "heuristic" in assessment.reasoning.lower()
    assert "ml=" in assessment.reasoning
    assert hasattr(assessment, "confidence_percent")
    assert 0.0 <= assessment.confidence_percent <= 100.0


def test_history_store_and_tuning(tmp_path):
    # use a temporary database file
    db_file = tmp_path / "history.db"
    store = DeploymentHistoryStore(str(db_file))

    # synthetic outcomes where ml is always closer to actual
    for i in range(5):
        store.save(
            DeploymentOutcome(
                deployment_id=f"d{i}",
                heuristic_score=20.0,
                ml_score=40.0,
                final_score=30.0,
                actual_error_rate_percent=0.4,  # maps to 40
                actual_latency_change_percent=0.0,
                rollback_triggered=False,
            )
        )

    predictor = EnsembleRiskPredictor(history_store=store)
    # initial weights default 0.6/0.4
    assert predictor.heuristic_weight == 0.6
    predictor.tune_weights()

    # after tuning the ml weight should be larger (ml was more accurate)
    assert predictor.ml_weight > predictor.heuristic_weight


