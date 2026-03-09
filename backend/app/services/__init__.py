"""
OperatorOS AI/RAG services — the intelligence layer.

Re-exports every service for convenient imports::

    from app.services import RAGService, OpenRouterClient, EmbeddingService
"""

from app.services.openrouter import OpenRouterClient
from app.services.embedding import EmbeddingService
from app.services.rag import RAGService
from app.services.document_processor import DocumentProcessor
from app.services.notice_processor import NoticeProcessor
from app.services.communication_drafter import CommunicationDrafter
from app.services.compliance_tracker import ComplianceTracker

__all__ = [
    "OpenRouterClient",
    "EmbeddingService",
    "RAGService",
    "DocumentProcessor",
    "NoticeProcessor",
    "CommunicationDrafter",
    "ComplianceTracker",
]
