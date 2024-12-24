import discord
from discord.ext import commands
import openai
from gpt_api_key import GPT_API_KEY

class RequestGPT:
    def __init__(self):
        self.api_key = GPT_API_KEY
        openai.api_key = self.api_key
        
    def send_request(self, model: str, system: str, user: str) -> str:
        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ]
        )
        return response.choices[0].message.content

class GPTService:
    def __init__(self):
        self.gpt_request = RequestGPT()
        
    def get_answer(self, user: str) -> str:
        return self.gpt_request.send_request("gpt-3.5-turbo", "다음 질문에 대해 간단히 답변해주세요.", user)

class QuestionEmbed:
    @staticmethod
    def create_error_embed(description: str) -> discord.Embed:
        return discord.Embed(
            title="❗ 오류",
            description=description,
            color=discord.Color.red()
        )
    
    @staticmethod
    def create_answer_embed(answer: str, question: str) -> discord.Embed:
        embed = discord.Embed(
            title="답변",
            description=answer,
            color=discord.Color.green()
        )
        embed.set_footer(text=f"질문: {question}")
        return embed

class Question(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.gpt_service = GPTService()

    @commands.command(name="질문", aliases=['물어보기'], description="질문")
    async def question(self, ctx, *, question=None):
        if question is None:
            embed = QuestionEmbed.create_error_embed("!질문 [질문할 내용] <-- 이렇게 써")
            await ctx.reply(embed=embed)
            return

        try:
            answer = self.gpt_service.get_answer(question)
            embed = QuestionEmbed.create_answer_embed(answer, question)
        except Exception:
            embed = QuestionEmbed.create_error_embed("GPT API")
            
        await ctx.reply(embed=embed)