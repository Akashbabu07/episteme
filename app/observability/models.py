import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class RunRecord(Base):
    __tablename__ = "runs"

   id:Mapped[uuid.UUID]=mapped_column(primary_key=True,default=uuid.uuid4)
   question: Mapped[str] = mapped_column(Text)
       status: Mapped[str] = mapped_column(String(50), default="running")
       final_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
       stopped_reason: Mapped[str | None] = mapped_column(String(50), nullable=True)
       total_input_tokens: Mapped[int] = mapped_column(Integer, default=0)
       total_output_tokens: Mapped[int] = mapped_column(Integer, default=0)
       started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
       finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)





class StepRecord(Base):
    __tablename__ = "steps"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("runs.id"))
    step_number: Mapped[int] = mapped_column(Integer)
    step_type: Mapped[str] = mapped_column(String(50))
    input_data: Mapped[dict] = mapped_column(JSON)
    output_data: Mapped[dict] = mapped_column(JSON)
    tool_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

