# OneTap AI - Discord Bot Integration

This is the Discord bot integration (Phase 5) for OneTap AI, allowing users to trigger analysis and chat with the RAG coach directly from their Discord servers.

## Setup

1. Install requirements:
   ```bash
   pip install discord.py httpx
   ```

2. Get a Discord Bot Token from the [Discord Developer Portal](https://discord.com/developers/applications).

3. Set your environment variables:
   ```bash
   export DISCORD_BOT_TOKEN="your_bot_token"
   # Optional: Point to production backend
   export ONETAP_API_URL="https://api.onetapai.com/v1"
   ```

4. Run the bot:
   ```bash
   python bot.py
   ```

## Commands

- `!analyze <riot_id>`: Triggers the backend analysis pipeline and returns a coaching summary.
  - *Example*: `!analyze Friday#PlayZ`
- `!coach <riot_id> <question>`: Queries the RAG knowledge base using the player's profile context.
  - *Example*: `!coach Friday#PlayZ how do I hold A site on Ascent?`
