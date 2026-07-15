import os
import discord
import requests
import imagehash
import asyncio
import re
import unicodedata
import datetime
from discord.ext import commands
from PIL import Image
from io import BytesIO
from flask import Flask
from threading import Thread

# ==================== SERVIDOR WEB PARA O RENDER ====================
app = Flask(__name__)
@app.route('/')
def home(): return "Bot online e operando!"
def run_server(): app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
Thread(target=run_server, daemon=True).start()

# ==================== CONFIGURAÇÕES GERAIS ====================
CONFIG_SERVIDORES = {
    1143627184842493992: {"nome": "GHOUL", "canal_logs": 1272293056812683345, "canal_punicoes": 1468415943251202252, "categoria_tickets": 1527037033057353728, "cargo_staff": 1274081192450195671},
    1169685424738947172: {"nome": "BLOX KINGS", "canal_logs": 1526271422253629681, "canal_punicoes": 1526255782222626907, "categoria_tickets": 1170495547426217995, "cargo_staff": 1317249055058825236},
    1331323352840933497: {"nome": "NIGHTWARE STORE", "canal_logs": 1527037894743687168, "canal_punicoes": 1527038039111635114, "categoria_tickets": 1331327159448375356, "cargo_staff": 1333982207701684294}
}

IMAGENS_TICKETS = {
    "GHOUL": "https://cdn.discordapp.com/attachments/1444429504838631586/1454170002746769530/Banner_ticket_20250205_120340_0000.png",
    "COD": "https://cdn.discordapp.com/attachments/1183819407013707947/1469731813709578417/GHOUL_20260207_132912_0000.png",
    "BLOX_KINGS": "https://cdn.discordapp.com/attachments/1183819407013707947/1526281157635870730/file_000000002958720eab459d97fd2c5b8e.png",
    "NIGHTWARE": "https://cdn.discordapp.com/attachments/1440377531848200295/1452759780111155323/standard.gif"
}

# Termos que dão BAN INSTANTÂNEO
TERMOS_BAN = ["checkmybio", "checkmyprofile", "lookmybio", "lookatmybio", "checkbio", "olharabiografia", "olheminhabio", "olhaabiografia", "vejaabiografia", "miramibio", "miraatubio", "freenitro", "nitrogratis", "onlyfansfree"]

# Palavrões que APENAS APAGAM a mensagem (Lista Ampliada)
PALAVROES = [
    "fdp", "filhodaputa", "caralho", "krl", "bosta", "escroto", "merda", 
    "arrombado", "viado", "corno", "desgracado", "vagabundo", "porra", 
    "buceta", "cacete", "puta", "puto", "cuzao", "pica", "rola", 
    "xoxota", "piranha", "vadia", "retardado", "foder", "fodase", 
    "tnc", "tomarnocu", "vsf", "vtnc", "pqp", "fuck", "bitch", "asshole", 
    "bastard", "dick", "pussy", "shit", "cunt", "motherfucker"
]

IMAGENS_BLOQUEADAS = ['9977339a644d9a62', '936c6c4e946cd966', '9748a8dcbd4a2579', 'c48ff019712fe2c6', '91ac6db293ab09a6']

# ==================== SETUP DO BOT ====================
class MeuBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all(), help_command=None)
    async def setup_hook(self):
        self.add_view(ViewGhoul())
        self.add_view(ViewKings())
        self.add_view(ViewNightware())
        self.add_view(ViewFechar())

bot = MeuBot()

def obter_config(guild_id): return CONFIG_SERVIDORES.get(guild_id)

def normalizar_texto(texto):
    texto = texto.lower()
    texto = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    for orig, sub in {'1': 'i', '3': 'e', '4': 'a', '0': 'o', '5': 's', '7': 't', '$': 's', '@': 'a'}.items():
        texto = texto.replace(orig, sub)
    return re.sub(r'[^a-z0-9\s]', '', texto)

# ==================== SISTEMA DE PUNIÇÕES BONITO ====================
async def log_punicao_bonito(guild, user, staff, acao, motivo, prova_url=None):
    config = obter_config(guild.id)
    if not config: return
    canal = bot.get_channel(config["canal_punicoes"])
    if not canal: return

    embed = discord.Embed(color=discord.Color.red())
    embed.set_author(name="🚨 REGISTRO DE PUNIÇÃO", icon_url=guild.icon.url if guild.icon else None)
    descricao = f"**Usuário:** {user.mention} (`{user.id}`)\n**Staff:** {staff.mention}\n**Ação:** {acao}\n**Motivo:** {motivo}"
    embed.description = descricao
    if prova_url:
        embed.set_image(url=prova_url)
        embed.add_field(name="Prova:", value="Ver imagem abaixo.", inline=False)
    embed.set_footer(text=f"Sistema de Segurança • {datetime.datetime.now().strftime('%d/%m/%Y, %H:%M')}")
    await canal.send(embed=embed)

# ==================== LOGS AUTOMÁTICOS DE STAFF (AUDIT LOGS) ====================
@bot.event
async def on_member_ban(guild, user):
    await asyncio.sleep(2)
    async for entry in guild.audit_logs(limit=3, action=discord.AuditLogAction.ban):
        if entry.target.id == user.id:
            if entry.user.id == bot.user.id: return 
            await log_punicao_bonito(guild, user, entry.user, "Banimento (Via Discord)", entry.reason or "Sem motivo preenchido.")
            return

@bot.event
async def on_member_unban(guild, user):
    await asyncio.sleep(2)
    async for entry in guild.audit_logs(limit=3, action=discord.AuditLogAction.unban):
        if entry.target.id == user.id:
            if entry.user.id == bot.user.id: return
            await log_punicao_bonito(guild, user, entry.user, "Desbanimento (Via Discord)", entry.reason or "Sem motivo preenchido.")
            return

@bot.event
async def on_member_update(before, after):
    if before.timed_out_until != after.timed_out_until:
        await asyncio.sleep(2)
        if after.timed_out_until is not None:
            async for entry in before.guild.audit_logs(limit=3, action=discord.AuditLogAction.member_update):
                if entry.target.id == after.id and hasattr(entry.after, 'timed_out_until'):
                    if entry.user.id == bot.user.id: return
                    await log_punicao_bonito(before.guild, after, entry.user, "Mute (Via Discord)", entry.reason or "Sem motivo preenchido.")
                    return
        elif after.timed_out_until is None:
            async for entry in before.guild.audit_logs(limit=3, action=discord.AuditLogAction.member_update):
                if entry.target.id == after.id and hasattr(entry.before, 'timed_out_until') and not hasattr(entry.after, 'timed_out_until'):
                    if entry.user.id == bot.user.id: return
                    await log_punicao_bonito(before.guild, after, entry.user, "Desmutado (Via Discord)", entry.reason or "Sem motivo preenchido.")
                    return

# ==================== SISTEMA DE ATENDIMENTO (TICKETS) ====================
class DropdownGhoul(discord.ui.Select):
    def __init__(self):
        opcoes = [discord.SelectOption(label="Denúncias", value="denuncias", emoji="🚨"), discord.SelectOption(label="Suporte", value="suporte", emoji="🛠️"), discord.SelectOption(label="Dúvidas", value="duvidas", emoji="❓"), discord.SelectOption(label="Exposed", value="exposed", emoji="⚠️")]
        super().__init__(placeholder="Selecione o setor...", min_values=1, max_values=1, options=opcoes, custom_id="sel_ghoul")
    async def callback(self, interaction: discord.Interaction): await criar_canal_ticket(interaction, self.values[0], "GHOUL")

class DropdownKings(discord.ui.Select):
    def __init__(self):
        opcoes = [discord.SelectOption(label="Comprar Robux", value="robux", emoji="💰"), discord.SelectOption(label="Frutas", value="frutas", emoji="🍎"), discord.SelectOption(label="Contas", value="contas", emoji="📦"), discord.SelectOption(label="Suporte Geral", value="suporte", emoji="🛠️")]
        super().__init__(placeholder="Selecione o produto...", min_values=1, max_values=1, options=opcoes, custom_id="sel_kings")
    async def callback(self, interaction: discord.Interaction): await criar_canal_ticket(interaction, self.values[0], "BLOX KINGS")

class DropdownNightware(discord.ui.Select):
    def __init__(self):
        opcoes = [discord.SelectOption(label="Comprar", value="compras", emoji="🛒"), discord.SelectOption(label="Financeiro", value="financeiro", emoji="💳"), discord.SelectOption(label="Suporte", value="suporte", emoji="🛠️")]
        super().__init__(placeholder="Selecione a categoria...", min_values=1, max_values=1, options=opcoes, custom_id="sel_nightware")
    async def callback(self, interaction: discord.Interaction): await criar_canal_ticket(interaction, self.values[0], "NIGHTWARE STORE")

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
    if not config or interaction.response.is_done(): return
    categoria = discord.utils.get(interaction.guild.categories, id=config["categoria_tickets"])
    cargo_staff = interaction.guild.get_role(config["cargo_staff"])
    
    overwrites = {
        interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
        interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True),
        interaction.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
    }
    if cargo_staff: overwrites[cargo_staff] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

    canal = await interaction.guild.create_text_channel(name=f"ticket-{interaction.user.name}-{setor}", category=categoria, overwrites=overwrites)
    embed = discord.Embed(title=f"🚨 Atendimento | {sv_nome}", description=f"Olá {interaction.user.mention}, seu ticket para **{setor.upper()}** foi aberto!\nDescreva seu problema para a Staff.", color=discord.Color.red())
    await canal.send(content=f"{interaction.user.mention} {cargo_staff.mention if cargo_staff else ''}", embed=embed, view=ViewFechar())
    await interaction.response.send_message(f"✅ Ticket criado em {canal.mention}!", ephemeral=True)

# ==================== EVENTOS E AUTO-MODERAÇÃO ====================
@bot.event
async def on_ready():
    print(f"✅ {bot.user.name} online, audit logs ativados e anti-palavrão/anti-link prontos!")

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild: return
    config = obter_config(message.guild.id)
    if not config:
        await bot.process_commands(message)
        return

    is_staff = message.author.guild_permissions.manage_messages

    if not is_staff:
        texto_norm = normalizar_texto(message.content)
        
        # 1. AUTO-BAN: Bio Check / Fakes
        for termo in TERMOS_BAN:
            if termo in texto_norm:
                await message.delete()
                try:
                    await message.author.ban(reason="Bot Fake / Bio Check automático detectado.")
                    await log_punicao_bonito(message.guild, message.author, bot.user, "Banimento (Automático)", f"Tentativa de golpe/spam com o termo: `{termo}`")
                except: pass
                return

        # 2. ANTI-PALAVRÃO: Apaga Totalmente a Mensagem
        for palavrao in PALAVROES:
            if palavrao in texto_norm:
                try:
                    await message.delete()
                except: pass
                return 

        # 3. AUTO-BAN: Imagens bloqueadas
        if message.attachments:
            for anexo in message.attachments:
                if any(anexo.filename.lower().endswith(ext) for ext in ["png", "jpg", "jpeg", "webp"]):
                    try:
                        response = requests.get(anexo.url)
                        img = Image.open(BytesIO(response.content))
                        hash_img = str(imagehash.average_hash(img))
                        if hash_img in IMAGENS_BLOQUEADAS:
                            await message.delete()
                            await message.author.ban(reason="Imagem maliciosa/proibida enviada.")
                            await log_punicao_bonito(message.guild, message.author, bot.user, "Banimento (Automático)", "Envio de imagem na Blacklist.", anexo.url)
                            return
                    except: pass

        # 4. ANTI-LINK: Apaga, Muta 1 Hora e Loga Punição
        if re.search(r'(discord\.gg/|discord\.com/invite/)', message.content.lower()):
            await message.delete()
            try:
                await message.author.timeout(datetime.timedelta(hours=1), reason="Divulgação de link.")
                await log_punicao_bonito(message.guild, message.author, bot.user, "Mute (1 Hora Automático)", "Divulgação de link de convite Discord.")
            except: pass
            return

    await bot.process_commands(message)

# ==================== COMANDOS MANUAIS ====================
@bot.command()
@commands.has_permissions(moderate_members=True)
async def mute(ctx, membro: discord.Member, tempo_minutos: int, *, motivo="Sem motivo"):
    await ctx.message.delete()
    try:
        await membro.timeout(datetime.timedelta(minutes=tempo_minutos), reason=f"{ctx.author.name} | {motivo}")
        await ctx.send(f"🔇 {membro.mention} mutado por {tempo_minutos} min.", delete_after=5)
        await log_punicao_bonito(ctx.guild, membro, ctx.author, f"Mute ({tempo_minutos} min)", motivo)
    except: pass

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, membro: discord.Member, *, motivo="Sem motivo especificado"):
    await ctx.message.delete()
    prova_url = ctx.message.attachments[0].url if ctx.message.attachments else None
    try:
        await membro.ban(reason=f"{ctx.author.name} | {motivo}")
        await ctx.send(f"🔨 {membro.name} banido com sucesso!", delete_after=5)
        await log_punicao_bonito(ctx.guild, membro, ctx.author, "Banimento Manual", motivo, prova_url)
    except: pass

@bot.command()
@commands.has_permissions(ban_members=True)
async def unban(ctx, user_id: int):
    await ctx.message.delete()
    user = await bot.fetch_user(user_id)
    await ctx.guild.unban(user)
    await ctx.send(f"🕊️ {user.name} desbanido!", delete_after=5)

# ==================== COMANDOS DE PAINEIS ====================
@bot.command(name="ticket_ghoul")
@commands.has_permissions(administrator=True)
async def ticket_ghoul(ctx):
    await ctx.message.delete()
    embed = discord.Embed(title="🛡️ CENTRAL DE ATENDIMENTO - GHOUL", description="Abra seu ticket abaixo.", color=discord.Color.red())
    if IMAGENS_TICKETS["GHOUL"]: embed.set_image(url=IMAGENS_TICKETS["GHOUL"])
    await ctx.send(embed=embed, view=ViewGhoul())

@bot.command(name="ticket_kings")
@commands.has_permissions(administrator=True)
async def ticket_kings(ctx):
    await ctx.message.delete()
    embed = discord.Embed(title="👑 CENTRAL DE ATENDIMENTO - BLOX KINGS", description="Compre Robux e frutas abaixo.", color=discord.Color.red())
    if IMAGENS_TICKETS["BLOX_KINGS"]: embed.set_image(url=IMAGENS_TICKETS["BLOX_KINGS"])
    await ctx.send(embed=embed, view=ViewKings())

@bot.command(name="ticket_nightware")
@commands.has_permissions(administrator=True)
async def ticket_nightware(ctx):
    await ctx.message.delete()
    embed = discord.Embed(title="🛍️ CENTRAL DE ATENDIMENTO - NIGHTWARE", description="Compre nossos produtos abaixo.", color=discord.Color.red())
    if IMAGENS_TICKETS["NIGHTWARE"]: embed.set_image(url=IMAGENS_TICKETS["NIGHTWARE"])
    await ctx.send(embed=embed, view=ViewNightware())

# ==================== LOGS DE MENSAGENS ====================
@bot.event
async def on_message_delete(message):
    if message.author.bot or not message.guild: return
    config = obter_config(message.guild.id)
    if config and (canal_logs := bot.get_channel(config["canal_logs"])):
        embed = discord.Embed(title="🗑️ Mensagem Apagada", description=f"{message.author.mention} em {message.channel.mention}.", color=discord.Color.red())
        if message.content: embed.add_field(name="Conteúdo", value=message.content[:1024], inline=False)
        await canal_logs.send(embed=embed)

TOKEN = os.getenv('TOKEN')
bot.run(TOKEN)
