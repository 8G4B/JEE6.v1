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

    @commands.command(name="등업")
    @commands.has_permissions(administrator=True)
    async def promotion(self, ctx):
        guild = ctx.guild
        if not guild:
            return

        try:
            next_students = self._load_students(2026)
        except FileNotFoundError:
            await ctx.send("2026년 학생 명렬표 파일(`2026_전체학생명렬_flat.json`)을 찾을 수 없습니다.")
            return

        students_by_name: dict[str, list] = {}
        for s in next_students:
            students_by_name.setdefault(s["name"], []).append(s)

        msg = await ctx.send("등업 중입니다...")

        nick_pattern = re.compile(r"^([1-3])([1-4])(\d{2})\s+(.+)$")

        count_nick = 0
        count_role = 0
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

            gender_suffix = None
            for role in member.roles:
                if "남학생" in role.name:
                    gender_suffix = "남학생"
                    break
                if "여학생" in role.name:
                    gender_suffix = "여학생"
                    break

            old_role_names = {
                f"{cur_grade}학년",
                f"{cur_grade}학년 {cur_class}반",
            }
            if gender_suffix:
                old_role_names.add(f"{cur_grade}학년 {gender_suffix}")

            new_role_names = [
                f"{new_grade}학년",
                f"{new_grade}학년 {new_class}반",
            ]
            if gender_suffix:
                new_role_names.append(f"{new_grade}학년 {gender_suffix}")

            roles_to_remove = [r for r in member.roles if r.name in old_role_names]
            roles_to_add = [
                r for rname in new_role_names
                if (r := discord.utils.get(guild.roles, name=rname)) is not None
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
        if skipped:
            summary += f"\n실패작들: {', '.join(skipped)}"

        await msg.edit(content=summary)
