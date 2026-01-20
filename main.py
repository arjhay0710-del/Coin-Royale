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
gemini_model = genai.GenerativeModel('gemini-pro')

# Database channel ID
DATABASE_CHANNEL_ID = 1454384036674797689

# Bot branding colors
class Colors:
    PRIMARY = 0xFF6B35  # JollyMax Orange
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
server_configs = {}  # {guild_id: {support_channel, auto_response}}
support_tickets = {}  # {user_id: {ticket_count, last_ticket}}
pending_database_save = False
last_database_save = datetime.now()

# JollyMax Knowledge Base
JOLLYMAX_KNOWLEDGE = """
JollyMax is a leading digital goods platform for gaming top-ups and digital content.

Common Issues and Solutions:

1. DIAMONDS/CURRENCY NOT RECEIVED:
   - Check your game account ID is correct
   - Wait 5-15 minutes for processing
   - Verify you're logged into the correct account
   - Check if the game server matches your region
   - Contact support with Order ID if not received after 30 minutes

2. PAYMENT ISSUES:
   - Ensure payment method has sufficient funds
   - Try alternative payment methods
   - Clear browser cache and cookies
   - Check if your card supports international transactions
   - Verify billing address matches card details

3. WRONG ACCOUNT TOP-UP:
   - Double-check User ID before confirming
   - JollyMax cannot transfer items between accounts
   - Contact support immediately with Order ID
   - Provide correct User ID for investigation

4. ORDER STATUS:
   - Check "My Orders" in your JollyMax account
   - Orders typically process within 5-15 minutes
   - Look for email confirmation
   - Use Order ID to track status

5. REFUND REQUESTS:
   - Refunds only if items not delivered within 24 hours
   - Items already received cannot be refunded
   - Contact support with Order ID and proof
   - Processing time: 3-7 business days

IMPORTANT REMINDERS:
- Always verify your User ID/Game ID before purchase
- Keep your Order ID for reference
- Check game server region
- Screenshot your purchase confirmation
- Wait at least 30 minutes before contacting support

For urgent issues, contact JollyMax Support:
- Website: https://www.jollymax.com/ph
- Customer Service through website chat
- Provide: Order ID, User ID, Issue Description
"""

async def get_ai_response(user_message: str, user_name: str) -> str:
    """Get AI response from Google Gemini"""
    try:
        prompt = f"""You are JollyBot Helper, a friendly and professional customer support assistant for JollyMax (https://www.jollymax.com/ph), a top-up platform for gaming currency and digital content.

Your role:
- Help users with top-up issues, payment problems, and general inquiries
- Be empathetic, patient, and solution-focused
- Provide clear step-by-step solutions
- Always ask for Order ID when relevant
- Remind users to verify their User ID/Game ID before purchases
- Escalate complex issues to human support when needed

Knowledge Base:
{JOLLYMAX_KNOWLEDGE}

Response Guidelines:
- Keep responses concise but helpful (max 300 words)
- Use bullet points for steps
- Be friendly and use emojis appropriately
- Always end with asking if they need more help
- If you don't know something, direct them to official support

Current user: {user_name}

User's question: {user_message}

Please provide a helpful response:"""

        response = gemini_model.generate_content(prompt)
        return response.text.strip()
    
    except Exception as e:
        logging.error(f"Google Gemini API error: {e}")
        return "I'm having trouble connecting right now. Please try again in a moment, or contact JollyMax support directly at https://www.jollymax.com/ph for immediate assistance."

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
    global server_configs, support_tickets
    
    try:
        db_channel = bot.get_channel(DATABASE_CHANNEL_ID)
        if not db_channel:
            logging.error(f"Database channel {DATABASE_CHANNEL_ID} not found!")
            server_configs = {}
            support_tickets = {}
            return

        server_configs = {}
        support_tickets = {}
        
        async for message in db_channel.history(limit=50):
            if message.author == bot.user and message.content.startswith("```json"):
                try:
                    json_content = message.content[7:-3].strip()
                    data = json.loads(json_content)
                    
                    if isinstance(data, dict):
                        server_configs = data.get("server_configs", {})
                        support_tickets = data.get("support_tickets", {})
                        
                        logging.info(f"✅ Successfully loaded database:")
                        logging.info(f"   🏢 {len(server_configs)} server configurations")
                        logging.info(f"   🎫 {len(support_tickets)} support tickets")
                        return
                    
                except json.JSONDecodeError as e:
                    logging.warning(f"JSON decode error: {e}")
                    continue
        
        logging.warning("⚠️ No valid database found, starting fresh")
        server_configs = {}
        support_tickets = {}
        
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
            "support_tickets": support_tickets,
            "metadata": {
                "version": "1.0-jollybot",
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "total_servers": len(server_configs),
                "total_tickets": len(support_tickets)
            }
        }
        
        json_content = json.dumps(database_data, indent=2, ensure_ascii=False)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        
        message_content = f"```json\n{json_content}\n```"
        embed = discord.Embed(
            title="💾 JollyBot Helper Database Backup",
            description=f"```yaml\nVersion: 1.0-jollybot\nServers: {database_data['metadata']['total_servers']}\nTickets: {database_data['metadata']['total_tickets']}\nUpdated: {timestamp}\n```",
            color=Colors.INFO,
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_footer(text="JollyBot Helper System")
        
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
    return app_commands.check(predicate)DANGER
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True
    return app_commands.check(predicate)

# Commands

@tree.command(name="setup", description="⚙️ Setup JollyBot Helper for your server")
@app_commands.describe(
    support_channel="Channel for support logs (optional)",
    auto_response="Enable automatic AI responses when bot is mentioned"
)
@is_administrator()
async def setup_bot(
    interaction: discord.Interaction,
    support_channel: Optional[discord.TextChannel] = None,
    auto_response: bool = True
):
    """Setup bot configuration"""
    await interaction.response.defer(ephemeral=True)
    
    guild_id = str(interaction.guild_id)
    if guild_id not in server_configs:
        server_configs[guild_id] = {}
    
    if support_channel:
        if not support_channel.permissions_for(interaction.guild.me).send_messages:
            embed = discord.Embed(
                title="❌ Permission Error",
                description=f"I don't have permission to send messages in {support_channel.mention}",
                color=Colors.DANGER
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        server_configs[guild_id]["support_channel"] = support_channel.id
    
    server_configs[guild_id]["auto_response"] = auto_response
    
    asyncio.create_task(batch_save_database())
    
    embed = discord.Embed(
        title="✅ JollyBot Helper Configured",
        description="Bot is ready to assist your members!",
        color=Colors.SUCCESS
    )
    
    if support_channel:
        embed.add_field(name="📋 Support Channel", value=support_channel.mention, inline=False)
    
    embed.add_field(name="🤖 Auto Response", value="Enabled" if auto_response else "Disabled", inline=False)
    embed.add_field(
        name="💡 How to Use",
        value="Users can mention the bot anywhere: `@JollyBot Helper I need help with my top-up`",
        inline=False
    )
    
    await interaction.followup.send(embed=embed, ephemeral=True)
    logging.info(f"⚙️ Bot configured by {interaction.user.name} in {interaction.guild.name}")

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
    
    if "support_channel" in config:
        support_channel = bot.get_channel(config["support_channel"])
        embed.add_field(
            name="📋 Support Channel",
            value=support_channel.mention if support_channel else "Not found",
            inline=False
        )
    
    embed.add_field(
        name="🤖 Auto Response",
        value="Enabled" if config.get("auto_response", True) else "Disabled",
        inline=False
    )
    
    embed.set_footer(text="JollyBot Helper")
    
    await interaction.followup.send(embed=embed, ephemeral=True)

@tree.command(name="ask", description="❓ Ask JollyBot Helper a question")
@app_commands.describe(question="Your question about JollyMax top-ups or issues")
async def ask_jollybot(interaction: discord.Interaction, question: str):
    """Ask the bot a question"""
    await interaction.response.defer()
    
    # Log support ticket
    user_id = str(interaction.user.id)
    if user_id not in support_tickets:
        support_tickets[user_id] = {"ticket_count": 0, "last_ticket": None}
    
    support_tickets[user_id]["ticket_count"] += 1
    support_tickets[user_id]["last_ticket"] = datetime.now(timezone.utc).isoformat()
    
    asyncio.create_task(batch_save_database())
    
    # Get AI response
    ai_response = await get_ai_response(question, interaction.user.display_name)
    
    embed = discord.Embed(
        title="🎮 JollyBot Helper",
        description=ai_response,
        color=Colors.PRIMARY,
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_author(
        name=interaction.user.display_name,
        icon_url=interaction.user.display_avatar.url
    )
    embed.add_field(
        name="❓ Your Question",
        value=f"```{question[:200]}```",
        inline=False
    )
    embed.set_footer(text="JollyMax Support | Need more help? Visit jollymax.com/ph")
    
    await interaction.followup.send(embed=embed)
    
    # Log to support channel
    guild_id = str(interaction.guild_id)
    if guild_id in server_configs and "support_channel" in server_configs[guild_id]:
        support_channel = bot.get_channel(server_configs[guild_id]["support_channel"])
        if support_channel:
            log_embed = discord.Embed(
                title="📝 Support Request",
                color=Colors.INFO,
                timestamp=datetime.now(timezone.utc)
            )
            log_embed.add_field(name="User", value=f"{interaction.user.mention}", inline=True)
            log_embed.add_field(name="Channel", value=f"{interaction.channel.mention}", inline=True)
            log_embed.add_field(name="Question", value=question[:1024], inline=False)
            
            try:
                await support_channel.send(embed=log_embed)
            except:
                pass

@tree.command(name="help", description="❓ View help information")
async def help_command(interaction: discord.Interaction):
    """Show help information"""
    await interaction.response.defer(ephemeral=True)
    
    embed = discord.Embed(
        title="🎮 JollyBot Helper",
        description="Your AI-powered assistant for JollyMax top-up support!\n\n**JollyMax:** https://www.jollymax.com/ph",
        color=Colors.PRIMARY
    )
    embed.set_thumbnail(url="https://i.imgur.com/jollymax-logo.png")
    
    embed.add_field(
        name="💬 How to Get Help",
        value=(
            "**Method 1:** Mention me in any channel\n"
            "`@JollyBot Helper I need help with my diamond top-up`\n\n"
            "**Method 2:** Use the ask command\n"
            "`/ask question:My diamonds didn't arrive`"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🆘 Common Issues I Can Help With",
        value=(
            "• Diamonds/currency not received\n"
            "• Payment problems\n"
            "• Wrong account top-up\n"
            "• Order status inquiries\n"
            "• Refund requests\n"
            "• General top-up questions"
        ),
        inline=False
    )
    
    if interaction.user.guild_permissions.administrator:
        embed.add_field(
            name="🔧 Admin Commands",
            value=(
                "`/setup` - Configure the bot\n"
                "`/config` - View current settings\n"
                "`/stats` - View support statistics"
            ),
            inline=False
        )
    
    embed.add_field(
        name="📋 Important Tips",
        value=(
            "• Always have your **Order ID** ready\n"
            "• Verify your **User ID/Game ID** before purchase\n"
            "• Wait 15-30 minutes before reporting issues\n"
            "• Check your game server region"
        ),
        inline=False
    )
    
    embed.set_footer(text="JollyBot Helper - Powered by AI")
    
    await interaction.followup.send(embed=embed, ephemeral=True)

@tree.command(name="stats", description="📊 View support statistics")
@is_administrator()
async def view_stats(interaction: discord.Interaction):
    """View support statistics"""
    await interaction.response.defer(ephemeral=True)
    
    total_tickets = sum(data["ticket_count"] for data in support_tickets.values())
    total_users = len(support_tickets)
    
    embed = discord.Embed(
        title="📊 Support Statistics",
        description=f"**{interaction.guild.name}**",
        color=Colors.INFO,
        timestamp=datetime.now(timezone.utc)
    )
    
    embed.add_field(name="🎫 Total Requests", value=str(total_tickets), inline=True)
    embed.add_field(name="👥 Unique Users", value=str(total_users), inline=True)
    embed.add_field(name="🏢 Servers", value=str(len(server_configs)), inline=True)
    
    # Top 5 users
    if support_tickets:
        sorted_users = sorted(
            support_tickets.items(),
            key=lambda x: x[1]["ticket_count"],
            reverse=True
        )[:5]
        
        top_users = "\n".join([
            f"<@{user_id}>: {data['ticket_count']} requests"
            for user_id, data in sorted_users
        ])
        
        embed.add_field(name="🔥 Top Users", value=top_users or "No data", inline=False)
    
    embed.set_footer(text="JollyBot Helper Statistics")
    
    await interaction.followup.send(embed=embed, ephemeral=True)

# Events

@bot.event
async def on_message(message):
    """Handle messages mentioning the bot"""
    if message.author.bot:
        return
    
    # Check if bot is mentioned
    if bot.user.mentioned_in(message):
        # Check if auto-response is enabled
        guild_id = str(message.guild.id) if message.guild else None
        
        if guild_id and guild_id in server_configs:
            if not server_configs[guild_id].get("auto_response", True):
                return
        
        # Extract message content without mention
        question = message.content.replace(f'<@{bot.user.id}>', '').replace(f'<@!{bot.user.id}>', '').strip()
        
        if not question:
            embed = discord.Embed(
                title="👋 Hello! How can I help?",
                description="Please mention me with your question!\n\n**Example:**\n`@JollyBot Helper My diamonds didn't arrive after top-up`",
                color=Colors.INFO
            )
            await message.reply(embed=embed)
            return
        
        # Show typing indicator
        async with message.channel.typing():
            # Log support ticket
            user_id = str(message.author.id)
            if user_id not in support_tickets:
                support_tickets[user_id] = {"ticket_count": 0, "last_ticket": None}
            
            support_tickets[user_id]["ticket_count"] += 1
            support_tickets[user_id]["last_ticket"] = datetime.now(timezone.utc).isoformat()
            
            asyncio.create_task(batch_save_database())
            
            # Get AI response
            ai_response = await get_ai_response(question, message.author.display_name)
            
            embed = discord.Embed(
                title="🎮 JollyBot Helper",
                description=ai_response,
                color=Colors.PRIMARY,
                timestamp=datetime.now(timezone.utc)
            )
            embed.set_author(
                name=message.author.display_name,
                icon_url=message.author.display_avatar.url
            )
            embed.set_footer(text="Need more help? Use /ask or visit jollymax.com/ph")
            
            await message.reply(embed=embed)
            
            # Log to support channel
            if guild_id and guild_id in server_configs and "support_channel" in server_configs[guild_id]:
                support_channel = bot.get_channel(server_configs[guild_id]["support_channel"])
                if support_channel and support_channel.id != message.channel.id:
                    log_embed = discord.Embed(
                        title="📝 Support Request (Mention)",
                        color=Colors.INFO,
                        timestamp=datetime.now(timezone.utc)
                    )
                    log_embed.add_field(name="User", value=f"{message.author.mention}", inline=True)
                    log_embed.add_field(name="Channel", value=f"{message.channel.mention}", inline=True)
                    log_embed.add_field(name="Question", value=question[:1024], inline=False)
                    log_embed.add_field(
                        name="Jump to Message",
                        value=f"[Click here]({message.jump_url})",
                        inline=False
                    )
                    
                    try:
                        await support_channel.send(embed=log_embed)
                    except:
                        pass
    
    await bot.process_commands(message)

@bot.event
async def on_ready():
    """Bot startup"""
    logging.info(f"🚀 JollyBot Helper logged in as {bot.user}")
    logging.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    await load_database()
    
    try:
        synced = await tree.sync()
        logging.info(f"✅ Synced {len(synced)} slash commands")
    except Exception as e:
        logging.error(f"❌ Failed to sync commands: {e}")
    
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="JollyMax Support | @mention me!"
        )
    )
    
    logging.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logging.info(f"🎯 JollyBot Helper is online!")
    logging.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

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