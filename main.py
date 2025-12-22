import discord
from discord.ext import commands, tasks
from discord import app_commands
from discord.ui import View, Button, Modal, TextInput
import json
import os
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List
import random
import asyncio
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Database channel ID (change this to your database channel)
DATABASE_CHANNEL_ID = 1234567890123456789  # REPLACE WITH YOUR CHANNEL ID

# Bot branding colors
class Colors:
    PRIMARY = 0xFF6B6B  # Pokemon Red
    SUCCESS = 0x51CF66  # Pokemon Green
    WARNING = 0xFFD43B  # Pokemon Yellow
    DANGER = 0xFF6B6B   # Red
    INFO = 0x4DABF7     # Blue
    RARE = 0xCC5DE8     # Purple for rare Pokemon

# Pokemon database with images
POKEMON_DATA = {
    # Generation 1 - Kanto (1-25)
    "Bulbasaur": {"type": "Grass/Poison", "hp": 45, "attack": 49, "defense": 49, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/1.png"},
    "Ivysaur": {"type": "Grass/Poison", "hp": 60, "attack": 62, "defense": 63, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/2.png"},
    "Venusaur": {"type": "Grass/Poison", "hp": 80, "attack": 82, "defense": 83, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/3.png"},
    "Charmander": {"type": "Fire", "hp": 39, "attack": 52, "defense": 43, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/4.png"},
    "Charmeleon": {"type": "Fire", "hp": 58, "attack": 64, "defense": 58, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/5.png"},
    "Charizard": {"type": "Fire/Flying", "hp": 78, "attack": 84, "defense": 78, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/6.png"},
    "Squirtle": {"type": "Water", "hp": 44, "attack": 48, "defense": 65, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/7.png"},
    "Wartortle": {"type": "Water", "hp": 59, "attack": 63, "defense": 80, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/8.png"},
    "Blastoise": {"type": "Water", "hp": 79, "attack": 83, "defense": 100, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/9.png"},
    "Caterpie": {"type": "Bug", "hp": 45, "attack": 30, "defense": 35, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/10.png"},
    "Metapod": {"type": "Bug", "hp": 50, "attack": 20, "defense": 55, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/11.png"},
    "Butterfree": {"type": "Bug/Flying", "hp": 60, "attack": 45, "defense": 50, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/12.png"},
    "Weedle": {"type": "Bug/Poison", "hp": 40, "attack": 35, "defense": 30, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/13.png"},
    "Kakuna": {"type": "Bug/Poison", "hp": 45, "attack": 25, "defense": 50, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/14.png"},
    "Beedrill": {"type": "Bug/Poison", "hp": 65, "attack": 90, "defense": 40, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/15.png"},
    "Pidgey": {"type": "Normal/Flying", "hp": 40, "attack": 45, "defense": 40, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/16.png"},
    "Pidgeotto": {"type": "Normal/Flying", "hp": 63, "attack": 60, "defense": 55, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/17.png"},
    "Pidgeot": {"type": "Normal/Flying", "hp": 83, "attack": 80, "defense": 75, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/18.png"},
    "Rattata": {"type": "Normal", "hp": 30, "attack": 56, "defense": 35, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/19.png"},
    "Raticate": {"type": "Normal", "hp": 55, "attack": 81, "defense": 60, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/20.png"},
    "Spearow": {"type": "Normal/Flying", "hp": 40, "attack": 60, "defense": 30, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/21.png"},
    "Fearow": {"type": "Normal/Flying", "hp": 65, "attack": 90, "defense": 65, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/22.png"},
    "Ekans": {"type": "Poison", "hp": 35, "attack": 60, "defense": 44, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/23.png"},
    "Arbok": {"type": "Poison", "hp": 60, "attack": 95, "defense": 69, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/24.png"},
    "Pikachu": {"type": "Electric", "hp": 35, "attack": 55, "defense": 40, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/25.png"},
    
    # Generation 1 - Kanto (26-50)
    "Raichu": {"type": "Electric", "hp": 60, "attack": 90, "defense": 55, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/26.png"},
    "Sandshrew": {"type": "Ground", "hp": 50, "attack": 75, "defense": 85, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/27.png"},
    "Sandslash": {"type": "Ground", "hp": 75, "attack": 100, "defense": 110, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/28.png"},
    "Nidoran♀": {"type": "Poison", "hp": 55, "attack": 47, "defense": 52, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/29.png"},
    "Nidorina": {"type": "Poison", "hp": 70, "attack": 62, "defense": 67, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/30.png"},
    "Nidoqueen": {"type": "Poison/Ground", "hp": 90, "attack": 92, "defense": 87, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/31.png"},
    "Nidoran♂": {"type": "Poison", "hp": 46, "attack": 57, "defense": 40, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/32.png"},
    "Nidorino": {"type": "Poison", "hp": 61, "attack": 72, "defense": 57, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/33.png"},
    "Nidoking": {"type": "Poison/Ground", "hp": 81, "attack": 102, "defense": 77, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/34.png"},
    "Clefairy": {"type": "Fairy", "hp": 70, "attack": 45, "defense": 48, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/35.png"},
    "Clefable": {"type": "Fairy", "hp": 95, "attack": 70, "defense": 73, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/36.png"},
    "Vulpix": {"type": "Fire", "hp": 38, "attack": 41, "defense": 40, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/37.png"},
    "Ninetales": {"type": "Fire", "hp": 73, "attack": 76, "defense": 75, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/38.png"},
    "Jigglypuff": {"type": "Normal/Fairy", "hp": 115, "attack": 45, "defense": 20, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/39.png"},
    "Wigglytuff": {"type": "Normal/Fairy", "hp": 140, "attack": 70, "defense": 45, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/40.png"},
    "Zubat": {"type": "Poison/Flying", "hp": 40, "attack": 45, "defense": 35, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/41.png"},
    "Golbat": {"type": "Poison/Flying", "hp": 75, "attack": 80, "defense": 70, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/42.png"},
    "Oddish": {"type": "Grass/Poison", "hp": 45, "attack": 50, "defense": 55, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/43.png"},
    "Gloom": {"type": "Grass/Poison", "hp": 60, "attack": 65, "defense": 70, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/44.png"},
    "Vileplume": {"type": "Grass/Poison", "hp": 75, "attack": 80, "defense": 85, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/45.png"},
    "Paras": {"type": "Bug/Grass", "hp": 35, "attack": 70, "defense": 55, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/46.png"},
    "Parasect": {"type": "Bug/Grass", "hp": 60, "attack": 95, "defense": 80, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/47.png"},
    "Venonat": {"type": "Bug/Poison", "hp": 60, "attack": 55, "defense": 50, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/48.png"},
    "Venomoth": {"type": "Bug/Poison", "hp": 70, "attack": 65, "defense": 60, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/49.png"},
    "Diglett": {"type": "Ground", "hp": 10, "attack": 55, "defense": 25, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/50.png"},
    
    # Generation 1 - Kanto (51-75)
    "Dugtrio": {"type": "Ground", "hp": 35, "attack": 100, "defense": 50, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/51.png"},
    "Meowth": {"type": "Normal", "hp": 40, "attack": 45, "defense": 35, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/52.png"},
    "Persian": {"type": "Normal", "hp": 65, "attack": 70, "defense": 60, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/53.png"},
    "Psyduck": {"type": "Water", "hp": 50, "attack": 52, "defense": 48, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/54.png"},
    "Golduck": {"type": "Water", "hp": 80, "attack": 82, "defense": 78, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/55.png"},
    "Mankey": {"type": "Fighting", "hp": 40, "attack": 80, "defense": 35, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/56.png"},
    "Primeape": {"type": "Fighting", "hp": 65, "attack": 105, "defense": 60, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/57.png"},
    "Growlithe": {"type": "Fire", "hp": 55, "attack": 70, "defense": 45, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/58.png"},
    "Arcanine": {"type": "Fire", "hp": 90, "attack": 110, "defense": 80, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/59.png"},
    "Poliwag": {"type": "Water", "hp": 40, "attack": 50, "defense": 40, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/60.png"},
    "Poliwhirl": {"type": "Water", "hp": 65, "attack": 65, "defense": 65, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/61.png"},
    "Poliwrath": {"type": "Water/Fighting", "hp": 90, "attack": 95, "defense": 95, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/62.png"},
    "Abra": {"type": "Psychic", "hp": 25, "attack": 20, "defense": 15, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/63.png"},
    "Kadabra": {"type": "Psychic", "hp": 40, "attack": 35, "defense": 30, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/64.png"},
    "Alakazam": {"type": "Psychic", "hp": 55, "attack": 50, "defense": 45, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/65.png"},
    "Machop": {"type": "Fighting", "hp": 70, "attack": 80, "defense": 50, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/66.png"},
    "Machoke": {"type": "Fighting", "hp": 80, "attack": 100, "defense": 70, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/67.png"},
    "Machamp": {"type": "Fighting", "hp": 90, "attack": 130, "defense": 80, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/68.png"},
    "Bellsprout": {"type": "Grass/Poison", "hp": 50, "attack": 75, "defense": 35, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/69.png"},
    "Weepinbell": {"type": "Grass/Poison", "hp": 65, "attack": 90, "defense": 50, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/70.png"},
    "Victreebel": {"type": "Grass/Poison", "hp": 80, "attack": 105, "defense": 65, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/71.png"},
    "Tentacool": {"type": "Water/Poison", "hp": 40, "attack": 40, "defense": 35, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/72.png"},
    "Tentacruel": {"type": "Water/Poison", "hp": 80, "attack": 70, "defense": 65, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/73.png"},
    "Geodude": {"type": "Rock/Ground", "hp": 40, "attack": 80, "defense": 100, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/74.png"},
    "Graveler": {"type": "Rock/Ground", "hp": 55, "attack": 95, "defense": 115, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/75.png"},
    
    # Generation 1 - Kanto (76-100)
    "Golem": {"type": "Rock/Ground", "hp": 80, "attack": 120, "defense": 130, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/76.png"},
    "Ponyta": {"type": "Fire", "hp": 50, "attack": 85, "defense": 55, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/77.png"},
    "Rapidash": {"type": "Fire", "hp": 65, "attack": 100, "defense": 70, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/78.png"},
    "Slowpoke": {"type": "Water/Psychic", "hp": 90, "attack": 65, "defense": 65, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/79.png"},
    "Slowbro": {"type": "Water/Psychic", "hp": 95, "attack": 75, "defense": 110, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/80.png"},
    "Magnemite": {"type": "Electric/Steel", "hp": 25, "attack": 35, "defense": 70, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/81.png"},
    "Magneton": {"type": "Electric/Steel", "hp": 50, "attack": 60, "defense": 95, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/82.png"},
    "Farfetch'd": {"type": "Normal/Flying", "hp": 52, "attack": 90, "defense": 55, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/83.png"},
    "Doduo": {"type": "Normal/Flying", "hp": 35, "attack": 85, "defense": 45, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/84.png"},
    "Dodrio": {"type": "Normal/Flying", "hp": 60, "attack": 110, "defense": 70, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/85.png"},
    "Seel": {"type": "Water", "hp": 65, "attack": 45, "defense": 55, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/86.png"},
    "Dewgong": {"type": "Water/Ice", "hp": 90, "attack": 70, "defense": 80, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/87.png"},
    "Grimer": {"type": "Poison", "hp": 80, "attack": 80, "defense": 50, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/88.png"},
    "Muk": {"type": "Poison", "hp": 105, "attack": 105, "defense": 75, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/89.png"},
    "Shellder": {"type": "Water", "hp": 30, "attack": 65, "defense": 100, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/90.png"},
    "Cloyster": {"type": "Water/Ice", "hp": 50, "attack": 95, "defense": 180, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/91.png"},
    "Gastly": {"type": "Ghost/Poison", "hp": 30, "attack": 35, "defense": 30, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/92.png"},
    "Haunter": {"type": "Ghost/Poison", "hp": 45, "attack": 50, "defense": 45, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/93.png"},
    "Gengar": {"type": "Ghost/Poison", "hp": 60, "attack": 65, "defense": 60, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/94.png"},
    "Onix": {"type": "Rock/Ground", "hp": 35, "attack": 45, "defense": 160, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/95.png"},
    "Drowzee": {"type": "Psychic", "hp": 60, "attack": 48, "defense": 45, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/96.png"},
    "Hypno": {"type": "Psychic", "hp": 85, "attack": 73, "defense": 70, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/97.png"},
    "Krabby": {"type": "Water", "hp": 30, "attack": 105, "defense": 90, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/98.png"},
    "Kingler": {"type": "Water", "hp": 55, "attack": 130, "defense": 115, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/99.png"},
    "Voltorb": {"type": "Electric", "hp": 40, "attack": 30, "defense": 50, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/100.png"},
    
    # Generation 1 - Kanto (101-110)
    "Electrode": {"type": "Electric", "hp": 60, "attack": 50, "defense": 70, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/101.png"},
    "Exeggcute": {"type": "Grass/Psychic", "hp": 60, "attack": 40, "defense": 80, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/102.png"},
    "Exeggutor": {"type": "Grass/Psychic", "hp": 95, "attack": 95, "defense": 85, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/103.png"},
    "Cubone": {"type": "Ground", "hp": 50, "attack": 50, "defense": 95, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/104.png"},
    "Marowak": {"type": "Ground", "hp": 60, "attack": 80, "defense": 110, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/105.png"},
    "Hitmonlee": {"type": "Fighting", "hp": 50, "attack": 120, "defense": 53, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/106.png"},
    "Hitmonchan": {"type": "Fighting", "hp": 50, "attack": 105, "defense": 79, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/107.png"},
    "Lickitung": {"type": "Normal", "hp": 90, "attack": 55, "defense": 75, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/108.png"},
    "Koffing": {"type": "Poison", "hp": 40, "attack": 65, "defense": 95, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/109.png"},
    "Weezing": {"type": "Poison", "hp": 65, "attack": 90, "defense": 120, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/110.png"},
}

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="/", intents=intents)
tree = bot.tree

# Global data structures
player_data = {}  # {user_id: {pokemon: {}, inventory: {}, cooldowns: {}}}
active_trades = {}  # {trade_id: {}}
pending_database_save = False
last_database_save = datetime.now()

# Cooldown tracking
user_cooldowns = {}  # {user_id: last_command_time}

def check_cooldown(user_id: int) -> bool:
    """Check if user can use a command (3 second cooldown)"""
    now = datetime.now()
    if user_id in user_cooldowns:
        time_since_last = (now - user_cooldowns[user_id]).total_seconds()
        if time_since_last < 3:
            return False
    user_cooldowns[user_id] = now
    return True

def get_player_data(user_id: int) -> Dict:
    """Get player data, initialize if doesn't exist"""
    if user_id not in player_data:
        player_data[user_id] = {
            "pokemon": None,
            "current_hp": 0,
            "inventory": {
                "pokeball": 5,
                "greatball": 0,
                "ultraball": 0,
                "potion": 3
            },
            "money": 1000
        }
    return player_data[user_id]

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

async def save_database():
    """Save data to database channel"""
    try:
        db_channel = bot.get_channel(DATABASE_CHANNEL_ID)
        if not db_channel:
            logging.error(f"Database channel {DATABASE_CHANNEL_ID} not found!")
            return

        data = {
            "player_data": {str(k): v for k, v in player_data.items()},
            "timestamp": datetime.now().isoformat()
        }
        
        json_str = json.dumps(data, indent=2)
        content = f"```json\n{json_str}\n```"
        
        await db_channel.send(content)
        logging.info("✅ Database saved successfully")
        
    except Exception as e:
        logging.error(f"Error saving database: {e}")

async def load_database():
    """Load data from database channel"""
    global player_data
    
    try:
        db_channel = bot.get_channel(DATABASE_CHANNEL_ID)
        if not db_channel:
            logging.error(f"Database channel {DATABASE_CHANNEL_ID} not found!")
            return

        async for message in db_channel.history(limit=50):
            if message.author == bot.user and message.content.startswith("```json"):
                try:
                    json_content = message.content[7:-3].strip()
                    data = json.loads(json_content)
                    
                    if "player_data" in data:
                        player_data_raw = data.get("player_data", {})
                        player_data = {int(k): v for k, v in player_data_raw.items()}
                        logging.info(f"✅ Loaded data for {len(player_data)} players")
                        return
                        
                except json.JSONDecodeError:
                    continue
                    
    except Exception as e:
        logging.error(f"Error loading database: {e}")

# Catch Animation Embed
def create_catch_animation_embed(pokemon_name: str, ball_type: str) -> discord.Embed:
    """Create animated catch sequence embed"""
    embed = discord.Embed(
        title="🎯 Catching Pokemon!",
        description=f"You threw a **{ball_type}**!\n\n"
                    f"```\n"
                    f"  (O)  ←━━━━━━  ʕ •ᴥ•ʔ\n"
                    f"                {pokemon_name}\n"
                    f"```\n"
                    f"The ball is wobbling...",
        color=Colors.WARNING
    )
    return embed

def create_catch_success_embed(pokemon_name: str, pokemon_data: Dict) -> discord.Embed:
    """Create successful catch embed"""
    embed = discord.Embed(
        title="🎉 Gotcha!",
        description=f"**{pokemon_name}** was caught!\n\n"
                    f"**Type:** {pokemon_data['type']}\n"
                    f"**HP:** {pokemon_data['hp']}\n"
                    f"**Attack:** {pokemon_data['attack']}\n"
                    f"**Defense:** {pokemon_data['defense']}",
        color=Colors.SUCCESS
    )
    embed.set_thumbnail(url=pokemon_data['image'])
    embed.set_footer(text="CosmoCatch • Your Pokemon Adventure", icon_url="https://i.imgur.com/AfFp7pu.png")
    return embed

def create_catch_fail_embed(pokemon_name: str) -> discord.Embed:
    """Create failed catch embed"""
    embed = discord.Embed(
        title="❌ Oh no!",
        description=f"**{pokemon_name}** broke free!\nTry again with a better ball!",
        color=Colors.DANGER
    )
    return embed

# Battle Animation
def create_battle_animation_embed(attacker_name: str, defender_name: str, damage: int) -> discord.Embed:
    """Create battle animation embed"""
    embed = discord.Embed(
        title="⚔️ Battle!",
        description=f"```\n"
                    f"{attacker_name}  ━━━━━★  {defender_name}\n"
                    f"        💥 {damage} damage!\n"
                    f"```",
        color=Colors.WARNING
    )
    return embed

# Trade Request View
class TradeRequestView(View):
    def __init__(self, initiator_id: int, target_id: int, pokemon_offered: str):
        super().__init__(timeout=60)
        self.initiator_id = initiator_id
        self.target_id = target_id
        self.pokemon_offered = pokemon_offered
        self.accepted = False
        
    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success, emoji="✅")
    async def accept_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.target_id:
            await interaction.response.send_message("❌ This trade is not for you!", ephemeral=True)
            return
            
        self.accepted = True
        self.stop()
        
        # Show form for target to select their Pokemon
        modal = TradePokemonModal(self.initiator_id, self.target_id, self.pokemon_offered)
        await interaction.response.send_modal(modal)
        
    @discord.ui.button(label="Deny", style=discord.ButtonStyle.danger, emoji="❌")
    async def deny_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.target_id:
            await interaction.response.send_message("❌ This trade is not for you!", ephemeral=True)
            return
            
        embed = discord.Embed(
            title="❌ Trade Declined",
            description=f"<@{self.target_id}> declined the trade.",
            color=Colors.DANGER
        )
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()

# Trade Pokemon Selection Modal
class TradePokemonModal(Modal, title="Trade Pokemon"):
    pokemon_name = TextInput(
        label="Your Pokemon Name",
        placeholder="Enter the exact name of your Pokemon",
        required=True,
        max_length=50
    )
    
    def __init__(self, initiator_id: int, target_id: int, pokemon_offered: str):
        super().__init__()
        self.initiator_id = initiator_id
        self.target_id = target_id
        self.pokemon_offered = pokemon_offered
        
    async def on_submit(self, interaction: discord.Interaction):
        target_pokemon = self.pokemon_name.value.strip()
        
        # Get player data
        initiator_data = get_player_data(self.initiator_id)
        target_data = get_player_data(self.target_id)
        
        # Validate Pokemon
        if not target_data["pokemon"] or target_data["pokemon"]["name"] != target_pokemon:
            await interaction.response.send_message(
                f"❌ You don't have a Pokemon named **{target_pokemon}**!",
                ephemeral=True
            )
            return
            
        # Execute trade
        initiator_pokemon = initiator_data["pokemon"]
        target_pokemon_data = target_data["pokemon"]
        
        initiator_data["pokemon"] = target_pokemon_data
        initiator_data["current_hp"] = target_pokemon_data["hp"]
        target_data["pokemon"] = initiator_pokemon
        target_data["current_hp"] = initiator_pokemon["hp"]
        
        embed = discord.Embed(
            title="✅ Trade Successful!",
            description=f"<@{self.initiator_id}> traded **{self.pokemon_offered}** ↔️ **{target_pokemon}** with <@{self.target_id}>",
            color=Colors.SUCCESS
        )
        embed.set_footer(text="CosmoCatch • Your Pokemon Adventure")
        
        await interaction.response.send_message(embed=embed)
        asyncio.create_task(batch_save_database())

# PVP Battle View
class BattleRequestView(View):
    def __init__(self, challenger_id: int, opponent_id: int, wager_amount: int):
        super().__init__(timeout=60)
        self.challenger_id = challenger_id
        self.opponent_id = opponent_id
        self.wager_amount = wager_amount
        
    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success, emoji="✅")
    async def accept_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.opponent_id:
            await interaction.response.send_message("❌ This battle is not for you!", ephemeral=True)
            return
            
        # Show form for opponent to confirm their Pokemon
        modal = BattlePokemonModal(self.challenger_id, self.opponent_id, self.wager_amount)
        await interaction.response.send_modal(modal)
        self.stop()
        
    @discord.ui.button(label="Deny", style=discord.ButtonStyle.danger, emoji="❌")
    async def deny_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.opponent_id:
            await interaction.response.send_message("❌ This battle is not for you!", ephemeral=True)
            return
            
        embed = discord.Embed(
            title="❌ Battle Declined",
            description=f"<@{self.opponent_id}> declined the battle.",
            color=Colors.DANGER
        )
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()

# Battle Pokemon Confirmation Modal
class BattlePokemonModal(Modal, title="Confirm Battle Pokemon"):
    pokemon_name = TextInput(
        label="Your Pokemon Name",
        placeholder="Enter your Pokemon's name to confirm",
        required=True,
        max_length=50
    )
    
    def __init__(self, challenger_id: int, opponent_id: int, wager_amount: int):
        super().__init__()
        self.challenger_id = challenger_id
        self.opponent_id = opponent_id
        self.wager_amount = wager_amount
        
    async def on_submit(self, interaction: discord.Interaction):
        # Get player data
        challenger_data = get_player_data(self.challenger_id)
        opponent_data = get_player_data(self.opponent_id)
        
        # Validate Pokemon
        if not opponent_data["pokemon"] or opponent_data["pokemon"]["name"] != self.pokemon_name.value.strip():
            await interaction.response.send_message(
                f"❌ You don't have a Pokemon named **{self.pokemon_name.value}**!",
                ephemeral=True
            )
            return
            
        # Start battle
        await interaction.response.defer()
        
        # Battle animation
        p1_pokemon = challenger_data["pokemon"]
        p2_pokemon = opponent_data["pokemon"]
        
        p1_hp = challenger_data["current_hp"]
        p2_hp = opponent_data["current_hp"]
        
        battle_log = []
        turn = 1
        
        while p1_hp > 0 and p2_hp > 0:
            # Attacker and defender alternate
            if turn % 2 == 1:
                attacker = p1_pokemon
                defender = p2_pokemon
                damage = max(1, attacker["attack"] - defender["defense"] // 2)
                p2_hp -= damage
                battle_log.append(f"Turn {turn}: {attacker['name']} attacks {defender['name']} for {damage} damage! ({defender['name']} HP: {max(0, p2_hp)})")
            else:
                attacker = p2_pokemon
                defender = p1_pokemon
                damage = max(1, attacker["attack"] - defender["defense"] // 2)
                p1_hp -= damage
                battle_log.append(f"Turn {turn}: {attacker['name']} attacks {defender['name']} for {damage} damage! ({defender['name']} HP: {max(0, p1_hp)})")
            
            # Animation delay
            await asyncio.sleep(5)
            
            # Send animation embed
            anim_embed = create_battle_animation_embed(attacker["name"], defender["name"], damage)
            await interaction.followup.send(embed=anim_embed)
            
            turn += 1
            
            # Prevent infinite battles
            if turn > 20:
                break
        
        # Determine winner
        if p1_hp > p2_hp:
            winner_id = self.challenger_id
            loser_id = self.opponent_id
            winner_pokemon = p1_pokemon["name"]
        else:
            winner_id = self.opponent_id
            loser_id = self.challenger_id
            winner_pokemon = p2_pokemon["name"]
        
        # Transfer money
        winner_data = get_player_data(winner_id)
        loser_data = get_player_data(loser_id)
        
        winner_data["money"] += self.wager_amount
        loser_data["money"] -= self.wager_amount
        
        # Update HP
        challenger_data["current_hp"] = max(0, p1_hp)
        opponent_data["current_hp"] = max(0, p2_hp)
        
        # Victory embed
        victory_embed = discord.Embed(
            title="🏆 Battle Complete!",
            description=f"**Winner:** <@{winner_id}>'s {winner_pokemon}\n\n"
                        f"**Wager:** 💰 {self.wager_amount} coins\n\n"
                        f"**Battle Log:**\n```\n" + "\n".join(battle_log[-5:]) + "\n```",
            color=Colors.SUCCESS
        )
        victory_embed.set_footer(text="CosmoCatch • Your Pokemon Adventure")
        
        await interaction.followup.send(embed=victory_embed)
        asyncio.create_task(batch_save_database())

# Commands

@tree.command(name="catch", description="Catch a wild Pokemon!")
@app_commands.describe(
    ball="Choose your Pokeball",
)
@app_commands.choices(ball=[
    app_commands.Choice(name="Pokeball", value="pokeball"),
    app_commands.Choice(name="Greatball", value="greatball"),
    app_commands.Choice(name="Ultraball", value="ultraball")
])
async def catch(interaction: discord.Interaction, ball: str):
    """Catch a wild Pokemon"""
    # Cooldown check
    if not check_cooldown(interaction.user.id):
        await interaction.response.send_message("⏳ Please wait 3 seconds between commands!", ephemeral=True)
        return
    
    player = get_player_data(interaction.user.id)
    
    # Check if already has a Pokemon
    if player["pokemon"]:
        embed = discord.Embed(
            title="❌ Already Have Pokemon",
            description=f"You already have **{player['pokemon']['name']}**!\nYou can only have one Pokemon at a time.",
            color=Colors.DANGER
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Check ball inventory
    if player["inventory"].get(ball, 0) <= 0:
        await interaction.response.send_message(f"❌ You don't have any **{ball}s**!", ephemeral=True)
        return
    
    # Deduct ball
    player["inventory"][ball] -= 1
    
    # Random Pokemon
    pokemon_name = random.choice(list(POKEMON_DATA.keys()))
    pokemon_data = POKEMON_DATA[pokemon_name].copy()
    pokemon_data["name"] = pokemon_name
    
    # Catch rate based on ball
    catch_rates = {
        "pokeball": 0.5,
        "greatball": 0.7,
        "ultraball": 0.9
    }
    
    # Show animation
    await interaction.response.send_message(embed=create_catch_animation_embed(pokemon_name, ball.capitalize()))
    
    # Wait for animation
    await asyncio.sleep(5)
    
    # Determine success
    success = random.random() < catch_rates[ball]
    
    if success:
        # Caught!
        player["pokemon"] = pokemon_data
        player["current_hp"] = pokemon_data["hp"]
        
        await interaction.edit_original_response(embed=create_catch_success_embed(pokemon_name, pokemon_data))
        asyncio.create_task(batch_save_database())
    else:
        # Failed
        await interaction.edit_original_response(embed=create_catch_fail_embed(pokemon_name))

@tree.command(name="pokemon", description="View your Pokemon")
async def pokemon_cmd(interaction: discord.Interaction):
    """View your Pokemon"""
    if not check_cooldown(interaction.user.id):
        await interaction.response.send_message("⏳ Please wait 3 seconds between commands!", ephemeral=True)
        return
    
    player = get_player_data(interaction.user.id)
    
    if not player["pokemon"]:
        embed = discord.Embed(
            title="❌ No Pokemon",
            description="You don't have a Pokemon yet! Use `/catch` to catch one!",
            color=Colors.DANGER
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    poke = player["pokemon"]
    current_hp = player["current_hp"]
    max_hp = poke["hp"]
    hp_percentage = (current_hp / max_hp) * 100
    
    # HP bar
    hp_bar_length = 20
    filled = int((current_hp / max_hp) * hp_bar_length)
    hp_bar = "█" * filled + "░" * (hp_bar_length - filled)
    
    embed = discord.Embed(
        title=f"✨ {poke['name']}",
        description=f"**Type:** {poke['type']}\n\n"
                    f"**HP:** {current_hp}/{max_hp} ({hp_percentage:.1f}%)\n"
                    f"```{hp_bar}```\n"
                    f"**Attack:** {poke['attack']}\n"
                    f"**Defense:** {poke['defense']}",
        color=Colors.PRIMARY
    )
    embed.set_thumbnail(url=poke['image'])
    embed.set_footer(text="CosmoCatch • Your Pokemon Adventure")
    
    await interaction.response.send_message(embed=embed)

@tree.command(name="inventory", description="View your inventory")
async def inventory(interaction: discord.Interaction):
    """View inventory"""
    if not check_cooldown(interaction.user.id):
        await interaction.response.send_message("⏳ Please wait 3 seconds between commands!", ephemeral=True)
        return
    
    player = get_player_data(interaction.user.id)
    inv = player["inventory"]
    
    embed = discord.Embed(
        title="🎒 Inventory",
        description=f"**💰 Money:** {player['money']} coins\n\n"
                    f"**Pokéballs:**\n"
                    f"🔴 Pokéball: {inv['pokeball']}\n"
                    f"🔵 Great Ball: {inv['greatball']}\n"
                    f"🟡 Ultra Ball: {inv['ultraball']}\n\n"
                    f"**Items:**\n"
                    f"🧪 Potion: {inv['potion']}",
        color=Colors.INFO
    )
    embed.set_footer(text="CosmoCatch • Your Pokemon Adventure")
    
    await interaction.response.send_message(embed=embed)

@tree.command(name="shop", description="View the shop")
async def shop(interaction: discord.Interaction):
    """View shop"""
    if not check_cooldown(interaction.user.id):
        await interaction.response.send_message("⏳ Please wait 3 seconds between commands!", ephemeral=True)
        return
    
    embed = discord.Embed(
        title="🏪 CosmoCatch Shop",
        description="Use `/buy <item> <amount>` to purchase items!\n\n"
                    "**Pokéballs:**\n"
                    "🔴 `pokeball` - 100 coins\n"
                    "🔵 `greatball` - 300 coins\n"
                    "🟡 `ultraball` - 500 coins\n\n"
                    "**Items:**\n"
                    "🧪 `potion` - 200 coins (Restores 50 HP)",
        color=Colors.WARNING
    )
    embed.set_footer(text="CosmoCatch • Your Pokemon Adventure")
    
    await interaction.response.send_message(embed=embed)

@tree.command(name="buy", description="Buy items from the shop")
@app_commands.describe(
    item="Item to buy",
    amount="Amount to buy"
)
@app_commands.choices(item=[
    app_commands.Choice(name="Pokeball", value="pokeball"),
    app_commands.Choice(name="Greatball", value="greatball"),
    app_commands.Choice(name="Ultraball", value="ultraball"),
    app_commands.Choice(name="Potion", value="potion")
])
async def buy(interaction: discord.Interaction, item: str, amount: int):
    """Buy items"""
    if not check_cooldown(interaction.user.id):
        await interaction.response.send_message("⏳ Please wait 3 seconds between commands!", ephemeral=True)
        return
    
    if amount <= 0:
        await interaction.response.send_message("❌ Amount must be positive!", ephemeral=True)
        return
    
    player = get_player_data(interaction.user.id)
    
    prices = {
        "pokeball": 100,
        "greatball": 300,
        "ultraball": 500,
        "potion": 200
    }
    
    total_cost = prices[item] * amount
    
    if player["money"] < total_cost:
        await interaction.response.send_message(
            f"❌ Not enough money! You need {total_cost} coins but only have {player['money']}.",
            ephemeral=True
        )
        return
    
    player["money"] -= total_cost
    player["inventory"][item] += amount
    
    embed = discord.Embed(
        title="✅ Purchase Successful!",
        description=f"Bought **{amount}x {item.capitalize()}** for **{total_cost} coins**!\n\n"
                    f"**Remaining Money:** {player['money']} coins",
        color=Colors.SUCCESS
    )
    
    await interaction.response.send_message(embed=embed)
    asyncio.create_task(batch_save_database())

@tree.command(name="potion", description="Use a potion to heal your Pokemon")
async def potion(interaction: discord.Interaction):
    """Use potion"""
    if not check_cooldown(interaction.user.id):
        await interaction.response.send_message("⏳ Please wait 3 seconds between commands!", ephemeral=True)
        return
    
    player = get_player_data(interaction.user.id)
    
    if not player["pokemon"]:
        await interaction.response.send_message("❌ You don't have a Pokemon!", ephemeral=True)
        return
    
    if player["inventory"]["potion"] <= 0:
        await interaction.response.send_message("❌ You don't have any potions!", ephemeral=True)
        return
    
    max_hp = player["pokemon"]["hp"]
    current_hp = player["current_hp"]
    
    if current_hp >= max_hp:
        await interaction.response.send_message("❌ Your Pokemon is already at full HP!", ephemeral=True)
        return
    
    # Use potion
    player["inventory"]["potion"] -= 1
    heal_amount = 50
    player["current_hp"] = min(max_hp, current_hp + heal_amount)
    
    embed = discord.Embed(
        title="🧪 Potion Used!",
        description=f"**{player['pokemon']['name']}** restored {heal_amount} HP!\n\n"
                    f"**HP:** {player['current_hp']}/{max_hp}",
        color=Colors.SUCCESS
    )
    
    await interaction.response.send_message(embed=embed)
    asyncio.create_task(batch_save_database())

@tree.command(name="trade", description="Trade your Pokemon with another user")
@app_commands.describe(
    user="User to trade with"
)
async def trade(interaction: discord.Interaction, user: discord.Member):
    """Trade Pokemon"""
    if not check_cooldown(interaction.user.id):
        await interaction.response.send_message("⏳ Please wait 3 seconds between commands!", ephemeral=True)
        return
    
    if user.id == interaction.user.id:
        await interaction.response.send_message("❌ You can't trade with yourself!", ephemeral=True)
        return
    
    if user.bot:
        await interaction.response.send_message("❌ You can't trade with bots!", ephemeral=True)
        return
    
    player = get_player_data(interaction.user.id)
    target_player = get_player_data(user.id)
    
    if not player["pokemon"]:
        await interaction.response.send_message("❌ You don't have a Pokemon to trade!", ephemeral=True)
        return
    
    if not target_player["pokemon"]:
        await interaction.response.send_message(f"❌ {user.mention} doesn't have a Pokemon!", ephemeral=True)
        return
    
    # Create trade request
    embed = discord.Embed(
        title="📦 Trade Request",
        description=f"{interaction.user.mention} wants to trade their **{player['pokemon']['name']}** with {user.mention}!\n\n"
                    f"{user.mention}, accept or deny?",
        color=Colors.INFO
    )
    
    view = TradeRequestView(interaction.user.id, user.id, player['pokemon']['name'])
    await interaction.response.send_message(embed=embed, view=view)

@tree.command(name="battle", description="Battle wild Pokemon or challenge another player")
@app_commands.describe(
    mode="Battle mode",
    user="User to battle (PVP only)",
    wager="Amount to wager (PVP only)"
)
@app_commands.choices(mode=[
    app_commands.Choice(name="Wild Pokemon", value="wild"),
    app_commands.Choice(name="Player vs Player", value="pvp")
])
async def battle(interaction: discord.Interaction, mode: str, user: Optional[discord.Member] = None, wager: Optional[int] = None):
    """Battle system"""
    if not check_cooldown(interaction.user.id):
        await interaction.response.send_message("⏳ Please wait 3 seconds between commands!", ephemeral=True)
        return
    
    player = get_player_data(interaction.user.id)
    
    if not player["pokemon"]:
        await interaction.response.send_message("❌ You don't have a Pokemon!", ephemeral=True)
        return
    
    if player["current_hp"] <= 0:
        await interaction.response.send_message("❌ Your Pokemon has fainted! Use a potion first!", ephemeral=True)
        return
    
    if mode == "wild":
        # Wild Pokemon battle
        await interaction.response.defer()
        
        # Random wild Pokemon
        wild_name = random.choice(list(POKEMON_DATA.keys()))
        wild_data = POKEMON_DATA[wild_name].copy()
        wild_data["name"] = wild_name
        wild_hp = wild_data["hp"]
        
        player_pokemon = player["pokemon"]
        player_hp = player["current_hp"]
        
        battle_log = []
        turn = 1
        
        # Battle loop
        while player_hp > 0 and wild_hp > 0:
            # Player attacks
            damage = max(1, player_pokemon["attack"] - wild_data["defense"] // 2)
            wild_hp -= damage
            battle_log.append(f"Turn {turn}: {player_pokemon['name']} attacks for {damage} damage! (Wild HP: {max(0, wild_hp)})")
            
            if wild_hp <= 0:
                break
            
            # Show animation
            await asyncio.sleep(5)
            anim_embed = create_battle_animation_embed(player_pokemon["name"], wild_name, damage)
            await interaction.followup.send(embed=anim_embed)
            
            # Wild attacks
            damage = max(1, wild_data["attack"] - player_pokemon["defense"] // 2)
            player_hp -= damage
            battle_log.append(f"Turn {turn}: {wild_name} attacks for {damage} damage! (Your HP: {max(0, player_hp)})")
            
            # Show animation
            await asyncio.sleep(5)
            anim_embed = create_battle_animation_embed(wild_name, player_pokemon["name"], damage)
            await interaction.followup.send(embed=anim_embed)
            
            turn += 1
            
            if turn > 15:
                break
        
        # Update player HP
        player["current_hp"] = max(0, player_hp)
        
        # Determine result
        if player_hp > 0:
            reward = random.randint(50, 200)
            player["money"] += reward
            
            embed = discord.Embed(
                title="🏆 Victory!",
                description=f"You defeated wild **{wild_name}**!\n\n"
                            f"**Reward:** 💰 {reward} coins\n\n"
                            f"**Your Pokemon HP:** {player['current_hp']}/{player_pokemon['hp']}",
                color=Colors.SUCCESS
            )
        else:
            embed = discord.Embed(
                title="💀 Defeated",
                description=f"Your **{player_pokemon['name']}** fainted!\n\n"
                            f"Use a potion to revive it!",
                color=Colors.DANGER
            )
        
        await interaction.followup.send(embed=embed)
        asyncio.create_task(batch_save_database())
        
    elif mode == "pvp":
        # PVP battle
        if not user:
            await interaction.response.send_message("❌ You must specify a user for PVP!", ephemeral=True)
            return
        
        if user.id == interaction.user.id:
            await interaction.response.send_message("❌ You can't battle yourself!", ephemeral=True)
            return
        
        if user.bot:
            await interaction.response.send_message("❌ You can't battle bots!", ephemeral=True)
            return
        
        if not wager:
            wager = 0
        
        if wager < 0:
            await interaction.response.send_message("❌ Wager must be positive!", ephemeral=True)
            return
        
        if player["money"] < wager:
            await interaction.response.send_message(f"❌ You don't have enough money to wager {wager} coins!", ephemeral=True)
            return
        
        target_player = get_player_data(user.id)
        
        if not target_player["pokemon"]:
            await interaction.response.send_message(f"❌ {user.mention} doesn't have a Pokemon!", ephemeral=True)
            return
        
        if target_player["current_hp"] <= 0:
            await interaction.response.send_message(f"❌ {user.mention}'s Pokemon has fainted!", ephemeral=True)
            return
        
        if target_player["money"] < wager:
            await interaction.response.send_message(f"❌ {user.mention} doesn't have enough money for this wager!", ephemeral=True)
            return
        
        # Create battle request
        embed = discord.Embed(
            title="⚔️ Battle Challenge!",
            description=f"{interaction.user.mention}'s **{player['pokemon']['name']}** challenges {user.mention}'s Pokemon!\n\n"
                        f"**Wager:** 💰 {wager} coins\n\n"
                        f"{user.mention}, accept or deny?",
            color=Colors.WARNING
        )
        
        view = BattleRequestView(interaction.user.id, user.id, wager)
        await interaction.response.send_message(embed=embed, view=view)

@tree.command(name="sell", description="Sell your Pokemon")
async def sell(interaction: discord.Interaction):
    """Sell Pokemon"""
    if not check_cooldown(interaction.user.id):
        await interaction.response.send_message("⏳ Please wait 3 seconds between commands!", ephemeral=True)
        return
    
    player = get_player_data(interaction.user.id)
    
    if not player["pokemon"]:
        await interaction.response.send_message("❌ You don't have a Pokemon to sell!", ephemeral=True)
        return
    
    # Calculate sell price
    poke = player["pokemon"]
    sell_price = (poke["hp"] + poke["attack"] + poke["defense"]) * 10
    
    # Sell Pokemon
    pokemon_name = poke["name"]
    player["pokemon"] = None
    player["current_hp"] = 0
    player["money"] += sell_price
    
    embed = discord.Embed(
        title="💰 Pokemon Sold",
        description=f"You sold **{pokemon_name}** for **{sell_price} coins**!\n\n"
                    f"**New Balance:** {player['money']} coins",
        color=Colors.SUCCESS
    )
    
    await interaction.response.send_message(embed=embed)
    asyncio.create_task(batch_save_database())

@bot.event
async def on_ready():
    """Bot startup"""
    logging.info(f"🚀 CosmoCatch logged in as {bot.user}")
    
    await load_database()
    
    try:
        synced = await tree.sync()
        logging.info(f"✅ Synced {len(synced)} commands")
    except Exception as e:
        logging.error(f"❌ Failed to sync commands: {e}")
    
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.playing,
            name="Pokemon Adventure | /catch"
        )
    )
    
    logging.info("🎊 CosmoCatch is ready!")

# Get token and run
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN is not set")

bot.run(DISCORD_TOKEN)
