import discord
import repos.firebase_repo as repo


class TeamSelect(discord.ui.Select):
    async def callback(self, interaction: discord.Interaction):
        repo.add_active_players(self.values)

        await interaction.respond(content="Os jogadores foram adicionados a lista de ativos.", ephemeral=True,
                                  delete_after=5)


class FixedTeamSelect(discord.ui.Select):
    async def callback(self, interaction: discord.Interaction):
        repo.add_fixed_players(self.values, self.custom_id)

        await interaction.respond(content=f"Os jogadores foram adicionados ao time {self.custom_id}.", ephemeral=True,
                                  delete_after=5)


class TeamSelectView(discord.ui.View):
    def __init__(self, teams=None):
        super().__init__(timeout=None)

        if (teams is None) or (len(teams) == 0):
            select = TeamSelect(
                placeholder="Escolha os jogadores ativos!",
                min_values=1,
                max_values=10,
                select_type=discord.ComponentType.user_select,
            )

            self.add_item(select)
        else:
            for team in teams:
                select = FixedTeamSelect(
                    placeholder=f"Escolha os jogadores do time {team}!",
                    min_values=1,
                    max_values=5,
                    select_type=discord.ComponentType.user_select,
                    custom_id=team
                )

                self.add_item(select)


class DeleteButton(discord.ui.Button):
    async def callback(self, interaction: discord.Interaction):
        player_id = self.custom_id
        repo.remove_active_player(player_id)

        # Isso aqui tá feio demais kkkkkkkkkkkkkkkkkkkkkkkkkkk
        players = repo.get_active_players()

        embed = discord.Embed(
            title="Jogadores ativos",
            color=discord.Colour.blurple(),
        )

        for idx, player in enumerate(players):
            player_info = repo.get_player_by_id(player)
            embed.add_field(name=f"Jogador {idx + 1}", value=f"<@{player_info.get('discord_id')}>", inline=True)

        await interaction.message.edit(embed=embed, view=DeleteButtons(players))
        await interaction.response.send_message("Jogador removido!", ephemeral=True)


class DeleteButtons(discord.ui.View):
    def __init__(self, players):
        super().__init__(timeout=None)

        for idx, player in enumerate(players):
            button = DeleteButton(
                label=f"Jogador {idx + 1}",
                custom_id=player,
                style=discord.ButtonStyle.red
            )
            self.add_item(button)


class ResultButtons(discord.ui.View):
    def __init__(self, match_id, author_id):
        super().__init__(timeout=None)

        self.match_id = match_id
        self.author_id = author_id

    @discord.ui.button(label="Vitoria para o time azul", style=discord.ButtonStyle.blurple)
    async def blue_button_callback(self, button, interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "Somente a pessoa que usou o comando pode definir os ganhadores!",
                ephemeral=True
            )
            return

        repo.set_match_victory(self.match_id, "BLUE")
        await interaction.message.edit(view=None)

    @discord.ui.button(label="Vitoria para o time vermelho", style=discord.ButtonStyle.red)
    async def red_button_callback(self, button, interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "Somente a pessoa que usou o comando pode definir os ganhadores!",
                ephemeral=True
            )
            return

        repo.set_match_victory(self.match_id, "RED")
        await interaction.message.edit(view=None)
