# bot_core.py - Template universale per bot Discord+Telegram

import asyncio
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import json
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
import stripe
from web3 import Web3

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Platform(Enum):
    DISCORD = "discord"
    TELEGRAM = "telegram"
    BOTH = "both"

@dataclass
class User:
    id: str
    platform: Platform
    username: str
    credits: float = 0
    premium_until: Optional[int] = None
    settings: Dict[str, Any] = None

class BotCore:
    """Core universale per bot multipiattaforma"""
    
    def __init__(self, config_path: str = "config.json"):
        with open(config_path) as f:
            self.config = json.load(f)
        
        # Database
        self.engine = create_async_engine(
            self.config['database_url'],
            echo=True,
            pool_size=20,
            max_overflow=10
        )
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
        
        # Redis per cache e rate limiting
        self.redis = redis.from_url(self.config['redis_url'])
        
        # Web3 per crypto
        self.w3 = Web3(Web3.HTTPProvider(self.config['infura_url']))
        
        # Stripe per pagamenti
        stripe.api_key = self.config['stripe_secret_key']
        
        # Rate limiting
        self.rate_limiter = RateLimiter(self.redis)
        
        # Moduli funzionali
        self.modules: Dict[str, Any] = {}
        
    async def initialize(self):
        """Inizializza tutti i moduli"""
        logger.info("Initializing bot core...")
        
        # Carica moduli
        self.modules['payments'] = PaymentModule(self)
        self.modules['analytics'] = AnalyticsModule(self)
        self.modules['admin'] = AdminModule(self)
        
        # Connetti a Discord
        if self.config.get('discord_token'):
            await self.connect_discord()
        
        # Connetti a Telegram
        if self.config.get('telegram_token'):
            await self.connect_telegram()
        
        logger.info("Bot core initialized successfully")
    
    async def connect_discord(self):
        """Connessione a Discord con sharding"""
        import discord
        from discord.ext import commands
        
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        self.discord_bot = commands.Bot(
            command_prefix=self.config['discord_prefix'],
            intents=intents,
            shard_count=self.config.get('discord_shards', 1)
        )
        
        @self.discord_bot.event
        async def on_ready():
            logger.info(f"Discord bot connected as {self.discord_bot.user}")
        
        # Avvia in background
        asyncio.create_task(self.discord_bot.start(self.config['discord_token']))
    
    async def connect_telegram(self):
        """Connessione a Telegram"""
        from telegram.ext import Application, CommandHandler, MessageHandler, filters
        
        self.telegram_app = Application.builder().token(
            self.config['telegram_token']
        ).build()
        
        # Avvia in background
        asyncio.create_task(self.telegram_app.initialize())
        asyncio.create_task(self.telegram_app.start())

class RateLimiter:
    """Rate limiting avanzato con Redis"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def check_limit(self, user_id: str, action: str, 
                         max_requests: int, window: int) -> bool:
        """Controlla se l'utente ha superato il limite"""
        key = f"ratelimit:{user_id}:{action}"
        
        current = await self.redis.get(key)
        if current and int(current) >= max_requests:
            return False
        
        # Incrementa contatore
        pipe = self.redis.pipeline()
        await pipe.incr(key)
        await pipe.expire(key, window)
        await pipe.execute()
        
        return True

# config.json esempio
config_template = {
    "database_url": "postgresql+asyncpg://user:pass@localhost/botdb",
    "redis_url": "redis://localhost:6379/0",
    "infura_url": "https://mainnet.infura.io/v3/YOUR_KEY",
    "stripe_secret_key": "sk_live_...",
    "discord_token": "YOUR_DISCORD_BOT_TOKEN",
    "discord_prefix": "!",
    "telegram_token": "YOUR_TELEGRAM_BOT_TOKEN",
    "admin_ids": ["YOUR_DISCORD_ID", "YOUR_TELEGRAM_ID"],
    "premium_plans": {
        "monthly": {"price": 9.99, "credits": 1000},
        "yearly": {"price": 99.99, "credits": 12000}
    }
}
