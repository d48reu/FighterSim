"""SQLAlchemy ORM models for MMA Management Simulator."""

from __future__ import annotations

import enum
from datetime import date
from typing import Optional, List

from sqlalchemy import (
    Boolean, Column, Date, Enum, Float, ForeignKey, Index,
    Integer, String, Text, CheckConstraint
)
from sqlalchemy.orm import relationship, Mapped

from .database import Base


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class WeightClass(str, enum.Enum):
    FLYWEIGHT = "Flyweight"
    LIGHTWEIGHT = "Lightweight"
    WELTERWEIGHT = "Welterweight"
    MIDDLEWEIGHT = "Middleweight"
    HEAVYWEIGHT = "Heavyweight"


class FightMethod(str, enum.Enum):
    KO_TKO = "KO/TKO"
    SUBMISSION = "Submission"
    UNANIMOUS_DECISION = "Unanimous Decision"
    SPLIT_DECISION = "Split Decision"
    MAJORITY_DECISION = "Majority Decision"


class FighterStyle(str, enum.Enum):
    STRIKER = "Striker"
    GRAPPLER = "Grappler"
    WRESTLER = "Wrestler"
    WELL_ROUNDED = "Well-Rounded"


class ContractStatus(str, enum.Enum):
    ACTIVE = "Active"
    EXPIRED = "Expired"
    TERMINATED = "Terminated"


class EventStatus(str, enum.Enum):
    SCHEDULED = "Scheduled"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"


class Archetype(str, enum.Enum):
    PHENOM         = "Phenom"
    LATE_BLOOMER   = "Late Bloomer"
    GATEKEEPER     = "Gatekeeper"
    JOURNEYMAN     = "Journeyman"
    GOAT_CANDIDATE = "GOAT Candidate"
    SHOOTING_STAR  = "Shooting Star"


# ---------------------------------------------------------------------------
# Fighter
# ---------------------------------------------------------------------------

class Fighter(Base):
    """Represents a fighter in the simulation."""

    __tablename__ = "fighters"

    id: Mapped[int] = Column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = Column(String(100), nullable=False)
    nickname: Mapped[Optional[str]] = Column(String(30), nullable=True)
    age: Mapped[int] = Column(Integer, nullable=False)
    nationality: Mapped[str] = Column(String(60), nullable=False)
    weight_class: Mapped[str] = Column(Enum(WeightClass), nullable=False)
    style: Mapped[str] = Column(Enum(FighterStyle), nullable=False)

    # Core attributes (1–100)
    striking: Mapped[int] = Column(Integer, nullable=False)
    grappling: Mapped[int] = Column(Integer, nullable=False)
    wrestling: Mapped[int] = Column(Integer, nullable=False)
    cardio: Mapped[int] = Column(Integer, nullable=False)
    chin: Mapped[int] = Column(Integer, nullable=False)
    speed: Mapped[int] = Column(Integer, nullable=False)

    # Career info
    wins: Mapped[int] = Column(Integer, default=0)
    losses: Mapped[int] = Column(Integer, default=0)
    draws: Mapped[int] = Column(Integer, default=0)
    ko_wins: Mapped[int] = Column(Integer, default=0)
    sub_wins: Mapped[int] = Column(Integer, default=0)

    # Prime age range
    prime_start: Mapped[int] = Column(Integer, nullable=False)
    prime_end: Mapped[int] = Column(Integer, nullable=False)

    # Condition (0–100) and injury months remaining
    condition: Mapped[float] = Column(Float, default=100.0)
    injury_months: Mapped[int] = Column(Integer, default=0)

    # Rankings score (cached)
    ranking_score: Mapped[float] = Column(Float, default=0.0)

    # Narrative engine fields
    archetype: Mapped[Optional[str]] = Column(Enum(Archetype), nullable=True)
    narrative_tags: Mapped[Optional[str]] = Column(Text, default="[]")
    popularity: Mapped[float] = Column(Float, default=10.0)
    hype: Mapped[float] = Column(Float, default=10.0)
    rivalry_with: Mapped[Optional[int]] = Column(Integer, ForeignKey("fighters.id"), nullable=True)
    goat_score: Mapped[float] = Column(Float, default=0.0)
    traits: Mapped[Optional[str]] = Column(Text, default="[]")

    # Relationships
    contracts: Mapped[List["Contract"]] = relationship(
        "Contract", back_populates="fighter", cascade="all, delete-orphan"
    )
    fights_as_a: Mapped[List["Fight"]] = relationship(
        "Fight", foreign_keys="Fight.fighter_a_id", back_populates="fighter_a"
    )
    fights_as_b: Mapped[List["Fight"]] = relationship(
        "Fight", foreign_keys="Fight.fighter_b_id", back_populates="fighter_b"
    )

    __table_args__ = (
        Index("ix_fighter_weight_class", "weight_class"),
        Index("ix_fighter_age", "age"),
        CheckConstraint("striking BETWEEN 1 AND 100"),
        CheckConstraint("grappling BETWEEN 1 AND 100"),
        CheckConstraint("wrestling BETWEEN 1 AND 100"),
        CheckConstraint("cardio BETWEEN 1 AND 100"),
        CheckConstraint("chin BETWEEN 1 AND 100"),
        CheckConstraint("speed BETWEEN 1 AND 100"),
    )

    @property
    def record(self) -> str:
        return f"{self.wins}-{self.losses}-{self.draws}"

    @property
    def finish_rate(self) -> float:
        if self.wins == 0:
            return 0.0
        return (self.ko_wins + self.sub_wins) / self.wins

    @property
    def overall(self) -> int:
        """Weighted overall rating."""
        return round(
            self.striking * 0.2
            + self.grappling * 0.2
            + self.wrestling * 0.15
            + self.cardio * 0.15
            + self.chin * 0.15
            + self.speed * 0.15
        )

    def __repr__(self) -> str:
        return f"<Fighter {self.name} ({self.weight_class}, {self.record})>"


# ---------------------------------------------------------------------------
# Organization
# ---------------------------------------------------------------------------

class Organization(Base):
    """Represents an MMA promotion."""

    __tablename__ = "organizations"

    id: Mapped[int] = Column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = Column(String(120), nullable=False)
    prestige: Mapped[float] = Column(Float, default=50.0)
    bank_balance: Mapped[float] = Column(Float, default=1_000_000.0)
    is_player: Mapped[bool] = Column(Boolean, default=False)

    contracts: Mapped[List["Contract"]] = relationship(
        "Contract", back_populates="organization", cascade="all, delete-orphan"
    )
    events: Mapped[List["Event"]] = relationship(
        "Event", back_populates="organization", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Organization {self.name} prestige={self.prestige:.1f}>"


# ---------------------------------------------------------------------------
# Contract
# ---------------------------------------------------------------------------

class Contract(Base):
    """A fighter's contract with an organization."""

    __tablename__ = "contracts"

    id: Mapped[int] = Column(Integer, primary_key=True, autoincrement=True)
    fighter_id: Mapped[int] = Column(Integer, ForeignKey("fighters.id"), nullable=False)
    organization_id: Mapped[int] = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    status: Mapped[str] = Column(Enum(ContractStatus), default=ContractStatus.ACTIVE)
    salary: Mapped[float] = Column(Float, nullable=False)
    fight_count_total: Mapped[int] = Column(Integer, nullable=False)  # fights in contract
    fights_remaining: Mapped[int] = Column(Integer, nullable=False)
    expiry_date: Mapped[date] = Column(Date, nullable=False)

    fighter: Mapped["Fighter"] = relationship("Fighter", back_populates="contracts")
    organization: Mapped["Organization"] = relationship("Organization", back_populates="contracts")

    __table_args__ = (
        Index("ix_contract_expiry", "expiry_date"),
        Index("ix_contract_fighter", "fighter_id"),
    )

    def __repr__(self) -> str:
        return f"<Contract fighter_id={self.fighter_id} org_id={self.organization_id} status={self.status}>"


# ---------------------------------------------------------------------------
# Event
# ---------------------------------------------------------------------------

class Event(Base):
    """An MMA event with a fight card."""

    __tablename__ = "events"

    id: Mapped[int] = Column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = Column(String(120), nullable=False)
    event_date: Mapped[date] = Column(Date, nullable=False)
    venue: Mapped[str] = Column(String(120), nullable=False)
    organization_id: Mapped[int] = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    status: Mapped[str] = Column(Enum(EventStatus), default=EventStatus.COMPLETED)
    has_press_conference: Mapped[bool] = Column(Boolean, default=False)
    gate_revenue: Mapped[float] = Column(Float, default=0.0)
    ppv_buys: Mapped[int] = Column(Integer, default=0)

    organization: Mapped["Organization"] = relationship("Organization", back_populates="events")
    fights: Mapped[List["Fight"]] = relationship(
        "Fight", back_populates="event", cascade="all, delete-orphan",
        order_by="Fight.card_position"
    )

    __table_args__ = (
        Index("ix_event_date", "event_date"),
    )

    @property
    def total_revenue(self) -> float:
        return self.gate_revenue + self.ppv_buys * 45.0

    def __repr__(self) -> str:
        return f"<Event {self.name} on {self.event_date}>"


# ---------------------------------------------------------------------------
# Fight
# ---------------------------------------------------------------------------

class Fight(Base):
    """A single bout result."""

    __tablename__ = "fights"

    id: Mapped[int] = Column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[int] = Column(Integer, ForeignKey("events.id"), nullable=False)
    fighter_a_id: Mapped[int] = Column(Integer, ForeignKey("fighters.id"), nullable=False)
    fighter_b_id: Mapped[int] = Column(Integer, ForeignKey("fighters.id"), nullable=False)
    weight_class: Mapped[str] = Column(Enum(WeightClass), nullable=False)
    card_position: Mapped[int] = Column(Integer, default=0)

    is_title_fight: Mapped[bool] = Column(Boolean, default=False)

    press_conference: Mapped[Optional[str]] = Column(Text, nullable=True)

    # Result
    winner_id: Mapped[Optional[int]] = Column(Integer, ForeignKey("fighters.id"), nullable=True)
    method: Mapped[Optional[str]] = Column(Enum(FightMethod), nullable=True)
    round_ended: Mapped[Optional[int]] = Column(Integer, nullable=True)
    time_ended: Mapped[Optional[str]] = Column(String(10), nullable=True)
    narrative: Mapped[Optional[str]] = Column(Text, nullable=True)

    event: Mapped["Event"] = relationship("Event", back_populates="fights")
    fighter_a: Mapped["Fighter"] = relationship(
        "Fighter", foreign_keys=[fighter_a_id], back_populates="fights_as_a"
    )
    fighter_b: Mapped["Fighter"] = relationship(
        "Fighter", foreign_keys=[fighter_b_id], back_populates="fights_as_b"
    )

    __table_args__ = (
        Index("ix_fight_event", "event_id"),
        Index("ix_fight_fighter_a", "fighter_a_id"),
        Index("ix_fight_fighter_b", "fighter_b_id"),
    )

    def __repr__(self) -> str:
        return f"<Fight {self.fighter_a_id} vs {self.fighter_b_id} — {self.method}>"


# ---------------------------------------------------------------------------
# Rankings cache
# ---------------------------------------------------------------------------

class Ranking(Base):
    """Cached ranking entry per weight class."""

    __tablename__ = "rankings"

    id: Mapped[int] = Column(Integer, primary_key=True, autoincrement=True)
    weight_class: Mapped[str] = Column(Enum(WeightClass), nullable=False)
    fighter_id: Mapped[int] = Column(Integer, ForeignKey("fighters.id"), nullable=False)
    rank: Mapped[int] = Column(Integer, nullable=False)
    score: Mapped[float] = Column(Float, nullable=False)
    dirty: Mapped[bool] = Column(Boolean, default=True)

    __table_args__ = (
        Index("ix_ranking_weight_class", "weight_class"),
    )


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

class Notification(Base):
    """Lightweight event log for contract and finance alerts."""

    __tablename__ = "notifications"

    id: Mapped[int] = Column(Integer, primary_key=True, autoincrement=True)
    message: Mapped[str] = Column(String(300), nullable=False)
    type: Mapped[str] = Column(String(50), nullable=False)
    created_date: Mapped[date] = Column(Date, nullable=False)
    read: Mapped[bool] = Column(Boolean, default=False)


# ---------------------------------------------------------------------------
# Game State
# ---------------------------------------------------------------------------

class GameState(Base):
    """Persistent game clock and player org reference."""

    __tablename__ = "game_state"

    id: Mapped[int] = Column(Integer, primary_key=True)
    current_date: Mapped[date] = Column(Date, nullable=False)
    player_org_id: Mapped[Optional[int]] = Column(Integer, ForeignKey("organizations.id"), nullable=True)


# ---------------------------------------------------------------------------
# Training Camps & Fighter Development
# ---------------------------------------------------------------------------

class TrainingCamp(Base):
    """A training facility where fighters develop their skills."""

    __tablename__ = "training_camps"

    id: Mapped[int] = Column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = Column(String(100), nullable=False)
    specialty: Mapped[str] = Column(String(50), nullable=False)
    tier: Mapped[int] = Column(Integer, nullable=False)
    cost_per_month: Mapped[float] = Column(Float, nullable=False)
    prestige_required: Mapped[float] = Column(Float, default=0.0)
    slots: Mapped[int] = Column(Integer, nullable=False)

    def __repr__(self) -> str:
        return f"<TrainingCamp {self.name} T{self.tier}>"


class FighterDevelopment(Base):
    """Tracks a fighter's training assignment and progress."""

    __tablename__ = "fighter_development"

    id: Mapped[int] = Column(Integer, primary_key=True, autoincrement=True)
    fighter_id: Mapped[int] = Column(Integer, ForeignKey("fighters.id"), nullable=False)
    camp_id: Mapped[Optional[int]] = Column(Integer, ForeignKey("training_camps.id"), nullable=True)
    focus: Mapped[str] = Column(String(50), nullable=False, default="Balanced")
    months_at_camp: Mapped[int] = Column(Integer, default=0)
    total_development_spend: Mapped[float] = Column(Float, default=0.0)
    last_trained: Mapped[Optional[date]] = Column(Date, nullable=True)

    fighter: Mapped["Fighter"] = relationship("Fighter")
    camp: Mapped[Optional["TrainingCamp"]] = relationship("TrainingCamp")

    __table_args__ = (
        Index("ix_dev_fighter", "fighter_id"),
    )
