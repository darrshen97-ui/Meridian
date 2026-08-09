from __future__ import annotations

import datetime as dt

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, utcnow

DOCUMENT_KINDS = ("pdf_statement", "csv_export", "ofx")
PARSE_STATUSES = ("pending", "parsing", "parsed", "partial", "failed")


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint(f"kind IN {DOCUMENT_KINDS}", name="kind"),
        CheckConstraint(f"parse_status IN {PARSE_STATUSES}", name="parse_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"))
    kind: Mapped[str] = mapped_column(String(20))
    filename: Mapped[str] = mapped_column(String(255))
    stored_path: Mapped[str] = mapped_column(String(500))
    period_start: Mapped[dt.date | None] = mapped_column(Date)
    period_end: Mapped[dt.date | None] = mapped_column(Date)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    parse_status: Mapped[str] = mapped_column(String(20), default="pending")
    parse_error: Mapped[str | None] = mapped_column(Text)
    uploaded_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
