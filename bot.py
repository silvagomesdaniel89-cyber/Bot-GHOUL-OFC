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
    """
    Carrega o banco de dados JSON persistente.
    Caso o arquivo não exista ou esteja corrompido, inicializa um dicionário limpo.
    """
    if not os.path.exists(DB_FILE):
        print("[DATABASE] Arquivo database.json não encontrado. Criando nova base estruturada.")
        return {
            "hashes_proibidos": [], 
            "sorteios": {}, 
            "config_servidores": {},
            "advertencias": {}
        }
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            print("[DATABASE] Banco de dados carregado com sucesso.")
            return json.load(f)
    except Exception as e:
        print(f"[DATABASE ERROR] Erro crítico ao ler o JSON: {e}. Restaurando padrão seguro.")
        return {
            "hashes_proibidos": [], 
            "sorteios": {}, 
            "config_servidores": {},
            "advertencias": {}
        }

def salvar_db(data):
    """
    Salva os dados atuais de forma segura no arquivo JSON para evitar perdas em reboots.
    """
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"[DATABASE ERROR] Falha ao salvar dados no disco: {e}")

# Instancia o banco de dados na inicialização
db = carregar_db()

# =====================================================================
# SERVIDOR WEB KEEP-ALIVE PARA RENDER
# =====================================================================
app = Flask(__name__)

@app.route("/")
def home():
    """
    Endpoint HTTP mantido ativo para impedir que a Render adormeça o bot.
    """
    return "GHOUL SECURITY - Sistema de Segurança Avançada & Gestão Ativo 24/7."

def run_server():
    """
    Executa o servidor Flask em uma thread paralela em background.
    """
    try:
        port = int(os.environ.get("PORT", 8080))
        app.run(host="0.0.0.0", port=port)
    except Exception as e:
        print(f"[FLASK ERROR] Erro ao iniciar servidor web local: {e}")

Thread(target=run_server, daemon=True).start()

# =====================================================================
# CONFIGURAÇÕES GLOBAIS E ESTÉTICA VERMELHA TOTAL (0xFF0000)
# =====================================================================
COR_PRINCIPAL = 0xFF0000  # Vermelho Puro Absoluto para toda a interface

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
    """
    Gerenciador principal de eventos do bot, reconexões, sincronização de comandos
    Slash e restauração de views persistentes em memória.
    """
    def __init__(self):
        super().__init__(
            command_prefix="!", 
            intents=discord.Intents.all(), 
            help_command=None
        )

    async def setup_hook(self):
        print("[SETUP] Inicializando views persistentes...")
        
        # Reconecta os botões do sistema de tickets
        self.add_view(TicketPainelView())
        self.add_view(TicketAcoesView())
        
        # Reconecta os botões de sorteios ativos salvos em JSON
        restaurados = 0
        for msg_id, dados in list(db["sorteios"].items()):
            if dados.get("status") == "ativo":
                self.add_view(ParticiparSorteioView(msg_id, dados["config"]))
                restaurados += 1
                
        print(f"[SETUP] {restaurados} sorteios ativos re-anexados com sucesso.")
                
        try:
            synced = await self.tree.sync()
            print(f"[SYNC] {len(synced)} comandos Slash sincronizados com sucesso.")
        except Exception as e:
            print(f"[SYNC ERROR] Falha ao sincronizar comandos: {e}")

bot = BotSupremoUltimate()

def obter_config(guild_id): 
    """
    Retorna as configurações do servidor correspondente ou um modelo vazio seguro.
    """
    return CONFIG_SERVIDORES.get(guild_id, {
        "nome": "Servidor Desconhecido",
        "canal_logs": None,
        "canal_punicoes": None,
        "categoria_tickets": None,
        "cargo_staff": None
    })

# =====================================================================
# SISTEMA DE LOGS DE PUNIÇÕES COM CONSOLE DEBUG
# =====================================================================
async def enviar_log_punicao(guild, user, staff, acao, motivo, prova_bytes=None):
    """
    Envia logs detalhados para o canal de punições com rastreamento no console.
    """
    config = obter_config(guild.id)
    canal_id_config = config.get("canal_punicoes")
    
    print(f"[LOG DEBUG] Tentando disparar log para Guild: {guild.name} (ID: {guild.id})")
    print(f"[LOG DEBUG] Canal de punições configurado no dicionário: {canal_id_config}")

    if not canal_id_config: 
        print(f"[LOGS ERRO] O ID do canal de punições NÃO está definido no dicionário para este servidor!")
        return
        
    canal = guild.get_channel(canal_id_config)
    if not canal: 
        print(f"[LOGS ERRO] O canal com ID {canal_id_config} não foi encontrado pelo bot! Verifique se o ID está correto e o bot está no servidor.")
        return

    embed = discord.Embed(
        title=f"🚨 REGISTRO DE SEGURANÇA | {acao}", 
        color=COR_PRINCIPAL, 
        timestamp=discord.utils.utcnow()
    )
    
    if hasattr(user, "display_avatar") and user.display_avatar:
        embed.set_thumbnail(url=user.display_avatar.url)
    
    embed.add_field(name="👤 Alvo da Ação", value=f"{user.mention}\n(`{user.id}`)", inline=True)
    
    staff_name = staff.mention if hasattr(staff, 'mention') else str(staff)
    embed.add_field(name="🛡️ Responsável", value=f"{staff_name}", inline=True)
    
    embed.add_field(name="📄 Descrição / Motivo", value=f"```ini\n[ {motivo} ]\n```", inline=False)
    
    avatar_url = bot.user.display_avatar.url if bot.user.display_avatar else None
    embed.set_footer(text=f"GHOUL SECURITY • {guild.name}", icon_url=avatar_url)
    
    try:
        if prova_bytes:
            file = discord.File(BytesIO(prova_bytes), filename="evidencia_automod.png")
            embed.set_image(url="attachment://evidencia_automod.png")
            await canal.send(embed=embed, file=file)
        else:
            await canal.send(embed=embed)
        print(f"[LOGS SUCESSO] Log enviado perfeitamente para o canal #{canal.name}!")
    except Exception as e:
        print(f"[LOGS ERRO CRÍTICO] Falha ao enviar mensagem no canal de logs: {e}")

@bot.event
async def on_member_ban(guild, user):
    await asyncio.sleep(1.5)
    try:
        async for entry in guild.audit_logs(limit=2, action=discord.AuditLogAction.ban):
            if entry.target.id == user.id:
                if entry.user.id == bot.user.id: 
                    return 
                motivo = entry.reason if entry.reason else "Nenhum motivo especificado."
                await enviar_log_punicao(guild, user, entry.user, "BANIMENTO MANUAL", motivo)
                break
    except Exception as e:
        print(f"[EVENT BAN ERROR] {e}")

@bot.event
async def on_member_remove(member):
    await asyncio.sleep(1.5)
    try:
        async for entry in member.guild.audit_logs(limit=2, action=discord.AuditLogAction.kick):
            if entry.target.id == member.id:
                if entry.user.id == bot.user.id: 
                    return
                motivo = entry.reason if entry.reason else "Nenhum motivo especificado."
                await enviar_log_punicao(member.guild, member, entry.user, "EXPULSÃO MANUAL", motivo)
                break
    except Exception as e:
        print(f"[EVENT KICK ERROR] {e}")

# =====================================================================
# AUTOMOD TOTAL (APAGA DE TODOS: MEMBROS, MODS E DONOS)
# =====================================================================
@bot.tree.command(name="bloquear_imagem", description="[ADMIN] Adiciona uma imagem na Blacklist letal.")
@app_commands.default_permissions(administrator=True)
async def bloquear_imagem(interaction: discord.Interaction, imagem: discord.Attachment):
    if not imagem.content_type or not imagem.content_type.startswith("image/"):
        return await interaction.response.send_message("❌ O arquivo precisa ser uma imagem válida.", ephemeral=True)
    
    await interaction.response.defer(ephemeral=True)
    try:
        data = await imagem.read()
        img = Image.open(BytesIO(data)).convert("RGB")
        h = str(imagehash.average_hash(img))
        
        if h not in db["hashes_proibidos"]:
            db["hashes_proibidos"].append(h)
            salvar_db(db)
            
        embed = discord.Embed(
            title="⛔ IMAGEM REGISTRADA NA BLACKLIST", 
            description=f"A imagem foi computada com sucesso.\nQualquer pessoa (membro ou dono) que tentar postar terá a mensagem apagada instantaneamente.\n\n**Hash Gerado:** `{h}`", 
            color=COR_PRINCIPAL
        )
        embed.set_footer(text="GHOUL SECURITY", icon_url=bot.user.display_avatar.url if bot.user.display_avatar else None)
        await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Erro ao computar hash da imagem: {e}", ephemeral=True)

@bot.event
async def on_message(message):
    """
    Filtro Automod Universal. 
    Intercepta mensagens de QUALQUER usuário (incluindo o Dono do Servidor).
    Apaga o conteúdo proibido e registra logs.
    """
    if message.author.bot or not message.guild: 
        return

    # =================================================================
    # 1. VERIFICAÇÃO DE IMAGENS PROIBIDAS (APAGA DE TODOS, BANE SE NÃO FOR DONO)
    # =================================================================
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
                            
                            # AÇÃO 1: APAGA A MENSAGEM SEMPRE (Mesmo se for o dono ou admin)
                            try: 
                                await message.delete()
                                print(f"[AUTOMOD] Mensagem com imagem proibida de {message.author} foi apagada com sucesso.")
                            except Exception as e:
                                print(f"[AUTOMOD ERRO] Não consegui apagar a imagem: {e}")

                            # Verifica se o autor é o Dono supremo do servidor
                            is_dono = (message.author.id == message.guild.owner_id)
                            
                            if not is_dono:
                                # Se não for o dono, aplica o banimento normal
                                try:
                                    await message.author.send(embed=discord.Embed(
                                        title="🚨 BANIMENTO AUTOMÁTICO", 
                                        description=f"Você foi banido de **{message.guild.name}** por postar conteúdo visual estritamente proibido.", 
                                        color=COR_PRINCIPAL
                                    ))
                                except: pass

                                try:
                                    await message.guild.ban(message.author, reason="AutoMod Letal: Envio de imagem proibida.")
                                except Exception as e:
                                    print(f"[AUTOMOD ERRO] Falha ao banir membro: {e}")
                            else:
                                print(f"[AUTOMOD AVISO] O autor é o DONO do servidor ({message.author}). A imagem foi apagada com sucesso, mas o banimento foi ignorado por segurança da API.")

                            # AÇÃO 2: DISPARA O LOG DE PUNIÇÃO IMEDIATAMENTE
                            await enviar_log_punicao(
                                message.guild, 
                                message.author, 
                                bot.user, 
                                "INTERCEPTAÇÃO DE IMAGEM PROIBIDA", 
                                f"Mensagem com imagem restrita apagada de {message.author} (`{message.author.id}`).", 
                                prova_bytes=img_bytes
                            )
                            return
                except Exception as e:
                    print(f"[AUTOMOD ERROR] Falha no processamento de hash da imagem: {e}")

    # =================================================================
    # 2. FILTRO ANTI-DIVULGAÇÃO DE LINKS (APAGA DE TODOS)
    # =================================================================
    texto_inf = message.content.lower()
    if "discord.gg/" in texto_inf or "discord.com/invite/" in texto_inf:
        try:
            await message.delete()
            print(f"[AUTOMOD] Link de convite postado por {message.author} foi apagado.")
            
            aviso = await message.channel.send(embed=discord.Embed(
                description=f"⚠️ {message.author.mention}, a divulgação de links de convite é proibida!", 
                color=COR_PRINCIPAL
            ))
            await aviso.delete(delay=5)
            
            await enviar_log_punicao(
                message.guild, 
                message.author, 
                bot.user, 
                "DIVULGAÇÃO BLOQUEADA", 
                f"Link de convite apagado no canal {message.channel.mention}."
            )
            return
        except Exception as e:
            print(f"[AUTOMOD ERRO] Falha ao filtrar link: {e}")

    # =================================================================
    # 3. FILTRO MASSIVO DE PALAVRÕES (APAGA DE TODOS)
    # =================================================================
    palavroes = [
        "fdp", "fdps", "vsf", "vtnc", "pnc", "tnc", "pqp", "krl", "crrl", "kralho", 
        "caralho", "porra", "merda", "bosta", "buceta", "puta", "cu", "cuzao", 
        "cuzão", "pau", "piroca", "foder", "fodeu", "fodido", "cacete", "chupa", 
        "punheta", "viado", "arrombado", "desgraçado", "corno", "vagabundo", 
        "otario", "imbecil", "idiota", "retardado", "escroto", "safado", "desgraça"
    ]
    
    texto_verificacao = re.sub(r"[^a-z0-9\s]", "", message.content.lower())
    palavras_msg = texto_verificacao.split()
    
    for p in palavroes:
        if p in palavras_msg or any(p in w for w in palavras_msg):
            try: 
                await message.delete()
                print(f"[AUTOMOD] Palavrão interceptado e apagado de {message.author}.")
            except: 
                pass
            
            embed_palavra = discord.Embed(
                description=f"⚠️ {message.author.mention}, Cuidado com seu linguajar seu BOBOCA!", 
                color=COR_PRINCIPAL
            )
            embed_palavra.set_footer(text="GHOUL SECURITY", icon_url=bot.user.display_avatar.url if bot.user.display_avatar else None)
            
            try:
                msg_alerta = await message.channel.send(embed=embed_palavra)
                await msg_alerta.delete(delay=5)
            except: 
                pass
                
            await enviar_log_punicao(
                message.guild, 
                message.author, 
                bot.user, 
                "PALAVRÃO INTERCEPTADO", 
                f"Termo inadequado apagado no canal {message.channel.mention}."
            )
            return

    # Processa os comandos de barra ou prefixo normalmente para todos
    await bot.process_commands(message)

# =====================================================================
# SISTEMA DE TICKETS PROFISSIONAL (BOTÕES LADO A LADO)
# =====================================================================
class TicketAcoesView(discord.ui.View):
    """
    View acoplada no canal privado do ticket contendo os botões 
    'Fechar Ticket' e 'Reivindicar Ticket' lado a lado na mesma linha (row=0).
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
        embed = discord.Embed(
            title="🔒 ENCERRANDO TICKET", 
            description=f"Solicitado por {interaction.user.mention}. O canal será apagado em **5 segundos**...", 
            color=COR_PRINCIPAL
        )
        embed.set_footer(text="GHOUL SECURITY", icon_url=bot.user.display_avatar.url if bot.user.display_avatar else None)
        await interaction.response.send_message(embed=embed)
        await asyncio.sleep(5)
        try: 
            await interaction.channel.delete(reason=f"Ticket fechado por {interaction.user}")
        except Exception as e: 
            print(f"[TICKET ERROR] Falha ao deletar canal: {e}")

    @discord.ui.button(
        label="Reivindicar Ticket", 
        style=discord.ButtonStyle.primary, 
        emoji="✋", 
        custom_id="reivindicar_ticket_btn_persisted", 
        row=0
    )
    async def reivindicar_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="✋ ATENDIMENTO ASSUMIDO", 
            description=f"O staff {interaction.user.mention} reivindicou este atendimento e assumiu a responsabilidade exclusiva.", 
            color=COR_PRINCIPAL
        )
        embed.set_footer(text="GHOUL SECURITY", icon_url=bot.user.display_avatar.url if bot.user.display_avatar else None)
        await interaction.response.send_message(embed=embed)

class TicketSelectDropdown(discord.ui.Select):
    """
    Menu suspenso com os departamentos do ticket.
    """
    def __init__(self):
        options = [
            discord.SelectOption(label="Suporte Geral", description="Dúvidas e orientações gerais", emoji="💬", value="suporte"),
            discord.SelectOption(label="Denúncias", description="Reportar infrações no servidor", emoji="🚨", value="denuncia"),
            discord.SelectOption(label="Financeiro / Lojas", description="Pagamentos, cash e produtos", emoji="🛒", value="compras"),
            discord.SelectOption(label="Parcerias", description="Propostas comerciais oficiais", emoji="🤝", value="parceria")
        ]
        super().__init__(
            placeholder="📂 Clique aqui para escolher o departamento desejado...", 
            options=options, 
            custom_id="ticket_dropdown_main"
        )

    async def callback(self, interaction: discord.Interaction):
        config = obter_config(interaction.guild.id)
        if not config or not config.get("categoria_tickets"):
            return await interaction.response.send_message("❌ A categoria de tickets não foi configurada para este servidor.", ephemeral=True)

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
            canal = await interaction.guild.create_text_channel(
                name=nome_canal, 
                category=categoria, 
                overwrites=overwrites
            )
        except Exception as e:
            return await interaction.response.send_message(f"❌ Erro ao criar o canal privado: {e}", ephemeral=True)

        embed_ticket = discord.Embed(
            title="🎫 PAINEL DE ATENDIMENTO PRIVADO", 
            description=f"Olá {interaction.user.mention}!\n\nDepartamento selecionado: **`{self.values[0].upper()}`**.\nPor favor, descreva detalhadamente sua solicitação.", 
            color=COR_PRINCIPAL
        )
        embed_ticket.set_footer(text=f"GHOUL SECURITY • User ID: {interaction.user.id}", icon_url=bot.user.display_avatar.url if bot.user.display_avatar else None)

        marcacacao = f"{interaction.user.mention} {cargo_staff.mention if cargo_staff else ''}"
        await canal.send(content=marcacacao, embed=embed_ticket, view=TicketAcoesView())
        await interaction.response.send_message(f"✅ Seu ticket foi aberto com privacidade: {canal.mention}", ephemeral=True)

class TicketPainelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelectDropdown())

@bot.tree.command(name="painel_tickets", description="[ADMIN] Envia o painel interativo definitivo de criação de tickets")
@app_commands.default_permissions(administrator=True)
async def painel_tickets(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎫 CENTRAL DE ATENDIMENTO E SUPORTE", 
        description="Precisa de ajuda ou quer fazer uma denúncia?\nSelecione o assunto correspondente no menu suspenso abaixo para abrir um canal de atendimento privado.", 
        color=COR_PRINCIPAL
    )
    banner = IMAGENS_TICKETS.get(interaction.guild_id)
    if banner: 
        embed.set_image(url=banner)
    embed.set_footer(text="GHOUL SECURITY", icon_url=bot.user.display_avatar.url if bot.user.display_avatar else None)
    
    await interaction.channel.send(embed=embed, view=TicketPainelView())
    await interaction.response.send_message("✅ Painel de tickets gerado com sucesso!", ephemeral=True)

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
    embed = discord.Embed(title="✋ REIVINDICADO", description=f"{interaction.user.mention} assumiu o atendimento.", color=COR_PRINCIPAL)
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
# SISTEMA DE SORTEIOS COMPLETO (COM MODAIS E MULTIPLICADORES)
# =====================================================================
class SorteioModalGenerico(discord.ui.Modal):
    def __init__(self, painel, tipo, titulo):
        super().__init__(title=titulo)
        self.painel = painel
        self.tipo = tipo
        if tipo == "nome": self.campo = discord.ui.TextInput(label="Título do Prêmio", default=painel.config["nome"])
        elif tipo == "desc": self.campo = discord.ui.TextInput(label="Descrição", style=discord.TextStyle.paragraph, default=painel.config["descricao"])
        elif tipo == "vencedores": self.campo = discord.ui.TextInput(label="Qtd Vencedores", default=str(painel.config["vencedores"]))
        elif tipo == "duracao": self.campo = discord.ui.TextInput(label="Duração em Minutos", default=str(painel.config["duracao_minutos"]))
        elif tipo == "emoji": self.campo = discord.ui.TextInput(label="Emoji", default=painel.config["emoji"])
        elif tipo == "img": self.campo = discord.ui.TextInput(label="URL Imagem", default=painel.config["imagem"], required=False)
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
        super().__init__(title="Multiplicador de Vantagem")
        self.painel = painel; self.cargo_id = cargo_id
        self.campo = discord.ui.TextInput(label="Peso (Ex: 2, 5, 10)")
        self.add_item(self.campo)

    async def on_submit(self, interaction: discord.Interaction):
        if self.campo.value.isdigit(): 
            self.painel.config["entradas_extras"][str(self.cargo_id)] = int(self.campo.value)
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
        await interaction.response.send_message(f"🎉 Inscrição confirmada! Entradas: **{total_entradas}x**", ephemeral=True)

class PainelCriacaoSorteioView(discord.ui.View):
    def __init__(self, interaction):
        super().__init__(timeout=None)
        self.aba = "aparencia"
        self.config = {
            "nome": "Sorteio VIP", "descricao": "Clique para concorrer!", "imagem": "", 
            "vencedores": 1, "duracao_minutos": 60, "emoji": "🎉",
            "canal_id": interaction.channel_id, "entradas_extras": {}, "somar_entradas": False
        }
        self.montar_interface()

    def construir_embed(self):
        embed = discord.Embed(color=COR_PRINCIPAL)
        if self.aba == "aparencia": embed.title = "🎨 Aparência"; embed.description = f"Título: {self.config['nome']}"
        elif self.aba == "geral": embed.title = "⚙️ Geral"; embed.description = f"Vencedores: {self.config['vencedores']} | Duração: {self.config['duracao_minutos']}m"
        elif self.aba == "extras": embed.title = "🎟️ Vantagens"; embed.description = "Configurar pesos por cargo"
        embed.set_footer(text="GHOUL SECURITY", icon_url=bot.user.display_avatar.url if bot.user.display_avatar else None)
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
            self.add_item(select_extra)

        btn_iniciar = discord.ui.Button(label="🚀 PUBLICAR SORTEIO", style=discord.ButtonStyle.success, row=4)
        btn_iniciar.callback = self.publicar
        self.add_item(btn_iniciar)

    async def publicar(self, interaction: discord.Interaction):
        canal = interaction.guild.get_channel(self.config["canal_id"])
        if not canal: return await interaction.response.send_message("❌ Canal inválido.", ephemeral=True)
        
        termino = discord.utils.utcnow() + datetime.timedelta(minutes=self.config["duracao_minutos"])
        embed = discord.Embed(title=f"🎉 {self.config['nome']}", description=f"{self.config['descricao']}\n\nClique abaixo!", color=COR_PRINCIPAL)
        embed.add_field(name="🏆 Vencedores", value=f"`{self.config['vencedores']}`", inline=True)
        embed.add_field(name="⏳ Termina", value=f"{discord.utils.format_dt(termino, 'R')}", inline=True)
        if self.config["imagem"]: embed.set_image(url=self.config["imagem"])
        embed.set_footer(text="GHOUL SECURITY", icon_url=bot.user.display_avatar.url if bot.user.display_avatar else None)

        msg = await canal.send(embed=embed)
        await msg.edit(view=ParticiparSorteioView(msg.id, self.config))
        db["sorteios"][str(msg.id)] = {"canal_id": canal.id, "status": "ativo", "config": self.config, "participantes_unicos": [], "pool_entradas": []}
        salvar_db(db)
        await interaction.response.edit_message(content="✅ Sorteio publicado com sucesso!", embed=None, view=None)
        bot.loop.create_task(finalizar_sorteio(canal, str(msg.id), self.config["duracao_minutos"]))

async def finalizar_sorteio(canal, msg_id, minutos):
    await asyncio.sleep(minutos * 60)
    if msg_id not in db["sorteios"] or db["sorteios"][msg_id]["status"] != "ativo": return
    dados = db["sorteios"][msg_id]; dados["status"] = "encerrado"; salvar_db(db)
    try: msg = await canal.fetch_message(int(msg_id))
    except: return

    if not dados["pool_entradas"]:
        embed = discord.Embed(title="😔 SORTEIO ENCERRADO", description="Sem participantes.", color=COR_PRINCIPAL)
        embed.set_footer(text="GHOUL SECURITY", icon_url=bot.user.display_avatar.url if bot.user.display_avatar else None)
        return await msg.edit(embed=embed, view=None)

    vencedores = []
    pool = list(dados["pool_entradas"])
    while len(vencedores) < dados["config"]["vencedores"] and pool:
        escolhido = random.choice(pool)
        if escolhido not in vencedores: vencedores.append(escolhido)
        pool = [p for p in pool if p != escolhido]

    mentions = ", ".join([f"<@{v}>" for v in vencedores])
    e = msg.embeds[0]
    e.title = f"🎊 ENCERRADO: {dados['config']['nome']}"
    e.description = f"**Ganhadores:** {mentions}"
    e.clear_fields()
    await msg.edit(embed=e, view=None)
    await canal.send(f"🎉 **PARABÉNS** {mentions}! Vocês venceram **{dados['config']['nome']}**!\n🔗 {msg.jump_url}")

@bot.tree.command(name="sorteio", description="[ADMIN] Painel de sorteios")
@app_commands.default_permissions(administrator=True)
async def cmd_sorteio(interaction: discord.Interaction):
    p = PainelCriacaoSorteioView(interaction)
    await interaction.response.send_message(embed=p.construir_embed(), view=p, ephemeral=True)

@bot.tree.command(name="reroll", description="[ADMIN] Sorteia novo ganhador")
@app_commands.default_permissions(administrator=True)
async def cmd_reroll(interaction: discord.Interaction, mensagem_id: str):
    if mensagem_id not in db["sorteios"] or not db["sorteios"][mensagem_id]["pool_entradas"]:
        return await interaction.response.send_message("❌ Sorteio inválido.", ephemeral=True)
    novo = random.choice(db["sorteios"][mensagem_id]["pool_entradas"])
    canal = interaction.guild.get_channel(db["sorteios"][mensagem_id]["canal_id"])
    embed = discord.Embed(title="🎲 REROLL", description=f"Novo ganhador: <@{novo}>", color=COR_PRINCIPAL)
    embed.set_footer(text="GHOUL SECURITY", icon_url=bot.user.display_avatar.url if bot.user.display_avatar else None)
    await interaction.response.send_message(embed=embed)
    if canal: await canal.send(f"🎉 **REROLL!** O novo ganhador é <@{novo}>!")

# =====================================================================
# COMANDOS DE MODERAÇÃO
# =====================================================================
@bot.tree.command(name="ban", description="[MOD] Bane um usuário")
@app_commands.default_permissions(ban_members=True)
async def cmd_ban(interaction: discord.Interaction, membro: discord.Member, motivo: str):
    await membro.ban(reason=motivo)
    await enviar_log_punicao(interaction.guild, membro, interaction.user, "BANIMENTO", motivo)
    await interaction.response.send_message(f"✅ {membro.mention} banido.", ephemeral=True)

@bot.tree.command(name="kick", description="[MOD] Expulsa um usuário")
@app_commands.default_permissions(kick_members=True)
async def cmd_kick(interaction: discord.Interaction, membro: discord.Member, motivo: str):
    await membro.kick(reason=motivo)
    await enviar_log_punicao(interaction.guild, membro, interaction.user, "EXPULSÃO", motivo)
    await interaction.response.send_message(f"✅ {membro.mention} expulso.", ephemeral=True)

@bot.tree.command(name="mute", description="[MOD] Silencia usuário (timeout)")
@app_commands.default_permissions(moderate_members=True)
async def cmd_mute(interaction: discord.Interaction, membro: discord.Member, minutos: int, motivo: str):
    await membro.timeout(datetime.timedelta(minutes=minutos), reason=motivo)
    await enviar_log_punicao(interaction.guild, membro, interaction.user, f"CASTIGO ({minutos}m)", motivo)
    await interaction.response.send_message(f"✅ {membro.mention} mutado.", ephemeral=True)

@bot.tree.command(name="clear", description="[MOD] Limpa mensagens")
@app_commands.default_permissions(manage_messages=True)
async def cmd_clear(interaction: discord.Interaction, quantidade: int):
    await interaction.response.defer(ephemeral=True)
    apagadas = await interaction.channel.purge(limit=quantidade)
    await interaction.followup.send(f"✅ `{len(apagadas)}` mensagens apagadas.", ephemeral=True)

@bot.tree.command(name="aviso", description="[ADMIN] Envia aviso oficial")
@app_commands.default_permissions(administrator=True)
async def cmd_aviso(interaction: discord.Interaction, titulo: str, mensagem: str):
    embed = discord.Embed(title=f"📢 {titulo}", description=mensagem, color=COR_PRINCIPAL)
    embed.set_footer(text="GHOUL SECURITY", icon_url=bot.user.display_avatar.url if bot.user.display_avatar else None)
    await interaction.channel.send(embed=embed)
    await interaction.response.send_message("✅ Enviado!", ephemeral=True)

# =====================================================================
# INICIALIZAÇÃO
# =====================================================================
@bot.event
async def on_ready():
    print("=" * 60)
    print(f"🤖 GHOUL SECURITY ONLINE: {bot.user.name}")
    print(f"🛡️ AutoMod Universal Ativo (Apaga de todos, bane membros).")
    print("=" * 60)

if __name__ == "__main__":
    TOKEN = os.getenv("TOKEN")
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("❌ ERRO: Token não configurado!")
