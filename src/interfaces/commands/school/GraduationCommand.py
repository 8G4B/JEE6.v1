import discord
from discord.ext import commands
import re
from src.interfaces.commands.Base import BaseCommand


class GraduationCommand(BaseCommand):
    @commands.command(name="졸업")
    @commands.has_permissions(administrator=True)
    async def graduation(self, ctx):
        """
        졸업 처리 명령어:
        1. 3학년 관련 역할 제거 및 졸업생 역할 부여
        2. 닉네임 변경 (3101 홍길동 -> 7기 홍길동)
        """
        guild = ctx.guild
        if not guild:
            return

        # Roles to remove
        target_roles_names = [
            "3학년", "3학년 남학생", "3학년 여학생", 
            "3학년 1반", "3학년 2반", "3학년 3반", "3학년 4반"
        ]

        # Target graduate role
        graduate_role_name = "졸업생"
        graduate_role = discord.utils.get(guild.roles, name=graduate_role_name)

        if not graduate_role:
            await ctx.send(f"오류: '{graduate_role_name}' 역할을 찾을 수 없습니다.")
            return

        # Progress message
        msg = await ctx.send("졸업 처리 중입니다... (이 작업은 시간이 걸릴 수 있습니다)")

        count_roles = 0
        count_nicks = 0

        # Iterate over all members
        for member in guild.members:
            if member.bot:
                continue

            # 1. Role Update
            roles_to_remove = []
            has_3rd_year = False

            member_role_names = [r.name for r in member.roles]

            for r_name in target_roles_names:
                if r_name in member_role_names:
                    role_obj = discord.utils.get(guild.roles, name=r_name)
                    if role_obj:
                        roles_to_remove.append(role_obj)
                        has_3rd_year = True

            if has_3rd_year:
                try:
                    await member.remove_roles(*roles_to_remove)
                    await member.add_roles(graduate_role)
                    count_roles += 1
                except discord.Forbidden:
                    print(f"Failed to update roles for {member.display_name}: Permission denied")
                except Exception as e:
                    print(f"Failed to update roles for {member.display_name}: {e}")

            # 2. Nickname Update
            # Pattern: 4 digits starting with 3, space, name. e.g. "3101 홍길동"
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

        await msg.edit(content=f"졸업 처리가 완료되었습니다.\n- 역할 변경: {count_roles}명\n- 닉네임 변경: {count_nicks}명")
