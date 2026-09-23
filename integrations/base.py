"""Base connector interface for external update ingestion (Gmail, Slack, Webhooks)."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseIntegrationConnector(ABC):
    """Abstract base class for data ingestion connectors."""

    @abstractmethod
    def fetch_messages(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch raw unread or recent messages from the provider."""
        pass

    @abstractmethod
    def normalize_message(self, raw_message: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize message into a standard structure (sender, subject, body, timestamp)."""
        pass

    @abstractmethod
    def identify_project(self, normalized_message: Dict[str, Any], projects: List[Any]) -> Dict[str, Any]:
        """
        Identify project association using deterministic signals first, then AI matching.
        Returns dict with project_id, confidence, match_uncertain flag, and candidates.
        """
        pass

    @abstractmethod
    def create_update(self, project_id: str, normalized_message: Dict[str, Any]) -> Dict[str, Any]:
        """Create a staged update from the normalized message for human review."""
        pass
