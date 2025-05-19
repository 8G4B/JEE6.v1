from discord.ext import commands


class CustomBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!")
        self.remove_command("help")
