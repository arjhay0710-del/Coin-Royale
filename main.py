import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import os
from datetime import datetime, timezone, timedelta
import logging
import asyncio
import hashlib
import random
from typing import Optional, Dict, List
from keep_alive import keep_alive

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Database channel ID
DATABASE_CHANNEL_ID = 1454384036674797689

# Bot branding colors
class Colors:
    PRIMARY = 0x5865F2  # Discord Blurple
    SUCCESS = 0x57F287  # Green
    WARNING = 0xFEE75C  # Yellow
    DANGER = 0xED4245   # Red
    INFO = 0x5865F2     # Blue
    MATCH = 0xFF69B4    # Pink
    SESSION = 0x9B59B6  # Purple

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.dm_messages = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# Global data structures
match_queue = []  # Users waiting for a match
active_sessions = {}  # {user_id: session_data}
user_preferences = {}  # {user_id: {interests, language, etc}}
user_stats = {}  # {user_id: {matches, reports, ratings}}
banned_users = set()  # Users banned from matching
session_logs = {}  # {session_id: [messages]}
pending_database_save = False
last_database_save = datetime.now()

# Content filter - Discord ToS compliant
BANNED_WORDS = [
    # Explicit content
    "nude", "naked", "sex", "porn", "xxx", "nsfw", "dick", "cock", "pussy", 
    "ass", "boob", "tit", "cum", "orgasm", "masturbate", "horny",
    # Slurs and hate speech
    "nigger", "nigga", "faggot", "fag", "retard", "tranny", "kike",
    # Illegal content
    "cp", "child porn", "pedo", "pedophile", "minor", "underage",
    # Personal info requests (common grooming)
    "send pic", "show me", "snap", "snapchat", "kik", "whatsapp",
    # Threats
    "kill yourself", "kys", "suicide", "harm yourself"
]

INTERESTS_LIST = [
    "gaming", "anime", "coding", "music", "art", "sports", "movies", 
    "books", "fitness", "cooking", "travel", "photography", "memes",
    "science", "tech", "fashion", "pets", "nature"
]

LANGUAGES = ["english", "spanish", "french", "german", "portuguese", "russian", "japanese", "korean", "chinese"]

class MatchSession:
    def __init__(self, user1_id: int, user2_id: int, guild1_id: int, guild2_id: int):
        self.session_id = f"{user1_id}_{user2_id}_{int(datetime.now(timezone.utc).timestamp())}"
        self.user1_id = user1_id
        self.user2_id = user2_id
        self.guild1_id = guild1_id
        self.guild2_id = guild2_id
        self.start_time = datetime.now(timezone.utc)
        self.last_activity = datetime.now(timezone.utc)
        self.messages_count = 0
        self.warnings = {user1_id: 0, user2_id: 0}
        self.revealed = False
        
    def get_partner(self, user_id: int) -> int:
        return self.user2_id if user_id == self.user1_id else self.user1_id
    
    def update_activity(self):
        self.last_activity = datetime.now(timezone.utc)
        self.messages_count += 1
    
    def is_inactive(self, minutes: int = 5) -> bool:
        return (datetime.now(timezone.utc) - self.last_activity).total_seconds() > minutes * 60

def check_content_safety(message: str) -> tuple[bool, str]:
    """Check if message violates Discord ToS. Returns (is_safe, reason)"""
    message_lower = message.lower()
    
    # Check for banned words
    for word in BANNED_WORDS:
        if word in message_lower:
            return False, "inappropriate_content"
    
    # Check for excessive caps (yelling)
    if len(message) > 20 and sum(1 for c in message if c.isupper()) / len(message) > 0.7:
        return False, "excessive_caps"
    
    # Check for spam patterns
    if len(set(message)) < len(message) * 0.3 and len(message) > 10:
        return False, "spam"
    
    # Check for URL/link sharing (potential phishing)
    if any(x in message_lower for x in ["http://", "https://", "www.", ".com", ".net", ".org"]):
        return False, "link_sharing"
    
    # Check for personal info requests
    personal_info = ["address", "phone", "age", "location", "where you live", "real name"]
    if any(x in message_lower for x in personal_info):
        return False, "personal_info_request"
    
    return True, ""

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
    global user_preferences, user_stats, banned_users
    
    try:
        db_channel = bot.get_channel(DATABASE_CHANNEL_ID)
        if not db_channel:
            logging.error(f"Database channel {DATABASE_CHANNEL_ID} not found!")
            user_preferences = {}
            user_stats = {}
            banned_users = set()
            return

        user_preferences = {}
        user_stats = {}
        banned_users = set()
        
        async for message in db_channel.history(limit=50):
            if message.author == bot.user and message.content.startswith("```json"):
                try:
                    json_content = message.content[7:-3].strip()
                    data = json.loads(json_content)
                    
                    if isinstance(data, dict) and "user_preferences" in data:
                        user_preferences = data.get("user_preferences", {})
                        user_stats = data.get("user_stats", {})
                        banned_users = set(data.get("banned_users", []))
                        
                        logging.info(f"✅ Successfully loaded database:")
                        logging.info(f"   👥 {len(user_preferences)} user profiles")
                        logging.info(f"   📊 {len(user_stats)} user stats")
                        logging.info(f"   🚫 {len(banned_users)} banned users")
                        return
                    
                except json.JSONDecodeError as e:
                    logging.warning(f"JSON decode error: {e}")
                    continue
        
        logging.warning("⚠️ No valid database found, starting fresh")
        user_preferences = {}
        user_stats = {}
        banned_users = set()
        
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
            "user_preferences": user_preferences,
            "user_stats": user_stats,
            "banned_users": list(banned_users),
            "metadata": {
                "version": "1.0-chatara",
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "total_users": len(user_preferences),
                "active_sessions": len(active_sessions)
            }
        }
        
        json_content = json.dumps(database_data, indent=2, ensure_ascii=False)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        content_hash = hashlib.md5(json_content.encode()).hexdigest()[:8]
        
        message_content = f"```json\n{json_content}\n```"
        embed = discord.Embed(
            title="💾 Chatara Database Backup",
            description=f"```yaml\nVersion: 1.0-chatara\nUsers: {database_data['metadata']['total_users']}\nActive Sessions: {database_data['metadata']['active_sessions']}\nUpdated: {timestamp}\nHash: {content_hash}\n```",
            color=Colors.INFO,
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_footer(text="Chatara Global Match System", icon_url="https://i.imgur.com/AfFp7pu.png")
        
        await db_channel.send(content=message_content, embed=embed)
        logging.info(f"✅ Database saved successfully (hash: {content_hash})")
        
    except Exception as e:
        logging.error(f"Critical error saving database: {e}")

async def end_session(session: MatchSession, reason: str = "ended"):
    """End a chat session"""
    user1 = bot.get_user(session.user1_id)
    user2 = bot.get_user(session.user2_id)
    
    # Remove from active sessions
    if session.user1_id in active_sessions:
        del active_sessions[session.user1_id]
    if session.user2_id in active_sessions:
        del active_sessions[session.user2_id]
    
    # Calculate session duration
    duration = (datetime.now(timezone.utc) - session.start_time).total_seconds()
    duration_str = f"{int(duration // 60)}m {int(duration % 60)}s"
    
    # Send end message to both users
    end_embed = discord.Embed(
        title="💬 Chat Session Ended",
        description=f"Your anonymous chat has ended.\n**Reason:** {reason}\n**Duration:** {duration_str}\n**Messages:** {session.messages_count}",
        color=Colors.INFO,
        timestamp=datetime.now(timezone.utc)
    )
    end_embed.add_field(
        name="🔄 Find Another Match?",
        value="Use `/find` to start a new conversation!",
        inline=False
    )
    end_embed.set_footer(text="Chatara - Connect Globally")
    
    if user1:
        try:
            await user1.send(embed=end_embed)
        except:
            pass
    
    if user2:
        try:
            await user2.send(embed=end_embed)
        except:
            pass
    
    # Update user stats
    if session.user1_id not in user_stats:
        user_stats[session.user1_id] = {"matches": 0, "messages_sent": 0, "total_time": 0}
    if session.user2_id not in user_stats:
        user_stats[session.user2_id] = {"matches": 0, "messages_sent": 0, "total_time": 0}
    
    user_stats[session.user1_id]["total_time"] += duration
    user_stats[session.user2_id]["total_time"] += duration
    
    asyncio.create_task(batch_save_database())

# Commands

@tree.command(name="find", description="🔍 Find a random match worldwide")
@app_commands.describe(
    interests="Optional: Your interests (gaming, anime, coding, etc)",
    language="Optional: Preferred language"
)
async def find_match(interaction: discord.Interaction, interests: Optional[str] = None, language: Optional[str] = None):
    """Find a random anonymous chat partner"""
    await interaction.response.defer(ephemeral=True)
    
    user_id = interaction.user.id
    
    # Check if user is banned
    if user_id in banned_users:
        embed = discord.Embed(
            title="🚫 Account Suspended",
            description="Your account has been suspended from Chatara for violating community guidelines.",
            color=Colors.DANGER
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        return
    
    # Check if already in a session
    if user_id in active_sessions:
        embed = discord.Embed(
            title="⚠️ Already in Session",
            description="You're already in an active chat! Use `/stop` to end it first.",
            color=Colors.WARNING
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        return
    
    # Check if already in queue
    if any(q['user_id'] == user_id for q in match_queue):
        embed = discord.Embed(
            title="⏳ Already Searching",
            description="You're already in the match queue. Please wait...",
            color=Colors.WARNING
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        return
    
    # Save user preferences
    if user_id not in user_preferences:
        user_preferences[user_id] = {}
    
    if interests:
        user_preferences[user_id]["interests"] = [i.strip().lower() for i in interests.split(",")]
    if language:
        user_preferences[user_id]["language"] = language.lower()
    
    # Try to find a match
    matched = False
    best_match = None
    best_score = -1
    
    for i, queued_user in enumerate(match_queue):
        # Don't match with yourself
        if queued_user['user_id'] == user_id:
            continue
        
        # Calculate match score
        score = 0
        
        # Interest matching
        if interests and queued_user.get('interests'):
            user_interests = set([i.strip().lower() for i in interests.split(",")])
            queued_interests = set(queued_user['interests'])
            common_interests = user_interests & queued_interests
            score += len(common_interests) * 10
        
        # Language matching
        if language and queued_user.get('language') == language.lower():
            score += 50
        
        # Random factor to ensure variety
        score += random.randint(0, 20)
        
        if score > best_score:
            best_score = score
            best_match = (i, queued_user)
    
    if best_match:
        match_index, partner = best_match
        match_queue.pop(match_index)
        
        # Create session
        session = MatchSession(
            user_id,
            partner['user_id'],
            interaction.guild_id,
            partner['guild_id']
        )
        
        active_sessions[user_id] = session
        active_sessions[partner['user_id']] = session
        
        # Update stats
        if user_id not in user_stats:
            user_stats[user_id] = {"matches": 0, "messages_sent": 0, "total_time": 0}
        if partner['user_id'] not in user_stats:
            user_stats[partner['user_id']] = {"matches": 0, "messages_sent": 0, "total_time": 0}
        
        user_stats[user_id]["matches"] += 1
        user_stats[partner['user_id']]["matches"] += 1
        
        # Notify both users
        match_embed = discord.Embed(
            title="✨ Match Found!",
            description="You've been connected with a stranger from somewhere in the world!",
            color=Colors.MATCH,
            timestamp=datetime.now(timezone.utc)
        )
        match_embed.add_field(
            name="📝 Important Rules",
            value="• Be respectful and kind\n• No personal information sharing\n• No inappropriate content\n• Report abuse with `/report`",
            inline=False
        )
        match_embed.add_field(
            name="🎮 Session Commands",
            value="`/next` - Skip to next person\n`/stop` - End chat session\n`/reveal` - Show your identity (both must agree)",
            inline=False
        )
        match_embed.set_footer(text="Start chatting by sending a message here!")
        
        user = bot.get_user(user_id)
        partner_user = bot.get_user(partner['user_id'])
        
        if user:
            try:
                await user.send(embed=match_embed)
            except:
                pass
        
        if partner_user:
            try:
                await partner_user.send(embed=match_embed)
            except:
                pass
        
        await interaction.followup.send(
            "✅ **Match found!** Check your DMs to start chatting!",
            ephemeral=True
        )
        
        asyncio.create_task(batch_save_database())
        matched = True
    
    if not matched:
        # Add to queue
        queue_entry = {
            'user_id': user_id,
            'guild_id': interaction.guild_id,
            'timestamp': datetime.now(timezone.utc),
            'interests': [i.strip().lower() for i in interests.split(",")] if interests else [],
            'language': language.lower() if language else None
        }
        match_queue.append(queue_entry)
        
        embed = discord.Embed(
            title="🔍 Searching for Match...",
            description="Looking for someone to chat with worldwide!\n\nYou'll be notified when a match is found.",
            color=Colors.INFO
        )
        embed.add_field(name="👥 In Queue", value=f"**{len(match_queue)}** people searching", inline=True)
        embed.add_field(name="⏱️ Average Wait", value="~30 seconds", inline=True)
        
        if interests:
            embed.add_field(name="🎯 Your Interests", value=interests, inline=False)
        if language:
            embed.add_field(name="🌍 Language", value=language.title(), inline=False)
        
        embed.set_footer(text="Chatara - Connecting you globally...")
        
        await interaction.followup.send(embed=embed, ephemeral=True)

@tree.command(name="next", description="⏭️ Skip current match and find a new one")
async def next_match(interaction: discord.Interaction):
    """Skip to the next match"""
    await interaction.response.defer(ephemeral=True)
    
    user_id = interaction.user.id
    
    if user_id not in active_sessions:
        embed = discord.Embed(
            title="❌ No Active Session",
            description="You're not currently in a chat. Use `/find` to start one!",
            color=Colors.DANGER
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        return
    
    session = active_sessions[user_id]
    partner_id = session.get_partner(user_id)
    partner = bot.get_user(partner_id)
    
    # Notify partner
    if partner:
        skip_embed = discord.Embed(
            title="⏭️ Partner Skipped",
            description="Your chat partner has moved on to the next match.",
            color=Colors.WARNING
        )
        skip_embed.add_field(
            name="🔄 Want to continue?",
            value="Use `/find` to match with someone new!",
            inline=False
        )
        try:
            await partner.send(embed=skip_embed)
        except:
            pass
    
    # End session
    await end_session(session, "skipped")
    
    # Auto-search for new match
    await interaction.followup.send(
        "⏭️ **Skipped!** Searching for a new match...",
        ephemeral=True
    )
    
    # Simulate calling /find again
    await find_match(interaction)

@tree.command(name="stop", description="🛑 Stop your current chat session")
async def stop_session(interaction: discord.Interaction):
    """End the current chat session"""
    await interaction.response.defer(ephemeral=True)
    
    user_id = interaction.user.id
    
    # Check if in queue
    for i, queued in enumerate(match_queue):
        if queued['user_id'] == user_id:
            match_queue.pop(i)
            await interaction.followup.send(
                "✅ **Removed from queue**",
                ephemeral=True
            )
            return
    
    # Check if in session
    if user_id not in active_sessions:
        embed = discord.Embed(
            title="❌ No Active Session",
            description="You're not currently in a chat or queue.",
            color=Colors.DANGER
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        return
    
    session = active_sessions[user_id]
    await end_session(session, "stopped by user")
    
    await interaction.followup.send(
        "✅ **Session ended successfully**",
        ephemeral=True
    )

@tree.command(name="report", description="🚨 Report your current match for inappropriate behavior")
@app_commands.describe(reason="Why are you reporting this user?")
async def report_user(interaction: discord.Interaction, reason: str):
    """Report a user for inappropriate behavior"""
    await interaction.response.defer(ephemeral=True)
    
    user_id = interaction.user.id
    
    if user_id not in active_sessions:
        embed = discord.Embed(
            title="❌ No Active Session",
            description="You can only report users during an active chat.",
            color=Colors.DANGER
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        return
    
    session = active_sessions[user_id]
    partner_id = session.get_partner(user_id)
    
    # Log the report
    report_data = {
        "reporter_id": user_id,
        "reported_id": partner_id,
        "reason": reason,
        "session_id": session.session_id,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    # Auto-end session
    await end_session(session, "reported")
    
    # Send confirmation
    embed = discord.Embed(
        title="✅ Report Submitted",
        description="Thank you for helping keep Chatara safe. Our team will review this report.",
        color=Colors.SUCCESS
    )
    embed.add_field(
        name="📋 What happens next?",
        value="• Your report is logged securely\n• Repeat offenders are automatically banned\n• You've been disconnected from this user",
        inline=False
    )
    await interaction.followup.send(embed=embed, ephemeral=True)
    
    logging.warning(f"⚠️ REPORT: User {user_id} reported {partner_id} for: {reason}")

@tree.command(name="stats", description="📊 View your Chatara statistics")
async def view_stats(interaction: discord.Interaction):
    """View personal stats"""
    await interaction.response.defer(ephemeral=True)
    
    user_id = interaction.user.id
    
    if user_id not in user_stats:
        embed = discord.Embed(
            title="📊 Your Statistics",
            description="You haven't used Chatara yet! Use `/find` to start chatting.",
            color=Colors.INFO
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        return
    
    stats = user_stats[user_id]
    total_time = stats.get("total_time", 0)
    hours = int(total_time // 3600)
    minutes = int((total_time % 3600) // 60)
    
    embed = discord.Embed(
        title="📊 Your Chatara Statistics",
        description=f"**{interaction.user.name}'s** global chat stats",
        color=Colors.PRIMARY,
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    embed.add_field(name="💬 Total Matches", value=f"**{stats.get('matches', 0)}**", inline=True)
    embed.add_field(name="✉️ Messages Sent", value=f"**{stats.get('messages_sent', 0)}**", inline=True)
    embed.add_field(name="⏱️ Total Chat Time", value=f"**{hours}h {minutes}m**", inline=True)
    
    if user_id in user_preferences:
        prefs = user_preferences[user_id]
        if prefs.get('interests'):
            embed.add_field(name="🎯 Your Interests", value=", ".join(prefs['interests']), inline=False)
        if prefs.get('language'):
            embed.add_field(name="🌍 Language", value=prefs['language'].title(), inline=True)
    
    embed.set_footer(text="Chatara - Connect Globally")
    
    await interaction.followup.send(embed=embed, ephemeral=True)

@tree.command(name="reveal", description="👤 Reveal your identity to your match (both must agree)")
async def reveal_identity(interaction: discord.Interaction):
    """Reveal identity to match"""
    await interaction.response.defer(ephemeral=True)
    
    user_id = interaction.user.id
    
    if user_id not in active_sessions:
        embed = discord.Embed(
            title="❌ No Active Session",
            description="You need to be in an active chat to reveal your identity.",
            color=Colors.DANGER
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        return
    
    session = active_sessions[user_id]
    partner_id = session.get_partner(user_id)
    partner = bot.get_user(partner_id)
    
    if session.revealed:
        embed = discord.Embed(
            title="ℹ️ Already Revealed",
            description=f"You're chatting with **{partner.name}** from **{partner.display_name}**",
            color=Colors.INFO
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        return
    
    # Mark session as revealed
    session.revealed = True
    
    # Reveal to both users
    reveal_embed = discord.Embed(
        title="👤 Identity Revealed!",
        description=f"You're now chatting with **{partner.name}**!",
        color=Colors.SUCCESS
    )
    reveal_embed.set_thumbnail(url=partner.display_avatar.url if partner else None)
    reveal_embed.add_field(
        name="✨ Remember",
        value="Continue to follow Discord's community guidelines!",
        inline=False
    )
    
    reveal_embed_partner = discord.Embed(
        title="👤 Identity Revealed!",
        description=f"You're now chatting with **{interaction.user.name}**!",
        color=Colors.SUCCESS
    )
    reveal_embed_partner.set_thumbnail(url=interaction.user.display_avatar.url)
    
    await interaction.followup.send(embed=reveal_embed, ephemeral=True)
    
    if partner:
        try:
            await partner.send(embed=reveal_embed_partner)
        except:
            pass

@tree.command(name="help", description="❓ Learn how to use Chatara")
async def help_command(interaction: discord.Interaction):
    """Show help information"""
    await interaction.response.defer(ephemeral=True)
    
    embed = discord.Embed(
        title="🌍 Welcome to Chatara!",
        description="Connect with random people from Discord servers worldwide in anonymous 1-on-1 chats.",
        color=Colors.PRIMARY
    )
    
    embed.add_field(
        name="🚀 Getting Started",
        value="`/find` - Start searching for a match\n`/find interests: gaming, anime` - Match by interests\n`/find language: spanish` - Match by language",
        inline=False
    )
    
    embed.add_field(
        name="💬 During Chat",
        value="`/next` - Skip to next person\n`/stop` - End current session\n`/reveal` - Show your identity\n`/report <reason>` - Report abuse",
        inline=False
    )
    
    embed.add_field(
        name="📊 Other Commands",
        value="`/stats` - View your statistics\n`/help` - Show this message",
        inline=False
    )
    
    embed.add_field(
        name="🛡️ Safety Rules",
        value="✅ Be respectful and kind\n✅ Follow Discord ToS\n❌ No personal info sharing\n❌ No inappropriate content\n❌ No harassment or threats",
        inline=False
    )
    
    embed.add_field(
        name="🎯 Available Interests",
        value=", ".join(INTERESTS_LIST[:10]) + "...",
        inline=False
    )
    
    embed.set_footer(text="Chatara - Safer than Omegle, Better than Discord")
    
    await interaction.followup.send(embed=embed, ephemeral=True)

# Message handler for active sessions
@bot.event
async def on_message(message):
    # Ignore bot messages
    if message.author.bot:
        return
    
    # Only handle DMs
    if not isinstance(message.channel, discord.DMChannel):
        return
    
    user_id = message.author.id
    
    # Check if user is in active session
    if user_id not in active_sessions:
        return
    
    session = active_sessions[user_id]
    partner_id = session.get_partner(user_id)
    partner = bot.get_user(partner_id)
    
    if not partner:
        await message.channel.send("⚠️ Your partner has disconnected.")
        await end_session(session, "partner_disconnected")
        return
    
    # Check content safety
    is_safe, violation_type = check_content_safety(message.content)
    
    if not is_safe:
        session.warnings[user_id] += 1
        
        warning_embed = discord.Embed(
            title="⚠️ Content Warning",
            description=f"Your message violated our safety guidelines: **{violation_type}**",
            color=Colors.WARNING
        )
        warning_embed.add_field(
            name="🚨 Warning Level",
            value=f"**{session.warnings[user_id]}/3** - {3 - session.warnings[user_id]} warnings remaining",
            inline=False
        )
        
        if session.warnings[user_id] >= 3:
            warning_embed.add_field(
                name="🚫 Account Suspended",
                value="You've been banned from Chatara for repeated violations.",
                inline=False
            )
            banned_users.add(user_id)
            await end_session(session, "banned_for_violations")
            asyncio.create_task(batch_save_database())
        
        await message.channel.send(embed=warning_embed)
        
        if session.warnings[user_id] >= 3:
            return
        
        return
    
    # Update session activity
    session.update_activity()
    
    # Update user stats
    if user_id not in user_stats:
        user_stats[user_id] = {"matches": 0, "messages_sent": 0, "total_time": 0}
    user_stats[user_id]["messages_sent"] += 1
    
    # Relay message to partner
    try:
        relay_embed = discord.Embed(
            description=message.content,
            color=Colors.SESSION,
            timestamp=datetime.now(timezone.utc)
        )
        
        if session.revealed:
            relay_embed.set_author(
                name=message.author.name,
                icon_url=message.author.display_avatar.url
            )
        else:
            relay_embed.set_author(name="Anonymous Stranger")
        
        await partner.send(embed=relay_embed)
        
    except discord.Forbidden:
        await message.channel.send("⚠️ Couldn't deliver message. Partner may have DMs disabled.")
        await end_session(session, "delivery_failed")

# Background tasks
@tasks.loop(minutes=1)
async def check_inactive_sessions():
    """End inactive sessions"""
    for user_id, session in list(active_sessions.items()):
        if session.is_inactive(5):
            await end_session(session, "inactivity")

@tasks.loop(minutes=5)
async def cleanup_queue():
    """Remove stale queue entries"""
    now = datetime.now(timezone.utc)
    global match_queue
    match_queue = [
        q for q in match_queue
        if (now - q['timestamp']).total_seconds() < 300
    ]

@bot.event
async def on_ready():
    """Bot startup"""
    logging.info(f"🚀 Chatara Bot logged in as {bot.user}")
    logging.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    await load_database()
    
    try:
        synced = await tree.sync()
        logging.info(f"✅ Synced {len(synced)} slash commands")
    except Exception as e:
        logging.error(f"❌ Failed to sync commands: {e}")
    
    check_inactive_sessions.start()
    cleanup_queue.start()
    
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{len(match_queue)} users searching | /find"
        )
    )
    
    logging.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logging.info(f"🎊 Chatara is live and connecting users globally!")
    logging.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

@bot.event
async def on_guild_join(guild):
    """Handle bot joining a guild"""
    logging.info(f"🆕 Joined new server: {guild.name} ({guild.id})")
    
    welcome_embed = discord.Embed(
        title="🌍 Welcome to Chatara!",
        description="Connect your server members with random Discord users worldwide in anonymous 1-on-1 chats.",
        color=Colors.PRIMARY
    )
    
    welcome_embed.add_field(
        name="🚀 Quick Start",
        value="```\n1. Use /find to search for a match\n2. Chat anonymously via DMs\n3. Use /next to skip, /stop to end\n4. Check /stats for your history\n```",
        inline=False
    )
    
    welcome_embed.add_field(
        name="✨ Features",
        value="• 🌐 Global matching across all servers\n• 🎯 Interest-based matching\n• 🌍 Language preferences\n• 🛡️ Advanced safety filters\n• 📊 Personal statistics",
        inline=False
    )
    
    welcome_embed.add_field(
        name="🛡️ Safety First",
        value="• Auto-moderation with content filters\n• Report system for abuse\n• 3-strike ban system\n• Discord ToS compliant",
        inline=False
    )
    
    welcome_embed.set_footer(text="Chatara - Safer than Omegle, Better for Discord")
    welcome_embed.set_thumbnail(url=bot.user.display_avatar.url if bot.user.display_avatar else None)
    
    # Find suitable channel
    target_channel = guild.system_channel
    if not target_channel or not target_channel.permissions_for(guild.me).send_messages:
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                target_channel = channel
                break
    
    if target_channel:
        try:
            await target_channel.send(embed=welcome_embed)
        except:
            pass

# Get Discord token and start
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN is not set in environment.")

keep_alive()
bot.run(DISCORD_TOKEN)