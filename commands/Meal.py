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
                    meal['DDISH_NM'] = meal['DDISH_NM'].replace('*', '')
                RequestMeal._cache[date] = (meals, datetime.now())
                return meals
            return None
            
        except (requests.RequestException, json.JSONDecodeError, KeyError):
            return None

class Meal(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name='급식', description='급식 조회')
    async def meal(self, ctx):
        now = datetime.now()
        today = now.strftime("%Y%m%d")
        current_hour = now.hour
        current_minute = now.minute
        
        meal_info = RequestMeal.get_meal_info(today)
        
        if meal_info:
            if current_hour < 7 or (current_hour == 7 and current_minute < 30):
                menu = next((meal["DDISH_NM"] for meal in meal_info if meal["MMEAL_SC_CODE"] == "1"), "NO_MEAL")
                title = "🍳 아침"
            elif current_hour < 12 or (current_hour == 12 and current_minute < 30):
                menu = next((meal["DDISH_NM"] for meal in meal_info if meal["MMEAL_SC_CODE"] == "2"), "NO_MEAL")
                title = "🍚 점심"
            elif current_hour < 18 or (current_hour == 18 and current_minute < 30):
                menu = next((meal["DDISH_NM"] for meal in meal_info if meal["MMEAL_SC_CODE"] == "3"), "NO_MEAL")
                title = "🍖 저녁"
            else:
                tomorrow = (now + timedelta(days=1)).strftime("%Y%m%d")
                tomorrow_meal_info = RequestMeal.get_meal_info(tomorrow)
                if tomorrow_meal_info:
                    menu = next((meal["DDISH_NM"] for meal in tomorrow_meal_info if meal["MMEAL_SC_CODE"] == "1"), "NO_MEAL")
                    title = "🍳 내일 아침"
                else:
                    menu = "NO_MEAL"
                    title = "🍳 내일 아침"
            
            embed = discord.Embed(
                title=title,
                description=menu.replace("<br/>", "\n"),
                color=discord.Color.orange()
            )
        else:
            embed = discord.Embed(
                title="❗ 오류",
                description="나이스 API 이슈",
                color=discord.Color.red()
            )
            
        await ctx.reply(embed=embed)
        
    @commands.command(name='급식.아침', aliases=['급식.조식'], description='아침 조회')
    async def breakfast(self, ctx):
        today = datetime.now().strftime("%Y%m%d")
        meal_info = RequestMeal.get_meal_info(today)
        
        if meal_info:
            breakfast_menu = next((meal["DDISH_NM"] for meal in meal_info if meal["MMEAL_SC_CODE"] == "1"), "NO_MEAL")
            
            embed = discord.Embed(
                title="🍳 아침",
                description=breakfast_menu.replace("<br/>", "\n"),
                color=discord.Color.orange()
            )
        else:
            embed = discord.Embed(
                title="❗ 오류",
                description="조식 정보를 가져올 수 없습니다.",
                color=discord.Color.red()
            )
            
        await ctx.reply(embed=embed)
        
    @commands.command(name='급식.점심', aliases=['급식.중식'], description='점심 조회')
    async def lunch(self, ctx):
        today = datetime.now().strftime("%Y%m%d")
        meal_info = RequestMeal.get_meal_info(today)
        
        if meal_info:
            lunch_menu = next((meal["DDISH_NM"] for meal in meal_info if meal["MMEAL_SC_CODE"] == "2"), "NO_MEAL")
            
            embed = discord.Embed(
                title="🍚 점심",
                description=lunch_menu.replace("<br/>", "\n"),
                color=discord.Color.orange()
            )
        else:
            embed = discord.Embed(
                title="❗ 오류",
                description="중식 정보를 가져올 수 없습니다.",
                color=discord.Color.red()
            )
        
        await ctx.reply(embed=embed)
        
    @commands.command(name='급식.저녁', aliases=['급식.석식'], description='저녁 조회')
    async def dinner(self, ctx):
        today = datetime.now().strftime("%Y%m%d")
        meal_info = RequestMeal.get_meal_info(today)
        
        if meal_info:
            dinner_menu = next((meal["DDISH_NM"] for meal in meal_info if meal["MMEAL_SC_CODE"] == "3"), "NO_MEAL")
            
            embed = discord.Embed(
                title="🍖 저녁",
                description=dinner_menu.replace("<br/>", "\n"),
                color=discord.Color.orange()
            )
        else:
            embed = discord.Embed(
                title="❗ 오류",
                description="석식 정보를 가져올 수 없습니다.",
                color=discord.Color.red()
            )
            
        await ctx.reply(embed=embed)
        
    @commands.command(name='급식.내일아침', aliases=['급식.내일조식'], description='내일 아침 조회')
    async def tomorrow_breakfast(self, ctx):
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y%m%d")
        meal_info = RequestMeal.get_meal_info(tomorrow)
        
        if meal_info:
            breakfast_menu = next((meal["DDISH_NM"] for meal in meal_info if meal["MMEAL_SC_CODE"] == "1"), "NO_MEAL")
            
            embed = discord.Embed(
                title="🍳 내일 아침",
                description=breakfast_menu.replace("<br/>", "\n"),
                color=discord.Color.orange()
            )
        else:
            embed = discord.Embed(
                title="❗ 오류",
                description="내일 조식 정보를 가져올 수 없습니다.",
                color=discord.Color.red()
            )
            
        await ctx.reply(embed=embed)
    
    @commands.command(name='급식.내일점심', aliases=['급식.내일중식'], description='내일 점심 조회')
    async def tomorrow_lunch(self, ctx):
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y%m%d")
        meal_info = RequestMeal.get_meal_info(tomorrow)
        
        if meal_info:
            lunch_menu = next((meal["DDISH_NM"] for meal in meal_info if meal["MMEAL_SC_CODE"] == "2"), "NO_MEAL")
            
            embed = discord.Embed(
                title="🍚 내일 점심",
                description=lunch_menu.replace("<br/>", "\n"),
                color=discord.Color.orange()
            )
        else:
            embed = discord.Embed(
                title="❗ 오류",
                description="내일 중식 정보를 가져올 수 없습니다.",
                color=discord.Color.red()
            )
            
        await ctx.reply(embed=embed)

    @commands.command(name='급식.내일저녁', aliases=['급식.내일석식'], description='내일 저녁 조회')
    async def tomorrow_dinner(self, ctx):
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y%m%d")
        meal_info = RequestMeal.get_meal_info(tomorrow)
        
        if meal_info:
            dinner_menu = next((meal["DDISH_NM"] for meal in meal_info if meal["MMEAL_SC_CODE"] == "3"), "NO_MEAL")
            
            embed = discord.Embed(
                title="🍖 내일 저녁",
                description=dinner_menu.replace("<br/>", "\n"),
                color=discord.Color.orange()
            )
        else:
            embed = discord.Embed(
                title="❗ 오류",
                description="내일 석식 정보를 가져올 수 없습니다.",
                color=discord.Color.red()
            )
            
        await ctx.reply(embed=embed)