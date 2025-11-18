"""CML API Client for lab and device management."""

import httpx
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)


class CMLClient:
    """Client for interacting with Cisco Modeling Labs API."""

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        verify_ssl: bool = True
    ):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self.token: Optional[str] = None
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                verify=self.verify_ssl,
                timeout=30.0
            )
        return self._client

    async def authenticate(self) -> str:
        """Authenticate with CML and get API token."""
        client = await self._get_client()
        
        try:
            response = await client.post(
                f"{self.base_url}/api/v0/authenticate",
                auth=(self.username, self.password)
            )
            response.raise_for_status()
            self.token = response.text.strip('"')
            logger.info("Successfully authenticated with CML")
            return self.token
        except httpx.HTTPStatusError as e:
            logger.error(f"Authentication failed: {e.response.status_code}")
            raise Exception(f"CML authentication failed: {e.response.text}")

    async def _ensure_authenticated(self):
        """Ensure we have a valid token."""
        if not self.token:
            await self.authenticate()

    async def get(self, endpoint: str, params: Optional[dict] = None) -> Any:
        """Make GET request to CML API."""
        await self._ensure_authenticated()
        client = await self._get_client()
        
        headers = {"Authorization": f"Bearer {self.token}"}
        response = await client.get(
            f"{self.base_url}/api/v0{endpoint}",
            headers=headers,
            params=params
        )
        response.raise_for_status()
        return response.json()

    async def post(self, endpoint: str, data: Any = None) -> Any:
        """Make POST request to CML API."""
        await self._ensure_authenticated()
        client = await self._get_client()
        
        headers = {"Authorization": f"Bearer {self.token}"}
        response = await client.post(
            f"{self.base_url}/api/v0{endpoint}",
            headers=headers,
            json=data
        )
        response.raise_for_status()
        return response.json()

    async def get_lab(self, lab_id: str) -> dict:
        """Get lab details by ID."""
        return await self.get(f"/labs/{lab_id}")

    async def get_lab_by_title(self, title: str) -> Optional[dict]:
        """Get lab by title."""
        labs = await self.get("/labs", params={"show_all": True})
        for lab_id in labs:
            lab = await self.get_lab(lab_id)
            if lab.get("lab_title") == title:
                return lab
        return None

    async def get_nodes(self, lab_id: str) -> list[dict]:
        """Get all nodes in a lab."""
        return await self.get(
            f"/labs/{lab_id}/nodes",
            params={"data": True, "operational": True}
        )

    async def get_node_by_label(self, lab_id: str, label: str) -> Optional[dict]:
        """Get node by label within a lab."""
        nodes = await self.get_nodes(lab_id)
        for node in nodes:
            if node.get("data", {}).get("label") == label:
                return node
        return None

    async def get_node_config(self, lab_id: str, node_id: str) -> str:
        """Get node configuration."""
        node = await self.get(f"/labs/{lab_id}/nodes/{node_id}")
        return node.get("data", {}).get("configuration", "")

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
