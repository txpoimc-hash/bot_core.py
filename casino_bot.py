# casino_bot.py - Bot gambling con credits virtuali

import random
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Tuple

class CasinoGameBot:
    """Bot per giochi da casinò con credits virtuali"""
    
    GAMES = {
        'slots': {
            'name': '🎰 Slot Machine',
            'min_bet': 10,
            'max_bet': 1000,
            'house_edge': 0.05,  # 5% edge
            'description': 'Gira le slot e vinci moltiplicatori!'
        },
        'blackjack': {
            'name': '🃏 Blackjack',
            'min_bet': 50,
            'max_bet': 5000,
            'house_edge': 0.005,  # 0.5% edge con gioco perfetto
            'description': 'Batti il banco a 21!'
        },
        'roulette': {
            'name': '🎲 Roulette',
            'min_bet': 25,
            'max_bet': 2500,
            'house_edge': 0.0263,  # 2.63% edge
            'description': 'Scommetti su numeri, colori o combinazioni'
        },
        'dice': {
            'name': '🎯 Dice Duel',
            'min_bet': 5,
            'max_bet': 500,
            'house_edge': 0.01,  # 1% edge
            'description': 'Lancia i dadi contro il bot!'
        },
        'crash': {
            'name': '📈 Crash Game',
            'min_bet': 10,
            'max_bet': 2000,
            'house_edge': 0.03,  # 3% edge
            'description': 'Cash out prima che il moltiplicatore crash!'
        }
    }
    
    def __init__(self, bot_core):
        self.core = bot_core
        self.active_games = {}
        self.jackpot_pool = 0
        self.daily_bonus_amount = 100
        
    async def register_commands(self):
        """Registra comandi su entrambe le piattaforme"""
        
        # Discord commands
        @self.core.discord_bot.command(name="slots")
        async def discord_slots(ctx, bet: int):
            await self.play_game(ctx, "slots", bet, Platform.DISCORD)
        
        @self.core.discord_bot.command(name="blackjack")
        async def discord_blackjack(ctx, bet: int):
            await self.start_blackjack(ctx, bet, Platform.DISCORD)
        
        # Telegram commands
        from telegram.ext import CommandHandler
        
        self.core.telegram_app.add_handler(
            CommandHandler("slots", self.telegram_slots)
        )
        self.core.telegram_app.add_handler(
            CommandHandler("blackjack", self.telegram_blackjack)
        )
    
    async def play_game(self, ctx, game: str, bet: int, platform: Platform):
        """Esegue un gioco e gestisce vincite/perdite"""
        
        # Verifica bet valida
        game_config = self.GAMES[game]
        if bet < game_config['min_bet']:
            await self.send_message(ctx, f"❌ Bet minima: {game_config['min_bet']} credits", platform)
            return
        if bet > game_config['max_bet']:
            await self.send_message(ctx, f"❌ Bet massima: {game_config['max_bet']} credits", platform)
            return
        
        # Ottieni utente e verifica credits
        user = await self.get_user(ctx.author.id if platform == Platform.DISCORD else ctx.from_user.id, platform)
        if user.credits < bet:
            await self.send_message(ctx, f"❌ Non hai abbastanza credits! Hai solo {user.credits} credits", platform)
            return
        
        # Sottrai bet
        user.credits -= bet
        await self.update_user(user)
        
        # Determina risultato
        if game == "slots":
            result = await self.play_slots(bet)
        elif game == "dice":
            result = await self.play_dice(bet)
        elif game == "crash":
            result = await self.play_crash(bet)
        else:
            result = {'win': False, 'multiplier': 0, 'payout': 0}
        
        # Aggiorna credits
        if result['win']:
            user.credits += result['payout']
            await self.update_user(user)
            
            # Contribuisci al jackpot (1% delle vincite)
            jackpot_contribution = int(result['payout'] * 0.01)
            self.jackpot_pool += jackpot_contribution
            
            # Notifica vincita
            await self.send_message(ctx, 
                f"🎉 **VITTORIA!**\n"
                f"Bet: {bet} credits\n"
                f"Moltiplicatore: x{result['multiplier']}\n"
                f"Vincita: {result['payout']} credits\n"
                f"Nuovo saldo: {user.credits} credits",
                platform
            )
        else:
            await self.send_message(ctx,
                f"😢 **Sconfitta!**\n"
                f"Bet: {bet} credits\n"
                f"Hai perso! Riprova!\n"
                f"Nuovo saldo: {user.credits} credits",
                platform
            )
    
    async def play_slots(self, bet: int) -> Dict:
        """Slot machine con moltiplicatori"""
        
        # Genera risultati
        symbols = ['🍒', '🍋', '🍊', '🍇', '💎', '7️⃣']
        weights = [30, 25, 20, 15, 7, 3]  # Probabilità
        
        reels = []
        for _ in range(3):
            symbol = random.choices(symbols, weights=weights)[0]
            reels.append(symbol)
        
        # Calcola vincita
        multipliers = {
            ('7️⃣', '7️⃣', '7️⃣'): 50,
            ('💎', '💎', '💎'): 20,
            ('🍇', '🍇', '🍇'): 10,
            ('🍊', '🍊', '🍊'): 5,
            ('🍋', '🍋', '🍋'): 3,
            ('🍒', '🍒', '🍒'): 2,
        }
        
        result_key = tuple(reels)
        multiplier = multipliers.get(result_key, 0)
        
        # Doppia chance per due uguali
        if multiplier == 0 and len(set(reels)) == 2:
            # Due simboli uguali
            for symbol in set(reels):
                if reels.count(symbol) == 2:
                    if symbol == '7️⃣':
                        multiplier = 5
                    elif symbol == '💎':
                        multiplier = 3
                    elif symbol == '🍇':
                        multiplier = 2
                    else:
                        multiplier = 1.5
                    break
        
        win = multiplier > 0
        payout = int(bet * multiplier) if win else 0
        
        return {
            'win': win,
            'reels': reels,
            'multiplier': multiplier,
            'payout': payout
        }
    
    async def play_dice(self, bet: int) -> Dict:
        """Gioco dei dadi"""
        player_roll = random.randint(1, 6) + random.randint(1, 6)
        bot_roll = random.randint(1, 6) + random.randint(1, 6)
        
        if player_roll > bot_roll:
            multiplier = 2
            win = True
        elif player_roll == bot_roll:
            multiplier = 1.5  # Push
            win = True
        else:
            multiplier = 0
            win = False
        
        payout = int(bet * multiplier) if win else 0
        
        return {
            'win': win,
            'player_roll': player_roll,
            'bot_roll': bot_roll,
            'multiplier': multiplier,
            'payout': payout
        }
    
    async def play_crash(self, bet: int) -> Dict:
        """Gioco Crash con cashout automatico"""
        
        # Simula moltiplicatore crescente
        multiplier = 1.0
        crashed = False
        
        # Il moltiplicatore cresce in modo casuale
        while not crashed:
            multiplier *= random.uniform(1.01, 1.1)
            
            # Probabilità di crash aumenta col moltiplicatore
            crash_chance = 0.01 + (multiplier - 1) * 0.02
            if random.random() < crash_chance:
                crashed = True
                break
            
            # Limite massimo
            if multiplier > 10:
                multiplier = 10
                break
        
        # Cashout casuale (simula decisione giocatore)
        cashout_at = random.uniform(1.2, 3.0)
        
        if cashout_at < multiplier:
            win = True
            payout = int(bet * cashout_at)
            final_multiplier = cashout_at
        else:
            win = False
            payout = 0
            final_multiplier = 0
        
        return {
            'win': win,
            'crash_at': round(multiplier, 2),
            'cashout_at': round(cashout_at, 2),
            'multiplier': round(final_multiplier, 2),
            'payout': payout
        }
    
    async def start_blackjack(self, ctx, bet: int, platform: Platform):
        """Avvia una partita di Blackjack"""
        
        # Implementazione blackjack
        # ... (lunga, omessa per brevità)
        pass
    
    async def daily_bonus(self, ctx, platform: Platform):
        """Bonus giornaliero per fidelizzazione"""
        
        user_id = ctx.author.id if platform == Platform.DISCORD else ctx.from_user.id
        last_bonus_key = f"daily_bonus:{user_id}"
        
        # Verifica se già ritirato oggi
        last_bonus = await self.core.redis.get(last_bonus_key)
        if last_bonus:
            await self.send_message(ctx, "❌ Hai già ritirato il bonus oggi! Torna domani!", platform)
            return
        
        # Assegna bonus
        user = await self.get_user(user_id, platform)
        user.credits += self.daily_bonus_amount
        await self.update_user(user)
        
        # Salva timestamp
        await self.core.redis.setex(last_bonus_key, 86400, str(datetime.now()))
        
        await self.send_message(ctx, 
            f"🎁 **Bonus Giornaliero!**\n"
            f"Hai ricevuto {self.daily_bonus_amount} credits!\n"
            f"Nuovo saldo: {user.credits} credits",
            platform
        )
