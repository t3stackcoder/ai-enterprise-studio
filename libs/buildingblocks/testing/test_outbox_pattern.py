"""
Outbox Pattern Tests

Tests the transactional outbox pattern implementation including event persistence,
CQRS outbox commands/queries, and integration with pipeline behaviors.
These tests verify that domain events are reliably saved and can be published.
"""

from uuid import uuid4

import pytest
from building_blocks.behaviors.pipeline_behaviors import OutboxBehavior
from building_blocks.messaging.outbox_cqrs import (
    GetUnpublishedEventsHandler,
    GetUnpublishedEventsQuery,
    MarkEventAsPublishedCommand,
    MarkEventAsPublishedHandler,
    SaveEventsToOutboxCommand,
    SaveEventsToOutboxHandler,
    SaveEventToOutboxCommand,
    SaveEventToOutboxHandler,
)
from infrastructure_testing.mocks import MockDomainEvent
from models.messaging.event_outbox import EventOutbox
from sqlalchemy.orm import Session

from .builders import BBOutboxBuilder, BBTestCreateUserCommand


class TestOutboxBehavior:
    """Test outbox pipeline behavior"""

    @pytest.mark.asyncio
    async def test_outbox_behavior_saves_domain_events_on_success(self, test_db_session: Session):
        """REAL TEST: Events are persisted when command succeeds"""
        # Given: Command with domain events and outbox behavior
        from building_blocks.cqrs.mediator import EnterpriseMediator

        mediator = EnterpriseMediator()

        # Register outbox handlers with mediator
        mediator.register_command_handler(SaveEventToOutboxCommand, SaveEventToOutboxHandler())
        mediator.register_command_handler(SaveEventsToOutboxCommand, SaveEventsToOutboxHandler())

        outbox_behavior = OutboxBehavior(mediator=mediator)

        # Create command with domain events
        command = BBTestCreateUserCommand(username="outboxtest", email="outbox@example.com")
        command.domain_events = [
            MockDomainEvent(event_type="UserCreatedEvent", username="outboxtest"),
            MockDomainEvent(event_type="EmailValidatedEvent", email="outbox@example.com"),
        ]
        command.correlation_id = str(uuid4())
        command.db_session = test_db_session

        async def successful_handler():
            return "user_created"

        # When: Execute command through outbox behavior
        result = await outbox_behavior.handle(command, successful_handler)
        test_db_session.commit()  # Commit the transaction

        # Then: Command succeeds and events are saved to outbox
        assert result == "user_created"

        # Verify events were saved to database
        saved_events = test_db_session.query(EventOutbox).all()
        assert len(saved_events) == 2

        event_types = [event.event_type for event in saved_events]
        assert "UserCreatedEvent" in event_types
        assert "EmailValidatedEvent" in event_types

        # All events should have same correlation ID
        for event in saved_events:
            assert str(event.correlation_id) == command.correlation_id
            assert event.published_at is None  # Not published yet

    @pytest.mark.asyncio
    async def test_outbox_behavior_does_not_save_events_on_failure(self, test_db_session: Session):
        """REAL TEST: Events are not saved when command fails"""
        # Given: Command with domain events but failing handler
        from building_blocks.cqrs.mediator import EnterpriseMediator

        mediator = EnterpriseMediator()
        mediator.register_command_handler(SaveEventToOutboxCommand, SaveEventToOutboxHandler())

        outbox_behavior = OutboxBehavior(mediator=mediator)

        command = BBTestCreateUserCommand(username="failtest", email="fail@example.com")
        command.domain_events = [MockDomainEvent(event_type="ShouldNotBeSavedEvent")]
        command.db_session = test_db_session

        def failing_handler():
            return exec('raise Exception("Command failed!")')

        # When: Command fails
        with pytest.raises(Exception, match="Command failed!"):
            await outbox_behavior.handle(command, failing_handler)

        # Then: No events should be saved
        saved_events = test_db_session.query(EventOutbox).all()
        assert len(saved_events) == 0

    @pytest.mark.asyncio
    async def test_outbox_behavior_skips_queries(self, test_db_session: Session):
        """REAL TEST: Outbox behavior only processes commands, not queries"""
        # Given: Query (not command) with mock events
        from building_blocks.cqrs.mediator import EnterpriseMediator

        from .builders import BBTestGetUserQuery

        mediator = EnterpriseMediator()
        outbox_behavior = OutboxBehavior(mediator=mediator)

        query = BBTestGetUserQuery(user_id="123")
        query.domain_events = [MockDomainEvent(event_type="ShouldBeIgnoredEvent")]
        query.db_session = test_db_session

        async def handler():
            return {"user_id": "123", "username": "test"}

        # When: Execute query through outbox behavior
        result = await outbox_behavior.handle(query, handler)

        # Then: Query succeeds but no events saved (queries don't have events)
        assert result == {"user_id": "123", "username": "test"}

        saved_events = test_db_session.query(EventOutbox).all()
        assert len(saved_events) == 0


class TestOutboxCQRSCommands:
    """Test CQRS commands for outbox operations"""

    @pytest.mark.asyncio
    async def test_save_event_to_outbox_command(self, test_db_session: Session):
        """REAL TEST: SaveEventToOutboxCommand persists single event"""
        # Given: Save event command and handler
        handler = SaveEventToOutboxHandler()
        event = MockDomainEvent(event_type="TestEvent", data="test_data")
        correlation_id = uuid4()

        command = SaveEventToOutboxCommand(
            event=event, correlation_id=correlation_id, db_session=test_db_session
        )

        # When: Execute save command
        await handler.handle(command)
        test_db_session.commit()  # Commit the transaction

        # Then: Event should be saved to database
        saved_events = test_db_session.query(EventOutbox).all()
        assert len(saved_events) == 1

        saved_event = saved_events[0]
        assert saved_event.event_type == "TestEvent"
        assert saved_event.correlation_id == correlation_id
        assert saved_event.published_at is None

    @pytest.mark.asyncio
    async def test_save_multiple_events_to_outbox_command(self, test_db_session: Session):
        """REAL TEST: SaveEventsToOutboxCommand persists multiple events"""
        # Given: Save multiple events command
        handler = SaveEventsToOutboxHandler()
        events = [
            MockDomainEvent(event_type="Event1", data="data1"),
            MockDomainEvent(event_type="Event2", data="data2"),
            MockDomainEvent(event_type="Event3", data="data3"),
        ]
        correlation_id = uuid4()

        command = SaveEventsToOutboxCommand(
            events=events, correlation_id=correlation_id, db_session=test_db_session
        )

        # When: Execute save command
        await handler.handle(command)
        test_db_session.commit()  # Commit the transaction

        # Then: All events should be saved
        saved_events = test_db_session.query(EventOutbox).all()
        assert len(saved_events) == 3

        event_types = [event.event_type for event in saved_events]
        assert "Event1" in event_types
        assert "Event2" in event_types
        assert "Event3" in event_types

        # All should have same correlation ID
        for event in saved_events:
            assert event.correlation_id == correlation_id


class TestOutboxCQRSQueries:
    """Test CQRS queries for outbox operations"""

    @pytest.mark.asyncio
    async def test_get_unpublished_events_query(self, test_db_session: Session):
        """REAL TEST: Query returns only unpublished events"""
        # Given: Mix of published and unpublished events
        published_event = EventOutbox.from_event(
            MockDomainEvent(event_type="PublishedEvent"), correlation_id=uuid4()
        )
        published_event.mark_as_published()

        unpublished_event1 = EventOutbox.from_event(
            MockDomainEvent(event_type="UnpublishedEvent1"), correlation_id=uuid4()
        )

        unpublished_event2 = EventOutbox.from_event(
            MockDomainEvent(event_type="UnpublishedEvent2"), correlation_id=uuid4()
        )

        test_db_session.add_all([published_event, unpublished_event1, unpublished_event2])
        test_db_session.commit()

        # When: Query for unpublished events
        query = GetUnpublishedEventsQuery(limit=10, db_session=test_db_session)
        handler = GetUnpublishedEventsHandler()

        events = await handler.handle(query)

        # Then: Should return only unpublished events
        assert len(events) == 2
        event_types = [event.event_type for event in events]
        assert "UnpublishedEvent1" in event_types
        assert "UnpublishedEvent2" in event_types
        assert "PublishedEvent" not in event_types

    @pytest.mark.asyncio
    async def test_mark_event_as_published_command(self, test_db_session: Session):
        """REAL TEST: Command marks event as published"""
        # Given: Unpublished event in database
        event = EventOutbox.from_event(
            MockDomainEvent(event_type="ToBePublishedEvent"), correlation_id=uuid4()
        )
        test_db_session.add(event)
        test_db_session.commit()

        # Verify it's unpublished
        assert event.published_at is None

        # When: Mark as published
        command = MarkEventAsPublishedCommand(event_id=event.id, db_session=test_db_session)
        handler = MarkEventAsPublishedHandler()

        await handler.handle(command)
        test_db_session.commit()  # Commit the transaction

        # Then: Event should be marked as published
        test_db_session.refresh(event)
        assert event.published_at is not None


class TestOutboxBuilder:
    """Test outbox builder utility"""

    def test_outbox_builder_creates_command_with_events(self):
        """REAL TEST: Builder creates commands with domain events"""
        # Given: Outbox builder with events
        builder = BBOutboxBuilder()
        correlation_id = str(uuid4())

        # When: Build command with events
        command = (
            builder.with_domain_event("UserCreatedEvent", username="buildertest")
            .with_domain_event("EmailSentEvent", email="builder@example.com")
            .with_correlation_id(correlation_id)
            .build_command_with_events()
        )

        # Then: Command should have events attached
        assert len(command.domain_events) == 2
        assert command.correlation_id == correlation_id

        event_types = [event.event_type for event in command.domain_events]
        assert "UserCreatedEvent" in event_types
        assert "EmailSentEvent" in event_types

        # All events should have correlation ID
        for event in command.domain_events:
            assert event.correlation_id == correlation_id


class TestOutboxIntegration:
    """Test outbox pattern integration with full pipeline"""

    @pytest.mark.asyncio
    async def test_full_pipeline_with_outbox_saves_events_transactionally(
        self, test_db_session: Session
    ):
        """REAL TEST: Full pipeline with transaction and outbox behaviors"""
        # Given: Mediator with transaction and outbox behaviors
        from building_blocks.behaviors.pipeline_behaviors import TransactionBehavior
        from building_blocks.cqrs.mediator import EnterpriseMediator

        mediator = EnterpriseMediator()

        # Register outbox handlers
        mediator.register_command_handler(SaveEventToOutboxCommand, SaveEventToOutboxHandler())
        mediator.register_command_handler(SaveEventsToOutboxCommand, SaveEventsToOutboxHandler())

        # Add behaviors in order: transaction → outbox
        mediator.add_pipeline_behavior(TransactionBehavior(auto_commit=True))
        mediator.add_pipeline_behavior(OutboxBehavior(mediator=mediator))

        # Register test handler
        from infrastructure_testing.mocks import MockHandler

        test_handler = MockHandler(response="integration_success")
        mediator.register_command_handler(BBTestCreateUserCommand, test_handler)

        # When: Send command with events through full pipeline
        command = BBTestCreateUserCommand(username="integration", email="integration@example.com")
        command.domain_events = [
            MockDomainEvent(event_type="IntegrationTestEvent", username="integration")
        ]
        command.requires_transaction = True
        command.db_session = test_db_session
        command.correlation_id = str(uuid4())

        await mediator.send_command(command)

        # Then: Command executed and events saved in same transaction
        test_handler.assert_called_once_with("handle", command)

        saved_events = test_db_session.query(EventOutbox).all()
        assert len(saved_events) == 1
        assert saved_events[0].event_type == "IntegrationTestEvent"
        assert str(saved_events[0].correlation_id) == command.correlation_id
