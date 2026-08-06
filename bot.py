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
    return "Bot de Segurança Máxima & Gestão Integrada Online (Versão 1000+ Linhas)."

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
        # Persistência de views vitais para sobrevivência a reboots
        self.add_view(TicketPainelView())
        self.add_view(TicketAcoesView())
        
        # Restaura todos os sorteios ativos salvos no banco de dados
        for msg_id, dados in list(db["sorteios"].items()):
            if dados.get("status") == "ativo":
                self.add_view(ParticiparSorteioView(msg_id, dados["config"]))
                
        try:
            synced = await self.tree.sync()
            print(f"[SYNC] {len(synced)} comandos de barra sincronizados globalmente.")
        except Exception as e:
            print(f"[SYNC ERROR] Erro ao sincronizar comandos: {e}")

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
# SISTEMA DE LOGS DE PUNIÇÕES E AUDITORIA AVANÇADA
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
    embed.set_footer(text=f"Core de Proteção Absoluta • {guild.name}")
    
    try:
        if prova_bytes:
            file = discord.File(BytesIO(prova_bytes), filename="evidencia_proibida.png")
            embed.set_image(url="attachment://evidencia_proibida.png")
            await canal.send(embed=embed, file=file)
        else:
            await canal.send(embed=embed)
    except Exception as e:
        print(f"Erro ao enviar log de punição: {e}")

@bot.event
async def on_member_ban(guild, user):
    await asyncio.sleep(1.5)
    async for entry in guild.audit_logs(limit=2, action=discord.AuditLogAction.ban):
        if entry.target.id == user.id:
            if entry.user.id == bot.user.id: return # Ignora se foi o próprio bot que baniu
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
# AUTOMOD INTELIGENTE: BLOQUEIO, DELETE E BAN DE IMAGENS PROIBIDAS
# =====================================================================
@bot.tree.command(name="bloquear_imagem", description="[ADMIN] Adiciona uma imagem ao banco de dados letal (Quem postar é banido e a imagem é apagada)")
@app_commands.default_permissions(administrator=True)
async def bloquear_imagem(interaction: discord.Interaction, imagem: discord.Attachment):
    if not imagem.content_type or not imagem.content_type.startswith("image/"):
        return await interaction.response.send_message("❌ O arquivo enviado precisa obrigatoriamente ser uma imagem.", ephemeral=True)
    
    await interaction.response.defer(ephemeral=True)
    try:
        data = await imagem.read()
        img = Image.open(BytesIO(data)).convert("RGB")
        h = str(imagehash.average_hash(img))
        
        if h not in db["hashes_proibidos"]:
            db["hashes_proibidos"].append(h)
            salvar_db(db)
            
        embed = discord.Embed(
            title="⛔ IMAGEM REGISTRADA NO BANCO LETAL", 
            description=f"A imagem foi computada com sucesso.\nQualquer usuário que tentar postá-la terá a mensagem **deletada instantaneamente** e sofrerá **banimento permanente**.\n\n**Hash Gerado:** `{h}`", 
            color=COR_PRINCIPAL
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Erro crítico ao processar o hash da imagem: {e}", ephemeral=True)

@bot.tree.command(name="remover_imagem_bloqueada", description="[ADMIN] Remove um hash do banco de imagens proibidas")
@app_commands.default_permissions(administrator=True)
async def remover_imagem_bloqueada(interaction: discord.Interaction, hash_str: str):
    if hash_str in db["hashes_proibidos"]:
        db["hashes_proibidos"].remove(hash_str)
        salvar_db(db)
        await interaction.response.send_message(f"✅ O hash `{hash_str}` foi removido com sucesso da lista proibida.", ephemeral=True)
    else:
        await interaction.response.send_message("❌ Hash não encontrado no banco de dados.", ephemeral=True)

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild: return
    if message.author.guild_permissions.administrator: return

    # 1. VERIFICAÇÃO RIGOROSA DE IMAGENS PROIBIDAS (DELETE + BAN)
    if message.attachments and db["hashes_proibidos"]:
        for anexo in message.attachments:
            if anexo.content_type and anexo.content_type.startswith("image/"):
                try:
                    img_bytes = await anexo.read()
                    img = Image.open(BytesIO(img_bytes)).convert("RGB")
                    img_hash = imagehash.average_hash(img)

                    for h_str in db["hashes_proibidos"]:
                        target_hash = imagehash.hex_to_hash(h_str)
                        # Distância menor ou igual a 6 indica imagens visualmente idênticas ou variantes modificadas
                        if img_hash - target_hash <= 6:
                            # AÇÃO 1: APAGAR IMEDIATAMENTE A MENSAGEM
                            try: 
                                await message.delete()
                            except Exception as ex: 
                                print(f"Erro ao apagar mensagem proibida: {ex}")

                            # AÇÃO 2: TENTAR AVISAR O USUÁRIO NO PRIVADO
                            try:
                                embed_aviso = discord.Embed(
                                    title="🚨 BANIMENTO AUTOMÁTICO APLICADO", 
                                    description=f"Você foi banido permanentemente do servidor **{message.guild.name}** por postar conteúdo visual estritamente proibido pelas diretrizes de segurança.", 
                                    color=COR_PRINCIPAL
                                )
                                await message.author.send(embed=embed_aviso)
                            except: 
                                pass

                            # AÇÃO 3: APLICAR O BANIMENTO NO SERVIDOR
                            try:
                                await message.guild.ban(
                                    message.author, 
                                    reason="AutoMod Letal: Envio de imagem proibida registrada no banco de dados."
                                )
                            except Exception as ex:
                                print(f"Erro ao banir usuário do automod: {ex}")

                            # AÇÃO 4: REGISTRAR LOG DETALHADA COM A PROVA ANEXADA
                            await enviar_log_punicao(
                                message.guild, 
                                message.author, 
                                bot.user, 
                                "BANIMENTO AUTOMÁTICO (IMAGEM PROIBIDA)", 
                                "O sistema detectou e interceptou o envio de uma imagem restrita cadastrada no banco de hashes.", 
                                prova_bytes=img_bytes
                            )
                            return
                except Exception as e:
                    print(f"Erro interno no processamento de hash da mensagem: {e}")

    # 2. FILTRO ANTI-DIVULGAÇÃO DE LINKS DE OUTROS SERVIDORES
    if "discord.gg/" in message.content.lower() or "discord.com/invite/" in message.content.lower():
        try:
            await message.delete()
            aviso = await message.channel.send(embed=discord.Embed(description=f"⚠️ {message.author.mention}, a divulgação de links de convite é proibida neste servidor!", color=COR_PRINCIPAL))
            await aviso.delete(delay=5)
            return
        except:
            pass

    # 3. FILTRO DE PALAVRÕES E OFENSAS GRAVES
    palavroes = ["fdp", "fdps", "f d p", "vsf", "vtnc", "pnc", "tnc", "vtmnc", "pqp", 
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
            try: 
                await message.delete()
            except: 
                pass
            
            embed_palavra = discord.Embed(
                description=f"⚠️ {message.author.mention}, Cuidado com seu linguajar seu BOBOCA!.", 
                color=COR_PRINCIPAL
            )
            msg_alerta = await message.channel.send(embed=embed_palavra)
            await msg_alerta.delete(delay=5)
            return

    await bot.process_commands(message)

# =====================================================================
# SISTEMA DE TICKETS PROFISSIONAL (COM BOTÕES LADO A LADO E COMANDOS)
# =====================================================================
class TicketAcoesView(discord.ui.View):
    """
    View persistente que contém os botões 'Fechar Ticket' e 'Reivindicar Ticket' 
    EXATAMENTE LADO A LADO na mesma linha.
    """
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Fechar Ticket", 
        style=discord.ButtonStyle.danger, 
        emoji="🔒", 
        custom_id="fechar_ticket_btn_persisted", 
        row=0
    )
    async def fechar_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Valida se o usuário tem permissão ou é staff/admin para fechar
        embed = discord.Embed(
            title="🔒 TICKET SENDO ENCERRADO",
            description=f"Solicitado por {interaction.user.mention}. Este canal será completamente apagado em **5 segundos**...", 
            color=COR_PRINCIPAL
        )
        await interaction.response.send_message(embed=embed)
        await asyncio.sleep(5)
        try:
            await interaction.channel.delete(reason=f"Ticket fechado por {interaction.user}")
        except Exception as e:
            print(f"Erro ao deletar canal de ticket: {e}")

    @discord.ui.button(
        label="Reivindicar Ticket", 
        style=discord.ButtonStyle.primary, 
        emoji="✋", 
        custom_id="reivindicar_ticket_btn_persisted", 
        row=0
    )
    async def reivindicar_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Altera visualmente o botão ou avisa no canal quem assumiu
        embed = discord.Embed(
            title="✋ ATENDIMENTO ASSUMIDO", 
            description=f"O membro da staff {interaction.user.mention} reivindicou este ticket e assumiu a responsabilidade pelo atendimento exclusivo.", 
            color=COR_PRINCIPAL
        )
        await interaction.response.send_message(embed=embed)

class TicketSelectDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Suporte Geral", description="Dúvidas gerais, orientações e auxílio", emoji="💬", value="suporte"),
            discord.SelectOption(label="Denúncias", description="Reportar comportamentos tóxicos ou infrações", emoji="🚨", value="denuncia"),
            discord.SelectOption(label="Financeiro / Lojas", description="Questões referentes a pagamentos, cash ou produtos", emoji="🛒", value="compras"),
            discord.SelectOption(label="Parcerias", description="Propostas de parcerias e divulgações oficiais", emoji="🤝", value="parceria")
        ]
        super().__init__(placeholder="📂 Clique aqui para escolher o departamento desejado...", options=options, custom_id="ticket_dropdown_main")

    async def callback(self, interaction: discord.Interaction):
        config = obter_config(interaction.guild.id)
        if not config or not config.get("categoria_tickets"):
            return await interaction.response.send_message("❌ As categorias de tickets deste servidor não foram configuradas corretamente pelo administrador.", ephemeral=True)

        categoria = interaction.guild.get_channel(config["categoria_tickets"])
        cargo_staff = interaction.guild.get_role(config["cargo_staff"]) if config.get("cargo_staff") else None

        # Configura permissões privadas para o canal do ticket
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }
        if cargo_staff:
            overwrites[cargo_staff] = discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True)

        # Criação do canal do ticket
        nome_canal = f"ticket-{interaction.user.name.lower()}"
        try:
            canal = await interaction.guild.create_text_channel(
                name=nome_canal, 
                category=categoria if categoria else None, 
                overwrites=overwrites,
                topic=f"Atendimento privado de {interaction.user} (ID: {interaction.user.id}) - Departamento: {self.values[0].upper()}"
            )
        except Exception as e:
            return await interaction.response.send_message(f"❌ Ocorreu um erro ao criar o canal do ticket: {e}", ephemeral=True)

        embed_ticket = discord.Embed(
            title="🎫 PAINEL DE ATENDIMENTO PRIVADO", 
            description=f"Olá {interaction.user.mention}!\n\nSeu ticket foi aberto com sucesso no departamento: **`{self.values[0].upper()}`**.\nPor favor, descreva detalhadamente o seu problema ou solicitação e aguarde um membro da nossa equipe responder.\n\nUtilize os botões abaixo para **Reivindicar** ou **Fechar** o atendimento.", 
            color=COR_PRINCIPAL
        )
        embed_ticket.set_footer(text=f"ID do Usuário: {interaction.user.id}")

        # Envia a mensagem com os botões lado a lado
        await canal.send(content=f"{interaction.user.mention} {cargo_staff.mention if cargo_staff else ''}", embed=embed_ticket, view=TicketAcoesView())
        await interaction.response.send_message(f"✅ Seu ticket foi aberto com privacidade com sucesso: {canal.mention}", ephemeral=True)

class TicketPainelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelectDropdown())

@bot.tree.command(name="painel_tickets", description="[ADMIN] Envia o painel interativo definitivo de criação de tickets")
@app_commands.default_permissions(administrator=True)
async def painel_tickets(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎫 CENTRAL DE ATENDIMENTO E SUPORTE", 
        description="Precisa de ajuda com alguma questão, denúncia ou transação?\nSelecione o assunto correspondente no menu suspenso abaixo para abrir um canal de atendimento exclusivo e privado com nossa staff.", 
        color=COR_PRINCIPAL
    )
    banner = IMAGENS_TICKETS.get(interaction.guild_id)
    if banner: 
        embed.set_image(url=banner)
    embed.set_footer(text="Atendimento automatizado e seguro.")
    
    await interaction.channel.send(embed=embed, view=TicketPainelView())
    await interaction.response.send_message("✅ Painel de tickets gerado e fixado com sucesso!", ephemeral=True)

# COMANDOS DE BARRA EXCLUSIVOS PARA SUPORTE E TICKETS
@bot.tree.command(name="close", description="[STAFF] Fecha o ticket em andamento atual")
async def cmd_close(interaction: discord.Interaction):
    if "ticket-" not in interaction.channel.name:
        return await interaction.response.send_message("❌ Este comando só pode ser executado dentro de canais de tickets.", ephemeral=True)
    
    embed = discord.Embed(
        title="🔒 TICKET ENCERRADO",
        description=f"O canal será apagado em 5 segundos por ordem de {interaction.user.mention}.", 
        color=COR_PRINCIPAL
    )
    await interaction.response.send_message(embed=embed)
    await asyncio.sleep(5)
    try:
        await interaction.channel.delete(reason=f"Fechado via comando /close por {interaction.user}")
    except:
        pass

@bot.tree.command(name="reivindicar", description="[STAFF] Assume o atendimento do ticket atual")
async def cmd_reivindicar(interaction: discord.Interaction):
    if "ticket-" not in interaction.channel.name:
        return await interaction.response.send_message("❌ Este comando só pode ser executado dentro de canais de tickets.", ephemeral=True)
        
    embed = discord.Embed(
        title="✋ TICKET REIVINDICADO", 
        description=f"O membro da staff {interaction.user.mention} assumiu o controle total deste atendimento.", 
        color=COR_PRINCIPAL
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="add_membro", description="[STAFF] Adiciona um membro específico ao ticket atual")
async def cmd_add_membro(interaction: discord.Interaction, membro: discord.Member):
    if "ticket-" not in interaction.channel.name: 
        return await interaction.response.send_message("❌ Apenas em canais de ticket.", ephemeral=True)
    
    await interaction.channel.set_permissions(membro, read_messages=True, send_messages=True, attach_files=True)
    await interaction.response.send_message(embed=discord.Embed(description=f"✅ O usuário {membro.mention} foi adicionado ao ticket.", color=COR_PRINCIPAL))

@bot.tree.command(name="rem_membro", description="[STAFF] Remove um membro do ticket atual")
async def cmd_rem_membro(interaction: discord.Interaction, membro: discord.Member):
    if "ticket-" not in interaction.channel.name: 
        return await interaction.response.send_message("❌ Apenas em canais de ticket.", ephemeral=True)
        
    await interaction.channel.set_permissions(membro, overwrite=None)
    await interaction.response.send_message(embed=discord.Embed(description=f"✅ O usuário {membro.mention} foi removido do ticket.", color=COR_PRINCIPAL))

# =====================================================================
# SISTEMA DE SORTEIOS ÉPICOS COM REROLL E PERSISTÊNCIA COMPLETA
# =====================================================================
class SorteioModalGenerico(discord.ui.Modal):
    def __init__(self, painel, tipo, titulo):
        super().__init__(title=titulo)
        self.painel = painel
        self.tipo = tipo
        if tipo == "nome": 
            self.campo = discord.ui.TextInput(label="Título do Prêmio", default=painel.config["nome"])
        elif tipo == "desc": 
            self.campo = discord.ui.TextInput(label="Descrição do Sorteio", style=discord.TextStyle.paragraph, default=painel.config["descricao"])
        elif tipo == "vencedores": 
            self.campo = discord.ui.TextInput(label="Quantidade de Vencedores", default=str(painel.config["vencedores"]))
        elif tipo == "duracao": 
            self.campo = discord.ui.TextInput(label="Duração em Minutos", default=str(painel.config["duracao_minutos"]))
        elif tipo == "emoji": 
            self.campo = discord.ui.TextInput(label="Emoji do Botão", default=painel.config["emoji"])
        elif tipo == "img": 
            self.campo = discord.ui.TextInput(label="URL da Imagem Ilustrativa", default=painel.config["imagem"], required=False)
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
        super().__init__(title="Configurar Multiplicador de Entradas")
        self.painel = painel
        self.cargo_id = cargo_id
        self.campo = discord.ui.TextInput(label="Peso de Entradas Extras (Ex: 2, 5, 10)")
        self.add_item(self.campo)

    async def on_submit(self, interaction: discord.Interaction):
        if self.campo.value.isdigit(): 
            self.painel.config["entradas_extras"][str(self.cargo_id)] = int(self.campo.value)
        await interaction.response.edit_message(embed=self.painel.construir_embed(), view=self.painel)

class ParticiparSorteioView(discord.ui.View):
    def __init__(self, msg_id, config):
        super().__init__(timeout=None)
        self.msg_id = str(msg_id)
        self.config = config
        
        btn = discord.ui.Button(
            label="Participar", 
            style=discord.ButtonStyle.danger, 
            emoji=config.get("emoji", "🎉"), 
            custom_id=f"join_sorteio_{msg_id}"
        )
        btn.callback = self.participar_callback
        self.add_item(btn)

    async def participar_callback(self, interaction: discord.Interaction):
        if self.msg_id not in db["sorteios"] or db["sorteios"][self.msg_id]["status"] != "ativo":
            return await interaction.response.send_message("❌ Este sorteio já foi encerrado ou não está mais ativo.", ephemeral=True)

        dados = db["sorteios"][self.msg_id]
        uid = str(interaction.user.id)
        user_roles = [str(r.id) for r in interaction.user.roles]

        if uid in dados["participantes_unicos"]:
            return await interaction.response.send_message("🍀 Você já está participando deste sorteio!", ephemeral=True)

        # Cálculo dinâmico de entradas extras por cargos
        total_entradas = 1
        achou_extras = []
        for cid, qtd in self.config.get("entradas_extras", {}).items():
            if cid in user_roles: 
                achou_extras.append(qtd)
        
        if achou_extras:
            if self.config.get("somar_entradas"): 
                total_entradas += sum(achou_extras)
            else: 
                total_entradas = max(achou_extras)

        dados["participantes_unicos"].append(uid)
        for _ in range(total_entradas): 
            dados["pool_entradas"].append(uid)
        
        salvar_db(db)

        await interaction.response.send_message(
            f"🎉 Sua participação foi confirmada com sucesso!\nVocê acumulou **{total_entradas}x entradas** neste sorteio devido aos seus cargos.", 
            ephemeral=True
        )

class PainelCriacaoSorteioView(discord.ui.View):
    def __init__(self, interaction):
        super().__init__(timeout=None)
        self.aba = "aparencia"
        self.config = {
            "nome": "Sorteio Exclusivo",
            "descricao": "Clique no botão vermelho abaixo para registrar a sua participação e concorrer aos prêmios!",
            "imagem": "", 
            "vencedores": 1, 
            "duracao_minutos": 60, 
            "emoji": "🎉",
            "canal_id": interaction.channel_id,
            "entradas_extras": {}, 
            "somar_entradas": False
        }
        self.montar_interface()

    def construir_embed(self):
        embed = discord.Embed(color=COR_PRINCIPAL)
        if self.aba == "aparencia":
            embed.title = "🎨 Painel de Customização Visual"
            embed.description = f"**Título:** {self.config['nome']}\n**Descrição:** {self.config['descricao']}\n**Emoji:** {self.config['emoji']}\n**Banner/Imagem:** {'Configurado' if self.config['imagem'] else 'Nenhum'}"
        elif self.aba == "geral":
            embed.title = "⚙️ Configurações Gerais do Sorteio"
            embed.description = f"**Vencedores Simultâneos:** {self.config['vencedores']}\n**Duração Total:** {self.config['duracao_minutos']} minutos\n**Canal de Destino:** <#{self.config['canal_id']}>"
        elif self.aba == "extras":
            embed.title = "🎟️ Gerenciamento de Vantagens e Cargos"
            txt = "\n".join([f"<@&{c}>: **{q}x entradas**" for c, q in self.config["entradas_extras"].items()]) if self.config["entradas_extras"] else "Nenhum cargo configurado com peso extra."
            embed.description = f"{txt}\n\n**Modo de Acúmulo:** {'Somar vantagens de múltiplos cargos' if self.config['somar_entradas'] else 'Considerar apenas o cargo de maior peso'}"
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
            btn1 = discord.ui.Button(label="Editar Nome", row=1); btn1.callback = lambda i: i.response.send_modal(SorteioModalGenerico(self, "nome", "Editar Nome"))
            btn2 = discord.ui.Button(label="Editar Descrição", row=1); btn2.callback = lambda i: i.response.send_modal(SorteioModalGenerico(self, "desc", "Editar Descrição"))
            btn3 = discord.ui.Button(label="URL da Imagem", row=1); btn3.callback = lambda i: i.response.send_modal(SorteioModalGenerico(self, "img", "Editar Imagem"))
            self.add_item(btn1); self.add_item(btn2); self.add_item(btn3)
        elif self.aba == "geral":
            btn1 = discord.ui.Button(label="Qtd Vencedores", row=1); btn1.callback = lambda i: i.response.send_modal(SorteioModalGenerico(self, "vencedores", "Vencedores"))
            btn2 = discord.ui.Button(label="Duração (Min)", row=1); btn2.callback = lambda i: i.response.send_modal(SorteioModalGenerico(self, "duracao", "Duração"))
            select_canal = discord.ui.ChannelSelect(channel_types=[discord.ChannelType.text], row=2, placeholder="Selecione o canal de envio...")
            async def cb_canal(i): 
                self.config["canal_id"] = select_canal.values[0].id
                await i.response.edit_message(embed=self.construir_embed(), view=self)
            select_canal.callback = cb_canal
            self.add_item(btn1); self.add_item(btn2); self.add_item(select_canal)
        elif self.aba == "extras":
            select_extra = discord.ui.RoleSelect(row=1, placeholder="Selecione um cargo para dar peso extra...")
            async def cb_ext(i): 
                await i.response.send_modal(SorteioEntradaExtraModal(self, select_extra.values[0].id))
            select_extra.callback = cb_ext
            
            btn_somar = discord.ui.Button(label="Alternar Modo de Soma", style=discord.ButtonStyle.success, row=2)
            async def cb_somar(i): 
                self.config["somar_entradas"] = not self.config["somar_entradas"]
                self.montar_interface()
                await i.response.edit_message(embed=self.construir_embed(), view=self)
            btn_somar.callback = cb_somar
            self.add_item(select_extra); self.add_item(btn_somar)

        btn_iniciar = discord.ui.Button(label="🚀 PUBLICAR SORTEIO AGORA", style=discord.ButtonStyle.success, row=4)
        btn_iniciar.callback = self.publicar_sorteio_callback
        self.add_item(btn_iniciar)

    async def publicar_sorteio_callback(self, interaction: discord.Interaction):
        canal = interaction.guild.get_channel(self.config["canal_id"])
        if not canal:
            return await interaction.response.send_message("❌ Canal de destino inválido ou inacessível.", ephemeral=True)

        termino = discord.utils.utcnow() + datetime.timedelta(minutes=self.config["duracao_minutos"])

        embed = discord.Embed(
            title=f"🎉 {self.config['nome']}", 
            description=f"{self.config['descricao']}\n\nClique no botão vermelho abaixo para registrar sua entrada!", 
            color=COR_PRINCIPAL
        )
        embed.add_field(name="🏆 Vencedores", value=f"`{self.config['vencedores']}`", inline=True)
        embed.add_field(name="⏳ Encerra em", value=f"{discord.utils.format_dt(termino, 'R')}", inline=True)
        if self.config["imagem"]: 
            embed.set_image(url=self.config["imagem"])
        embed.set_footer(text="Sistema Oficial de Sorteios")

        msg = await canal.send(embed=embed)
        view = ParticiparSorteioView(msg.id, self.config)
        await msg.edit(view=view)

        # Salva permanentemente no banco de dados
        db["sorteios"][str(msg.id)] = {
            "guild_id": interaction.guild.id,
            "canal_id": canal.id,
            "status": "ativo",
            "config": self.config,
            "participantes_unicos": [],
            "pool_entradas": [],
            "timestamp_fim": termino.timestamp()
        }
        salvar_db(db)
        
        await interaction.response.edit_message(content="✅ Sorteio configurado e publicado com sucesso no canal escolhido!", embed=None, view=None)
        
        # Agenda a finalização automática em background
        bot.loop.create_task(finalizar_sorteio_background(canal, str(msg.id), self.config["duracao_minutos"]))

async def finalizar_sorteio_background(canal, msg_id, minutos):
    await asyncio.sleep(minutos * 60)
    if msg_id not in db["sorteios"] or db["sorteios"][msg_id]["status"] != "ativo": 
        return
    
    dados = db["sorteios"][msg_id]
    dados["status"] = "encerrado"
    salvar_db(db)

    try: 
        msg = await canal.fetch_message(int(msg_id))
    except: 
        return

    if not dados["pool_entradas"]:
        embed_vazio = discord.Embed(
            title="😔 SORTEIO ENCERRADO - SEM VENCEDORES", 
            description="O sorteio terminou, mas infelizmente nenhum participante entrou a tempo.", 
            color=COR_PRINCIPAL
        )
        return await msg.edit(embed=embed_vazio, view=None)

    vencedores = []
    pool_copia = list(dados["pool_entradas"])
    while len(vencedores) < dados["config"]["vencedores"] and pool_copia:
        escolhido = random.choice(pool_copia)
        if escolhido not in vencedores: 
            vencedores.append(escolhido)

    mentions = ", ".join([f"<@{v}>" for v in vencedores])
    
    e = msg.embeds[0]
    e.title = f"🎊 SORTEIO ENCERRADO: {dados['config']['nome']}"
    e.description = f"**Ganhadores Oficiais Sorteados:**\n{mentions}"
    e.clear_fields()
    
    await msg.edit(embed=e, view=None)
    await canal.send(f"🎉 **PARABÉNS** {mentions}! Vocês foram os vencedores do sorteio **{dados['config']['nome']}**!\n🔗 {msg.jump_url}")

@bot.tree.command(name="sorteio", description="[ADMIN] Abre o painel avançado de criação de sorteios")
@app_commands.default_permissions(administrator=True)
async def cmd_sorteio(interaction: discord.Interaction):
    painel = PainelCriacaoSorteioView(interaction)
    await interaction.response.send_message(embed=painel.construir_embed(), view=painel, ephemeral=True)

@bot.tree.command(name="reroll", description="[ADMIN] Sorteia um novo vencedor para um sorteio anterior através do ID da mensagem")
@app_commands.default_permissions(administrator=True)
async def cmd_reroll(interaction: discord.Interaction, mensagem_id: str):
    if mensagem_id not in db["sorteios"]:
        return await interaction.response.send_message("❌ Sorteio não localizado no banco de dados.", ephemeral=True)
    
    dados = db["sorteios"][mensagem_id]
    pool = dados["pool_entradas"]
    
    if not pool:
        return await interaction.response.send_message("❌ Não há participantes registrados neste sorteio para realizar uma nova roletagem.", ephemeral=True)
        
    novo_vencedor = random.choice(pool)
    canal = interaction.guild.get_channel(dados["canal_id"])
    
    embed = discord.Embed(
        title="🎲 REROLL REALIZADO COM SUCESSO", 
        description=f"O sorteio referente a **{dados['config']['nome']}** foi roletado novamente pela administração.\n\n👑 **Novo Ganhador Sorteado:** <@{novo_vencedor}>", 
        color=COR_PRINCIPAL
    )
    await interaction.response.send_message(embed=embed)
    
    if canal:
        await canal.send(f"🎉 **REROLL DE SORTEIO!** O novo ganhador contemplado é <@{novo_vencedor}>! Parabéns!")

# =====================================================================
# COMANDOS DE MODERAÇÃO E UTILIDADES GERAIS (TUDO EM VERMELHO)
# =====================================================================
@bot.tree.command(name="ban", description="[MOD] Bane um usuário permanentemente do servidor")
@app_commands.default_permissions(ban_members=True)
async def cmd_ban(interaction: discord.Interaction, membro: discord.Member, motivo: str):
    try:
        await membro.ban(reason=motivo)
        await enviar_log_punicao(interaction.guild, membro, interaction.user, "BANIMENTO", motivo)
        await interaction.response.send_message(embed=discord.Embed(description=f"✅ O usuário {membro.mention} foi banido com sucesso.", color=COR_PRINCIPAL))
    except Exception as e:
        await interaction.response.send_message(f"❌ Erro ao banir usuário: {e}", ephemeral=True)

@bot.tree.command(name="kick", description="[MOD] Expulsa um usuário do servidor")
@app_commands.default_permissions(kick_members=True)
async def cmd_kick(interaction: discord.Interaction, membro: discord.Member, motivo: str):
    try:
        await membro.kick(reason=motivo)
        await enviar_log_punicao(interaction.guild, membro, interaction.user, "EXPULSÃO", motivo)
        await interaction.response.send_message(embed=discord.Embed(description=f"✅ O usuário {membro.mention} foi expulso com sucesso.", color=COR_PRINCIPAL))
    except Exception as e:
        await interaction.response.send_message(f"❌ Erro ao expulsar usuário: {e}", ephemeral=True)

@bot.tree.command(name="mute", description="[MOD] Aplica castigo (timeout) em um usuário")
@app_commands.default_permissions(moderate_members=True)
async def cmd_mute(interaction: discord.Interaction, membro: discord.Member, minutos: int, motivo: str):
    try:
        delta = datetime.timedelta(minutes=minutos)
        await membro.timeout(delta, reason=motivo)
        await enviar_log_punicao(interaction.guild, membro, interaction.user, f"CASTIGO ({minutos}m)", motivo)
        await interaction.response.send_message(embed=discord.Embed(description=f"✅ O usuário {membro.mention} foi silenciado por {minutos} minutos.", color=COR_PRINCIPAL))
    except Exception as e:
        await interaction.response.send_message(f"❌ Erro ao mutar usuário: {e}", ephemeral=True)

@bot.tree.command(name="unmute", description="[MOD] Remove o castigo de um usuário")
@app_commands.default_permissions(moderate_members=True)
async def cmd_unmute(interaction: discord.Interaction, membro: discord.Member):
    try:
        await membro.timeout(None)
        await interaction.response.send_message(embed=discord.Embed(description=f"✅ O castigo de {membro.mention} foi removido.", color=COR_PRINCIPAL))
    except Exception as e:
        await interaction.response.send_message(f"❌ Erro ao desmutar: {e}", ephemeral=True)

@bot.tree.command(name="clear", description="[MOD] Limpa um número específico de mensagens do chat")
@app_commands.default_permissions(manage_messages=True)
async def cmd_clear(interaction: discord.Interaction, quantidade: int):
    await interaction.response.defer(ephemeral=True)
    apagadas = await interaction.channel.purge(limit=quantidade)
    await interaction.followup.send(embed=discord.Embed(description=f"✅ `{len(apagadas)}` mensagens foram apagadas com sucesso.", color=COR_PRINCIPAL), ephemeral=True)

@bot.tree.command(name="lock", description="[ADMIN] Tranca o canal atual impedindo envio de mensagens")
@app_commands.default_permissions(manage_channels=True)
async def cmd_lock(interaction: discord.Interaction):
    await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=False)
    await interaction.response.send_message(embed=discord.Embed(title="🔒 CANAL TRANCADO", description="Este canal foi bloqueado para membros pela moderação.", color=COR_PRINCIPAL))

@bot.tree.command(name="unlock", description="[ADMIN] Destranca o canal atual liberando o chat")
@app_commands.default_permissions(manage_channels=True)
async def cmd_unlock(interaction: discord.Interaction):
    await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=True)
    await interaction.response.send_message(embed=discord.Embed(title="🔓 CANAL DESTRANCADO", description="Este canal foi liberado para conversação.", color=COR_PRINCIPAL))

@bot.tree.command(name="aviso", description="[ADMIN] Cria um aviso oficial formatado em embed vermelho")
@app_commands.default_permissions(administrator=True)
async def cmd_aviso(interaction: discord.Interaction, titulo: str, mensagem: str):
    embed = discord.Embed(title=f"📢 {titulo}", description=mensagem, color=COR_PRINCIPAL)
    embed.set_footer(text=f"Aviso oficial emitido por {interaction.user.name}")
    await interaction.channel.send(embed=embed)
    await interaction.response.send_message("✅ Aviso publicado com sucesso!", ephemeral=True)

# =====================================================================
# INICIALIZAÇÃO DO BOT
# =====================================================================
@bot.event
async def on_ready():
    print("=" * 60)
    print(f"🤖 BOT OPERANDO COM SUCESSO: {bot.user.name}")
    print(f"🆔 ID da Aplicação: {bot.user.id}")
    print(f"🛡️ Hashes Letais Carregados: {len(db['hashes_proibidos'])}")
    print(f"🎉 Sorteios Ativos Restaurados: {len(db['sorteios'])}")
    print("=" * 60)

if __name__ == "__main__":
    TOKEN = os.getenv("TOKEN")
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("❌ ERRO CRÍTICO: Token do bot não configurado nas variáveis de ambiente da Render!")
