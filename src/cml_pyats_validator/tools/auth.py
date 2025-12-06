"""
Authentication Tool

Initializes and manages CML client connection.
"""

from ..client import CMLClient
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Global client instance
_cml_client: Optional[CMLClient] = None


async def initialize_cml_client(
    cml_url: str,
    username: str,
    password: str,
    verify_ssl: bool = True
) -> dict:
    """Initialize the CML client with authentication credentials
    
    Must be called before using other validation tools.
    
    Args:
        cml_url: CML server URL (e.g., https://cml-server)
        username: CML username
        password: CML password
        verify_ssl: Verify SSL certificates (set to False for self-signed certs)
    
    Returns:
        Authentication status and server information
    """
    global _cml_client
    
    try:
        _cml_client = CMLClient(cml_url, username, password, verify_ssl)
        await _cml_client.authenticate()
        
        return {
            "status": "authenticated",
            "server_url": cml_url,
            "username": username,
            "ssl_verify": verify_ssl
        }
    except Exception as e:
        logger.error(f"CML client initialization failed: {e}")
        return {
            "status": "failed",
            "error": str(e)
        }


def get_cml_client() -> CMLClient:
    """Get the global CML client instance
    
    Returns:
        CMLClient instance
    
    Raises:
        RuntimeError: If client not initialized
    """
    if _cml_client is None:
        raise RuntimeError(
            "CML client not initialized. Call initialize_cml_client first."
        )
    return _cml_client
