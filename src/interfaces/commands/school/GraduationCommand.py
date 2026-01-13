import discord
from discord.ext import commands
import re
from src.interfaces.commands.Base import BaseCommand


class GraduationCommand(BaseCommand):
    @commands.command(name="졸업")
    @commands.has_permissions(administrator=True)
    async def graduation(self, ctx):
        guild = ctx.guild
        if not guild:
            return

        graduate_role_name = "졸업생"
        graduate_role = discord.utils.get(guild.roles, name=graduate_role_name)

        if not graduate_role:
            await ctx.send(f"오류: '{graduate_role_name}' 역할을 찾을 수 없습니다.")
            return

        msg = await ctx.send("졸업생 닉네임 변경 중입니다... (이 작업은 시간이 걸릴 수 있습니다)")

        count_nicks = 0

        for member in guild.members:
            if member.bot:
                continue

            if graduate_role not in member.roles:
                continue

            current_name = member.display_name
            pattern = r"^3\d{3}\s+(.+)$"
            match = re.match(pattern, current_name)

            if match:
                name_part = match.group(1)
                new_nick = f"7기 {name_part}"
                try:
                    if current_name != new_nick:
                        await member.edit(nick=new_nick)
                        count_nicks += 1
                except discord.Forbidden:
                    print(f"Failed to update nickname for {member.display_name}: Permission denied")
                except Exception as e:
                    print(f"Failed to update nickname for {member.display_name}: {e}")

        await msg.edit(content=f"졸업생 닉네임 변경이 완료되었습니다.\n- 닉네임 변경: {count_nicks}명")
