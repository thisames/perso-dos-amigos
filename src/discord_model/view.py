import discord
import repos.firebase_repo as repo


class TeamSelect(discord.ui.Select):
    async def callback(self, interaction: discord.Interaction):
        repo.add_active_players(self.values)

        await interaction.message.edit(content="Os jogadores foram adicionados a lista de ativos.", view=None)


class TeamSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

        players = repo.get_players()
        players_options = []
        for player in players:
            players_options.append(discord.SelectOption(label=player.get("nome"), value=player.id))

        select = TeamSelect(
            placeholder="Escolha os jogadores ativos!",
            min_values=1,
            max_values=repo.get_players_max_size(),
            options=players_options
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
