import os
from sqlalchemy import String, Text, Integer, DateTime, Date, Boolean, func, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

EMBED_DIM = int(os.getenv("EMBED_DIM", "768"))  # keep in sync with Alembic migration (see alembic/versions)

class Base(DeclarativeBase):
    pass

class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    doc_id: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(500))
    
    # Legacy field (kept for backward compatibility)
    version_date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    # Version control fields
    version_major: Mapped[int] = mapped_column(Integer, default=1, server_default="1", index=True)
    version_minor: Mapped[int] = mapped_column(Integer, default=0, server_default="0", index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", index=True)
    effective_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    archived_at: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)
    superseded_by_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id"), nullable=True)
    
    # Metadata
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    doc_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # laws|discipline|competition|other
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    chunks: Mapped[list["Chunk"]] = relationship(back_populates="document", cascade="all, delete-orphan")
    superseded_by: Mapped["Document | None"] = relationship("Document", remote_side=[id], foreign_keys=[superseded_by_id])


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)

    section_label: Mapped[str] = mapped_column(String(300), index=True)  # e.g., "LUẬT 11 – Việt vị"
    section_type: Mapped[str] = mapped_column(String(50), index=True)    # LAW|ARTICLE|CLAUSE|PAGE
    page_start: Mapped[int] = mapped_column(Integer)
    page_end: Mapped[int] = mapped_column(Integer)

    text: Mapped[str] = mapped_column(Text)

    embedding: Mapped[list[float]] = mapped_column(Vector(EMBED_DIM))  # cosine search

    document: Mapped["Document"] = relationship(back_populates="chunks")
