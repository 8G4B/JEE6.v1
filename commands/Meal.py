import discord
from discord.ext import commands
import meal_api_key
import requests
import json
from datetime import datetime

class RequestMeal:
    params = {
        'key': meal_api_key.MEAL_API_KEY,
        'type': 'json',
        'ATPT_OFCDC_SC_CODE': 'F10', 
        'SD_SCHUL_CODE': '7380292',  
    }
    
    base_url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
    
    @staticmethod
    def get_meal_info(date):
        params = RequestMeal.params.copy()
        params['MLSV_YMD'] = date
        
        try:
            response = requests.get(RequestMeal.base_url, params=params)
            data = response.json()
            
            if 'mealServiceDietInfo' in data:
                meals = data['mealServiceDietInfo'][1]['row']
                for meal in meals:  
                    meal['DDISH_NM'] = meal['DDISH_NM'].replace('*', '')
                return meals
            return None
            
        except (requests.RequestException, json.JSONDecodeError, KeyError):
            return None

class Meal(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.command(name='급식.아침', description='아침 조회')
    async def breakfast(self, ctx):
        today = datetime.now().strftime("%Y%m%d")
        meal_info = RequestMeal.get_meal_info(today)
        
        if meal_info:
            breakfast_menu = next((meal["DDISH_NM"] for meal in meal_info if meal["MMEAL_SC_CODE"] == "1"), "급식 정보가 없습니다.")
            
            embed = discord.Embed(
                title="아침",
                description=breakfast_menu.replace("<br/>", "\n"),
                color=discord.Color.purple()
            )
        else:
            embed = discord.Embed(
                title="아침",
                description="급식 정보를 가져올 수 없습니다.",
                color=discord.Color.purple()
            )
            
        await ctx.message.delete()
        await ctx.reply(f"{ctx.author.ion}", embed=embed)
        
    @commands.command(name='급식.점심', description='점심 조회')
    async def lunch(self, ctx):
        today = datetime.now().strftime("%Y%m%d")
        meal_info = RequestMeal.get_meal_info(today)
        
        if meal_info:
            lunch_menu = next((meal["DDISH_NM"] for meal in meal_info if meal["MMEAL_SC_CODE"] == "2"), "급식 정보가 없습니다.")
            
            embed = discord.Embed(
                title="점심",
                description=lunch_menu.replace("<br/>", "\n"),
                color=discord.Color.purple()
            )
        else:
            embed = discord.Embed(
                title="점심",
                description="급식 정보를 가져올 수 없습니다.",
                color=discord.Color.purple()
            )
        
        await ctx.message.delete()
        await ctx.reply(f"{ctx.author.mention}", embed=embed)
        
    @commands.command(name='급식.저녁', description='저녁 조회')
    async def dinner(self, ctx):
        today = datetime.now().strftime("%Y%m%d")
        meal_info = RequestMeal.get_meal_info(today)
        
        if meal_info:
            dinner_menu = next((meal["DDISH_NM"] for meal in meal_info if meal["MMEAL_SC_CODE"] == "3"), "급식 정보가 없습니다.")
            
            embed = discord.Embed(
                title="저녁",
                description=dinner_menu.replace("<br/>", "\n"),
                color=discord.Color.purple()
            )
        else:
            embed = discord.Embed(
                title="저녁",
                description="급식 정보를 가져올 수 없습니다.",
                color=discord.Color.purple()
            )
            
        await ctx.message.delete()
        await ctx.reply(f"{ctx.author.mention}", embed=embed)
