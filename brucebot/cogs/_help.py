import discord
from discord.ext import commands


class MyHelp(commands.HelpCommand):
    """Base for help commands."""

    def get_command_signature(self, command: commands.Command) -> str:
        """Retrieve the signature portion of the help page."""
        return (
            f"{self.context.clean_prefix}{command.qualified_name} {command.signature}"
        )

    async def send_bot_help(self, mapping: dict) -> None:
        """Help with bot functions."""
        embed = discord.Embed(title="Brucebot Help", color=discord.Color.blurple())

        for cog, cmds in mapping.items():
            filtered = await self.filter_commands(cmds, sort=True)
            command_signatures = [self.get_command_signature(c) for c in filtered]

            if command_signatures and cog is not None:
                embed.add_field(
                    name=cog.qualified_name,
                    value=cog.description,
                    inline=True,
                )

        embed.set_footer(
            text=f"{self.context.clean_prefix}bhelp [category] for more details.",
        )

        channel = self.get_destination()
        await channel.send(embed=embed)

    async def send_command_help(self, command: commands.Command) -> discord.Embed:
        """Help with specific commands."""
        embed = discord.Embed(
            title=self.get_command_signature(command),
            color=discord.Color.random(),
        )
        if command.help:
            embed.description = command.help
        if alias := command.aliases:
            embed.add_field(name="Aliases", value=", ".join(alias), inline=False)

        channel = self.get_destination()
        await channel.send(embed=embed)

    async def send_cog_help(self, cog: commands.Cog) -> None:
        """Help with cogs."""
        embed = discord.Embed(
            title=cog.qualified_name or "No Category",
            description=cog.description,
            color=discord.Color.blurple(),
        )

        if filtered_commands := await self.filter_commands(cog.get_commands()):
            for command in filtered_commands:
                embed.add_field(
                    name=self.get_command_signature(command),
                    value=command.help or "No Help Message Found... ",
                    inline=False,
                )

        await self.get_destination().send(embed=embed)

    async def send_group_help(self, group: commands.Group) -> None:
        """Help with specific groups of commands."""
        embed = discord.Embed(
            title=self.get_command_signature(group),
            description=group.help,
            color=discord.Color.blurple(),
        )

        embed.description += "\n\n__**subcommands**__"

        if filtered_commands := await self.filter_commands(group.commands):
            for command in filtered_commands:
                embed.add_field(
                    name=f"{self.context.clean_prefix}{command.qualified_name} {command.signature}",  # noqa: E501
                    value=command.brief or command.help,
                    inline=False,
                )

        embed.set_footer(
            text=(
                f"{self.context.clean_prefix}bhelp {group.qualified_name} "
                "[subcommand] for more details."
            ),
        )

        await self.get_destination().send(embed=embed)
