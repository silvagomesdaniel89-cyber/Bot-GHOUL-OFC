import os
import discord
import requests
import imagehash
import asyncio
import re
import unicodedata
import datetime
import random
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
    return "GHOUL SECURITY operando com perfeição!"

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
    },
    1489007277267620013: {
        "nome": "POLIAS", 
        "canal_logs": 1489007278693814453, 
        "canal_punicoes": 1533828688213311608, 
        "categoria_tickets": 1533834644569456681, 
        "cargo_staff": 1489007277267620020
    }
}

TERMOS_BAN = ["checkmybio", "checkmyprofile", "lookmybio", "freenitro", "nitrogratis"]
PALAVROES = ["fdp", "filhodaputa", "caralho", "bosta", "merda", "arrombado", "viado", "corno", "porra", "buceta", "cacete", "puta", "cuzao", "pica", "rola", "xoxota", "vadia", "foder", "tnc", "tomarnocu", "vsf", "vtnc", "pqp"]
IMAGENS_BLOQUEADAS = ['9977339a644d9a62', '936c6c4e946cd966', '9748a8dcbd4a2579', 'c48ff019712fe2c6', '91ac6db293ab09a6', 'c1e1eb965c5e5cd0', 'f5de4a08bdbd5aa5', '956a6e944ac9a6c9', '931e6ae394d3486f']

# ==================== ESTRUTURA DO BOT ====================
class MeuBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents, help_command=None)
        self.ultimos_banimentos = set() 
        self.ultimos_mutes = set()

    async def setup_hook(self):
        self.add_view(ViewGhoul())
        self.add_view(ViewKings())
        self.add_view(ViewNightware())
        self.add_view(ViewFechar())
        self.add_view(ViewCustomTicket()) 
        await self.tree.sync()

bot = MeuBot()

def obter_config(guild_id): return CONFIG_SERVIDORES.get(guild_id)

def normalizar_texto(texto):
    texto = texto.lower()
    texto = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    substituicoes = {'1': 'i', '3': 'e', '4': 'a', '0': 'o', '5': 's', '7': 't', '$': 's', '@': 'a'}
    for orig, sub in substituicoes.items(): texto = texto.replace(orig, sub)
    return re.sub(r'[^a-z0-9\s]', '', texto)

def converter_tempo(tempo_str):
    match = re.match(r"^(\d+)([mhd])$", tempo_str.lower().strip())
    if not match: return None
    valor, unidade = int(match.group(1)), match.group(2)
    if unidade == 'm': return valor * 60
    if unidade == 'h': return valor * 3600
    if unidade == 'd': return valor * 86400
    return None

# ==================== SISTEMA DE PUNIÇÕES ====================
async def log_punicao_bonito(guild, user, staff, acao, motivo, prova_url=None):
    config = obter_config(guild.id)
    if not config or not (canal := bot.get_channel(config["canal_punicoes"])): return

    embed = discord.Embed(title=f"🔨 {config['nome']} - Punição Aplicada", color=0x950606, timestamp=discord.utils.utcnow())
    if hasattr(user, 'display_avatar') and user.display_avatar: embed.set_thumbnail(url=user.display_avatar.url)
    
    embed.description = (
        f"👤 **Usuário:** {user.mention} (`{user.name}`)\n"
        f"🆔 **ID:** `{user.id}`\n"
        f"🛡️ **Staff:** {staff.mention}\n"
        f"🚨 **Ação:** `{acao}`\n"
        f"📄 **Motivo:** {motivo}\n"
    )
    if prova_url: embed.set_image(url=prova_url)
    embed.set_footer(text=f"Segurança Ativa {config['nome']}")
    await canal.send(embed=embed)

async def executar_banimento(guild, membro, staff, motivo, acao_log, prova_url=None):
    bot.ultimos_banimentos.add(membro.id)
    try: await membro.send(f"**Aviso de Banimento**\nVocê foi banido(a).\n**Motivo:** {motivo}")
    except: pass 
    try:
        await membro.ban(reason=f"{staff.name} | {motivo}")
        await log_punicao_bonito(guild, membro, staff, acao_log, motivo, prova_url)
    except Exception as e:
        print(f"Erro ao banir: {e}")

# ==================== AUTOMOD & ANTI-IMAGEM ====================
@bot.event
async def on_message(message):
    if message.author.bot: return
    texto = normalizar_texto(message.content)
    
    # 1. Filtro de Links/Scam
    for termo in TERMOS_BAN:
        if termo in texto:
            await message.delete()
            await executar_banimento(message.guild, message.author, message.guild.me, "Link suspeito / Scam detectado", "Auto-Ban: Scam")
            return

    # 2. Filtro de Palavrões
    for palavrao in PALAVROES:
        if palavrao in texto:
            await message.delete()
            aviso = await message.channel.send(f"⚠️ {message.author.mention}, cuidado com o linguajar!", delete_after=5)
            break

    # 3. Filtro de Imagens (NSFW/Gore)
    if message.attachments:
        for attachment in message.attachments:
            if attachment.filename.lower().endswith(('png', 'jpg', 'jpeg', 'webp')):
                try:
                    img_data = await attachment.read()
                    img = Image.open(BytesIO(img_data))
                    hash_img = str(imagehash.average_hash(img))
                    if hash_img in IMAGENS_BLOQUEADAS:
                        await message.delete()
                        await executar_banimento(message.guild, message.author, message.guild.me, "Imagem bloqueada detectada", "Auto-Ban: Imagem Proibida", attachment.url)
                        return
                except: pass
                
    await bot.process_commands(message)

# ==================== LOGS NATIVOS (MUTE E BAN VIA DISCORD) ====================
@bot.event
async def on_member_ban(guild, user):
    if user.id in bot.ultimos_banimentos: return # Já foi pelo comando
    
    async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
        if entry.target.id == user.id:
            await log_punicao_bonito(guild, user, entry.user, "Banimento", entry.reason or "Sem motivo especificado")
            return

@bot.event
async def on_member_update(before, after):
    # Detectar Mute Nativo
    if before.timed_out_until is None and after.timed_out_until is not None:
        if after.id in bot.ultimos_mutes:
            bot.ultimos_mutes.remove(after.id)
            return
        
        async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_update):
            if entry.target.id == after.id and hasattr(entry.after, 'timed_out_until'):
                duracao = after.timed_out_until - discord.utils.utcnow()
                minutos = int(duracao.total_seconds() / 60)
                await log_punicao_bonito(after.guild, after, entry.user, f"Mute ({minutos}m)", entry.reason or "Sem motivo especificado")
                return

# ==================== LOGS GERAIS E AVATAR ====================
@bot.event
async def on_user_update(before, after):
    for guild in bot.guilds:
        config = obter_config(guild.id)
        if not config: continue
        member = guild.get_member(after.id)
        if not member: continue
        canal_logs = bot.get_channel(config["canal_logs"])
        if not canal_logs: continue

        if before.avatar != after.avatar:
            embed = discord.Embed(title=f"🖼️ {config['nome']} - Alteração de Avatar", color=0x950606, timestamp=discord.utils.utcnow())
            av_antigo = before.avatar.url if before.avatar else before.default_avatar.url
            av_novo = after.avatar.url if after.avatar else after.default_avatar.url

            embed.description = (
                f"👤 **Membro:** {after.mention}\n"
                f"📝 **Nome:** `{after.name}`\n"
                f"🆔 **ID:** `{after.id}`\n\n"
                f"📸 **Avatar Anterior:** [Clique aqui]({av_antigo})\n"
                f"✨ **Avatar Novo:** [Clique aqui]({av_novo})"
            )
            embed.set_thumbnail(url=av_antigo)
            embed.set_image(url=av_novo)
            embed.set_footer(text=f"Segurança Ativa {config['nome']}")
            await canal_logs.send(embed=embed)

# ==================== SISTEMA DE TICKETS ====================
class ViewFechar(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Fechar Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="btn_fechar")
    async def fechar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 Fechando canal em 3 segundos...", ephemeral=True)
        await asyncio.sleep(3)
        await interaction.channel.delete()

async def criar_canal_ticket(interaction: discord.Interaction, setor: str):
    config = obter_config(interaction.guild.id)
    if not config: return
    
    categoria = discord.utils.get(interaction.guild.categories, id=config["categoria_tickets"])
    cargo_staff = interaction.guild.get_role(config["cargo_staff"])
    
    overwrites = {
        interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
        interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True),
        interaction.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
    }
    if cargo_staff: overwrites[cargo_staff] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

    canal = await interaction.guild.create_text_channel(name=f"ticket-{interaction.user.name}-{setor}", category=categoria, overwrites=overwrites)
    
    embed = discord.Embed(
        title=f"🚨 {config['nome']} - Atendimento", 
        description=f"Olá {interaction.user.mention},\nSeu ticket para **{setor.upper()}** foi aberto!\nDescreva detalhadamente o que precisa.", 
        color=0x950606
    )
    await canal.send(content=f"{interaction.user.mention} {cargo_staff.mention if cargo_staff else ''}", embed=embed, view=ViewFechar())
    if not interaction.response.is_done():
        await interaction.response.send_message(f"✅ Ticket criado em {canal.mention}!", ephemeral=True)

class DropdownGhoul(discord.ui.Select):
    def __init__(self):
        opcoes = [discord.SelectOption(label="Denúncias", value="denuncias", emoji="🚨"), discord.SelectOption(label="Suporte", value="suporte", emoji="🛠️")]
        super().__init__(placeholder="Selecione o setor...", min_values=1, max_values=1, options=opcoes, custom_id="sel_ghoul")
    async def callback(self, interaction): await criar_canal_ticket(interaction, self.values[0])

class ViewGhoul(discord.ui.View):
    def __init__(self): 
        super().__init__(timeout=None)
        self.add_item(DropdownGhoul())

# Dropdowns para Blox Kings e Nightware (Versão simplificada p/ espaço, você pode adicionar mais depois)
class DropdownKings(discord.ui.Select):
    def __init__(self):
        super().__init__(placeholder="Selecione o setor...", options=[discord.SelectOption(label="Suporte", value="suporte", emoji="🛠️")], custom_id="sel_kings")
    async def callback(self, interaction): await criar_canal_ticket(interaction, self.values[0])

class DropdownNightware(discord.ui.Select):
    def __init__(self):
        super().__init__(placeholder="Selecione o setor...", options=[discord.SelectOption(label="Suporte", value="suporte", emoji="🛠️")], custom_id="sel_nightware")
    async def callback(self, interaction): await criar_canal_ticket(interaction, self.values[0])

class ViewKings(discord.ui.View):
    def __init__(self): 
        super().__init__(timeout=None)
        self.add_item(DropdownKings())

class ViewNightware(discord.ui.View):
    def __init__(self): 
        super().__init__(timeout=None)
        self.add_item(DropdownNightware())

# ==================== TICKET PERSONALIZADO CRIADO PELO /ticket_criar ====================
class ViewCustomTicket(discord.ui.View):
    def __init__(self, label_btn="Abrir Ticket"):
        super().__init__(timeout=None)
        btn = discord.ui.Button(label=label_btn, style=discord.ButtonStyle.danger, emoji="🎫", custom_id="btn_custom_tkt_fixo")
        btn.callback = self.abrir
        self.add_item(btn)
        
    async def abrir(self, interaction: discord.Interaction):
        await criar_canal_ticket(interaction, "geral")

class ModalCriarTicketNaHora(discord.ui.Modal, title="🎫 Criar Painel de Ticket"):
    titulo = discord.ui.TextInput(label="Título do Embed", placeholder="Ex: CENTRAL DE ATENDIMENTO")
    descricao = discord.ui.TextInput(label="Descrição do Embed", style=discord.TextStyle.paragraph)
    nome_botao = discord.ui.TextInput(label="Nome do Botão", default="Abrir Ticket")
    imagem_url = discord.ui.TextInput(label="URL da Imagem (Opcional)", required=False, placeholder="https://link-da-imagem.png")

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True) # <- IMPEDE O ERRO DE NÃO RESPONDER
        
        embed = discord.Embed(title=self.titulo.value, description=self.descricao.value, color=0x950606)
        if self.imagem_url.value:
            embed.set_image(url=self.imagem_url.value)
        
        await interaction.channel.send(embed=embed, view=ViewCustomTicket(self.nome_botao.value))
        await interaction.followup.send("✅ Painel criado perfeitamente!")

@bot.tree.command(name="ticket_criar", description="Cria um painel de ticket personalizado.")
@app_commands.default_permissions(administrator=True)
async def ticket_criar_slash(interaction: discord.Interaction):
    await interaction.response.send_modal(ModalCriarTicketNaHora())

# ==================== SISTEMA DE SORTEIO AVANÇADO ====================
class SorteioView(discord.ui.View):
    def __init__(self, premio, tempo_segs, ganhadores, cargo_extra, multiplicador):
        super().__init__(timeout=tempo_segs)
        self.premio = premio
        self.qtd = ganhadores
        self.cargo_extra = cargo_extra
        self.multiplicador = multiplicador
        self.participantes = {} # ID -> peso (entradas)

    @discord.ui.button(label="Participar (0)", style=discord.ButtonStyle.primary, emoji="🎉")
    async def participar(self, interaction: discord.Interaction, button: discord.ui.Button):
        peso = 1
        if self.cargo_extra and self.cargo_extra in interaction.user.roles:
            peso = self.multiplicador
            
        if interaction.user.id in self.participantes:
            del self.participantes[interaction.user.id]
            await interaction.response.send_message("❌ Você saiu do sorteio!", ephemeral=True)
        else:
            self.participantes[interaction.user.id] = peso
            await interaction.response.send_message(f"🎉 Você entrou no sorteio! (Você tem {peso}x chances)", ephemeral=True)
        
        button.label = f"Participar ({len(self.participantes)})"
        await interaction.message.edit(view=self)

@bot.tree.command(name="sorteio", description="Cria um sorteio estilo Loritta.")
@app_commands.describe(
    premio="Nome do prêmio (Ex: Fruta Perm)", 
    duracao="Tempo (Ex: 10m, 1h, 1d)", 
    ganhadores="Quantos irão ganhar?", 
    canal="Em qual canal enviar o sorteio?", 
    imagem="Imagem anexada para o sorteio (opcional)", 
    cargo_extra="Cargo que ganha mais chances (opcional)", 
    multiplicador="Multiplicador do cargo extra"
)
@app_commands.default_permissions(administrator=True)
async def sorteio_slash(
    interaction: discord.Interaction, 
    premio: str, duracao: str, ganhadores: int, canal: discord.TextChannel,
    imagem: discord.Attachment = None, cargo_extra: discord.Role = None, multiplicador: int = 2
):
    await interaction.response.defer(ephemeral=True)
    tempo_segs = converter_tempo(duracao)
    
    if not tempo_segs:
        return await interaction.followup.send("❌ Tempo inválido! Use `10m`, `1h`.")

    embed = discord.Embed(
        title=f"🎉 SORTEIO: {premio}",
        description=f"Inscreva-se e comece a ganhar! Quem sabe você não seja o próximo a ganhar?\n\n"
                    f"⏰ **Acaba em:** `{duracao}`\n"
                    f"👑 **Vencedores:** `{ganhadores}`\n"
                    f"👤 **Host:** {interaction.user.mention}\n",
        color=0x950606,
        timestamp=discord.utils.utcnow() + datetime.timedelta(seconds=tempo_segs)
    )
    
    if cargo_extra:
        embed.description += f"\n✨ **Entradas Extras:**\n{cargo_extra.mention} **{multiplicador}x** entradas!"
        
    if imagem:
        embed.set_image(url=imagem.url)

    embed.set_footer(text="Sorteio termina")
    
    view = SorteioView(premio, tempo_segs, ganhadores, cargo_extra, multiplicador)
    msg = await canal.send(embed=embed, view=view)
    await interaction.followup.send(f"✅ Sorteio criado no canal {canal.mention}!")

    await asyncio.sleep(tempo_segs)

    # Processar Vencedores
    if not view.participantes:
        return await canal.send(f"❌ O sorteio de **{premio}** foi encerrado, mas ninguém participou.")

    urna = []
    for uid, peso in view.participantes.items():
        urna.extend([uid] * peso)
        
    ganhadores_unicos = list(set(urna))
    vencedores_finais = random.sample(ganhadores_unicos, min(ganhadores, len(ganhadores_unicos)))
    mencoes = ", ".join([f"<@{uid}>" for uid in vencedores_finais])
    
    embed_fim = discord.Embed(title=f"🎉 SORTEIO ENCERRADO: {premio}", description=f"🏆 **Vencedores:** {mencoes}", color=0x950606)
    await msg.edit(embed=embed_fim, view=None)
    await canal.send(f"🎉 Parabéns {mencoes}! Vocês ganharam **{premio}**!")

# ==================== COMANDOS DE PUNIÇÃO ====================
@bot.tree.command(name="mute", description="Silencia um membro no servidor temporariamente.")
@app_commands.default_permissions(moderate_members=True)
async def mute_slash(interaction: discord.Interaction, membro: discord.Member, tempo_minutos: int, motivo: str = "Sem motivo especificado"):
    await interaction.response.defer(ephemeral=True)
    bot.ultimos_mutes.add(membro.id)
    await membro.timeout(datetime.timedelta(minutes=tempo_minutos), reason=f"{interaction.user.name} | {motivo}")
    await log_punicao_bonito(interaction.guild, membro, interaction.user, f"Mute Comando ({tempo_minutos}m)", motivo)
    await interaction.followup.send(f"✅ {membro.mention} foi silenciado com sucesso.")

@bot.tree.command(name="ban", description="Bane um membro do servidor permanentemente.")
@app_commands.default_permissions(ban_members=True)
async def ban_slash(interaction: discord.Interaction, membro: discord.Member, motivo: str = "Sem motivo especificado"):
    await interaction.response.defer(ephemeral=True)
    await executar_banimento(interaction.guild, membro, interaction.user, motivo, "Banimento Comando")
    await interaction.followup.send(f"🔨 {membro.mention} foi banido com sucesso.")

@bot.event
async def on_ready():
    print(f"✅ Bot logado! {bot.user.name} está online, Comandos sincronizados.")

TOKEN = os.getenv('TOKEN')
bot.run(TOKEN)
