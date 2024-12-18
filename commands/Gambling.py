import discord
from discord.ext import commands, tasks

from datetime import datetime
import json
import os
import secrets
import random
import threading

class Gambling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cooldowns = {}
        self.balances = {}
        self.jackpot = 0
        self.data_file = 'gambling_data.json'
        self.locks = {}
        self.global_lock = threading.RLock()
        self._load_data()
        
        self.reset_jackpot.start()

    def _calculate_tax(self, income):
        if income <= 0:
            return 0
            
        tax_brackets = [ ## 종합소득세
            (1000000000000000, 0.45),  
            (500000000000000, 0.42),   
            (300000000000000, 0.40),   
            (150000000000000, 0.38),   
            (88000000000000, 0.35),    
            (50000000000000, 0.24),    
            (14000000000000, 0.15),    
            (5000000000000, 0.06),
            (0, 0)                  
        ]
        
        for threshold, rate in tax_brackets:
            if income > threshold:
                return int(income * rate)
        return 0

    def _calculate_transfer_tax(self, amount):
        tax_brackets = [ ## 증여세
            (30000000000000, 0.15),  
            (10000000000000, 0.125), 
            (5000000000000, 0.10),   
            (1000000000000, 0.075), 
            (0, 0.05)                
        ]
        
        for threshold, rate in tax_brackets:
            if amount > threshold:
                return int(amount * rate)
        return 0
    
    @tasks.loop(seconds=1)
    async def reset_jackpot(self):
        now = datetime.now()
        if (
            (now.hour == 7 and now.minute == 30) or
            (now.hour == 12 and now.minute == 30) or 
            (now.hour == 18 and now.minute == 30)
        ):
            self.jackpot = 1000000
            self._save_data()
            return discord.Embed(
                title="🎰 잭팟 리셋",
                description="잭팟이 100만원으로 리셋되었습니다.",
                color=discord.Color.green()
            )

    def _get_lock(self, user_id):
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
            
        if bet is None or bet < 100:
            return discord.Embed(
                title="❗ 오류",
                description="100원 이상 베팅하세요",
                color=discord.Color.red()
            )
        if bet >= 100000000000000:  # 100조원
            return discord.Embed(
                title="❗ 오류",
                description="100조원 이상 베팅할 수 없습니다",
                color=discord.Color.red()
            )
        return None

    def _validate_coin_guess(self, guess):
        if guess not in ["앞", "뒤"]:
            return discord.Embed(
                title="❗ 오류", 
                description="**'앞'**이랑 **'뒤'**만 입력해라...",
                color=discord.Color.red()
            )
        return None

    def _validate_dice_guess(self, guess):
        if guess not in [str(i) for i in range(1, 7)]:
            return discord.Embed(
                title="❗ 오류",
                description="**1부터 6까지 숫자**만 입력해라...",
                color=discord.Color.red()
            )
        return None

    def _play_game(self, author_id, author_name, guess, result, bet, multiplier, game_type):
        lock = self._get_lock(author_id)
        if not lock.acquire(timeout=5):
            return discord.Embed(
                title="❗ 오류",
                description="서버 이슈",
                color=discord.Color.red()
            )
        
        try:
            is_correct = guess == result
            winnings = int(bet * multiplier) if is_correct else -bet
            
            if is_correct:
                tax_rate = self._calculate_tax(winnings) / winnings if winnings > 0 else 0
                tax = int(winnings * tax_rate)
                winnings_after_tax = winnings - tax
                current_balance = self.balances.get(author_id, 0)
                self.balances[author_id] = current_balance + winnings_after_tax
                self.jackpot += tax
            else:
                current_balance = self.balances.get(author_id, 0)
                self.balances[author_id] = current_balance + winnings
                self.jackpot += abs(winnings)
                
            self._save_data()
            return self._create_game_embed(author_name, is_correct, guess, result, bet, winnings_after_tax if is_correct else winnings, author_id, game_type, tax if is_correct else None)
        finally:
            lock.release()

    def _check_game_cooldown(self, user_id, game_type):
        current_time = datetime.now()
        cooldown_key = f"{game_type}_{user_id}"
        last_used = self.cooldowns.get(cooldown_key)
        
        if last_used:
            cooldown_time = 1800 if game_type == "jackpot_win" else 5
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
                embed = discord.Embed(
                    title="❗ 오류",
                    description="돈이 부족해...",
                    color=discord.Color.red()
                )
            else:
                result = secrets.choice(["앞", "뒤"])
                embed = self._play_game(ctx.author.id, ctx.author.name, guess, result, bet, random.uniform(0.6, 1.7), "coin")
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
                embed = discord.Embed(
                    title="❗ 오류",
                    description="돈이 부족해...",
                    color=discord.Color.red()
                )
            else:
                result = secrets.choice([str(i) for i in range(1, 7)])
                embed = self._play_game(ctx.author.id, ctx.author.name, guess, result, bet, random.uniform(4.6, 5.7), "dice")
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
            
        if bet is None or bet < 1000:
            embed = discord.Embed(
                title="❗ 오류",
                description="1,000원 이상 베팅하세요",
                color=discord.Color.red()
            )
            await ctx.reply(embed=embed)
            return
            
        if bet >= 100000000000000:  
            embed = discord.Embed(
                title="❗ 오류",
                description="100조원 이상 베팅할 수 없습니다",
                color=discord.Color.red()
            )
            await ctx.reply(embed=embed)
            return
            
        with self._get_lock(ctx.author.id):
            current_balance = self.balances.get(ctx.author.id, 0)
            min_bet = current_balance // 100  # 재산의 1프로
            
            if bet > current_balance:
                embed = discord.Embed(
                    title="❗ 오류",
                    description="돈이 부족해...",
                    color=discord.Color.red()
                )
                await ctx.reply(embed=embed)
                return
                
            if bet < min_bet:
                embed = discord.Embed(
                    title="❗ 오류",
                    description=f"현재 재산의 1% 이상 베팅하세요. (최소 {min_bet:,}원)",
                    color=discord.Color.red()
                )
                await ctx.reply(embed=embed)
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
            
            if last_used and (current_time - last_used).total_seconds() < 60:
                remaining = 60 - int((current_time - last_used).total_seconds())
                embed = discord.Embed(
                    title="힘들어서 쉬는 중 ㅋ",
                    description=f"{remaining}초 후에 다시 시도해주세요.",
                    color=discord.Color.red()
                )
            else:
                amount = random.randint(100, 2000)
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
            embed = discord.Embed(
                title="❗ 오류",
                description="!도박.송금 [유저] [금액] <-- 이렇게 써",
                color=discord.Color.red()
            )
            await ctx.reply(embed=embed)
            return

        if amount == "올인":
            amount = self.balances.get(ctx.author.id, 0)
        else:
            try:
                amount = int(amount)
            except ValueError:
                embed = discord.Embed(
                    title="❗ 오류",
                    description="올바른 금액을 입력하세요",
                    color=discord.Color.red()
                )
                await ctx.reply(embed=embed)
                return

        if amount <= 1000:
            embed = discord.Embed(
                title="❗ 오류",
                description="1,000원 이하는 송금할 수 없습니다.",
                color=discord.Color.red()
            )
            await ctx.reply(embed=embed)
            return
            
        if amount >= 100000000000000:  
            embed = discord.Embed(
                title="❗ 오류",
                description="100조원 이상 송금할 수 없습니다",
                color=discord.Color.red()
            )
            await ctx.reply(embed=embed)
            return

        with self._get_lock(ctx.author.id), self._get_lock(recipient.id):
            sender_balance = self.balances.get(ctx.author.id, 0)
            
            if amount > sender_balance:
                embed = discord.Embed(
                    title="❗ 오류",
                    description="돈이 부족해...",
                    color=discord.Color.red()
                )
                await ctx.reply(embed=embed)
                return

            tax = self._calculate_transfer_tax(amount)
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
