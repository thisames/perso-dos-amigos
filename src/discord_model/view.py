import discord
import src.repos.firebase_repo as repo

from src.utils.embed import create_active_players_embed


class TeamSelect(discord.ui.Select):
    """
    A dropdown menu to select players to be added to the active list.
    """

    async def callback(self, interaction: discord.Interaction):
        repo.add_active_players(self.values)

        await interaction.response.send_message(
            content="Os jogadores foram adicionados à lista de ativos.",
            ephemeral=True,
            delete_after=5,
        )


class FixedTeamSelect(discord.ui.Select):
    """
    A dropdown menu to assign players to a specific fixed team.
    """

    async def callback(self, interaction: discord.Interaction):
        repo.add_fixed_players(self.values, self.custom_id)

        await interaction.response.send_message(
            content=f"Os jogadores foram adicionados ao time {self.custom_id}.",
            ephemeral=True,
            delete_after=5,
        )


class TeamSelectView(discord.ui.View):
    """
    A view that generates dropdown menus for selecting active players or fixed team members.
    """

    def __init__(self, teams=None):
        super().__init__(timeout=None)

        if not teams:
            self.add_item(
                TeamSelect(
                    placeholder="Escolha os jogadores ativos!",
                    min_values=1,
                    max_values=10,
                    select_type=discord.ComponentType.user_select,
                )
            )
        else:
            for team in teams:
                self.add_item(
                    FixedTeamSelect(
                        placeholder=f"Escolha os jogadores do time {team}!",
                        min_values=1,
                        max_values=5,
                        select_type=discord.ComponentType.user_select,
                        custom_id=team,
                    )
                )


class DeleteButton(discord.ui.Button):
    """
    A button to remove a specific player from the active players list.
    """

    def __init__(self, player_id, label):
        super().__init__(label=label, custom_id=player_id, style=discord.ButtonStyle.red)
        self.player_id = player_id

    async def callback(self, interaction: discord.Interaction):
        repo.remove_active_player(self.player_id)
        players = repo.get_active_players()

        embed = create_active_players_embed(players)
        view = DeleteButtons(players)

        await interaction.message.edit(embed=embed, view=view)
        await interaction.response.send_message("Jogador removido!", ephemeral=True)


class DeleteButtons(discord.ui.View):
    """
    A view that contains buttons to remove active players.
    """

    def __init__(self, players):
        super().__init__(timeout=None)
        for idx, player_id in enumerate(players):
            self.add_item(DeleteButton(player_id=player_id, label=f"Jogador {idx + 1}"))


class ResultButtons(discord.ui.View):
    """
    A view to set the match result, with buttons for each team.
    """

    def __init__(self, match_id, author_id):
        super().__init__(timeout=None)
        self.match_id = match_id
        self.author_id = author_id

    @discord.ui.button(label="Vitória para o time azul", style=discord.ButtonStyle.blurple)
    async def blue_button_callback(self, button: discord.ui.Button, interaction: discord.Interaction):
        await self._handle_result(interaction, "BLUE")

    @discord.ui.button(label="Vitória para o time vermelho", style=discord.ButtonStyle.red)
    async def red_button_callback(self, button: discord.ui.Button, interaction: discord.Interaction):
        await self._handle_result(interaction, "RED")

    async def _handle_result(self, interaction: discord.Interaction, result: str):
        """
        Handle match result submission based on the user's interaction.
        """
        if interaction.user.id != self.author_id or interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "Somente a pessoa que usou o comando pode definir os ganhadores!",
                ephemeral=True,
            )
            return

        repo.set_match_victory(self.match_id, result)
        await interaction.message.edit(view=None)
