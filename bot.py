import os
import discord
import requests
import imagehash
import asyncio
import re
import unicodedata
import datetime
import random
from discord.ext import commands, tasks
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
    },
    # NOVO SERVIDOR ADICIONADO
    123456789012345678: {
        "nome": "BELLAZZZ STORE", 
        "canal_logs": 0, 
        "canal_punicoes": 0, 
        "categoria_tickets": 0, 
        "cargo_staff": 0
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
    'c48ff019712fe2c6', '91ac6db293ab09a6', 'c1e1eb965c5e5cd0', 'f5de4a08bdbd5aa5', '956a6e944ac9a6c9', '931e6ae394d3486f'
]

# ==================== ESTRUTURA DO BOT ====================
class MeuBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents, help_command=None)
        self.mensagens_ignoradas = set()
        self.ultimos_banimentos = set() 
        self.ultimos_mutes = set()
        self.midia_cache = {} 

    async def setup_hook(self):
        self.add_view(ViewGhoul())
        self.add_view(ViewKings())
        self.add_view(ViewNightware())
        self.add_view(ViewValidar())
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

def converter_tempo(tempo_str):
    """Converte strings como 10m, 1h, 2d para segundos."""
    match = re.match(r"^(\d+)([mhd])$", tempo_str.lower().strip())
    if not match:
        return None
    valor, unidade = int(match.group(1)), match.group(2)
    if unidade == 'm': return valor * 60
    if unidade == 'h': return valor * 3600
    if unidade == 'd': return valor * 86400
    return None

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
    if hasattr(user, 'display_avatar') and user.display_avatar: 
        embed.set_thumbnail(url=user.display_avatar.url)
    
    # Formatação sem quebra de menção mobile
    description = (
        f"👤 **Usuário:** {user.mention} (`{user.name}`)\n"
        f"🆔 **ID:** `{user.id}`\n"
        f"🛡️ **Staff:** {staff.mention}\n"
        f"🚨 **Ação:** `{acao}`\n"
        f"📄 **Motivo:** {motivo}\n"
    )
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
    try: await membro.send(carta_dm)
    except: pass 

    try:
        await membro.ban(reason=f"{staff.name} | {motivo}")
        await log_punicao_bonito(guild, membro, staff, acao_log, motivo, prova_url)
        return True
    except Exception as e:
        print(f"[ERRO PERMISSÃO] Não foi possível banir o usuário {membro.name} ({membro.id}). Detalhe: {e}")
        return False

# ==================== EVLOGS COMPLETO DO GS (GAMERSAFER) ====================
@bot.event
async def on_guild_channel_create(channel):
    config = obter_config(channel.guild.id)
    if config and (canal_logs := bot.get_channel(config["canal_logs"])):
        embed = discord.Embed(title=f"📁 {config['nome']} - Canal Criado", color=0x950606, timestamp=discord.utils.utcnow())
        embed.description = f"➕ **Nome:** {channel.mention} (`{channel.name}`)\n🆔 **ID:** `{channel.id}`\n🏷️ **Tipo:** `{str(channel.type).capitalize()}`"
        embed.set_footer(text=f"Segurança Ativa {config['nome']}")
        await canal_logs.send(embed=embed)

@bot.event
async def on_guild_channel_delete(channel):
    config = obter_config(channel.guild.id)
    if config and (canal_logs := bot.get_channel(config["canal_logs"])):
        embed = discord.Embed(title=f"🗑️ {config['nome']} - Canal Apagado", color=0x950606, timestamp=discord.utils.utcnow())
        embed.description = f"❌ **Nome:** `{channel.name}`\n🆔 **ID:** `{channel.id}`\n🏷️ **Tipo:** `{str(channel.type).capitalize()}`"
        embed.set_footer(text=f"Segurança Ativa {config['nome']}")
        await canal_logs.send(embed=embed)

@bot.event
async def on_guild_role_create(role):
    config = obter_config(role.guild.id)
    if config and (canal_logs := bot.get_channel(config["canal_logs"])):
        embed = discord.Embed(title=f"🛡️ {config['nome']} - Cargo Criado", color=0x950606, timestamp=discord.utils.utcnow())
        embed.description = f"➕ **Cargo:** {role.mention} (`{role.name}`)\n🆔 **ID:** `{role.id}`"
        embed.set_footer(text=f"Segurança Ativa {config['nome']}")
        await canal_logs.send(embed=embed)

@bot.event
async def on_guild_role_delete(role):
    config = obter_config(role.guild.id)
    if config and (canal_logs := bot.get_channel(config["canal_logs"])):
        embed = discord.Embed(title=f"🗑️ {config['nome']} - Cargo Deletado", color=0x950606, timestamp=discord.utils.utcnow())
        embed.description = f"❌ **Cargo:** `{role.name}`\n🆔 **ID:** `{role.id}`"
        embed.set_footer(text=f"Segurança Ativa {config['nome']}")
        await canal_logs.send(embed=embed)

@bot.event
async def on_invite_create(invite):
    config = obter_config(invite.guild.id)
    if config and (canal_logs := bot.get_channel(config["canal_logs"])):
        embed = discord.Embed(title=f"🔗 {config['nome']} - Convite Criado", color=0x950606, timestamp=discord.utils.utcnow())
        embed.description = f"👤 **Criador:** {invite.inviter.mention if invite.inviter else 'Desconhecido'}\n🔗 **Código:** `{invite.code}`\n💬 **Canal:** {invite.channel.mention}"
        embed.set_footer(text=f"Segurança Ativa {config['nome']}")
        await canal_logs.send(embed=embed)

@bot.event
async def on_guild_emojis_update(guild, before, after):
    config = obter_config(guild.id)
    if config and (canal_logs := bot.get_channel(config["canal_logs"])):
        if len(before) < len(after):
            novo = [e for e in after if e not in before][0]
            embed = discord.Embed(title=f"😀 {config['nome']} - Novo Emoji", color=0x950606, timestamp=discord.utils.utcnow())
            embed.description = f"✨ **Emoji:** {novo} (`{novo.name}`)\n🆔 **ID:** `{novo.id}`"
            await canal_logs.send(embed=embed)
        elif len(before) > len(after):
            removido = [e for e in before if e not in after][0]
            embed = discord.Embed(title=f"🗑️ {config['nome']} - Emoji Removido", color=0x950606, timestamp=discord.utils.utcnow())
            embed.description = f"❌ **Emoji:** `{removido.name}`\n🆔 **ID:** `{removido.id}`"
            await canal_logs.send(embed=embed)

# CORREÇÃO DO ERRO "VOCÊ NÃO TEM ACESSO A ESTE LINK" (AVATAR/PERFIL LOGS)
@bot.event
async def on_user_update(before, after):
    for guild in bot.guilds:
        config = obter_config(guild.id)
        if not config: continue
        member = guild.get_member(after.id)
        if not member: continue
        canal_logs = bot.get_channel(config["canal_logs"])
        if not canal_logs: continue

        # Avatar Global - Formatado sem dar bug de "sem acesso" no Discord mobile
        if before.avatar != after.avatar:
            embed = discord.Embed(
                title=f"🖼️ {config['nome']} - Alteração de Avatar", 
                color=0x950606, 
                timestamp=discord.utils.utcnow()
            )
            
            avatar_antigo_url = before.avatar.url if before.avatar else before.default_avatar.url
            avatar_novo_url = after.avatar.url if after.avatar else after.default_avatar.url

            # Substituído a menção crua por texto formatado limpo
            embed.description = (
                f"👤 **Membro:** **{after.display_name}** (`@{after.name}`)\n"
                f"🆔 **ID:** `{after.id}`\n\n"
                f"📸 **Avatar Anterior:** [Clique para abrir]({avatar_antigo_url})\n"
                f"✨ **Avatar Novo:** [Clique para abrir]({avatar_novo_url})\n\n"
                f"*Foto alterada globalmente pelo usuário.*"
            )
            embed.set_thumbnail(url=avatar_antigo_url)
            embed.set_image(url=avatar_novo_url)
            embed.set_footer(text=f"Segurança Ativa {config['nome']}", icon_url=guild.icon.url if guild.icon else None)
            await canal_logs.send(embed=embed)

# ==================== SISTEMA DE TICKETS COM NOVAS OPÇÕES ====================
class DropdownGhoul(discord.ui.Select):
    def __init__(self):
        opcoes = [
            discord.SelectOption(label="Denúncias", value="denuncias", description="Denúncias, ajuda técnica e revisão.", emoji="🚨"), 
            discord.SelectOption(label="Suporte", value="suporte", description="Recorra a uma punição (warn/mute).", emoji="🛠️"), 
            discord.SelectOption(label="Dúvidas", value="duvidas", description="Tire dúvidas sobre a comunidade ou regras.", emoji="❓"),
            discord.SelectOption(label="Exposed", value="exposed", description="Falar sobre membro expondo outro.", emoji="⚠️"),
            discord.SelectOption(label="Parcerias", value="parcerias", description="Fazer parcerias com o servidor.", emoji="🤝") # NOVO TICKET
        ]
        super().__init__(placeholder="Selecione o setor do suporte...", min_values=1, max_values=1, options=opcoes, custom_id="sel_ghoul")
    async def callback(self, interaction: discord.Interaction): 
        await criar_canal_ticket(interaction, self.values[0])

class DropdownKings(discord.ui.Select):
    def __init__(self):
        opcoes = [
            discord.SelectOption(label="Robux", value="robux", description="Comprar Robux ou ver tabelas", emoji="💰"), 
            discord.SelectOption(label="Gamepass", value="gamepass", description="Comprar Gamepasses do Blox Fruits", emoji="📦"), 
            discord.SelectOption(label="Frutas Perm", value="frutas_perm", description="Comprar Frutas Permanentes", emoji="🍊"),
            discord.SelectOption(label="Frutas Físicas", value="frutas_fisicas", description="Comprar Frutas Físicas (Inventário)", emoji="🍎"),
            discord.SelectOption(label="Contas GHM/Fruta", value="contas", description="Geral, Fruta Inv ou Contas Random", emoji="💸"),
            discord.SelectOption(label="Resgate", value="resgate", description="Resgatar compras ou prêmios.", emoji="🎁") # NOVO TICKET
        ]
        super().__init__(placeholder="Selecione a categoria correta no menu abaixo...", min_values=1, max_values=1, options=opcoes, custom_id="sel_kings")
    async def callback(self, interaction: discord.Interaction): 
        await criar_canal_ticket(interaction, self.values[0])

class DropdownNightware(discord.ui.Select):
    def __init__(self):
        opcoes = [
            discord.SelectOption(label="Comprar", value="compras", description="Adquirir produtos de nossa loja.", emoji="🛒"), 
            discord.SelectOption(label="Financeiro", value="financeiro", description="Tratar de pagamentos, reembolsos e faturamento.", emoji="💳"), 
            discord.SelectOption(label="Suporte", value="suporte", description="Atendimento geral para dúvidas e problemas.", emoji="🛠️")
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

class ViewValidar(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="Validar", style=discord.ButtonStyle.danger, emoji="🎫", custom_id="btn_validar_cod")
    async def validar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await criar_canal_ticket(interaction, "coldawn")

class ViewFechar(discord.ui.View):
    def __init__(self): 
        super().__init__(timeout=None)
    @discord.ui.button(label="Fechar Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="btn_fechar")
    async def fechar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 Fechando canal em 3 segundos...", ephemeral=True)
        await asyncio.sleep(3)
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
            f"Seu ticket para **{setor.upper()}** foi aberto com sucesso!\n"
            f"Descreva detalhadamente o que precisa abaixo para que a equipe possa te responder."
        ), 
        color=0x950606
    )
    await canal.send(content=f"{interaction.user.mention} {cargo_staff.mention if cargo_staff else ''}", embed=embed, view=ViewFechar())
    await interaction.response.send_message(f"✅ Ticket criado em {canal.mention}!", ephemeral=True)

# ==================== SISTEMA DE SORTEIO ESTILO LORITTA ====================
class SorteioView(discord.ui.View):
    def __init__(self, premio, tempo_segs, quantidade_vencedores):
        super().__init__(timeout=tempo_segs)
        self.premio = premio
        self.vencedores_qtd = quantidade_vencedores
        self.participantes = set()

    @discord.ui.button(label="Participar (0)", style=discord.ButtonStyle.success, emoji="🎉")
    async def participar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id in self.participantes:
            self.participantes.remove(interaction.user.id)
            await interaction.response.send_message("❌ Você saiu do sorteio!", ephemeral=True)
        else:
            self.participantes.add(interaction.user.id)
            await interaction.response.send_message("🎉 Você entrou no sorteio com sucesso!", ephemeral=True)
        
        button.label = f"Participar ({len(self.participantes)})"
        await interaction.message.edit(view=self)

class ModalSorteio(discord.ui.Modal, title="🎉 Criar Novo Sorteio"):
    nome_sorteio = discord.ui.TextInput(label="Título do Sorteio", placeholder="Ex: 1000 Robux / Fruta Perm")
    descricao = discord.ui.TextInput(label="Descrição", style=discord.TextStyle.paragraph, placeholder="Detalhes sobre o sorteio...")
    duracao = discord.ui.TextInput(label="Duração (ex: 10m, 1h, 1d)", placeholder="10m")
    vencedores = discord.ui.TextInput(label="Quantidade de Vencedores", default="1")

    async def on_submit(self, interaction: discord.Interaction):
        tempo_segs = converter_tempo(self.duracao.value)
        if not tempo_segs:
            await interaction.response.send_message("❌ Tempo inválido! Use algo como `10m`, `1h` ou `1d`.", ephemeral=True)
            return

        qtd_vencedores = int(self.vencedores.value) if self.vencedores.value.isdigit() else 1
        
        embed = discord.Embed(
            title=f"🎉 SORTEIO: {self.nome_sorteio.value}",
            description=f"{self.descricao.value}\n\n⏰ **Tempo:** `{self.duracao.value}`\n👑 **Vencedores:** `{qtd_vencedores}`\n👤 **Criado por:** {interaction.user.mention}",
            color=0x950606,
            timestamp=discord.utils.utcnow() + datetime.timedelta(seconds=tempo_segs)
        )
        embed.set_footer(text="Termina em")

        view = SorteioView(self.nome_sorteio.value, tempo_segs, qtd_vencedores)
        await interaction.response.send_message("✅ Sorteio iniciado com sucesso!", ephemeral=True)
        msg = await interaction.channel.send(embed=embed, view=view)

        await asyncio.sleep(tempo_segs)

        # Finalizar sorteio
        if not view.participantes:
            await interaction.channel.send(f"❌ O sorteio de **{self.nome_sorteio.value}** foi encerrado, mas ninguém participou.")
            return

        ganhadores = random.sample(list(view.participantes), min(qtd_vencedores, len(view.participantes)))
        mencoes = ", ".join([f"<@{uid}>" for uid in ganhadores])
        
        embed_fim = discord.Embed(
            title=f"🎉 SORTEIO ENCERRADO: {self.nome_sorteio.value}",
            description=f"🏆 **Vencedores:** {mencoes}\n🎉 Parabéns! Entrem em contato com a Staff.",
            color=0x950606
        )
        await msg.edit(embed=embed_fim, view=None)
        await interaction.channel.send(f"🎉 Parabéns {mencoes}! Vocês venceram o sorteio de **{self.nome_sorteio.value}**!")

# ==================== COMANDOS DE BARRA ATUALIZADOS ====================
@bot.tree.command(name="sorteio", description="Cria um novo sorteio estilo Loritta no canal.")
@app_commands.default_permissions(administrator=True)
async def sorteio_slash(interaction: discord.Interaction):
    await interaction.response.send_modal(ModalSorteio())

@bot.tree.command(name="close", description="Fecha o canal de ticket atual imediatamente.")
@app_commands.command(name="fechar", description="Fecha o canal de ticket atual imediatamente.")
async def fechar_slash(interaction: discord.Interaction):
    if "ticket-" not in interaction.channel.name:
        await interaction.response.send_message("❌ Este comando só pode ser usado dentro de um ticket!", ephemeral=True)
        return
    await interaction.response.send_message("🔒 Fechando ticket em 3 segundos...")
    await asyncio.sleep(3)
    await interaction.channel.delete()

class ModalCriarTicketNaHora(discord.ui.Modal, title="🎫 Criar Painel de Ticket"):
    titulo = discord.ui.TextInput(label="Título do Embed", placeholder="Ex: CENTRAL DE ATENDIMENTO")
    descricao = discord.ui.TextInput(label="Descrição do Embed", style=discord.TextStyle.paragraph)
    nome_botao = discord.ui.TextInput(label="Nome do Botão de Abrir Ticket", default="Abrir Ticket")

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(title=self.titulo.value, description=self.descricao.value, color=0x950606)
        
        class ViewCustomTicket(discord.ui.View):
            def __init__(self, label_botao):
                super().__init__(timeout=None)
                self.add_item(discord.ui.Button(label=label_botao, style=discord.ButtonStyle.danger, emoji="🎫", custom_id="btn_custom_tkt"))
        
        await interaction.channel.send(embed=embed, view=ViewCustomTicket(self.nome_botao.value))
        await interaction.response.send_message("✅ Painel de ticket criado na hora com sucesso!", ephemeral=True)

@bot.tree.command(name="ticket_criar", description="Cria um painel de ticket personalizado na hora.")
@app_commands.default_permissions(administrator=True)
async def ticket_criar_slash(interaction: discord.Interaction):
    await interaction.response.send_modal(ModalCriarTicketNaHora())

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
        await interaction.followup.send("❌ Não foi possível mutar. Verifique as permissões.")

@bot.tree.command(name="ban", description="Bane um membro do servidor permanentemente.")
@app_commands.default_permissions(ban_members=True)
async def ban_slash(interaction: discord.Interaction, membro: discord.Member, motivo: str = "Sem motivo especificado"):
    await interaction.response.defer(ephemeral=True)
    sucesso = await executar_banimento(interaction.guild, membro, interaction.user, motivo, "Banimento Comando")
    if sucesso:
        await interaction.followup.send(f"🔨 O usuário {membro.mention} foi banido com sucesso.")
    else:
        await interaction.followup.send("❌ Erro ao banir. Verifique o cargo do usuário.")

@bot.event
async def on_ready():
    print(f"✅ Sistema perfeito! {bot.user.name} está online, comandos sincronizados e operando na cor #950606.")

TOKEN = os.getenv('TOKEN')
bot.run(TOKEN)
