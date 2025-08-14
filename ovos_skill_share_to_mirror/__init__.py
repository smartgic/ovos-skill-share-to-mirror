"""OVOS Skill for controlling YouTube playback on MagicMirror² via MMM-ShareToMirror."""

from __future__ import annotations

from ovos_utils.log import LOG
from ovos_workshop.skills import OVOSSkill

from .api_client import MirrorAPIClient
from .youtube_search import YouTubeSearcher
from .utils import (
    DEFAULT_BASE_URL,
    DEFAULT_SEEK_SECONDS,
    DEFAULT_TIMEOUT,
    build_channel_search_query,
    extract_number_from_text,
    extract_url_from_text,
    is_valid_url,
    normalize_base_url,
)


class ShareToMirrorSkill(OVOSSkill):
    """OVOS Skill for controlling YouTube playback on MagicMirror² via MMM-ShareToMirror.
    
    This skill provides voice control for YouTube videos displayed on a MagicMirror²
    device through the MMM-ShareToMirror module. It supports video search, URL playback,
    transport controls (play/pause/stop), seeking, and status queries.
    
    The skill is organized into separate modules:
    - api_client: Handles HTTP communication with MagicMirror
    - youtube_search: Manages YouTube video search functionality  
    - utils: Common utility functions and constants
    
    Attributes:
        api_client: MirrorAPIClient instance for API communication
        youtube_searcher: YouTubeSearcher instance for video search
        
    Example:
        Voice commands:
        - "Play a video about cooking on the mirror"
        - "Pause the video on the mirror"
        - "Rewind 30 seconds on the mirror"
    """

    def initialize(self) -> None:
        """Initialize the skill by loading settings and creating components.
        
        This method sets up the API client, YouTube searcher, and registers
        all intent handlers for voice commands.
        """
        # Load settings
        settings = self._load_settings()
        
        # Create API client for MagicMirror communication
        self.api_client = MirrorAPIClient(
            base_url=settings["base_url"],
            api_token=settings["api_token"],
            verify_ssl=settings["verify_ssl"],
            timeout=settings["timeout"]
        )
        
        # Create YouTube searcher
        self.youtube_searcher = YouTubeSearcher(
            backend=settings["search_backend"],
            api_key=settings["youtube_api_key"]
        )
        
        # Store video options for later use
        self.video_options = {
            "caption_enabled": settings["caption_enabled"],
            "caption_lang": settings["caption_lang"],
            "quality_target": settings["quality_target"],
            "quality_lock": settings["quality_lock"],
        }
        
        # Register intent handlers
        self._register_intents()
        
        LOG.info(f"[ShareToMirror] Initialized with base_url={settings['base_url']}, "
                f"search_backend={settings['search_backend']}")

    def _load_settings(self) -> dict:
        """Load and validate skill configuration settings.
        
        Returns:
            Dictionary of validated settings
        """
        return {
            "base_url": normalize_base_url(self.settings.get("base_url", DEFAULT_BASE_URL)),
            "api_token": (self.settings.get("api_token") or "").strip() or None,
            "verify_ssl": bool(self.settings.get("verify_ssl", True)),
            "timeout": max(1, int(self.settings.get("request_timeout", DEFAULT_TIMEOUT))),
            "caption_enabled": bool(self.settings.get("caption_enabled", False)),
            "caption_lang": self.settings.get("caption_lang", "en"),
            "quality_target": self.settings.get("quality_target", "auto"),
            "quality_lock": bool(self.settings.get("quality_lock", False)),
            "search_backend": self.settings.get("search_backend", "yt_dlp"),
            "youtube_api_key": (self.settings.get("youtube_api_key") or "").strip() or None,
        }

    def _register_intents(self) -> None:
        """Register all intent handlers for voice command recognition.
        
        Maps intent files to their corresponding handler methods.
        Logs errors for any intents that fail to register.
        """
        intent_handlers = [
            ("mirror.play.topic.intent", self.handle_play_topic),
            ("mirror.play.url.intent", self.handle_play_url),
            ("mirror.play.video.intent", self.handle_play_video),
            ("mirror.play.channel.intent", self.handle_play_channel),
            ("mirror.play.shorts.intent", self.handle_play_shorts),
            ("mirror.play.long.intent", self.handle_play_long),
            ("mirror.pause.intent", self.handle_pause),
            ("mirror.resume.intent", self.handle_resume),
            ("mirror.stop.intent", self.handle_stop_intent),
            ("mirror.rewind.intent", self.handle_rewind),
            ("mirror.forward.intent", self.handle_forward),
            ("mirror.skip.intent", self.handle_skip),
            ("mirror.restart.intent", self.handle_restart),
            ("mirror.status.intent", self.handle_status),
        ]
        
        for intent_file, handler in intent_handlers:
            try:
                self.register_intent_file(intent_file, handler)
            except Exception as e:
                LOG.error(f"[ShareToMirror] Failed to register {intent_file}: {e}")

    # ===== Intent handlers =====

    def handle_play_topic(self, message) -> None:
        """Handle intent to play a YouTube video by searching for a topic.
        
        Args:
            message: Intent message containing the topic to search for.
            
        Voice examples:
            - "Play a video about cooking on the mirror"
            - "Show me something about space exploration on the mirror"
        """
        topic = (message.data.get("topic") or "").strip()
        self._handle_search_and_play(topic, "topic")

    def handle_play_video(self, message) -> None:
        """Handle intent to play a specific video by name.
        
        Args:
            message: Intent message containing the video name.
            
        Voice examples:
            - "Play the video called Bohemian Rhapsody on the mirror"
            - "Show the video named Python tutorial on the mirror"
        """
        video_name = (message.data.get("video") or message.data.get("name") or "").strip()
        self._handle_search_and_play(video_name, "video")

    def handle_play_channel(self, message) -> None:
        """Handle intent to play content from a specific YouTube channel.
        
        Args:
            message: Intent message containing the channel name.
            
        Voice examples:
            - "Play something from TED Talks channel on the mirror"
            - "Show me videos from National Geographic on the mirror"
        """
        channel = (message.data.get("channel") or "").strip()
        if not channel:
            self.speak_dialog("not_found", {"topic": "channel"})
            return
            
        # Build optimized search query for channel content
        search_query = build_channel_search_query(channel)
        LOG.info(f"[ShareToMirror] Searching for channel content: {search_query!r}")
        url = self.youtube_searcher.search(search_query)
        if not url:
            self.speak_dialog("not_found", {"topic": channel})
            return
            
        if self._play_video(url):
            self.speak_dialog("playing.topic", {"topic": f"{channel} channel"})

    def handle_play_shorts(self, message) -> None:
        """Handle intent to play YouTube Shorts about a specific topic.
        
        Args:
            message: Intent message containing the topic to search for.
            
        Voice examples:
            - "Play shorts about cooking on the mirror"
            - "Show me shorts about cats on the mirror"
            - "Find short videos about music on the mirror"
        """
        topic = (message.data.get("topic") or "").strip()
        self._handle_search_and_play(topic, "shorts", video_type="shorts")

    def handle_play_long(self, message) -> None:
        """Handle intent to play long-form YouTube videos about a specific topic.
        
        Args:
            message: Intent message containing the topic to search for.
            
        Voice examples:
            - "Play long videos about history on the mirror"
            - "Show me full videos about science on the mirror"
            - "Find complete videos about documentaries on the mirror"
        """
        topic = (message.data.get("topic") or "").strip()
        self._handle_search_and_play(topic, "long videos", video_type="long")

    def handle_play_url(self, message) -> None:
        """Handle intent to play a specific YouTube URL.
        
        Args:
            message: Intent message containing the URL to play.
            
        Voice examples:
            - "Play this URL on the mirror https://youtube.com/watch?v=..."
            - "Send this to the mirror https://youtu.be/..."
        """
        url = (message.data.get("url") or "").strip()
        if not is_valid_url(url):
            # Extract URL from utterance if not in message data
            utterance = (message.data.get("utterance") or "").strip()
            url = extract_url_from_text(utterance)
        
        if not url:
            self.speak_dialog("api_error")
            return
            
        if self._play_video(url):
            self.speak_dialog("playing.url")

    def handle_pause(self, _message) -> None:
        """Handle intent to pause video playback.
        
        Args:
            _message: Intent message (unused).
            
        Voice examples:
            - "Pause the video on the mirror"
            - "Pause playback on the mirror"
        """
        if self.api_client.control_playback("pause"):
            self.speak_dialog("paused")

    def handle_resume(self, _message) -> None:
        """Handle intent to resume video playback.
        
        Args:
            _message: Intent message (unused).
            
        Voice examples:
            - "Resume the video on the mirror"
            - "Continue playback on the mirror"
        """
        if self.api_client.control_playback("resume"):
            self.speak_dialog("resumed")

    def handle_stop_intent(self, _message) -> None:
        """Handle intent to stop video playback completely.
        
        Args:
            _message: Intent message (unused).
            
        Voice examples:
            - "Stop the video on the mirror"
            - "Stop playback on the mirror"
        """
        if self.api_client.stop_video():
            self.speak_dialog("stopped")

    def handle_rewind(self, message) -> None:
        """Handle intent to rewind video by specified or default seconds.
        
        Args:
            message: Intent message potentially containing number of seconds.
            
        Voice examples:
            - "Rewind 30 seconds on the mirror"
            - "Go back 10 seconds on the mirror"
            - "Rewind on the mirror" (uses default seconds)
        """
        utterance = (message.data.get("utterance") or "").lower()
        seconds_val = extract_number_from_text(utterance)
        seconds = int(seconds_val) if seconds_val else DEFAULT_SEEK_SECONDS
        
        if self.api_client.control_playback("rewind", seconds=seconds):
            self.speak_dialog("rewound", {"seconds": seconds})

    def handle_forward(self, message) -> None:
        """Handle intent to fast-forward video by specified or default seconds.
        
        Args:
            message: Intent message potentially containing number of seconds.
            
        Voice examples:
            - "Forward 30 seconds on the mirror"
            - "Skip ahead 15 seconds on the mirror"
            - "Fast forward on the mirror" (uses default seconds)
        """
        utterance = (message.data.get("utterance") or "").lower()
        seconds_val = extract_number_from_text(utterance)
        seconds = int(seconds_val) if seconds_val else DEFAULT_SEEK_SECONDS
        
        if self.api_client.control_playback("forward", seconds=seconds):
            self.speak_dialog("forwarded", {"seconds": seconds})

    def handle_skip(self, _message) -> None:
        """Handle intent to skip to next video or skip current video.
        
        Args:
            _message: Intent message (unused).
            
        Voice examples:
            - "Skip this video on the mirror"
            - "Next video on the mirror"
        """
        # For now, skip means stop current video
        if self.api_client.stop_video():
            self.speak_dialog("stopped")

    def handle_restart(self, _message) -> None:
        """Handle intent to restart current video from the beginning.
        
        Args:
            _message: Intent message (unused).
            
        Voice examples:
            - "Restart the video on the mirror"
            - "Start over on the mirror"
        """
        if self.api_client.control_playback("restart"):
            self.speak_dialog("restarted")

    def handle_status(self, _message) -> None:
        """Handle intent to query current playback status.
        
        Args:
            _message: Intent message (unused).
            
        Voice examples:
            - "What's playing on the mirror"
            - "Mirror status"
            - "What's the current video on the mirror"
        """
        status_data = self.api_client.get_status()
        if not status_data:
            self.speak_dialog("cannot_connect")
            return
            
        state = status_data.get("state", {})
        playing = state.get("playing", False)
        last = state.get("lastUrl") or state.get("lastVideoId") or "unknown"
        self.speak_dialog("status", {
            "state": "playing" if playing else "stopped", 
            "last": last
        })

    # ===== OVOS Framework Integration =====

    def stop(self) -> bool:
        """Handle global stop command from OVOS framework.
        
        Returns:
            True if stop command was successfully sent, False otherwise.
        """
        return self.api_client.stop_video()

    def shutdown(self) -> None:
        """Clean up resources when skill shuts down.
        
        Properly closes API client connections to prevent resource leaks.
        """
        if hasattr(self, 'api_client'):
            self.api_client.close()
        super().shutdown()

    # ===== Helper Methods =====

    def _handle_search_and_play(self, search_term: str, content_type: str, 
                               video_type: str = "any") -> None:
        """Consolidated handler for search-based video playback.
        
        Args:
            search_term: The term to search for
            content_type: Type of content for error messages
            video_type: Video duration type ('any', 'shorts', 'long')
        """
        if not search_term:
            self.speak_dialog("not_found", {"topic": content_type})
            return
            
        LOG.info(f"[ShareToMirror] Searching YouTube for {content_type}: {search_term!r}")
        url = self.youtube_searcher.search(search_term, video_type=video_type)
        if not url:
            topic_name = f"{search_term} {content_type}" if content_type != "topic" else search_term
            self.speak_dialog("not_found", {"topic": topic_name})
            return
            
        if self._play_video(url):
            topic_name = f"{search_term} {content_type}" if content_type != "topic" else search_term
            self.speak_dialog("playing.topic", {"topic": topic_name})

    def _play_video(self, url: str) -> bool:
        """Play a video URL on the mirror with configured options.
        
        Args:
            url: YouTube or other video URL to play
            
        Returns:
            True if playback started successfully, False otherwise
        """
        # Start video playback
        if not self.api_client.play_video(url):
            return False
            
        # Apply video options (captions, quality)
        success = self.api_client.set_options(
            caption_enabled=self.video_options["caption_enabled"],
            caption_lang=self.video_options["caption_lang"],
            quality_target=self.video_options["quality_target"],
            quality_lock=self.video_options["quality_lock"]
        )
        
        if not success:
            LOG.warning("[ShareToMirror] Failed to set video options")
            
        return True



def create_skill() -> ShareToMirrorSkill:
    """Create and return a new ShareToMirrorSkill instance.
    
    Returns:
        Initialized ShareToMirrorSkill instance ready for use.
    """
    return ShareToMirrorSkill()
