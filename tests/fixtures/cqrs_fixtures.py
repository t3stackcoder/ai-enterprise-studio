"""
CQRS fixtures for integration tests

Provides pytest fixtures for:
- EnterpriseMediator with pipeline behaviors
- Test command/query handlers
- CQRS test utilities
"""

import os
import sys
from pathlib import Path

# Add libs to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "libs"))

from typing import Generator

import pytest
from buildingblocks.behaviors import (
    LoggingBehavior,
    ValidationBehavior,
)
from buildingblocks.cqrs import EnterpriseMediator, IMediator


@pytest.fixture(scope="function")
def mediator() -> Generator[IMediator, None, None]:
    """
    Function-scoped mediator fixture with validation and logging behaviors.
    Clean instance for each test.
    """
    mediator = EnterpriseMediator()

    # Add standard pipeline behaviors
    mediator.add_pipeline_behavior(ValidationBehavior())
    mediator.add_pipeline_behavior(LoggingBehavior(slow_threshold=1.0))

    yield mediator


@pytest.fixture(scope="function")
def mediator_minimal() -> Generator[IMediator, None, None]:
    """
    Function-scoped mediator fixture without pipeline behaviors.
    Use for testing handlers in isolation.
    """
    mediator = EnterpriseMediator()
    yield mediator


@pytest.fixture(scope="function")
def mediator_full() -> Generator[IMediator, None, None]:
    """
    Function-scoped mediator fixture with full enterprise behaviors.
    Includes validation, logging, retry, and circuit breaker.
    """
    from buildingblocks.behaviors import (
        CircuitBreakerBehavior,
        LoggingBehavior,
        ValidationBehavior,
    )

    mediator = EnterpriseMediator()

    # Add enterprise pipeline behaviors
    mediator.add_pipeline_behavior(ValidationBehavior())
    mediator.add_pipeline_behavior(LoggingBehavior(slow_threshold=1.0))
    mediator.add_pipeline_behavior(CircuitBreakerBehavior(failure_threshold=3))

    yield mediator
