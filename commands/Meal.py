import discord
from discord.ext import commands
import meal_api_key
import requests
import json
from datetime import datetime, timedelta
from typing import Dict, Optional, List

ATPT_OFCDC_SC_CODE = 'F10' # 광주광역시교육청
SD_SCHUL_CODE = '7380292' # GSM 

NO_MEAL = "급식이 없습니다."

class RequestMeal:
    params = {
        'key': meal_api_key.MEAL_API_KEY,
        'type': 'json',
        'ATPT_OFCDC_SC_CODE': ATPT_OFCDC_SC_CODE, 
        'SD_SCHUL_CODE': SD_SCHUL_CODE,  
    }
    
    base_url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
    
    _cache: Dict[str, tuple[List, datetime]] = {}
    CACHE_DURATION = timedelta(hours=1)  
    
    @staticmethod
    def get_meal_info(date: str) -> Optional[List]:
        if date in RequestMeal._cache:
            cached_data, cache_time = RequestMeal._cache[date]
            if datetime.now() - cache_time < RequestMeal.CACHE_DURATION:
                return cached_data
            del RequestMeal._cache[date]
        
        params = RequestMeal.params.copy()
        params['MLSV_YMD'] = date
        
        try:
            response = requests.get(RequestMeal.base_url, params=params)
            data = response.json()
            
            if 'mealServiceDietInfo' in data:
                meals = data['mealServiceDietInfo'][1]['row']
                for meal in meals:  
                    meal['DDISH_NM'] = '\n'.join(f'- {dish.strip()}' for dish in meal['DDISH_NM'].replace('*', '').split('<br/>') if dish.strip())
                RequestMeal._cache[date] = (meals, datetime.now())
                return meals
            return None
            
        except (requests.RequestException, json.JSONDecodeError, KeyError):
            return None

class MealEmbed:
    @staticmethod
    def create_meal_embed(title: str, menu: str) -> discord.Embed:
        return discord.Embed(
            title=title,
            description=menu,
            color=discord.Color.orange()
        )
    
    @staticmethod
    def create_error_embed(description: str) -> discord.Embed:
        return discord.Embed(
            title="❗ 오류",
            description=description, 
            color=discord.Color.red()
        )

class MealService:
    def __init__(self):
        self.meal_request = RequestMeal()
    
    def get_current_meal(self, now: datetime) -> tuple[str, str]:
        today = now.strftime("%Y%m%d")
        current_hour = now.hour
        current_minute = now.minute
        
        meal_info = RequestMeal.get_meal_info(today)
        
        if not meal_info:
            return None, None
            
        if current_hour < 7 or (current_hour == 7 and current_minute < 30):
            menu = next((meal["DDISH_NM"] for meal in meal_info if meal["MMEAL_SC_CODE"] == "1"), NO_MEAL)
            title = "🍳 아침"
        elif current_hour < 12 or (current_hour == 12 and current_minute < 30):
            menu = next((meal["DDISH_NM"] for meal in meal_info if meal["MMEAL_SC_CODE"] == "2"), NO_MEAL)
            title = "🍚 점심"
        elif current_hour < 18 or (current_hour == 18 and current_minute < 30):
            menu = next((meal["DDISH_NM"] for meal in meal_info if meal["MMEAL_SC_CODE"] == "3"), NO_MEAL)
            title = "🍖 저녁"
        else:
            tomorrow = (now + timedelta(days=1)).strftime("%Y%m%d")
            tomorrow_meal_info = RequestMeal.get_meal_info(tomorrow)
            if tomorrow_meal_info:
                menu = next((meal["DDISH_NM"] for meal in tomorrow_meal_info if meal["MMEAL_SC_CODE"] == "1"), NO_MEAL)
                title = "🍳 내일 아침"
            else:
                menu = NO_MEAL
                title = "🍳 내일 아침"
                
        return title, menu
        
    def get_meal_by_type(self, date: str, meal_code: str, title: str) -> tuple[str, str]:
        meal_info = RequestMeal.get_meal_info(date)
        if not meal_info:
            return None, None
            
        menu = next((meal["DDISH_NM"] for meal in meal_info if meal["MMEAL_SC_CODE"] == meal_code), NO_MEAL)
        return title, menu

class Meal(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.meal_service = MealService()
    
    @commands.command(name='급식', description='급식 조회')
    async def meal(self, ctx):
        title, menu = self.meal_service.get_current_meal(datetime.now())
        
        if title and menu:
            embed = MealEmbed.create_meal_embed(title, menu)
        else:
            embed = MealEmbed.create_error_embed("나이스 API 이슈")
            
        await ctx.reply(embed=embed)
        
    @commands.command(name='급식.아침', aliases=['급식.조식'], description='아침 조회')
    async def breakfast(self, ctx):
        title, menu = self.meal_service.get_meal_by_type(
            datetime.now().strftime("%Y%m%d"),
            "1",
            "🍳 아침"
        )
        
        if title and menu:
            embed = MealEmbed.create_meal_embed(title, menu)
        else:
            embed = MealEmbed.create_error_embed("조식 정보를 가져올 수 없습니다.")
            
        await ctx.reply(embed=embed)
        
    @commands.command(name='급식.점심', aliases=['급식.중식'], description='점심 조회')
    async def lunch(self, ctx):
        title, menu = self.meal_service.get_meal_by_type(
            datetime.now().strftime("%Y%m%d"),
            "2", 
            "🍚 점심"
        )
        
        if title and menu:
            embed = MealEmbed.create_meal_embed(title, menu)
        else:
            embed = MealEmbed.create_error_embed("중식 정보를 가져올 수 없습니다.")
        
        await ctx.reply(embed=embed)
        
    @commands.command(name='급식.저녁', aliases=['급식.석식'], description='저녁 조회')
    async def dinner(self, ctx):
        title, menu = self.meal_service.get_meal_by_type(
            datetime.now().strftime("%Y%m%d"),
            "3",
            "🍖 저녁"
        )
        
        if title and menu:
            embed = MealEmbed.create_meal_embed(title, menu)
        else:
            embed = MealEmbed.create_error_embed("석식 정보를 가져올 수 없습니다.")
            
        await ctx.reply(embed=embed)
        
    @commands.command(name='급식.내일아침', aliases=['급식.내일조식'], description='내일 아침 조회')
    async def tomorrow_breakfast(self, ctx):
        title, menu = self.meal_service.get_meal_by_type(
            (datetime.now() + timedelta(days=1)).strftime("%Y%m%d"),
            "1",
            "🍳 내일 아침"
        )
        
        if title and menu:
            embed = MealEmbed.create_meal_embed(title, menu)
        else:
            embed = MealEmbed.create_error_embed("내일 조식 정보를 가져올 수 없습니다.")
            
        await ctx.reply(embed=embed)
    
    @commands.command(name='급식.내일점심', aliases=['급식.내일중식'], description='내일 점심 조회')
    async def tomorrow_lunch(self, ctx):
        title, menu = self.meal_service.get_meal_by_type(
            (datetime.now() + timedelta(days=1)).strftime("%Y%m%d"),
            "2",
            "🍚 내일 점심"
        )
        
        if title and menu:
            embed = MealEmbed.create_meal_embed(title, menu)
        else:
            embed = MealEmbed.create_error_embed("내일 중식 정보를 가져올 수 없습니다.")
            
        await ctx.reply(embed=embed)

    @commands.command(name='급식.내일저녁', aliases=['급식.내일석식'], description='내일 저녁 조회')
    async def tomorrow_dinner(self, ctx):
        title, menu = self.meal_service.get_meal_by_type(
            (datetime.now() + timedelta(days=1)).strftime("%Y%m%d"),
            "3",
            "🍖 내일 저녁"
        )
        
        if title and menu:
            embed = MealEmbed.create_meal_embed(title, menu)
        else:
            embed = MealEmbed.create_error_embed("내일 석식 정보를 가져올 수 없습니다.")
            
        await ctx.reply(embed=embed)