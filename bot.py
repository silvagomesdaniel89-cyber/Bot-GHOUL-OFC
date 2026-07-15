import re
import unicodedata
import os
import discord
import requests
import imagehash
import asyncio
from PIL import Image
from io import BytesIO
from flask import Flask
from datetime import timedelta
from threading import Thread
from discord.ext import commands

# ==================== CONFIGURAÇÃO MULTISSERVIDORES ====================
CONFIG_SERVIDORES = {
    1143627184842493992: {  # ID do Servidor: GHOUL
        "nome": "GHOUL",
        "canal_logs": 1272293056812683345,       # Canal de logs gerais (mensagens, voz, perfil)
        "canal_punicoes": 1468415943251202252,   # Canal para avisos de bans/mutes
        "categoria_tickets": 1527037033057353728,
        "cargo_staff": 1274081192450195671,
    },
    1169685424738947172: {  # ID do Servidor: BLOX KINGS
        "nome": "BLOX KINGS",
        "canal_logs": 1526271422253629681,
        "canal_punicoes": 1526255782222626907,
        "categoria_tickets": 1170495547426217995,
        "cargo_staff": 1317249055058825236,
    },
    1331323352840933497: {  # ID do Servidor: NIGHTWARE STORE
        "nome": "NIGHTWARE STORE",
        "canal_logs": 1527037894743687168,
        "canal_punicoes": 1527038039111635114,
        "categoria_tickets": 1331327159448375356,
        "cargo_staff": 1333982207701684294,
    }
}

# ==================== IMAGENS DE BANNER DOS TICKET ====================
# Substitua pelas URLs reais das suas artes/banners.
IMAGENS_TICKETS = {
    "GHOUL": "https://cdn.discordapp.com/attachments/1444429504838631586/1454170002746769530/Banner_ticket_20250205_120340_0000.png?ex=6a591a59&is=6a57c8d9&hm=db7d7925f0954c26860c2b0ecd11f974ee0c5df4b650fbfbfab69aa54f06928e",
    "COD": "https://cdn.discordapp.com/attachments/1183819407013707947/1469731813709578417/GHOUL_20260207_132912_0000.png?ex=6a5906ea&is=6a57b56a&hm=9265b6a1d49b9a1ed3427911f5b531e398c73c238052889171a16ec80accf525",
    "BLOX_KINGS": "https://cdn.discordapp.com/attachments/1183819407013707947/1526281157635870730/file_000000002958720eab459d97fd2c5b8e.png?ex=6a591698&is=6a57c518&hm=21e4a41c202aca8c264ed1d997e15cb3916c4c5a55cb54f3340e27b1bd75c8ec",
    "NIGHTWARE": "https://cdn.discordapp.com/attachments/1440377531848200295/1452759780111155323/standard.gif?ex=6a58963a&is=6a5744ba&hm=296484ff3b62c71a50985ba5c23340456b491c271bc122bb17437885718c965f"
}
# ======================================================================

TERMOS_PROIBIDOS = [
    "checkmybio", "checkmyprofile", "lookmybio", "lookatmybio", "checkbio",
    "olharabiografia", "olheminhabio", "olhaabiografia", "vejaabiografia",
    "miramibio", "miraatubio", "freenitro", "nitrogratis", "onlyfansfree",
    "fdp", "filhodaputa", "caralho", "bosta", "escroto", "merda", "arrombado",
    "viado", "corno", "desgracado", "vagabundo", "porra", "fuck", "bitch",
    "asshole", "bastard", "dick", "pussy", "shit", "cunt", "motherfucker",
    "mierda", "maricon", "cabron", "gilipollas", "hijodeputa", "pendejo"
]

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

def obter_config(guild_id):
    return CONFIG_SERVIDORES.get(guild_id)

def normalizar_texto(texto):
    texto = texto.lower()
    texto = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    substituicoes = {'1': 'i', '3': 'e', '4': 'a', '0': 'o', '5': 's', '7': 't', '$': 's', '@': 'a'}
    for orig, sub in substituicoes.items():
        texto = texto.replace(orig, sub)
    return re.sub(r'[^a-z0-9\s]', '', texto)

# ==================== SISTEMA DE ATENDIMENTO (TICKETS) ====================

class DropdownGhoul(discord.ui.Select):
    def __init__(self):
        opcoes = [
            discord.SelectOption(label="Denúncias", value="denuncias", description="Denúncias, ajuda técnica e revisão.", emoji="🚨"),
            discord.SelectOption(label="Suporte", value="suporte", description="Recorra a uma punição (warn/mute).", emoji="🛠️"),
            discord.SelectOption(label="Dúvidas", value="duvidas", description="Tire dúvidas sobre a comunidade ou regras.", emoji="❓"),
            discord.SelectOption(label="Exposed", value="exposed", description="Falar sobre membro expondo outro.", emoji="⚠️")
        ]
        super().__init__(placeholder="Selecione o setor do suporte...", min_values=1, max_values=1, options=opcoes, custom_id="sel_ghoul")

    async def callback(self, interaction: discord.Interaction):
        await criar_canal_ticket(interaction, self.values[0], "GHOUL")

class DropdownKings(discord.ui.Select):
    def __init__(self):
        opcoes = [
            discord.SelectOption(label="Comprar Robux", value="robux", description="Adquira Robux com segurança.", emoji="💰"),
            discord.SelectOption(label="Frutas Permanentes", value="frutas", description="Frutas permanentes e físicas.", emoji="🍎"),
            discord.SelectOption(label="Contas / Gamepasses", value="contas", description="Contas e passes de jogo.", emoji="📦"),
            discord.SelectOption(label="Suporte Geral", value="suporte", description="Fale com nossa equipe.", emoji="🛠️"),
            discord.SelectOption(label="Outros", value="outros", description="Outros assuntos ou dúvidas.", emoji="📌")
        ]
        super().__init__(placeholder="Selecione o produto ou suporte...", min_values=1, max_values=1, options=opcoes, custom_id="sel_kings")

    async def callback(self, interaction: discord.Interaction):
        await criar_canal_ticket(interaction, self.values[0], "BLOX KINGS")

class DropdownNightware(discord.ui.Select):
    def __init__(self):
        opcoes = [
            discord.SelectOption(label="Comprar Produtos", value="compras", description="Adquira nossos produtos.", emoji="🛒"),
            discord.SelectOption(label="Financeiro", value="financeiro", description="Dúvidas sobre pagamentos.", emoji="💳"),
            discord.SelectOption(label="Suporte Geral", value="suporte", description="Fale com o suporte.", emoji="🛠️"),
            discord.SelectOption(label="Outros", value="outros", description="Outros assuntos.", emoji="📌")
        ]
        super().__init__(placeholder="Selecione a categoria de atendimento...", min_values=1, max_values=1, options=opcoes, custom_id="sel_nightware")

    async def callback(self, interaction: discord.Interaction):
        await criar_canal_ticket(interaction, self.values[0], "NIGHTWARE STORE")

class ViewGhoul(discord.ui.View):
    def __init__(self): super().__init__(timeout=None); self.add_item(DropdownGhoul())

class ViewKings(discord.ui.View):
    def __init__(self): super().__init__(timeout=None); self.add_item(DropdownKings())

class ViewNightware(discord.ui.View):
    def __init__(self): super().__init__(timeout=None); self.add_item(DropdownNightware())

class ViewFechar(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Fechar Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="btn_fechar")
    async def fechar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 Fechando canal em 5 segundos...", ephemeral=True)
        await asyncio.sleep(5)
        await interaction.channel.delete()

async def criar_canal_ticket(interaction: discord.Interaction, setor: str, sv_nome: str):
    config = obter_config(interaction.guild.id)
    if not config: return
    
    categoria = discord.utils.get(interaction.guild.categories, id=config["categoria_tickets"])
    cargo_staff = interaction.guild.get_role(config["cargo_staff"])
    
    overwrites = {
        interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
        interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True),
        interaction.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
    }
    if cargo_staff:
        overwrites[cargo_staff] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

    canal = await interaction.guild.create_text_channel(
        name=f"ticket-{interaction.user.name}-{setor}",
        category=categoria,
        overwrites=overwrites
    )
    
    embed = discord.Embed(
        title=f"👑 Atendimento | {sv_nome}",
        description=f"Olá {interaction.user.mention}, seu canal de atendimento para **{setor.upper()}** foi criado com sucesso!\nDescreva seu problema ou dúvida para que a Staff possa ajudar.",
        color=discord.Color.blue()
    )
    await canal.send(content=f"{interaction.user.mention} {cargo_staff.mention if cargo_staff else ''}", embed=embed, view=ViewFechar())
    await interaction.response.send_message(f"✅ Ticket criado em {canal.mention}!", ephemeral=True)

# ==================== EVENTOS DE INICIALIZAÇÃO ====================

@bot.event
async def on_ready():
    bot.add_view(ViewGhoul())
    bot.add_view(ViewKings())
    bot.add_view(ViewNightware())
    bot.add_view(ViewFechar())
    print(f"✅ Bot {bot.user.name} online e pronto nos 3 servidores com sistema de logs integrado!")

# ==================== FILTRO ANTI-LINK E ANTI-FDP ====================

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    config = obter_config(message.guild.id)
    if not config:
        await bot.process_commands(message)
        return

    texto_norm = normalizar_texto(message.content)
    
    # Anti-link (Mute de 1 Hora)
    if re.search(r'(discord\.gg/|discord\.com/invite/)', message.content.lower()):
        if not message.author.guild_permissions.manage_messages:
            await message.delete()
            try:
                await message.author.timeout(datetime.timedelta(hours=1), reason="Divulgação de link de servidor.")
            except:
                pass
            
            canal_punicoes = bot.get_channel(config["canal_punicoes"])
            if canal_punicoes:
                embed = discord.Embed(
                    title="🚫 Punição Automática: Mute (1 Hora)",
                    description=f"O usuário {message.author.mention} foi mutado automaticamente por enviar links de outros servidores.",
                    color=discord.Color.red(),
                    timestamp=discord.utils.utcnow()
                )
                await canal_punicoes.send(embed=embed)
            return

    # Anti-Fake / Palavras Proibidas
    for termo in TERMOS_PROIBIDOS:
        if termo in texto_norm:
            if not message.author.guild_permissions.manage_messages:
                await message.delete()
                return

    await bot.process_commands(message)

# ==================== SISTEMA DE LOGS COMPLETOS ====================

@bot.event
async def on_message_delete(message):
    if message.author.bot or not message.guild: return
    config = obter_config(message.guild.id)
    if not config: return
    canal_logs = bot.get_channel(config["canal_logs"])
    if not canal_logs: return

    embed = discord.Embed(
        title="🗑️ Mensagem Apagada",
        description=f"Mensagem enviada por {message.author.mention} foi excluída em {message.channel.mention}.",
        color=discord.Color.red(),
        timestamp=discord.utils.utcnow()
    )
    embed.set_author(name=message.author.name, icon_url=message.author.display_avatar.url)
    
    if message.content:
        embed.add_field(name="Texto Original", value=message.content[:1024], inline=False)
    
    if message.attachments:
        for anexo in message.attachments:
            if any(anexo.filename.lower().endswith(ext) for ext in ["png", "jpg", "jpeg", "gif", "webp"]):
                embed.set_image(url=anexo.url)
                embed.add_field(name="Imagem Anexada", value=f"[Clique para ver]({anexo.url})", inline=False)
                break

    await canal_logs.send(embed=embed)

@bot.event
async def on_message_edit(before, after):
    if before.author.bot or not before.guild or before.content == after.content: return
    config = obter_config(before.guild.id)
    if not config: return
    canal_logs = bot.get_channel(config["canal_logs"])
    if not canal_logs: return

    embed = discord.Embed(
        title="✏️ Mensagem Editada",
        description=f"Mensagem de {before.author.mention} modificada em {before.channel.mention}.",
        color=discord.Color.orange(),
        timestamp=discord.utils.utcnow()
    )
    embed.set_author(name=before.author.name, icon_url=before.author.display_avatar.url)
    embed.add_field(name="Antes", value=before.content[:1024] or "*Sem conteúdo*", inline=False)
    embed.add_field(name="Depois", value=after.content[:1024] or "*Sem conteúdo*", inline=False)
    await canal_logs.send(embed=embed)

@bot.event
async def on_member_update(before, after):
    config = obter_config(before.guild.id)
    if not config: return
    canal_logs = bot.get_channel(config["canal_logs"])
    if not canal_logs: return

    # Log de Apelido (Nickname)
    if before.nick != after.nick:
        embed = discord.Embed(
            title="📝 Apelido Alterado",
            description=f"O membro {after.mention} mudou seu apelido no servidor.",
            color=discord.Color.teal(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_author(name=after.name, icon_url=after.display_avatar.url)
        embed.add_field(name="Apelido Anterior", value=before.nick or "*Sem apelido*", inline=True)
        embed.add_field(name="Apelido Novo", value=after.nick or "*Sem apelido*", inline=True)
        await canal_logs.send(embed=embed)

@bot.event
async def on_user_update(before, after):
    # Logs globais de conta (Avatar ou Nome de Usuário)
    for guild in bot.guilds:
        if guild.get_member(after.id):
            config = obter_config(guild.id)
            if not config: continue
            canal_logs = bot.get_channel(config["canal_logs"])
            if not canal_logs: continue

            # Nome alterado
            if before.name != after.name:
                embed = discord.Embed(title="👤 Nome de Usuário Alterado", color=discord.Color.blue(), timestamp=discord.utils.utcnow())
                embed.add_field(name="Antes", value=before.name, inline=True)
                embed.add_field(name="Depois", value=after.name, inline=True)
                await canal_logs.send(embed=embed)

            # Avatar alterado
            if before.avatar != after.avatar:
                embed = discord.Embed(
                    title="🖼️ Foto de Perfil Alterada",
                    description=f"{after.mention} atualizou seu avatar global.",
                    color=discord.Color.purple(),
                    timestamp=discord.utils.utcnow()
                )
                embed.set_thumbnail(url=before.display_avatar.url)
                embed.set_image(url=after.display_avatar.url)
                await canal_logs.send(embed=embed)

@bot.event
async def on_voice_state_update(member, before, after):
    config = obter_config(member.guild.id)
    if not config: return
    canal_logs = bot.get_channel(config["canal_logs"])
    if not canal_logs: return

    embed = discord.Embed(timestamp=discord.utils.utcnow())
    embed.set_author(name=f"{member.name} ({member.id})", icon_url=member.display_avatar.url)

    # Entrou em call/palco
    if not before.channel and after.channel:
        embed.title = "🔊 Conectou à Call"
        embed.description = f"{member.mention} entrou no canal de voz/palco {after.channel.mention}."
        embed.color = discord.Color.green()
        await canal_logs.send(embed=embed)
    # Saiu da call/palco
    elif before.channel and not after.channel:
        embed.title = "🔇 Saiu da Call"
        embed.description = f"{member.mention} desconectou-se do canal {before.channel.mention}."
        embed.color = discord.Color.red()
        await canal_logs.send(embed=embed)
    # Trocou de call
    elif before.channel and after.channel and before.channel != after.channel:
        embed.title = "🔄 Trocou de Call"
        embed.description = f"{member.mention} mudou de {before.channel.mention} para {after.channel.mention}."
        embed.color = discord.Color.blue()
        await canal_logs.send(embed=embed)

@bot.event
async def on_member_ban(guild, user):
    config = obter_config(guild.id)
    if not config: return
    canal_punicoes = bot.get_channel(config["canal_punicoes"])
    if canal_punicoes:
        embed = discord.Embed(
            title="🔨 Membro Banido",
            description=f"O usuário **{user.name}** (`{user.id}`) foi banido do servidor.",
            color=discord.Color.dark_red(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        await canal_punicoes.send(embed=embed)

@bot.event
async def on_member_unban(guild, user):
    config = obter_config(guild.id)
    if not config: return
    canal_logs = bot.get_channel(config["canal_logs"])
    if canal_logs:
        embed = discord.Embed(
            title="🕊️ Membro Desbanido",
            description=f"O banimento de **{user.name}** (`{user.id}`) foi revogado.",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        await canal_logs.send(embed=embed)

# ==================== COMANDOS EXCLUSIVOS DE PAINEL ====================

@bot.command(name="ticket_ghoul")
@commands.has_permissions(administrator=True)
async def ticket_ghoul(ctx):
    await ctx.message.delete()
    embed = discord.Embed(
        title="🛡️ CENTRAL DE ATENDIMENTO - GHOUL",
        description="𝐃𝐞𝐧𝐮́𝐧𝐜𝐢𝐚𝐬:\n↳ 𝐃𝐞𝐧𝐮́𝐧𝐜𝐢𝐚𝐬, 𝐚𝐣𝐮𝐝𝐚 𝐭𝐞́𝐜𝐧𝐢𝐜𝐚 𝐞 𝐫𝐞𝐯𝐢𝐬𝐚̃𝐨 𝐝𝐞 𝐩𝐮𝐧𝐢𝐜̧𝐨̃𝐞𝐬.\n\n"
                    "𝐒𝐮𝐩𝐨𝐫𝐭𝐞:\n↳ 𝐑𝐞𝐜𝐨𝐫𝐫𝐚 𝐚 𝐮𝐦𝐚 𝐩𝐮𝐧𝐢𝐜̧𝐚̃𝐨 (𝐰𝐚𝐫𝐧/𝐦𝐮𝐭𝐞).\n\n"
                    "𝐃𝐮́𝐯𝐢𝐝𝐚𝐬:\n↳ 𝐓𝐢𝐫𝐞 𝐝𝐮́𝐯𝐢𝐝𝐚𝐬 𝐬𝐨𝐛𝐫𝐞 𝐚 𝐜𝐨𝐦𝐮𝐧𝐢𝐝𝐚𝐝𝐞 𝐨𝐮 𝐫𝐞𝐠𝐫𝐚𝐬 𝐝𝐨 𝐬𝐞𝐫𝐯𝐢𝐝𝐨𝐫.\n\n"
                    "𝐄𝐱𝐩𝐨𝐬𝐞𝐝:\n↳ 𝐅𝐚𝐥𝐚𝐫 𝐬𝐨𝐛𝐫𝐞 𝐚𝐥𝐠𝐮𝐦 𝐦𝐞𝐦𝐛𝐫𝐨 𝐪𝐮𝐞 𝐞𝐬𝐭𝐚́ 𝐞𝐱𝐩𝐨𝐧𝐝𝐨 𝐨𝐮𝐭𝐫𝐨 𝐦𝐞𝐦𝐛𝐫𝐨.\n\n"
                    "𝐋𝐞𝐦𝐛𝐫𝐞-𝐬𝐞: 𝐍𝐨𝐬𝐬𝐚 𝐞𝐪𝐮𝐢𝐩𝐞 𝐞𝐬𝐭𝐚́ 𝐩𝐫𝐨𝐧𝐭𝐚 𝐩𝐚𝐫𝐚 𝐢𝐧𝐯𝐞𝐬𝐭𝐢𝐠𝐚𝐫 𝐞 𝐫𝐞𝐬𝐨𝐥𝐯𝐞𝐫 𝐪𝐮𝐚𝐥𝐪𝐮𝐞𝐫 𝐬𝐢𝐭𝐮𝐚𝐜̧𝐚̃𝐨 𝐝𝐞 𝐟𝐨𝐫𝐦𝐚 𝐫𝐚́𝐩𝐢𝐝𝐚 𝐞 𝐣𝐮𝐬𝐭𝐚. 𝐒𝐮𝐚 𝐩𝐫𝐢𝐯𝐚𝐜𝐢𝐝𝐚𝐝𝐞 𝐬𝐞𝐫𝐚́ 𝐫𝐞𝐬𝐩𝐞𝐢𝐭𝐚𝐝𝐚 𝐝𝐮𝐫𝐚𝐧𝐭𝐞 𝐭𝐨𝐝𝐨 𝐨 𝐩𝐫𝐨𝐜𝐞𝐬𝐬𝐨!",
        color=discord.Color.from_rgb(142, 68, 173)
    )
    if IMAGENS_TICKETS["GHOUL"]:
        embed.set_image(url=IMAGENS_TICKETS["GHOUL"])
    await ctx.send(embed=embed, view=ViewGhoul())

@bot.command(name="ticket_cod")
@commands.has_permissions(administrator=True)
async def ticket_cod(ctx):
    await ctx.message.delete()
    embed = discord.Embed(
        title="⚓ Verificação de COD ⚓",
        description="Quando chamar **Levi**, apareça com o print comprovando que não está de COD!\n\n"
                    "Anexe sua imagem de comprovação no chat para validação da Staff.",
        color=discord.Color.blue()
    )
    if IMAGENS_TICKETS["COD"]:
        embed.set_image(url=IMAGENS_TICKETS["COD"])
    await ctx.send(embed=embed)

@bot.command(name="ticket_kings")
@commands.has_permissions(administrator=True)
async def ticket_kings(ctx):
    await ctx.message.delete()
    embed = discord.Embed(
        title="👑 CENTRAL DE ATENDIMENTO - BLOX KINGS 👑",
        description="Precisa de ajuda, deseja comprar **Robux**, **Frutas Permanentes** ou **Contas**?\n\n"
                    "Selecione a categoria correta no menu abaixo para abrir o seu ticket.\n"
                    "Lembre-se: Não abra tickets sem necessidade para evitar punições.",
        color=discord.Color.gold()
    )
    if IMAGENS_TICKETS["BLOX_KINGS"]:
        embed.set_image(url=IMAGENS_TICKETS["BLOX_KINGS"])
    await ctx.send(embed=embed, view=ViewKings())

@bot.command(name="ticket_nightware")
@commands.has_permissions(administrator=True)
async def ticket_nightware(ctx):
    await ctx.message.delete()
    embed = discord.Embed(
        title="🛍️ CENTRAL DE ATENDIMENTO - NIGHTWARE STORE 👑",
        description="Precisa de ajuda, deseja comprar nossos serviços ou produtos?\n\n"
                    "Selecione a categoria correta no menu abaixo para abrir o seu ticket.\n"
                    "Lembre-se: Não abra tickets sem necessidade para evitar punições.",
        color=discord.Color.dark_purple()
    )
    if IMAGENS_TICKETS["NIGHTWARE"]:
        embed.set_image(url=IMAGENS_TICKETS["NIGHTWARE"])
    await ctx.send(embed=embed, view=ViewNightware())

# ==================== COMANDOS DE MODERAÇÃO ====================

@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban(ctx, membro: discord.Member, *, motivo="Sem motivo especificado"):
    await ctx.message.delete()
    await membro.ban(reason=f"{ctx.author.name} | {motivo}")
    await ctx.send(f"✅ {membro.name} foi banido com sucesso!", delete_after=5)

@bot.command(name="unban")
@commands.has_permissions(ban_members=True)
async def unban(ctx, user_id: int):
    await ctx.message.delete()
    user = await bot.fetch_user(user_id)
    await ctx.guild.unban(user)
    await ctx.send(f"🕊️ {user.name} foi desbanido!", delete_after=5)

import os
# ... outros imports

TOKEN = os.getenv('DISCORD_TOKEN') # Ou o nome que você deu à variável no painel do Render
bot.run(TOKEN)
