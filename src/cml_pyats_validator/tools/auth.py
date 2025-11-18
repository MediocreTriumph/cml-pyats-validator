"""Authentication tool for CML server."""

from typing import Optional
import os
from ..client import CMLClient

# Global client instance
_cml_client: Optional[CMLClient] = None


async def initialize_client(
    cml_url: str,
    username: str,
    password: str,
    verify_ssl: bool = True
) -> dict:
    """
    Initialize and authenticate with CML server.
    
    Stores credentials for subsequent tool calls. Must be called before
    using other validation tools.
    
    Args:
        cml_url: Base URL of CML server (e.g., https://cml-server)
        username: CML username
        password: CML password
        verify_ssl: Whether to verify SSL certificates (False for self-signed certs)
        
    Returns:
        Dictionary with authentication status and server info
    """
    global _cml_client
    
    try:
        # Create new client
        _cml_client = CMLClient(
            base_url=cml_url,
            username=username,
            password=password,
            verify_ssl=verify_ssl
        )
        
        # Authenticate
        token = await _cml_client.authenticate()
        
        # Store credentials as environment variables for tmux tools to use
        os.environ["CML_URL"] = cml_url
        os.environ["CML_USERNAME"] = username
        os.environ["CML_PASSWORD"] = password
        os.environ["CML_VERIFY_SSL"] = str(verify_ssl)
        
        return {
            "status": "success",
            "message": "Successfully authenticated with CML server",
            "server_url": cml_url,
            "authenticated": True
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Authentication failed: {str(e)}",
            "authenticated": False
        }


def get_client() -> Optional[CMLClient]:
    """Get the global CML client instance."""
    return _cml_client


def require_client() -> CMLClient:
    """Get CML client or raise error if not initialized."""
    if _cml_client is None:
        raise RuntimeError(
            "CML client not initialized. Call initialize_client first."
        )
    return _cml_client
