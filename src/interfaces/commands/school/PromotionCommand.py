import json
import re
from pathlib import Path

import discord
from discord.ext import commands

from src.config.settings.Base import BaseConfig
from src.interfaces.commands.Base import BaseCommand


class PromotionCommand(BaseCommand):
    def _load_students(self, year: int) -> list:
        path = BaseConfig.BASE_DIR.parent / "assets" / "students" / f"{year}_전체학생명렬_flat.json"
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)["students"]

    def _resolve_student(self, name: str, cur_grade: int, cur_class: int, students_by_name: dict) -> dict | None:
        candidates = students_by_name.get(name, [])
        if not candidates:
            return None

        expected_grade = cur_grade + 1
        grade_filtered = [s for s in candidates if s["grade"] == expected_grade]

        if len(grade_filtered) == 0:
            return None
        if len(grade_filtered) == 1:
            return grade_filtered[0]

        if cur_class in (3, 4):
            class_filtered = [s for s in grade_filtered if s["class"] == cur_class]
        else:
            class_filtered = [s for s in grade_filtered if s["class"] not in (3, 4)]

        if len(class_filtered) == 1:
            return class_filtered[0]
        return None

    async def _get_or_create_role(
        self,
        guild: discord.Guild,
        name: str,
        cache: dict,
        created: list,
    ) -> discord.Role:
        if name in cache:
            return cache[name]
        role = discord.utils.get(guild.roles, name=name)
        if role is None:
            role = await guild.create_role(name=name, reason="!역할 명령어로 자동 생성")
            created.append(name)
        cache[name] = role
        return role

    @commands.command(name="역할")
    @commands.has_permissions(administrator=True)
    async def assign_roles(self, ctx):
        guild = ctx.guild
        if not guild:
            return

        try:
            students = self._load_students(2026)
        except FileNotFoundError:
            await ctx.send("명렬표 파일(`2026_전체학생명렬_flat.json`)을 찾을 수 없습니다.")
            return

        students_by_name: dict[str, list] = {}
        for s in students:
            students_by_name.setdefault(s["name"], []).append(s)

        msg = await ctx.send("역할 부여 중입니다...")

        student_nick_pattern = re.compile(r"^[1-3][1-4]\d{2}\s+.+$")
        role_cache: dict[str, discord.Role] = {}
        created_roles: list[str] = []

        count_done = 0
        ambiguous: list[str] = []
        skipped: list[str] = []

        for member in guild.members:
            if member.bot:
                continue

            if student_nick_pattern.match(member.display_name):
                continue

            name = member.display_name
            candidates = students_by_name.get(name)

            if not candidates:
                continue

            if len(candidates) > 1:
                ambiguous.append(name)
                continue

            student = candidates[0]
            grade = student["grade"]
            cls = student["class"]
            no = student["no"]
            gender_suffix = "남학생" if student["gender"] == "M" else "여학생"

            new_nick = f"{grade}{cls}{no:02d} {name}"
            target_role_names = [
                f"{grade}학년",
                f"{grade}학년 {cls}반",
                f"{grade}학년 {gender_suffix}",
            ]

            try:
                await member.edit(nick=new_nick)

                roles_to_add = []
                for rname in target_role_names:
                    role_obj = await self._get_or_create_role(guild, rname, role_cache, created_roles)
                    if role_obj not in member.roles:
                        roles_to_add.append(role_obj)

                if roles_to_add:
                    await member.add_roles(*roles_to_add)

                count_done += 1

            except discord.Forbidden:
                skipped.append(f"{name} (권한 없음)")
            except Exception as e:
                skipped.append(f"{name} ({e})")

        summary = f"{count_done}명 처리 완료했어요"
        if created_roles:
            summary += f"\n새로 만든 역할: {', '.join(created_roles)}"
        if ambiguous:
            summary += f"\n동명이인 (수동 처리 필요): {', '.join(ambiguous)}"
        if skipped:
            summary += f"\n실패작들: {', '.join(skipped)}"

        await msg.edit(content=summary)

    @commands.command(name="등업")
    @commands.has_permissions(administrator=True)
    async def promotion(self, ctx):
        guild = ctx.guild
        if not guild:
            return

        try:
            next_students = self._load_students(2026)
        except FileNotFoundError:
            await ctx.send("명렬표 파일(`2026_전체학생명렬_flat.json`)을 찾을 수 없습니다.")
            return

        students_by_name: dict[str, list] = {}
        for s in next_students:
            students_by_name.setdefault(s["name"], []).append(s)

        msg = await ctx.send("등업 중입니다...")

        nick_pattern = re.compile(r"^([1-3])([1-4])(\d{2})\s+(.+)$")

        count_nick = 0
        count_role = 0
        count_already = 0
        skipped: list[str] = []

        for member in guild.members:
            if member.bot:
                continue

            match = nick_pattern.match(member.display_name)
            if not match:
                continue

            cur_grade = int(match.group(1))
            cur_class = int(match.group(2))
            name = match.group(4)

            if cur_grade == 3:
                continue

            new_student = self._resolve_student(name, cur_grade, cur_class, students_by_name)

            if new_student is None:
                skipped.append(f"{member.display_name}")
                continue

            new_grade = new_student["grade"]
            new_class = new_student["class"]
            new_no = new_student["no"]
            new_nick = f"{new_grade}{new_class}{new_no:02d} {name}"

            gender_suffix = "남학생" if new_student["gender"] == "M" else "여학생"

            old_role_names = {
                f"{cur_grade}학년",
                f"{cur_grade}학년 {cur_class}반",
                f"{cur_grade}학년 {gender_suffix}",
            }

            new_role_names = [
                f"{new_grade}학년",
                f"{new_grade}학년 {new_class}반",
                f"{new_grade}학년 {gender_suffix}",
            ]

            member_role_names = {r.name for r in member.roles}
            nick_done = member.display_name == new_nick
            old_roles_cleared = not any(rname in member_role_names for rname in old_role_names)
            new_roles_set = all(rname in member_role_names for rname in new_role_names)

            if nick_done and old_roles_cleared and new_roles_set:
                count_already += 1
                continue

            roles_to_remove = [r for r in member.roles if r.name in old_role_names]
            roles_to_add = [
                r for rname in new_role_names
                if (r := discord.utils.get(guild.roles, name=rname)) is not None
                and r not in member.roles
            ]

            try:
                if member.display_name != new_nick:
                    await member.edit(nick=new_nick)
                    count_nick += 1

                if roles_to_remove:
                    await member.remove_roles(*roles_to_remove)
                if roles_to_add:
                    await member.add_roles(*roles_to_add)

                if roles_to_remove or roles_to_add:
                    count_role += 1

            except discord.Forbidden:
                skipped.append(f"{member.display_name} (권한 없음)")
            except Exception as e:
                skipped.append(f"{member.display_name} ({e})")

        summary = f"닉네임 {count_nick}명, 역할 {count_role}명 변경했어요"
        if count_already:
            summary += f"\n{count_already}명 건너뜀"
        if skipped:
            summary += f"\n실패작들: {', '.join(skipped)}"

        await msg.edit(content=summary)
