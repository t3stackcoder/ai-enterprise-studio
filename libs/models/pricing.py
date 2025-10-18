"""
VisionScope Enhanced Pricing Database Models
Implements flexible pricing with credit purchases, dynamic pricing, overage handling, and promotions
"""

import uuid
from enum import Enum

from models.user import UUID, Base
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func


class WorkspaceStatus(str, Enum):
    ACTIVE = "active"
    PAYMENT_FAILED = "payment_failed"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"
    DELETED = "deleted"


class ProjectStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class CollaboratorRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"


class BillingPeriod(str, Enum):
    MONTHLY = "monthly"
    ANNUAL = "annual"


class TransactionType(str, Enum):
    ALLOCATION = "allocation"
    CONSUMPTION = "consumption"
    REFUND = "refund"
    PURCHASE = "purchase"
    BONUS = "bonus"
    ROLLOVER = "rollover"
    OVERAGE = "overage"


class PurchaseType(str, Enum):
    ONE_TIME = "one_time"
    OVERAGE = "overage"
    BONUS = "bonus"


class PromoType(str, Enum):
    CREDIT_BONUS = "credit_bonus"
    TIER_DISCOUNT = "tier_discount"
    FREE_TRIAL = "free_trial"


class OverageStatus(str, Enum):
    PENDING = "pending"
    INVOICED = "invoiced"
    PAID = "paid"
    FAILED = "failed"


class PricingTier(Base):
    __tablename__ = "pricing_tiers"

    tier_id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    tier_code = Column(String(50), unique=True, nullable=False, index=True)
    display_name = Column(String(100), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    credit_allocations = relationship(
        "TierCreditAllocation", back_populates="tier", cascade="all, delete-orphan"
    )
    tier_features = relationship("TierFeature", back_populates="tier", cascade="all, delete-orphan")
    workspaces = relationship("Workspace", back_populates="tier")


class TierCreditAllocation(Base):
    __tablename__ = "tier_credit_allocations"

    tier_id = Column(UUID(), ForeignKey("pricing_tiers.tier_id"), primary_key=True)
    billing_period = Column(String(20), primary_key=True)  # 'monthly', 'annual'
    base_credits = Column(Integer, nullable=False)
    bonus_credits = Column(Integer, default=0)  # Promotional/loyalty bonus
    price = Column(Numeric(10, 2), nullable=False)
    rollover_enabled = Column(Boolean, default=False)
    max_rollover_credits = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    tier = relationship("PricingTier", back_populates="credit_allocations")


class TierFeature(Base):
    __tablename__ = "tier_features"

    tier_id = Column(UUID(), ForeignKey("pricing_tiers.tier_id"), primary_key=True)
    feature_code = Column(String(50), primary_key=True)
    enabled = Column(Boolean, default=True, nullable=False)
    monthly_limit = Column(Integer)  # NULL = unlimited
    rate_limit_per_minute = Column(Integer, default=60, nullable=False)
    concurrent_limit = Column(Integer, default=1, nullable=False)
    max_input_size_mb = Column(Integer, default=10, nullable=False)
    priority_level = Column(Integer, default=5, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    tier = relationship("PricingTier", back_populates="tier_features")

    __table_args__ = (Index("idx_tier_features_feature_code", "feature_code"),)


class Workspace(Base):
    __tablename__ = "workspaces"

    workspace_id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    workspace_name = Column(String(255), nullable=False)
    description = Column(Text)
    owner_id = Column(UUID(), nullable=False, index=True)
    tier_id = Column(UUID(), ForeignKey("pricing_tiers.tier_id"), nullable=False, index=True)
    billing_period = Column(String(20), default=BillingPeriod.MONTHLY.value, nullable=False)

    storage_limit_gb = Column(Integer, default=10, nullable=False)
    max_collaborators = Column(Integer, default=1, nullable=False)

    # Overage settings
    allow_overage = Column(Boolean, default=False, nullable=False)
    overage_limit_credits = Column(Integer, default=0, nullable=False)
    overage_rate_per_credit = Column(Numeric(10, 4), default=0.05)
    current_overage_balance = Column(Integer, default=0, nullable=False)

    stripe_subscription_id = Column(String(255), unique=True)
    stripe_customer_id = Column(String(255))
    next_billing_date = Column(Date)
    status = Column(String(20), default=WorkspaceStatus.ACTIVE.value, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    tier = relationship("PricingTier", back_populates="workspaces")
    credits = relationship(
        "WorkspaceCredit", back_populates="workspace", cascade="all, delete-orphan"
    )
    credit_transactions = relationship(
        "CreditTransaction", back_populates="workspace", cascade="all, delete-orphan"
    )
    credit_purchases = relationship(
        "CreditPurchase", back_populates="workspace", cascade="all, delete-orphan"
    )
    projects = relationship(
        "WorkspaceProject", back_populates="workspace", cascade="all, delete-orphan"
    )
    collaborators = relationship(
        "WorkspaceCollaborator", back_populates="workspace", cascade="all, delete-orphan"
    )
    usage_logs = relationship("UsageLog", back_populates="workspace")
    quotas = relationship(
        "WorkspaceQuota", back_populates="workspace", cascade="all, delete-orphan"
    )
    overage_charges = relationship(
        "OverageCharge", back_populates="workspace", cascade="all, delete-orphan"
    )
    promotions = relationship(
        "WorkspacePromotion", back_populates="workspace", cascade="all, delete-orphan"
    )


class WorkspaceCollaborator(Base):
    __tablename__ = "workspace_collaborators"

    workspace_id = Column(UUID(), ForeignKey("workspaces.workspace_id"), primary_key=True)
    user_id = Column(UUID(), primary_key=True, index=True)
    role = Column(String(50), default=CollaboratorRole.EDITOR.value, nullable=False)
    invited_by = Column(UUID())
    invited_at = Column(DateTime(timezone=True), server_default=func.now())
    accepted_at = Column(DateTime(timezone=True))
    permissions = Column(JSONB)

    # Relationships
    workspace = relationship("Workspace", back_populates="collaborators")


class WorkspaceCredit(Base):
    __tablename__ = "workspace_credits"

    workspace_id = Column(UUID(), ForeignKey("workspaces.workspace_id"), primary_key=True)
    feature_code = Column(String(50), primary_key=True)
    current_credits = Column(Integer, default=0, nullable=False)
    used_this_month = Column(Integer, default=0, nullable=False)
    total_used = Column(Integer, default=0, nullable=False)
    billing_cycle_start = Column(Date, nullable=False)
    last_reset_date = Column(Date)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    workspace = relationship("Workspace", back_populates="credits")

    __table_args__ = (Index("idx_workspace_credits_workspace_id", "workspace_id"),)


class CreditTransaction(Base):
    __tablename__ = "credit_transactions"

    transaction_id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(), ForeignKey("workspaces.workspace_id"), nullable=False, index=True)
    feature_code = Column(String(50))

    transaction_type = Column(String(30), nullable=False)
    credits_delta = Column(Integer, nullable=False)  # Positive = added, negative = consumed
    balance_after = Column(Integer, nullable=False)

    reference_id = Column(UUID())  # Links to usage_log_id, purchase_id, etc.
    reference_type = Column(String(30))  # 'usage_log', 'purchase', 'billing_cycle', etc.

    description = Column(Text)
    transaction_metadata = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationships
    workspace = relationship("Workspace", back_populates="credit_transactions")

    __table_args__ = (
        Index("idx_credit_txn_workspace_created", "workspace_id", "created_at"),
        Index("idx_credit_txn_reference", "reference_id", "reference_type"),
    )


class CreditPurchase(Base):
    __tablename__ = "credit_purchases"

    purchase_id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(), ForeignKey("workspaces.workspace_id"), nullable=False, index=True)
    credits_purchased = Column(Integer, nullable=False)
    price_paid = Column(Numeric(10, 2), nullable=False)
    stripe_payment_id = Column(String(255))
    expires_at = Column(Date)  # Optional: credits expire after 90 days
    credits_remaining = Column(Integer, nullable=False)
    purchase_type = Column(String(20), default=PurchaseType.ONE_TIME.value, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    workspace = relationship("Workspace", back_populates="credit_purchases")


class WorkspaceProject(Base):
    __tablename__ = "workspace_projects"

    project_id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(), ForeignKey("workspaces.workspace_id"), nullable=False, index=True)
    project_name = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(String(20), default=ProjectStatus.ACTIVE.value, nullable=False, index=True)
    created_by = Column(UUID(), nullable=False, index=True)
    video_url = Column(String(500))
    thumbnail_url = Column(String(500))
    duration_seconds = Column(Integer)
    processing_status = Column(String(20), default=ProcessingStatus.PENDING.value, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    workspace = relationship("Workspace", back_populates="projects")
    usage_logs = relationship("UsageLog", back_populates="project")


class UsageLog(Base):
    __tablename__ = "usage_logs"

    log_id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(), ForeignKey("workspaces.workspace_id"), nullable=False)
    project_id = Column(UUID(), ForeignKey("workspace_projects.project_id"))
    user_id = Column(UUID(), nullable=False)
    feature_code = Column(String(50), nullable=False)
    credits_consumed = Column(Integer, nullable=False)
    processing_time_seconds = Column(Numeric(10, 3))
    input_size_bytes = Column(Integer)
    output_size_bytes = Column(Integer)
    request_metadata = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationships
    workspace = relationship("Workspace", back_populates="usage_logs")
    project = relationship("WorkspaceProject", back_populates="usage_logs")

    __table_args__ = (
        Index("idx_usage_logs_workspace_feature", "workspace_id", "feature_code"),
        Index("idx_usage_logs_project_id", "project_id"),
        Index("idx_usage_logs_user_created", "user_id", "created_at"),
    )


class FeatureDefinition(Base):
    __tablename__ = "feature_definitions"

    feature_code = Column(String(50), primary_key=True)
    display_name = Column(String(100), nullable=False)
    description = Column(Text)
    category = Column(String(50), nullable=False)
    default_credits_per_use = Column(Integer, default=1, nullable=False)
    gpu_intensive = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    pricing_rules = relationship(
        "FeaturePricingRule", back_populates="feature", cascade="all, delete-orphan"
    )


class FeaturePricingRule(Base):
    __tablename__ = "feature_pricing_rules"

    rule_id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    feature_code = Column(
        String(50), ForeignKey("feature_definitions.feature_code"), nullable=False, index=True
    )
    tier_id = Column(UUID(), ForeignKey("pricing_tiers.tier_id"))  # NULL = all tiers
    credits_per_use = Column(Integer, nullable=False)

    # Dynamic pricing factors
    input_size_multiplier = Column(Numeric(5, 2), default=1.0)  # Bigger files cost more
    bulk_discount_threshold = Column(Integer)  # After X uses, discount applies
    bulk_discount_rate = Column(Numeric(5, 2))  # 0.8 = 20% off bulk

    valid_from = Column(DateTime(timezone=True), nullable=False)
    valid_until = Column(DateTime(timezone=True))  # NULL = indefinite
    priority = Column(Integer, default=0, nullable=False)  # Higher priority rules win

    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    feature = relationship("FeatureDefinition", back_populates="pricing_rules")

    __table_args__ = (
        Index("idx_pricing_rules_feature_active", "feature_code", "is_active"),
        Index("idx_pricing_rules_valid_dates", "valid_from", "valid_until"),
    )


class WorkspaceQuota(Base):
    __tablename__ = "workspace_quotas"

    workspace_id = Column(UUID(), ForeignKey("workspaces.workspace_id"), primary_key=True)
    quota_type = Column(
        String(50), primary_key=True
    )  # 'api_calls_per_day', 'concurrent_jobs', 'storage_gb'

    quota_limit = Column(Integer, nullable=False)
    current_usage = Column(Integer, default=0, nullable=False)

    resets_at = Column(DateTime(timezone=True))  # For time-based quotas
    reset_frequency = Column(String(20))  # 'daily', 'monthly', 'never'

    soft_limit_threshold = Column(Integer)  # Warn at this level
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    workspace = relationship("Workspace", back_populates="quotas")


class OverageCharge(Base):
    __tablename__ = "overage_charges"

    charge_id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(), ForeignKey("workspaces.workspace_id"), nullable=False, index=True)
    billing_period_start = Column(Date, nullable=False)
    billing_period_end = Column(Date, nullable=False)

    credits_used_in_overage = Column(Integer, nullable=False)
    rate_per_credit = Column(Numeric(10, 4), nullable=False)
    total_charge = Column(Numeric(10, 2), nullable=False)

    stripe_invoice_id = Column(String(255))
    status = Column(String(20), default=OverageStatus.PENDING.value, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    workspace = relationship("Workspace", back_populates="overage_charges")


class PromotionalCode(Base):
    __tablename__ = "promotional_codes"

    promo_code = Column(String(50), primary_key=True)
    promo_type = Column(String(30), nullable=False)

    credit_bonus = Column(Integer)
    discount_percentage = Column(Numeric(5, 2))
    free_trial_days = Column(Integer)

    max_redemptions = Column(Integer)
    times_redeemed = Column(Integer, default=0, nullable=False)

    valid_from = Column(DateTime(timezone=True), nullable=False)
    valid_until = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    workspace_promotions = relationship(
        "WorkspacePromotion", back_populates="promo", cascade="all, delete-orphan"
    )


class WorkspacePromotion(Base):
    __tablename__ = "workspace_promotions"

    workspace_id = Column(UUID(), ForeignKey("workspaces.workspace_id"), primary_key=True)
    promo_code = Column(String(50), ForeignKey("promotional_codes.promo_code"), primary_key=True)
    applied_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))
    credits_granted = Column(Integer)

    # Relationships
    workspace = relationship("Workspace", back_populates="promotions")
    promo = relationship("PromotionalCode", back_populates="workspace_promotions")
