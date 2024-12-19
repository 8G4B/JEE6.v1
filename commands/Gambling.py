import discord
from discord.ext import commands, tasks

from datetime import datetime
import json
import os
import secrets
import random
import threading
import asyncio

# 최소배팅액
MIN_BET = 100
MIN_JACKPOT_BET = 1000

# 최대배팅액
MAX_BET = 100_000_000_000_000 

# 잭팟 초기화
INITIAL_JACKPOT = 1_000_000

# 쿨타임
JACKPOT_WIN_COOLDOWN = 1800  
GAME_COOLDOWN = 5
WORK_COOLDOWN = 60

INCOME_TAX_BRACKETS = [ # 종합소득세
    (1_000_000_000_000_000, 0.45),
    (  500_000_000_000_000, 0.42),
    (  300_000_000_000_000, 0.40),
    (  150_000_000_000_000, 0.38),
    (   88_000_000_000_000, 0.35),
    (   50_000_000_000_000, 0.24),
    (   14_000_000_000_000, 0.15),
    (    5_000_000_000_000, 0.06),
    (0, 0)                
]

# 증권거래세
SECURITIES_TRANSACTION_TAX_BRACKETS = [ 
    (30_000_000_000_000, 0.02),
    (10_000_000_000_000, 0.01),
    (0, 0.005)
]

# 증여세
GIFT_TAX_BRACKETS = [ 
    (30_000_000_000_000, 0.15),
    (10_000_000_000_000, 0.125),
    ( 5_000_000_000_000, 0.10),
    ( 1_000_000_000_000, 0.075),
    (0, 0.05)             
]

# 배수
COIN_MULTIPLIER_RANGE = (0.6, 1.7)
DICE_MULTIPLIER_RANGE = (4.6, 5.7)
BLACKJACK_MULTIPLIER_RANGE = (1.5, 2.5)

# !도박.노동
WORK_REWARD_RANGE = (100, 2000)

# 리셋시간
UNIT_TIMES = [ (7, 30),
    (12, 30),
    (18, 30)
]

# TODO: 리팩토링.. 제발..

class Gambling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cooldowns = {}
        self.balances = {}
        self.jackpot = 0
        self.data_file = 'gambling_data.json'
        self.locks = {}
        self.global_lock = threading.RLock()
        self.blackjack_players = set()
        self._load_data()
        
        self.reset_jackpot.start()
    
    def _create_error_embed(self, description: str) -> discord.Embed:
        return discord.Embed(
            title="❗ 오류",
            description=description,
            color=discord.Color.red()
        )

    def _calculate_tax(self, income: int, game_type: str = None) -> int:
        if income <= 0:
            return 0
            
        if game_type in ["coin", "dice", "blackjack"]:
            for threshold, rate in self.SECURITIES_TRANSACTION_TAX_BRACKETS:
                if income > threshold:
                    return int(income * rate)
            return 0
            
        for threshold, rate in self.INCOME_TAX_BRACKETS:
            if income > threshold:
                return int(income * rate)
        return 0

    def _calculate_gift_tax(self, amount: int) -> int:
        for threshold, rate in self.GIFT_TAX_BRACKETS:
            if amount > threshold:
                return int(amount * rate)
        return 0
    
    @tasks.loop(seconds=1)
    async def reset_jackpot(self):
        now = datetime.now()
        for hour, minute in self.UNIT_TIMES:
            if now.hour == hour and now.minute == minute:
                self.jackpot = self.INITIAL_JACKPOT
                self._save_data()
                return discord.Embed(
                    title="🎰 잭팟 리셋",
                    description="잭팟이 100만원으로 리셋되었습니다.",
                    color=discord.Color.green()
                )

    def _get_lock(self, user_id) -> threading.RLock:
        if user_id not in self.locks:
            self.locks[user_id] = threading.RLock()
        return self.locks[user_id]

    def _load_data(self):
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    self.balances = {int(k): v for k, v in data.get('balances', {}).items()}
                    self.jackpot = data.get('jackpot', 0)
        except Exception as e:
            print(f"_load_data: {e}")

    def _save_data(self):
        try:
            data = {
                'balances': self.balances,
                'jackpot': self.jackpot
            }
            with open(self.data_file, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            print(f"_save_data: {e}")

    def _validate_bet(self, bet, user_id=None):
        if isinstance(bet, str) and bet == "올인" and user_id is not None:
            bet = self.balances.get(user_id, 0)
            
        if (bet is None) or (bet < self.MIN_BET):
            return self._create_error_embed("100원 이상 베팅하세요")
            
        if bet >= self.MAX_BET:
            return self._create_error_embed("100조원 이상 베팅할 수 없습니다")
            
        return None

    def _validate_coin_guess(self, guess):
        if guess not in ["앞", "뒤"]:
            return self._create_error_embed("**'앞'**이랑 **'뒤'**만 입력해라...")
        return None

    def _validate_dice_guess(self, guess):
        if guess not in [str(i) for i in range(1, 7)]:
            return self._create_error_embed("**1부터 6까지 숫자**만 입력해라...")
        return None

    def _play_game(self, author_id, author_name, guess, result, bet, multiplier, game_type):
        lock = self._get_lock(author_id)
        if not lock.acquire(timeout=5):
            return self._create_error_embed("서버 이슈")
        
        try:
            is_correct = (guess == result)
            if is_correct:
                winnings = int(bet * multiplier)
            else:
                winnings = -bet
            
            
            if is_correct:
                tax_rate = self._calculate_tax(winnings, game_type) / winnings if winnings > 0 else 0
                tax = int(winnings * tax_rate)
                winnings_after_tax = winnings - tax
                current_balance = self.balances.get(author_id, 0)
                self.balances[author_id] = current_balance + winnings_after_tax
            else:
                current_balance = self.balances.get(author_id, 0)
                self.balances[author_id] = current_balance + winnings
                
            self._save_data()
            return self._create_game_embed(author_name, is_correct, guess, result, bet, winnings_after_tax if is_correct else winnings, author_id, game_type, tax if is_correct else None)
        finally:
            lock.release()

    def _check_game_cooldown(self, user_id, game_type):
        current_time = datetime.now()
        cooldown_key = f"{game_type}_{user_id}"
        last_used = self.cooldowns.get(cooldown_key)
        
        if last_used:
            cooldown_time = self.JACKPOT_WIN_COOLDOWN if game_type == "jackpot_win" else self.GAME_COOLDOWN
            if (current_time - last_used).total_seconds() < cooldown_time:
                remaining = cooldown_time - int((current_time - last_used).total_seconds())
                minutes = remaining // 60
                seconds = remaining % 60
                time_str = f"{minutes}분 {seconds}초" if minutes > 0 else f"{seconds}초"
                return discord.Embed(
                    title="⏳️ 쿨타임",
                    description=f"{time_str} 후에 다시 시도해주세요.",
                    color=discord.Color.red()
                )
        
        if game_type != "jackpot_win":
            self.cooldowns[cooldown_key] = current_time
        return None

    def _get_card_value(self, card: str) -> int:
        if card in ['J', 'Q', 'K']:
            return 10
        elif card == 'A':
            return 11
        return int(card)

    def _calculate_hand_value(self, hand: list[str]) -> int:
        value = 0
        aces = 0
        
        for card in hand:
            if card == 'A':
                aces += 1
            else:
                value += self._get_card_value(card)
                
        for _ in range(aces):
            if value + 11 <= 21:
                value += 11
            else:
                value += 1
                
        return value

    async def cog_check(self, ctx):
        if ctx.author.id in self.blackjack_players and ctx.command.name == "도박.블랙잭":
            await ctx.reply(embed=self._create_error_embed("이미 블랙잭 게임이 진행 중입니다."))
            return False
        return True

    @commands.command(name="도박.블랙잭", description="블랙잭")
    async def blackjack(self, ctx, bet: str = None):
        if cooldown_embed := self._check_game_cooldown(ctx.author.id, "blackjack"):
            await ctx.reply(embed=cooldown_embed)
            return
            
        if bet == "올인":
            bet = self.balances.get(ctx.author.id, 0)
        else:
            try:
                bet = int(bet) if bet is not None else None
            except ValueError:
                bet = None
                
        if error_embed := self._validate_bet(bet, ctx.author.id):
            await ctx.reply(embed=error_embed)
            return
            
        if bet > self.balances.get(ctx.author.id, 0):
            await ctx.reply(embed=self._create_error_embed("돈이 부족해..."))
            return
            
        self.blackjack_players.add(ctx.author.id)
            
        cards = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A'] * 4
        random.shuffle(cards)
        
        player_hand = [cards.pop(), cards.pop()]
        dealer_hand = [cards.pop(), cards.pop()]
        
        player_value = self._calculate_hand_value(player_hand)
        dealer_value = self._calculate_hand_value(dealer_hand)
        
        embed = discord.Embed(
            title=f"🃏 {ctx.author.name}의 블랙잭",
            description=f"{ctx.author.name}의 패: {' '.join(player_hand)} (합계: {player_value})\nJEE6의 패: {dealer_hand[0]} ?",
            color=discord.Color.blue()
        )
        embed.add_field(name="선택", value="👊 Hit 또는 🛑 Stand", inline=False)
        
        game_message = await ctx.reply(embed=embed)
        await game_message.add_reaction("👊")  
        await game_message.add_reaction("🛑")  
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["👊", "🛑"] and reaction.message.id == game_message.id
            
        while True:
            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
                await reaction.remove(user) 
                
                if str(reaction.emoji) == "👊":
                    player_hand.append(cards.pop())
                    player_value = self._calculate_hand_value(player_hand)
                    
                    if player_value > 21:
                        with self._get_lock(ctx.author.id):
                            current_balance = self.balances.get(ctx.author.id, 0)
                            self.balances[ctx.author.id] = current_balance - bet
                            self._save_data()
                            
                        embed = discord.Embed(
                            title=f"🃏 {ctx.author.name} 버스트!",
                            description=f"{ctx.author.name}의 패: {' '.join(player_hand)} (합계: {player_value})\nJEE6의 패: {' '.join(dealer_hand)} (합계: {dealer_value})\n## 수익: {bet:,}원 × -1 = -{bet:,}원\n- 재산: {self.balances[ctx.author.id]:,}원",
                            color=discord.Color.red()
                        )
                        await game_message.edit(embed=embed)
                        self.blackjack_players.remove(ctx.author.id)  
                        return
                        
                    embed = discord.Embed(
                        title=f"🃏 {ctx.author.name}의 블랙잭",
                        description=f"{ctx.author.name}의 패: {' '.join(player_hand)} (합계: {player_value})\nJEE6의 패: {dealer_hand[0]} ?",
                        color=discord.Color.blue()
                    )
                    embed.add_field(name="선택", value="👊 Hit 또는 🛑 Stand", inline=False)
                    await game_message.edit(embed=embed)
                    
                elif str(reaction.emoji) == "🛑":
                    while dealer_value < 17:
                        dealer_hand.append(cards.pop())
                        dealer_value = self._calculate_hand_value(dealer_hand)
                        
                    with self._get_lock(ctx.author.id):
                        current_balance = self.balances.get(ctx.author.id, 0)
                        
                        if dealer_value > 21 or player_value > dealer_value:
                            multiplier = random.uniform(*self.BLACKJACK_MULTIPLIER_RANGE) if player_value == 21 else 1
                            winnings = int(bet * multiplier)
                            tax = self._calculate_tax(winnings, "blackjack")
                            winnings_after_tax = winnings - tax
                            self.balances[ctx.author.id] = current_balance + winnings_after_tax
                            
                            embed = discord.Embed(
                                title=f"🃏 {ctx.author.name} 승리",
                                description=f"{ctx.author.name}의 패: {' '.join(player_hand)} (합계: {player_value})\nJEE6의 패: {' '.join(dealer_hand)} (합계: {dealer_value})\n## 수익: {bet:,}원 × {multiplier:.2f} = {winnings:,}원(세금: {tax:,}원)\n- 재산: {self.balances[ctx.author.id]:,}원",
                                color=discord.Color.green()
                            )
                        elif player_value < dealer_value or player_value == dealer_value:
                            self.balances[ctx.author.id] = current_balance - bet
                            embed = discord.Embed(
                                title=f"🃏 {ctx.author.name} {'패배' if player_value < dealer_value else '무승부'}",
                                description=f"{ctx.author.name}의 패: {' '.join(player_hand)} (합계: {player_value})\nJEE6의 패: {' '.join(dealer_hand)} (합계: {dealer_value})\n## 수익: {bet:,}원 × -1 = -{bet:,}원\n- 재산: {self.balances[ctx.author.id]:,}원",
                                color=discord.Color.red()
                            )
                            
                        self._save_data()
                        await game_message.edit(embed=embed)
                        self.blackjack_players.remove(ctx.author.id)  
                        return
                        
            except asyncio.TimeoutError:
                embed = discord.Embed(
                    title="⏳️ 시간 초과",
                    description="30초 동안 응답이 없어 취소됐어요",
                    color=discord.Color.red()
                )
                await game_message.edit(embed=embed)
                self.blackjack_players.remove(ctx.author.id) 
                return

    @commands.command(name="도박.동전", description="동전 던지기")
    async def coin(self, ctx, guess: str = None, bet: str = None):
        if cooldown_embed := self._check_game_cooldown(ctx.author.id, "coin"):
            embed = cooldown_embed
        elif error_embed := self._validate_coin_guess(guess):
            embed = error_embed
        else:
            if bet == "올인":
                bet = self.balances.get(ctx.author.id, 0)
            else:
                try:
                    bet = int(bet) if bet is not None else None
                except ValueError:
                    bet = None
                    
            if error_embed := self._validate_bet(bet, ctx.author.id):
                embed = error_embed
            elif bet > self.balances.get(ctx.author.id, 0):
                embed = self._create_error_embed("돈이 부족해...")
            else:
                result = secrets.choice(["앞", "뒤"])
                embed = self._play_game(ctx.author.id, ctx.author.name, guess, result, bet, random.uniform(*self.COIN_MULTIPLIER_RANGE), "coin")
        await ctx.reply(embed=embed)

    @commands.command(name="도박.주사위", description="주사위")
    async def dice(self, ctx, guess: str = None, bet: str = None):
        if cooldown_embed := self._check_game_cooldown(ctx.author.id, "dice"):
            embed = cooldown_embed
        elif error_embed := self._validate_dice_guess(guess):
            embed = error_embed
        else:
            if bet == "올인":
                bet = self.balances.get(ctx.author.id, 0)
            else:
                try:
                    bet = int(bet) if bet is not None else None
                except ValueError:
                    bet = None
                    
            if error_embed := self._validate_bet(bet, ctx.author.id):
                embed = error_embed
            elif bet > self.balances.get(ctx.author.id, 0):
                embed = self._create_error_embed("돈이 부족해...")
            else:
                result = secrets.choice([str(i) for i in range(1, 7)])
                embed = self._play_game(ctx.author.id, ctx.author.name, guess, result, bet, random.uniform(*self.DICE_MULTIPLIER_RANGE), "dice")
        await ctx.reply(embed=embed)

    @commands.command(name="도박.잭팟", description="잭팟")
    async def jackpot(self, ctx, bet: str = None):
        if cooldown_embed := self._check_game_cooldown(ctx.author.id, "jackpot"):
            await ctx.reply(embed=cooldown_embed)
            return
            
        if cooldown_embed := self._check_game_cooldown(ctx.author.id, "jackpot_win"):
            await ctx.reply(embed=cooldown_embed)
            return
            
        if bet == "올인":
            bet = self.balances.get(ctx.author.id, 0)
        else:
            try:
                bet = int(bet) if bet is not None else None
            except ValueError:
                bet = None
            
        if bet is None or bet < self.MIN_JACKPOT_BET:
            await ctx.reply(embed=self._create_error_embed("1,000원 이상 베팅하세요"))
            return
            
        if bet >= self.MAX_BET:  
            await ctx.reply(embed=self._create_error_embed("100조원 이상 베팅할 수 없습니다"))
            return
            
        with self._get_lock(ctx.author.id):
            current_balance = self.balances.get(ctx.author.id, 0)
            min_bet = current_balance // 100  # 재산의 1프로
            
            if bet > current_balance:
                await ctx.reply(embed=self._create_error_embed("돈이 부족해..."))
                return
                
            if bet < min_bet:
                await ctx.reply(embed=self._create_error_embed(f"현재 재산의 1% 이상 베팅하세요. (최소 {min_bet:,}원)"))
                return
                
            self.balances[ctx.author.id] = current_balance - bet
            self.jackpot += bet
            
            if secrets.randbelow(100) <= 1:
                winnings = self.jackpot // 10
                tax = self._calculate_tax(winnings)
                winnings_after_tax = winnings - tax
                self.balances[ctx.author.id] = current_balance - bet + winnings_after_tax
                self.jackpot = self.jackpot - winnings  
                self.cooldowns[f"jackpot_win_{ctx.author.id}"] = datetime.now()
                embed = discord.Embed(
                    title=f"🎉 {ctx.author.name} 당첨",
                    description=f"- 현재 잭팟: {self.jackpot:,}원(-{winnings:,}) \n## 수익: {winnings_after_tax:,}원(세금: {tax:,}원)\n- 재산: {self.balances[ctx.author.id]:,}원(+{winnings_after_tax:,})",
                    color=discord.Color.gold()
                )
            else:
                embed = discord.Embed(
                    title=f"🎰 {ctx.author.name} 잭팟 실패ㅋ",
                    description=f"\n- 현재 잭팟: {self.jackpot:,}원 \n## 수익: -{bet:,}원\n- 재산: {self.balances[ctx.author.id]:,}원",
                    color=discord.Color.red()
                )
            
            self._save_data()
            await ctx.reply(embed=embed)

    @commands.command(name="도박.노동", aliases=['도박.일', '도박.돈'], description="도박.노동")
    async def get_money(self, ctx):
        with self._get_lock(ctx.author.id):
            current_time = datetime.now()
            last_used = self.cooldowns.get(ctx.author.id)
            
            if last_used and (current_time - last_used).total_seconds() < self.WORK_COOLDOWN:
                remaining = self.WORK_COOLDOWN - int((current_time - last_used).total_seconds())
                embed = discord.Embed(
                    title="힘들어서 쉬는 중 ㅋ",
                    description=f"{remaining}초 후에 다시 시도해주세요.",
                    color=discord.Color.red()
                )
            else:
                amount = random.randint(*self.WORK_REWARD_RANGE)
                self.balances[ctx.author.id] = self.balances.get(ctx.author.id, 0) + amount
                embed = discord.Embed(
                    title=f"☭ {ctx.author.name} 노동",
                    description=f"정당한 노동을 통해 {amount:,}원을 벌었다. \n- 재산: {self.balances.get(ctx.author.id, 0):,}원(+{amount:,})",
                    color=discord.Color.green()
                )
                self.cooldowns[ctx.author.id] = current_time
                self._save_data()  
            
            await ctx.reply(embed=embed)

    @commands.command(name="도박.지갑", aliases=['도박.잔액', '도박.직바'], description="잔액 확인")
    async def check_balance(self, ctx):
        with self._get_lock(ctx.author.id):
            balance = self.balances.get(ctx.author.id, 0)
            embed = discord.Embed(
                title=f"💰 {ctx.author.name}의 지갑",
                description=f"현재 잔액: {balance:,}원",
                color=discord.Color.blue()
            )
            await ctx.reply(embed=embed)

    @commands.command(name="도박.랭킹", description="랭킹")
    async def ranking(self, ctx):
        with self.global_lock:
            sorted_balances = sorted(self.balances.items(), key=lambda item: item[1], reverse=True)
            top_3 = sorted_balances[:3]
            
            description_lines = []
            for i, (user_id, balance) in enumerate(top_3):
                user = await self.bot.fetch_user(user_id)
                description_lines.append(f"{i+1}. {user.name}: {balance:,}원")
            
            description = "\n".join(description_lines)
            
            embed = discord.Embed(
                title="🏅 상위 3명 랭킹",
                description=description if description else "랭킹이 없습니다.",
                color=discord.Color.blue()
            )
            await ctx.reply(embed=embed)
        
    @commands.command(name="도박.전체랭킹", description="전체 랭킹")
    async def all_ranking(self, ctx):
        with self.global_lock:
            sorted_balances = sorted(self.balances.items(), key=lambda item: item[1], reverse=True)
            
            description_lines = []
            for i, (user_id, balance) in enumerate(sorted_balances):
                user = await self.bot.fetch_user(user_id)
                description_lines.append(f"{i+1}. {user.name}: {balance:,}원")
                
            description = "\n".join(description_lines)

            embed = discord.Embed(
                title="🏅 전체 랭킹", 
                description=description,
                color=discord.Color.blue()
            )
            await ctx.reply(embed=embed)

    @commands.command(name="도박.송금", description="송금")
    async def transfer(self, ctx, recipient: discord.Member = None, amount: str = None):
        if recipient is None or amount is None:
            await ctx.reply(embed=self._create_error_embed("!도박.송금 [유저] [금액] <-- 이렇게 써"))
            return

        if amount == "올인":
            amount = self.balances.get(ctx.author.id, 0)
        else:
            try:
                amount = int(amount)
            except ValueError:
                await ctx.reply(embed=self._create_error_embed("올바른 금액을 입력하세요"))
                return

        if amount <= self.MIN_JACKPOT_BET:
            await ctx.reply(embed=self._create_error_embed("1,000원 이하는 송금할 수 없습니다."))
            return
            
        if amount >= self.MAX_BET:  
            await ctx.reply(embed=self._create_error_embed("100조원 이상 송금할 수 없습니다"))
            return

        with self._get_lock(ctx.author.id), self._get_lock(recipient.id):
            sender_balance = self.balances.get(ctx.author.id, 0)
            
            if amount > sender_balance:
                await ctx.reply(embed=self._create_error_embed("돈이 부족해..."))
                return

            tax = self._calculate_gift_tax(amount)
            amount_after_tax = amount - tax
            
            self.balances[ctx.author.id] = sender_balance - amount
            self.balances[recipient.id] = self.balances.get(recipient.id, 0) + amount_after_tax
            self.jackpot += tax
            
            embed = discord.Embed(
                title="💸 송금 완료",
                description=f"{ctx.author.name} → {recipient.name}\n## {amount:,}원 송금(세금: {tax:,}원)\n- 잔액: {self.balances[ctx.author.id]:,}원",
                color=discord.Color.green()
            )
            
            self._save_data()
            await ctx.reply(embed=embed)

    def _create_game_embed(self, author_name, is_correct, guess, result, bet=None, winnings=None, author_id=None, game_type=None, tax=None):
        title = f"{'🪙' if game_type == 'coin' else '🎲' if game_type == 'dice' else '🎰'} {author_name} {'맞음 ㄹㅈㄷ' if is_correct else '틀림ㅋ'}"
        color = discord.Color.green() if is_correct else discord.Color.red()
        
        description_parts = [
            f"- 예측: {guess}",
            f"- 결과: {result}"
        ]
        
        if bet is not None and is_correct:
            multiplier = round((winnings + (tax or 0)) / bet, 2) if winnings > 0 else -1
            balance = self.balances.get(author_id, 0)
            sign = '+' if winnings > 0 else ''
            
            description_parts.extend([
                f"## 수익: {bet:,}원 × {multiplier} = {winnings:,}원(세금: {tax:,}원)" if tax else f"## 수익: {bet:,}원 × {multiplier} = {winnings:,}원",
                f"- 재산: {balance:,}원({sign}{winnings:,})"
            ])
        elif bet is not None:
            multiplier = -1
            balance = self.balances.get(author_id, 0)
            
            description_parts.extend([
                f"## 수익: {bet:,}원 × {multiplier} = {winnings:,}원",
                f"- 재산: {balance:,}원({winnings:,})"
            ])
            
        description = "\n".join(description_parts)
            
        return discord.Embed(
            title=title,
            description=description,
            color=color
        )