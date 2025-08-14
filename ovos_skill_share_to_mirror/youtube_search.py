"""YouTube search functionality for finding videos with variety and fuzzy matching."""

from __future__ import annotations

import hashlib
import random
import time
from typing import List, Optional, Set

from ovos_utils.log import LOG

# Optional imports
try:
    from googleapiclient.discovery import build as gapi_build  # type: ignore
except ImportError:  # pragma: no cover
    gapi_build = None

try:
    import yt_dlp  # type: ignore
except ImportError:  # pragma: no cover
    yt_dlp = None

try:
    from fuzzywuzzy import fuzz  # type: ignore
except ImportError:  # pragma: no cover
    fuzz = None


class YouTubeSearcher:
    """Handles YouTube video search with variety and fuzzy matching.
    
    This class provides intelligent YouTube video search that avoids repeating
    the same videos and uses fuzzy matching to improve search accuracy and speed.
    
    Features:
    - Multiple result fetching to avoid repetition
    - Fuzzy matching for better query understanding
    - Search history tracking to prevent duplicates
    - Query enhancement for better results
    
    Attributes:
        backend: Search backend ('yt_dlp' or 'google_api')
        api_key: YouTube Data API key (required for google_api backend)
        search_history: Set of previously returned video URLs
        max_results: Maximum number of results to fetch per search
    """

    def __init__(self, backend: str = "yt_dlp", api_key: Optional[str] = None, 
                 max_results: int = 5):
        """Initialize the YouTube searcher.
        
        Args:
            backend: Search backend to use ('yt_dlp' or 'google_api')
            api_key: YouTube Data API key (required for google_api backend)
            max_results: Maximum number of results to fetch per search
        """
        self.backend = backend
        self.api_key = api_key
        self.max_results = max_results
        self.search_history: Set[str] = set()
        
        # Validate backend configuration
        self._validate_backend()

    def _validate_backend(self) -> None:
        """Validate and adjust search backend configuration."""
        if self.backend == "google_api":
            if not self.api_key or not gapi_build:
                LOG.warning("[YouTubeSearch] Google API selected but key/client missing; "
                           "falling back to yt_dlp")
                self.backend = "yt_dlp"
        
        if self.backend == "yt_dlp" and yt_dlp is None:
            LOG.warning("[YouTubeSearch] yt-dlp unavailable; search disabled")

    def search(self, query: str, video_type: str = "any") -> Optional[str]:
        """Search for a YouTube video with variety and fuzzy matching.
        
        This method enhances the search query, fetches multiple results,
        and returns a video that hasn't been played recently.
        
        Args:
            query: Search query string
            video_type: Type of video to search for ('any', 'shorts', 'long')
            
        Returns:
            YouTube video URL if found, None otherwise
        """
        # Enhance query for better results and video type
        enhanced_query = self._enhance_query(query, video_type)
        
        if self.backend == "google_api" and self.api_key and gapi_build:
            return self._search_google_api(enhanced_query, video_type)
        elif self.backend == "yt_dlp" and yt_dlp:
            return self._search_yt_dlp(enhanced_query, video_type)
        else:
            LOG.warning("[YouTubeSearch] No search backend available")
            return None

    def _enhance_query(self, query: str, video_type: str = "any") -> str:
        """Enhance search query for better and more varied results.
        
        Args:
            query: Original search query
            video_type: Type of video to search for ('any', 'shorts', 'long')
            
        Returns:
            Enhanced query string
        """
        # Add video type specific modifiers
        if video_type == "shorts":
            query = f"{query} shorts"
        elif video_type == "long":
            # Add modifiers that typically yield longer content
            long_modifiers = ["full", "complete", "documentary", "tutorial", "guide", "explained"]
            modifier = random.choice(long_modifiers)
            query = f"{query} {modifier}"
        
        # Add variety modifiers to get different results
        variety_modifiers = [
            "latest", "new", "best", "top", "popular", "recent",
            "tutorial", "guide", "review", "explained", "2024", "2023"
        ]
        
        # Use fuzzy matching to find similar queries we've used before
        if fuzz and self.search_history:
            for previous_url in list(self.search_history)[-10:]:  # Check last 10 searches
                # Extract query hash from URL for comparison
                query_hash = self._get_query_hash(query)
                if query_hash in previous_url:
                    # Add a variety modifier to get different results
                    modifier = random.choice(variety_modifiers)
                    enhanced = f"{query} {modifier}"
                    LOG.debug(f"[YouTubeSearch] Enhanced query to avoid repetition: {enhanced}")
                    return enhanced
        
        # Occasionally add variety even for new queries (but not if we already added video type)
        if video_type == "any" and random.random() < 0.3:  # 30% chance to add variety
            modifier = random.choice(variety_modifiers)
            enhanced = f"{query} {modifier}"
            LOG.debug(f"[YouTubeSearch] Added variety to query: {enhanced}")
            return enhanced
            
        return query

    def _get_query_hash(self, query: str) -> str:
        """Generate a short hash for a query to track similar searches.
        
        Args:
            query: Search query string
            
        Returns:
            Short hash string for the query
        """
        return hashlib.md5(query.lower().strip().encode()).hexdigest()[:8]

    def _search_google_api(self, query: str, video_type: str = "any") -> Optional[str]:
        """Search YouTube using Google API with multiple results and duration filtering.
        
        Args:
            query: Search query string
            video_type: Type of video to search for ('any', 'shorts', 'long')
            
        Returns:
            YouTube video URL if found, None otherwise
        """
        try:
            youtube = gapi_build("youtube", "v3", developerKey=self.api_key)
            
            # Set duration filter based on video type
            duration_filter = None
            if video_type == "shorts":
                duration_filter = "short"  # Under 4 minutes
            elif video_type == "long":
                duration_filter = "long"   # Over 20 minutes
            
            request_params = {
                "q": query,
                "part": "id,snippet",
                "type": "video",
                "maxResults": self.max_results,
                "order": "relevance"
            }
            
            if duration_filter:
                request_params["videoDuration"] = duration_filter
            
            request = youtube.search().list(**request_params)
            response = request.execute()
            
            items = response.get("items", [])
            if not items:
                LOG.info(f"[YouTubeSearch] No {video_type} results found for: {query}")
                return None
            
            # Find a video we haven't played recently
            for item in items:
                video_id = item["id"]["videoId"]
                url = f"https://www.youtube.com/watch?v={video_id}"
                
                if url not in self.search_history:
                    # Add to history and return
                    self.search_history.add(url)
                    self._cleanup_history()
                    
                    title = item.get("snippet", {}).get("title", "Unknown")
                    LOG.info(f"[YouTubeSearch] Found new {video_type} video: {title} - {url}")
                    return url
            
            # If all results were in history, return the first one anyway
            video_id = items[0]["id"]["videoId"]
            url = f"https://www.youtube.com/watch?v={video_id}"
            LOG.info(f"[YouTubeSearch] All {video_type} results seen before, returning first: {url}")
            return url
            
        except Exception as e:
            LOG.exception(f"[YouTubeSearch] Google API search failed: {e}")
            return None

    def _search_yt_dlp(self, query: str, video_type: str = "any") -> Optional[str]:
        """Search YouTube using yt-dlp with multiple results and duration awareness.
        
        Args:
            query: Search query string
            video_type: Type of video to search for ('any', 'shorts', 'long')
            
        Returns:
            YouTube video URL if found, None otherwise
        """
        ydl_opts = {
            "quiet": True, 
            "skip_download": True, 
            "extract_flat": "in_playlist"
        }
        
        try:
            # Search for multiple results to provide variety
            search_query = f"ytsearch{self.max_results}:{query}"
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore
                info = ydl.extract_info(search_query, download=False)
                
            if not info or "entries" not in info or not info["entries"]:
                LOG.info(f"[YouTubeSearch] No results found for: {query}")
                return None
            
            entries = info["entries"]
            
            # Filter by video type if specified
            if video_type != "any":
                entries = self._filter_by_duration(entries, video_type)
                if not entries:
                    LOG.info(f"[YouTubeSearch] No {video_type} videos found after filtering")
                    return None
            
            # Find a video we haven't played recently
            for entry in entries:
                url = self._extract_url_from_entry(entry)
                if url and url not in self.search_history:
                    # Add to history and return
                    self.search_history.add(url)
                    self._cleanup_history()
                    
                    title = entry.get("title", "Unknown")
                    duration = entry.get("duration", "Unknown")
                    LOG.info(f"[YouTubeSearch] Found new {video_type} video: {title} ({duration}) - {url}")
                    return url
            
            # If all results were in history, return the first valid one
            for entry in entries:
                url = self._extract_url_from_entry(entry)
                if url:
                    title = entry.get("title", "Unknown")
                    LOG.info(f"[YouTubeSearch] All {video_type} results seen before, returning first: {title} - {url}")
                    return url
            
            return None
            
        except Exception as e:
            LOG.exception(f"[YouTubeSearch] yt-dlp search failed: {e}")
            return None

    def _filter_by_duration(self, entries: List[dict], video_type: str) -> List[dict]:
        """Filter video entries by duration based on video type.
        
        Args:
            entries: List of video entries from search results
            video_type: Type of video to filter for ('shorts' or 'long')
            
        Returns:
            Filtered list of entries matching the duration criteria
        """
        filtered = []
        
        for entry in entries:
            duration = entry.get("duration")
            if not duration:
                # If no duration info, include it for 'any' type searches
                if video_type == "any":
                    filtered.append(entry)
                continue
            
            # Parse duration (can be in seconds or HH:MM:SS format)
            duration_seconds = self._parse_duration(duration)
            
            if video_type == "shorts" and duration_seconds and duration_seconds <= 60:
                # YouTube Shorts are typically 60 seconds or less
                filtered.append(entry)
            elif video_type == "long" and duration_seconds and duration_seconds >= 600:
                # Long videos are 10+ minutes
                filtered.append(entry)
            elif video_type == "any":
                filtered.append(entry)
        
        return filtered

    def _parse_duration(self, duration) -> Optional[int]:
        """Parse video duration into seconds.
        
        Args:
            duration: Duration in various formats (seconds, MM:SS, HH:MM:SS)
            
        Returns:
            Duration in seconds, or None if unparseable
        """
        if isinstance(duration, (int, float)):
            return int(duration)
        
        if isinstance(duration, str):
            try:
                # Try parsing as seconds first
                return int(float(duration))
            except ValueError:
                pass
            
            # Try parsing as time format (MM:SS or HH:MM:SS)
            try:
                parts = duration.split(":")
                if len(parts) == 2:  # MM:SS
                    return int(parts[0]) * 60 + int(parts[1])
                elif len(parts) == 3:  # HH:MM:SS
                    return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            except (ValueError, IndexError):
                pass
        
        return None

    def _extract_url_from_entry(self, entry: dict) -> Optional[str]:
        """Extract URL from a yt-dlp search result entry.
        
        Args:
            entry: yt-dlp search result entry
            
        Returns:
            YouTube video URL if extractable, None otherwise
        """
        # Try to get direct URL first
        if "url" in entry and entry["url"].startswith("http"):
            return entry["url"]
        
        # Fallback to constructing URL from video ID
        video_id = entry.get("id")
        if video_id:
            return f"https://www.youtube.com/watch?v={video_id}"
            
        return None

    def _cleanup_history(self) -> None:
        """Clean up search history to prevent unlimited growth.
        
        Keeps only the most recent 50 searches to balance variety
        with memory usage.
        """
        if len(self.search_history) > 50:
            # Convert to list, keep last 30, convert back to set
            history_list = list(self.search_history)
            self.search_history = set(history_list[-30:])
            LOG.debug("[YouTubeSearch] Cleaned up search history")

    def clear_history(self) -> None:
        """Clear the search history to allow previously played videos again.
        
        This can be useful for testing or if users want to replay content.
        """
        self.search_history.clear()
        LOG.info("[YouTubeSearch] Search history cleared")

    def get_history_size(self) -> int:
        """Get the current size of the search history.
        
        Returns:
            Number of videos in search history
        """
        return len(self.search_history)

    def is_available(self) -> bool:
        """Check if the search backend is available and functional.
        
        Returns:
            True if search functionality is available
        """
        if self.backend == "google_api":
            return bool(self.api_key and gapi_build)
        elif self.backend == "yt_dlp":
            return yt_dlp is not None
        return False
