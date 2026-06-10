from discord.ext import commands
import logging
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional
from src.interfaces.commands.Base import BaseCommand
from src.utils.embeds.MealEmbed import MealEmbed
from src.clients.ApiGatewayClient import ApiGatewayClient

logger = logging.getLogger(__name__)

# -d / --date 플래그와 그 값(0610, 06-10, 2026-06-10 등)을 잡아낸다.
_DATE_FLAG_RE = re.compile(r"(?:^|\s)(?:--date|-d)(?:[=\s]+(\S+))?")


class MealCommands(BaseCommand):
    def __init__(self, bot, container):
        super().__init__(bot, container)
        self.api = ApiGatewayClient()

    def _parse_date_option(self, options: str) -> Optional[str]:
        """명령 옵션에서 날짜를 뽑아 YYYYMMDD로 반환. 날짜 미지정이면 None, 잘못되면 ValueError."""
        text = (options or "").strip()
        if not text:
            return None
        flag = _DATE_FLAG_RE.search(text)
        if not flag:
            return None  # 날짜 플래그가 없으면 그냥 무시
        value = flag.group(1)
        if not value:
            raise ValueError("날짜를 입력해주세요. 예: `-d 0610`")
        return self._normalize_date(value)

    def _normalize_date(self, raw: str) -> str:
        year = datetime.now(ZoneInfo("Asia/Seoul")).year
        try:
            if raw.isdigit():
                if len(raw) == 8:
                    y, mo, d = int(raw[:4]), int(raw[4:6]), int(raw[6:8])
                elif len(raw) == 4:
                    y, mo, d = year, int(raw[:2]), int(raw[2:])
                else:
                    raise ValueError
            else:
                parts = [p for p in re.split(r"[-./]", raw) if p]
                if len(parts) == 3:
                    y, mo, d = int(parts[0]), int(parts[1]), int(parts[2])
                elif len(parts) == 2:
                    y, mo, d = year, int(parts[0]), int(parts[1])
                else:
                    raise ValueError
            dt = datetime(y, mo, d)
        except (ValueError, TypeError):
            raise ValueError(
                f"`{raw}` 는 올바른 날짜가 아니에요. 예: `0610`, `06-10`, `2026-06-10`"
            )
        if dt.year != year:
            raise ValueError(f"올해({year}년) 날짜만 조회할 수 있어요.")
        return dt.strftime("%Y%m%d")

    async def _send_meal(self, ctx, meal_type: str, day: str, options: str = ""):
        try:
            date = self._parse_date_option(options)
        except ValueError as e:
            await ctx.reply(embed=MealEmbed.create_error_embed(str(e)))
            return

        try:
            data = await self.api.get_meal(meal_type=meal_type, day=day, date=date)

            if data.get("error"):
                await ctx.reply(embed=MealEmbed.create_error_embed(data["error"]))
                return
            if not data.get("menu"):
                await ctx.reply(
                    embed=MealEmbed.create_error_embed("급식 정보를 가져올 수 없습니다.")
                )
                return

            embed = MealEmbed.create_meal_embed(
                data["title"], data["menu"], data.get("cal_info", "")
            )
            # 급식을 먼저 보여주고, 사진은 기다리지 않는다.
            msg = await ctx.reply(embed=embed)
            await self._attach_meal_image(msg, embed, data)
        except Exception as e:
            logger.error(e)
            await ctx.send(embed=MealEmbed.create_error_embed(e))

    async def _attach_meal_image(self, msg, embed, data: dict):
        # 사진이 준비되면 메시지를 수정해 끼워넣는다. 실패해도 급식 메시지엔 영향 없음.
        date, meal_code = data.get("date"), data.get("meal_code")
        if not (date and meal_code):
            return
        try:
            result = await self.api.get_meal_image(date, meal_code)
            image_url = result.get("image_url")
            if image_url:
                embed.set_image(url=image_url)
                await msg.edit(embed=embed)
        except Exception as e:
            logger.warning(f"급식 사진 첨부 실패: {e}")

    @commands.command(
        name="급식",
        aliases=["밥", "meal", "ㄱㅅ"],
        description="현재 시간에 맞는 급식 조회",
    )
    async def meal(self, ctx, *, options: str = ""):
        logger.info(f"meal({ctx.guild.name}, {ctx.author.name})")
        await self._send_meal(ctx, "auto", "today", options)

    @commands.command(
        name="급식.아침",
        aliases=["급식.조식", "meal.breakfast", "ㄱㅅ.ㅇㅊ", "아침"],
        description="아침 급식 조회",
    )
    async def breakfast(self, ctx, *, options: str = ""):
        await self._send_meal(ctx, "breakfast", "today", options)

    @commands.command(
        name="급식.점심",
        aliases=["급식.중식", "meal.lunch", "ㄱㅅ.ㅈㅅ", "점심"],
        description="점심 급식 조회",
    )
    async def lunch(self, ctx, *, options: str = ""):
        await self._send_meal(ctx, "lunch", "today", options)

    @commands.command(
        name="급식.저녁",
        aliases=["급식.석식", "meal.dinner", "ㄱㅅ.ㅈㄴ", "저녁"],
        description="저녁 급식 조회",
    )
    async def dinner(self, ctx, *, options: str = ""):
        await self._send_meal(ctx, "dinner", "today", options)

    @commands.command(
        name="급식.내일아침",
        aliases=["급식.내일조식", "meal.tomorrow_breakfast", "ㄱㅅ.ㄴㅇㅊ", "내일아침"],
        description="내일 아침 급식 조회",
    )
    async def tomorrow_breakfast(self, ctx, *, options: str = ""):
        await self._send_meal(ctx, "breakfast", "tomorrow", options)

    @commands.command(
        name="급식.내일점심",
        aliases=["급식.내일중식", "meal.tomorrow_lunch", "ㄱㅅ.ㄴㅈㅅ", "내일점심"],
        description="내일 점심 급식 조회",
    )
    async def tomorrow_lunch(self, ctx, *, options: str = ""):
        await self._send_meal(ctx, "lunch", "tomorrow", options)

    @commands.command(
        name="급식.내일저녁",
        aliases=["급식.내일석식", "meal.tomorrow_dinner", "ㄱㅅ.ㄴㅓㄴ", "내일저녁"],
        description="내일 저녁 급식 조회",
    )
    async def tomorrow_dinner(self, ctx, *, options: str = ""):
        await self._send_meal(ctx, "dinner", "tomorrow", options)
