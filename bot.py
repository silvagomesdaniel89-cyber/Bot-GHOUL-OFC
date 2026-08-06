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
# Variável global para o nome do arquivo de banco de dados
DB_FILE = "database.json"

def carregar_db():
    """
    Carrega o banco de dados JSON.
    Se o arquivo não existir ou estiver corrompido, cria uma estrutura do zero
    para evitar que o bot crashe na inicialização.
    """
    if not os.path.exists(DB_FILE):
        print("[DATABASE] Arquivo não encontrado. Criando um novo banco de dados limpo.")
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
        print(f"[DATABASE ERROR] Erro ao ler o arquivo JSON: {e}. Restaurando padrão.")
        return {
            "hashes_proibidos": [], 
            "sorteios": {}, 
            "config_servidores": {},
            "advertencias": {}
        }

def salvar_db(data):
    """
    Salva as informações atuais da memória de volta para o arquivo JSON.
    Garante que as punições, imagens e sorteios não sejam perdidos.
    """
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"[DATABASE ERROR] Falha crítica ao salvar o arquivo: {e}")

# Inicializa o banco de dados logo na abertura do script
db = carregar_db()

# =====================================================================
# SERVIDOR WEB KEEP-ALIVE PARA RENDER
# =====================================================================
app = Flask(__name__)

@app.route("/")
def home():
    """
    Rota principal do Flask. 
    Usada por serviços como UptimeRobot para manter o bot 24/7 na Render.
    """
    return "GHOUL SECURITY - Sistema de Segurança Máxima e Gestão Operacional Ativo 24/7."

def run_server():
    """
    Inicia o servidor Flask em uma porta designada pela Render.
    """
    try:
        port = int(os.environ.get("PORT", 8080))
        app.run(host="0.0.0.0", port=port)
    except Exception as e:
        print(f"[FLASK ERROR] Erro ao iniciar o servidor Web: {e}")

# Inicia a thread do servidor em background
Thread(target=run_server, daemon=True).start()

# =====================================================================
# CONFIGURAÇÕES GLOBAIS E ESTÉTICA VERMELHA TOTAL (0xFF0000)
# =====================================================================
COR_PRINCIPAL = 0xFF0000  # Vermelho Puro Absoluto para TUDO

# Dicionário robusto de configuração para multi-servidores
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

# Separação explícita de banners por Guild ID
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
    Classe base do bot. Gerencia a inicialização, sync de comandos de barra,
    e a restauração de views persistentes (Tickets e Sorteios) para que 
    não parem de funcionar caso o bot reinicie.
    """
    def __init__(self):
        super().__init__(
            command_prefix="!", 
            intents=discord.Intents.all(), 
            help_command=None
        )

    async def setup_hook(self):
        print("[SETUP] Iniciando restauração de Views persistentes...")
        
        # Registra os botões e selects dos tickets permanentemente
        self.add_view(TicketPainelView())
        self.add_view(TicketAcoesView())
        print("[SETUP] Views de Tickets restauradas com sucesso.")
        
        # Varre o banco de dados atrás de sorteios ativos para reconectar os botões
        sorteios_restaurados = 0
        for msg_id, dados in list(db["sorteios"].items()):
            if dados.get("status") == "ativo":
                self.add_view(ParticiparSorteioView(msg_id, dados["config"]))
                sorteios_restaurados += 1
                
        print(f"[SETUP] {sorteios_restaurados} Sorteios ativos restaurados com sucesso.")
                
        # Sincroniza a árvore de comandos Slash (/) com o Discord
        try:
            print("[SYNC] Sincronizando comandos de barra...")
            synced = await self.tree.sync()
            print(f"[SYNC] Sucesso! {len(synced)} comandos registrados globalmente.")
        except Exception as e:
            print(f"[SYNC ERROR] Ocorreu um erro severo ao sincronizar os comandos: {e}")

# Instância global do bot
bot = BotSupremoUltimate()

def obter_config(guild_id): 
    """
    Função auxiliar de segurança. Retorna as configurações do servidor.
    Se o servidor não estiver cadastrado, retorna um dicionário nulo 
    para evitar KeyError.
    """
    return CONFIG_SERVIDORES.get(guild_id, {
        "nome": "Servidor Desconhecido",
        "canal_logs": None,
        "canal_punicoes": None,
        "categoria_tickets": None,
        "cargo_staff": None
    })

# =====================================================================
# SISTEMA DE LOGS DE PUNIÇÕES (PADRÃO GHOUL SECURITY)
# =====================================================================
async def enviar_log_punicao(guild, user, staff, acao, motivo, prova_bytes=None):
    """
    Função centralizada para enviar logs de auditoria visualmente ricos.
    Suporta anexação de imagens proibidas apagadas pelo automod.
    """
    config = obter_config(guild.id)
    if not config or not config.get("canal_punicoes"): 
        print(f"[LOGS] Canal de punições não configurado para o servidor {guild.name}.")
        return
        
    canal = guild.get_channel(config["canal_punicoes"])
    if not canal: 
        print(f"[LOGS] Canal de punições não encontrado (ID inválido) no servidor {guild.name}.")
        return

    # Construção robusta do Embed de punição
    embed = discord.Embed(
        title=f"🚨 REGISTRO DE SEGURANÇA | {acao}", 
        color=COR_PRINCIPAL, 
        timestamp=discord.utils.utcnow()
    )
    
    if hasattr(user, "display_avatar") and user.display_avatar:
        embed.set_thumbnail(url=user.display_avatar.url)
    
    embed.add_field(name="👤 Alvo da Ação", value=f"{user.mention}\n(`{user.id}`)", inline=True)
    
    # Tratamento para identificar se a staff foi o próprio bot (automod) ou um usuário humano
    staff_name = staff.mention if hasattr(staff, 'mention') else str(staff)
    embed.add_field(name="🛡️ Responsável", value=f"{staff_name}", inline=True)
    
    embed.add_field(name="📄 Descrição / Motivo", value=f"```ini\n[ {motivo} ]\n```", inline=False)
    
    # RODAPÉ RIGIDAMENTE PADRONIZADO COM O NOME "GHOUL SECURITY" E O AVATAR DO BOT
    avatar_url = bot.user.display_avatar.url if bot.user.display_avatar else None
    embed.set_footer(text=f"GHOUL SECURITY • {guild.name}", icon_url=avatar_url)
    
    try:
        if prova_bytes:
            # Se houver prova em bytes (imagem capturada pelo automod), envia como anexo
            file = discord.File(BytesIO(prova_bytes), filename="evidencia.png")
            embed.set_image(url="attachment://evidencia.png")
            await canal.send(embed=embed, file=file)
        else:
            await canal.send(embed=embed)
    except Exception as e:
        print(f"[LOGS ERROR] Erro fatal ao tentar enviar log de punição: {e}")

@bot.event
async def on_member_ban(guild, user):
    """
    Rastreia banimentos manuais feitos pelo painel do Discord
    e envia para o canal de logs automaticamente.
    """
    await asyncio.sleep(1.5) # Aguarda o Discord atualizar os Logs de Auditoria
    try:
        async for entry in guild.audit_logs(limit=2, action=discord.AuditLogAction.ban):
            if entry.target.id == user.id:
                if entry.user.id == bot.user.id: 
                    return # Ignora se foi o próprio bot, pois ele já tem sua própria função de log
                
                motivo = entry.reason if entry.reason else "Nenhum motivo especificado."
                await enviar_log_punicao(guild, user, entry.user, "BANIMENTO MANUAL", motivo)
                break
    except Exception as e:
        print(f"[EVENT ERROR] Erro no evento on_member_ban: {e}")

@bot.event
async def on_member_remove(member):
    """
    Rastreia expulsões manuais (Kicks) feitas pelo painel do Discord.
    """
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
        print(f"[EVENT ERROR] Erro no evento on_member_remove: {e}")

# =====================================================================
# AUTOMOD INTELIGENTE E GESTÃO DE IMAGENS LETAIS
# =====================================================================
@bot.tree.command(name="bloquear_imagem", description="[ADMIN] Adiciona imagem letal. Quem postar será banido permanentemente.")
@app_commands.default_permissions(administrator=True)
async def bloquear_imagem(interaction: discord.Interaction, imagem: discord.Attachment):
    """
    Comando Slash para cadastrar uma nova imagem no banco de dados letal.
    Usa ImageHash (Average Hash) para detectar variações da mesma imagem no futuro.
    """
    if not imagem.content_type or not imagem.content_type.startswith("image/"):
        return await interaction.response.send_message("❌ Erro: O arquivo enviado precisa ser estritamente uma imagem.", ephemeral=True)
    
    await interaction.response.defer(ephemeral=True)
    
    try:
        # Lê a imagem diretamente da memória, sem salvar no HD
        data = await imagem.read()
        img = Image.open(BytesIO(data)).convert("RGB")
        h = str(imagehash.average_hash(img))
        
        # Verifica duplicidade
        if h not in db["hashes_proibidos"]:
            db["hashes_proibidos"].append(h)
            salvar_db(db)
            
        # Cria a mensagem de sucesso
        embed = discord.Embed(
            title="⛔ IMAGEM REGISTRADA NO BANCO", 
            description=f"A imagem foi processada e computada com sucesso.\nQualquer usuário que tentar postar esta imagem (ou variantes dela) terá a mensagem deletada instantaneamente e sofrerá banimento permanente.\n\n**Hash Gerado para o DB:** `{h}`", 
            color=COR_PRINCIPAL
        )
        
        avatar_url = bot.user.display_avatar.url if bot.user.display_avatar else None
        embed.set_footer(text="GHOUL SECURITY", icon_url=avatar_url)
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Erro crítico no processamento visual (Pillow/ImageHash): {e}", ephemeral=True)

@bot.tree.command(name="remover_imagem_bloqueada", description="[ADMIN] Remove um hash do banco de imagens proibidas")
@app_commands.default_permissions(administrator=True)
async def remover_imagem_bloqueada(interaction: discord.Interaction, hash_str: str):
    """
    Comando para perdoar um hash anteriormente bloqueado.
    """
    if hash_str in db["hashes_proibidos"]:
        db["hashes_proibidos"].remove(hash_str)
        salvar_db(db)
        await interaction.response.send_message(f"✅ O hash `{hash_str}` foi removido com sucesso da Blacklist.", ephemeral=True)
    else:
        await interaction.response.send_message("❌ Hash não encontrado no banco de dados ativo.", ephemeral=True)

@bot.event
async def on_message(message):
    """
    O evento mais crítico do bot. Rastreia absolutamente todas as mensagens
    buscando quebra de regras (imagens letais, links, palavrões).
    """
    # 1. Barreiras de Segurança Iniciais
    if message.author.bot: 
        return
    if not message.guild: 
        return

    # Verifica se o autor NÃO é administrador.
    # Administradores não são alvejados pelo AutoMod, mas ainda podem usar comandos!
    if not message.author.guild_permissions.administrator:
        
        # =================================================================
        # VERIFICAÇÃO RIGOROSA 1: IMAGENS PROIBIDAS (DELETE + AVISO DM + BAN + LOG)
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
                            # Tolerância de variação = 6 (pega pequenas edições, filtros, crops)
                            if img_hash - target_hash <= 6:
                                
                                # Passo A: Deleta a mensagem ofensiva na hora
                                try: 
                                    await message.delete()
                                except Exception as e: 
                                    print(f"[AUTOMOD] Não consegui deletar a msg letal: {e}")

                                # Passo B: Envia uma DM assustadora pro usuário
                                try:
                                    embed_aviso = discord.Embed(
                                        title="🚨 BANIMENTO AUTOMÁTICO APLICADO", 
                                        description=f"Você acaba de ser banido permanentemente do servidor **{message.guild.name}**.\nMotivo: Tentativa de burlar a segurança postando conteúdo visual estritamente proibido.", 
                                        color=COR_PRINCIPAL
                                    )
                                    embed_aviso.set_footer(
                                        text="GHOUL SECURITY", 
                                        icon_url=bot.user.display_avatar.url if bot.user.display_avatar else None
                                    )
                                    await message.author.send(embed=embed_aviso)
                                except Exception as e: 
                                    print(f"[AUTOMOD] Falha ao enviar DM de ban (bloqueado?): {e}")

                                # Passo C: Bate o martelo (Ban permanente)
                                try:
                                    await message.guild.ban(
                                        message.author, 
                                        reason="AutoMod Letal de GHOUL SECURITY: Envio de imagem contida na Blacklist de Hashes."
                                    )
                                except Exception as e: 
                                    print(f"[AUTOMOD] Falha de permissão ao tentar aplicar ban: {e}")

                                # Passo D: Registra log rica enviando a imagem apagada para a staff analisar
                                await enviar_log_punicao(
                                    message.guild, 
                                    message.author, 
                                    bot.user, 
                                    "BAN AUTOMÁTICO (IMAGEM PROIBIDA)", 
                                    "O sistema inteligente detectou uma imagem restrita registrada na Blacklist.", 
                                    prova_bytes=img_bytes
                                )
                                return # Encerra o script para essa mensagem
                    except Exception as e:
                        print(f"[AUTOMOD CRITICAL] Erro no processamento de hash da mensagem: {e}")

        # =================================================================
        # VERIFICAÇÃO RIGOROSA 2: FILTRO ANTI-DIVULGAÇÃO DE LINKS DE CONVITE
        # =================================================================
        texto_inferior = message.content.lower()
        if "discord.gg/" in texto_inferior or "discord.com/invite/" in texto_inferior:
            try:
                await message.delete()
                
                embed_link = discord.Embed(
                    description=f"⚠️ {message.author.mention}, a divulgação de links de convite de outros servidores é estritamente proibida aqui!", 
                    color=COR_PRINCIPAL
                )
                embed_link.set_footer(
                    text="GHOUL SECURITY", 
                    icon_url=bot.user.display_avatar.url if bot.user.display_avatar else None
                )
                
                aviso = await message.channel.send(embed=embed_link)
                await aviso.delete(delay=5)
                return
            except Exception as e: 
                print(f"[AUTOMOD] Falha ao deletar link: {e}")

        # =================================================================
        # VERIFICAÇÃO RIGOROSA 3: FILTRO MASSIVO DE PALAVRÕES (EXPANDIDO)
        # =================================================================
        # Lista verticalizada contendo uma biblioteca completa de palavrões BR
        palavroes = [
            "fdp", 
            "fdps", 
            "f d p", 
            "vsf", 
            "vtnc", 
            "pnc", 
            "tnc", 
            "vtmnc", 
            "pqp", 
            "krl", 
            "crrl", 
            "kralho", 
            "caralh0", 
            "kct", 
            "kacete", 
            "krai", 
            "carai",
            "p0rra", 
            "prra", 
            "mrd", 
            "vsff", 
            "vnc", 
            "fdendo", 
            "caralho", 
            "caralhos", 
            "caralhuda", 
            "caralhudo", 
            "porra", 
            "porraloca", 
            "porrra", 
            "porraloka",
            "merda", 
            "merdinha", 
            "merdoes", 
            "merdão", 
            "bosta", 
            "bostinha", 
            "bostalhão", 
            "bostileiro", 
            "bostola", 
            "buceta", 
            "buketa", 
            "bucetinha", 
            "buseta", 
            "boceta", 
            "bucetão", 
            "puta", 
            "putinha", 
            "putasso", 
            "putona", 
            "putaria", 
            "cu", 
            "cuzao", 
            "cuzão", 
            "cuzinho", 
            "cuzonas", 
            "cusao", 
            "cuzões", 
            "pau", 
            "paumole", 
            "pauzao", 
            "pauzin", 
            "paunocu", 
            "paunoku", 
            "piroca", 
            "pirocudo", 
            "pirok", 
            "pirraca", 
            "pirokuda", 
            "foder", 
            "fodendo", 
            "fodeu", 
            "fodido", 
            "fodida", 
            "fudido", 
            "fudida", 
            "fodão", 
            "foderam", 
            "cacete", 
            "cacetada", 
            "cacetinho", 
            "chupa", 
            "chupando", 
            "chupeta", 
            "chupador", 
            "punheta", 
            "punheteiro", 
            "punheteira", 
            "gozada", 
            "gozar", 
            "gozando", 
            "bicha", 
            "bichona", 
            "boiola", 
            "viado", 
            "viadinho", 
            "viadaço", 
            "traveco", 
            "arrombado", 
            "arrombada", 
            "arrombados", 
            "desgraçado", 
            "desgracado", 
            "desgraçada", 
            "desgracada", 
            "corno", 
            "cornos", 
            "corna", 
            "cornuda", 
            "cornudo", 
            "chifrudo", 
            "chifruda", 
            "vagabundo", 
            "vagabunda", 
            "vagabundos", 
            "vagabundas", 
            "vagaba", 
            "otario", 
            "otária", 
            "otarios", 
            "otárias", 
            "imbecil", 
            "imbecis", 
            "idiota", 
            "idiotas", 
            "retardado", 
            "retardada", 
            "escroto", 
            "escrota", 
            "safado", 
            "safada", 
            "canalha", 
            "canalhas", 
            "miserável", 
            "miseravel", 
            "desgraça", 
            "desgraca", 
            "peste", 
            "praga", 
            "inferno", 
            "babaca", 
            "babacas", 
            "estúpido", 
            "estupido", 
            "estúpida", 
            "estupida", 
            "fedido", 
            "fedida", 
            "fedorento", 
            "fedorenta", 
            "lixo", 
            "lixos", 
            "lixoso", 
            "lixosa", 
            "mongol", 
            "mongolóide", 
            "mongoloide", 
            "nojento", 
            "nojenta", 
            "noia", 
            "nóia", 
            "patife", 
            "pirralho", 
            "pirralha", 
            "pivete", 
            "porco", 
            "porca", 
            "preguiçoso", 
            "preguiçosa", 
            "prostituta", 
            "prostituto", 
            "quenga", 
            "rabudo", 
            "rabuda", 
            "ridículo", 
            "ridiculo", 
            "ridícula", 
            "ridicula", 
            "rola", 
            "rolinha", 
            "sacana", 
            "sapatão", 
            "sapatao", 
            "seboso", 
            "sebosa", 
            "sem-vergonha", 
            "semvergonha", 
            "sujo", 
            "suja", 
            "tarado", 
            "tarada", 
            "trouxa", 
            "trouxas", 
            "vigarista", 
            "xexelento", 
            "xexelenta", 
            "xibiu", 
            "xota", 
            "xoxota", 
            "tomanocu", 
            "toma no cu", 
            "vai tomar no cu", 
            "vai se fuder", 
            "vai se fodir", 
            "puta que pariu", 
            "putaquepariu", 
            "filho da puta"
        ]
        
        # Limpa o texto tirando pontos, virgulas, traços etc, para não burlar o filtro
        texto_verificacao = re.sub(r"[^a-z0-9\s]", "", message.content.lower())
        palavras_msg = texto_verificacao.split()
        
        for p in palavroes:
            if p in palavras_msg or any(p in w for w in palavras_msg):
                try: 
                    await message.delete()
                except Exception as e: 
                    print(f"[AUTOMOD] Não foi possivel deletar o palavrão: {e}")
                    pass
                
                # Resposta exata solicitada pelo usuário (Cuidado com seu linguajar seu BOBOCA!)
                embed_palavra = discord.Embed(
                    description=f"⚠️ {message.author.mention}, Cuidado com seu linguajar seu BOBOCA!", 
                    color=COR_PRINCIPAL
                )
                embed_palavra.set_footer(
                    text="GHOUL SECURITY", 
                    icon_url=bot.user.display_avatar.url if bot.user.display_avatar else None
                )
                
                try:
                    msg_alerta = await message.channel.send(embed=embed_palavra)
                    await msg_alerta.delete(delay=5)
                except Exception as e:
                    print(f"[AUTOMOD] Erro ao enviar aviso de palavrão: {e}")
                    
                return # Interrompe a execução aqui para não enviar duplicação

    # Esta linha é vital. Processa os comandos normalmente (SEJA ADMIN OU NÃO!)
    await bot.process_commands(message)

# =====================================================================
# SISTEMA DE TICKETS PROFISSIONAL (BOTÕES NA MESMA LINHA E GHOUL SECURITY)
# =====================================================================
class TicketAcoesView(discord.ui.View):
    """
    View acoplada dentro do canal do Ticket criado.
    Responsável por exibir de forma persistente os botões:
    [ Fechar Ticket (Vermelho) ] [ Reivindicar Ticket (Azul) ] LADO A LADO (Row=0).
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
        # Inicia a sequência de encerramento
        embed = discord.Embed(
            title="🔒 ENCERRANDO TICKET", 
            description=f"Solicitado por {interaction.user.mention}. O canal será permanentemente apagado em **5 segundos**...", 
            color=COR_PRINCIPAL
        )
        embed.set_footer(
            text="GHOUL SECURITY", 
            icon_url=bot.user.display_avatar.url if bot.user.display_avatar else None
        )
        
        await interaction.response.send_message(embed=embed)
        await asyncio.sleep(5)
        
        try: 
            await interaction.channel.delete(reason=f"Ticket fechado por {interaction.user}")
        except Exception as e: 
            print(f"[TICKET] Falha ao deletar o canal: {e}")

    @discord.ui.button(
        label="Reivindicar Ticket", 
        style=discord.ButtonStyle.primary, 
        emoji="✋", 
        custom_id="reivindicar_ticket_btn_persisted", 
        row=0
    )
    async def reivindicar_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Ação visual e de controle para avisar o cliente quem assumiu o caso
        embed = discord.Embed(
            title="✋ ATENDIMENTO ASSUMIDO", 
            description=f"O membro da staff {interaction.user.mention} assumiu a responsabilidade exclusiva deste ticket. Aguarde instruções.", 
            color=COR_PRINCIPAL
        )
        embed.set_footer(
            text="GHOUL SECURITY", 
            icon_url=bot.user.display_avatar.url if bot.user.display_avatar else None
        )
        
        await interaction.response.send_message(embed=embed)

class TicketSelectDropdown(discord.ui.Select):
    """
    Menu Dropdown Suspenso que aparece no canal principal para o membro escolher o assunto.
    """
    def __init__(self):
        options = [
            discord.SelectOption(label="Suporte Geral", description="Dúvidas e orientações gerais", emoji="💬", value="suporte"),
            discord.SelectOption(label="Denúncias", description="Reportar infrações no servidor", emoji="🚨", value="denuncia"),
            discord.SelectOption(label="Financeiro / Lojas", description="Pagamentos, produtos e serviços", emoji="🛒", value="compras"),
            discord.SelectOption(label="Parcerias", description="Propostas comerciais oficiais", emoji="🤝", value="parceria")
        ]
        super().__init__(
            placeholder="📂 Clique e selecione o departamento desejado...", 
            options=options, 
            custom_id="ticket_dropdown_main"
        )

    async def callback(self, interaction: discord.Interaction):
        # Obtém a configuração de cargos e canais da Guild atual
        config = obter_config(interaction.guild.id)
        if not config or not config.get("categoria_tickets"):
            return await interaction.response.send_message("❌ A categoria de tickets não foi configurada pelo administrador.", ephemeral=True)

        categoria = interaction.guild.get_channel(config["categoria_tickets"])
        cargo_staff = interaction.guild.get_role(config["cargo_staff"]) if config.get("cargo_staff") else None

        # Arquitetura de Permissões: Privado para o usuário, bot e staff. Invisível pro resto.
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }
        
        if cargo_staff:
            overwrites[cargo_staff] = discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True)

        # Geração de nomenclatura do canal
        nome_canal = f"ticket-{interaction.user.name.lower()}"
        
        try:
            canal = await interaction.guild.create_text_channel(
                name=nome_canal, 
                category=categoria, 
                overwrites=overwrites
            )
        except Exception as e:
            return await interaction.response.send_message(f"❌ Erro crítico do Discord ao tentar criar o canal privado: {e}", ephemeral=True)

        # Montagem do Embed dentro do canal privado
        embed_ticket = discord.Embed(
            title="🎫 PAINEL DE ATENDIMENTO PRIVADO", 
            description=f"Olá {interaction.user.mention}!\n\nVocê selecionou o Departamento: **`{self.values[0].upper()}`**.\nDescreva seu problema de forma clara e objetiva para agilizar o suporte.", 
            color=COR_PRINCIPAL
        )
        embed_ticket.set_footer(
            text=f"GHOUL SECURITY • User ID: {interaction.user.id}", 
            icon_url=bot.user.display_avatar.url if bot.user.display_avatar else None
        )

        # Envia a mensagem marcando o usuário e a staff, acoplando a view com os 2 botões na horizontal
        marcacacao_texto = f"{interaction.user.mention} {cargo_staff.mention if cargo_staff else ''}"
        await canal.send(content=marcacacao_texto, embed=embed_ticket, view=TicketAcoesView())
        
        # Responde o usuário silenciosamente no canal publico onde ele clicou no menu
        await interaction.response.send_message(f"✅ Ticket aberto e pronto para atendimento: {canal.mention}", ephemeral=True)

class TicketPainelView(discord.ui.View):
    """
    View mestre do menu de tickets. Fica hospedada eternamente no canal de suporte.
    """
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelectDropdown())

@bot.tree.command(name="painel_tickets", description="[ADMIN] Invoca o painel definitivo de criação de tickets no canal atual")
@app_commands.default_permissions(administrator=True)
async def painel_tickets(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎫 CENTRAL DE ATENDIMENTO OFICIAL", 
        description="Selecione o assunto no menu abaixo para abrir um canal de atendimento privado 1x1 com nossa moderação.\nÉ proibido abrir tickets sem motivo aparente.", 
        color=COR_PRINCIPAL
    )
    
    # Carrega banner customizado por ID do servidor
    banner = IMAGENS_TICKETS.get(interaction.guild_id)
    if banner: 
        embed.set_image(url=banner)
        
    embed.set_footer(
        text="GHOUL SECURITY", 
        icon_url=bot.user.display_avatar.url if bot.user.display_avatar else None
    )
    
    await interaction.channel.send(embed=embed, view=TicketPainelView())
    await interaction.response.send_message("✅ Painel fixado no canal com sucesso!", ephemeral=True)

# COMANDOS DE BARRA EXCLUSIVOS PARA O CANAL DO TICKET
@bot.tree.command(name="close", description="[STAFF] Fecha o ticket atual por meio de um comando")
async def cmd_close(interaction: discord.Interaction):
    if "ticket-" not in interaction.channel.name:
        return await interaction.response.send_message("❌ Uso restrito. Execute apenas dentro de canais de tickets abertos.", ephemeral=True)
        
    embed = discord.Embed(
        title="🔒 TICKET ENCERRADO", 
        description="Encerrando ambiente em 5 segundos...", 
        color=COR_PRINCIPAL
    )
    embed.set_footer(
        text="GHOUL SECURITY", 
        icon_url=bot.user.display_avatar.url if bot.user.display_avatar else None
    )
    
    await interaction.response.send_message(embed=embed)
    await asyncio.sleep(5)
    try: 
        await interaction.channel.delete(reason=f"Encerrado via /close por {interaction.user}")
    except: 
        pass

@bot.tree.command(name="reivindicar", description="[STAFF] Assume o ticket atual por comando")
async def cmd_reivindicar(interaction: discord.Interaction):
    if "ticket-" not in interaction.channel.name:
        return await interaction.response.send_message("❌ Apenas em canais de tickets.", ephemeral=True)
        
    embed = discord.Embed(
        title="✋ TICKET REIVINDICADO", 
        description=f"O comando do ticket foi transferido para {interaction.user.mention}.", 
        color=COR_PRINCIPAL
    )
    embed.set_footer(
        text="GHOUL SECURITY", 
        icon_url=bot.user.display_avatar.url if bot.user.display_avatar else None
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="add_membro", description="[STAFF] Adiciona um membro terceiro ao ticket")
async def cmd_add_membro(interaction: discord.Interaction, membro: discord.Member):
    if "ticket-" not in interaction.channel.name: 
        return await interaction.response.send_message("❌ Apenas em tickets.", ephemeral=True)
        
    await interaction.channel.set_permissions(membro, read_messages=True, send_messages=True)
    await interaction.response.send_message(embed=discord.Embed(description=f"✅ O usuário {membro.mention} foi adicionado ao ticket privado.", color=COR_PRINCIPAL))

@bot.tree.command(name="rem_membro", description="[STAFF] Expulsa um membro do ticket")
async def cmd_rem_membro(interaction: discord.Interaction, membro: discord.Member):
    if "ticket-" not in interaction.channel.name: 
        return await interaction.response.send_message("❌ Apenas em tickets.", ephemeral=True)
        
    await interaction.channel.set_permissions(membro, overwrite=None)
    await interaction.response.send_message(embed=discord.Embed(description=f"✅ O usuário {membro.mention} perdeu acesso a este ticket.", color=COR_PRINCIPAL))

# =====================================================================
# SISTEMA DE SORTEIOS ÉPICOS (COMPLETO, EXPANDIDO E PERSISTENTE)
# =====================================================================
class SorteioModalGenerico(discord.ui.Modal):
    """
    Modal de formulário versátil que recebe inserção de texto dos botões do painel de criação.
    Permite customizar tudo do sorteio usando a API do Discord modals.
    """
    def __init__(self, painel, tipo, titulo):
        super().__init__(title=titulo)
        self.painel = painel
        self.tipo = tipo
        
        if tipo == "nome": 
            self.campo = discord.ui.TextInput(
                label="Título do Prêmio (O que será sorteado?)", 
                style=discord.TextStyle.short,
                default=painel.config["nome"],
                required=True
            )
        elif tipo == "desc": 
            self.campo = discord.ui.TextInput(
                label="Descrição do Sorteio (Regras, informações)", 
                style=discord.TextStyle.paragraph, 
                default=painel.config["descricao"],
                required=True
            )
        elif tipo == "vencedores": 
            self.campo = discord.ui.TextInput(
                label="Quantidade de Vencedores Simultâneos", 
                style=discord.TextStyle.short,
                default=str(painel.config["vencedores"]),
                required=True
            )
        elif tipo == "duracao": 
            self.campo = discord.ui.TextInput(
                label="Duração em Minutos (Ex: 60 para 1 hora)", 
                style=discord.TextStyle.short,
                default=str(painel.config["duracao_minutos"]),
                required=True
            )
        elif tipo == "emoji": 
            self.campo = discord.ui.TextInput(
                label="Emoji do Botão (Ex: 🎉, 🎁, 🚀)", 
                style=discord.TextStyle.short,
                default=painel.config["emoji"],
                required=True
            )
        elif tipo == "img": 
            self.campo = discord.ui.TextInput(
                label="URL da Imagem Ilustrativa (Opcional)", 
                style=discord.TextStyle.short,
                default=painel.config["imagem"], 
                required=False
            )
            
        self.add_item(self.campo)

    async def on_submit(self, interaction: discord.Interaction):
        # Tratamento seguro da entrada do usuário para não quebrar a aplicação
        val = self.campo.value.strip()
        
        if self.tipo == "nome": 
            self.painel.config["nome"] = val
        elif self.tipo == "desc": 
            self.painel.config["descricao"] = val
        elif self.tipo == "img": 
            self.painel.config["imagem"] = val
        elif self.tipo == "vencedores": 
            self.painel.config["vencedores"] = int(val) if val.isdigit() and int(val) > 0 else 1
        elif self.tipo == "duracao": 
            self.painel.config["duracao_minutos"] = int(val) if val.isdigit() and int(val) > 0 else 60
        elif self.tipo == "emoji": 
            self.painel.config["emoji"] = val
            
        await interaction.response.edit_message(embed=self.painel.construir_embed(), view=self.painel)

class SorteioEntradaExtraModal(discord.ui.Modal):
    """
    Modal acoplado para configurar a mecânica "Pay-to-Win" / Vantagens VIP.
    Define o peso numérico do cargo selecionado (x2, x5, x10 chances).
    """
    def __init__(self, painel, cargo_id):
        super().__init__(title="Configurar Multiplicador de Vantagem")
        self.painel = painel
        self.cargo_id = cargo_id
        
        self.campo = discord.ui.TextInput(
            label="Peso de Entradas Extras (Somente números)",
            style=discord.TextStyle.short,
            placeholder="Exemplo: 2, 5, 10"
        )
        self.add_item(self.campo)

    async def on_submit(self, interaction: discord.Interaction):
        if self.campo.value.isdigit(): 
            self.painel.config["entradas_extras"][str(self.cargo_id)] = int(self.campo.value)
        await interaction.response.edit_message(embed=self.painel.construir_embed(), view=self.painel)

class ParticiparSorteioView(discord.ui.View):
    """
    O botão vermelho final que aparece para os membros entrarem no sorteio.
    Hospeda a lógica avançada de vantagens baseada nos cargos.
    """
    def __init__(self, msg_id, config):
        super().__init__(timeout=None)
        self.msg_id = str(msg_id)
        self.config = config
        
        btn = discord.ui.Button(
            label="Participar Oficialmente", 
            style=discord.ButtonStyle.danger, 
            emoji=config.get("emoji", "🎉"), 
            custom_id=f"join_sorteio_{msg_id}"
        )
        btn.callback = self.participar_callback
        self.add_item(btn)

    async def participar_callback(self, interaction: discord.Interaction):
        if self.msg_id not in db["sorteios"] or db["sorteios"][self.msg_id]["status"] != "ativo":
            return await interaction.response.send_message("❌ Ação Negada: Este sorteio já foi encerrado ou não está mais ativo no sistema.", ephemeral=True)

        dados = db["sorteios"][self.msg_id]
        uid = str(interaction.user.id)
        user_roles = [str(r.id) for r in interaction.user.roles]

        if uid in dados["participantes_unicos"]:
            return await interaction.response.send_message("🍀 Calma! O sistema já computou que você está participando.", ephemeral=True)

        # Lógica matemática para as entradas bônus
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

        # Adiciona 1 vez no participantes unicos e N vezes no pool de sorteio
        dados["participantes_unicos"].append(uid)
        for _ in range(total_entradas): 
            dados["pool_entradas"].append(uid)
            
        salvar_db(db)

        msg_sucesso = f"🎉 Inscrição confirmada e registrada nos servidores!\n"
        if total_entradas > 1:
            msg_sucesso += f"Graças aos seus cargos, você inseriu seu nome **{total_entradas}x** no globo eletrônico."
            
        await interaction.response.send_message(msg_sucesso, ephemeral=True)

class PainelCriacaoSorteioView(discord.ui.View):
    """
    O Painel Interativo para o Administrador modular e criar o sorteio, 
    separado em 3 abas principais (Aparência, Geral, Vantagens).
    """
    def __init__(self, interaction):
        super().__init__(timeout=None)
        self.aba = "aparencia"
        self.config = {
            "nome": "Sorteio VIP da Semana",
            "descricao": "Leia as regras com atenção e clique no botão para registrar seu ticket!",
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
            embed.title = "🎨 Construção Visual do Sorteio"
            embed.description = f"**Título Atual:** {self.config['nome']}\n**Descrição:** {self.config['descricao']}\n**Emoji Configurado:** {self.config['emoji']}"
            
        elif self.aba == "geral": 
            embed.title = "⚙️ Parametros e Regras Gerais"
            embed.description = f"**Total de Vencedores Sorteados:** {self.config['vencedores']} players\n**Duração do Evento:** {self.config['duracao_minutos']} minutos\n**Canal Alvo da Postagem:** <#{self.config['canal_id']}>"
            
        elif self.aba == "extras": 
            embed.title = "🎟️ Benefícios de Cargos (P2W)"
            
            linhas_txt = []
            for cargo, qtd in self.config["entradas_extras"].items():
                linhas_txt.append(f"<@&{cargo}> -> concede peso de **{qtd}x** entradas")
                
            txt = "\n".join(linhas_txt) if linhas_txt else "Nenhum cargo extra configurado no momento."
            embed.description = f"{txt}\n\n**Modo de Somatório:** {'ON (Pessoas com múltiplos cargos ganham a soma)' if self.config['somar_entradas'] else 'OFF (Somente o cargo mais forte conta)'}"
            
        embed.set_footer(text="GHOUL SECURITY • Painel Administrativo", icon_url=bot.user.display_avatar.url if bot.user.display_avatar else None)
        return embed

    def montar_interface(self):
        self.clear_items()
        
        # Abas superiores
        b1 = discord.ui.Button(label="Guia Aparência", style=discord.ButtonStyle.danger if self.aba=="aparencia" else discord.ButtonStyle.secondary, row=0)
        b2 = discord.ui.Button(label="Guia Config. Geral", style=discord.ButtonStyle.danger if self.aba=="geral" else discord.ButtonStyle.secondary, row=0)
        b3 = discord.ui.Button(label="Guia Vantagens", style=discord.ButtonStyle.danger if self.aba=="extras" else discord.ButtonStyle.secondary, row=0)
        
        async def f_apa(i): 
            self.aba="aparencia"
            self.montar_interface()
            await i.response.edit_message(embed=self.construir_embed(), view=self)
            
        async def f_ger(i): 
            self.aba="geral"
            self.montar_interface()
            await i.response.edit_message(embed=self.construir_embed(), view=self)
            
        async def f_ext(i): 
            self.aba="extras"
            self.montar_interface()
            await i.response.edit_message(embed=self.construir_embed(), view=self)
            
        b1.callback=f_apa
        b2.callback=f_ger
        b3.callback=f_ext
        
        self.add_item(b1)
        self.add_item(b2)
        self.add_item(b3)

        # Botões da Aba Aparência
        if self.aba == "aparencia":
            btn1 = discord.ui.Button(label="Mudar Título", style=discord.ButtonStyle.primary, row=1)
            btn1.callback = lambda i: i.response.send_modal(SorteioModalGenerico(self, "nome", "Título do Sorteio"))
            
            btn2 = discord.ui.Button(label="Mudar Descrição", style=discord.ButtonStyle.primary, row=1)
            btn2.callback = lambda i: i.response.send_modal(SorteioModalGenerico(self, "desc", "Descrição do Sorteio"))
            
            btn3 = discord.ui.Button(label="Colar URL Banner", style=discord.ButtonStyle.primary, row=1)
            btn3.callback = lambda i: i.response.send_modal(SorteioModalGenerico(self, "img", "URL do Banner"))
            
            self.add_item(btn1)
            self.add_item(btn2)
            self.add_item(btn3)
            
        # Botões da Aba Geral
        elif self.aba == "geral":
            btn1 = discord.ui.Button(label="Definir Qtd Vencedores", style=discord.ButtonStyle.primary, row=1)
            btn1.callback = lambda i: i.response.send_modal(SorteioModalGenerico(self, "vencedores", "Total Ganhadores"))
            
            btn2 = discord.ui.Button(label="Definir Duração (M)", style=discord.ButtonStyle.primary, row=1)
            btn2.callback = lambda i: i.response.send_modal(SorteioModalGenerico(self, "duracao", "Minutos do Sorteio"))
            
            select_canal = discord.ui.ChannelSelect(channel_types=[discord.ChannelType.text], row=2, placeholder="Onde o sorteio será postado?")
            
            async def cb_canal(i): 
                self.config["canal_id"] = select_canal.values[0].id
                await i.response.edit_message(embed=self.construir_embed(), view=self)
                
            select_canal.callback = cb_canal
            
            self.add_item(btn1)
            self.add_item(btn2)
            self.add_item(select_canal)
            
        # Botões da Aba Vantagens Extras
        elif self.aba == "extras":
            select_extra = discord.ui.RoleSelect(row=1, placeholder="Selecione um cargo da guilda...")
            
            async def cb_ext(i): 
                await i.response.send_modal(SorteioEntradaExtraModal(self, select_extra.values[0].id))
                
            select_extra.callback = cb_ext
            
            btn_somar = discord.ui.Button(label="Ativar/Desativar Acúmulo de Somatório", style=discord.ButtonStyle.primary, row=2)
            
            async def cb_somar(i): 
                self.config["somar_entradas"] = not self.config["somar_entradas"]
                self.montar_interface()
                await i.response.edit_message(embed=self.construir_embed(), view=self)
                
            btn_somar.callback = cb_somar
            
            self.add_item(select_extra)
            self.add_item(btn_somar)

        # Botão final de lançamento presente em todas as abas (Row 4)
        btn_iniciar = discord.ui.Button(label="🚀 DISPARAR SORTEIO PARA O PÚBLICO", style=discord.ButtonStyle.success, row=4)
        btn_iniciar.callback = self.publicar
        self.add_item(btn_iniciar)

    async def publicar(self, interaction: discord.Interaction):
        """
        Executa a materialização do sorteio no canal de destino e 
        starta o cronômetro do bot via async task.
        """
        canal = interaction.guild.get_channel(self.config["canal_id"])
        
        if not canal:
            return await interaction.response.send_message("❌ O canal selecionado é inválido. Ele pode ter sido apagado.", ephemeral=True)
            
        termino = discord.utils.utcnow() + datetime.timedelta(minutes=self.config["duracao_minutos"])

        embed = discord.Embed(
            title=f"🎉 EVENTO: {self.config['nome']}", 
            description=f"{self.config['descricao']}\n\n**O tempo está correndo! Clique no botão abaixo para não perder.**", 
            color=COR_PRINCIPAL
        )
        embed.add_field(name="🏆 Vencedores Simultâneos", value=f"`{self.config['vencedores']}`", inline=True)
        embed.add_field(name="⏳ Encerramento Automático", value=f"{discord.utils.format_dt(termino, 'R')}", inline=True)
        
        if self.config["imagem"]: 
            embed.set_image(url=self.config["imagem"])
            
        embed.set_footer(text="GHOUL SECURITY", icon_url=bot.user.display_avatar.url if bot.user.display_avatar else None)

        msg = await canal.send(embed=embed)
        view = ParticiparSorteioView(msg.id, self.config)
        await msg.edit(view=view)

        # Salva a persistência
        db["sorteios"][str(msg.id)] = {
            "canal_id": canal.id, 
            "status": "ativo", 
            "config": self.config, 
            "participantes_unicos": [], 
            "pool_entradas": [], 
            "timestamp_fim": termino.timestamp()
        }
        salvar_db(db)
        
        await interaction.response.edit_message(content="✅ Sistema injetado! O sorteio já está rolando no canal.", embed=None, view=None)
        
        # Cria e roda a função cronometrada em segundo plano sem travar o bot
        bot.loop.create_task(finalizar_sorteio(canal, str(msg.id), self.config["duracao_minutos"]))

async def finalizar_sorteio(canal, msg_id, minutos):
    """
    Função engatilhada para aguardar silenciosamente o tempo acabar
    e fazer o sorteio matemático garantindo que não haja vencedores repetidos.
    """
    await asyncio.sleep(minutos * 60)
    
    # Validações caso o sorteio já tenha sido apagado ou cancelado manualmente
    if msg_id not in db["sorteios"] or db["sorteios"][msg_id]["status"] != "ativo": 
        return
    
    dados = db["sorteios"][msg_id]
    dados["status"] = "encerrado"
    salvar_db(db)

    try: 
        msg = await canal.fetch_message(int(msg_id))
    except Exception as e: 
        print(f"[SORTEIO] Não localizei a msg {msg_id} para encerrar: {e}")
        return

    # Sorteio abandonado (0 pessoas)
    if not dados["pool_entradas"]:
        embed_vazio = discord.Embed(
            title="😔 EVENTO CANCELADO", 
            description="O tempo se esgotou e infelizmente não houveram inscrições válidas.", 
            color=COR_PRINCIPAL
        )
        embed_vazio.set_footer(text="GHOUL SECURITY", icon_url=bot.user.display_avatar.url if bot.user.display_avatar else None)
        return await msg.edit(embed=embed_vazio, view=None)

    vencedores = []
    pool = list(dados["pool_entradas"])
    
    # Roletagem inteligente
    while len(vencedores) < dados["config"]["vencedores"] and pool:
        escolhido = random.choice(pool)
        if escolhido not in vencedores: 
            vencedores.append(escolhido)
            # Remove o player do pool caso a roletagem puxe ele de novo por acidente
            pool = [p for p in pool if p != escolhido]

    mentions = ", ".join([f"<@{v}>" for v in vencedores])
    
    # Edita a mensagem original do sorteio para mostrar a conclusão
    e = msg.embeds[0]
    e.title = f"🎊 EVENTO ENCERRADO: {dados['config']['nome']}"
    e.description = f"**Ganhadores Validados:**\n{mentions}\n\nObrigado a todos por participarem!"
    e.clear_fields()
    
    await msg.edit(embed=e, view=None)
    
    # Envia uma mensagem extra marcando os sorteados para notifica-los
    await canal.send(f"🎉 **PARABÉNS** {mentions}! Vocês foram sorteados e faturaram **{dados['config']['nome']}**!\nAbram um ticket caso seja necessário reivindicar.\n🔗 {msg.jump_url}")

@bot.tree.command(name="sorteio", description="[ADMIN] Abre o painel gerencial de Sorteios Interativos")
@app_commands.default_permissions(administrator=True)
async def cmd_sorteio(interaction: discord.Interaction):
    painel = PainelCriacaoSorteioView(interaction)
    await interaction.response.send_message(embed=painel.construir_embed(), view=painel, ephemeral=True)

@bot.tree.command(name="reroll", description="[ADMIN] Executa uma nova roletagem de um sorteio antigo através da ID")
@app_commands.default_permissions(administrator=True)
async def cmd_reroll(interaction: discord.Interaction, mensagem_id: str):
    """
    Sorteia um novo player caso o vencedor anterior seja fake/inativo,
    usando as entradas do banco de dados persistente.
    """
    if mensagem_id not in db["sorteios"] or not db["sorteios"][mensagem_id]["pool_entradas"]:
        return await interaction.response.send_message("❌ A ID não bate com nenhum evento salvo ou o sorteio nunca teve participantes.", ephemeral=True)
    
    dados = db["sorteios"][mensagem_id]
    novo_ganhador = random.choice(dados["pool_entradas"])
    canal = interaction.guild.get_channel(dados["canal_id"])
    
    embed = discord.Embed(
        title="🎲 SISTEMA DE REROLL ATIVADO", 
        description=f"A staff invalidou um ganhador antigo e girou a roleta de novo.\n\n👑 **O Novo Campeão É:** <@{novo_ganhador}>", 
        color=COR_PRINCIPAL
    )
    embed.set_footer(text="GHOUL SECURITY", icon_url=bot.user.display_avatar.url if bot.user.display_avatar else None)
    
    await interaction.response.send_message(embed=embed)
    
    if canal: 
        await canal.send(f"🎉 **ATENÇÃO AO REROLL!** A sorte virou e o novo campeão é <@{novo_ganhador}>! Parabéns!")

# =====================================================================
# COMANDOS GERAIS DE MODERAÇÃO E UTILIDADES DA STAFF (REFORÇADOS)
# =====================================================================
@bot.tree.command(name="ban", description="[MOD] Aplica banimento permanente no player com envio de registro no log")
@app_commands.default_permissions(ban_members=True)
async def cmd_ban(interaction: discord.Interaction, membro: discord.Member, motivo: str):
    try:
        await membro.ban(reason=motivo)
        await enviar_log_punicao(interaction.guild, membro, interaction.user, "BANIMENTO", motivo)
        
        embed = discord.Embed(description=f"✅ Martelo batido. {membro.mention} foi banido do servidor.", color=COR_PRINCIPAL)
        embed.set_footer(text="GHOUL SECURITY", icon_url=bot.user.display_avatar.url if bot.user.display_avatar else None)
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ Não foi possível banir este cargo: {e}", ephemeral=True)

@bot.tree.command(name="kick", description="[MOD] Desconecta/Expulsa o usuário fisicamente do servidor")
@app_commands.default_permissions(kick_members=True)
async def cmd_kick(interaction: discord.Interaction, membro: discord.Member, motivo: str):
    try:
        await membro.kick(reason=motivo)
        await enviar_log_punicao(interaction.guild, membro, interaction.user, "EXPULSÃO", motivo)
        
        embed = discord.Embed(description=f"✅ {membro.mention} foi chutado do servidor.", color=COR_PRINCIPAL)
        embed.set_footer(text="GHOUL SECURITY", icon_url=bot.user.display_avatar.url if bot.user.display_avatar else None)
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ Não foi possível expulsar este cargo: {e}", ephemeral=True)

@bot.tree.command(name="mute", description="[MOD] Joga o usuário no vazio (Timeout oficial do Discord)")
@app_commands.default_permissions(moderate_members=True)
async def cmd_mute(interaction: discord.Interaction, membro: discord.Member, minutos: int, motivo: str):
    try:
        await membro.timeout(datetime.timedelta(minutes=minutos), reason=motivo)
        await enviar_log_punicao(interaction.guild, membro, interaction.user, f"CASTIGO SILENCIOSO ({minutos}m)", motivo)
        
        embed = discord.Embed(description=f"✅ Ação executada. {membro.mention} está censurado por {minutos} minutos.", color=COR_PRINCIPAL)
        embed.set_footer(text="GHOUL SECURITY", icon_url=bot.user.display_avatar.url if bot.user.display_avatar else None)
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ Erro de hierarquia ao tentar castigar: {e}", ephemeral=True)

@bot.tree.command(name="unmute", description="[MOD] Restaura o direito de fala do player")
@app_commands.default_permissions(moderate_members=True)
async def cmd_unmute(interaction: discord.Interaction, membro: discord.Member):
    try:
        await membro.timeout(None)
        
        embed = discord.Embed(description=f"✅ Censor removido. {membro.mention} já pode comunicar-se.", color=COR_PRINCIPAL)
        embed.set_footer(text="GHOUL SECURITY", icon_url=bot.user.display_avatar.url if bot.user.display_avatar else None)
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ Falha de API: {e}", ephemeral=True)

@bot.tree.command(name="clear", description="[MOD] Purificador em massa. Apaga dezenas de mensagens instantly")
@app_commands.default_permissions(manage_messages=True)
async def cmd_clear(interaction: discord.Interaction, quantidade: int):
    # Proteção de limite do Discord
    if quantidade > 100 or quantidade < 1:
        return await interaction.response.send_message("❌ A quantidade deve estar entre 1 e 100 mensagens.", ephemeral=True)
        
    await interaction.response.defer(ephemeral=True)
    
    try:
        apagadas = await interaction.channel.purge(limit=quantidade)
        embed = discord.Embed(description=f"✅ Protocolo de purificação completo. `{len(apagadas)}` rastros apagados.", color=COR_PRINCIPAL)
        embed.set_footer(text="GHOUL SECURITY", icon_url=bot.user.display_avatar.url if bot.user.display_avatar else None)
        await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Falha na purificação: {e}", ephemeral=True)

@bot.tree.command(name="aviso", description="[ADMIN] Projeta uma mensagem oficial da administração no canal atual")
@app_commands.default_permissions(administrator=True)
async def cmd_aviso(interaction: discord.Interaction, titulo: str, mensagem: str):
    embed = discord.Embed(title=f"📢 COMUNICADO OFICIAL | {titulo}", description=mensagem, color=COR_PRINCIPAL)
    embed.set_footer(text="GHOUL SECURITY", icon_url=bot.user.display_avatar.url if bot.user.display_avatar else None)
    
    await interaction.channel.send(embed=embed)
    await interaction.response.send_message("✅ Transmissão enviada com sucesso ao público!", ephemeral=True)

# =====================================================================
# INICIALIZAÇÃO DE SEGURANÇA FINAL DO BOT
# =====================================================================
@bot.event
async def on_ready():
    """
    O evento é chamado assim que o bot conecta com sucesso aos servidores da API do Discord.
    Ele valida a identidade e prepara as estruturas na memória RAM.
    """
    print("\n")
    print("=" * 70)
    print(f"🤖 [GHOUL SECURITY] - SISTEMA INICIALIZADO COM ÊXITO")
    print(f"🆔 IDENTIDADE CONECTADA: {bot.user.name} | ID: {bot.user.id}")
    print(f"🛡️ HASHES LETAIS EM BANCO DE DADOS: {len(db['hashes_proibidos'])} arquivos blindados.")
    print(f"🎉 EVENTOS DE SORTEIO NA MEMÓRIA: {len(db['sorteios'])} registros.")
    print("=" * 70)
    print("\n[INFO] O bot está pronto para receber interações. Monitore os logs abaixo se precisar.")

# Bloco final que invoca o token e aterra o loop do asyncio
if __name__ == "__main__":
    TOKEN = os.getenv("TOKEN")
    
    # Tratativa para evitar o erro clássico de deploy sem variável
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("❌ [ERRO CRÍTICO] Falha catastrófica: O Token do bot não foi localizado nas Variáveis de Ambiente!")
        print("💡 Verifique se a variável 'TOKEN' está inserida no painel 'Environment' da Render.")
