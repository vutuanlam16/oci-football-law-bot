"""
Versioning and conflict detection service for legal documents.

This module handles:
- Version tracking (major.minor versioning)
- Conflict detection when multiple versions exist
- Archiving superseded versions
- Querying active vs. historical versions
"""

from datetime import datetime, date
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.models import Document, Chunk


class VersionConflict(Exception):
    """Raised when version conflict is detected."""
    def __init__(self, message: str, conflicts: list[dict]):
        super().__init__(message)
        self.conflicts = conflicts


class VersioningService:
    """Service for managing document versions and detecting conflicts."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_active_version(
        self, 
        doc_type: Optional[str] = None,
        title_pattern: Optional[str] = None
    ) -> list[Document]:
        """Get all active (non-archived) documents."""
        query = self.db.query(Document).filter(Document.is_active == True)
        
        if doc_type:
            query = query.filter(Document.doc_type == doc_type)
        
        if title_pattern:
            query = query.filter(Document.title.ilike(f"%{title_pattern}%"))
        
        return query.all()
    
    def get_version_history(self, doc_id: str) -> list[Document]:
        """Get all versions of a document by doc_id pattern."""
        # Extract base doc_id (without version suffix like _v2024)
        base_id = doc_id.split("_v")[0] if "_v" in doc_id else doc_id
        
        return (
            self.db.query(Document)
            .filter(Document.doc_id.like(f"{base_id}%"))
            .order_by(
                Document.version_major.desc(),
                Document.version_minor.desc()
            )
            .all()
        )
    
    def detect_conflicts(
        self, 
        doc_type: Optional[str] = None,
        effective_on: Optional[date] = None
    ) -> list[dict]:
        """
        Detect version conflicts: multiple active versions of same document.
        
        Returns list of conflicts with format:
        [
            {
                "base_doc": str,  # base document identifier
                "versions": [
                    {"doc_id": str, "version": "1.0", "effective_date": date, ...},
                    ...
                ]
            }
        ]
        """
        query = self.db.query(Document).filter(Document.is_active == True)
        
        if doc_type:
            query = query.filter(Document.doc_type == doc_type)
        
        if effective_on:
            query = query.filter(
                or_(
                    Document.effective_date.is_(None),
                    Document.effective_date <= effective_on
                )
            )
        
        docs = query.all()
        
        # Group by base doc_id (remove version suffix)
        groups = {}
        for doc in docs:
            base_id = doc.doc_id.split("_v")[0] if "_v" in doc.doc_id else doc.doc_id
            
            # Also try to group by title similarity (for same law in different years)
            title_key = doc.title.split("(")[0].strip() if "(" in doc.title else doc.title.strip()
            
            key = (base_id, title_key, doc.doc_type)
            
            if key not in groups:
                groups[key] = []
            
            groups[key].append({
                "doc_id": doc.doc_id,
                "id": doc.id,
                "title": doc.title,
                "version": f"{doc.version_major}.{doc.version_minor}",
                "version_major": doc.version_major,
                "version_minor": doc.version_minor,
                "effective_date": doc.effective_date,
                "created_at": doc.created_at,
            })
        
        # Find conflicts (multiple active versions)
        conflicts = []
        for (base_id, title_key, doc_type), versions in groups.items():
            if len(versions) > 1:
                conflicts.append({
                    "base_doc": base_id,
                    "title_pattern": title_key,
                    "doc_type": doc_type,
                    "conflict_count": len(versions),
                    "versions": sorted(
                        versions, 
                        key=lambda v: (v["version_major"], v["version_minor"]),
                        reverse=True
                    )
                })
        
        return conflicts
    
    def archive_version(
        self,
        doc_id: str,
        superseded_by_doc_id: Optional[str] = None
    ) -> Document:
        """
        Archive a specific version by setting is_active=False.
        
        Args:
            doc_id: Document ID to archive
            superseded_by_doc_id: Optional ID of document that supersedes this one
        
        Returns:
            Archived document
        """
        doc = self.db.query(Document).filter(Document.doc_id == doc_id).first()
        if not doc:
            raise ValueError(f"Document {doc_id} not found")
        
        doc.is_active = False
        doc.archived_at = datetime.utcnow()
        
        if superseded_by_doc_id:
            superseding_doc = (
                self.db.query(Document)
                .filter(Document.doc_id == superseded_by_doc_id)
                .first()
            )
            if superseding_doc:
                doc.superseded_by_id = superseding_doc.id
        
        self.db.commit()
        self.db.refresh(doc)
        
        return doc
    
    def resolve_conflicts_auto(
        self,
        doc_type: Optional[str] = None,
        strategy: str = "keep_latest"
    ) -> list[dict]:
        """
        Automatically resolve conflicts using a strategy.
        
        Strategies:
        - keep_latest: Archive all but the version with highest major.minor
        - keep_effective: Keep only the version with latest effective_date
        
        Returns list of archived documents.
        """
        conflicts = self.detect_conflicts(doc_type=doc_type)
        archived = []
        
        for conflict in conflicts:
            versions = conflict["versions"]
            
            if strategy == "keep_latest":
                # Keep first (highest version), archive rest
                to_keep = versions[0]
                to_archive = versions[1:]
            
            elif strategy == "keep_effective":
                # Keep version with latest effective_date
                versions_sorted = sorted(
                    versions,
                    key=lambda v: v["effective_date"] or date(1900, 1, 1),
                    reverse=True
                )
                to_keep = versions_sorted[0]
                to_archive = [v for v in versions if v["doc_id"] != to_keep["doc_id"]]
            
            else:
                raise ValueError(f"Unknown strategy: {strategy}")
            
            # Archive old versions
            for ver in to_archive:
                doc = self.archive_version(
                    ver["doc_id"],
                    superseded_by_doc_id=to_keep["doc_id"]
                )
                archived.append({
                    "doc_id": doc.doc_id,
                    "title": doc.title,
                    "version": f"{doc.version_major}.{doc.version_minor}",
                    "superseded_by": to_keep["doc_id"]
                })
        
        return archived
    
    def create_new_version(
        self,
        base_doc_id: str,
        new_major: int,
        new_minor: int = 0,
        archive_old: bool = True,
        effective_date: Optional[date] = None
    ) -> tuple[Document, Optional[Document]]:
        """
        Create a new version of an existing document.
        
        This creates a new Document record with incremented version,
        and optionally archives the old version.
        
        Args:
            base_doc_id: Base document ID (without version suffix)
            new_major: New major version number
            new_minor: New minor version number
            archive_old: Whether to archive previous active version
            effective_date: When this version becomes effective
        
        Returns:
            Tuple of (new_document, old_document_if_archived)
        """
        # Find current active version
        current = (
            self.db.query(Document)
            .filter(
                and_(
                    Document.doc_id.like(f"{base_doc_id}%"),
                    Document.is_active == True
                )
            )
            .first()
        )
        
        if not current:
            raise ValueError(f"No active document found for {base_doc_id}")
        
        # Create new document with same metadata but new version
        new_doc_id = f"{base_doc_id}_v{new_major}.{new_minor}"
        
        new_doc = Document(
            doc_id=new_doc_id,
            title=f"{current.title} (v{new_major}.{new_minor})",
            version_major=new_major,
            version_minor=new_minor,
            is_active=True,
            effective_date=effective_date or datetime.utcnow().date(),
            doc_type=current.doc_type,
            source_url=current.source_url,
        )
        
        self.db.add(new_doc)
        self.db.flush()  # Get new_doc.id
        
        # Archive old version if requested
        archived_doc = None
        if archive_old:
            archived_doc = self.archive_version(
                current.doc_id,
                superseded_by_doc_id=new_doc.doc_id
            )
        
        self.db.commit()
        self.db.refresh(new_doc)
        
        return new_doc, archived_doc
    
    def get_statistics(self) -> dict:
        """Get version control statistics."""
        total_docs = self.db.query(func.count(Document.id)).scalar()
        active_docs = self.db.query(func.count(Document.id)).filter(Document.is_active == True).scalar()
        archived_docs = self.db.query(func.count(Document.id)).filter(Document.is_active == False).scalar()
        conflicts = self.detect_conflicts()
        
        return {
            "total_documents": total_docs,
            "active_documents": active_docs,
            "archived_documents": archived_docs,
            "conflicts_detected": len(conflicts),
            "conflict_details": conflicts
        }
