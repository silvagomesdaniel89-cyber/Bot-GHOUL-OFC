import asyncio
import datetime
import os
import re
import random
import unicodedata
from io import BytesIO
from discord import app_commands
from discord.ext import commands
import discord
from flask import Flask
import imagehash
from PIL import Image
import requests
from threading import Thread

# ==================== SERVIDOR WEB PARA MANTER ONLINE ====================
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot online e operando com perfeição!"

def run_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

Thread(target=run_server, daemon=True).start()

# ==================== CONFIGURAÇÕES DOS SERVIDORES ====================
CONFIG_SERVIDORES = {
    1143627184842493992: {
        "nome": "GHOUL SECURITY",
        "canal_logs": 1272293056812683345,
        "canal_punicoes": 1468415943251202252,
        "categoria_tickets": 1527037033057353728,
        "cargo_staff": 1274081192450195671,
    },
    1169685424738947172: {
        "nome": "BLOX KINGS",
        "canal_logs": 1526271422253629681,
        "canal_punicoes": 1526255782222626907,
        "categoria_tickets": 1170495547426217995,
        "cargo_staff": 1317249055058825236,
    },
    1331323352840933497: {
        "nome": "NIGHTWARE STORE",
        "canal_logs": 1527037894743687168,
        "canal_punicoes": 1527038039111635114,
        "categoria_tickets": 1331327159448375356,
        "cargo_staff": 1333982207701684294,
    },
    1489007277267620013: {
        "nome": "POLIAS",
        "canal_logs": 1489007278693814453,
        "canal_punicoes": 1533828688213311608,
        "categoria_tickets": 1533834644569456681,
        "cargo_staff": 1489007277267620020,
    },
}

IMAGENS_TICKETS = {
    "GHOUL": "https://cdn.discordapp.com/attachments/1444429504838631586/1454170002746769530/Banner_ticket_20250205_120340_0000.png",
    "COD": "https://cdn.discordapp.com/attachments/1183819407013707947/1469731813709578417/GHOUL_20260207_132912_0000.png",
    "BLOX_KINGS": "https://cdn.discordapp.com/attachments/1183819407013707947/1526281157635870730/file_000000002958720eab459d97fd2c5b8e.png",
    "NIGHTWARE": "https://cdn.discordapp.com/attachments/1440377531848200295/1452759780111155323/standard.gif",
    "POLIAS": "https://cdn.discordapp.com/attachments/1431364353482948608/1533832231108214864/file_000000004fd4820eb39bb046269d5d96.png",
}

TERMOS_BAN = ["checkmybio", "checkmyprofile", "lookmybio", "lookatmybio", "checkbio", "olharabiografia", "olheminhabio", "freenitro", "nitrogratis", "onlyfansfree"]
PALAVROES = ["fdp", "filhodaputa", "caralho", "krl", "bosta", "escroto", "merda", "arrombado", "viado", "corno", "desgracado", "vagabundo", "porra", "buceta", "cacete", "puta", "puto", "cuzao", "pica", "rola", "xoxota", "vadia", "foder", "fodase", "tnc", "tomarnocu", "vsf", "vtnc", "pqp"]
IMAGENS_BLOQUEADAS = ["9977339a644d9a62", "936c6c4e946cd966", "9748a8dcbd4a2579", "c48ff019712fe2c6", "91ac6db293ab09a6", "c1e1eb965c5e5cd0", "f5de4a08bdbd5aa5", "956a6e944ac9a6c9", "931e6ae394d3486f"]

# ==================== ESTRUTURA DO BOT ====================
class MeuBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents, help_command=None)
        self.mensagens_ignoradas = set()
        self.ultimos_banimentos = set()
        self.ultimos_mutes = set()
        self.midia_cache = {}
        self.sorteios_ativos = {}

    async def setup_hook(self):
        self.add_view(ViewGhoul())
        self.add_view(ViewKings())
        self.add_view(ViewNightware())
        self.add_view(ViewPolias())
        self.add_view(ViewValidar())
        self.add_view(ViewTicketCustomizado())
        self.add_view(ViewControlesTicket())
        self.add_view(SorteioView(""))
        await self.tree.sync()

bot = MeuBot()

def obter_config(guild_id):
    return CONFIG_SERVIDORES.get(guild_id)

def normalizar_texto(texto):
    texto = texto.lower()
    texto = "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")
    substituicoes = {"1": "i", "3": "e", "4": "a", "0": "o", "5": "s", "7": "t", "$": "s", "@": "a"}
    for orig, sub in substituicoes.items():
        texto = texto.replace(orig, sub)
    return re.sub(r"[^a-z0-9\s]", "", texto)

async def enviar_log(guild_id, embed, files=None):
    config = obter_config(guild_id)
    if not config: return
    guild = bot.get_guild(guild_id)
    if not guild: return
    canal = guild.get_channel(config["canal_logs"])
    if not canal: return
    if files:
        await canal.send(embed=embed, files=files)
    else:
        await canal.send(embed=embed)

# ==================== PUNIÇÕES E AUTOMODERAÇÃO ====================
async def log_punicao_bonito(guild, user, staff, acao, motivo, prova_url=None):
    config = obter_config(guild.id)
    if not config: return
    canal = guild.get_channel(config["canal_punicoes"])
    if not canal: return

    embed = discord.Embed(title=f"🔨 {config['nome']} - Punição Aplicada", color=0x950606, timestamp=discord.utils.utcnow())
    if user.display_avatar: embed.set_thumbnail(url=user.display_avatar.url)
    embed.description = f"👤 **Usuário:** {user.mention}\n📛 **Nick:** `{user.name}`\n🆔 **ID:** `{user.id}`\n🛡️ **Staff:** {staff.mention if hasattr(staff, 'mention') else staff}\n🚨 **Ação:** `{acao}`\n📄 **Motivo:** {motivo}"
    if prova_url: embed.set_image(url=prova_url)
    embed.set_footer(text=f"Segurança Ativa {config['nome']}", icon_url=guild.icon.url if guild.icon else None)
    await canal.send(embed=embed)

async def executar_banimento(guild, membro, staff, motivo, acao_log, prova_url=None):
    bot.ultimos_banimentos.add(membro.id)
    config = obter_config(guild.id)
    nome_servidor = config["nome"] if config else guild.name
    try:
        await membro.send(f"**{nome_servidor} | Aviso de Banimento**\n\nCaro(a) {membro.mention},\nVocê foi banido(a).\n**Motivo:** {motivo}\n\n*Atenciosamente, Equipe {nome_servidor}*")
    except: pass
    try:
        staff_name = staff.name if hasattr(staff, "name") else str(staff)
        await membro.ban(reason=f"{staff_name} | {motivo}")
        await log_punicao_bonito(guild, membro, staff, acao_log, motivo, prova_url)
        return True
    except:
        return False

# ==================== COMANDO DE MUTE E LOGS DE PUNIÇÃO ====================
@bot.tree.command(name="mute", description="Silencia temporariamente um membro no servidor.")
@app_commands.default_permissions(moderate_members=True)
async def mute_slash(interaction: discord.Interaction, membro: discord.Member, minutos: int, *, motivo: str):
    await interaction.response.defer(ephemeral=True)
    tempo = datetime.timedelta(minutes=minutos)
    try:
        await membro.timeout(tempo, reason=f"{interaction.user} | {motivo}")
        await log_punicao_bonito(interaction.guild, membro, interaction.user, "Mute / Silenciamento", f"{motivo} (Duração: {minutos} minutos)")
        await interaction.followup.send(f"✅ O membro {membro.mention} foi silenciado por **{minutos} minutos**.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Não foi possível silenciar o membro: {e}", ephemeral=True)

# ==================== LOGS ESTILO GAMERSAFER ====================
@bot.event
async def on_voice_state_update(member, before, after):
    config = obter_config(member.guild.id)
    if not config: return

    embed = discord.Embed(color=0x950606, timestamp=discord.utils.utcnow())
    if member.display_avatar: embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=f"Logs de Voz | {config['nome']}")

    if before.channel is None and after.channel is not None:
        embed.title = "🎙️ Usuário entrou no Canal de Voz"
        embed.description = f"👤 **Usuário:** {member.mention} ({member.id})\n🔊 **Canal:** {after.channel.mention}"
        await enviar_log(member.guild.id, embed)
    elif before.channel is not None and after.channel is None:
        desconectado_por = None
        await asyncio.sleep(1)
        try:
            async for entry in member.guild.audit_logs(limit=3, action=discord.AuditLogAction.member_disconnect):
                if entry.target.id == member.id and (discord.utils.utcnow() - entry.created_at).total_seconds() < 5:
                    desconectado_por = entry.user
                    break
        except: pass

        if desconectado_por:
            embed.title = "⚠️ Usuário desconectado pela Staff"
            embed.description = f"👤 **Usuário:** {member.mention} ({member.id})\n🛡️ **Staff:** {desconectado_por.mention}\n🔇 **Canal Anterior:** {before.channel.mention}"
        else:
            embed.title = "🚪 Usuário saiu do Canal de Voz"
            embed.description = f"👤 **Usuário:** {member.mention} ({member.id})\n🔇 **Canal Anterior:** {before.channel.mention}"
        await enviar_log(member.guild.id, embed)
    elif before.channel and after.channel and before.channel.id != after.channel.id:
        movido_por = None
        await asyncio.sleep(1)
        try:
            async for entry in member.guild.audit_logs(limit=3, action=discord.AuditLogAction.member_move):
                if entry.target.id == member.id and (discord.utils.utcnow() - entry.created_at).total_seconds() < 5:
                    movido_por = entry.user
                    break
        except: pass

        embed.title = "🔀 Usuário movido de Canal"
        embed.description = f"👤 **Usuário:** {member.mention} ({member.id})\n⬅️ **Antigo:** {before.channel.mention}\n➡️ **Novo:** {after.channel.mention}"
        if movido_por:
            embed.description += f"\n🛡️ **Movido por:** {movido_por.mention}"
        await enviar_log(member.guild.id, embed)

@bot.event
async def on_member_update(before, after):
    config = obter_config(before.guild.id)
    if not config: return

    if before.roles != after.roles:
        added = [r.mention for r in after.roles if r not in before.roles]
        removed = [r.mention for r in before.roles if r not in after.roles]
        
        responsavel = "Usuário/Desconhecido"
        await asyncio.sleep(1)
        try:
            async for entry in before.guild.audit_logs(limit=3, action=discord.AuditLogAction.member_role_update):
                if entry.target.id == after.id and (discord.utils.utcnow() - entry.created_at).total_seconds() < 5:
                    responsavel = entry.user.mention
                    break
        except: pass

        embed = discord.Embed(title="🛡️ Atualização de Cargos", color=0x950606, timestamp=discord.utils.utcnow())
        embed.set_thumbnail(url=after.display_avatar.url if after.display_avatar else None)
        desc = f"👤 **Membro:** {after.mention} ({after.id})\n🛡️ **Autor da Ação:** {responsavel}\n"
        if added: desc += f"\n✅ **Cargos Adicionados:** {', '.join(added)}"
        if removed: desc += f"\n❌ **Cargos Removidos:** {', '.join(removed)}"
        embed.description = desc
        embed.set_footer(text=f"Logs de Cargos | {config['nome']}")
        await enviar_log(before.guild.id, embed)

    if before.guild_avatar != after.guild_avatar:
        embed = discord.Embed(title="🖼️ Avatar do Servidor Alterado", description=f"👤 **Membro:** {after.mention}", color=0x950606)
        if before.guild_avatar: embed.set_thumbnail(url=before.guild_avatar.url)
        if after.guild_avatar: embed.set_image(url=after.guild_avatar.url)
        await enviar_log(before.guild.id, embed)

@bot.event
async def on_user_update(before, after):
    if before.avatar != after.avatar:
        for guild in bot.guilds:
            config = obter_config(guild.id)
            if config and guild.get_member(after.id):
                embed = discord.Embed(title="🖼️ Avatar Global Alterado", description=f"👤 **Usuário:** {after.mention} ({after.id})", color=0x950606)
                if before.avatar: embed.set_thumbnail(url=before.avatar.url)
                if after.avatar: embed.set_image(url=after.avatar.url)
                await enviar_log(guild.id, embed)

@bot.event
async def on_raw_bulk_message_delete(payload):
    config = obter_config(payload.guild_id)
    if not config: return
    embed = discord.Embed(title="🗑️ Mensagens Apagadas em Massa", color=0x950606, timestamp=discord.utils.utcnow())
    embed.description = f"🧹 **Quantidade:** `{len(payload.message_ids)}` mensagens\n💬 **Canal:** <#{payload.channel_id}>"
    await enviar_log(payload.guild_id, embed)

# ==================== COMANDO DE LIMPAR / PURGE ====================
@bot.tree.command(name="limpar", description="Apaga mensagens em massa no canal atual (Estilo Loritta).")
@app_commands.default_permissions(manage_messages=True)
async def limpar_slash(interaction: discord.Interaction, quantidade: int):
    await interaction.response.defer(ephemeral=True)
    try:
        deleted = await interaction.channel.purge(limit=quantidade)
        await interaction.followup.send(f"✅ Sucesso! **{len(deleted)}** mensagens foram varridas do mapa.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Não foi possível apagar as mensagens: {e}", ephemeral=True)

# ==================== SISTEMA DE TICKETS ====================
class ViewControlesTicket(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Reivindicar Ticket", style=discord.ButtonStyle.success, emoji="✋", custom_id="btn_reivindicar")
    async def reivindicar(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = obter_config(interaction.guild.id)
        if not config: return
        cargo_staff = interaction.guild.get_role(config["cargo_staff"])
        
        if cargo_staff not in interaction.user.roles and not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Apenas staffs podem reivindicar tickets!", ephemeral=True)
            
        embed = discord.Embed(title="✋ Ticket Reivindicado", description=f"O staff {interaction.user.mention} assumiu este ticket e irá te ajudar em breve!", color=0x2ecc71)
        button.disabled = True
        button.label = f"Assumido por {interaction.user.name}"
        await interaction.response.edit_message(view=self)
        await interaction.channel.send(embed=embed)

    @discord.ui.button(label="Fechar Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="btn_fechar_ticket")
    async def fechar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 Fechando canal em 5 segundos...", ephemeral=True)
        await asyncio.sleep(5)
        await interaction.channel.delete()

async def criar_canal_ticket(interaction: discord.Interaction, setor: str):
    config = obter_config(interaction.guild.id)
    if not config or interaction.response.is_done(): return
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
        description=f"Olá {interaction.user.mention},\n\nSeu ticket para **{setor.upper()}** foi aberto com sucesso!\nDescreva detalhadamente o que precisa abaixo. Nossa equipe vai te atender logo.",
        color=0x950606,
    )
    await canal.send(content=f"{interaction.user.mention} {cargo_staff.mention if cargo_staff else ''}", embed=embed, view=ViewControlesTicket())
    await interaction.response.send_message(f"✅ Ticket criado em {canal.mention}!", ephemeral=True)

class ViewTicketCustomizado(discord.ui.View):
    def __init__(self, setor_nome="Geral"):
        super().__init__(timeout=None)
        self.setor_nome = setor_nome

    @discord.ui.button(label="Abrir Ticket", style=discord.ButtonStyle.primary, emoji="🎫", custom_id="btn_ticket_custom")
    async def abrir(self, interaction: discord.Interaction, button: discord.ui.Button):
        await criar_canal_ticket(interaction, self.setor_nome)

class ModalTicketCustomizado(discord.ui.Modal, title="Criar Painel de Ticket"):
    titulo = discord.ui.TextInput(label="Título do Embed", placeholder="Ex: Central de Segurança", required=True)
    descricao = discord.ui.TextInput(label="Descrição do Painel", style=discord.TextStyle.paragraph, placeholder="Insira o texto que aparecerá no embed.", required=True)
    setor = discord.ui.TextInput(label="Nome do Setor", placeholder="Ex: seguranca (sem espaços)", required=True)
    imagem_url = discord.ui.TextInput(label="URL da Imagem (Opcional)", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(title=self.titulo.value, description=self.descricao.value, color=0x950606)
        if self.imagem_url.value:
            embed.set_image(url=self.imagem_url.value)
        
        view = ViewTicketCustomizado(self.setor.value)
        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message("✅ Painel criado com sucesso!", ephemeral=True)

@bot.tree.command(name="painel_customizado", description="Cria um painel de ticket personalizado (ideal para Segurança).")
@app_commands.default_permissions(administrator=True)
async def painel_custom(interaction: discord.Interaction):
    await interaction.response.send_modal(ModalTicketCustomizado())

class DropdownGhoul(discord.ui.Select):
    def __init__(self):
        opcoes = [
            discord.SelectOption(label="Denúncias", value="denuncias", emoji="🚨"),
            discord.SelectOption(label="Suporte", value="suporte", emoji="🛠️"),
            discord.SelectOption(label="Dúvidas", value="duvidas", emoji="❓"),
            discord.SelectOption(label="Exposed", value="exposed", emoji="⚠️"),
        ]
        super().__init__(placeholder="Selecione o setor do suporte...", options=opcoes, custom_id="sel_ghoul")
    async def callback(self, interaction: discord.Interaction):
        await criar_canal_ticket(interaction, self.values[0])

class ViewGhoul(discord.ui.View):
    def __init__(self): super().__init__(timeout=None); self.add_item(DropdownGhoul())

class DropdownKings(discord.ui.Select):
    def __init__(self):
        opcoes = [discord.SelectOption(label="Robux", value="robux", emoji="💰"), discord.SelectOption(label="Gamepass", value="gamepass", emoji="📦")]
        super().__init__(placeholder="Selecione...", options=opcoes, custom_id="sel_kings")
    async def callback(self, interaction: discord.Interaction):
        await criar_canal_ticket(interaction, self.values[0])

class ViewKings(discord.ui.View):
    def __init__(self): super().__init__(timeout=None); self.add_item(DropdownKings())

class DropdownNightware(discord.ui.Select):
    def __init__(self):
        opcoes = [discord.SelectOption(label="Comprar", value="compras", emoji="🛒"), discord.SelectOption(label="Suporte", value="suporte", emoji="🛠️")]
        super().__init__(placeholder="Selecione...", options=opcoes, custom_id="sel_nightware")
    async def callback(self, interaction: discord.Interaction):
        await criar_canal_ticket(interaction, self.values[0])

class ViewNightware(discord.ui.View):
    def __init__(self): super().__init__(timeout=None); self.add_item(DropdownNightware())

class DropdownPolias(discord.ui.Select):
    def __init__(self):
        opcoes = [discord.SelectOption(label="Suporte", value="suporte", emoji="🛠️"), discord.SelectOption(label="Parcerias", value="parcerias", emoji="🤝")]
        super().__init__(placeholder="Selecione...", options=opcoes, custom_id="sel_polias")
    async def callback(self, interaction: discord.Interaction):
        await criar_canal_ticket(interaction, self.values[0])

class ViewPolias(discord.ui.View):
    def __init__(self): super().__init__(timeout=None); self.add_item(DropdownPolias())

class ViewValidar(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Validar", style=discord.ButtonStyle.danger, emoji="🎫", custom_id="btn_validar_cod")
    async def validar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await criar_canal_ticket(interaction, "coldawn")

# ==================== AUTOMODERAÇÃO (TEXTO E IMAGENS PROIBIDAS) ====================
@bot.event
async def on_message(message):
    if message.author.bot or not message.guild: return
    config = obter_config(message.guild.id)
    if not config: return

    # Verificação de Imagens Proibidas (Hash Matcher)
    if message.attachments:
        for attachment in message.attachments:
            if any(attachment.filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.webp', '.gif']):
                try:
                    response = requests.get(attachment.url, timeout=5)
                    img = Image.open(BytesIO(response.content))
                    h = str(imagehash.average_hash(img))
                    
                    for img_bloq in IMAGENS_BLOQUEADAS:
                        if img_bloq in h or h in img_bloq:
                            bot.mensagens_ignoradas.add(message.id)
                            try: await message.delete()
                            except: pass
                            await executar_banimento(message.guild, message.author, bot.user, "Envio de Imagem Proibida / Automod", "Ban Automático (Imagem Proibida)", attachment.url)
                            return
                except Exception:
                    pass

    texto_norm = normalizar_texto(message.content)
    texto_junto = re.sub(r"\s+", "", texto_norm)

    # Filtro de Palavrões com Resposta
    for palavrao in PALAVROES:
        if palavrao in texto_junto:
            bot.mensagens_ignoradas.add(message.id)
            try: await message.delete()
            except: pass
            
            aviso = await message.channel.send(f"{message.author.mention}, cuidado com o linguajar seu boboca!")
            await asyncio.sleep(4)
            try: await aviso.delete()
            except: pass
            
            canal = message.guild.get_channel(config["canal_logs"])
            if canal:
                embed = discord.Embed(title=f"🛡️ {config['nome']} - Filtro Automático", color=0x950606, timestamp=discord.utils.utcnow())
                if message.author.display_avatar: embed.set_thumbnail(url=message.author.display_avatar.url)
                embed.description = f"👤 **Usuário:** {message.author.mention}\n🚨 **Ocorrência:** `Palavrão Detectado`\n\n**Mensagem Deletada:**\n```{message.content}```"
                await canal.send(embed=embed)
            return

    # Filtro de Links/Golpes (Termos Ban)
    for termo in TERMOS_BAN:
        if termo in texto_junto:
            bot.mensagens_ignoradas.add(message.id)
            try: await message.delete()
            except: pass
            await executar_banimento(message.guild, message.author, bot.user, f"Tentativa de golpe: `{termo}`", "Ban Automático")
            return

# ==================== SORTEIOS (GIVEAWAYS) ====================
class SorteioView(discord.ui.View):
    def __init__(self, sorteio_id: str):
        super().__init__(timeout=None)
        self.sorteio_id = sorteio_id

    @discord.ui.button(label="Participar 🎉", style=discord.ButtonStyle.success, custom_id="btn_participar_sorteio")
    async def participar(self, interaction: discord.Interaction, button: discord.ui.Button):
        s_id = str(interaction.message.id)
        if s_id not in bot.sorteios_ativos:
            return await interaction.response.send_message("❌ Este sorteio já acabou ou é inválido!", ephemeral=True)
            
        participantes = bot.sorteios_ativos[s_id]["participantes"]
        if interaction.user.id in participantes:
            participantes.remove(interaction.user.id)
            await interaction.response.send_message("🚪 Você saiu do sorteio.", ephemeral=True)
        else:
            participantes.append(interaction.user.id)
            await interaction.response.send_message("🎉 Você entrou no sorteio! Boa sorte!", ephemeral=True)
            
        button.label = f"Participar 🎉 ({len(participantes)})"
        await interaction.message.edit(view=self)

@bot.tree.command(name="sorteio_iniciar", description="Inicia um sorteio no canal atual.")
@app_commands.default_permissions(manage_events=True)
async def sorteio_slash(interaction: discord.Interaction, premio: str, vencedores: int, duracao_minutos: int):
    tempo_final = discord.utils.utcnow() + datetime.timedelta(minutes=duracao_minutos)
    timestamp_formatado = f"<t:{int(tempo_final.timestamp())}:R>"
    
    embed = discord.Embed(title="🎉 NOVO SORTEIO 🎉", description=f"**Prêmio:** {premio}\n**Ganhador(es):** {vencedores}\n**Termina:** {timestamp_formatado}", color=0x950606)
    embed.set_footer(text="Clique no botão abaixo para participar!")
    
    await interaction.response.send_message("✅ Sorteio criado!", ephemeral=True)
    msg = await interaction.channel.send(embed=embed, view=SorteioView(""))
    
    bot.sorteios_ativos[str(msg.id)] = {
        "premio": premio,
        "vencedores": vencedores,
        "participantes": []
    }

    await asyncio.sleep(duracao_minutos * 60)
    
    if str(msg.id) not in bot.sorteios_ativos: return
    dados = bot.sorteios_ativos[str(msg.id)]
    participantes = dados["participantes"]
    
    try:
        msg = await interaction.channel.fetch_message(msg.id)
        if not participantes:
            embed.description = f"**Prêmio:** {premio}\n**Sorteio Encerrado!** Ninguém participou."
            await msg.edit(embed=embed, view=None)
            await interaction.channel.send(f"❌ O sorteio de **{premio}** foi cancelado pois não houve participantes.")
            return

        ganhadores = random.sample(participantes, min(vencedores, len(participantes)))
        bot.sorteios_ativos[str(msg.id)]["ganhadores_recentes"] = ganhadores
        
        texto_ganhadores = ", ".join([f"<@{uid}>" for uid in ganhadores])
        embed.description = f"**Prêmio:** {premio}\n**Sorteio Encerrado!**\n🏆 **Ganhador(es):** {texto_ganhadores}"
        await msg.edit(embed=embed, view=None)
        await interaction.channel.send(f"🎉 Parabéns {texto_ganhadores}! Vocês ganharam o sorteio de **{premio}**!")
    except:
        pass

@bot.tree.command(name="sorteio_roletar", description="Sorteia novamente o vencedor de um sorteio recente.")
@app_commands.default_permissions(manage_events=True)
async def roletar_slash(interaction: discord.Interaction, id_mensagem: str):
    if id_mensagem not in bot.sorteios_ativos or not bot.sorteios_ativos[id_mensagem].get("ganhadores_recentes"):
        return await interaction.response.send_message("❌ Sorteio não encontrado ou sem participantes suficientes para roletar.", ephemeral=True)
        
    dados = bot.sorteios_ativos[id_mensagem]
    participantes = dados["participantes"]
    
    if len(participantes) == 0:
        return await interaction.response.send_message("❌ Não há participantes para escolher.", ephemeral=True)
        
    novo_ganhador = random.choice(participantes)
    await interaction.response.send_message(f"🎲 **ROLETADO!** O novo ganhador do prêmio **{dados['premio']}** é <@{novo_ganhador}>! Parabéns!")

@bot.event
async def on_ready():
    print(f"✅ Sistema completo e blindado! {bot.user.name} está online, comandos sincronizados e operando com cor #950606.")

TOKEN = os.getenv("TOKEN")
if TOKEN:
    bot.run(TOKEN)
else:
    print("❌ ERRO: Token não encontrado no ambiente.")
