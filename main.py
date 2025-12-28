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

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# Global data structures
server_configs = {}  # {guild_id: {announcement_channel, welcome_channel, welcome_message}}
pending_database_save = False
last_database_save = datetime.now()

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
    global server_configs
    
    try:
        db_channel = bot.get_channel(DATABASE_CHANNEL_ID)
        if not db_channel:
            logging.error(f"Database channel {DATABASE_CHANNEL_ID} not found!")
            server_configs = {}
            return

        server_configs = {}
        
        async for message in db_channel.history(limit=50):
            if message.author == bot.user and message.content.startswith("```json"):
                try:
                    json_content = message.content[7:-3].strip()
                    data = json.loads(json_content)
                    
                    if isinstance(data, dict) and "server_configs" in data:
                        server_configs = data.get("server_configs", {})
                        
                        logging.info(f"✅ Successfully loaded database:")
                        logging.info(f"   🏢 {len(server_configs)} server configurations")
                        return
                    
                except json.JSONDecodeError as e:
                    logging.warning(f"JSON decode error: {e}")
                    continue
        
        logging.warning("⚠️ No valid database found, starting fresh")
        server_configs = {}
        
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
            "metadata": {
                "version": "1.0-onestate",
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "total_servers": len(server_configs)
            }
        }
        
        json_content = json.dumps(database_data, indent=2, ensure_ascii=False)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        
        message_content = f"```json\n{json_content}\n```"
        embed = discord.Embed(
            title="💾 One State PH Database Backup",
            description=f"```yaml\nVersion: 1.0-onestate\nServers: {database_data['metadata']['total_servers']}\nUpdated: {timestamp}\n```",
            color=Colors.INFO,
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_footer(text="One State PH Bot System")
        
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

@tree.command(name="settext", description="📝 Send a custom message to any channel")
@app_commands.describe(
    channel="The channel to send the message to",
    text="The message text",
    image="Optional: Image URL to include"
)
@is_administrator()
async def set_text(
    interaction: discord.Interaction, 
    channel: discord.TextChannel, 
    text: str, 
    image: Optional[str] = None
):
    """Send a custom message to specified channel"""
    await interaction.response.defer(ephemeral=True)
    
    # Check if bot has permission to send in target channel
    if not channel.permissions_for(interaction.guild.me).send_messages:
        embed = discord.Embed(
            title="❌ Permission Error",
            description=f"I don't have permission to send messages in {channel.mention}",
            color=Colors.DANGER
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        return
    
    # Create message embed
    message_embed = discord.Embed(
        description=text,
        color=Colors.PRIMARY,
        timestamp=datetime.now(timezone.utc)
    )
    
    if image:
        try:
            message_embed.set_image(url=image)
        except:
            pass
    
    # Send message
    try:
        await channel.send(embed=message_embed)
        
        # Confirmation
        confirm_embed = discord.Embed(
            title="✅ Message Sent",
            description=f"Successfully sent message to {channel.mention}",
            color=Colors.SUCCESS
        )
        await interaction.followup.send(embed=confirm_embed, ephemeral=True)
        
        logging.info(f"📝 Message sent by {interaction.user.name} in {interaction.guild.name} to #{channel.name}")
        
    except Exception as e:
        error_embed = discord.Embed(
            title="❌ Error",
            description=f"Failed to send message: {str(e)}",
            color=Colors.DANGER
        )
        await interaction.followup.send(embed=error_embed, ephemeral=True)

@tree.command(name="setupwelcome", description="👋 Setup welcome messages for new members")
@app_commands.describe(
    channel="The channel to send welcome messages to",
    text="Welcome message text (use [@username] as placeholder)"
)
@is_administrator()
async def setup_welcome(
    interaction: discord.Interaction, 
    channel: discord.TextChannel, 
    text: str
):
    """Setup welcome message configuration"""
    await interaction.response.defer(ephemeral=True)
    
    # Check if bot has permission to send in target channel
    if not channel.permissions_for(interaction.guild.me).send_messages:
        embed = discord.Embed(
            title="❌ Permission Error",
            description=f"I don't have permission to send messages in {channel.mention}",
            color=Colors.DANGER
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        return
    
    # Validate text contains placeholder
    if "[@username]" not in text:
        embed = discord.Embed(
            title="⚠️ Missing Placeholder",
            description="Welcome message must contain `[@username]` placeholder.\n\n**Example:**\n`Welcome [@username] to our server!`",
            color=Colors.WARNING
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        return
    
    # Save configuration
    guild_id = str(interaction.guild_id)
    if guild_id not in server_configs:
        server_configs[guild_id] = {}
    
    server_configs[guild_id]["welcome_channel"] = channel.id
    server_configs[guild_id]["welcome_message"] = text
    
    asyncio.create_task(batch_save_database())
    
    # Preview embed
    preview_text = text.replace("[@username]", interaction.user.mention)
    preview_embed = discord.Embed(
        title="👋 Welcome Message Preview",
        description=preview_text,
        color=Colors.SUCCESS,
        timestamp=datetime.now(timezone.utc)
    )
    preview_embed.set_thumbnail(url=interaction.user.display_avatar.url)
    preview_embed.set_footer(text=f"{interaction.guild.name}")
    
    # Confirmation
    confirm_embed = discord.Embed(
        title="✅ Welcome System Configured",
        description=f"**Channel:** {channel.mention}\n**Message:** {text}",
        color=Colors.SUCCESS
    )
    confirm_embed.add_field(
        name="📝 Preview",
        value="See below for how it will look!",
        inline=False
    )
    
    await interaction.followup.send(embed=confirm_embed, ephemeral=True)
    await interaction.followup.send(embed=preview_embed, ephemeral=True)
    
    logging.info(f"👋 Welcome system configured by {interaction.user.name} in {interaction.guild.name}")

@tree.command(name="editwelcome", description="✏️ Edit the welcome message configuration")
@app_commands.describe(
    channel="Optional: New channel for welcome messages",
    text="Optional: New welcome message text (use [@username] as placeholder)"
)
@is_administrator()
async def edit_welcome(
    interaction: discord.Interaction, 
    channel: Optional[discord.TextChannel] = None, 
    text: Optional[str] = None
):
    """Edit welcome message configuration"""
    await interaction.response.defer(ephemeral=True)
    
    guild_id = str(interaction.guild_id)
    
    # Check if welcome system is configured
    if guild_id not in server_configs or "welcome_channel" not in server_configs[guild_id]:
        embed = discord.Embed(
            title="⚠️ Not Configured",
            description="Welcome system is not set up yet. Use `/setupwelcome` first!",
            color=Colors.WARNING
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        return
    
    # If nothing to update
    if not channel and not text:
        embed = discord.Embed(
            title="⚠️ No Changes",
            description="Please provide at least one parameter to update:\n• `channel` - New welcome channel\n• `text` - New welcome message",
            color=Colors.WARNING
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        return
    
    changes = []
    
    # Update channel
    if channel:
        if not channel.permissions_for(interaction.guild.me).send_messages:
            embed = discord.Embed(
                title="❌ Permission Error",
                description=f"I don't have permission to send messages in {channel.mention}",
                color=Colors.DANGER
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        server_configs[guild_id]["welcome_channel"] = channel.id
        changes.append(f"**Channel:** {channel.mention}")
    
    # Update text
    if text:
        if "[@username]" not in text:
            embed = discord.Embed(
                title="⚠️ Missing Placeholder",
                description="Welcome message must contain `[@username]` placeholder.\n\n**Example:**\n`Welcome [@username] to our server!`",
                color=Colors.WARNING
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        server_configs[guild_id]["welcome_message"] = text
        changes.append(f"**Message:** {text}")
    
    asyncio.create_task(batch_save_database())
    
    # Preview embed
    preview_text = server_configs[guild_id]["welcome_message"].replace("[@username]", interaction.user.mention)
    preview_embed = discord.Embed(
        title="👋 Updated Welcome Message Preview",
        description=preview_text,
        color=Colors.SUCCESS,
        timestamp=datetime.now(timezone.utc)
    )
    preview_embed.set_thumbnail(url=interaction.user.display_avatar.url)
    preview_embed.set_footer(text=f"{interaction.guild.name}")
    
    # Confirmation
    confirm_embed = discord.Embed(
        title="✅ Welcome System Updated",
        description="**Changes made:**\n" + "\n".join(changes),
        color=Colors.SUCCESS
    )
    confirm_embed.add_field(
        name="📝 Preview",
        value="See below for how it will look!",
        inline=False
    )
    
    await interaction.followup.send(embed=confirm_embed, ephemeral=True)
    await interaction.followup.send(embed=preview_embed, ephemeral=True)
    
    logging.info(f"✏️ Welcome system updated by {interaction.user.name} in {interaction.guild.name}")

@tree.command(name="config", description="⚙️ View current bot configuration")
@is_administrator()
async def view_config(interaction: discord.Interaction):
    """View current server configuration"""
    await interaction.response.defer(ephemeral=True)
    
    guild_id = str(interaction.guild_id)
    
    if guild_id not in server_configs or not server_configs[guild_id]:
        embed = discord.Embed(
            title="⚙️ Server Configuration",
            description="No configuration set yet. Use `/setupwelcome` to get started!",
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
    
    # Welcome system
    if "welcome_channel" in config:
        welcome_channel = bot.get_channel(config["welcome_channel"])
        embed.add_field(
            name="👋 Welcome System",
            value=f"**Channel:** {welcome_channel.mention if welcome_channel else 'Not found'}\n**Message:** {config.get('welcome_message', 'Not set')}",
            inline=False
        )
    else:
        embed.add_field(
            name="👋 Welcome System",
            value="Not configured",
            inline=False
        )
    
    embed.set_footer(text="One State PH")
    
    await interaction.followup.send(embed=embed, ephemeral=True)

@tree.command(name="help", description="❓ View all available commands")
async def help_command(interaction: discord.Interaction):
    """Show help information"""
    await interaction.response.defer(ephemeral=True)
    
    embed = discord.Embed(
        title="🇵🇭 One State PH Bot",
        description="Server management bot for announcements and welcome messages.",
        color=Colors.PRIMARY
    )
    embed.set_thumbnail(url="https://i.imgur.com/z536L8R.png")
    
    if interaction.user.guild_permissions.administrator:
        embed.add_field(
            name="🔧 Admin Commands",
            value=(
                "`/settext` - Send custom messages to any channel\n"
                "`/setupwelcome` - Configure welcome messages\n"
                "`/editwelcome` - Edit welcome message settings\n"
                "`/config` - View current configuration\n"
                "`/help` - Show this message"
            ),
            inline=False
        )
        
        embed.add_field(
            name="📝 Set Text Usage",
            value="```/settext channel:#general text:Hello everyone! image:https://example.com/image.png```",
            inline=False
        )
        
        embed.add_field(
            name="👋 Welcome Setup Usage",
            value="```/setupwelcome channel:#welcome text:Welcome [@username] to our community!```\n**Note:** Use `[@username]` as placeholder",
            inline=False
        )
        
        embed.add_field(
            name="✏️ Edit Welcome Usage",
            value="```/editwelcome channel:#new-welcome text:New message [@username]!```\n**Note:** You can update channel, text, or both",
            inline=False
        )
    else:
        embed.add_field(
            name="ℹ️ Information",
            value="Only administrators can use bot commands.\nContact a server admin for assistance.",
            inline=False
        )
    
    embed.set_footer(text="One State PH - Server Management")
    
    await interaction.followup.send(embed=embed, ephemeral=True)

# Events

@bot.event
async def on_member_join(member: discord.Member):
    """Handle new member joins"""
    guild_id = str(member.guild.id)
    
    if guild_id not in server_configs:
        return
    
    config = server_configs[guild_id]
    
    if "welcome_channel" not in config or "welcome_message" not in config:
        return
    
    welcome_channel = bot.get_channel(config["welcome_channel"])
    
    if not welcome_channel:
        return
    
    # Check permissions
    if not welcome_channel.permissions_for(member.guild.me).send_messages:
        return
    
    # Create welcome message
    welcome_text = config["welcome_message"].replace("[@username]", member.mention)
    
    welcome_embed = discord.Embed(
        title="👋 Welcome!",
        description=welcome_text,
        color=Colors.SUCCESS,
        timestamp=datetime.now(timezone.utc)
    )
    welcome_embed.set_thumbnail(url=member.display_avatar.url)
    welcome_embed.set_footer(text=f"{member.guild.name}")
    
    try:
        await welcome_channel.send(embed=welcome_embed)
        logging.info(f"👋 Welcome message sent for {member.name} in {member.guild.name}")
    except Exception as e:
        logging.error(f"Failed to send welcome message: {e}")

@bot.event
async def on_ready():
    """Bot startup"""
    logging.info(f"🚀 One State PH Bot logged in as {bot.user}")
    logging.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    await load_database()
    
    try:
        synced = await tree.sync()
        logging.info(f"✅ Synced {len(synced)} slash commands")
    except Exception as e:
        logging.error(f"❌ Failed to sync commands: {e}")
    
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{len(bot.guilds)} servers | /help"
        )
    )
    
    logging.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logging.info(f"🎯 One State PH is online!")
    logging.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

@bot.event
async def on_guild_join(guild):
    """Handle bot joining a guild"""
    logging.info(f"🆕 Joined new server: {guild.name} ({guild.id})")
    
    welcome_embed = discord.Embed(
        title="🇵🇭 One State PH Bot",
        description="Thank you for adding One State PH to your server!",
        color=Colors.PRIMARY
    )
    welcome_embed.set_thumbnail(url="https://i.imgur.com/z536L8R.png")
    
    welcome_embed.add_field(
        name="🚀 Quick Start",
        value="Administrators can use:\n• `/setupwelcome` - Configure welcome messages\n• `/editwelcome` - Edit welcome settings\n• `/settext` - Send custom messages\n• `/config` - View settings\n• `/help` - View all commands",
        inline=False
    )
    
    welcome_embed.add_field(
        name="🔐 Permissions",
        value="Only users with **Administrator** permission can use bot commands.",
        inline=False
    )
    
    welcome_embed.set_footer(text="One State PH - Server Management")
    
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