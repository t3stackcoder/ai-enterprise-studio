"""
CQRS Commands and Queries for Event Outbox operations
"""

import uuid
from dataclasses import dataclass
from typing import Any

from building_blocks.cqrs import ICommand, ICommandHandler, IQuery, IQueryHandler
from models.messaging.event_outbox import EventOutbox

# ============ COMMANDS (Write Operations) ============


@dataclass
class SaveEventToOutboxCommand(ICommand):
    """Command to save an event to the outbox"""

    event: Any
    correlation_id: uuid.UUID | None = None
    db_session: Any = None  # Will be injected by pipeline


@dataclass
class SaveEventsToOutboxCommand(ICommand):
    """Command to save multiple events to the outbox"""

    events: list[Any]
    correlation_id: uuid.UUID | None = None
    db_session: Any = None  # Will be injected by pipeline


@dataclass
class MarkEventAsPublishedCommand(ICommand):
    """Command to mark an event as published"""

    event_id: uuid.UUID
    db_session: Any = None  # Will be injected by pipeline


@dataclass
class MarkEventAsFailedCommand(ICommand):
    """Command to mark an event as failed"""

    event_id: uuid.UUID
    error_message: str
    db_session: Any = None  # Will be injected by pipeline


@dataclass
class CleanupPublishedEventsCommand(ICommand):
    """Command to cleanup old published events"""

    older_than_days: int = 30
    db_session: Any = None  # Will be injected by pipeline


# ============ QUERIES (Read Operations) ============


@dataclass
class GetUnpublishedEventsQuery(IQuery[list[EventOutbox]]):
    """Query to get unpublished events from outbox"""

    limit: int = 100
    db_session: Any = None  # Will be injected by pipeline

    @property
    def cache_key(self) -> str:
        return f"unpublished_events:{self.limit}"


@dataclass
class GetEventsByCorrelationIdQuery(IQuery[list[EventOutbox]]):
    """Query to get events by correlation ID"""

    correlation_id: uuid.UUID
    db_session: Any = None  # Will be injected by pipeline

    @property
    def cache_key(self) -> str:
        return f"events_by_correlation:{self.correlation_id}"


@dataclass
class GetFailedEventsQuery(IQuery[list[EventOutbox]]):
    """Query to get failed events that can be retried"""

    max_retries: int = 3
    db_session: Any = None  # Will be injected by pipeline

    @property
    def cache_key(self) -> str:
        return f"failed_events:{self.max_retries}"


# ============ COMMAND HANDLERS ============


class SaveEventToOutboxHandler(ICommandHandler[SaveEventToOutboxCommand]):
    """Handler for saving single event to outbox"""

    async def handle(self, command: SaveEventToOutboxCommand) -> None:
        if not command.db_session:
            raise ValueError("Database session is required")

        outbox_event = EventOutbox.from_event(command.event, command.correlation_id)
        command.db_session.add(outbox_event)
        # Note: Transaction will be committed by TransactionBehavior


class SaveEventsToOutboxHandler(ICommandHandler[SaveEventsToOutboxCommand]):
    """Handler for saving multiple events to outbox"""

    async def handle(self, command: SaveEventsToOutboxCommand) -> None:
        if not command.db_session:
            raise ValueError("Database session is required")

        for event in command.events:
            outbox_event = EventOutbox.from_event(event, command.correlation_id)
            command.db_session.add(outbox_event)
        # Note: Transaction will be committed by TransactionBehavior


class MarkEventAsPublishedHandler(ICommandHandler[MarkEventAsPublishedCommand]):
    """Handler for marking event as published"""

    async def handle(self, command: MarkEventAsPublishedCommand) -> None:
        if not command.db_session:
            raise ValueError("Database session is required")

        event = (
            command.db_session.query(EventOutbox).filter(EventOutbox.id == command.event_id).first()
        )

        if event:
            event.mark_as_published()
        # Note: Transaction will be committed by TransactionBehavior


class MarkEventAsFailedHandler(ICommandHandler[MarkEventAsFailedCommand]):
    """Handler for marking event as failed"""

    async def handle(self, command: MarkEventAsFailedCommand) -> None:
        if not command.db_session:
            raise ValueError("Database session is required")

        event = (
            command.db_session.query(EventOutbox).filter(EventOutbox.id == command.event_id).first()
        )

        if event:
            event.mark_as_failed(command.error_message)
        # Note: Transaction will be committed by TransactionBehavior


class CleanupPublishedEventsHandler(ICommandHandler[CleanupPublishedEventsCommand]):
    """Handler for cleaning up old published events"""

    async def handle(self, command: CleanupPublishedEventsCommand) -> None:
        if not command.db_session:
            raise ValueError("Database session is required")

        from datetime import datetime, timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=command.older_than_days)

        command.db_session.query(EventOutbox).filter(
            EventOutbox.published_at.isnot(None), EventOutbox.published_at < cutoff_date
        ).delete()
        # Note: Transaction will be committed by TransactionBehavior


# ============ QUERY HANDLERS ============


class GetUnpublishedEventsHandler(IQueryHandler[GetUnpublishedEventsQuery, list[EventOutbox]]):
    """Handler for getting unpublished events"""

    async def handle(self, query: GetUnpublishedEventsQuery) -> list[EventOutbox]:
        if not query.db_session:
            raise ValueError("Database session is required")

        return (
            query.db_session.query(EventOutbox)
            .filter(EventOutbox.published_at.is_(None))
            .order_by(EventOutbox.created_at)
            .limit(query.limit)
            .all()
        )


class GetEventsByCorrelationIdHandler(
    IQueryHandler[GetEventsByCorrelationIdQuery, list[EventOutbox]]
):
    """Handler for getting events by correlation ID"""

    async def handle(self, query: GetEventsByCorrelationIdQuery) -> list[EventOutbox]:
        if not query.db_session:
            raise ValueError("Database session is required")

        return (
            query.db_session.query(EventOutbox)
            .filter(EventOutbox.correlation_id == query.correlation_id)
            .order_by(EventOutbox.created_at)
            .all()
        )


class GetFailedEventsHandler(IQueryHandler[GetFailedEventsQuery, list[EventOutbox]]):
    """Handler for getting failed events"""

    async def handle(self, query: GetFailedEventsQuery) -> list[EventOutbox]:
        if not query.db_session:
            raise ValueError("Database session is required")

        return (
            query.db_session.query(EventOutbox)
            .filter(
                EventOutbox.published_at.is_(None),
                EventOutbox.retry_count < query.max_retries,
                EventOutbox.error_message.isnot(None),
            )
            .order_by(EventOutbox.created_at)
            .all()
        )
