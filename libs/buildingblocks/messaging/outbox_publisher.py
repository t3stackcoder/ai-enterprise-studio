"""
Background Event Publisher for Transactional Outbox
Uses pure CQRS to read from outbox and publish events
"""

import asyncio
import logging
from typing import Any

from building_blocks.cqrs import IMediator
from building_blocks.messaging.interfaces import IEvent
from building_blocks.messaging.message_bus import get_message_bus
from building_blocks.messaging.outbox_cqrs import (
    CleanupPublishedEventsCommand,
    GetUnpublishedEventsQuery,
    MarkEventAsFailedCommand,
    MarkEventAsPublishedCommand,
)
from database import SessionLocal
from models.messaging.event_outbox import EventOutbox

logger = logging.getLogger(__name__)


class OutboxEventPublisher:
    """
    Background service that publishes events from outbox using CQRS
    """

    def __init__(
        self,
        mediator: IMediator,
        polling_interval: int = 5,
        batch_size: int = 100,
        max_retries: int = 3,
    ):
        self.mediator = mediator
        self.polling_interval = polling_interval
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.event_registry: dict[str, type] = {}
        self.running = False

    def register_event_type(self, event_class: type[IEvent]) -> None:
        """
        Register an event class for deserialization

        Args:
            event_class: Event class that can be reconstructed from JSON
        """
        self.event_registry[event_class.__name__] = event_class
        logger.info(f"Registered event type: {event_class.__name__}")

    def register_event_types(self, event_classes: list[type[IEvent]]) -> None:
        """Register multiple event types"""
        for event_class in event_classes:
            self.register_event_type(event_class)

    async def start(self) -> None:
        """Start the background publisher"""
        if self.running:
            logger.warning("OutboxEventPublisher is already running")
            return

        self.running = True
        logger.info(f"Starting OutboxEventPublisher (polling every {self.polling_interval}s)")

        try:
            while self.running:
                await self._process_outbox_events()
                await asyncio.sleep(self.polling_interval)
        except Exception as e:
            logger.error(f"OutboxEventPublisher crashed: {e}")
            raise
        finally:
            self.running = False
            logger.info("OutboxEventPublisher stopped")

    def stop(self) -> None:
        """Stop the background publisher"""
        logger.info("Stopping OutboxEventPublisher...")
        self.running = False

    async def _process_outbox_events(self) -> None:
        """Process a batch of unpublished events using CQRS"""
        try:
            # Create database session for this batch
            db_session = SessionLocal()

            try:
                # Get unpublished events using CQRS query
                query = GetUnpublishedEventsQuery(limit=self.batch_size, db_session=db_session)

                unpublished_events = await self.mediator.send_query(query)

                if not unpublished_events:
                    return  # No events to process

                logger.debug(f"Processing {len(unpublished_events)} outbox events")

                # Process each event
                for outbox_event in unpublished_events:
                    await self._publish_single_event(outbox_event, db_session)

            finally:
                db_session.close()

        except Exception as e:
            logger.error(f"Error processing outbox events: {e}")

    async def _publish_single_event(self, outbox_event: EventOutbox, db_session) -> None:
        """Publish a single event from the outbox"""
        try:
            # Reconstruct the original event
            event = self._reconstruct_event(outbox_event)
            if not event:
                await self._mark_as_failed(
                    outbox_event.id, f"Unknown event type: {outbox_event.event_type}", db_session
                )
                return

            # Get message bus and publish event
            message_bus = get_message_bus()

            # Determine if it's an event or command
            if hasattr(event, "__bases__") and IEvent in event.__bases__:
                await message_bus.publish_event(event)
            else:
                # Assume it's an event if we can't determine
                await message_bus.publish_event(event)

            # Mark as published using CQRS command
            await self._mark_as_published(outbox_event.id, db_session)

            logger.debug(f"Published event {outbox_event.event_type} " f"(id: {outbox_event.id})")

        except Exception as e:
            logger.error(
                f"Failed to publish event {outbox_event.event_type} "
                f"(id: {outbox_event.id}): {e}"
            )

            # Mark as failed using CQRS command
            await self._mark_as_failed(outbox_event.id, str(e), db_session)

    def _reconstruct_event(self, outbox_event: EventOutbox) -> Any:
        """Reconstruct event from outbox record"""
        event_class = self.event_registry.get(outbox_event.event_type)
        if not event_class:
            logger.warning(
                f"Event type {outbox_event.event_type} not registered, " "cannot reconstruct event"
            )
            return None

        try:
            return outbox_event.reconstruct_event(event_class)
        except Exception as e:
            logger.error(f"Failed to reconstruct event {outbox_event.event_type}: {e}")
            return None

    async def _mark_as_published(self, event_id: str, db_session) -> None:
        """Mark event as published using CQRS"""
        try:
            command = MarkEventAsPublishedCommand(event_id=event_id, db_session=db_session)
            await self.mediator.send_command(command)
        except Exception as e:
            logger.error(f"Failed to mark event {event_id} as published: {e}")

    async def _mark_as_failed(self, event_id: str, error_message: str, db_session) -> None:
        """Mark event as failed using CQRS"""
        try:
            command = MarkEventAsFailedCommand(
                event_id=event_id, error_message=error_message, db_session=db_session
            )
            await self.mediator.send_command(command)
        except Exception as e:
            logger.error(f"Failed to mark event {event_id} as failed: {e}")

    async def cleanup_old_events(self, older_than_days: int = 30) -> None:
        """Cleanup old published events using CQRS"""
        try:
            db_session = SessionLocal()
            try:
                command = CleanupPublishedEventsCommand(
                    older_than_days=older_than_days, db_session=db_session
                )
                await self.mediator.send_command(command)
                logger.info(f"Cleaned up events older than {older_than_days} days")
            finally:
                db_session.close()
        except Exception as e:
            logger.error(f"Failed to cleanup old events: {e}")


# Convenience function to create and run publisher
async def run_outbox_publisher(
    mediator: IMediator,
    event_types: list[type[IEvent]] = None,
    polling_interval: int = 5,
) -> None:
    """
    Run the outbox publisher with registered event types

    Args:
        mediator: CQRS mediator instance
        event_types: List of event classes to register
        polling_interval: How often to check for new events (seconds)
    """
    publisher = OutboxEventPublisher(mediator=mediator, polling_interval=polling_interval)

    # Register event types if provided
    if event_types:
        publisher.register_event_types(event_types)

    # Start publishing
    await publisher.start()


# Example standalone script entry point
if __name__ == "__main__":

    async def main():
        # This would be your actual setup
        from building_blocks.cqrs import get_mediator

        mediator = get_mediator()

        # Register your event types here
        event_types = [
            # VideoProcessedEvent,
            # UserRegisteredEvent,
            # CreditConsumedEvent,
            # Add your actual event classes
        ]

        await run_outbox_publisher(mediator=mediator, event_types=event_types, polling_interval=5)

    # Run the publisher
    asyncio.run(main())
