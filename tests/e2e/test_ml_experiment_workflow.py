"""
E2E ML Experiment Workflow Tests

Tests complete ML experiment pipeline:
1. Log experiment run to MLflow
2. Save model artifact to MinIO
3. Cache experiment results in Redis
4. Query experiment metrics

Services: MLflow + MinIO + Redis
"""

import os
import sys
from pathlib import Path

# Add libs to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "libs"))

import io
import json
from dataclasses import dataclass
from uuid import uuid4

import mlflow
import pytest
from buildingblocks.cqrs import ICommand, ICommandHandler, IQuery, IQueryHandler


# ============================================================================
# Commands
# ============================================================================


@dataclass
class CreateMLExperimentCommand(ICommand):
    """Create new ML experiment"""

    experiment_name: str


@dataclass
class LogTrainingRunCommand(ICommand):
    """Log training run with params and metrics"""

    experiment_id: str
    run_name: str
    params: dict
    metrics: dict


@dataclass
class SaveModelArtifactCommand(ICommand):
    """Save model file to MinIO"""

    bucket_name: str
    model_id: str
    model_data: bytes


@dataclass
class CacheExperimentResultsCommand(ICommand):
    """Cache experiment results in Redis"""

    experiment_id: str
    run_id: str
    results: dict


# ============================================================================
# Queries
# ============================================================================


@dataclass
class GetBestRunQuery(IQuery[dict | None]):
    """Find best run by metric"""

    experiment_id: str
    metric_name: str
    maximize: bool = True


@dataclass
class GetCachedResultsQuery(IQuery[dict | None]):
    """Get cached experiment results"""

    run_id: str


# ============================================================================
# Handlers
# ============================================================================


class CreateMLExperimentHandler(ICommandHandler):
    """Handler for creating ML experiments"""

    def __init__(self, mlflow_client):
        self.mlflow = mlflow_client

    async def handle(self, command: CreateMLExperimentCommand) -> None:
        self.mlflow.create_experiment(command.experiment_name)


class LogTrainingRunHandler(ICommandHandler):
    """Handler for logging training runs"""

    def __init__(self, mlflow_client):
        self.mlflow = mlflow_client

    async def handle(self, command: LogTrainingRunCommand) -> None:
        with mlflow.start_run(
            experiment_id=command.experiment_id, run_name=command.run_name
        ):
            # Log params
            for key, value in command.params.items():
                mlflow.log_param(key, value)

            # Log metrics
            for key, value in command.metrics.items():
                mlflow.log_metric(key, value)


class SaveModelArtifactHandler(ICommandHandler):
    """Handler for saving model artifacts to MinIO"""

    def __init__(self, minio_client):
        self.minio = minio_client

    async def handle(self, command: SaveModelArtifactCommand) -> None:
        object_name = f"models/{command.model_id}/model.pkl"
        data_stream = io.BytesIO(command.model_data)
        self.minio.put_object(
            bucket_name=command.bucket_name,
            object_name=object_name,
            data=data_stream,
            length=len(command.model_data),
            content_type="application/octet-stream",
        )


class CacheExperimentResultsHandler(ICommandHandler):
    """Handler for caching experiment results in Redis"""

    def __init__(self, redis_client):
        self.redis = redis_client

    async def handle(self, command: CacheExperimentResultsCommand) -> None:
        cache_key = f"experiment:results:{command.run_id}"
        self.redis.setex(cache_key, 7200, json.dumps(command.results))  # 2 hour TTL


class GetBestRunHandler(IQueryHandler):
    """Handler for finding best run by metric"""

    def __init__(self, mlflow_client):
        self.mlflow = mlflow_client

    async def handle(self, query: GetBestRunQuery) -> dict | None:
        order_by = f"metrics.{query.metric_name} {'DESC' if query.maximize else 'ASC'}"
        runs = self.mlflow.search_runs(
            experiment_ids=[query.experiment_id], order_by=[order_by], max_results=1
        )

        if runs.empty:
            return None

        best_run = runs.iloc[0]
        # Access DataFrame columns - params and metrics are stored with prefixes
        return {
            "run_id": best_run["run_id"],
            "params": {k.replace("params.", ""): best_run[k] for k in best_run.index if k.startswith("params.")},
            "metrics": {k.replace("metrics.", ""): best_run[k] for k in best_run.index if k.startswith("metrics.")},
        }


class GetCachedResultsHandler(IQueryHandler):
    """Handler for retrieving cached experiment results"""

    def __init__(self, redis_client):
        self.redis = redis_client

    async def handle(self, query: GetCachedResultsQuery) -> dict | None:
        cache_key = f"experiment:results:{query.run_id}"
        cached = self.redis.get(cache_key)
        return json.loads(cached) if cached else None


# ============================================================================
# Tests
# ============================================================================


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_complete_ml_experiment_workflow(
    mlflow_clean, minio_clean, redis_clean, mediator
):
    """
    Complete E2E workflow: Create experiment → Log run → Save model → Cache results
    
    This simulates a real ML training pipeline using all three services.
    """
    # Register all handlers
    mediator.register_command_handler(
        CreateMLExperimentCommand, CreateMLExperimentHandler(mlflow_clean)
    )
    mediator.register_command_handler(
        LogTrainingRunCommand, LogTrainingRunHandler(mlflow_clean)
    )
    mediator.register_command_handler(
        SaveModelArtifactCommand, SaveModelArtifactHandler(minio_clean)
    )
    mediator.register_command_handler(
        CacheExperimentResultsCommand, CacheExperimentResultsHandler(redis_clean)
    )
    mediator.register_query_handler(GetBestRunQuery, GetBestRunHandler(mlflow_clean))
    mediator.register_query_handler(
        GetCachedResultsQuery, GetCachedResultsHandler(redis_clean)
    )

    # Step 1: Create ML experiment
    experiment_name = f"test_training_{uuid4().hex[:8]}"
    await mediator.send_command(CreateMLExperimentCommand(experiment_name=experiment_name))
    experiment = mlflow_clean.get_experiment_by_name(experiment_name)
    experiment_id = experiment.experiment_id
    print(f"✅ Step 1: Created experiment: {experiment_name}")

    # Step 2: Log training run
    params = {"learning_rate": 0.001, "batch_size": 32, "epochs": 10}
    metrics = {"accuracy": 0.95, "loss": 0.05, "f1_score": 0.93}

    await mediator.send_command(
        LogTrainingRunCommand(
            experiment_id=experiment_id,
            run_name="run_001",
            params=params,
            metrics=metrics,
        )
    )
    print(f"✅ Step 2: Logged training run with params and metrics")

    # Get run_id for later steps
    runs = mlflow_clean.search_runs(experiment_ids=[experiment_id])
    run_id = runs.iloc[0].run_id

    # Step 3: Save model artifact to MinIO
    model_id = str(uuid4())
    model_data = b"fake model weights data"
    test_bucket = os.getenv("MINIO_TEST_BUCKET", "test-artifacts")

    await mediator.send_command(
        SaveModelArtifactCommand(
            bucket_name=test_bucket, model_id=model_id, model_data=model_data
        )
    )
    print(f"✅ Step 3: Saved model artifact to MinIO: {model_id}")

    # Step 4: Cache experiment results
    results = {"model_id": model_id, "status": "completed", "metrics": metrics}

    await mediator.send_command(
        CacheExperimentResultsCommand(
            experiment_id=experiment_id, run_id=run_id, results=results
        )
    )
    print(f"✅ Step 4: Cached experiment results in Redis")

    # Step 5: Retrieve best run
    best_run = await mediator.send_query(
        GetBestRunQuery(experiment_id=experiment_id, metric_name="accuracy", maximize=True)
    )

    assert best_run is not None
    assert best_run["run_id"] == run_id
    assert best_run["metrics"]["accuracy"] == 0.95
    print(f"✅ Step 5: Retrieved best run by accuracy")

    # Step 6: Retrieve cached results (cache hit)
    cached_results = await mediator.send_query(GetCachedResultsQuery(run_id=run_id))

    assert cached_results is not None
    assert cached_results["model_id"] == model_id
    assert cached_results["status"] == "completed"
    print(f"✅ Step 6: Retrieved cached results (cache hit)")

    print(f"🎉 Complete ML experiment workflow successful!")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_compare_multiple_runs(mlflow_clean, mediator):
    """
    Test logging multiple runs and finding the best one.
    
    This tests model comparison workflows.
    """
    # Register handlers
    mediator.register_command_handler(
        CreateMLExperimentCommand, CreateMLExperimentHandler(mlflow_clean)
    )
    mediator.register_command_handler(
        LogTrainingRunCommand, LogTrainingRunHandler(mlflow_clean)
    )
    mediator.register_query_handler(GetBestRunQuery, GetBestRunHandler(mlflow_clean))

    # Create experiment
    experiment_name = f"test_comparison_{uuid4().hex[:8]}"
    await mediator.send_command(CreateMLExperimentCommand(experiment_name=experiment_name))
    experiment = mlflow_clean.get_experiment_by_name(experiment_name)
    experiment_id = experiment.experiment_id

    # Log 3 runs with different accuracies
    runs_data = [
        ("run_baseline", {"lr": 0.01}, {"accuracy": 0.85, "loss": 0.15}),
        ("run_tuned", {"lr": 0.001}, {"accuracy": 0.92, "loss": 0.08}),  # Best
        ("run_aggressive", {"lr": 0.1}, {"accuracy": 0.78, "loss": 0.22}),
    ]

    for run_name, params, metrics in runs_data:
        await mediator.send_command(
            LogTrainingRunCommand(
                experiment_id=experiment_id,
                run_name=run_name,
                params=params,
                metrics=metrics,
            )
        )

    print(f"✅ Logged {len(runs_data)} training runs")

    # Find best run by accuracy
    best_run = await mediator.send_query(
        GetBestRunQuery(experiment_id=experiment_id, metric_name="accuracy", maximize=True)
    )

    assert best_run is not None
    assert best_run["metrics"]["accuracy"] == 0.92
    assert float(best_run["params"]["lr"]) == 0.001  # MLflow stores params as strings

    print(f"✅ Found best run with accuracy: {best_run['metrics']['accuracy']}")

    # Find worst run by accuracy (minimize)
    worst_run = await mediator.send_query(
        GetBestRunQuery(experiment_id=experiment_id, metric_name="accuracy", maximize=False)
    )

    assert worst_run is not None
    assert worst_run["metrics"]["accuracy"] == 0.78
    assert float(worst_run["params"]["lr"]) == 0.1  # MLflow stores params as strings

    print(f"✅ Found worst run with accuracy: {worst_run['metrics']['accuracy']}")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_model_versioning_workflow(minio_clean, mediator):
    """
    Test saving multiple versions of the same model.
    
    This tests model versioning via MinIO.
    """
    # Register handler
    mediator.register_command_handler(
        SaveModelArtifactCommand, SaveModelArtifactHandler(minio_clean)
    )

    test_bucket = os.getenv("MINIO_TEST_BUCKET", "test-artifacts")
    model_id = str(uuid4())

    # Save 3 versions of the model
    for version in [1, 2, 3]:
        model_data = f"model version {version} weights".encode()
        await mediator.send_command(
            SaveModelArtifactCommand(
                bucket_name=test_bucket,
                model_id=f"{model_id}_v{version}",
                model_data=model_data,
            )
        )

    print(f"✅ Saved 3 versions of model: {model_id}")

    # Verify all versions exist
    objects = minio_clean.list_objects(test_bucket, prefix=f"models/{model_id}")
    object_list = list(objects)

    assert len(object_list) == 3
    print(f"✅ Verified all 3 model versions in MinIO")
