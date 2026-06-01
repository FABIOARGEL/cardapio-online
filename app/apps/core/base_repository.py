"""
Base Repository — single source of database access patterns.

All repositories must inherit from BaseRepository to ensure:
- Consistent pagination
- Centralized query methods
- Logging of slow queries
- Type-safe return values
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

import mongoengine as me

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=me.Document)


@dataclass(frozen=True)
class PaginatedResult:
    """Immutable result container for paginated queries."""
    results: list[dict]
    count: int
    page: int
    total_pages: int
    page_size: int = 12

    def to_dict(self) -> dict:
        return {
            'results': self.results,
            'count': self.count,
            'page': self.page,
            'total_pages': self.total_pages,
        }


class BaseRepository(Generic[T]):
    """
    Abstract base repository with common query patterns.

    Subclasses must set `document_class` to the MongoEngine Document.

    Usage:
        class UserRepository(BaseRepository[User]):
            document_class = User

            def find_by_email(self, email: str) -> User | None:
                return self.find_one(email=email)
    """

    document_class: type[T]

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Core query methods
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    def find_by_id(self, doc_id: str) -> T | None:
        """Find a document by its primary key."""
        try:
            return self.document_class.objects(id=doc_id).first()
        except Exception:
            logger.warning("Invalid ID format: %s for %s", doc_id, self.document_class.__name__)
            return None

    def find_one(self, **filters: Any) -> T | None:
        """Find a single document matching filters."""
        return self.document_class.objects(**filters).first()

    def find_many(self, ordering: str = '-criado_em', **filters: Any) -> list[T]:
        """Find all documents matching filters with ordering."""
        return list(self.document_class.objects(**filters).order_by(ordering))

    def count(self, **filters: Any) -> int:
        """Count documents matching filters."""
        return self.document_class.objects(**filters).count()

    def exists(self, **filters: Any) -> bool:
        """Check if any document matches filters."""
        return self.document_class.objects(**filters).first() is not None

    def save(self, document: T) -> T:
        """Save a document."""
        document.save()
        return document

    def delete(self, document: T) -> None:
        """Delete a document."""
        document.delete()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Pagination
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    def paginate(
        self,
        page: int = 1,
        page_size: int = 12,
        ordering: str = '-criado_em',
        serializer_fn: callable | None = None,
        **filters: Any,
    ) -> PaginatedResult:
        """
        Paginate a queryset with consistent logic.

        Args:
            page: Page number (1-indexed)
            page_size: Items per page
            ordering: MongoDB ordering field
            serializer_fn: Optional function to serialize each document
            **filters: MongoEngine query filters

        Returns:
            PaginatedResult with serialized results
        """
        start = time.monotonic()

        queryset = self.document_class.objects(**filters).order_by(ordering)
        total = queryset.count()
        total_pages = max(1, (total + page_size - 1) // page_size)

        # Clamp page to valid range
        page = max(1, min(page, total_pages))
        offset = (page - 1) * page_size

        documents = queryset.skip(offset).limit(page_size)

        if serializer_fn:
            results = [serializer_fn(doc) for doc in documents]
        else:
            results = [doc.to_dict() if hasattr(doc, 'to_dict') else doc for doc in documents]

        elapsed = time.monotonic() - start
        if elapsed > 0.5:
            logger.warning(
                "Slow query on %s: %.2fs (filters=%s, page=%d)",
                self.document_class.__name__, elapsed, filters, page,
            )

        return PaginatedResult(
            results=results,
            count=total,
            page=page,
            total_pages=total_pages,
            page_size=page_size,
        )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Aggregation helper
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    def aggregate(self, pipeline: list[dict]) -> list[dict]:
        """Run a MongoDB aggregation pipeline."""
        start = time.monotonic()
        results = list(self.document_class.objects.aggregate(pipeline))
        elapsed = time.monotonic() - start

        if elapsed > 1.0:
            logger.warning(
                "Slow aggregation on %s: %.2fs (pipeline stages=%d)",
                self.document_class.__name__, elapsed, len(pipeline),
            )

        return results
