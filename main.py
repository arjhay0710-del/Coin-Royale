import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import os
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List
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
    PRIMARY = 0xFF0000  # Red (Pokéball)
    SUCCESS = 0x57F287  # Green
    WARNING = 0xFEE75C  # Yellow
    DANGER = 0xED4245   # Red
    INFO = 0x5865F2     # Blue
    POKEVERSE = 0xFFCB05  # Pokémon Yellow

# Pokémon data with rarities, base stats, and images (Gen 1 - 151 Pokémon)
POKEMON_DATA = {
    # Common (60% spawn rate) - 40 Pokémon
    "Pidgey": {"rarity": "common", "hp": 40, "atk": 45, "type": "🪶 Flying", "id": 16},
    "Rattata": {"rarity": "common", "hp": 30, "atk": 56, "type": "⚪ Normal", "id": 19},
    "Caterpie": {"rarity": "common", "hp": 45, "atk": 30, "type": "🐛 Bug", "id": 10},
    "Weedle": {"rarity": "common", "hp": 40, "atk": 35, "type": "🐛 Bug", "id": 13},
    "Spearow": {"rarity": "common", "hp": 40, "atk": 60, "type": "🪶 Flying", "id": 21},
    "Ekans": {"rarity": "common", "hp": 35, "atk": 60, "type": "☠️ Poison", "id": 23},
    "Sandshrew": {"rarity": "common", "hp": 50, "atk": 75, "type": "⛰️ Ground", "id": 27},
    "Zubat": {"rarity": "common", "hp": 40, "atk": 45, "type": "☠️ Poison", "id": 41},
    "Oddish": {"rarity": "common", "hp": 45, "atk": 50, "type": "🌿 Grass", "id": 43},
    "Paras": {"rarity": "common", "hp": 35, "atk": 70, "type": "🐛 Bug", "id": 46},
    "Venonat": {"rarity": "common", "hp": 60, "atk": 55, "type": "🐛 Bug", "id": 48},
    "Diglett": {"rarity": "common", "hp": 10, "atk": 55, "type": "⛰️ Ground", "id": 50},
    "Meowth": {"rarity": "common", "hp": 40, "atk": 45, "type": "⚪ Normal", "id": 52},
    "Psyduck": {"rarity": "common", "hp": 50, "atk": 52, "type": "💧 Water", "id": 54},
    "Mankey": {"rarity": "common", "hp": 40, "atk": 80, "type": "🥊 Fighting", "id": 56},
    "Poliwag": {"rarity": "common", "hp": 40, "atk": 50, "type": "💧 Water", "id": 60},
    "Bellsprout": {"rarity": "common", "hp": 50, "atk": 75, "type": "🌿 Grass", "id": 69},
    "Tentacool": {"rarity": "common", "hp": 40, "atk": 40, "type": "💧 Water", "id": 72},
    "Geodude": {"rarity": "common", "hp": 40, "atk": 80, "type": "🪨 Rock", "id": 74},
    "Slowpoke": {"rarity": "common", "hp": 90, "atk": 65, "type": "💧 Water", "id": 79},
    "Magnemite": {"rarity": "common", "hp": 25, "atk": 35, "type": "⚡ Electric", "id": 81},
    "Doduo": {"rarity": "common", "hp": 35, "atk": 85, "type": "🪶 Flying", "id": 84},
    "Seel": {"rarity": "common", "hp": 65, "atk": 45, "type": "💧 Water", "id": 86},
    "Grimer": {"rarity": "common", "hp": 80, "atk": 80, "type": "☠️ Poison", "id": 88},
    "Shellder": {"rarity": "common", "hp": 30, "atk": 65, "type": "💧 Water", "id": 90},
    "Gastly": {"rarity": "common", "hp": 30, "atk": 35, "type": "👻 Ghost", "id": 92},
    "Drowzee": {"rarity": "common", "hp": 60, "atk": 48, "type": "🧠 Psychic", "id": 96},
    "Krabby": {"rarity": "common", "hp": 30, "atk": 105, "type": "💧 Water", "id": 98},
    "Voltorb": {"rarity": "common", "hp": 40, "atk": 30, "type": "⚡ Electric", "id": 100},
    "Cubone": {"rarity": "common", "hp": 50, "atk": 50, "type": "⛰️ Ground", "id": 104},
    "Koffing": {"rarity": "common", "hp": 40, "atk": 65, "type": "☠️ Poison", "id": 109},
    "Horsea": {"rarity": "common", "hp": 30, "atk": 40, "type": "💧 Water", "id": 116},
    "Goldeen": {"rarity": "common", "hp": 45, "atk": 67, "type": "💧 Water", "id": 118},
    "Staryu": {"rarity": "common", "hp": 30, "atk": 45, "type": "💧 Water", "id": 120},
    "Magikarp": {"rarity": "common", "hp": 20, "atk": 10, "type": "💧 Water", "id": 129},
    "Omanyte": {"rarity": "common", "hp": 35, "atk": 40, "type": "🪨 Rock", "id": 138},
    "Kabuto": {"rarity": "common", "hp": 30, "atk": 80, "type": "🪨 Rock", "id": 140},
    "Pidgeotto": {"rarity": "common", "hp": 63, "atk": 60, "type": "🪶 Flying", "id": 17},
    "Kakuna": {"rarity": "common", "hp": 45, "atk": 25, "type": "🐛 Bug", "id": 14},
    "Metapod": {"rarity": "common", "hp": 50, "atk": 20, "type": "🐛 Bug", "id": 11},
    
    # Uncommon (25% spawn rate) - 45 Pokémon
    "Pikachu": {"rarity": "uncommon", "hp": 35, "atk": 55, "type": "⚡ Electric", "id": 25},
    "Bulbasaur": {"rarity": "uncommon", "hp": 45, "atk": 49, "type": "🌿 Grass", "id": 1},
    "Charmander": {"rarity": "uncommon", "hp": 39, "atk": 52, "type": "🔥 Fire", "id": 4},
    "Squirtle": {"rarity": "uncommon", "hp": 44, "atk": 48, "type": "💧 Water", "id": 7},
    "Eevee": {"rarity": "uncommon", "hp": 55, "atk": 55, "type": "⚪ Normal", "id": 133},
    "Nidoran♀": {"rarity": "uncommon", "hp": 55, "atk": 47, "type": "☠️ Poison", "id": 29},
    "Nidoran♂": {"rarity": "uncommon", "hp": 46, "atk": 57, "type": "☠️ Poison", "id": 32},
    "Clefairy": {"rarity": "uncommon", "hp": 70, "atk": 45, "type": "🧚 Fairy", "id": 35},
    "Vulpix": {"rarity": "uncommon", "hp": 38, "atk": 41, "type": "🔥 Fire", "id": 37},
    "Jigglypuff": {"rarity": "uncommon", "hp": 115, "atk": 45, "type": "⚪ Normal", "id": 39},
    "Growlithe": {"rarity": "uncommon", "hp": 55, "atk": 70, "type": "🔥 Fire", "id": 58},
    "Abra": {"rarity": "uncommon", "hp": 25, "atk": 20, "type": "🧠 Psychic", "id": 63},
    "Machop": {"rarity": "uncommon", "hp": 70, "atk": 80, "type": "🥊 Fighting", "id": 66},
    "Ponyta": {"rarity": "uncommon", "hp": 50, "atk": 85, "type": "🔥 Fire", "id": 77},
    "Farfetch'd": {"rarity": "uncommon", "hp": 52, "atk": 90, "type": "🪶 Flying", "id": 83},
    "Onix": {"rarity": "uncommon", "hp": 35, "atk": 45, "type": "🪨 Rock", "id": 95},
    "Exeggcute": {"rarity": "uncommon", "hp": 60, "atk": 40, "type": "🌿 Grass", "id": 102},
    "Lickitung": {"rarity": "uncommon", "hp": 90, "atk": 55, "type": "⚪ Normal", "id": 108},
    "Rhyhorn": {"rarity": "uncommon", "hp": 80, "atk": 85, "type": "⛰️ Ground", "id": 111},
    "Chansey": {"rarity": "uncommon", "hp": 250, "atk": 5, "type": "⚪ Normal", "id": 113},
    "Tangela": {"rarity": "uncommon", "hp": 65, "atk": 55, "type": "🌿 Grass", "id": 114},
    "Kangaskhan": {"rarity": "uncommon", "hp": 105, "atk": 95, "type": "⚪ Normal", "id": 115},
    "Scyther": {"rarity": "uncommon", "hp": 70, "atk": 110, "type": "🐛 Bug", "id": 123},
    "Pinsir": {"rarity": "uncommon", "hp": 65, "atk": 125, "type": "🐛 Bug", "id": 127},
    "Tauros": {"rarity": "uncommon", "hp": 75, "atk": 100, "type": "⚪ Normal", "id": 128},
    "Ditto": {"rarity": "uncommon", "hp": 48, "atk": 48, "type": "⚪ Normal", "id": 132},
    "Porygon": {"rarity": "uncommon", "hp": 65, "atk": 60, "type": "⚪ Normal", "id": 137},
    "Ivysaur": {"rarity": "uncommon", "hp": 60, "atk": 62, "type": "🌿 Grass", "id": 2},
    "Charmeleon": {"rarity": "uncommon", "hp": 58, "atk": 64, "type": "🔥 Fire", "id": 5},
    "Wartortle": {"rarity": "uncommon", "hp": 59, "atk": 63, "type": "💧 Water", "id": 8},
    "Raticate": {"rarity": "uncommon", "hp": 55, "atk": 81, "type": "⚪ Normal", "id": 20},
    "Fearow": {"rarity": "uncommon", "hp": 65, "atk": 90, "type": "🪶 Flying", "id": 22},
    "Arbok": {"rarity": "uncommon", "hp": 60, "atk": 95, "type": "☠️ Poison", "id": 24},
    "Raichu": {"rarity": "uncommon", "hp": 60, "atk": 90, "type": "⚡ Electric", "id": 26},
    "Sandslash": {"rarity": "uncommon", "hp": 75, "atk": 100, "type": "⛰️ Ground", "id": 28},
    "Nidorina": {"rarity": "uncommon", "hp": 70, "atk": 62, "type": "☠️ Poison", "id": 30},
    "Nidorino": {"rarity": "uncommon", "hp": 61, "atk": 72, "type": "☠️ Poison", "id": 33},
    "Gloom": {"rarity": "uncommon", "hp": 60, "atk": 65, "type": "🌿 Grass", "id": 44},
    "Parasect": {"rarity": "uncommon", "hp": 60, "atk": 95, "type": "🐛 Bug", "id": 47},
    "Venomoth": {"rarity": "uncommon", "hp": 70, "atk": 65, "type": "🐛 Bug", "id": 49},
    "Dugtrio": {"rarity": "uncommon", "hp": 35, "atk": 100, "type": "⛰️ Ground", "id": 51},
    "Persian": {"rarity": "uncommon", "hp": 65, "atk": 70, "type": "⚪ Normal", "id": 53},
    "Golduck": {"rarity": "uncommon", "hp": 80, "atk": 82, "type": "💧 Water", "id": 55},
    "Primeape": {"rarity": "uncommon", "hp": 65, "atk": 105, "type": "🥊 Fighting", "id": 57},
    "Weepinbell": {"rarity": "uncommon", "hp": 65, "atk": 90, "type": "🌿 Grass", "id": 70},
    
    # Rare (10% spawn rate) - 35 Pokémon
    "Dratini": {"rarity": "rare", "hp": 41, "atk": 64, "type": "🐉 Dragon", "id": 147},
    "Lapras": {"rarity": "rare", "hp": 130, "atk": 85, "type": "💧 Water", "id": 131},
    "Snorlax": {"rarity": "rare", "hp": 160, "atk": 110, "type": "⚪ Normal", "id": 143},
    "Gyarados": {"rarity": "rare", "hp": 95, "atk": 125, "type": "💧 Water", "id": 130},
    "Aerodactyl": {"rarity": "rare", "hp": 80, "atk": 105, "type": "🪨 Rock", "id": 142},
    "Dragonair": {"rarity": "rare", "hp": 61, "atk": 84, "type": "🐉 Dragon", "id": 148},
    "Venusaur": {"rarity": "rare", "hp": 80, "atk": 82, "type": "🌿 Grass", "id": 3},
    "Charizard": {"rarity": "rare", "hp": 78, "atk": 84, "type": "🔥 Fire", "id": 6},
    "Blastoise": {"rarity": "rare", "hp": 79, "atk": 83, "type": "💧 Water", "id": 9},
    "Pidgeot": {"rarity": "rare", "hp": 83, "atk": 80, "type": "🪶 Flying", "id": 18},
    "Nidoqueen": {"rarity": "rare", "hp": 90, "atk": 92, "type": "☠️ Poison", "id": 31},
    "Nidoking": {"rarity": "rare", "hp": 81, "atk": 102, "type": "☠️ Poison", "id": 34},
    "Clefable": {"rarity": "rare", "hp": 95, "atk": 70, "type": "🧚 Fairy", "id": 36},
    "Ninetales": {"rarity": "rare", "hp": 73, "atk": 76, "type": "🔥 Fire", "id": 38},
    "Wigglytuff": {"rarity": "rare", "hp": 140, "atk": 70, "type": "⚪ Normal", "id": 40},
    "Vileplume": {"rarity": "rare", "hp": 75, "atk": 80, "type": "🌿 Grass", "id": 45},
    "Golbat": {"rarity": "rare", "hp": 75, "atk": 80, "type": "☠️ Poison", "id": 42},
    "Victreebel": {"rarity": "rare", "hp": 80, "atk": 105, "type": "🌿 Grass", "id": 71},
    "Tentacruel": {"rarity": "rare", "hp": 80, "atk": 70, "type": "💧 Water", "id": 73},
    "Golem": {"rarity": "rare", "hp": 80, "atk": 120, "type": "🪨 Rock", "id": 76},
    "Rapidash": {"rarity": "rare", "hp": 65, "atk": 100, "type": "🔥 Fire", "id": 78},
    "Slowbro": {"rarity": "rare", "hp": 95, "atk": 75, "type": "💧 Water", "id": 80},
    "Magneton": {"rarity": "rare", "hp": 50, "atk": 60, "type": "⚡ Electric", "id": 82},
    "Dodrio": {"rarity": "rare", "hp": 60, "atk": 110, "type": "🪶 Flying", "id": 85},
    "Dewgong": {"rarity": "rare", "hp": 90, "atk": 70, "type": "💧 Water", "id": 87},
    "Muk": {"rarity": "rare", "hp": 105, "atk": 105, "type": "☠️ Poison", "id": 89},
    "Cloyster": {"rarity": "rare", "hp": 50, "atk": 95, "type": "💧 Water", "id": 91},
    "Haunter": {"rarity": "rare", "hp": 45, "atk": 50, "type": "👻 Ghost", "id": 93},
    "Hypno": {"rarity": "rare", "hp": 85, "atk": 73, "type": "🧠 Psychic", "id": 97},
    "Kingler": {"rarity": "rare", "hp": 55, "atk": 130, "type": "💧 Water", "id": 99},
    "Electrode": {"rarity": "rare", "hp": 60, "atk": 50, "type": "⚡ Electric", "id": 101},
    "Exeggutor": {"rarity": "rare", "hp": 95, "atk": 95, "type": "🌿 Grass", "id": 103},
    "Marowak": {"rarity": "rare", "hp": 60, "atk": 80, "type": "⛰️ Ground", "id": 105},
    "Hitmonlee": {"rarity": "rare", "hp": 50, "atk": 120, "type": "🥊 Fighting", "id": 106},
    "Hitmonchan": {"rarity": "rare", "hp": 50, "atk": 105, "type": "🥊 Fighting", "id": 107},
    
    # Legendary (5% spawn rate) - 15 Pokémon
    "Articuno": {"rarity": "legendary", "hp": 90, "atk": 85, "type": "❄️ Ice", "id": 144},
    "Zapdos": {"rarity": "legendary", "hp": 90, "atk": 90, "type": "⚡ Electric", "id": 145},
    "Moltres": {"rarity": "legendary", "hp": 90, "atk": 100, "type": "🔥 Fire", "id": 146},
    "Mewtwo": {"rarity": "legendary", "hp": 106, "atk": 110, "type": "🧠 Psychic", "id": 150},
    "Mew": {"rarity": "legendary", "hp": 100, "atk": 100, "type": "🧠 Psychic", "id": 151},
    "Dragonite": {"rarity": "legendary", "hp": 91, "atk": 134, "type": "🐉 Dragon", "id": 149},
    "Gengar": {"rarity": "legendary", "hp": 60, "atk": 65, "type": "👻 Ghost", "id": 94},
    "Alakazam": {"rarity": "legendary", "hp": 55, "atk": 50, "type": "🧠 Psychic", "id": 65},
    "Machamp": {"rarity": "legendary", "hp": 90, "atk": 130, "type": "🥊 Fighting", "id": 68},
    "Arcanine": {"rarity": "legendary", "hp": 90, "atk": 110, "type": "🔥 Fire", "id": 59},
    "Poliwrath": {"rarity": "legendary", "hp": 90, "atk": 95, "type": "💧 Water", "id": 62},
    "Rhydon": {"rarity": "legendary", "hp": 105, "atk": 130, "type": "⛰️ Ground", "id": 112},
    "Starmie": {"rarity": "legendary", "hp": 60, "atk": 75, "type": "💧 Water", "id": 121},
    "Seaking": {"rarity": "legendary", "hp": 80, "atk": 92, "type": "💧 Water", "id": 119},
    "Omastar": {"rarity": "legendary", "hp": 70, "atk": 60, "type": "🪨 Rock", "id": 139},
}

def get_pokemon_image(pokemon_id: int) -> str:
    """Get Pokémon image URL from PokeAPI"""
    return f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/{pokemon_id}.png"

# Pokéball catch rates and prices
POKEBALL_DATA = {
    "pokeball": {"name": "Poké Ball", "emoji": "🔴", "catch_rate": 0.4, "price": 100},
    "greatball": {"name": "Great Ball", "emoji": "🔵", "catch_rate": 0.6, "price": 300},
    "ultraball": {"name": "Ultra Ball", "emoji": "🟡", "catch_rate": 0.8, "price": 600},
}

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# Global data structures - server-isolated
user_pokemon = {}  # {server_id: {user_id: [pokemon_list]}}
user_inventory = {}  # {server_id: {user_id: {pokeball: count, greatball: count, ultraball: count}}}
user_coins = {}  # {server_id: {user_id: coins}}
user_daily = {}  # {server_id: {user_id: last_daily_timestamp}}
active_trades = {}  # {server_id: {user_id: trade_data}}
wild_pokemon = {}  # {server_id: {user_id: pokemon_name}}
pending_database_save = False
last_database_save = datetime.now()

def get_coins(server_id: int, user_id: int) -> int:
    """Get user coins"""
    if server_id not in user_coins:
        user_coins[server_id] = {}
    if user_id not in user_coins[server_id]:
        user_coins[server_id][user_id] = 1000  # Starting coins
    return user_coins[server_id][user_id]

def set_coins(server_id: int, user_id: int, amount: int):
    """Set user coins"""
    if server_id not in user_coins:
        user_coins[server_id] = {}
    user_coins[server_id][user_id] = max(0, amount)

def get_inventory(server_id: int, user_id: int) -> Dict:
    """Get user inventory"""
    if server_id not in user_inventory:
        user_inventory[server_id] = {}
    if user_id not in user_inventory[server_id]:
        user_inventory[server_id][user_id] = {"pokeball": 5, "greatball": 0, "ultraball": 0}
    return user_inventory[server_id][user_id]

def get_pokemon_list(server_id: int, user_id: int) -> List:
    """Get user's Pokémon"""
    if server_id not in user_pokemon:
        user_pokemon[server_id] = {}
    if user_id not in user_pokemon[server_id]:
        user_pokemon[server_id][user_id] = []
    return user_pokemon[server_id][user_id]

def spawn_wild_pokemon() -> str:
    """Spawn a random wild Pokémon based on rarity"""
    rarity_weights = {
        "common": 60,
        "uncommon": 25,
        "rare": 10,
        "legendary": 5
    }
    
    pokemon_by_rarity = {}
    for name, data in POKEMON_DATA.items():
        rarity = data["rarity"]
        if rarity not in pokemon_by_rarity:
            pokemon_by_rarity[rarity] = []
        pokemon_by_rarity[rarity].append(name)
    
    chosen_rarity = random.choices(
        list(rarity_weights.keys()),
        weights=list(rarity_weights.values())
    )[0]
    
    return random.choice(pokemon_by_rarity[chosen_rarity])

async def batch_save_database():
    """Batch database saves"""
    global pending_database_save, last_database_save
    
    if not pending_database_save:
        pending_database_save = True
        await asyncio.sleep(5)
        
        if (datetime.now() - last_database_save).total_seconds() >= 30:
            await save_database()
            last_database_save = datetime.now()
        
        pending_database_save = False

async def load_database():
    """Load data from database channel"""
    global user_pokemon, user_inventory, user_coins, user_daily
    
    try:
        db_channel = bot.get_channel(DATABASE_CHANNEL_ID)
        if not db_channel:
            logging.error(f"Database channel {DATABASE_CHANNEL_ID} not found!")
            return

        user_pokemon = {}
        user_inventory = {}
        user_coins = {}
        user_daily = {}
        
        messages = []
        async for message in db_channel.history(limit=50):
            if message.author == bot.user:
                messages.append(message)
        
        messages.sort(key=lambda m: m.created_at, reverse=True)
        
        for message in messages:
            if message.content.startswith("```json") and message.content.endswith("```"):
                try:
                    json_content = message.content[7:-3].strip()
                    data = json.loads(json_content)
                    
                    if isinstance(data, dict) and "user_pokemon" in data:
                        user_pokemon = {int(k): {int(uk): uv for uk, uv in v.items()} for k, v in data.get("user_pokemon", {}).items()}
                        user_inventory = {int(k): {int(uk): uv for uk, uv in v.items()} for k, v in data.get("user_inventory", {}).items()}
                        user_coins = {int(k): {int(uk): uv for uk, uv in v.items()} for k, v in data.get("user_coins", {}).items()}
                        user_daily = {int(k): {int(uk): uv for uk, uv in v.items()} for k, v in data.get("user_daily", {}).items()}
                        
                        logging.info(f"✅ Successfully loaded PokéVerse database")
                        return
                except Exception as e:
                    logging.warning(f"Error processing message: {e}")
                    continue
        
        logging.warning("⚠️ No valid database found")
        
    except Exception as e:
        logging.error(f"Critical error loading database: {e}")

async def save_database():
    """Save all data to database channel"""
    try:
        db_channel = bot.get_channel(DATABASE_CHANNEL_ID)
        if not db_channel:
            logging.error(f"Database channel {DATABASE_CHANNEL_ID} not found!")
            return

        database_data = {
            "user_pokemon": user_pokemon,
            "user_inventory": user_inventory,
            "user_coins": user_coins,
            "user_daily": user_daily,
            "metadata": {
                "version": "1.0-pokeverse",
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "total_servers": len(user_pokemon)
            }
        }
        
        json_content = json.dumps(database_data, indent=2, ensure_ascii=False)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        content_hash = hashlib.md5(json_content.encode()).hexdigest()[:8]
        
        message_content = f"```json\n{json_content}\n```"
        embed = discord.Embed(
            title="💾 PokéVerse Database Backup",
            description=f"```yaml\nVersion: 1.0-pokeverse\nServers: {database_data['metadata']['total_servers']}\nUpdated: {timestamp}\nHash: {content_hash}\n```",
            color=Colors.PRIMARY,
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_footer(text="PokéVerse System")
        
        await db_channel.send(content=message_content, embed=embed)
        logging.info(f"✅ Database saved (hash: {content_hash})")
        
    except Exception as e:
        logging.error(f"Error saving database: {e}")

# Commands

@tree.command(name="catch", description="🎯 Catch a wild Pokémon")
@app_commands.describe(ball="Choose which Poké Ball to use")
@app_commands.choices(ball=[
    app_commands.Choice(name="🔴 Poké Ball (40% catch rate)", value="pokeball"),
    app_commands.Choice(name="🔵 Great Ball (60% catch rate)", value="greatball"),
    app_commands.Choice(name="🟡 Ultra Ball (80% catch rate)", value="ultraball")
])
async def catch(interaction: discord.Interaction, ball: app_commands.Choice[str]):
    """Catch a wild Pokémon"""
    await interaction.response.defer()
    
    server_id = interaction.guild.id
    user_id = interaction.user.id
    
    # Check inventory
    inventory = get_inventory(server_id, user_id)
    ball_type = ball.value
    
    if inventory.get(ball_type, 0) <= 0:
        await interaction.followup.send(f"❌ You don't have any {POKEBALL_DATA[ball_type]['name']}s! Use `/buy` to purchase more.", ephemeral=True)
        return
    
    # Deduct ball
    inventory[ball_type] -= 1
    
    # Spawn wild Pokémon
    pokemon_name = spawn_wild_pokemon()
    pokemon_data = POKEMON_DATA[pokemon_name]
    
    # Calculate catch attempt
    catch_rate = POKEBALL_DATA[ball_type]["catch_rate"]
    
    # Legendary Pokémon are harder to catch
    if pokemon_data["rarity"] == "legendary":
        catch_rate *= 0.5
    elif pokemon_data["rarity"] == "rare":
        catch_rate *= 0.7
    
    caught = random.random() < catch_rate
    
    ball_emoji = POKEBALL_DATA[ball_type]["emoji"]
    
    if caught:
        # Add to user's Pokémon
        pokemon_list = get_pokemon_list(server_id, user_id)
        pokemon_list.append({
            "name": pokemon_name,
            "hp": pokemon_data["hp"],
            "atk": pokemon_data["atk"],
            "type": pokemon_data["type"],
            "caught_at": datetime.now(timezone.utc).isoformat()
        })
        
        rarity_emoji = {"common": "⚪", "uncommon": "🟢", "rare": "🔵", "legendary": "🟣"}
        
        embed = discord.Embed(
            title=f"🎉 Gotcha! {pokemon_name} was caught!",
            description=f"{ball_emoji} **{POKEBALL_DATA[ball_type]['name']}** successfully caught **{pokemon_name}**!\n\n{rarity_emoji[pokemon_data['rarity']]} **Rarity:** {pokemon_data['rarity'].title()}\n{pokemon_data['type']}\n❤️ HP: {pokemon_data['hp']} | ⚔️ ATK: {pokemon_data['atk']}",
            color=Colors.SUCCESS,
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_thumbnail(url=get_pokemon_image(pokemon_data['id']))
        embed.set_footer(text=f"Total Pokémon: {len(pokemon_list)}")
    else:
        embed = discord.Embed(
            title=f"💨 {pokemon_name} broke free!",
            description=f"{ball_emoji} **{POKEBALL_DATA[ball_type]['name']}** failed to catch **{pokemon_name}**!\n\nThe Pokémon escaped! Better luck next time!",
            color=Colors.DANGER,
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_thumbnail(url=get_pokemon_image(pokemon_data['id']))
        embed.set_footer(text="Try using a better Poké Ball!")
    
    await interaction.followup.send(embed=embed)
    asyncio.create_task(batch_save_database())

@tree.command(name="inventory", description="🎒 View your Poké Balls and Pokémon")
async def inventory(interaction: discord.Interaction, user: Optional[discord.Member] = None):
    """View inventory"""
    target_user = user or interaction.user
    server_id = interaction.guild.id
    user_id = target_user.id
    
    inv = get_inventory(server_id, user_id)
    coins = get_coins(server_id, user_id)
    pokemon_list = get_pokemon_list(server_id, user_id)
    
    embed = discord.Embed(
        title=f"🎒 {target_user.display_name}'s Inventory",
        color=Colors.PRIMARY,
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_thumbnail(url=target_user.display_avatar.url)
    
    # Poké Balls
    balls_text = f"🔴 Poké Ball: **{inv.get('pokeball', 0)}**\n"
    balls_text += f"🔵 Great Ball: **{inv.get('greatball', 0)}**\n"
    balls_text += f"🟡 Ultra Ball: **{inv.get('ultraball', 0)}**"
    embed.add_field(name="🎯 Poké Balls", value=balls_text, inline=True)
    
    # Coins
    embed.add_field(name="💰 Coins", value=f"**{coins:,}** coins", inline=True)
    
    # Pokémon count
    embed.add_field(name="📊 Pokémon", value=f"**{len(pokemon_list)}** caught", inline=True)
    
    # Recent Pokémon
    if pokemon_list:
        recent = pokemon_list[-5:][::-1]
        pokemon_text = "\n".join([f"• {p['name']} {p['type']}" for p in recent])
        embed.add_field(name="🌟 Recent Catches", value=pokemon_text, inline=False)
    
    await interaction.response.send_message(embed=embed)

@tree.command(name="shop", description="🏪 View the Poké Mart")
async def shop(interaction: discord.Interaction):
    """View shop"""
    embed = discord.Embed(
        title="🏪 Poké Mart",
        description="Welcome to the Poké Mart! Purchase Poké Balls to catch Pokémon.",
        color=Colors.PRIMARY,
        timestamp=datetime.now(timezone.utc)
    )
    
    for ball_type, data in POKEBALL_DATA.items():
        embed.add_field(
            name=f"{data['emoji']} {data['name']}",
            value=f"💰 **{data['price']}** coins\n🎯 **{int(data['catch_rate']*100)}%** catch rate\n\nUse `/buy {ball_type} <amount>`",
            inline=True
        )
    
    coins = get_coins(interaction.guild.id, interaction.user.id)
    embed.set_footer(text=f"Your balance: {coins:,} coins")
    
    await interaction.response.send_message(embed=embed)

@tree.command(name="buy", description="💰 Buy Poké Balls from the shop")
@app_commands.describe(
    item="Which Poké Ball to buy",
    amount="How many to buy"
)
@app_commands.choices(item=[
    app_commands.Choice(name="🔴 Poké Ball (100 coins)", value="pokeball"),
    app_commands.Choice(name="🔵 Great Ball (300 coins)", value="greatball"),
    app_commands.Choice(name="🟡 Ultra Ball (600 coins)", value="ultraball")
])
async def buy(interaction: discord.Interaction, item: app_commands.Choice[str], amount: int):
    """Buy items from shop"""
    await interaction.response.defer(ephemeral=True)
    
    if amount <= 0:
        await interaction.followup.send("❌ Amount must be positive!", ephemeral=True)
        return
    
    server_id = interaction.guild.id
    user_id = interaction.user.id
    
    ball_type = item.value
    ball_data = POKEBALL_DATA[ball_type]
    total_cost = ball_data["price"] * amount
    
    coins = get_coins(server_id, user_id)
    
    if coins < total_cost:
        await interaction.followup.send(f"❌ Insufficient funds! You need {total_cost:,} coins but have {coins:,}.", ephemeral=True)
        return
    
    # Deduct coins and add balls
    set_coins(server_id, user_id, coins - total_cost)
    inventory = get_inventory(server_id, user_id)
    inventory[ball_type] = inventory.get(ball_type, 0) + amount
    
    new_coins = get_coins(server_id, user_id)
    
    embed = discord.Embed(
        title="✅ Purchase Successful!",
        description=f"You bought **{amount}x {ball_data['emoji']} {ball_data['name']}** for **{total_cost:,}** coins!\n\n💰 Remaining: **{new_coins:,}** coins",
        color=Colors.SUCCESS,
        timestamp=datetime.now(timezone.utc)
    )
    
    await interaction.followup.send(embed=embed, ephemeral=True)
    asyncio.create_task(batch_save_database())

@tree.command(name="pokemon", description="📋 View your Pokémon collection")
async def pokemon_list(interaction: discord.Interaction, user: Optional[discord.Member] = None):
    """View Pokémon collection"""
    target_user = user or interaction.user
    server_id = interaction.guild.id
    user_id = target_user.id
    
    pokemon_list = get_pokemon_list(server_id, user_id)
    
    if not pokemon_list:
        embed = discord.Embed(
            title="📋 Pokémon Collection",
            description=f"**{target_user.display_name}** hasn't caught any Pokémon yet!\n\nUse `/catch` to start your journey!",
            color=Colors.INFO
        )
        await interaction.response.send_message(embed=embed)
        return
    
    # Group by Pokémon name
    pokemon_counts = {}
    for p in pokemon_list:
        name = p["name"]
        if name not in pokemon_counts:
            pokemon_counts[name] = {"count": 0, "data": POKEMON_DATA[name]}
        pokemon_counts[name]["count"] += 1
    
    embed = discord.Embed(
        title=f"📋 {target_user.display_name}'s Pokémon",
        description=f"**Total: {len(pokemon_list)} Pokémon**",
        color=Colors.PRIMARY,
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_thumbnail(url=target_user.display_avatar.url)
    
    # Sort by rarity then count
    rarity_order = {"legendary": 0, "rare": 1, "uncommon": 2, "common": 3}
    sorted_pokemon = sorted(
        pokemon_counts.items(),
        key=lambda x: (rarity_order[x[1]["data"]["rarity"]], -x[1]["count"])
    )
    
    pokemon_text = ""
    for name, info in sorted_pokemon[:15]:
        data = info["data"]
        rarity_emoji = {"common": "⚪", "uncommon": "🟢", "rare": "🔵", "legendary": "🟣"}
        pokemon_text += f"{rarity_emoji[data['rarity']]} **{name}** x{info['count']} - {data['type']}\n"
    
    embed.description = pokemon_text or "No Pokémon yet!"
    embed.set_footer(text=f"Use /trade to exchange Pokémon with others!")
    
    await interaction.response.send_message(embed=embed)

@tree.command(name="daily", description="🎁 Claim daily coins")
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
                description=f"Come back in **{hours}h {minutes}m**!",
                color=Colors.WARNING
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
    
    daily_amount = random.randint(300, 500)
    coins = get_coins(server_id, user_id)
    set_coins(server_id, user_id, coins + daily_amount)
    user_daily[server_id][user_id] = now.isoformat()
    
    new_coins = get_coins(server_id, user_id)
    
    embed = discord.Embed(
        title="🎁 Daily Reward Claimed!",
        description=f"You received **{daily_amount:,} coins**!\n\n💰 Total: **{new_coins:,} coins**",
        color=Colors.SUCCESS,
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_footer(text="Come back in 24 hours!")
    
    await interaction.followup.send(embed=embed)
    asyncio.create_task(batch_save_database())

@bot.event
async def on_ready():
    """Bot startup"""
    logging.info(f"🚀 PokéVerse logged in as {bot.user}")
    
    await load_database()
    
    try:
        synced = await tree.sync()
        logging.info(f"✅ Synced {len(synced)} slash commands")
    except Exception as e:
        logging.error(f"❌ Failed to sync commands: {e}")
    
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.playing,
            name="PokéVerse | /catch"
        )
    )
    
    logging.info(f"🎮 PokéVerse is ready!")

# Start bot
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN is not set.")

keep_alive()
bot.run(DISCORD_TOKEN)