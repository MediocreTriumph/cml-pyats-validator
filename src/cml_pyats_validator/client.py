"""
CML API Client

Handles communication with Cisco Modeling Labs (CML) API.
"""

import httpx
import json
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class CMLClient:
    """Client for interacting with CML API"""
    
    def __init__(self, url: str, username: str, password: str, verify_ssl: bool = True):
        """Initialize CML client
        
        Args:
            url: CML server URL (e.g., https://cml-server)
            username: CML username
            password: CML password
            verify_ssl: Verify SSL certificates
        """
        self.url = url.rstrip('/')
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self.token: Optional[str] = None
        self.client = httpx.AsyncClient(verify=verify_ssl, timeout=30.0)
    
    async def authenticate(self) -> None:
        """Authenticate with CML and get auth token"""
        try:
            response = await self.client.post(
                f"{self.url}/api/v0/authenticate",
                json={"username": self.username, "password": self.password}
            )
            response.raise_for_status()
            self.token = response.text.strip('"')
            logger.info("Successfully authenticated with CML")
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise
    
    async def _request(self, method: str, endpoint: str, **kwargs) -> Any:
        """Make authenticated request to CML API"""
        if not self.token:
            await self.authenticate()
        
        headers = kwargs.pop('headers', {})
        headers['Authorization'] = f'Bearer {self.token}'
        
        response = await self.client.request(
            method,
            f"{self.url}{endpoint}",
            headers=headers,
            **kwargs
        )
        
        # Re-auth on 401
        if response.status_code == 401:
            await self.authenticate()
            headers['Authorization'] = f'Bearer {self.token}'
            response = await self.client.request(
                method,
                f"{self.url}{endpoint}",
                headers=headers,
                **kwargs
            )
        
        response.raise_for_status()
        
        # Handle JSON response properly
        if not response.text:
            return None
        
        try:
            result = response.json()
            
            # Handle double-encoded JSON (if response.json() returns a string)
            if isinstance(result, str):
                logger.debug(f"Response is string, attempting second JSON parse")
                try:
                    result = json.loads(result)
                except Exception:
                    # If it fails, return the string as-is
                    pass
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response text: {response.text[:500]}")
            raise
    
    async def get_lab(self, lab_id: str) -> Dict[str, Any]:
        """Get lab details"""
        return await self._request('GET', f'/api/v0/labs/{lab_id}')
    
    async def get_node(self, lab_id: str, node_id: str) -> Dict[str, Any]:
        """Get node details"""
        return await self._request('GET', f'/api/v0/labs/{lab_id}/nodes/{node_id}')
    
    async def get_nodes(self, lab_id: str) -> List[Dict[str, Any]]:
        """Get all nodes in a lab"""
        result = await self._request('GET', f'/api/v0/labs/{lab_id}/nodes')
        
        # Ensure we return a list
        if not isinstance(result, list):
            logger.error(f"Expected list from get_nodes, got {type(result)}")
            return []
        
        return result
    
    async def find_node_by_label(self, lab_id: str, label: str) -> Optional[Dict[str, Any]]:
        """Find a node by its label/name"""
        nodes = await self.get_nodes(lab_id)
        
        if not isinstance(nodes, list):
            logger.error(f"get_nodes returned non-list: {type(nodes)}")
            return None
        
        for node in nodes:
            if not isinstance(node, dict):
                logger.warning(f"Node is not a dict: {type(node)}")
                continue
                
            if node.get('label') == label:
                return node
        
        return None
    
    async def get_node_console_logs(self, lab_id: str, node_id: str, lines: int = 100) -> str:
        """Get console logs from a node"""
        return await self._request(
            'GET', 
            f'/api/v0/labs/{lab_id}/nodes/{node_id}/console_logs',
            params={'lines': lines}
        )
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()