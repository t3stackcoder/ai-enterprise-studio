"""
Celery configuration for VisionScope messaging
"""

import os

from celery import Celery
from kombu import Queue

# Create Celery app
celery_app = Celery("visionscope")


# Configuration
class CeleryConfig:
    # Redis as broker and result backend
    broker_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    result_backend = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # JSON serialization (more secure than pickle)
    task_serializer = "json"
    accept_content = ["json"]
    result_serializer = "json"

    # Timezone
    timezone = "UTC"
    enable_utc = True

    # Task routing
    task_routes = {
        "billing.*": {"queue": "billing"},
        "video_processing.*": {"queue": "video_processing"},
        "notifications.*": {"queue": "notifications"},
        "default": {"queue": "default"},
    }

    # Queues
    task_default_queue = "default"
    task_queues = (
        Queue("default", routing_key="default"),
        Queue("billing", routing_key="billing"),
        Queue("video_processing", routing_key="video_processing"),
        Queue("notifications", routing_key="notifications"),
    )

    # Worker settings
    worker_concurrency = 4
    worker_max_tasks_per_child = 1000
    worker_disable_rate_limits = False

    # Task execution
    task_acks_late = True  # Acknowledge task after completion
    task_reject_on_worker_lost = True  # Retry if worker dies
    task_soft_time_limit = 300  # 5 minutes
    task_time_limit = 600  # 10 minutes


# Apply configuration
celery_app.config_from_object(CeleryConfig)

# Auto-discover tasks
celery_app.autodiscover_tasks(
    ["features.billing.tasks", "features.video_processing.tasks", "features.notifications.tasks"]
)


# Example task definitions (these would be in feature modules)
@celery_app.task(name="billing.process_credit_consumption")
def process_credit_consumption(event_data: str, event_type: str = None):
    """Process credit consumption event"""
    from building_blocks.messaging.interfaces import CreditConsumedEvent
    from building_blocks.messaging.message_bus import deserialize_message

    try:
        event = deserialize_message(event_data, CreditConsumedEvent)
        # Process the event - update database, send notifications, etc.
        print(
            f"Processing credit consumption: {event.workspace_id} used {event.credits_consumed} credits"
        )
        # TODO: Implement actual business logic
        return {"status": "success", "event_id": str(event.message_id)}
    except Exception as e:
        print(f"Error processing credit consumption: {e}")
        raise


@celery_app.task(name="billing.deduct_credits")
def deduct_credits(command_data: str, command_type: str = None):
    """Handle deduct credits command"""
    from building_blocks.messaging.interfaces import DeductCreditsCommand
    from building_blocks.messaging.message_bus import deserialize_message

    try:
        command = deserialize_message(command_data, DeductCreditsCommand)
        # Process the command - deduct credits from workspace
        print(
            f"Deducting {command.credits_to_deduct} credits from workspace {command.workspace_id}"
        )
        # TODO: Implement actual business logic
        return {"status": "success", "command_id": str(command.message_id)}
    except Exception as e:
        print(f"Error deducting credits: {e}")
        raise


# Initialize message bus on startup
def initialize_messaging():
    """Initialize the message bus with event/command handlers"""
    from building_blocks.messaging.interfaces import CreditConsumedEvent, DeductCreditsCommand
    from building_blocks.messaging.message_bus import configure_message_bus

    message_bus = configure_message_bus(celery_app)

    # Register event handlers
    message_bus.register_event_handler(CreditConsumedEvent, "billing.process_credit_consumption")

    # Register command handlers
    message_bus.register_command_handler(DeductCreditsCommand, "billing.deduct_credits")

    return message_bus
