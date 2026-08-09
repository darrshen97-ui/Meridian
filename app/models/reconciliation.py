from __future__ import annotations

import datetime as dt

from sqlalchemy import BigInteger, CheckConstraint, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, utcnow

RECONCILIATION_STATUSES = ("clean", "findings", "running", "failed")
FINDING_KINDS = (
    "missing_in_provider",
    "missing_in_statement",
    "amount_mismatch",
    "duplicate_suspected",
    "date_shift",
)
SYNC_STATUSES = ("running", "succeeded", "failed", "partial")


class Reconciliation(Base):
    __tablename__ = "reconciliations"
    __table_args__ = (
        CheckConstraint(f"status IN {RECONCILIATION_STATUSES}", name="status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    period_start: Mapped[dt.date] = mapped_column(Date)
    period_end: Mapped[dt.date] = mapped_column(Date)
    statement_ending_minor: Mapped[int | None] = mapped_column(BigInteger)
    computed_ending_minor: Mapped[int | None] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(20))
    run_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ReconciliationFinding(Base):
    __tablename__ = "reconciliation_findings"
    __table_args__ = (CheckConstraint(f"kind IN {FINDING_KINDS}", name="kind"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    reconciliation_id: Mapped[int] = mapped_column(
        ForeignKey("reconciliations.id"), index=True
    )
    kind: Mapped[str] = mapped_column(String(30))
    transaction_id: Mapped[int | None] = mapped_column(ForeignKey("transactions.id"))
    counterpart_id: Mapped[int | None] = mapped_column(ForeignKey("transactions.id"))
    delta_minor: Mapped[int | None] = mapped_column(BigInteger)
    narrative: Mapped[str | None] = mapped_column(Text)
    resolved_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))


class SyncRun(Base):
    __tablename__ = "sync_runs"
    __table_args__ = (CheckConstraint(f"status IN {SYNC_STATUSES}", name="status"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    provider_key: Mapped[str] = mapped_column(String(60))
    started_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="running")
    cursor: Mapped[str | None] = mapped_column(String(255))
    records_ingested: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text)
