import os
import discord
import requests
import imagehash
import asyncio
import re
import unicodedata
import datetime
from discord.ext import commands
from discord import app_commands
from PIL import Image
from io import BytesIO
from flask import Flask
from threading import Thread

# ==================== SERVIDOR WEB PARA MANTER ONLINE ====================
app = Flask(__name__)
@app.route('/')
def home(): 
    return "Bot online e operando com perfeição!"

def run_server(): 
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

Thread(target=run_server, daemon=True).start()

# ==================== CONFIGURAÇÕES DOS SERVIDORES ====================
CONFIG_SERVIDORES = {
    1143627184842493992: {
        "nome": "GHOUL SECURITY", 
        "canal_logs": 1272293056812683345, 
        "canal_punicoes": 1468415943251202252, 
        "categoria_tickets": 1527037033057353728, 
        "cargo_staff": 1274081192450195671
    },
    1169685424738947172: {
        "nome": "BLOX KINGS", 
        "canal_logs": 1526271422253629681, 
        "canal_punicoes": 1526255782222626907, 
        "categoria_tickets": 1170495547426217995, 
        "cargo_staff": 1317249055058825236
    },
    1331323352840933497: {
        "nome": "NIGHTWARE STORE", 
        "canal_logs": 1527037894743687168, 
        "canal_punicoes": 1527038039111635114, 
        "categoria_tickets": 1331327159448375356, 
        "cargo_staff": 1333982207701684294
    }
}

IMAGENS_TICKETS = {
    "GHOUL": "https://cdn.discordapp.com/attachments/1444429504838631586/1454170002746769530/Banner_ticket_20250205_120340_0000.png",
    "COD": "https://cdn.discordapp.com/attachments/1183819407013707947/1469731813709578417/GHOUL_20260207_132912_0000.png",
    "BLOX_KINGS": "https://cdn.discordapp.com/attachments/1183819407013707947/1526281157635870730/file_000000002958720eab459d97fd2c5b8e.png",
    "NIGHTWARE": "https://cdn.discordapp.com/attachments/1440377531848200295/1452759780111155323/standard.gif"
}

TERMOS_BAN = [
    "checkmybio", "checkmyprofile", "lookmybio", "lookatmybio", 
    "checkbio", "olharabiografia", "olheminhabio", "freenitro", 
    "nitrogratis", "onlyfansfree"
]

PALAVROES = [
    "fdp", "filhodaputa", "caralho", "krl", "bosta", "escroto", "merda", 
    "arrombado", "viado", "corno", "desgracado", "vagabundo", "porra", 
    "buceta", "cacete", "puta", "puto", "cuzao", "pica", "rola", 
    "xoxota", "vadia", "foder", "fodase", "tnc", "tomarnocu", "vsf", 
    "vtnc", "pqp"
]

IMAGENS_BLOQUEADAS = [
    '9977339a644d9a62', '936c6c4e946cd966', '9748a8dcbd4a2579', 
    'c48ff019712fe2c6', '91ac6db293ab09a6'
]

# ==================== ESTRUTURA DO BOT ====================
class MeuBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents, help_command=None)
        self.mensagens_ignoradas = set()
        self.ultimos_banimentos = set() 
        self.ultimos_mutes = set()

    async def setup_hook(self):
        self.add_view(ViewGhoul())
        self.add_view(ViewKings())
        self.add_view(ViewNightware())
        self.add_view(ViewFechar())
        await self.tree.sync()

bot = MeuBot()

def obter_config(guild_id): 
    return CONFIG_SERVIDORES.get(guild_id)

def normalizar_texto(texto):
    texto = texto.lower()
    texto = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    substituicoes = {'1': 'i', '3': 'e', '4': 'a', '0': 'o', '5': 's', '7': 't', '$': 's', '@': 'a'}
    for orig, sub in substituicoes.items():
        texto = texto.replace(orig, sub)
    return re.sub(r'[^a-z0-9\s]', '', texto)

# ==================== SISTEMA DE PUNIÇÕES E LOGS (#950606) ====================
async def log_punicao_bonito(guild, user, staff, acao, motivo, prova_url=None):
    config = obter_config(guild.id)
    if not config or not (canal := bot.get_channel(config["canal_punicoes"])): 
        return

    embed = discord.Embed(
        title=f"🔨 {config['nome']} - Punição Aplicada", 
        color=0x950606, 
        timestamp=discord.utils.utcnow()
    )
    if user.display_avatar: 
        embed.set_thumbnail(url=user.display_avatar.url)
    
    description = (
        f"👤 **Usuário:** {user.mention} ({user.id})\n"
        f"🛡️ **Staff:** {staff.mention}\n"
        f"🚨 **Ação:** `{acao}`\n\n"
    )
    
    if "Ban" in acao:
        carta_ghoul = (
            f"**Aviso de Banimento:**\n"
            f"Caro(a) {user.mention},\n\n"
            f"Você foi banido(a) do servidor por violar as nossas regras. Lamentamos profundamente que tenha decidido ignorar as normas que estabelecemos para manter a segurança e o respeito mútuo dentro da nossa comunidade. O seu comportamento não foi tolerado e resultou nesta ação.\n\n"
            f"É imperativo que todos os membros sigam as diretrizes estabelecidas para garantir um ambiente seguro e acolhedor para todos os utilizadores.\n\n"
            f"Se tiver dúvidas sobre o banimento ou quiser discutir o assunto, pode contactar a moderação. No entanto, a decisão de banir permanece final e não será revertida sem uma consideração significativa.\n\n"
            f"Desejamos sinceramente que aprenda com esta experiência e que possa refletir sobre as suas ações futuras.\n\n"
            f"*Atenciosamente,*\n"
            f"**Equipe de Moderação - {config['nome']}**\n\n"
        )
        description += carta_ghoul

    description += f"**Motivo Original:**\n```{motivo}```"
    embed.description = description

    if prova_url:
        embed.set_image(url=prova_url)

    embed.set_footer(text=f"Segurança Ativa {config['nome']}", icon_url=guild.icon.url if guild.icon else None)
    await canal.send(embed=embed)

async def executar_banimento(guild, membro, staff, motivo, acao_log, prova_url=None):
    config = obter_config(guild.id)
    nome_servidor = config["nome"] if config else guild.name
    bot.ultimos_banimentos.add(membro.id)
    
    carta_dm = (
        f"**{nome_servidor} | Aviso de Banimento**\n\n"
        f"Caro(a) {membro.mention},\n\n"
        f"Você foi banido(a) por violar as nossas regras.\n\n"
        f"**Motivo:** {motivo}\n\n"
        f"A decisão de banir permanece final e não será revertida sem uma consideração significativa da nossa equipe.\n\n"
        f"*Atenciosamente,*\n"
        f"**Equipe de Moderação - {nome_servidor}**"
    )
    try:
        await membro.send(carta_dm)
    except: 
        pass 

    try:
        await membro.ban(reason=f"{staff.name} | {motivo}")
        await log_punicao_bonito(guild, membro, staff, acao_log, motivo, prova_url)
        return True
    except:
        return False

async def log_filtro_automod(message, ocorrencia, texto_original):
    config = obter_config(message.guild.id)
    if not config or not (canal := bot.get_channel(config["canal_logs"])): 
        return

    embed = discord.Embed(
        title=f"🛡️ {config['nome']} - Filtro Automático", 
        color=0x950606, 
        timestamp=discord.utils.utcnow()
    )
    if message.author.display_avatar: 
        embed.set_thumbnail(url=message.author.display_avatar.url)
    
    embed.description = (
        f"👤 **Usuário:** {message.author.mention} ({message.author.id})\n"
        f"💬 **Canal:** {message.channel.mention}\n"
        f"🚨 **Ocorrência:** `{ocorrencia}`\n\n"
        f"**Mensagem Deletada:**\n"
        f"```{texto_original}```"
    )
    
    embed.set_footer(text=f"Segurança Ativa {config['nome']}", icon_url=message.guild.icon.url if message.guild.icon else None)
    await canal.send(embed=embed)

# ==================== DETECÇÃO DE AÇÕES DA STAFF (AUDIT LOGS) ====================
@bot.event
async def on_member_ban(guild, user):
    if user.id in bot.ultimos_banimentos:
        bot.ultimos_banimentos.discard(user.id)
        return 

    await asyncio.sleep(2)
    async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.ban):
        if entry.target.id == user.id:
            if entry.user.id == bot.user.id: 
                return 
            await log_punicao_bonito(guild, user, entry.user, "Banimento (Painel/Botão Direito)", entry.reason or "Nenhum motivo inserido.")
            return

@bot.event
async def on_member_unban(guild, user):
    await asyncio.sleep(2)
    async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.unban):
        if entry.target.id == user.id:
            if entry.user.id == bot.user.id: 
                return
            await log_punicao_bonito(guild, user, entry.user, "Desbanimento (Painel/Botão Direito)", entry.reason or "Nenhum motivo inserido.")
            return

@bot.event
async def on_member_update(before, after):
    if before.timed_out_until != after.timed_out_until:
        if after.id in bot.ultimos_mutes:
            bot.ultimos_mutes.discard(after.id)
            return

        await asyncio.sleep(2)
        if after.timed_out_until is not None:
            async for entry in before.guild.audit_logs(limit=5, action=discord.AuditLogAction.member_update):
                if entry.target.id == after.id and hasattr(entry.after, 'timed_out_until'):
                    if entry.user.id == bot.user.id: 
                        return
                    tempo = after.timed_out_until - discord.utils.utcnow()
                    minutos = max(1, int(tempo.total_seconds() / 60))
                    await log_punicao_bonito(before.guild, after, entry.user, f"Mute ({minutos} mins - Discord)", entry.reason or "Aplicado via painel/botão direito.")
                    return
        elif after.timed_out_until is None:
            async for entry in before.guild.audit_logs(limit=5, action=discord.AuditLogAction.member_update):
                if entry.target.id == after.id and hasattr(entry.before, 'timed_out_until') and not hasattr(entry.after, 'timed_out_until'):
                    if entry.user.id == bot.user.id: 
                        return
                    await log_punicao_bonito(before.guild, after, entry.user, "Desmutado (Discord)", entry.reason or "Removido via painel/botão direito.")
                    return

# ==================== SISTEMA DE TICKETS (#950606) ====================
class DropdownGhoul(discord.ui.Select):
    def __init__(self):
        opcoes = [
            discord.SelectOption(label="Denúncias", value="denuncias", emoji="🚨"), 
            discord.SelectOption(label="Suporte", value="suporte", emoji="🛠️"), 
            discord.SelectOption(label="Dúvidas", value="duvidas", emoji="❓")
        ]
        super().__init__(placeholder="Selecione o setor...", min_values=1, max_values=1, options=opcoes, custom_id="sel_ghoul")
    async def callback(self, interaction: discord.Interaction): 
        await criar_canal_ticket(interaction, self.values[0])

class DropdownKings(discord.ui.Select):
    def __init__(self):
        opcoes = [
            discord.SelectOption(label="Comprar Robux", value="robux", emoji="💰"), 
            discord.SelectOption(label="Frutas", value="frutas", emoji="🍎"), 
            discord.SelectOption(label="Suporte Geral", value="suporte", emoji="🛠️")
        ]
        super().__init__(placeholder="Selecione o produto...", min_values=1, max_values=1, options=opcoes, custom_id="sel_kings")
    async def callback(self, interaction: discord.Interaction): 
        await criar_canal_ticket(interaction, self.values[0])

class DropdownNightware(discord.ui.Select):
    def __init__(self):
        opcoes = [
            discord.SelectOption(label="Comprar", value="compras", emoji="🛒"), 
            discord.SelectOption(label="Financeiro", value="financeiro", emoji="💳"), 
            discord.SelectOption(label="Suporte", value="suporte", emoji="🛠️")
        ]
        super().__init__(placeholder="Selecione a categoria...", min_values=1, max_values=1, options=opcoes, custom_id="sel_nightware")
    async def callback(self, interaction: discord.Interaction): 
        await criar_canal_ticket(interaction, self.values[0])

class ViewGhoul(discord.ui.View):
    def __init__(self): 
        super().__init__(timeout=None)
        self.add_item(DropdownGhoul())

class ViewKings(discord.ui.View):
    def __init__(self): 
        super().__init__(timeout=None)
        self.add_item(DropdownKings())

class ViewNightware(discord.ui.View):
    def __init__(self): 
        super().__init__(timeout=None)
        self.add_item(DropdownNightware())

class ViewFechar(discord.ui.View):
    def __init__(self): 
        super().__init__(timeout=None)
    @discord.ui.button(label="Fechar Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="btn_fechar")
    async def fechar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 Fechando canal em 5 segundos...", ephemeral=True)
        await asyncio.sleep(5)
        await interaction.channel.delete()

async def criar_canal_ticket(interaction: discord.Interaction, setor: str):
    config = obter_config(interaction.guild.id)
    if not config or interaction.response.is_done(): 
        return
    categoria = discord.utils.get(interaction.guild.categories, id=config["categoria_tickets"])
    cargo_staff = interaction.guild.get_role(config["cargo_staff"])
    
    overwrites = {
        interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
        interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True),
        interaction.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
    }
    if cargo_staff: 
        overwrites[cargo_staff] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

    canal = await interaction.guild.create_text_channel(name=f"ticket-{interaction.user.name}-{setor}", category=categoria, overwrites=overwrites)
    
    embed = discord.Embed(
        title=f"🚨 {config['nome']} - Atendimento", 
        description=(
            f"Olá {interaction.user.mention},\n\n"
            f"Seu ticket para o setor **{setor.upper()}** foi aberto com sucesso!\n"
            f"Descreva detalhadamente o que precisa abaixo para que a equipe possa te responder."
        ), 
        color=0x950606
    )
    await canal.send(content=f"{interaction.user.mention} {cargo_staff.mention if cargo_staff else ''}", embed=embed, view=ViewFechar())
    await interaction.response.send_message(f"✅ Ticket criado em {canal.mention}!", ephemeral=True)

# ==================== AUTOMODERAÇÃO ATIVA ====================
@bot.event
async def on_message(message):
    if message.author.bot or not message.guild: 
        return
    config = obter_config(message.guild.id)
    if not config: 
        return

    is_staff = message.author.guild_permissions.manage_messages
    is_admin = message.author.guild_permissions.administrator

    texto_norm = normalizar_texto(message.content)
    
    # 1. Filtro de Termos Proibidos (Ban Automático)
    for termo in TERMOS_BAN:
        if termo in texto_norm:
            bot.mensagens_ignoradas.add(message.id)
            try:
                await message.delete()
            except: 
                pass
            
            if not is_admin: 
                await executar_banimento(message.guild, message.author, bot.user, f"Tentativa de golpe: `{termo}`", "Ban (Automático)")
            return

    # 2. Filtro de Palavrões
    for palavrao in PALAVROES:
        if palavrao in texto_norm:
            bot.mensagens_ignoradas.add(message.id)
            try:
                await message.delete()
            except: 
                pass
            
            await log_filtro_automod(message, "Palavrão/Xingamento Detectado", message.content)
            return 

    # 3. Filtro de Imagens Proibidas
    if message.attachments:
        for anexo in message.attachments:
            if any(anexo.filename.lower().endswith(ext) for ext in ["png", "jpg", "jpeg", "webp"]):
                try:
                    response = requests.get(anexo.url)
                    img = Image.open(BytesIO(response.content))
                    if str(imagehash.average_hash(img)) in IMAGENS_BLOQUEADAS:
                        bot.mensagens_ignoradas.add(message.id)
                        try:
                            await message.delete()
                        except: 
                            pass
                        
                        if not is_admin:
                            await executar_banimento(message.guild, message.author, bot.user, "Envio de imagem proibida.", "Ban (Automático)", anexo.url)
                        return
                except: 
                    pass

    # 4. Filtro de Convites/Links
    if re.search(r'(discord\.gg/|discord\.com/invite/)', message.content.lower()):
        bot.mensagens_ignoradas.add(message.id)
        try:
            await message.delete()
        except: 
            pass
        
        if not is_staff: 
            try:
                bot.ultimos_mutes.add(message.author.id)
                await message.author.timeout(datetime.timedelta(hours=1), reason="Divulgação Automática.")
                await log_punicao_bonito(message.guild, message.author, bot.user, "Mute 1 Hora (Automático)", "Divulgação de link de convite.")
            except: 
                pass
        return

@bot.event
async def on_message_delete(message):
    if message.author.bot or not message.guild: 
        return
    if message.id in bot.mensagens_ignoradas:
        bot.mensagens_ignoradas.discard(message.id)
        return

    config = obter_config(message.guild.id)
    if config and (canal_logs := bot.get_channel(config["canal_logs"])):
        embed = discord.Embed(
            title=f"🗑️ {config['nome']} - Mensagem Apagada", 
            color=0x950606, 
            timestamp=discord.utils.utcnow()
        )
        if message.author.display_avatar:
            embed.set_thumbnail(url=message.author.display_avatar.url)
            
        conteudo = message.content[:1000] if message.content else "Mensagem vazia ou apenas mídia"
        embed.description = (
            f"👤 **Usuário:** {message.author.mention} ({message.author.id})\n"
            f"💬 **Canal:** {message.channel.mention}\n\n"
            f"**Conteúdo Original:**\n"
            f"```{conteudo}```"
        )
        embed.set_footer(text=f"Segurança Ativa {config['nome']}", icon_url=message.guild.icon.url if message.guild.icon else None)
        await canal_logs.send(embed=embed)

# ==================== COMANDOS DE BARRA (#950606) ====================
@bot.tree.command(name="mute", description="Silencia um membro no servidor temporariamente.")
@app_commands.default_permissions(moderate_members=True)
async def mute_slash(interaction: discord.Interaction, membro: discord.Member, tempo_minutos: int, motivo: str = "Sem motivo especificado"):
    await interaction.response.defer(ephemeral=True)
    try:
        bot.ultimos_mutes.add(membro.id)
        await membro.timeout(datetime.timedelta(minutes=tempo_minutos), reason=f"{interaction.user.name} | {motivo}")
        await interaction.followup.send(f"✅ O usuário {membro.mention} foi silenciado por {tempo_minutos} minuto(s) com sucesso.")
        await log_punicao_bonito(interaction.guild, membro, interaction.user, f"Mute Comando ({tempo_minutos} mins)", motivo)
    except Exception:
        await interaction.followup.send("❌ Não foi possível mutar. Verifique se o meu cargo está acima do cargo desse usuário.")

@bot.tree.command(name="ban", description="Bane um membro do servidor permanentemente.")
@app_commands.default_permissions(ban_members=True)
async def ban_slash(interaction: discord.Interaction, membro: discord.Member, motivo: str = "Sem motivo especificado"):
    await interaction.response.defer(ephemeral=True)
    sucesso = await executar_banimento(interaction.guild, membro, interaction.user, motivo, "Banimento Comando")
    if sucesso:
        await interaction.followup.send(f"🔨 O usuário {membro.mention} foi banido com sucesso.")
    else:
        await interaction.followup.send("❌ Erro ao banir. Verifique se o meu cargo é superior ao da pessoa que você está tentando banir.")

@bot.tree.command(name="painel_tickets", description="Envia o painel de atendimento de tickets no canal.")
@app_commands.choices(painel=[
    app_commands.Choice(name="GHOUL", value="ghoul"),
    app_commands.Choice(name="BLOX KINGS", value="kings"),
    app_commands.Choice(name="NIGHTWARE", value="nightware"),
    app_commands.Choice(name="COD", value="cod")
])
@app_commands.default_permissions(administrator=True)
async def painel_slash(interaction: discord.Interaction, painel: app_commands.Choice[str]):
    if painel.value == "ghoul":
        embed = discord.Embed(title="🛡️ CENTRAL DE ATENDIMENTO - GHOUL", description="Selecione uma opção no menu abaixo para abrir seu ticket.", color=0x950606)
        embed.set_image(url=IMAGENS_TICKETS["GHOUL"])
        view = ViewGhoul()
    elif painel.value == "kings":
        embed = discord.Embed(title="👑 CENTRAL DE ATENDIMENTO - BLOX KINGS", description="Selecione uma opção no menu abaixo para abrir seu ticket.", color=0x950606)
        embed.set_image(url=IMAGENS_TICKETS["BLOX_KINGS"])
        view = ViewKings()
    elif painel.value == "nightware":
        embed = discord.Embed(title="🛍️ CENTRAL DE ATENDIMENTO - NIGHTWARE", description="Selecione uma opção no menu abaixo para abrir seu ticket.", color=0x950606)
        embed.set_image(url=IMAGENS_TICKETS["NIGHTWARE"])
        view = ViewNightware()
    elif painel.value == "cod":
        embed = discord.Embed(title="🎯 CENTRAL DE ATENDIMENTO - COD", description="Selecione uma opção no menu abaixo para abrir seu ticket.", color=0x950606)
        embed.set_image(url=IMAGENS_TICKETS["COD"])
        view = ViewGhoul()

    await interaction.channel.send(embed=embed, view=view)
    await interaction.response.send_message(f"✅ Painel **{painel.name}** enviado com sucesso!", ephemeral=True)

@bot.event
async def on_ready():
    print(f"✅ Sistema perfeito! {bot.user.name} está online, comandos sincronizados e operando com cor #950606.")

TOKEN = os.getenv('TOKEN')
bot.run(TOKEN)
