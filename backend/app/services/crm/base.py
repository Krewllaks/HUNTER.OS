"""
HUNTER.OS - Abstract CRM Integration Interface.
All CRM adapters (HubSpot, Pipedrive, etc.) implement BaseCRM.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CRMContact:
    """Unified contact representation across CRMs."""

    external_id: Optional[str] = None
    email: str = ""
    first_name: str = ""
    last_name: str = ""
    company: str = ""
    title: str = ""
    phone: str = ""
    linkedin_url: str = ""
    score: int = 0
    status: str = "new"
    source: str = "HUNTER.OS"
    custom_fields: dict = field(default_factory=dict)


@dataclass
class CRMDeal:
    """Unified deal/opportunity representation."""

    external_id: Optional[str] = None
    contact_id: str = ""
    title: str = ""
    value: float = 0.0
    currency: str = "USD"
    stage: str = "new"
    source: str = "HUNTER.OS"


class CRMError(Exception):
    """Base exception for CRM integration errors."""

    def __init__(self, provider: str, message: str, status_code: Optional[int] = None):
        self.provider = provider
        self.message = message
        self.status_code = status_code
        super().__init__(f"[{provider}] {message}")


class CRMAuthError(CRMError):
    """Raised when CRM credentials are invalid or expired."""
    pass


class CRMRateLimitError(CRMError):
    """Raised when CRM API rate limit is hit."""

    def __init__(self, provider: str, retry_after: Optional[int] = None):
        self.retry_after = retry_after
        msg = f"Rate limit exceeded"
        if retry_after:
            msg += f" (retry after {retry_after}s)"
        super().__init__(provider, msg, status_code=429)


class BaseCRM(ABC):
    """Abstract CRM adapter. All CRM integrations implement this."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the CRM provider name (e.g. 'hubspot', 'pipedrive')."""
        ...

    @abstractmethod
    async def test_connection(self) -> bool:
        """Test if CRM credentials are valid. Returns True on success."""
        ...

    @abstractmethod
    async def push_contact(self, contact: CRMContact) -> str:
        """
        Create or update a contact in CRM.
        If contact.external_id is set, update; otherwise create.
        Returns external ID of the created/updated contact.
        """
        ...

    @abstractmethod
    async def push_deal(self, deal: CRMDeal) -> str:
        """Create a deal/opportunity. Returns external ID."""
        ...

    @abstractmethod
    async def get_contact(self, external_id: str) -> Optional[CRMContact]:
        """Fetch a contact by external ID. Returns None if not found."""
        ...

    @abstractmethod
    async def search_contact(self, email: str) -> Optional[CRMContact]:
        """Search for a contact by email. Returns None if not found."""
        ...

    async def close(self) -> None:
        """Cleanup resources (HTTP clients, etc.). Override if needed."""
        pass
