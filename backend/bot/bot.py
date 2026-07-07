import os
import discord
from discord.ext import commands
import httpx

# Discord Bot Setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Backend API URL (FastAPI)
API_URL = os.getenv("ONETAP_API_URL", "http://127.0.0.1:8000/api/v1")

@bot.event
async def on_ready():
    print(f'OneTap AI Bot connected as {bot.user}')

@bot.command(name='analyze')
async def analyze_player(ctx, riot_id: str):
    """Trigger a mechanical and spatial analysis for a player."""
    await ctx.send(f"🔍 Analyzing recent matches for **{riot_id}**... This might take a moment.")
    
    try:
        # Call our internal FastAPI backend
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{API_URL}/analyze", 
                json={"riot_id": riot_id, "region": "na", "match_count": 5}
            )
            response.raise_for_status()
            data = response.json()
            
        summary = data.get("coaching_summary", "Analysis complete! Check the dashboard for details.")
        
        embed = discord.Embed(title=f"Analysis Report: {riot_id}", color=discord.Color.red())
        embed.add_field(name="Coaching Summary", value=summary, inline=False)
        embed.set_footer(text="Powered by OneTap AI Radiant Engine")
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ Failed to analyze player. Error: {str(e)}")

@bot.command(name='coach')
async def ask_coach(ctx, riot_id: str, *, question: str):
    """Ask the OneTap AI RAG Coach a specific question."""
    await ctx.send("🧠 *Consulting the Radiant playbook...*")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{API_URL}/coach", 
                json={"riot_id": riot_id, "question": question}
            )
            response.raise_for_status()
            data = response.json()
            
        answer = data.get("answer", "I don't have an answer for that right now.")
        
        embed = discord.Embed(title=f"OneTap AI Coach", description=answer, color=discord.Color.gold())
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ Failed to reach the coach. Error: {str(e)}")

if __name__ == "__main__":
    TOKEN = os.getenv("DISCORD_BOT_TOKEN")
    if not TOKEN:
        print("WARNING: DISCORD_BOT_TOKEN not set. Run: export DISCORD_BOT_TOKEN='your_token_here'")
    else:
        bot.run(TOKEN)
