"""
MLflow integration tests using CQRS

Tests MLflow experiment tracking through CQRS mediator.
Validates experiment creation, run logging, and artifact storage.
"""

import os
import sys
from pathlib import Path

# Add libs to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "libs"))

from dataclasses import dataclass, field
from uuid import uuid4

import pytest
from buildingblocks.cqrs import ICommand, ICommandHandler, IQuery, IQueryHandler


# ============================================================================
# Commands
# ============================================================================


@dataclass
class CreateExperimentCommand(ICommand):
    """Create a new MLflow experiment"""

    experiment_name: str
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class LogExperimentRunCommand(ICommand):
    """Log a run in an MLflow experiment"""

    experiment_name: str
    run_name: str
    params: dict[str, any] = field(default_factory=dict)
    metrics: dict[str, float] = field(default_factory=dict)
    tags: dict[str, str] = field(default_factory=dict)


# ============================================================================
# Queries
# ============================================================================


@dataclass
class GetExperimentQuery(IQuery[dict | None]):
    """Get experiment details by name"""

    experiment_name: str


@dataclass
class SearchRunsQuery(IQuery[list]):
    """Search runs in an experiment"""

    experiment_name: str
    max_results: int = 10


# ============================================================================
# Handlers
# ============================================================================


class CreateExperimentHandler(ICommandHandler):
    """Handler for creating MLflow experiments"""

    def __init__(self, mlflow_client):
        self.mlflow = mlflow_client

    async def handle(self, command: CreateExperimentCommand) -> None:
        self.mlflow.create_experiment(name=command.experiment_name, tags=command.tags)


class LogExperimentRunHandler(ICommandHandler):
    """Handler for logging MLflow runs"""

    def __init__(self, mlflow_client):
        self.mlflow = mlflow_client

    async def handle(self, command: LogExperimentRunCommand) -> None:
        # Get experiment
        experiment = self.mlflow.get_experiment_by_name(command.experiment_name)
        if not experiment:
            raise ValueError(f"Experiment not found: {command.experiment_name}")

        # Start run
        with self.mlflow.start_run(
            experiment_id=experiment.experiment_id, run_name=command.run_name
        ) as run:
            # Log parameters
            for key, value in command.params.items():
                self.mlflow.log_param(key, value)

            # Log metrics
            for key, value in command.metrics.items():
                self.mlflow.log_metric(key, value)

            # Set tags
            for key, value in command.tags.items():
                self.mlflow.set_tag(key, value)


class GetExperimentHandler(IQueryHandler):
    """Handler for retrieving MLflow experiment details"""

    def __init__(self, mlflow_client):
        self.mlflow = mlflow_client

    async def handle(self, query: GetExperimentQuery) -> dict | None:
        experiment = self.mlflow.get_experiment_by_name(query.experiment_name)
        if not experiment:
            return None

        return {
            "experiment_id": experiment.experiment_id,
            "name": experiment.name,
            "lifecycle_stage": experiment.lifecycle_stage,
        }


class SearchRunsHandler(IQueryHandler):
    """Handler for searching MLflow runs"""

    def __init__(self, mlflow_client):
        self.mlflow = mlflow_client

    async def handle(self, query: SearchRunsQuery) -> list:
        experiment = self.mlflow.get_experiment_by_name(query.experiment_name)
        if not experiment:
            return []

        runs = self.mlflow.search_runs(
            experiment_ids=[experiment.experiment_id], max_results=query.max_results
        )
        return runs


# ============================================================================
# Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.mlflow
@pytest.mark.asyncio
async def test_create_experiment(mlflow_client, mediator):
    """
    Test creating an MLflow experiment via CQRS.
    """
    mediator.register_command_handler(
        CreateExperimentCommand, CreateExperimentHandler(mlflow_client)
    )
    mediator.register_query_handler(
        GetExperimentQuery, GetExperimentHandler(mlflow_client)
    )

    # Create experiment
    experiment_name = f"test_experiment_{uuid4().hex[:8]}"
    await mediator.send_command(
        CreateExperimentCommand(
            experiment_name=experiment_name, tags={"test": "integration"}
        )
    )

    # Verify experiment exists
    experiment = await mediator.send_query(GetExperimentQuery(experiment_name=experiment_name))
    assert experiment is not None
    assert experiment["name"] == experiment_name

    print(f"✅ Created MLflow experiment: {experiment_name}")


@pytest.mark.integration
@pytest.mark.mlflow
@pytest.mark.asyncio
async def test_log_experiment_run(mlflow_client, mediator):
    """
    Test logging a run in an MLflow experiment via CQRS.
    
    Flow:
    1. Create experiment
    2. Log a run with params and metrics
    3. Search for runs
    4. Verify run was logged
    """
    # Register handlers
    mediator.register_command_handler(
        CreateExperimentCommand, CreateExperimentHandler(mlflow_client)
    )
    mediator.register_command_handler(
        LogExperimentRunCommand, LogExperimentRunHandler(mlflow_client)
    )
    mediator.register_query_handler(SearchRunsQuery, SearchRunsHandler(mlflow_client))

    # Create experiment
    experiment_name = f"test_run_{uuid4().hex[:8]}"
    await mediator.send_command(CreateExperimentCommand(experiment_name=experiment_name))

    # Log run
    run_name = "test_run_001"
    await mediator.send_command(
        LogExperimentRunCommand(
            experiment_name=experiment_name,
            run_name=run_name,
            params={"learning_rate": 0.01, "batch_size": 32},
            metrics={"accuracy": 0.95, "loss": 0.05},
            tags={"model": "test_model"},
        )
    )

    # Search for runs
    runs = await mediator.send_query(SearchRunsQuery(experiment_name=experiment_name))

    # Verify run exists
    assert len(runs) > 0
    # Runs is a DataFrame, access first row using iloc
    run_data = runs.iloc[0]
    assert run_data["params.learning_rate"] == "0.01"
    assert run_data["metrics.accuracy"] == 0.95

    print(f"✅ Logged run in MLflow experiment: {experiment_name}/{run_name}")


@pytest.mark.integration
@pytest.mark.mlflow
@pytest.mark.asyncio
async def test_query_nonexistent_experiment(mlflow_client, mediator):
    """
    Test querying an experiment that doesn't exist returns None.
    """
    mediator.register_query_handler(
        GetExperimentQuery, GetExperimentHandler(mlflow_client)
    )

    experiment_name = f"nonexistent_{uuid4().hex[:8]}"
    result = await mediator.send_query(GetExperimentQuery(experiment_name=experiment_name))

    assert result is None
    print(f"✅ Query for nonexistent experiment returned None: {experiment_name}")
