import asyncio
import datetime
import os
import re
import unicodedata
import random
import time
from io import BytesIO
from threading import Thread

import discord
from discord import app_commands
from discord.ext import commands
from flask import Flask
import imagehash
from PIL import Image

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

TERMOS_BAN = [
    "checkmybio", "checkmyprofile", "lookmybio", "lookatmybio", "checkbio",
    "olharabiografia", "olheminhabio", "freenitro", "nitrogratis", "onlyfansfree"
]

PALAVROES = [
    "fdp", "filhodaputa", "caralho", "krl", "bosta", "escroto", "merda",
    "arrombado", "viado", "corno", "desgracado", "vagabundo", "porra", "buceta",
    "cacete", "puta", "puto", "cuzao", "pica", "rola", "xoxota", "vadia", "foder",
    "fodase", "tnc", "tomarnocu", "vsf", "vtnc", "pqp"
]

IMAGENS_BLOQUEADAS = [
    "9977339a644d9a62", "936c6c4e946cd966", "9748a8dcbd4a2579",
    "c48ff019712fe2c6", "91ac6db293ab09a6", "c1e1eb965c5e5cd0",
    "f5de4a08bdbd5aa5", "956a6e944ac9a6c9", "931e6ae394d3486f"
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
        self.sorteios_ativos = {}
        self.spam_control = {} # Para o Anti-Spam

    async def setup_hook(self):
        # Sincroniza os comandos Slash
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

# ==================== SISTEMA DE PUNIÇÕES ====================
async def log_punicao_bonito(guild, user, staff, acao, motivo, prova_url=None, anexos=None):
    config = obter_config(guild.id)
    if not config: return
    canal = guild.get_channel(config["canal_punicoes"])
    if not canal: return

    embed = discord.Embed(
        title=f"🔨 {config['nome']} - Punição Aplicada",
        color=0x950606,
        timestamp=discord.utils.utcnow()
    )
    if user.display_avatar:
        embed.set_thumbnail(url=user.display_avatar.url)

    embed.description = (
        f"👤 **Usuário:** {user.mention}\n"
        f"📛 **Nick:** `{user.name}`\n"
        f"🆔 **ID:** `{user.id}`\n"
        f"🛡️ **Staff:** {staff.mention if hasattr(staff, 'mention') else staff}\n"
        f"🚨 **Ação:** `{acao}`\n"
        f"📄 **Motivo:** {motivo}\n"
    )

    if prova_url:
        embed.set_image(url=prova_url)
    
    embed.set_footer(text=f"Segurança Ativa {config['nome']}", icon_url=guild.icon.url if guild.icon else None)
    
    if anexos:
        await canal.send(embed=embed, files=anexos)
    else:
        await canal.send(embed=embed)

async def executar_banimento(guild, membro, staff, motivo, acao_log, prova_url=None, anexos_prova=None):
    config = obter_config(guild.id)
    nome_servidor = config["nome"] if config else guild.name
    bot.ultimos_banimentos.add(membro.id)

    carta_dm = (
        f"**{nome_servidor} | Aviso de Banimento**\n\n"
        f"Caro(a) {membro.mention},\n"
        f"Você foi banido(a) por violar as nossas regras de segurança extrema.\n\n"
        f"**Motivo:** {motivo}\n\n"
        f"A decisão de banir permanece final.\n\n"
        f"*Equipe de Segurança - {nome_servidor}*"
    )
    try: await membro.send(carta_dm)
    except: pass

    try:
        staff_name = staff.name if hasattr(staff, "name") else str(staff)
        await guild.ban(membro, reason=f"{staff_name} | {motivo}", delete_message_days=1)
        await log_punicao_bonito(guild, membro, staff, acao_log, motivo, prova_url, anexos_prova)
        return True
    except Exception as e:
        print(f"[ERRO PERMISSÃO BAN] {e}")
        return False

# ==================== TODOS OS LOGS AVANÇADOS (GAMERSAFER STYLE) ====================
async def enviar_log_avancado(guild, title, description, user=None, image_url=None, files=None):
    config = obter_config(guild.id)
    if not config: return
    canal = guild.get_channel(config["canal_logs"])
    if not canal: return

    embed = discord.Embed(title=title, description=description, color=0x2b2d31, timestamp=discord.utils.utcnow())
    if user and user.display_avatar:
        embed.set_thumbnail(url=user.display_avatar.url)
    if image_url:
        embed.set_image(url=image_url)
    
    if files: await canal.send(embed=embed, files=files)
    else: await canal.send(embed=embed)

@bot.event
async def on_voice_state_update(member, before, after):
    # Moveu, Entrou, Saiu, Mute de Servidor
    if before.channel != after.channel:
        if before.channel is None:
            await enviar_log_avancado(member.guild, "🔊 Entrou no Canal de Voz", f"👤 **Membro:** {member.mention}\n📥 **Canal:** {after.channel.mention}", member)
        elif after.channel is None:
            await asyncio.sleep(1) # Aguarda o Audit Log registrar
            desconectado_por = None
            async for entry in member.guild.audit_logs(limit=5, action=discord.AuditLogAction.member_disconnect):
                if entry.target.id == member.id and (discord.utils.utcnow() - entry.created_at).total_seconds() < 15:
                    desconectado_por = entry.user
                    break
            
            if desconectado_por:
                await enviar_log_avancado(member.guild, "🚫 Desconectado à Força", f"👤 **Membro:** {member.mention}\n📤 **Canal:** {before.channel.mention}\n🛡️ **Staff:** {desconectado_por.mention}", member)
            else:
                await enviar_log_avancado(member.guild, "🔇 Saiu do Canal de Voz", f"👤 **Membro:** {member.mention}\n📤 **Saiu de:** {before.channel.mention}", member)
        else:
            await asyncio.sleep(1)
            movido_por = None
            async for entry in member.guild.audit_logs(limit=5, action=discord.AuditLogAction.member_move):
                if entry.target.id == member.id and (discord.utils.utcnow() - entry.created_at).total_seconds() < 15:
                    movido_por = entry.user
                    break

            desc = f"👤 **Membro:** {member.mention}\n⬅️ **Antes:** {before.channel.mention}\n➡️ **Agora:** {after.channel.mention}"
            if movido_por: desc += f"\n🛡️ **Movido por:** {movido_por.mention}"
            await enviar_log_avancado(member.guild, "🔄 Moveu de Canal", desc, member)

@bot.event
async def on_guild_channel_create(channel):
    await asyncio.sleep(1)
    criado_por = None
    async for entry in channel.guild.audit_logs(limit=5, action=discord.AuditLogAction.channel_create):
        if entry.target.id == channel.id: criado_por = entry.user; break
    desc = f"📁 **Canal:** {channel.mention} (`{channel.name}`)"
    if criado_por: desc += f"\n🛡️ **Criado por:** {criado_por.mention}"
    await enviar_log_avancado(channel.guild, "📁 Novo Canal Criado", desc)

@bot.event
async def on_guild_channel_delete(channel):
    await asyncio.sleep(1)
    apagado_por = None
    async for entry in channel.guild.audit_logs(limit=5, action=discord.AuditLogAction.channel_delete):
        if entry.target.id == channel.id: apagado_por = entry.user; break
    desc = f"📁 **Canal:** `{channel.name}`"
    if apagado_por: desc += f"\n🛡️ **Apagado por:** {apagado_por.mention}"
    await enviar_log_avancado(channel.guild, "🗑️ Canal Apagado", desc)

@bot.event
async def on_member_ban(guild, user):
    if user.id in bot.ultimos_banimentos: return # Já logou pelo bot
    await asyncio.sleep(1)
    banido_por, motivo = None, "Sem motivo"
    async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.ban):
        if entry.target.id == user.id:
            banido_por, motivo = entry.user, entry.reason
            break
    desc = f"👤 **Usuário:** {user.mention} (`{user.id}`)\n📄 **Motivo:** {motivo}"
    if banido_por: desc += f"\n🛡️ **Banido por:** {banido_por.mention}"
    await enviar_log_avancado(guild, "🔨 Usuário Banido", desc, user)


# ==================== FILTRO AUTOMOD DE ALTA PERFORMANCE ====================
@bot.event
async def on_message(message):
    if message.author.bot or not message.guild: return
    config = obter_config(message.guild.id)
    if not config: return

    # --- 1. SISTEMA ANTI-SPAM (Cooldown de 8s) ---
    autor_id = message.author.id
    agora = time.time()
    
    if not message.author.guild_permissions.administrator:
        if autor_id not in bot.spam_control:
            bot.spam_control[autor_id] = []
            
        # Filtra mensagens que ocorreram há menos de 8 segundos
        mensagens_recentes = [t for t in bot.spam_control[autor_id] if agora - t < 8]
        mensagens_recentes.append(agora)
        bot.spam_control[autor_id] = mensagens_recentes
        
        # Se enviou mais de 4 mensagens em menos de 8 segundos = SPAM
        if len(mensagens_recentes) > 4:
            bot.mensagens_ignoradas.add(message.id)
            try: await message.delete()
            except: pass
            
            bot.spam_control[autor_id] = [] # Reseta
            try:
                await message.author.timeout(datetime.timedelta(minutes=10), reason="Anti-Spam Acionado (Flood)")
                await message.channel.send(f"⚠️ {message.author.mention} foi silenciado por 10 minutos devido a SPAM.", delete_after=10)
                await log_punicao_bonito(message.guild, message.author, bot.user, "Mute Automático (10m)", "Spam intenso detectado.")
            except: pass
            return

    texto_norm = normalizar_texto(message.content)
    texto_junto = re.sub(r"\s+", "", texto_norm)

    # --- 2. DETECÇÃO DE IMAGENS PROIBIDAS (Corrigido) ---
    if message.attachments:
        for anexo in message.attachments:
            if any(anexo.filename.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp", ".gif"]):
                try:
                    bytes_img = await anexo.read()
                    img = Image.open(BytesIO(bytes_img)).convert("RGB")
                    img_avg_hash = imagehash.average_hash(img)
                    
                    for hash_bloqueado in IMAGENS_BLOQUEADAS:
                        hash_alvo = imagehash.hex_to_hash(hash_bloqueado)
                        # Distância menor ou igual a 8 significa que a imagem é quase idêntica
                        if (img_avg_hash - hash_alvo <= 8):
                            bot.mensagens_ignoradas.add(message.id)
                            # APAGA A MENSAGEM IMEDIATAMENTE antes de processar o ban
                            try: await message.delete()
                            except: pass
                            
                            file_prova = discord.File(BytesIO(bytes_img), filename="prova_ilegal.png")
                            await executar_banimento(message.guild, message.author, bot.user, "Envio de imagem proibida pelo AutoMod.", "Ban (Automático)", anexos_prova=[file_prova])
                            return # Para a execução
                except Exception as e:
                    print(f"Erro ao analisar imagem: {e}")

    # --- 3. TERMOS DE GOLPE/SCAM ---
    for termo in TERMOS_BAN:
        if termo in texto_junto:
            bot.mensagens_ignoradas.add(message.id)
            try: await message.delete()
            except: pass
            await executar_banimento(message.guild, message.author, bot.user, f"Golpe/Scam detectado: `{termo}`", "Ban (Automático)")
            return

    # --- 4. PALAVRÕES ---
    for palavrao in PALAVROES:
        if palavrao in texto_junto:
            bot.mensagens_ignoradas.add(message.id)
            try: await message.delete()
            except: pass
            await message.channel.send(f"⚠️ {message.author.mention}, moderador seu linguajar!", delete_after=5)
            await enviar_log_avancado(message.guild, "🛡️ Filtro - Palavrão", f"👤 **Usuário:** {message.author.mention}\n💬 **Canal:** {message.channel.mention}\n**Mensagem:** ```{message.content}```")
            return

    # --- 5. CONVITES ---
    if re.search(r"(discord\.gg/|discord\.com/invite/)", message.content.lower()) and not message.author.guild_permissions.administrator:
        bot.mensagens_ignoradas.add(message.id)
        try: await message.delete()
        except: pass
        try:
            await message.author.timeout(datetime.timedelta(hours=1), reason="Divulgação de link de convite.")
            await log_punicao_bonito(message.guild, message.author, bot.user, "Mute 1 Hora", "Divulgação de link externo.")
        except: pass
        return


# ==================== SISTEMA DE SORTEIO AVANÇADO ====================
@bot.tree.command(name="sorteio", description="Inicia um sorteio com sistema avançado de entradas extras (Estilo Loritta).")
@app_commands.describe(
    titulo="O que está sendo sorteado?", 
    minutos="Duração em minutos", 
    ganhadores="Quantas pessoas vão ganhar?",
    cargo_extra="Cargo que receberá entradas extras",
    entradas_extras="Quantidade de entradas que quem tem esse cargo vai receber (Ex: 1000)"
)
@app_commands.default_permissions(administrator=True)
async def sorteio(
    interaction: discord.Interaction, 
    titulo: str, 
    descricao: str, 
    minutos: int, 
    ganhadores: int = 1, 
    cargo_extra: discord.Role = None, 
    entradas_extras: int = 2
):
    termino = discord.utils.utcnow() + datetime.timedelta(minutes=minutos)
    
    embed = discord.Embed(title=f"🎉 SORTEIO: {titulo}", description=f"{descricao}\n\nReaja com 🎉 para participar!", color=0x29a6fe)
    embed.add_field(name="Ganhadores", value=str(ganhadores), inline=True)
    embed.add_field(name="Termina em", value=discord.utils.format_dt(termino, 'R'), inline=True)
    
    if cargo_extra and entradas_extras > 1:
        embed.add_field(name="✨ Vantagem Especial", value=f"Membros com {cargo_extra.mention} recebem **{entradas_extras} entradas extras** no sorteio!", inline=False)
        
    await interaction.response.send_message("Sorteio iniciado e configurado!", ephemeral=True)
    msg = await interaction.channel.send(embed=embed)
    await msg.add_reaction("🎉")

    bot.sorteios_ativos[msg.id] = {
        "ganhadores": ganhadores,
        "cargo_extra_id": cargo_extra.id if cargo_extra else None,
        "entradas_extras": entradas_extras
    }

    # Inicia contagem
    await asyncio.sleep(minutos * 60)
    await finalizar_sorteio(msg.channel, msg.id)

async def finalizar_sorteio(channel, msg_id):
    if msg_id not in bot.sorteios_ativos: return
    try:
        msg = await channel.fetch_message(msg_id)
        dados = bot.sorteios_ativos.pop(msg_id)
        
        reaction = discord.utils.get(msg.reactions, emoji="🎉")
        if not reaction: return
        
        users = [user async for user in reaction.users() if not user.bot]
        if not users:
            return await channel.send("😔 Ninguém participou do sorteio.")
            
        participantes = []
        for u in users:
            participantes.append(u) # Entrada padrão (1)
            
            # Aplica o peso absurdo se tiver o cargo
            if dados["cargo_extra_id"] and isinstance(u, discord.Member):
                if any(r.id == dados["cargo_extra_id"] for r in u.roles):
                    # Adiciona as entradas extras (ex: +999 entradas para totalizar 1000)
                    for _ in range(dados["entradas_extras"] - 1):
                        participantes.append(u)

        vencedores = []
        qtd_ganhadores = min(dados["ganhadores"], len(set(participantes)))
        
        # Sorteia garantindo que não pegue a mesma pessoa duas vezes
        while len(vencedores) < qtd_ganhadores:
            sorteado = random.choice(participantes)
            if sorteado not in vencedores:
                vencedores.append(sorteado)
        
        vencedores_mentions = ", ".join(v.mention for v in vencedores)
        embed = msg.embeds[0]
        embed.description = f"**SORTEIO ENCERRADO**\n\nGanhadores: {vencedores_mentions}"
        embed.color = 0x2b2d31
        await msg.edit(embed=embed)
        await channel.send(f"🎊 Parabéns {vencedores_mentions}! Vocês ganharam **{embed.title.replace('🎉 SORTEIO: ', '')}**! (Link: {msg.jump_url})")
    except Exception as e:
        print(f"Erro ao finalizar sorteio: {e}")

# ==================== COMANDOS BÁSICOS RESTANTES ====================
# [Mantenha os comandos de /limpar, /painel_tickets, /ban e dropdowns de tickets do seu código original aqui embaixo]
# O evento on_ready
@bot.event
async def on_ready():
    print(f"✅ {bot.user.name} online! Segurança máxima GamerSafer ativada.")

TOKEN = os.getenv("TOKEN")
if TOKEN: bot.run(TOKEN)
else: print("❌ ERRO: Token não encontrado.")
