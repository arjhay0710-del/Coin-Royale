import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import os
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict
import logging
import asyncio
import random
import hashlib
from keep_alive import keep_alive

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Database channel ID
DATABASE_CHANNEL_ID = 1405783978589290562

# Bot branding colors
class Colors:
    PRIMARY = 0xFFD700  # Gold
    SUCCESS = 0x57F287  # Green
    WARNING = 0xFEE75C  # Yellow
    DANGER = 0xED4245   # Red
    INFO = 0x5865F2     # Blue
    CASINO = 0xFF1493   # Deep Pink

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# Global data structures - server-isolated
user_balances = {}  # {server_id: {user_id: balance}}
user_daily = {}  # {server_id: {user_id: last_daily_timestamp}}
game_stats = {}  # {server_id: {user_id: {wins, losses, total_bet, total_won}}}
pending_database_save = False
last_database_save = datetime.now()

def get_balance(server_id: int, user_id: int) -> int:
    """Get user balance"""
    if server_id not in user_balances:
        user_balances[server_id] = {}
    if user_id not in user_balances[server_id]:
        user_balances[server_id][user_id] = 1000  # Starting balance
    return user_balances[server_id][user_id]

def set_balance(server_id: int, user_id: int, amount: int):
    """Set user balance"""
    if server_id not in user_balances:
        user_balances[server_id] = {}
    user_balances[server_id][user_id] = max(0, amount)

def add_balance(server_id: int, user_id: int, amount: int):
    """Add to user balance"""
    current = get_balance(server_id, user_id)
    set_balance(server_id, user_id, current + amount)

def subtract_balance(server_id: int, user_id: int, amount: int) -> bool:
    """Subtract from user balance, return False if insufficient funds"""
    current = get_balance(server_id, user_id)
    if current < amount:
        return False
    set_balance(server_id, user_id, current - amount)
    return True

def update_stats(server_id: int, user_id: int, won: bool, bet_amount: int, win_amount: int = 0):
    """Update game statistics"""
    if server_id not in game_stats:
        game_stats[server_id] = {}
    if user_id not in game_stats[server_id]:
        game_stats[server_id][user_id] = {
            "wins": 0,
            "losses": 0,
            "total_bet": 0,
            "total_won": 0
        }
    
    stats = game_stats[server_id][user_id]
    if won:
        stats["wins"] += 1
        stats["total_won"] += win_amount
    else:
        stats["losses"] += 1
    stats["total_bet"] += bet_amount

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
    global user_balances, user_daily, game_stats
    
    try:
        db_channel = bot.get_channel(DATABASE_CHANNEL_ID)
        if not db_channel:
            logging.error(f"Database channel {DATABASE_CHANNEL_ID} not found!")
            user_balances = {}
            user_daily = {}
            game_stats = {}
            return

        user_balances = {}
        user_daily = {}
        game_stats = {}
        
        messages_to_check = []
        
        async for message in db_channel.history(limit=50):
            if message.author == bot.user:
                messages_to_check.append(message)
        
        messages_to_check.sort(key=lambda m: m.created_at, reverse=True)
        
        for message in messages_to_check:
            if not message.content:
                continue
                
            if message.content.startswith("```json") and message.content.endswith("```"):
                try:
                    json_content = message.content[7:-3].strip()
                    if not json_content:
                        continue
                        
                    data = json.loads(json_content)
                    
                    if isinstance(data, dict) and "user_balances" in data:
                        balances_data = data.get("user_balances", {})
                        if isinstance(balances_data, dict):
                            for server_id, users in balances_data.items():
                                try:
                                    server_id_int = int(server_id)
                                    user_balances[server_id_int] = {}
                                    
                                    if isinstance(users, dict):
                                        for user_id, balance in users.items():
                                            try:
                                                user_id_int = int(user_id)
                                                user_balances[server_id_int][user_id_int] = int(balance)
                                            except (ValueError, TypeError):
                                                continue
                                except (ValueError, TypeError):
                                    continue
                        
                        daily_data = data.get("user_daily", {})
                        if isinstance(daily_data, dict):
                            for server_id, users in daily_data.items():
                                try:
                                    server_id_int = int(server_id)
                                    user_daily[server_id_int] = {}
                                    
                                    if isinstance(users, dict):
                                        for user_id, timestamp in users.items():
                                            try:
                                                user_id_int = int(user_id)
                                                user_daily[server_id_int][user_id_int] = timestamp
                                            except (ValueError, TypeError):
                                                continue
                                except (ValueError, TypeError):
                                    continue
                        
                        stats_data = data.get("game_stats", {})
                        if isinstance(stats_data, dict):
                            for server_id, users in stats_data.items():
                                try:
                                    server_id_int = int(server_id)
                                    game_stats[server_id_int] = {}
                                    
                                    if isinstance(users, dict):
                                        for user_id, stats in users.items():
                                            try:
                                                user_id_int = int(user_id)
                                                if isinstance(stats, dict):
                                                    game_stats[server_id_int][user_id_int] = stats
                                            except (ValueError, TypeError):
                                                continue
                                except (ValueError, TypeError):
                                    continue
                        
                        logging.info(f"✅ Successfully loaded database:")
                        logging.info(f"   💰 {len(user_balances)} servers with balances")
                        logging.info(f"   📊 {len(game_stats)} servers with stats")
                        return
                    
                except json.JSONDecodeError as e:
                    logging.warning(f"JSON decode error in message {message.id}: {e}")
                    continue
                except Exception as e:
                    logging.warning(f"Error processing message {message.id}: {e}")
                    continue
        
        logging.warning("⚠️ No valid database found, starting with empty database")
        user_balances = {}
        user_daily = {}
        game_stats = {}
        
    except Exception as e:
        logging.error(f"Critical error loading database: {e}")
        user_balances = {}
        user_daily = {}
        game_stats = {}

async def save_database():
    """Save all data to the database channel"""
    try:
        db_channel = bot.get_channel(DATABASE_CHANNEL_ID)
        if not db_channel:
            logging.error(f"Database channel {DATABASE_CHANNEL_ID} not found!")
            return

        database_data = {
            "user_balances": user_balances,
            "user_daily": user_daily,
            "game_stats": game_stats,
            "metadata": {
                "version": "1.0-coin-royale",
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "total_servers": len(user_balances),
                "save_timestamp": datetime.now(timezone.utc).timestamp()
            }
        }
        
        json_content = json.dumps(database_data, indent=2, ensure_ascii=False)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        content_hash = hashlib.md5(json_content.encode()).hexdigest()[:8]
        
        message_content = f"```json\n{json_content}\n```"
        embed = discord.Embed(
            title="💾 Coin Royale Database Backup",
            description=f"```yaml\nVersion: 1.0-coin-royale\nServers: {database_data['metadata']['total_servers']}\nUpdated: {timestamp}\nHash: {content_hash}\n```",
            color=Colors.PRIMARY,
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_footer(text="Coin Royale Casino System", icon_url="https://i.imgur.com/AfFp7pu.png")
        
        await db_channel.send(content=message_content, embed=embed)
        logging.info(f"✅ Database saved successfully (hash: {content_hash})")
        
    except discord.HTTPException as e:
        logging.error(f"Discord HTTP error saving database: {e}")
    except Exception as e:
        logging.error(f"Critical error saving database: {e}")

# Economy Commands

@tree.command(name="balance", description="💰 Check your coin balance")
async def balance(interaction: discord.Interaction, user: Optional[discord.Member] = None):
    """Check coin balance"""
    target_user = user or interaction.user
    
    balance = get_balance(interaction.guild.id, target_user.id)
    
    embed = discord.Embed(
        title="💰 Coin Balance",
        description=f"**{target_user.display_name}** has:\n\n🪙 **{balance:,} coins**",
        color=Colors.PRIMARY,
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_thumbnail(url=target_user.display_avatar.url)
    embed.set_footer(text="Coin Royale Casino", icon_url="https://i.imgur.com/AfFp7pu.png")
    
    await interaction.response.send_message(embed=embed)

@tree.command(name="daily", description="🎁 Claim daily free coins")
async def daily(interaction: discord.Interaction):
    """Claim daily coins"""
    await interaction.response.defer()
    
    server_id = interaction.guild.id
    user_id = interaction.user.id
    
    if server_id not in user_daily:
        user_daily[server_id] = {}
    
    now = datetime.now(timezone.utc)
    
    if user_id in user_daily[server_id]:
        last_claim = datetime.fromisoformat(user_daily[server_id][user_id])
        time_diff = now - last_claim
        
        if time_diff < timedelta(hours=24):
            next_claim = last_claim + timedelta(hours=24)
            remaining = next_claim - now
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)
            
            embed = discord.Embed(
                title="⏰ Daily Already Claimed",
                description=f"You've already claimed your daily reward!\n\n**Next claim:** {hours}h {minutes}m",
                color=Colors.WARNING,
                timestamp=datetime.now(timezone.utc)
            )
            embed.set_footer(text="Coin Royale Casino")
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
    
    daily_amount = random.randint(500, 1000)
    add_balance(server_id, user_id, daily_amount)
    user_daily[server_id][user_id] = now.isoformat()
    
    new_balance = get_balance(server_id, user_id)
    
    embed = discord.Embed(
        title="🎁 Daily Reward Claimed!",
        description=f"You received **{daily_amount:,} coins**!\n\n💰 New balance: **{new_balance:,} coins**",
        color=Colors.SUCCESS,
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    embed.set_footer(text="Come back in 24 hours! • Coin Royale Casino")
    
    await interaction.followup.send(embed=embed)
    asyncio.create_task(batch_save_database())

@tree.command(name="transfer", description="💸 Transfer coins to another user")
@app_commands.describe(
    user="The user to transfer coins to",
    amount="Amount of coins to transfer"
)
async def transfer(interaction: discord.Interaction, user: discord.Member, amount: int):
    """Transfer coins to another user"""
    await interaction.response.defer(ephemeral=True)
    
    if user.bot:
        await interaction.followup.send("❌ Cannot transfer coins to bots!", ephemeral=True)
        return
    
    if user.id == interaction.user.id:
        await interaction.followup.send("❌ Cannot transfer coins to yourself!", ephemeral=True)
        return
    
    if amount <= 0:
        await interaction.followup.send("❌ Amount must be positive!", ephemeral=True)
        return
    
    server_id = interaction.guild.id
    sender_id = interaction.user.id
    
    if not subtract_balance(server_id, sender_id, amount):
        balance = get_balance(server_id, sender_id)
        await interaction.followup.send(f"❌ Insufficient funds! You have {balance:,} coins.", ephemeral=True)
        return
    
    add_balance(server_id, user.id, amount)
    
    sender_balance = get_balance(server_id, sender_id)
    receiver_balance = get_balance(server_id, user.id)
    
    embed = discord.Embed(
        title="✅ Transfer Successful",
        description=f"**{interaction.user.display_name}** sent **{amount:,} coins** to **{user.display_name}**",
        color=Colors.SUCCESS,
        timestamp=datetime.now(timezone.utc)
    )
    embed.add_field(name=f"{interaction.user.display_name}", value=f"💰 {sender_balance:,} coins", inline=True)
    embed.add_field(name=f"{user.display_name}", value=f"💰 {receiver_balance:,} coins", inline=True)
    embed.set_footer(text="Coin Royale Casino")
    
    await interaction.followup.send(embed=embed, ephemeral=True)
    asyncio.create_task(batch_save_database())

# Betting/Game Commands

@tree.command(name="bet", description="🎲 Coin flip - win or lose")
@app_commands.describe(amount="Amount to bet")
async def bet(interaction: discord.Interaction, amount: int):
    """Simple coin flip bet"""
    await interaction.response.defer()
    
    if amount <= 0:
        await interaction.followup.send("❌ Bet amount must be positive!", ephemeral=True)
        return
    
    server_id = interaction.guild.id
    user_id = interaction.user.id
    
    if not subtract_balance(server_id, user_id, amount):
        balance = get_balance(server_id, user_id)
        await interaction.followup.send(f"❌ Insufficient funds! You have {balance:,} coins.", ephemeral=True)
        return
    
    won = random.choice([True, False])
    
    if won:
        winnings = amount * 2
        add_balance(server_id, user_id, winnings)
        update_stats(server_id, user_id, True, amount, winnings)
        
        new_balance = get_balance(server_id, user_id)
        
        embed = discord.Embed(
            title="🎉 YOU WIN!",
            description=f"🪙 You won **{winnings:,} coins**!\n\n💰 New balance: **{new_balance:,} coins**",
            color=Colors.SUCCESS,
            timestamp=datetime.now(timezone.utc)
        )
    else:
        update_stats(server_id, user_id, False, amount)
        new_balance = get_balance(server_id, user_id)
        
        embed = discord.Embed(
            title="💔 YOU LOSE!",
            description=f"You lost **{amount:,} coins**\n\n💰 Remaining: **{new_balance:,} coins**",
            color=Colors.DANGER,
            timestamp=datetime.now(timezone.utc)
        )
    
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    embed.set_footer(text="Coin Royale Casino")
    
    await interaction.followup.send(embed=embed)
    asyncio.create_task(batch_save_database())

@tree.command(name="slots", description="🎰 Slot machine")
@app_commands.describe(amount="Amount to bet")
async def slots(interaction: discord.Interaction, amount: int):
    """Slot machine game"""
    await interaction.response.defer()
    
    if amount <= 0:
        await interaction.followup.send("❌ Bet amount must be positive!", ephemeral=True)
        return
    
    server_id = interaction.guild.id
    user_id = interaction.user.id
    
    if not subtract_balance(server_id, user_id, amount):
        balance = get_balance(server_id, user_id)
        await interaction.followup.send(f"❌ Insufficient funds! You have {balance:,} coins.", ephemeral=True)
        return
    
    symbols = ["🍒", "🍋", "🍊", "🍇", "💎", "7️⃣"]
    weights = [30, 25, 20, 15, 7, 3]
    
    reel1 = random.choices(symbols, weights=weights)[0]
    reel2 = random.choices(symbols, weights=weights)[0]
    reel3 = random.choices(symbols, weights=weights)[0]
    
    result = f"{reel1} {reel2} {reel3}"
    
    if reel1 == reel2 == reel3:
        if reel1 == "7️⃣":
            multiplier = 50
        elif reel1 == "💎":
            multiplier = 20
        elif reel1 == "🍇":
            multiplier = 10
        elif reel1 == "🍊":
            multiplier = 5
        elif reel1 == "🍋":
            multiplier = 3
        else:
            multiplier = 2
        
        winnings = amount * multiplier
        add_balance(server_id, user_id, winnings)
        update_stats(server_id, user_id, True, amount, winnings)
        
        new_balance = get_balance(server_id, user_id)
        
        embed = discord.Embed(
            title="🎰 JACKPOT! 🎰",
            description=f"**{result}**\n\n💰 You won **{winnings:,} coins** ({multiplier}x)!\n\n🪙 New balance: **{new_balance:,} coins**",
            color=Colors.SUCCESS,
            timestamp=datetime.now(timezone.utc)
        )
    elif reel1 == reel2 or reel2 == reel3 or reel1 == reel3:
        winnings = int(amount * 1.5)
        add_balance(server_id, user_id, winnings)
        update_stats(server_id, user_id, True, amount, winnings)
        
        new_balance = get_balance(server_id, user_id)
        
        embed = discord.Embed(
            title="🎰 Small Win!",
            description=f"**{result}**\n\n💰 You won **{winnings:,} coins** (1.5x)!\n\n🪙 New balance: **{new_balance:,} coins**",
            color=Colors.WARNING,
            timestamp=datetime.now(timezone.utc)
        )
    else:
        update_stats(server_id, user_id, False, amount)
        new_balance = get_balance(server_id, user_id)
        
        embed = discord.Embed(
            title="🎰 No Match",
            description=f"**{result}**\n\nYou lost **{amount:,} coins**\n\n💰 Remaining: **{new_balance:,} coins**",
            color=Colors.DANGER,
            timestamp=datetime.now(timezone.utc)
        )
    
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    embed.set_footer(text="Coin Royale Casino")
    
    await interaction.followup.send(embed=embed)
    asyncio.create_task(batch_save_database())

@tree.command(name="dice", description="🎲 Roll dice (1-6)")
@app_commands.describe(amount="Amount to bet")
async def dice(interaction: discord.Interaction, amount: int):
    """Dice roll game"""
    await interaction.response.defer()
    
    if amount <= 0:
        await interaction.followup.send("❌ Bet amount must be positive!", ephemeral=True)
        return
    
    server_id = interaction.guild.id
    user_id = interaction.user.id
    
    if not subtract_balance(server_id, user_id, amount):
        balance = get_balance(server_id, user_id)
        await interaction.followup.send(f"❌ Insufficient funds! You have {balance:,} coins.", ephemeral=True)
        return
    
    player_roll = random.randint(1, 6)
    bot_roll = random.randint(1, 6)
    
    if player_roll > bot_roll:
        winnings = amount * 2
        add_balance(server_id, user_id, winnings)
        update_stats(server_id, user_id, True, amount, winnings)
        
        new_balance = get_balance(server_id, user_id)
        
        embed = discord.Embed(
            title="🎲 YOU WIN!",
            description=f"**Your roll:** 🎲 {player_roll}\n**Bot roll:** 🎲 {bot_roll}\n\n💰 You won **{winnings:,} coins**!\n\n🪙 New balance: **{new_balance:,} coins**",
            color=Colors.SUCCESS,
            timestamp=datetime.now(timezone.utc)
        )
    elif player_roll < bot_roll:
        update_stats(server_id, user_id, False, amount)
        new_balance = get_balance(server_id, user_id)
        
        embed = discord.Embed(
            title="🎲 YOU LOSE!",
            description=f"**Your roll:** 🎲 {player_roll}\n**Bot roll:** 🎲 {bot_roll}\n\nYou lost **{amount:,} coins**\n\n💰 Remaining: **{new_balance:,} coins**",
            color=Colors.DANGER,
            timestamp=datetime.now(timezone.utc)
        )
    else:
        add_balance(server_id, user_id, amount)
        new_balance = get_balance(server_id, user_id)
        
        embed = discord.Embed(
            title="🎲 TIE!",
            description=f"**Your roll:** 🎲 {player_roll}\n**Bot roll:** 🎲 {bot_roll}\n\nIt's a tie! Bet returned.\n\n💰 Balance: **{new_balance:,} coins**",
            color=Colors.WARNING,
            timestamp=datetime.now(timezone.utc)
        )
    
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    embed.set_footer(text="Coin Royale Casino")
    
    await interaction.followup.send(embed=embed)
    asyncio.create_task(batch_save_database())

@tree.command(name="roulette", description="🎡 Red or Black roulette")
@app_commands.describe(
    amount="Amount to bet",
    color="Choose: red or black"
)
@app_commands.choices(color=[
    app_commands.Choice(name="Red", value="red"),
    app_commands.Choice(name="Black", value="black")
])
async def roulette(interaction: discord.Interaction, amount: int, color: app_commands.Choice[str]):
    """Roulette game"""
    await interaction.response.defer()
    
    if amount <= 0:
        await interaction.followup.send("❌ Bet amount must be positive!", ephemeral=True)
        return
    
    server_id = interaction.guild.id
    user_id = interaction.user.id
    
    if not subtract_balance(server_id, user_id, amount):
        balance = get_balance(server_id, user_id)
        await interaction.followup.send(f"❌ Insufficient funds! You have {balance:,} coins.", ephemeral=True)
        return
    
    result_color = random.choice(["red", "black"])
    
    color_emoji = {"red": "🔴", "black": "⚫"}
    
    if color.value == result_color:
        winnings = amount * 2
        add_balance(server_id, user_id, winnings)
        update_stats(server_id, user_id, True, amount, winnings)
        
        new_balance = get_balance(server_id, user_id)
        
        embed = discord.Embed(
            title="🎡 YOU WIN!",
            description=f"**Result:** {color_emoji[result_color]} **{result_color.upper()}**\n\n💰 You won **{winnings:,} coins**!\n\n🪙 New balance: **{new_balance:,} coins**",
            color=Colors.SUCCESS,
            timestamp=datetime.now(timezone.utc)
        )
    else:
        update_stats(server_id, user_id, False, amount)
        new_balance = get_balance(server_id, user_id)
        
        embed = discord.Embed(
            title="🎡 YOU LOSE!",
            description=f"**Result:** {color_emoji[result_color]} **{result_color.upper()}**\n\nYou lost **{amount:,} coins**\n\n💰 Remaining: **{new_balance:,} coins**",
            color=Colors.DANGER,
            timestamp=datetime.now(timezone.utc)
        )
    
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    embed.set_footer(text="Coin Royale Casino")
    
    await interaction.followup.send(embed=embed)
    asyncio.create_task(batch_save_database())

@tree.command(name="blackjack", description="🃏 Simple blackjack")
@app_commands.describe(amount="Amount to bet")
async def blackjack(interaction: discord.Interaction, amount: int):
    """Simple blackjack game"""
    await interaction.response.defer()
    
    if amount <= 0:
        await interaction.followup.send("❌ Bet amount must be positive!", ephemeral=True)
        return
    
    server_id = interaction.guild.id
    user_id = interaction.user.id
    
    if not subtract_balance(server_id, user_id, amount):
        balance = get_balance(server_id, user_id)
        await interaction.followup.send(f"❌ Insufficient funds! You have {balance:,} coins.", ephemeral=True)
        return
    
    player_total = random.randint(17, 21)
    dealer_total = random.randint(17, 21)
    
    if player_total > dealer_total or (player_total == 21 and dealer_total != 21):
        winnings = amount * 2
        add_balance(server_id, user_id, winnings)
        update_stats(server_id, user_id, True, amount, winnings)
        
        new_balance = get_balance(server_id, user_id)
        
        embed = discord.Embed(
            title="🃏 BLACKJACK WIN!",
            description=f"**Your hand:** {player_total}\n**Dealer hand:** {dealer_total}\n\n💰 You won **{winnings:,} coins**!\n\n🪙 New balance: **{new_balance:,} coins**",
            color=Colors.SUCCESS,
            timestamp=datetime.now(timezone.utc)
        )
    elif player_total < dealer_total:
        update_stats(server_id, user_id, False, amount)
        new_balance = get_balance(server_id, user_id)
        
        embed = discord.Embed(
            title="🃏 DEALER WINS!",
            description=f"**Your hand:** {player_total}\n**Dealer hand:** {dealer_total}\n\nYou lost **{amount:,} coins**\n\n💰 Remaining: **{new_balance:,} coins**",
            color=Colors.DANGER,
            timestamp=datetime.now(timezone.utc)
        )
    else:
        add_balance(server_id, user_id, amount)
        new_balance = get_balance(server_id, user_id)
        
        embed = discord.Embed(
            title="🃏 PUSH!",
            description=f"**Your hand:** {player_total}\n**Dealer hand:** {dealer_total}\n\nIt's a tie! Bet returned.\n\n💰 Balance: **{new_balance:,} coins**",
            color=Colors.WARNING,
            timestamp=datetime.now(timezone.utc)
        )
    
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    embed.set_footer(text="Coin Royale Casino")
    
    await interaction.followup.send(embed=embed)
    asyncio.create_task(batch_save_database())

@tree.command(name="double", description="💥 50/50 double or lose")
@app_commands.describe(amount="Amount to bet")
async def double(interaction: discord.Interaction, amount: int):
    """50/50 double or lose"""
    await interaction.response.defer()
    
    if amount <= 0:
        await interaction.followup.send("❌ Bet amount must be positive!", ephemeral=True)
        return
    
    server_id = interaction.guild.id
    user_id = interaction.user.id
    
    if not subtract_balance(server_id, user_id, amount):
        balance = get_balance(server_id, user_id)
        await interaction.followup.send(f"❌ Insufficient funds! You have {balance:,} coins.", ephemeral=True)
        return
    
    won = random.choice([True, False])
    
    if won:
        winnings = amount * 2
        add_balance(server_id, user_id, winnings)
        update_stats(server_id, user_id, True, amount, winnings)
        
        new_balance = get_balance(server_id, user_id)
        
        embed = discord.Embed(
            title="💥 DOUBLED!",
            description=f"🎉 You doubled your bet!\n\n💰 You won **{winnings:,} coins**!\n\n🪙 New balance: **{new_balance:,} coins**",
            color=Colors.SUCCESS,
            timestamp=datetime.now(timezone.utc)
        )
    else:
        update_stats(server_id, user_id, False, amount)
        new_balance = get_balance(server_id, user_id)
        
        embed = discord.Embed(
            title="💔 LOST IT ALL!",
            description=f"You lost **{amount:,} coins**\n\n💰 Remaining: **{new_balance:,} coins**",
            color=Colors.DANGER,
            timestamp=datetime.now(timezone.utc)
        )
    
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    embed.set_footer(text="Coin Royale Casino")
    
    await interaction.followup.send(embed=embed)
    asyncio.create_task(batch_save_database())

@tree.command(name="stats", description="📊 View your game statistics")
async def stats(interaction: discord.Interaction, user: Optional[discord.Member] = None):
    """View game statistics"""
    target_user = user or interaction.user
    
    server_id = interaction.guild.id
    user_id = target_user.id
    
    balance = get_balance(server_id, user_id)
    
    if server_id not in game_stats or user_id not in game_stats[server_id]:
        embed = discord.Embed(
            title="📊 Game Statistics",
            description=f"**{target_user.display_name}** hasn't played any games yet!\n\n💰 Balance: **{balance:,} coins**",
            color=Colors.INFO,
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_thumbnail(url=target_user.display_avatar.url)
        embed.set_footer(text="Coin Royale Casino")
        await interaction.response.send_message(embed=embed)
        return
    
    stats = game_stats[server_id][user_id]
    
    total_games = stats["wins"] + stats["losses"]
    win_rate = (stats["wins"] / total_games * 100) if total_games > 0 else 0
    net_profit = stats["total_won"] - stats["total_bet"]
    
    embed = discord.Embed(
        title=f"📊 Game Statistics - {target_user.display_name}",
        color=Colors.PRIMARY,
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_thumbnail(url=target_user.display_avatar.url)
    
    embed.add_field(name="💰 Current Balance", value=f"**{balance:,}** coins", inline=True)
    embed.add_field(name="🎮 Total Games", value=f"**{total_games:,}**", inline=True)
    embed.add_field(name="📈 Win Rate", value=f"**{win_rate:.1f}%**", inline=True)
    
    embed.add_field(name="✅ Wins", value=f"**{stats['wins']:,}**", inline=True)
    embed.add_field(name="❌ Losses", value=f"**{stats['losses']:,}**", inline=True)
    embed.add_field(name="💵 Net Profit", value=f"**{net_profit:,}** coins", inline=True)
    
    embed.add_field(name="🎲 Total Bet", value=f"**{stats['total_bet']:,}** coins", inline=True)
    embed.add_field(name="🏆 Total Won", value=f"**{stats['total_won']:,}** coins", inline=True)
    
    embed.set_footer(text="Coin Royale Casino", icon_url="https://i.imgur.com/AfFp7pu.png")
    
    await interaction.response.send_message(embed=embed)

@tree.command(name="leaderboard", description="🏆 Top richest players")
async def leaderboard(interaction: discord.Interaction):
    """View server leaderboard"""
    await interaction.response.defer()
    
    server_id = interaction.guild.id
    
    if server_id not in user_balances or not user_balances[server_id]:
        embed = discord.Embed(
            title="🏆 Leaderboard",
            description="No players yet!",
            color=Colors.INFO,
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_footer(text="Coin Royale Casino")
        await interaction.followup.send(embed=embed)
        return
    
    sorted_users = sorted(
        user_balances[server_id].items(),
        key=lambda x: x[1],
        reverse=True
    )[:10]
    
    embed = discord.Embed(
        title="🏆 Coin Royale Leaderboard",
        description="**Top 10 Richest Players**",
        color=Colors.PRIMARY,
        timestamp=datetime.now(timezone.utc)
    )
    
    medals = ["🥇", "🥈", "🥉"]
    
    leaderboard_text = ""
    for i, (user_id, balance) in enumerate(sorted_users, 1):
        try:
            user = await bot.fetch_user(user_id)
            medal = medals[i-1] if i <= 3 else f"**{i}.**"
            leaderboard_text += f"{medal} {user.display_name} - **{balance:,}** coins\n"
        except:
            continue
    
    embed.description = leaderboard_text or "No players found"
    embed.set_footer(text=f"Server: {interaction.guild.name} • Coin Royale Casino")
    
    await interaction.followup.send(embed=embed)

@bot.event
async def on_ready():
    """Bot startup"""
    logging.info(f"🚀 Coin Royale logged in as {bot.user}")
    logging.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    await load_database()
    
    try:
        synced = await tree.sync()
        logging.info(f"✅ Synced {len(synced)} slash commands")
        command_names = [cmd.name for cmd in synced]
        logging.info(f"🎮 Commands: {', '.join(command_names)}")
    except Exception as e:
        logging.error(f"❌ Failed to sync commands: {e}")
    
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.playing,
            name="🎰 Coin Royale Casino | /balance"
        )
    )
    
    logging.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logging.info(f"🎰 Coin Royale is fully operational!")
    logging.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

@bot.event
async def on_guild_join(guild):
    """Handle bot joining a guild"""
    logging.info(f"🆕 Joined new server: {guild.name} ({guild.id})")
    
    welcome_embed = discord.Embed(
        title="🎰 Welcome to Coin Royale Casino!",
        description="Get ready to gamble and have fun!\n\nEveryone starts with **1,000 coins**!",
        color=Colors.PRIMARY
    )
    
    welcome_embed.add_field(
        name="💰 Economy Commands",
        value="```\n/balance - Check your coins\n/daily - Get daily coins\n/transfer - Send coins\n/stats - View your stats\n/leaderboard - Top players\n```",
        inline=False
    )
    
    welcome_embed.add_field(
        name="🎲 Casino Games",
        value="```\n/bet - Coin flip\n/slots - Slot machine\n/dice - Roll dice\n/roulette - Red or Black\n/blackjack - 21 card game\n/double - Double or lose\n```",
        inline=False
    )
    
    welcome_embed.set_footer(text="Coin Royale Casino • Good luck!", icon_url="https://i.imgur.com/AfFp7pu.png")
    welcome_embed.set_thumbnail(url=bot.user.display_avatar.url if bot.user.display_avatar else None)
    
    target_channel = None
    if guild.system_channel and guild.system_channel.permissions_for(guild.me).send_messages:
        target_channel = guild.system_channel
    else:
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                target_channel = channel
                break
    
    if target_channel:
        try:
            await target_channel.send(embed=welcome_embed)
        except discord.HTTPException:
            pass

@bot.event
async def on_guild_remove(guild):
    """Handle bot leaving a guild"""
    logging.info(f"👋 Left server: {guild.name} ({guild.id})")

# Get Discord token and start the bot
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN is not set in the environment.")

# Start keep alive system and run the bot
keep_alive()
bot.run(DISCORD_TOKEN)