import discord
from typing import List, Dict


class BusEmbed:
    @staticmethod
    def create_bus_arrival_embed(bus_info: List[Dict]) -> discord.Embed:
        embed = discord.Embed(
            title="🚌 버스 도착 정보",
            description="송정공원역(5149)",
            color=discord.Color.blue()
        )
        
        if not bus_info:
            embed.add_field(
                name="❌ 정보 없음",
                value="현재 도착 예정인 버스가 없습니다.",
                inline=False
            )
            return embed
        
        for i, bus in enumerate(bus_info, 1):
            route_no = bus['route_no']
            vehicle_type = bus['vehicle_type']
            arrival_time = bus['arrival_time']
            remaining_stations = bus['remaining_stations']
            current_stop = bus.get('current_stop', '')
            arrive_flag = bus.get('arrive_flag', 0)

            # 버스 유형에 따른 이모지
            bus_emoji = "🚌"
            if "저상" in vehicle_type:
                bus_emoji = "♿"
            elif "마을" in vehicle_type:
                bus_emoji = "🚐"

            field_name = f"{bus_emoji} {route_no}번 ({vehicle_type})"
            
            field_value = f"🕐 **{arrival_time}** 후 도착\n" if arrive_flag == 0 else f"⏳ **{arrival_time}** 후 도착 (곧 도착)"
            if current_stop:
                field_value += f"📍현재 **{current_stop}** ({remaining_stations}개 전)\n"
            else:
                field_value += f"📍{remaining_stations}개 정류장 전\n"
            
            embed.add_field(
                name=field_name,
                value=field_value,
                inline=True
            )

            if i % 2 == 0:
                embed.add_field(name="\u200b", value="\u200b", inline=True)

        embed.set_footer(text="💡 1분마다 정보가 업데이트됩니다.")
        return embed

    @staticmethod
    def create_error_embed(description: str) -> discord.Embed:
        return discord.Embed(
            title="❗ 오류",
            description=description,
            color=discord.Color.red()
        )
