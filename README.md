# 🪞 OVOS Skill — Share To Mirror (YouTube Control)

Transform your **MagicMirror²** into a voice-controlled YouTube player! This OVOS skill lets you search, play, and control YouTube videos on your mirror using simple voice commands.

## ✨ What You Can Do

- 🔎 **Search and play** YouTube videos by topic with intelligent variety
- 📱 **Play YouTube Shorts** - short-form videos (under 1 minute)
- 🎬 **Play long-form videos** - full-length content (10+ minutes)
- 🔗 **Play specific videos** using YouTube URLs or video names
- 📺 **Play channel content** from your favorite YouTube channels
- ⏯️ **Control playback** with pause, resume, stop, skip, and restart
- ⏪/⏩ **Navigate videos** by seeking forward or backward (custom or default seconds)
- 🧠 **Check status** to see what's currently playing
- 🛠️ **Customize defaults** for captions and video quality
- 🎯 **Smart search** that avoids repeating the same videos for identical requests

This skill features a modular architecture with intelligent search capabilities, fuzzy matching, and anti-repetition algorithms to provide varied content every time.

## 🧩 What You'll Need

Before getting started, make sure you have:

- An **Open Voice OS device**
- A **MagicMirror²** with the **MMM-ShareToMirror** module installed
- Both devices connected to the same network
- Internet access for YouTube content

## 📦 Installation

Install the skill using `pip`:

```bash
pip install git+https://github.com/smartgic/ovos-skill-share-to-mirror.git
```

---

## ⚙️ Configuration

Setting up the skill requires configuring both your MagicMirror² and your OVOS device.

### Step 1: Set Up MMM-ShareToMirror on Your MagicMirror²

Add the following configuration to your `~/MagicMirror/config/config.js`:

```js
{
  module: "MMM-ShareToMirror",
  position: "bottom_center",
  config: {
    // Basic server settings
    port: 8570,
    https: {
      enabled: false,   // Enable for HTTPS (requires SSL certificates)
      keyPath: "",      // Path to SSL private key
      certPath: ""      // Path to SSL certificate
    },

    // Hide the module UI (videos appear as overlay)
    invisible: true,

    // Video overlay appearance
    overlay: {
      width: "70vw",
      maxWidth: "1280px",
      aspectRatio: "16 / 9",
      top: "50%",
      left: "50%",
      zIndex: 9999,
      borderRadius: "18px",
      boxShadow: "0 10px 40px rgba(0,0,0,.55)"
    },

    // Default video settings
    caption: { enabled: false, lang: "en" },
    quality: { target: "auto", lock: false }
  }
}
```

**Important Notes:**
- The default port is **8570** - make sure this port is available
- HTTPS is recommended for security but requires valid SSL certificates
- The `invisible: true` setting hides the module UI, showing only the video overlay

#### Test Your MagicMirror² Setup

Verify everything is working by testing the API endpoints:

```bash
# Check if the service is running
curl http://<MIRROR_IP>:8570/api/health

# Test video playback
curl -X POST http://<MIRROR_IP>:8570/api/play \
  -H "Content-Type: application/json" \
  -d '{"url":"https://youtu.be/dQw4w9WgXcQ"}'
```

Replace `<MIRROR_IP>` with your MagicMirror²'s actual IP address.

### Step 2: Configure the OVOS Skill

Configure the skill settings either through the OVOS GUI or by editing the settings file directly.

**Settings file location:** `~/.config/mycroft/skills/ovos-skill-share-to-mirror.smartgic/settings.json`

**Basic configuration:**

```json
{
  "base_url": "http://<MIRROR_IP>:8570",
  "verify_ssl": true,
  "request_timeout": 6,

  "caption_enabled": false,
  "caption_lang": "en",
  "quality_target": "auto",
  "quality_lock": false,

  "search_backend": "yt_dlp",
  "youtube_api_key": ""
}
```

**Configuration Options Explained:**

- `base_url`: The full URL to your MagicMirror² (replace `<MIRROR_IP>` with the actual IP)
- `verify_ssl`: Set to `false` only if using self-signed certificates for testing
- `request_timeout`: How long to wait for responses from the mirror (in seconds)
- `search_backend`: Use `"yt_dlp"` for basic search or `"google_api"` for more accurate results
- `youtube_api_key`: Required only if using `"google_api"` as the search backend

**Pro Tips:**
- Use the actual IP address instead of `.local` hostnames for better reliability
- If your MagicMirror² is behind authentication, add an `api_token` field to the settings

---

## 🗣️ Voice Commands

All commands must include "**on the mirror**" to ensure the skill recognizes them correctly and doesn't conflict with other media skills.

### Video Search and Playback
- "**Play a video about [topic] on the mirror**"
  - Example: "Play a video about cooking pasta on the mirror"
- "**Play shorts about [topic] on the mirror**"
  - Example: "Play shorts about cats on the mirror"
- "**Play long videos about [topic] on the mirror**"
  - Example: "Play long videos about history on the mirror"
- "**Play the video called [name] on the mirror**"
  - Example: "Play the video called Bohemian Rhapsody on the mirror"
- "**Play something from [channel] channel on the mirror**"
  - Example: "Play something from TED Talks channel on the mirror"

### Direct URL Playback
- "**Play this URL on the mirror [YouTube URL]**"
  - Example: "Play this URL on the mirror https://www.youtube.com/watch?v=dQw4w9WgXcQ"
- "**Send this to the mirror [YouTube URL]**"
- "**Cast [YouTube URL] to the mirror**"

### Playback Controls
- "**Pause the video on the mirror**"
- "**Resume the video on the mirror**"
- "**Stop the video on the mirror**"
- "**Skip this video on the mirror**"
- "**Restart the video on the mirror**"

### Navigation
- "**Rewind [X] seconds on the mirror**"
  - Example: "Rewind 30 seconds on the mirror"
- "**Forward [X] seconds on the mirror**"
  - Example: "Forward 10 seconds on the mirror"
- "**Go back [X] seconds on the mirror**"
- "**Fast forward on the mirror**"

### Status and Information
- "**What's playing on the mirror**"
- "**Mirror status**"
- "**What's the mirror status**"
- "**Check mirror status**"

---

## 🧠 How It Works

Here's what happens when you give a voice command:

1. **Voice Recognition** – Your OVOS device recognizes phrases containing "on the mirror"
2. **Intelligent Search** – The skill uses advanced search algorithms:
   - **Anti-repetition**: Tracks search history to avoid playing the same videos
   - **Query enhancement**: Adds variety modifiers for different results
   - **Duration filtering**: Searches specifically for Shorts (≤60s) or long videos (≥10min)
   - **Multiple results**: Fetches 5 results and selects one not recently played
   - **Fuzzy matching**: Uses intelligent query understanding (optional)
3. **API Communication** – The skill sends commands to your MagicMirror² using these endpoints:
   - `/api/play` – Start playing a video
   - `/api/control` – Pause, resume, seek, or restart videos
   - `/api/stop` – Stop playback
   - `/api/status` – Check what's currently playing
   - `/api/options` – Set caption and quality preferences

The skill features a **modular architecture** with separate components for API communication, YouTube search, and utility functions, making it easy to maintain and extend.

### Smart Search Examples

**Variety in Action:**
- First request: "Play cooking videos" → Returns top cooking video
- Second request: "Play cooking videos" → Returns "cooking latest" or "cooking tutorial"
- Third request: "Play shorts about cooking" → Returns short cooking videos specifically

**Duration-Specific Search:**
- "Play shorts about cats" → Finds videos ≤60 seconds about cats
- "Play long videos about space" → Finds videos ≥10 minutes about space

---

## 🐞 Troubleshooting

### Connection Issues
**Problem:** "I couldn't reach your MagicMirror"

**Solutions:**
- Double-check your `base_url` setting includes the correct IP address and port (default: 8570)
- Test the connection manually: `curl http://<MIRROR_IP>:8570/api/health`
- Ensure both devices are on the same network
- If using HTTPS with self-signed certificates, temporarily set `verify_ssl` to `false` for testing

### Wrong Video Playing
**Problem:** The skill plays unexpected videos

**Solutions:**
- Be more specific in your requests: "Play a **YouTube video** about [specific topic] **on the mirror**"
- Try switching from `yt_dlp` to `google_api` in settings for more accurate search results
- Include the word "YouTube" in your command to clarify the content source

### Voice Recognition Issues
**Problem:** Other skills respond instead of this one

**Solutions:**
- Always include "**on the mirror**" in your commands
- Check if other media skills have higher priority and adjust accordingly
- Restart your OVOS device if voice recognition seems inconsistent

---

## 📄 License

Apache‑2.0
