import discord
from discord.ext import commands
from shared.meal_api_key import MEAL_API_KEY
import json
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import aiohttp

ATPT_OFCDC_SC_CODE = 'F10' # 광주광역시교육청
SD_SCHUL_CODE = '7380292' # GSM 

NO_MEAL = "급식이 없습니다."

MEAL_TIMES = [
    ((lambda h, m: h < 7 or (h == 7 and m < 30)), "1", "🍳 아침"),
    ((lambda h, m: h < 12 or (h == 12 and m < 30)), "2", "🍚 점심"), 
    ((lambda h, m: h < 18 or (h == 18 and m < 30)), "3", "🍖 저녁")
]

class RequestMeal:
    params = {
        'key': MEAL_API_KEY,
        'type': 'json',
        'ATPT_OFCDC_SC_CODE': ATPT_OFCDC_SC_CODE, 
        'SD_SCHUL_CODE': SD_SCHUL_CODE,  
    }
    
    base_url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
    
    _cache: Dict[str, tuple[List, datetime]] = {}
    CACHE_DURATION = timedelta(hours=1)  
    
    @staticmethod
    async def get_meal_info(date: str) -> Optional[List]:
        if date in RequestMeal._cache:
            cached_data, cache_time = RequestMeal._cache[date]
            if datetime.now() - cache_time < RequestMeal.CACHE_DURATION:
                return cached_data
            del RequestMeal._cache[date]
        
        params = RequestMeal.params.copy()
        params['MLSV_YMD'] = date
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(RequestMeal.base_url, params=params) as response:
                    data = await response.json()
                    
                    if 'mealServiceDietInfo' in data:
                        meals = data['mealServiceDietInfo'][1]['row']
                        for meal in meals:  
                            meal['DDISH_NM'] = '\n'.join(f'- {dish.strip()}' for dish in meal['DDISH_NM'].replace('*', '').split('<br/>') if dish.strip())
                        RequestMeal._cache[date] = (meals, datetime.now())
                        return meals
                    return None
                    
        except (aiohttp.ClientError, json.JSONDecodeError, KeyError):
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
    
    async def _get_menu_from_meal_info(self, meal_info: list, meal_code: str) -> str:
        return next((meal["DDISH_NM"] for meal in meal_info if meal["MMEAL_SC_CODE"] == meal_code), NO_MEAL)
    
    async def get_current_meal(self, now: datetime) -> tuple[str, str]:
        today = now.strftime("%Y%m%d")
        current_hour = now.hour
        current_minute = now.minute
        
        meal_info = await RequestMeal.get_meal_info(today)
        
        if not meal_info:
            return None, None
            
        for time_check, code, title in MEAL_TIMES:
            if time_check(current_hour, current_minute):
                menu = await self._get_menu_from_meal_info(meal_info, code)
                return title, menu
        
        tomorrow = (now + timedelta(days=1)).strftime("%Y%m%d")
        tomorrow_meal_info = await RequestMeal.get_meal_info(tomorrow)
        
        if tomorrow_meal_info:
            menu = await self._get_menu_from_meal_info(tomorrow_meal_info, "1")
        else:
            menu = NO_MEAL
            
        return "🍳 내일 아침", menu
        
    async def get_meal_by_type(self, date: str, meal_code: str, title: str) -> tuple[str, str]:
        meal_info = await RequestMeal.get_meal_info(date)
        if not meal_info:
            return None, None
            
        menu = await self._get_menu_from_meal_info(meal_info, meal_code)
        return title, menu

class Meal(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.meal_service = MealService()
        
    async def _handle_meal_command(self, ctx, date: str, meal_code: str, title: str, error_message: str):
        title, menu = await self.meal_service.get_meal_by_type(date, meal_code, title)
        
        embed = (MealEmbed.create_meal_embed(title, menu) if title and menu 
                else MealEmbed.create_error_embed(error_message))
        
        await ctx.reply(embed=embed)

    @commands.command(name='급식', aliases=['밥'], description='급식 조회')
    async def meal(self, ctx):
        title, menu = await self.meal_service.get_current_meal(datetime.now())
        embed = (MealEmbed.create_meal_embed(title, menu) if title and menu 
                else MealEmbed.create_error_embed("나이스 API 이슈"))
        await ctx.reply(embed=embed)

    @commands.command(name='급식.아침', aliases=['급식.조식'], description='아침 조회')
    async def breakfast(self, ctx):
        await self._handle_meal_command(
            ctx,
            datetime.now().strftime("%Y%m%d"),
            "1",
            "🍳 아침",
            "조식 정보를 가져올 수 없습니다."
        )

    @commands.command(name='급식.점심', aliases=['급식.중식'], description='점심 조회')
    async def lunch(self, ctx):
        await self._handle_meal_command(
            ctx,
            datetime.now().strftime("%Y%m%d"),
            "2",
            "🍚 점심",
            "중식 정보를 가져올 수 없습니다."
        )

    @commands.command(name='급식.저녁', aliases=['급식.석식'], description='저녁 조회')
    async def dinner(self, ctx):
        await self._handle_meal_command(
            ctx,
            datetime.now().strftime("%Y%m%d"),
            "3",
            "🍖 저녁",
            "석식 정보를 가져올 수 없습니다."
        )

    @commands.command(name='급식.내일아침', aliases=['급식.내일조식'], description='내일 아침 조회')
    async def tomorrow_breakfast(self, ctx):
        await self._handle_meal_command(
            ctx,
            (datetime.now() + timedelta(days=1)).strftime("%Y%m%d"),
            "1",
            "🍳 내일 아침",
            "내일 조식 정보를 가져올 수 없습니다."
        )

    @commands.command(name='급식.내일점심', aliases=['급식.내일중식'], description='내일 점심 조회')
    async def tomorrow_lunch(self, ctx):
        await self._handle_meal_command(
            ctx,
            (datetime.now() + timedelta(days=1)).strftime("%Y%m%d"),
            "2",
            "🍚 내일 점심",
            "내일 중식 정보를 가져올 수 없습니다."
        )

    @commands.command(name='급식.내일저녁', aliases=['급식.내일석식'], description='내일 저녁 조회')
    async def tomorrow_dinner(self, ctx):
        await self._handle_meal_command(
            ctx,
            (datetime.now() + timedelta(days=1)).strftime("%Y%m%d"),
            "3",
            "🍖 내일 저녁",
            "내일 석식 정보를 가져올 수 없습니다."
        )