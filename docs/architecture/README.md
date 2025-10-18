# VisionScope Architecture Documentation

## Overview

VisionScope is built on enterprise-grade architectural patterns designed for scalability, maintainability, and revenue optimization. This documentation covers the foundational systems that power our conversational video analysis platform.

## Core Architecture Components

### 🏗️ [CQRS Building Blocks](./CQRS_BUILDING_BLOCKS.md)

**Command Query Responsibility Segregation patterns for clean business logic**

- **Purpose**: Separate read/write operations for scalable business logic
- **Key Benefits**: Clean separation of concerns, testable handlers, scalable architecture
- **Business Value**: Faster development, easier maintenance, enterprise-ready patterns

### 📨 [Event-Driven Messaging](./MESSAGING_ARCHITECTURE.md)

**Celery + Redis messaging system for real-time operations**

- **Purpose**: Decouple systems through events and handle complex side effects
- **Key Benefits**: Real-time billing, scalable processing, reliable message delivery
- **Business Value**: Revenue-critical operations, usage tracking, investor-ready infrastructure

### 📦 [Transactional Outbox Pattern](./TRANSACTIONAL_OUTBOX.md)

**Reliable event publishing with ACID guarantees**

- **Purpose**: Solve dual-write problem and ensure zero event loss
- **Key Benefits**: Transactional consistency, automatic retry, complete audit trail
- **Business Value**: Bulletproof billing operations, regulatory compliance, enterprise reliability

### 💰 [Complete Pricing System](./PRICING_FEATURE_GROUPING.md)

**Enterprise pricing system with Feature Grouping + Building Blocks + ALL Side Effects Handled**

- **Purpose**: Complete pricing architecture with automatic side effect handling for all FK relationships
- **Key Benefits**: Zero side effects missed, transactional consistency, enterprise-grade reliability
- **Business Value**: Bulletproof billing, automated business processes, zero data inconsistencies

## Architecture Principles

### 1. **Clean Architecture**

```
Presentation Layer (FastAPI)
    ↓
Application Layer (CQRS Handlers)
    ↓
Domain Layer (Business Rules)
    ↓
Infrastructure Layer (Database, Messaging)
```

### 2. **Event-Driven Design**

```
Business Operation
    ↓
Command Handler (CQRS)
    ↓
Database Update + Event Publication
    ↓
Side Effects (Messaging)
    ↓
Analytics, Billing, Notifications
```

### 3. **Dependency Injection**

- Controllers depend on abstractions, not implementations
- Easy testing with mock dependencies
- Runtime configuration of services

## Technology Stack

### **Core Framework**

- **FastAPI** - High-performance async API framework
- **SQLAlchemy** - ORM with async support
- **Pydantic** - Data validation and serialization

### **Architecture Patterns**

- **CQRS** - Command/Query separation with mediator pattern
- **Event Sourcing** - Business events for audit trails and analytics
- **Domain-Driven Design** - Rich domain models with clear boundaries

### **Infrastructure**

- **Celery** - Distributed task queue for background processing
- **Redis** - Message broker and caching layer
- **PostgreSQL** - Primary database with JSONB support

## System Integration

### Request Flow Example

```
1. FastAPI Endpoint receives request
2. Controller creates Command/Query
3. Mediator routes to appropriate Handler
4. Handler executes business logic
5. Database updated through Repository
6. Events published to Message Bus
7. Celery workers process side effects
8. Response returned to client
```

### Side Effect Coordination

```
Primary Action (e.g., Video Analysis)
    ├── Credit Deduction (CQRS Command)
    ├── Usage Logging (Database Update)
    ├── Analytics Event (Message Bus)
    ├── Billing Notification (Async Task)
    └── User Notification (Background Job)
```

## Business Logic Organization

### **Features Structure**

```
features/
├── billing/
│   ├── commands/          # Credit operations
│   ├── queries/           # Usage reports
│   ├── handlers/          # Business logic
│   └── events/            # Billing events
├── video_processing/
│   ├── commands/          # Analysis operations
│   ├── queries/           # Results retrieval
│   └── handlers/          # Processing logic
└── workspace_management/
    ├── commands/          # Workspace operations
    ├── queries/           # Workspace data
    └── handlers/          # Management logic
```

### **Shared Components**

```
building_blocks/
├── cqrs/                  # Command/Query infrastructure
├── messaging/             # Event-driven messaging
├── exceptions/            # Domain error handling
└── behaviors/             # Cross-cutting concerns
```

## Data Architecture

### **8-Table Pricing Model**

1. **PricingTier** - Subscription levels (Free, Pro, Enterprise)
2. **TierFeature** - Feature availability per tier
3. **Workspace** - Customer billing units
4. **WorkspaceCredit** - Credit pools per feature
5. **WorkspaceCollaborator** - Team access management
6. **WorkspaceProject** - Project-based organization
7. **UsageLog** - Detailed operation tracking
8. **FeatureDefinition** - Feature metadata and pricing

### **Foreign Key Relationships**

```
PricingTier → Workspace → WorkspaceCredit
           ↓           ↓
    TierFeature   WorkspaceProject → UsageLog
                       ↓
               WorkspaceCollaborator
```

## Scalability Strategy

### **Horizontal Scaling**

- **API Layer**: Multiple FastAPI instances behind load balancer
- **Worker Layer**: Celery workers across multiple servers
- **Database**: Read replicas for query scaling

### **Queue Strategy**

- **High Priority**: `billing` queue for revenue operations
- **GPU Intensive**: `video_processing` queue with dedicated workers
- **Background**: `notifications` and `analytics` queues

### **Caching Strategy**

- **Redis**: Session data, frequent queries, rate limiting
- **Application**: Query result caching in CQRS handlers
- **CDN**: Static assets and processed video thumbnails

## Monitoring & Operations

### **Business Metrics**

- Revenue per hour (credits consumed × pricing)
- User engagement (videos processed per workspace)
- System performance (processing time per operation)

### **Technical Metrics**

- API response times and error rates
- Queue depth and processing times
- Database query performance
- Resource utilization (CPU, memory, GPU)

### **Alerting Strategy**

- **Critical**: Payment processing failures, system downtime
- **Warning**: High queue depth, slow processing times
- **Info**: Usage milestones, performance trends

## Development Workflow

### **New Feature Development**

1. Define domain models and business rules
2. Create Commands/Queries with handlers
3. Implement repository interfaces
4. Add FastAPI endpoints with dependency injection
5. Write unit tests for handlers
6. Add integration tests for full flows

### **Testing Strategy**

- **Unit Tests**: Individual CQRS handlers
- **Integration Tests**: Full request flows through mediator
- **End-to-End Tests**: API endpoints with real database
- **Performance Tests**: High-volume scenarios

## Security Architecture

### **Authentication & Authorization**

- JWT tokens for stateless authentication
- Role-based access control (RBAC) with workspace isolation
- API key authentication for service-to-service calls

### **Data Protection**

- Database encryption at rest
- TLS encryption for all API communications
- PII data handling with audit trails

---

## Getting Started

1. **Review [CQRS Building Blocks](./CQRS_BUILDING_BLOCKS.md)** - Understand command/query patterns
2. **Study [Messaging Architecture](./MESSAGING_ARCHITECTURE.md)** - Learn event-driven patterns
3. **Explore existing handlers** in `features/` directories
4. **Follow development patterns** established in the codebase

**This architecture provides the enterprise-grade foundation that makes VisionScope scalable, maintainable, and revenue-optimized for investor success.** 🚀💰
