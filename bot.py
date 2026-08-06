import asyncio
import datetime
import os
import re
import random
import time
import json
from io import BytesIO
from threading import Thread

import discord
from discord import app_commands
from discord.ext import commands
from flask import Flask
import imagehash
from PIL import Image

# =====================================================================
# SISTEMA DE BANCO DE DADOS PERSISTENTE (RENDER PROOF)
# =====================================================================
DB_FILE = "database.json"

def carregar_db():
    if not os.path.exists(DB_FILE):
        return {
            "hashes_proibidos": [], 
            "sorteios": {}, 
            "config_servidores": {},
            "advertencias": {}
        }
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except:
        return {
            "hashes_proibidos": [], 
            "sorteios": {}, 
            "config_servidores": {},
            "advertencias": {}
        }

def salvar_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

db = carregar_db()

# =====================================================================
# SERVIDOR WEB KEEP-ALIVE PARA RENDER
# =====================================================================
app = Flask(__name__)

@app.route("/")
def home():
    return "GHOUL SECURITY - Bot de Segurança Máxima Online!"

def run_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

Thread(target=run_server, daemon=True).start()

# =====================================================================
# CONFIGURAÇÕES GLOBAIS E ESTÉTICA VERMELHA TOTAL (0xFF0000)
# =====================================================================
COR_PRINCIPAL = 0xFF0000  # Vermelho Puro Absoluto para TUDO

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
    1143627184842493992: "https://cdn.discordapp.com/attachments/1444429504838631586/1454170002746769530/Banner_ticket_20250205_120340_0000.png",
    1169685424738947172: "https://cdn.discordapp.com/attachments/1183819407013707947/1526281157635870730/file_000000002958720eab459d97fd2c5b8e.png",
    1331323352840933497: "https://cdn.discordapp.com/attachments/1440377531848200295/1452759780111155323/standard.gif",
    1489007277267620013: "https://cdn.discordapp.com/attachments/1431364353482948608/1533832231108214864/file_000000004fd4820eb39bb046269d5d96.png",
}

# =====================================================================
# CLASSE PRINCIPAL DO BOT DE ALTA PERFORMANCE
# =====================================================================
class BotSupremoUltimate(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!", 
            intents=discord.Intents.all(), 
            help_command=None
        )

    async def setup_hook(self):
        self.add_view(TicketPainelView())
        self.add_view(TicketAcoesView())
        
        for msg_id, dados in list(db["sorteios"].items()):
            if dados.get("status") == "ativo":
                self.add_view(ParticiparSorteioView(msg_id, dados["config"]))
                
        try:
            synced = await self.tree.sync()
            print(f"[SYNC] {len(synced)} comandos de barra sincronizados.")
        except Exception as e:
            print(f"[SYNC ERROR] Erro: {e}")

bot = BotSupremoUltimate()

def obter_config(guild_id): 
    return CONFIG_SERVIDORES.get(guild_id, {
        "nome": "Servidor Padrão",
        "canal_logs": None,
        "canal_punicoes": None,
        "categoria_tickets": None,
        "cargo_staff": None
    })

# =====================================================================
# SISTEMA DE LOGS DE PUNIÇÕES (COM AVATAR DO BOT E NOME CORRETO)
# =====================================================================
async def enviar_log_punicao(guild, user, staff, acao, motivo, prova_bytes=None):
    config = obter_config(guild.id)
    if not config or not config.get("canal_punicoes"): return
    canal = guild.get_channel(config["canal_punicoes"])
    if not canal: return

    embed = discord.Embed(
        title=f"🚨 REGISTRO DE SEGURANÇA | {acao}", 
        color=COR_PRINCIPAL, 
        timestamp=discord.utils.utcnow()
    )
    if hasattr(user, "display_avatar") and user.display_avatar:
        embed.set_thumbnail(url=user.display_avatar.url)
    
    embed.add_field(name="👤 Alvo da Ação", value=f"{user.mention}\n(`{user.id}`)", inline=True)
    embed.add_field(name="🛡️ Responsável", value=f"{staff.mention if hasattr(staff, 'mention') else str(staff)}", inline=True)
    embed.add_field(name="📄 Descrição / Motivo", value=f"```ini\n[ {motivo} ]\n```", inline=False)
    
    # RODAPÉ PADRONIZADO GHOUL SECURITY
    avatar_url = bot.user.display_avatar.url if bot.user.display_avatar else None
    embed.set_footer(text=f"GHOUL SECURITY • {guild.name}", icon_url=avatar_url)
    
    try:
        if prova_bytes:
            file = discord.File(BytesIO(prova_bytes), filename="evidencia.png")
            embed.set_image(url="attachment://evidencia.png")
            await canal.send(embed=embed, file=file)
        else:
            await canal.send(embed=embed)
    except Exception as e:
        print(f"Erro log: {e}")

@bot.event
async def on_member_ban(guild, user):
    await asyncio.sleep(1.5)
    async for entry in guild.audit_logs(limit=2, action=discord.AuditLogAction.ban):
        if entry.target.id == user.id:
            if entry.user.id == bot.user.id: return
            await enviar_log_punicao(guild, user, entry.user, "BANIMENTO MANUAL", entry.reason or "Nenhum motivo especificado.")
            break

@bot.event
async def on_member_remove(member):
    await asyncio.sleep(1.5)
    async for entry in member.guild.audit_logs(limit=2, action=discord.AuditLogAction.kick):
        if entry.target.id == member.id:
            if entry.user.id == bot.user.id: return
            await enviar_log_punicao(member.guild, member, entry.user, "EXPULSÃO MANUAL", entry.reason or "Nenhum motivo especificado.")
            break

# =====================================================================
# AUTOMOD INTELIGENTE E GESTÃO DE MENSAGENS
# =====================================================================
@bot.tree.command(name="bloquear_imagem", description="[ADMIN] Adiciona imagem letal. Quem postar será banido.")
@app_commands.default_permissions(administrator=True)
async def bloquear_imagem(interaction: discord.Interaction, imagem: discord.Attachment):
    if not imagem.content_type or not imagem.content_type.startswith("image/"):
        return await interaction.response.send_message("❌ Precisa ser uma imagem.", ephemeral=True)
    
    await interaction.response.defer(ephemeral=True)
    try:
        data = await imagem.read()
        img = Image.open(BytesIO(data)).convert("RGB")
        h = str(imagehash.average_hash(img))
        
        if h not in db["hashes_proibidos"]:
            db["hashes_proibidos"].append(h)
            salvar_db(db)
            
        embed = discord.Embed(
            title="⛔ IMAGEM REGISTRADA", 
            description=f"A imagem foi computada com sucesso.\nQualquer usuário que tentar postá-la será banido.\n**Hash Gerado:** `{h}`", 
            color=COR_PRINCIPAL
        )
        avatar_url = bot.user.display_avatar.url if bot.user.display_avatar else None
        embed.set_footer(text="GHOUL SECURITY", icon_url=avatar_url)
        await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Erro crítico: {e}", ephemeral=True)

@bot.event
async def on_message(message):
    # Ignora mensagens do próprio bot e DMs
    if message.author.bot or not message.guild: 
        return

    # O GRANDE ERRO ESTAVA AQUI: Agora a verificação de Administrador NÃO impede os comandos!
    # Apenas impede que o administrador seja punido pelo AutoMod.
    if not message.author.guild_permissions.administrator:
        
        # 1. VERIFICAÇÃO DE IMAGENS PROIBIDAS (DELETE + BAN)
        if message.attachments and db["hashes_proibidos"]:
            for anexo in message.attachments:
                if anexo.content_type and anexo.content_type.startswith("image/"):
                    try:
                        img_bytes = await anexo.read()
                        img = Image.open(BytesIO(img_bytes)).convert("RGB")
                        img_hash = imagehash.average_hash(img)

                        for h_str in db["hashes_proibidos"]:
                            target_hash = imagehash.hex_to_hash(h_str)
                            if img_hash - target_hash <= 6:
                                try: await message.delete()
                                except: pass

                                try:
                                    embed_aviso = discord.Embed(
                                        title="🚨 BANIMENTO AUTOMÁTICO", 
                                        description=f"Você foi banido de **{message.guild.name}** por postar conteúdo visual estritamente proibido.", 
                                        color=COR_PRINCIPAL
                                    )
                                    embed_aviso.set_footer(text="GHOUL SECURITY", icon_url=bot.user.display_avatar.url if bot.user.display_avatar else None)
                                    await message.author.send(embed=embed_aviso)
                                except: pass

                                try:
                                    await message.guild.ban(message.author, reason="AutoMod Letal: Envio de imagem proibida.")
                                except: pass

                                await enviar_log_punicao(message.guild, message.author, bot.user, "BAN (IMAGEM PROIBIDA)", "O sistema interceptou uma imagem restrita.", prova_bytes=img_bytes)
                                return
                    except Exception as e:
                        print(f"Erro AutoMod Imagem: {e}")

        # 2. FILTRO DE LINKS
        if "discord.gg/" in message.content.lower() or "discord.com/invite/" in message.content.lower():
            try:
                await message.delete()
                embed_link = discord.Embed(description=f"⚠️ {message.author.mention}, a divulgação de links de convite é proibida!", color=COR_PRINCIPAL)
                embed_link.set_footer(text="GHOUL SECURITY", icon_url=bot.user.display_avatar.url if bot.user.display_avatar else None)
                aviso = await message.channel.send(embed=embed_link)
                await aviso.delete(delay=5)
                return
            except: pass

        # 3. FILTRO MASSIVO DE PALAVRÕES
        palavroes = [
            "fdp", "fdps", "f d p", "vsf", "vtnc", "pnc", "tnc", "vtmnc", "pqp", 
            "krl", "crrl", "kralho", "caralh0", "kct", "kacete", "krai", "carai",
            "p0rra", "prra", "mrd", "vsff", "vnc", "fdendo", "caralho", "caralhos", 
            "caralhuda", "caralhudo", "porra", "porraloca", "porrra", "porraloka",
            "merda", "merdinha", "merdoes", "merdão", "bosta", "bostinha", "bostalhão", 
            "bostileiro", "bostola", "buceta", "buketa", "bucetinha", "buseta", "boceta", 
            "bucetão", "puta", "putinha", "putasso", "putona", "putaria", "cu", "cuzao", 
            "cuzão", "cuzinho", "cuzonas", "cusao", "cuzões", "pau", "paumole", "pauzao", 
            "pauzin", "paunocu", "paunoku", "piroca", "pirocudo", "pirok", "pirraca", 
            "pirokuda", "foder", "fodendo", "fodeu", "fodido", "fodida", "fudido", 
            "fudida", "fodão", "foderam", "cacete", "cacetada", "cacetinho", "chupa", 
            "chupando", "chupeta", "chupador", "punheta", "punheteiro", "punheteira", 
            "gozada", "gozar", "gozando", "bicha", "bichona", "boiola", "viado", 
            "viadinho", "viadaço", "traveco", "arrombado", "arrombada", "arrombados", 
            "desgraçado", "desgracado", "desgraçada", "desgracada", "corno", "cornos", 
            "corna", "cornuda", "cornudo", "chifrudo", "chifruda", "vagabundo", 
            "vagabunda", "vagabundos", "vagabundas", "vagaba", "otario", "otária", 
            "otarios", "otárias", "imbecil", "imbecis", "idiota", "idiotas", "retardado", 
            "retardada", "escroto", "escrota", "safado", "safada", "canalha", "canalhas", 
            "miserável", "miseravel", "desgraça", "desgraca", "peste", "praga", "inferno", 
            "babaca", "babacas", "estúpido", "estupido", "estúpida", "estupida", "fedido", 
            "fedida", "fedorento", "fedorenta", "lixo", "lixos", "lixoso", "lixosa", "mongol", 
            "mongolóide", "mongoloide", "nojento", "nojenta", "noia", "nóia", "patife", 
            "pirralho", "pirralha", "pivete", "porco", "porca", "preguiçoso", "preguiçosa", 
            "prostituta", "prostituto", "quenga", "rabudo", "rabuda", "ridículo", "ridiculo", 
            "ridícula", "ridicula", "rola", "rolinha", "sacana", "sapatão", "sapatao", 
            "seboso", "sebosa", "sem-vergonha", "semvergonha", "sujo", "suja", "tarado", 
            "tarada", "trouxa", "trouxas", "vigarista", "xexelento", "xexelenta", "xibiu", 
            "xota", "xoxota", "tomanocu", "toma no cu", "vai tomar no cu", "vai se fuder", 
            "vai se fodir", "puta que pariu", "putaquepariu", "filho da puta"
        ]
        texto_verificacao = re.sub(r"[^a-z0-9\s]", "", message.content.lower())
        palavras_msg = texto_verificacao.split()
        
        for p in palavroes:
            if p in palavras_msg or any(p in w for w in palavras_msg):
                try: await message.delete()
                except: pass
                
                embed_palavra = discord.Embed(
                    description=f"⚠️ {message.author.mention}, Cuidado com seu linguajar seu BOBOCA!", 
                    color=COR_PRINCIPAL
                )
                embed_palavra.set_footer(text="GHOUL SECURITY", icon_url=bot.user.display_avatar.url if bot.user.display_avatar else None)
                msg_alerta = await message.channel.send(embed=embed_palavra)
                await msg_alerta.delete(delay=5)
                return

    # Processa os comandos normalmente (SEJA ADMIN OU NÃO!)
    await bot.process_commands(message)

# =====================================================================
# SISTEMA DE TICKETS PROFISSIONAL (COM GHOUL SECURITY)
# =====================================================================
class TicketAcoesView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Fechar Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="fechar_ticket_btn_persisted", row=0)
    async def fechar_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="🔒 ENCERRANDO TICKET", description=f"O canal será apagado em **5 segundos**...", color=COR_PRINCIPAL)
        embed.set_footer(text="GHOUL SECURITY", icon_url=bot.user.display_avatar.url if bot.user.display_avatar else None)
        await interaction.response.send_message(embed=embed)
        await asyncio.sleep(5)
        try: await interaction.channel.delete()
        except: pass

    @discord.ui.button(label="Reivindicar Ticket", style=discord.ButtonStyle.primary, emoji="✋", custom_id="reivindicar_ticket_btn_persisted", row=0)
    async def reivindicar_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="✋ ATENDIMENTO ASSUMIDO", description=f"O staff {interaction.user.mention} assumiu este ticket.", color=COR_PRINCIPAL)
        embed.set_footer(text="GHOUL SECURITY", icon_url=bot.user.display_avatar.url if bot.user.display_avatar else None)
        await interaction.response.send_message(embed=embed)

class TicketSelectDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Suporte Geral", description="Dúvidas e auxílio", emoji="💬", value="suporte"),
            discord.SelectOption(label="Denúncias", description="Reportar infrações", emoji="🚨", value="denuncia"),
            discord.SelectOption(label="Financeiro / Lojas", description="Pagamentos ou produtos", emoji="🛒", value="compras"),
            discord.SelectOption(label="Parcerias", description="Propostas comerciais", emoji="🤝", value="parceria")
        ]
        super().__init__(placeholder="📂 Selecione um departamento...", options=options, custom_id="ticket_dropdown_main")

    async def callback(self, interaction: discord.Interaction):
        config = obter_config(interaction.guild.id)
        if not config or not config.get("categoria_tickets"):
            return await interaction.response.send_message("❌ Categorias não configuradas.", ephemeral=True)

        categoria = interaction.guild.get_channel(config["categoria_tickets"])
        cargo_staff = interaction.guild.get_role(config["cargo_staff"]) if config.get("cargo_staff") else None

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }
        if cargo_staff:
            overwrites[cargo_staff] = discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True)

        nome_canal = f"ticket-{interaction.user.name.lower()}"
        try:
            canal = await interaction.guild.create_text_channel(name=nome_canal, category=categoria, overwrites=overwrites)
        except Exception as e:
            return await interaction.response.send_message(f"❌ Erro ao criar canal: {e}", ephemeral=True)

        embed_ticket = discord.Embed(
            title="🎫 PAINEL DE ATENDIMENTO", 
            description=f"Olá {interaction.user.mention}!\n\nDepartamento: **`{self.values[0].upper()}`**.\nDescreva seu problema abaixo.", 
            color=COR_PRINCIPAL
        )
        embed_ticket.set_footer(text=f"GHOUL SECURITY • ID: {interaction.user.id}", icon_url=bot.user.display_avatar.url if bot.user.display_avatar else None)

        await canal.send(content=f"{interaction.user.mention} {cargo_staff.mention if cargo_staff else ''}", embed=embed_ticket, view=TicketAcoesView())
        await interaction.response.send_message(f"✅ Ticket aberto: {canal.mention}", ephemeral=True)

class TicketPainelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelectDropdown())

@bot.tree.command(name="painel_tickets", description="[ADMIN] Envia o painel de criação de tickets")
@app_commands.default_permissions(administrator=True)
async def painel_tickets(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎫 CENTRAL DE ATENDIMENTO", 
        description="Selecione o assunto no menu abaixo para abrir um canal de atendimento privado.", 
        color=COR_PRINCIPAL
    )
    banner = IMAGENS_TICKETS.get(interaction.guild_id)
    if banner: embed.set_image(url=banner)
    embed.set_footer(text="GHOUL SECURITY", icon_url=bot.user.display_avatar.url if bot.user.display_avatar else None)
    
    await interaction.channel.send(embed=embed, view=TicketPainelView())
    await interaction.response.send_message("✅ Painel fixado!", ephemeral=True)

# COMANDOS DE BARRA EXCLUSIVOS PARA SUPORTE
@bot.tree.command(name="close", description="[STAFF] Fecha o ticket atual")
async def cmd_close(interaction: discord.Interaction):
    if "ticket-" not in interaction.channel.name:
        return await interaction.response.send_message("❌ Apenas em canais de tickets.", ephemeral=True)
    embed = discord.Embed(title="🔒 TICKET ENCERRADO", description="Apagando em 5 segundos...", color=COR_PRINCIPAL)
    embed.set_footer(text="GHOUL SECURITY", icon_url=bot.user.display_avatar.url if bot.user.display_avatar else None)
    await interaction.response.send_message(embed=embed)
    await asyncio.sleep(5)
    try: await interaction.channel.delete()
    except: pass

@bot.tree.command(name="reivindicar", description="[STAFF] Assume o ticket atual")
async def cmd_reivindicar(interaction: discord.Interaction):
    if "ticket-" not in interaction.channel.name:
        return await interaction.response.send_message("❌ Apenas em canais de tickets.", ephemeral=True)
    embed = discord.Embed(title="✋ REIVINDICADO", description=f"{interaction.user.mention} assumiu o ticket.", color=COR_PRINCIPAL)
    embed.set_footer(text="GHOUL SECURITY", icon_url=bot.user.display_avatar.url if bot.user.display_avatar else None)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="add_membro", description="[STAFF] Adiciona um membro ao ticket")
async def cmd_add_membro(interaction: discord.Interaction, membro: discord.Member):
    if "ticket-" not in interaction.channel.name: return await interaction.response.send_message("❌ Apenas em tickets.", ephemeral=True)
    await interaction.channel.set_permissions(membro, read_messages=True, send_messages=True)
    await interaction.response.send_message(embed=discord.Embed(description=f"✅ {membro.mention} adicionado.", color=COR_PRINCIPAL))

@bot.tree.command(name="rem_membro", description="[STAFF] Remove um membro do ticket")
async def cmd_rem_membro(interaction: discord.Interaction, membro: discord.Member):
    if "ticket-" not in interaction.channel.name: return await interaction.response.send_message("❌ Apenas em tickets.", ephemeral=True)
    await interaction.channel.set_permissions(membro, overwrite=None)
    await interaction.response.send_message(embed=discord.Embed(description=f"✅ {membro.mention} removido.", color=COR_PRINCIPAL))

# =====================================================================
# SISTEMA DE SORTEIOS ÉPICOS 
# =====================================================================
class SorteioModalGenerico(discord.ui.Modal):
    def __init__(self, painel, tipo, titulo):
        super().__init__(title=titulo)
        self.painel = painel
        self.tipo = tipo
        if tipo == "nome": self.campo = discord.ui.TextInput(label="Título do Prêmio", default=painel.config["nome"])
        elif tipo == "desc": self.campo = discord.ui.TextInput(label="Descrição do Sorteio", style=discord.TextStyle.paragraph, default=painel.config["descricao"])
        elif tipo == "vencedores": self.campo = discord.ui.TextInput(label="Quantidade de Vencedores", default=str(painel.config["vencedores"]))
        elif tipo == "duracao": self.campo = discord.ui.TextInput(label="Duração em Minutos", default=str(painel.config["duracao_minutos"]))
        elif tipo == "emoji": self.campo = discord.ui.TextInput(label="Emoji do Botão", default=painel.config["emoji"])
        elif tipo == "img": self.campo = discord.ui.TextInput(label="URL da Imagem Ilustrativa", default=painel.config["imagem"], required=False)
        self.add_item(self.campo)

    async def on_submit(self, interaction: discord.Interaction):
        val = self.campo.value.strip()
        if self.tipo == "nome": self.painel.config["nome"] = val
        elif self.tipo == "desc": self.painel.config["descricao"] = val
        elif self.tipo == "img": self.painel.config["imagem"] = val
        elif self.tipo == "vencedores": self.painel.config["vencedores"] = int(val) if val.isdigit() else 1
        elif self.tipo == "duracao": self.painel.config["duracao_minutos"] = int(val) if val.isdigit() else 60
        elif self.tipo == "emoji": self.painel.config["emoji"] = val
        await interaction.response.edit_message(embed=self.painel.construir_embed(), view=self.painel)

class SorteioEntradaExtraModal(discord.ui.Modal):
    def __init__(self, painel, cargo_id):
        super().__init__(title="Multiplicador")
        self.painel = painel; self.cargo_id = cargo_id
        self.campo = discord.ui.TextInput(label="Peso de Entradas Extras")
        self.add_item(self.campo)

    async def on_submit(self, interaction: discord.Interaction):
        if self.campo.value.isdigit(): self.painel.config["entradas_extras"][str(self.cargo_id)] = int(self.campo.value)
        await interaction.response.edit_message(embed=self.painel.construir_embed(), view=self.painel)

class ParticiparSorteioView(discord.ui.View):
    def __init__(self, msg_id, config):
        super().__init__(timeout=None)
        self.msg_id = str(msg_id); self.config = config
        btn = discord.ui.Button(label="Participar", style=discord.ButtonStyle.danger, emoji=config.get("emoji", "🎉"), custom_id=f"join_sorteio_{msg_id}")
        btn.callback = self.participar_callback
        self.add_item(btn)

    async def participar_callback(self, interaction: discord.Interaction):
        if self.msg_id not in db["sorteios"] or db["sorteios"][self.msg_id]["status"] != "ativo":
            return await interaction.response.send_message("❌ Sorteio encerrado.", ephemeral=True)

        dados = db["sorteios"][self.msg_id]
        uid = str(interaction.user.id)
        user_roles = [str(r.id) for r in interaction.user.roles]

        if uid in dados["participantes_unicos"]:
            return await interaction.response.send_message("🍀 Você já está participando!", ephemeral=True)

        total_entradas = 1
        achou_extras = [qtd for cid, qtd in self.config.get("entradas_extras", {}).items() if cid in user_roles]
        if achou_extras:
            total_entradas += sum(achou_extras) if self.config.get("somar_entradas") else max(achou_extras)

        dados["participantes_unicos"].append(uid)
        for _ in range(total_entradas): dados["pool_entradas"].append(uid)
        salvar_db(db)

        await interaction.response.send_message(f"🎉 Participação confirmada! Entradas: **{total_entradas}x**", ephemeral=True)

class PainelCriacaoSorteioView(discord.ui.View):
    def __init__(self, interaction):
        super().__init__(timeout=None)
        self.aba = "aparencia"
        self.config = {
            "nome": "Sorteio", "descricao": "Clique para participar!", "imagem": "", 
            "vencedores": 1, "duracao_minutos": 60, "emoji": "🎉",
            "canal_id": interaction.channel_id, "entradas_extras": {}, "somar_entradas": False
        }
        self.montar_interface()

    def construir_embed(self):
        embed = discord.Embed(color=COR_PRINCIPAL)
        if self.aba == "aparencia": embed.title = "🎨 Aparência"; embed.description = f"**Título:** {self.config['nome']}\n**Descrição:** {self.config['descricao']}"
        elif self.aba == "geral": embed.title = "⚙️ Geral"; embed.description = f"**Vencedores:** {self.config['vencedores']}\n**Duração:** {self.config['duracao_minutos']}m\n**Canal:** <#{self.config['canal_id']}>"
        elif self.aba == "extras": embed.title = "🎟️ Vantagens"; txt = "\n".join([f"<@&{c}>: **{q}x**" for c, q in self.config["entradas_extras"].items()]); embed.description = txt or "Nenhum"
        return embed

    def montar_interface(self):
        self.clear_items()
        b1 = discord.ui.Button(label="Aparência", style=discord.ButtonStyle.danger if self.aba=="aparencia" else discord.ButtonStyle.secondary, row=0)
        b2 = discord.ui.Button(label="Geral", style=discord.ButtonStyle.danger if self.aba=="geral" else discord.ButtonStyle.secondary, row=0)
        b3 = discord.ui.Button(label="Vantagens", style=discord.ButtonStyle.danger if self.aba=="extras" else discord.ButtonStyle.secondary, row=0)
        
        async def f_apa(i): self.aba="aparencia"; self.montar_interface(); await i.response.edit_message(embed=self.construir_embed(), view=self)
        async def f_ger(i): self.aba="geral"; self.montar_interface(); await i.response.edit_message(embed=self.construir_embed(), view=self)
        async def f_ext(i): self.aba="extras"; self.montar_interface(); await i.response.edit_message(embed=self.construir_embed(), view=self)
        b1.callback=f_apa; b2.callback=f_ger; b3.callback=f_ext
        self.add_item(b1); self.add_item(b2); self.add_item(b3)

        if self.aba == "aparencia":
            btn1 = discord.ui.Button(label="Nome", row=1); btn1.callback = lambda i: i.response.send_modal(SorteioModalGenerico(self, "nome", "Nome"))
            btn2 = discord.ui.Button(label="Descrição", row=1); btn2.callback = lambda i: i.response.send_modal(SorteioModalGenerico(self, "desc", "Descrição"))
            btn3 = discord.ui.Button(label="Imagem", row=1); btn3.callback = lambda i: i.response.send_modal(SorteioModalGenerico(self, "img", "Imagem"))
            self.add_item(btn1); self.add_item(btn2); self.add_item(btn3)
        elif self.aba == "geral":
            btn1 = discord.ui.Button(label="Vencedores", row=1); btn1.callback = lambda i: i.response.send_modal(SorteioModalGenerico(self, "vencedores", "Qtd"))
            btn2 = discord.ui.Button(label="Duração", row=1); btn2.callback = lambda i: i.response.send_modal(SorteioModalGenerico(self, "duracao", "Minutos"))
            select_canal = discord.ui.ChannelSelect(channel_types=[discord.ChannelType.text], row=2)
            async def cb_canal(i): self.config["canal_id"] = select_canal.values[0].id; await i.response.edit_message(embed=self.construir_embed(), view=self)
            select_canal.callback = cb_canal
            self.add_item(btn1); self.add_item(btn2); self.add_item(select_canal)
        elif self.aba == "extras":
            select_extra = discord.ui.RoleSelect(row=1)
            async def cb_ext(i): await i.response.send_modal(SorteioEntradaExtraModal(self, select_extra.values[0].id))
            select_extra.callback = cb_ext
            btn_somar = discord.ui.Button(label="Alternar Soma", style=discord.ButtonStyle.success, row=2)
            async def cb_somar(i): self.config["somar_entradas"] = not self.config["somar_entradas"]; self.montar_interface(); await i.response.edit_message(embed=self.construir_embed(), view=self)
            btn_somar.callback = cb_somar
            self.add_item(select_extra); self.add_item(btn_somar)

        btn_iniciar = discord.ui.Button(label="🚀 PUBLICAR", style=discord.ButtonStyle.success, row=4)
        btn_iniciar.callback = self.publicar
        self.add_item(btn_iniciar)

    async def publicar(self, interaction: discord.Interaction):
        canal = interaction.guild.get_channel(self.config["canal_id"])
        termino = discord.utils.utcnow() + datetime.timedelta(minutes=self.config["duracao_minutos"])

        embed = discord.Embed(title=f"🎉 {self.config['nome']}", description=f"{self.config['descricao']}\n\nClique no botão abaixo!", color=COR_PRINCIPAL)
        embed.add_field(name="🏆 Vencedores", value=f"`{self.config['vencedores']}`", inline=True)
        embed.add_field(name="⏳ Encerra em", value=f"{discord.utils.format_dt(termino, 'R')}", inline=True)
        if self.config["imagem"]: embed.set_image(url=self.config["imagem"])
        embed.set_footer(text="GHOUL SECURITY", icon_url=bot.user.display_avatar.url if bot.user.display_avatar else None)

        msg = await canal.send(embed=embed)
        view = ParticiparSorteioView(msg.id, self.config)
        await msg.edit(view=view)

        db["sorteios"][str(msg.id)] = {"canal_id": canal.id, "status": "ativo", "config": self.config, "participantes_unicos": [], "pool_entradas": [], "timestamp_fim": termino.timestamp()}
        salvar_db(db)
        await interaction.response.edit_message(content="✅ Publicado!", embed=None, view=None)
        bot.loop.create_task(finalizar_sorteio(canal, str(msg.id), self.config["duracao_minutos"]))

async def finalizar_sorteio(canal, msg_id, minutos):
    await asyncio.sleep(minutos * 60)
    if msg_id not in db["sorteios"] or db["sorteios"][msg_id]["status"] != "ativo": return
    
    dados = db["sorteios"][msg_id]
    dados["status"] = "encerrado"
    salvar_db(db)

    try: msg = await canal.fetch_message(int(msg_id))
    except: return

    if not dados["pool_entradas"]:
        embed = discord.Embed(title="😔 CANCELADO", description="Nenhum participante.", color=COR_PRINCIPAL)
        embed.set_footer(text="GHOUL SECURITY", icon_url=bot.user.display_avatar.url if bot.user.display_avatar else None)
        return await msg.edit(embed=embed, view=None)

    vencedores = []
    pool = list(dados["pool_entradas"])
    while len(vencedores) < dados["config"]["vencedores"] and pool:
        escolhido = random.choice(pool)
        if escolhido not in vencedores: vencedores.append(escolhido)

    mentions = ", ".join([f"<@{v}>" for v in vencedores])
    e = msg.embeds[0]
    e.title = f"🎊 ENCERRADO: {dados['config']['nome']}"
    e.description = f"**Ganhadores:** {mentions}"
    e.clear_fields()
    await msg.edit(embed=e, view=None)
    await canal.send(f"🎉 **PARABÉNS** {mentions}! Ganharam **{dados['config']['nome']}**!\n🔗 {msg.jump_url}")

@bot.tree.command(name="sorteio", description="[ADMIN] Painel de sorteio")
@app_commands.default_permissions(administrator=True)
async def cmd_sorteio(interaction: discord.Interaction):
    painel = PainelCriacaoSorteioView(interaction)
    await interaction.response.send_message(embed=painel.construir_embed(), view=painel, ephemeral=True)

@bot.tree.command(name="reroll", description="[ADMIN] Reroll sorteio")
@app_commands.default_permissions(administrator=True)
async def cmd_reroll(interaction: discord.Interaction, mensagem_id: str):
    if mensagem_id not in db["sorteios"] or not db["sorteios"][mensagem_id]["pool_entradas"]:
        return await interaction.response.send_message("❌ Sorteio inválido ou vazio.", ephemeral=True)
    
    dados = db["sorteios"][mensagem_id]
    novo = random.choice(dados["pool_entradas"])
    canal = interaction.guild.get_channel(dados["canal_id"])
    
    embed = discord.Embed(title="🎲 REROLL", description=f"O ganhador atualizado é <@{novo}>", color=COR_PRINCIPAL)
    embed.set_footer(text="GHOUL SECURITY", icon_url=bot.user.display_avatar.url if bot.user.display_avatar else None)
    await interaction.response.send_message(embed=embed)
    if canal: await canal.send(f"🎉 **REROLL!** O novo ganhador é <@{novo}>!")

# =====================================================================
# COMANDOS DE MODERAÇÃO E AVISOS
# =====================================================================
@bot.tree.command(name="ban", description="[MOD] Bane um usuário permanentemente")
@app_commands.default_permissions(ban_members=True)
async def cmd_ban(interaction: discord.Interaction, membro: discord.Member, motivo: str):
    await membro.ban(reason=motivo)
    await enviar_log_punicao(interaction.guild, membro, interaction.user, "BANIMENTO", motivo)
    await interaction.response.send_message(embed=discord.Embed(description=f"✅ {membro.mention} banido.", color=COR_PRINCIPAL))

@bot.tree.command(name="kick", description="[MOD] Expulsa um usuário")
@app_commands.default_permissions(kick_members=True)
async def cmd_kick(interaction: discord.Interaction, membro: discord.Member, motivo: str):
    await membro.kick(reason=motivo)
    await enviar_log_punicao(interaction.guild, membro, interaction.user, "EXPULSÃO", motivo)
    await interaction.response.send_message(embed=discord.Embed(description=f"✅ {membro.mention} expulso.", color=COR_PRINCIPAL))

@bot.tree.command(name="mute", description="[MOD] Silencia usuário (timeout)")
@app_commands.default_permissions(moderate_members=True)
async def cmd_mute(interaction: discord.Interaction, membro: discord.Member, minutos: int, motivo: str):
    await membro.timeout(datetime.timedelta(minutes=minutos), reason=motivo)
    await enviar_log_punicao(interaction.guild, membro, interaction.user, f"CASTIGO ({minutos}m)", motivo)
    await interaction.response.send_message(embed=discord.Embed(description=f"✅ {membro.mention} mutado por {minutos}m.", color=COR_PRINCIPAL))

@bot.tree.command(name="unmute", description="[MOD] Remove silenciamento")
@app_commands.default_permissions(moderate_members=True)
async def cmd_unmute(interaction: discord.Interaction, membro: discord.Member):
    await membro.timeout(None)
    await interaction.response.send_message(embed=discord.Embed(description=f"✅ {membro.mention} desmutado.", color=COR_PRINCIPAL))

@bot.tree.command(name="clear", description="[MOD] Apaga mensagens")
@app_commands.default_permissions(manage_messages=True)
async def cmd_clear(interaction: discord.Interaction, quantidade: int):
    await interaction.response.defer(ephemeral=True)
    apagadas = await interaction.channel.purge(limit=quantidade)
    await interaction.followup.send(embed=discord.Embed(description=f"✅ `{len(apagadas)}` mensagens apagadas.", color=COR_PRINCIPAL), ephemeral=True)

@bot.tree.command(name="aviso", description="[ADMIN] Envia um aviso vermelho")
@app_commands.default_permissions(administrator=True)
async def cmd_aviso(interaction: discord.Interaction, titulo: str, mensagem: str):
    embed = discord.Embed(title=f"📢 {titulo}", description=mensagem, color=COR_PRINCIPAL)
    embed.set_footer(text="GHOUL SECURITY", icon_url=bot.user.display_avatar.url if bot.user.display_avatar else None)
    await interaction.channel.send(embed=embed)
    await interaction.response.send_message("✅ Enviado!", ephemeral=True)

# =====================================================================
# INICIALIZAÇÃO DO BOT
# =====================================================================
@bot.event
async def on_ready():
    print("=" * 60)
    print(f"🤖 GHOUL SECURITY OPERACIONAL: {bot.user.name}")
    print(f"🛡️ Logs e Avatares configurados corretamente.")
    print("=" * 60)

if __name__ == "__main__":
    TOKEN = os.getenv("TOKEN")
    if TOKEN:
        bot.run(TOKEN)
