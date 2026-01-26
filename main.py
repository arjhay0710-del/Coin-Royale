import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from datetime import datetime, timezone
import logging
import asyncio
from typing import Optional
from keep_alive import keep_alive
import google.generativeai as genai

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Google Gemini Configuration
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
gemini_model = genai.GenerativeModel('gemini-2.0-flash-exp')

# Database channel ID
DATABASE_CHANNEL_ID = 1454384036674797689

# Bot branding colors
class Colors:
    PRIMARY = 0x9B59B6  # Purple
    SUCCESS = 0x57F287  # Green
    WARNING = 0xFEE75C  # Yellow
    DANGER = 0xED4245   # Red
    INFO = 0x5865F2     # Blue

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.messages = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# Global data structures
server_configs = {}  # {guild_id: {log_channel}}
song_history = {}  # {user_id: {song_count, last_song}}
pending_database_save = False
last_database_save = datetime.now()

async def generate_song(theme: str, genre: str, mood: str, user_name: str, additional_prompt: str = "") -> str:
    """Generate a song using Google Gemini"""
    try:
        prompt = f"""You are GeNsong, a creative AI song lyricist. Generate original, creative song lyrics.

USER: {user_name}
THEME: {theme}
GENRE: {genre}
MOOD: {mood}
{f'ADDITIONAL INSTRUCTIONS: {additional_prompt}' if additional_prompt else ''}

Generate a complete song with:
- A catchy title
- Verse 1
- Chorus (memorable and repeatable)
- Verse 2
- Chorus (repeat)
- Bridge
- Final Chorus

IMPORTANT RULES:
- Create 100% ORIGINAL lyrics - never reproduce existing song lyrics
- Make it creative, catchy, and emotionally resonant
- Match the specified genre and mood
- Use vivid imagery and metaphors
- Keep verses 4-8 lines, chorus 2-4 lines
- Make the chorus memorable and easy to sing

Format your response EXACTLY like this:

**🎵 [Song Title Here]**

**[Verse 1]**
[lyrics here]

**[Chorus]**
[lyrics here]

**[Verse 2]**
[lyrics here]

**[Chorus]**
[lyrics here]

**[Bridge]**
[lyrics here]

**[Final Chorus]**
[lyrics here]

---
*Genre: {genre} | Mood: {mood}*

Generate the song now:"""

        response = gemini_model.generate_content(prompt)
        return response.text.strip()
    
    except Exception as e:
        logging.error(f"Google Gemini API error: {e}")
        return "🎵 **Error Generating Song**\n\nI'm having trouble creating your song right now. Please try again in a moment!"

async def batch_save_database():
    """Batch database saves to avoid rate limiting"""
    global pending_database_save, last_database_save
    
    if not pending_database_save:
        pending_database_save = True
        await asyncio.sleep(5)
        
        if (datetime.now() - last_database_save).total_seconds() >= 30:
            await save_database()
            last_database_save = datetime.now()
        
        pending_database_save = False

async def load_database():
    """Load data from the database channel"""
    global server_configs, song_history
    
    try:
        db_channel = bot.get_channel(DATABASE_CHANNEL_ID)
        if not db_channel:
            logging.error(f"Database channel {DATABASE_CHANNEL_ID} not found!")
            server_configs = {}
            song_history = {}
            return

        server_configs = {}
        song_history = {}
        
        async for message in db_channel.history(limit=50):
            if message.author == bot.user and message.content.startswith("```json"):
                try:
                    json_content = message.content[7:-3].strip()
                    data = json.loads(json_content)
                    
                    if isinstance(data, dict):
                        server_configs = data.get("server_configs", {})
                        song_history = data.get("song_history", {})
                        
                        logging.info(f"✅ Successfully loaded database:")
                        logging.info(f"   🏢 {len(server_configs)} server configurations")
                        logging.info(f"   🎵 {len(song_history)} song histories")
                        return
                    
                except json.JSONDecodeError as e:
                    logging.warning(f"JSON decode error: {e}")
                    continue
        
        logging.warning("⚠️ No valid database found, starting fresh")
        server_configs = {}
        song_history = {}
        
    except Exception as e:
        logging.error(f"Critical error loading database: {e}")

async def save_database():
    """Save all data to the database channel"""
    try:
        db_channel = bot.get_channel(DATABASE_CHANNEL_ID)
        if not db_channel:
            logging.error(f"Database channel {DATABASE_CHANNEL_ID} not found!")
            return

        database_data = {
            "server_configs": server_configs,
            "song_history": song_history,
            "metadata": {
                "version": "1.0-gensong",
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "total_servers": len(server_configs),
                "total_songs": sum(h.get("song_count", 0) for h in song_history.values())
            }
        }
        
        json_content = json.dumps(database_data, indent=2, ensure_ascii=False)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        
        message_content = f"```json\n{json_content}\n```"
        embed = discord.Embed(
            title="💾 GeNsong Database Backup",
            description=f"```yaml\nVersion: 1.0-gensong\nServers: {database_data['metadata']['total_servers']}\nTotal Songs: {database_data['metadata']['total_songs']}\nUpdated: {timestamp}\n```",
            color=Colors.INFO,
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_footer(text="GeNsong System")
        
        await db_channel.send(content=message_content, embed=embed)
        logging.info(f"✅ Database saved successfully")
        
    except Exception as e:
        logging.error(f"Critical error saving database: {e}")

def is_administrator():
    """Check if user has administrator permission"""
    async def predicate(interaction: discord.Interaction) -> bool:
        if not interaction.user.guild_permissions.administrator:
            embed = discord.Embed(
                title="🚫 Permission Denied",
                description="Only administrators can use this command.",
                color=Colors.DANGER
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True
    return app_commands.check(predicate)

# Commands

@tree.command(name="setup", description="⚙️ Setup GeNsong for your server")
@app_commands.describe(log_channel="Channel for song generation logs (optional)")
@is_administrator()
async def setup_bot(
    interaction: discord.Interaction,
    log_channel: Optional[discord.TextChannel] = None
):
    """Setup bot configuration"""
    await interaction.response.defer(ephemeral=True)
    
    guild_id = str(interaction.guild_id)
    if guild_id not in server_configs:
        server_configs[guild_id] = {}
    
    if log_channel:
        if not log_channel.permissions_for(interaction.guild.me).send_messages:
            embed = discord.Embed(
                title="❌ Permission Error",
                description=f"I don't have permission to send messages in {log_channel.mention}",
                color=Colors.DANGER
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        server_configs[guild_id]["log_channel"] = log_channel.id
    
    asyncio.create_task(batch_save_database())
    
    embed = discord.Embed(
        title="✅ GeNsong Configured",
        description="Bot is ready to generate songs!",
        color=Colors.SUCCESS
    )
    
    if log_channel:
        embed.add_field(name="📋 Log Channel", value=log_channel.mention, inline=False)
    
    embed.add_field(
        name="💡 How to Use",
        value="Use `/generate` to create songs!\n`/generate theme:love genre:pop mood:happy`",
        inline=False
    )
    
    await interaction.followup.send(embed=embed, ephemeral=True)
    logging.info(f"⚙️ Bot configured by {interaction.user.name} in {interaction.guild.name}")

@tree.command(name="generate", description="🎵 Generate a song with AI")
@app_commands.describe(
    theme="Song theme (e.g., love, adventure, friendship)",
    genre="Music genre (e.g., pop, rock, rap, country)",
    mood="Song mood (e.g., happy, sad, energetic, calm)",
    additional="Additional instructions (optional)"
)
async def generate_song_cmd(
    interaction: discord.Interaction,
    theme: str,
    genre: str,
    mood: str,
    additional: Optional[str] = None
):
    """Generate a song"""
    await interaction.response.defer()
    
    # Log song generation
    user_id = str(interaction.user.id)
    if user_id not in song_history:
        song_history[user_id] = {"song_count": 0, "last_song": None}
    
    song_history[user_id]["song_count"] += 1
    song_history[user_id]["last_song"] = datetime.now(timezone.utc).isoformat()
    
    asyncio.create_task(batch_save_database())
    
    # Generate song
    song_lyrics = await generate_song(
        theme=theme,
        genre=genre,
        mood=mood,
        user_name=interaction.user.display_name,
        additional_prompt=additional or ""
    )
    
    # Split into chunks if too long (Discord embed description limit is 4096)
    if len(song_lyrics) > 4000:
        # Send as multiple messages
        embed1 = discord.Embed(
            title="🎵 Your Generated Song",
            description=song_lyrics[:4000],
            color=Colors.PRIMARY,
            timestamp=datetime.now(timezone.utc)
        )
        embed1.set_author(
            name=interaction.user.display_name,
            icon_url=interaction.user.display_avatar.url
        )
        embed1.add_field(name="🎸 Theme", value=theme, inline=True)
        embed1.add_field(name="🎼 Genre", value=genre, inline=True)
        embed1.add_field(name="💫 Mood", value=mood, inline=True)
        
        await interaction.followup.send(embed=embed1)
        
        # Send continuation
        embed2 = discord.Embed(
            description=song_lyrics[4000:],
            color=Colors.PRIMARY
        )
        embed2.set_footer(text=f"GeNsong • Song #{song_history[user_id]['song_count']}")
        await interaction.followup.send(embed=embed2)
    else:
        embed = discord.Embed(
            title="🎵 Your Generated Song",
            description=song_lyrics,
            color=Colors.PRIMARY,
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_author(
            name=interaction.user.display_name,
            icon_url=interaction.user.display_avatar.url
        )
        embed.add_field(name="🎸 Theme", value=theme, inline=True)
        embed.add_field(name="🎼 Genre", value=genre, inline=True)
        embed.add_field(name="💫 Mood", value=mood, inline=True)
        if additional:
            embed.add_field(name="📝 Additional", value=additional[:100], inline=False)
        embed.set_footer(text=f"GeNsong • Song #{song_history[user_id]['song_count']}")
        
        await interaction.followup.send(embed=embed)
    
    # Log to log channel
    guild_id = str(interaction.guild_id)
    if guild_id in server_configs and "log_channel" in server_configs[guild_id]:
        log_channel = bot.get_channel(server_configs[guild_id]["log_channel"])
        if log_channel:
            log_embed = discord.Embed(
                title="🎵 Song Generated",
                color=Colors.INFO,
                timestamp=datetime.now(timezone.utc)
            )
            log_embed.add_field(name="User", value=f"{interaction.user.mention}", inline=True)
            log_embed.add_field(name="Channel", value=f"{interaction.channel.mention}", inline=True)
            log_embed.add_field(name="Theme", value=theme, inline=True)
            log_embed.add_field(name="Genre", value=genre, inline=True)
            log_embed.add_field(name="Mood", value=mood, inline=True)
            log_embed.add_field(name="Total Songs", value=str(song_history[user_id]['song_count']), inline=True)
            
            try:
                await log_channel.send(embed=log_embed)
            except:
                pass

@tree.command(name="help", description="❓ View help information")
async def help_command(interaction: discord.Interaction):
    """Show help information"""
    await interaction.response.defer(ephemeral=True)
    
    embed = discord.Embed(
        title="🎵 GeNsong - AI Song Generator",
        description="Generate creative, original songs with AI!\n\nPowered by Google Gemini 2.0 Flash",
        color=Colors.PRIMARY
    )
    
    embed.add_field(
        name="🎸 How to Generate Songs",
        value=(
            "Use the `/generate` command:\n"
            "```/generate theme:love genre:pop mood:happy```\n\n"
            "**Parameters:**\n"
            "• **Theme**: What the song is about (love, adventure, etc.)\n"
            "• **Genre**: Music style (pop, rock, rap, country, etc.)\n"
            "• **Mood**: Feeling (happy, sad, energetic, calm, etc.)\n"
            "• **Additional**: Extra instructions (optional)"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🎼 Popular Genres",
        value="Pop • Rock • Rap • Country • R&B • Jazz • EDM • Folk • Metal • Indie",
        inline=False
    )
    
    embed.add_field(
        name="💫 Example Commands",
        value=(
            "`/generate theme:heartbreak genre:ballad mood:sad`\n"
            "`/generate theme:summer genre:reggae mood:relaxed`\n"
            "`/generate theme:motivation genre:hip-hop mood:energetic`\n"
            "`/generate theme:space genre:electronic mood:mysterious`"
        ),
        inline=False
    )
    
    if interaction.user.guild_permissions.administrator:
        embed.add_field(
            name="🔧 Admin Commands",
            value=(
                "`/setup` - Configure the bot\n"
                "`/config` - View current settings\n"
                "`/stats` - View generation statistics"
            ),
            inline=False
        )
    
    embed.set_footer(text="GeNsong - Powered by AI")
    
    await interaction.followup.send(embed=embed, ephemeral=True)

@tree.command(name="config", description="📊 View current bot configuration")
@is_administrator()
async def view_config(interaction: discord.Interaction):
    """View current server configuration"""
    await interaction.response.defer(ephemeral=True)
    
    guild_id = str(interaction.guild_id)
    
    if guild_id not in server_configs or not server_configs[guild_id]:
        embed = discord.Embed(
            title="⚙️ Server Configuration",
            description="No configuration set yet. Use `/setup` to get started!",
            color=Colors.INFO
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        return
    
    config = server_configs[guild_id]
    
    embed = discord.Embed(
        title="⚙️ Server Configuration",
        description=f"**{interaction.guild.name}**",
        color=Colors.PRIMARY,
        timestamp=datetime.now(timezone.utc)
    )
    
    if "log_channel" in config:
        log_channel = bot.get_channel(config["log_channel"])
        embed.add_field(
            name="📋 Log Channel",
            value=log_channel.mention if log_channel else "Not found",
            inline=False
        )
    
    embed.set_footer(text="GeNsong")
    
    await interaction.followup.send(embed=embed, ephemeral=True)

@tree.command(name="stats", description="📊 View song generation statistics")
@is_administrator()
async def view_stats(interaction: discord.Interaction):
    """View song statistics"""
    await interaction.response.defer(ephemeral=True)
    
    total_songs = sum(data.get("song_count", 0) for data in song_history.values())
    total_users = len(song_history)
    
    embed = discord.Embed(
        title="📊 Song Generation Statistics",
        description=f"**{interaction.guild.name}**",
        color=Colors.INFO,
        timestamp=datetime.now(timezone.utc)
    )
    
    embed.add_field(name="🎵 Total Songs", value=str(total_songs), inline=True)
    embed.add_field(name="👥 Unique Users", value=str(total_users), inline=True)
    embed.add_field(name="🏢 Servers", value=str(len(server_configs)), inline=True)
    
    # Top 5 users
    if song_history:
        sorted_users = sorted(
            song_history.items(),
            key=lambda x: x[1].get("song_count", 0),
            reverse=True
        )[:5]
        
        top_users = "\n".join([
            f"<@{user_id}>: {data.get('song_count', 0)} songs"
            for user_id, data in sorted_users
        ])
        
        embed.add_field(name="🔥 Top Songwriters", value=top_users or "No data", inline=False)
    
    embed.set_footer(text="GeNsong Statistics")
    
    await interaction.followup.send(embed=embed, ephemeral=True)

@tree.command(name="mysongs", description="🎤 View your song generation history")
async def my_songs(interaction: discord.Interaction):
    """View user's song history"""
    await interaction.response.defer(ephemeral=True)
    
    user_id = str(interaction.user.id)
    
    if user_id not in song_history or song_history[user_id].get("song_count", 0) == 0:
        embed = discord.Embed(
            title="🎤 Your Song History",
            description="You haven't generated any songs yet!\n\nUse `/generate` to create your first song!",
            color=Colors.WARNING
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        return
    
    user_data = song_history[user_id]
    
    embed = discord.Embed(
        title="🎤 Your Song History",
        description=f"You've generated **{user_data['song_count']}** songs!",
        color=Colors.PRIMARY,
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_author(
        name=interaction.user.display_name,
        icon_url=interaction.user.display_avatar.url
    )
    
    if user_data.get("last_song"):
        try:
            last_song_time = datetime.fromisoformat(user_data["last_song"])
            embed.add_field(
                name="⏰ Last Song Generated",
                value=f"<t:{int(last_song_time.timestamp())}:R>",
                inline=False
            )
        except:
            pass
    
    embed.set_footer(text="GeNsong • Keep creating!")
    
    await interaction.followup.send(embed=embed, ephemeral=True)

# Events

@bot.event
async def on_ready():
    """Bot startup"""
    logging.info(f"🚀 GeNsong logged in as {bot.user}")
    logging.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    await load_database()
    
    try:
        synced = await tree.sync()
        logging.info(f"✅ Synced {len(synced)} slash commands")
    except Exception as e:
        logging.error(f"❌ Failed to sync commands: {e}")
    
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.listening,
            name="songs | /generate"
        )
    )
    
    logging.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logging.info(f"🎯 GeNsong is online!")
    logging.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

@bot.event
async def on_guild_join(guild):
    """Handle bot joining a guild"""
    logging.info(f"🆕 Joined new server: {guild.name} ({guild.id})")

# Get tokens and start
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN is not set in environment variables.")

if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY is not set in environment variables.")

keep_alive()
bot.run(DISCORD_TOKEN)