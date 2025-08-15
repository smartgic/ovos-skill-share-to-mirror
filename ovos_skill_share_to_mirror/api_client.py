"""API client for communicating with MagicMirror MMM-ShareToMirror module."""

from __future__ import annotations

import socket
from typing import Any, Dict, Optional

import requests
from ovos_utils.log import LOG


class MirrorAPIClient:
    """HTTP client for MagicMirror MMM-ShareToMirror API.
    
    This class handles all HTTP communication with the MagicMirror device,
    including video playback control, status queries, and configuration.
    
    Attributes:
        base_url: Base URL of the MagicMirror API endpoint
        session: Reusable HTTP session for efficient connections
        timeout: Request timeout in seconds
        verify_ssl: Whether to verify SSL certificates
    """

    def __init__(self, base_url: str, api_token: Optional[str] = None, 
                 verify_ssl: bool = True, timeout: int = 6):
        """Initialize the API client.
        
        Args:
            base_url: Base URL of the MagicMirror API
            api_token: Optional API token for authentication
            verify_ssl: Whether to verify SSL certificates
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        
        # Create reusable HTTP session
        self.session = requests.Session()
        self.session.headers.update(self._get_headers(api_token))

    def _get_headers(self, api_token: Optional[str]) -> Dict[str, str]:
        """Generate HTTP headers for API requests.
        
        Args:
            api_token: Optional API token for authentication
            
        Returns:
            Dictionary of HTTP headers
        """
        headers = {"Content-Type": "application/json"}
        if api_token:
            headers["Authorization"] = f"Bearer {api_token}"
        return headers

    def _make_request(self, method: str, path: str, 
                     json_data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Make HTTP request with comprehensive error handling.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            path: API endpoint path
            json_data: Optional JSON payload
            
        Returns:
            Response JSON data if successful, None if failed
        """
        url = self.base_url + path
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                json=json_data,
                timeout=self.timeout,
                verify=self.verify_ssl
            )
            
            if response.status_code >= 400:
                LOG.error(f"[MirrorAPI] {method} {path} failed: "
                         f"{response.status_code} {response.text}")
                return None
                
            return response.json() if response.content else {}
            
        except (requests.RequestException, socket.error) as e:
            LOG.exception(f"[MirrorAPI] {method} {path} error: {e}")
            return None

    def play_video(self, url: str) -> bool:
        """Start playing a video URL on the mirror.
        
        Args:
            url: YouTube or other video URL to play
            
        Returns:
            True if playback started successfully
        """
        LOG.info(f"[MirrorAPI] Playing URL: {url}")
        result = self._make_request("POST", "/api/play", {"url": url})
        return result is not None

    def stop_video(self) -> bool:
        """Stop video playback completely.
        
        Returns:
            True if stop command was successful
        """
        result = self._make_request("POST", "/api/stop")
        return result is not None

    def control_playback(self, action: str, seconds: Optional[int] = None) -> bool:
        """Send playback control command.
        
        Args:
            action: Control action (pause, resume, rewind, forward, restart)
            seconds: Optional seconds parameter for seek operations
            
        Returns:
            True if control command was successful
        """
        payload: Dict[str, Any] = {"action": action}
        if seconds is not None:
            payload["seconds"] = seconds
            
        LOG.debug(f"[MirrorAPI] Control: {payload}")
        result = self._make_request("POST", "/api/control", payload)
        return result is not None

    def get_status(self) -> Optional[Dict[str, Any]]:
        """Get current playback status.
        
        Returns:
            Status data if successful, None if failed
        """
        return self._make_request("GET", "/api/status")

    def set_options(self, caption_enabled: bool = False, caption_lang: str = "en",
                   quality_target: str = "auto", quality_lock: bool = False) -> bool:
        """Set video options (captions, quality).
        
        Args:
            caption_enabled: Whether to enable captions
            caption_lang: Caption language code
            quality_target: Target video quality
            quality_lock: Whether to lock quality setting
            
        Returns:
            True if options were set successfully
        """
        payload = {
            "caption": {"enabled": caption_enabled, "lang": caption_lang},
            "quality": {"target": quality_target, "lock": quality_lock},
        }
        LOG.debug(f"[MirrorAPI] Setting options: {payload}")
        result = self._make_request("POST", "/api/options", payload)
        return result is not None

    def control_overlay(self, action: str) -> bool:
        """Control video overlay display mode.
        
        Args:
            action: Overlay action ('fullscreen', 'windowed', 'toggle')
            
        Returns:
            True if overlay control was successful
        """
        valid_actions = ["fullscreen", "windowed", "toggle"]
        if action not in valid_actions:
            LOG.error(f"[MirrorAPI] Invalid overlay action: {action}")
            return False
            
        payload = {"action": action}
        LOG.debug(f"[MirrorAPI] Overlay control: {payload}")
        result = self._make_request("POST", "/api/overlay", payload)
        return result is not None

    def close(self) -> None:
        """Close the HTTP session and clean up resources."""
        if hasattr(self, 'session'):
            self.session.close()
