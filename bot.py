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
        self.midia_cache = {} # Cache temporário de mídias deletadas

    async def setup_hook(self):
        self.add_view(ViewGhoul())
        self.add_view(ViewKings())
        self.add_view(ViewNightware())
        self.add_view(ViewValidar())
        self.add_view(ViewFechar())
        await self.tree.sync()

class ViewGhoul(discord.ui.View):
    def __init__(self):  
        super().__init__(timeout=None)
        self.add_item(DropdownGhoul())

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
    
    # Layout de punição super compacto, limpo e direto conforme solicitado
    description = (
        f"👤 **Usuário:** {user.mention}\n"
        f"📛 **Nick:** `{user.name}`\n"
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
    try:
        await membro.send(carta_dm)
    except: 
        pass 

    try:
        await membro.ban(reason=f"{staff.name} | {motivo}")
        await log_punicao_bonito(guild, membro, staff, acao_log, motivo, prova_url)
        return True
    except Exception as e:
        print(f"[ERRO PERMISSÃO] Não foi possível banir o usuário {membro.name} ({membro.id}). Detalhe: {e}")
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
        f"👤 **Usuário:** {message.author.mention}\n"
        f"📛 **Nick:** `{message.author.name}`\n"
        f"🆔 **ID:** `{message.author.id}`\n"
        f"💬 **Canal:** {message.channel.mention}\n"
        f"🚨 **Ocorrência:** `{ocorrencia}`\n\n"
        f"**Mensagem Deletada:**\n"
        f"```{texto_original}```"
    )
    
    embed.set_footer(text=f"Segurança Ativa {config['nome']}", icon_url=message.guild.icon.url if message.guild.icon else None)
    await canal.send(embed=embed)

# ==================== DETECÇÃO DE AÇÕES DA STAFF E LOGS DIVERSOS ====================
@bot.event
async def on_member_join(member):
    config = obter_config(member.guild.id)
    if config and (canal_logs := bot.get_channel(config["canal_logs"])):
        embed = discord.Embed(
            title=f"📥 {config['nome']} - Membro Entrou",
            description=f"👤 **Membro:** {member.mention} ({member.id})\nO usuário acaba de se juntar ao servidor.",
            color=0x950606,
            timestamp=discord.utils.utcnow()
        )
        if member.display_avatar:
            embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"Segurança Ativa {config['nome']}", icon_url=member.guild.icon.url if member.guild.icon else None)
        await canal_logs.send(embed=embed)

@bot.event
async def on_member_remove(member):
    config = obter_config(member.guild.id)
    if config and (canal_logs := bot.get_channel(config["canal_logs"])):
        embed = discord.Embed(
            title=f"📤 {config['nome']} - Membro Saiu",
            description=f"👤 **Membro:** {member.mention} ({member.id})\nO usuário deixou o servidor.",
            color=0x950606,
            timestamp=discord.utils.utcnow()
        )
        if member.display_avatar:
            embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"Segurança Ativa {config['nome']}", icon_url=member.guild.icon.url if member.guild.icon else None)
        await canal_logs.send(embed=embed)

@bot.event
async def on_member_ban(guild, user):
    if user.id in bot.ultimos_banimentos:
        bot.ultimos_banimentos.discard(user.id)
        return 

    await asyncio.sleep(2)
    try:
        async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.ban):
            if entry.target.id == user.id:
                if entry.user.id == bot.user.id: 
                    return 
                await log_punicao_bonito(guild, user, entry.user, "Banimento (Painel/Botão Direito)", entry.reason or "Nenhum motivo inserido.")
                return
    except: pass

@bot.event
async def on_member_unban(guild, user):
    await asyncio.sleep(2)
    try:
        async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.unban):
            if entry.target.id == user.id:
                if entry.user.id == bot.user.id: 
                    return
                await log_punicao_bonito(guild, user, entry.user, "Desbanimento (Painel/Botão Direito)", entry.reason or "Nenhum motivo inserido.")
                return
    except: pass

@bot.event
async def on_member_update(before, after):
    config = obter_config(before.guild.id)
    if not config: return
    canal_logs = bot.get_channel(config["canal_logs"])

    # Log de Mute (Timeout)
    if before.timed_out_until != after.timed_out_until:
        if after.id in bot.ultimos_mutes:
            bot.ultimos_mutes.discard(after.id)
            return

        await asyncio.sleep(2)
        try:
            if after.timed_out_until is not None:
                async for entry in before.guild.audit_logs(limit=5, action=discord.AuditLogAction.member_update):
                    if entry.target.id == after.id and hasattr(entry.after, 'timed_out_until'):
                        if entry.user.id == bot.user.id: return
                        tempo = after.timed_out_until - discord.utils.utcnow()
                        minutos = max(1, int(tempo.total_seconds() / 60))
                        await log_punicao_bonito(before.guild, after, entry.user, f"Mute ({minutos} mins - Discord)", entry.reason or "Aplicado via painel/botão direito.")
                        return
            elif after.timed_out_until is None:
                async for entry in before.guild.audit_logs(limit=5, action=discord.AuditLogAction.member_update):
                    if entry.target.id == after.id and hasattr(entry.before, 'timed_out_until') and not hasattr(entry.after, 'timed_out_until'):
                        if entry.user.id == bot.user.id: return
                        await log_punicao_bonito(before.guild, after, entry.user, "Desmutado (Discord)", entry.reason or "Removido via painel/botão direito.")
                        return
        except: pass

    # Log de Nickname
    if before.nick != after.nick:
        if canal_logs:
            embed = discord.Embed(
                title=f"👤 {config['nome']} - Alteração de Apelido",
                color=0x950606,
                timestamp=discord.utils.utcnow()
            )
            if after.display_avatar: embed.set_thumbnail(url=after.display_avatar.url)
            embed.description = f"👤 **Membro:** {after.mention} ({after.id})\n🏷️ **Antigo:** `{before.nick or before.name}`\n🏷️ **Novo:** `{after.nick or after.name}`"
            embed.set_footer(text=f"Segurança Ativa {config['nome']}", icon_url=before.guild.icon.url if before.guild.icon else None)
            await canal_logs.send(embed=embed)

    # Log de Avatar do Servidor (Guild Specific Avatar)
    if before.guild_avatar != after.guild_avatar:
        if canal_logs:
            embed = discord.Embed(
                title=f"🖼️ {config['nome']} - Alteração de Avatar do Servidor",
                color=0x950606,
                timestamp=discord.utils.utcnow()
            )
            avatar_antigo = before.guild_avatar.url if before.guild_avatar else (before.avatar.url if before.avatar else before.default_avatar.url)
            avatar_novo = after.guild_avatar.url if after.guild_avatar else (after.avatar.url if after.avatar else after.default_avatar.url)
            
            embed.description = (
                f"👤 **Membro:** {after.mention} ({after.id})\n"
                f"📸 **Avatar Anterior:** [Clique para abrir]({avatar_antigo})\n"
                f"✨ **Avatar Novo:** [Clique para abrir]({avatar_novo})\n\n"
                f"*O membro mudou sua foto de perfil específica neste servidor.*"
            )
            embed.set_thumbnail(url=avatar_antigo)
            embed.set_image(url=avatar_novo)
            embed.set_footer(text=f"Segurança Ativa {config['nome']}", icon_url=before.guild.icon.url if before.guild.icon else None)
            await canal_logs.send(embed=embed)

@bot.event
async def on_user_update(before, after):
    for guild in bot.guilds:
        config = obter_config(guild.id)
        if not config: continue
        member = guild.get_member(after.id)
        if not member: continue
        canal_logs = bot.get_channel(config["canal_logs"])
        if not canal_logs: continue

        # Nome Global
        if before.name != after.name:
            embed = discord.Embed(title=f"👤 {config['nome']} - Alteração de Nome Global", color=0x950606, timestamp=discord.utils.utcnow())
            if after.display_avatar: embed.set_thumbnail(url=after.display_avatar.url)
            embed.description = f"👤 **Membro:** {member.mention} ({member.id})\n📛 **Antigo:** `{before.name}`\n📛 **Novo:** `{after.name}`"
            embed.set_footer(text=f"Segurança Ativa {config['nome']}", icon_url=guild.icon.url if guild.icon else None)
            await canal_logs.send(embed=embed)

        # Avatar Global
        if before.avatar != after.avatar:
            embed = discord.Embed(
                title=f"🖼️ {config['nome']} - Alteração de Avatar", 
                color=0x950606, 
                timestamp=discord.utils.utcnow()
            )
            
            avatar_antigo_url = before.avatar.url if before.avatar else before.default_avatar.url
            avatar_novo_url = after.avatar.url if after.avatar else after.default_avatar.url

            embed.description = (
                f"👤 **Membro:** {member.mention} ({member.id})\n"
                f"📸 **Avatar Anterior:** [Clique para abrir]({avatar_antigo_url})\n"
                f"✨ **Avatar Novo:** [Clique para abrir]({avatar_novo_url})\n\n"
                f"*O membro alterou sua foto de perfil global.*"
            )
            embed.set_thumbnail(url=avatar_antigo_url)
            embed.set_image(url=avatar_novo_url)
            embed.set_footer(text=f"Segurança Ativa {config['nome']}", icon_url=guild.icon.url if guild.icon else None)
            await canal_logs.send(embed=embed)

@bot.event
async def on_voice_state_update(member, before, after):
    config = obter_config(member.guild.id)
    if not config or not (canal_logs := bot.get_channel(config["canal_logs"])): return

    embed = discord.Embed(color=0x950606, timestamp=discord.utils.utcnow())
    if member.display_avatar: embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=f"Segurança Ativa {config['nome']}", icon_url=member.guild.icon.url if member.guild.icon else None)

    if before.channel is None and after.channel is not None:
        tipo = "Palco 🎤" if isinstance(after.channel, discord.StageChannel) else "Canal de Voz 🔊"
        embed.title = f"🔊 {config['nome']} - Entrada em Call"
        embed.description = f"👤 **Membro:** {member.mention} ({member.id})\n📥 **Conectou em:** {after.channel.mention} ({after.channel.name})\n🏷️ **Tipo:** `{tipo}`"
        await canal_logs.send(embed=embed)

    elif before.channel is not None and after.channel is None:
        tipo = "Palco 🎤" if isinstance(before.channel, discord.StageChannel) else "Canal de Voz 🔊"
        embed.title = f"🔇 {config['nome']} - Saída de Call"
        embed.description = f"👤 **Membro:** {member.mention} ({member.id})\n📤 **Desconectou de:** {before.channel.mention} ({before.channel.name})\n🏷️ **Tipo:** `{tipo}`"
        await canal_logs.send(embed=embed)

    elif before.channel is not None and after.channel is not None and before.channel.id != after.channel.id:
        tipo_antigo = "Palco 🎤" if isinstance(before.channel, discord.StageChannel) else "Canal de Voz 🔊"
        tipo_novo = "Palco 🎤" if isinstance(after.channel, discord.StageChannel) else "Canal de Voz 🔊"
        embed.title = f"🔁 {config['nome']} - Movimentação de Call"
        embed.description = f"👤 **Membro:** {member.mention} ({member.id})\n📤 **Anterior:** {before.channel.mention} (`{tipo_antigo}`)\n📥 **Novo:** {after.channel.mention} (`{tipo_novo}`)"
        await canal_logs.send(embed=embed)

# ==================== LOGS NOVOS ADICIONADOS (CARGOS, CANAIS, TÓPICOS, ETC) ====================

@bot.event
async def on_guild_role_create(role):
    config = obter_config(role.guild.id)
    if config and (canal_logs := bot.get_channel(config["canal_logs"])):
        embed = discord.Embed(title=f"🔰 {config['nome']} - Novo Cargo Criado", description=f"O cargo {role.mention} (`{role.name}`) foi criado no servidor.", color=0x950606, timestamp=discord.utils.utcnow())
        embed.set_footer(text=f"Segurança Ativa {config['nome']}", icon_url=role.guild.icon.url if role.guild.icon else None)
        await canal_logs.send(embed=embed)

@bot.event
async def on_guild_role_delete(role):
    config = obter_config(role.guild.id)
    if config and (canal_logs := bot.get_channel(config["canal_logs"])):
        embed = discord.Embed(title=f"🗑️ {config['nome']} - Cargo Apagado", description=f"O cargo `{role.name}` foi apagado do servidor.", color=0x950606, timestamp=discord.utils.utcnow())
        embed.set_footer(text=f"Segurança Ativa {config['nome']}", icon_url=role.guild.icon.url if role.guild.icon else None)
        await canal_logs.send(embed=embed)

@bot.event
async def on_guild_role_update(before, after):
    config = obter_config(before.guild.id)
    if config and (canal_logs := bot.get_channel(config["canal_logs"])):
        if before.name != after.name or before.color != after.color or before.permissions != after.permissions:
            embed = discord.Embed(title=f"⚙️ {config['nome']} - Cargo Atualizado", description=f"O cargo {after.mention} (`{after.name}`) sofreu alterações.", color=0x950606, timestamp=discord.utils.utcnow())
            embed.set_footer(text=f"Segurança Ativa {config['nome']}", icon_url=before.guild.icon.url if before.guild.icon else None)
            await canal_logs.send(embed=embed)

@bot.event
async def on_guild_channel_create(channel):
    config = obter_config(channel.guild.id)
    if config and (canal_logs := bot.get_channel(config["canal_logs"])):
        embed = discord.Embed(title=f"📁 {config['nome']} - Novo Canal Criado", description=f"O canal {channel.mention} (`{channel.name}`) foi criado.", color=0x950606, timestamp=discord.utils.utcnow())
        embed.set_footer(text=f"Segurança Ativa {config['nome']}", icon_url=channel.guild.icon.url if channel.guild.icon else None)
        await canal_logs.send(embed=embed)

@bot.event
async def on_guild_channel_delete(channel):
    config = obter_config(channel.guild.id)
    if config and (canal_logs := bot.get_channel(config["canal_logs"])):
        embed = discord.Embed(title=f"🗑️ {config['nome']} - Canal Apagado", description=f"O canal `{channel.name}` foi apagado.", color=0x950606, timestamp=discord.utils.utcnow())
        embed.set_footer(text=f"Segurança Ativa {config['nome']}", icon_url=channel.guild.icon.url if channel.guild.icon else None)
        await canal_logs.send(embed=embed)

@bot.event
async def on_guild_channel_update(before, after):
    config = obter_config(before.guild.id)
    if config and (canal_logs := bot.get_channel(config["canal_logs"])):
        if before.name != after.name or before.overwrites != after.overwrites:
            embed = discord.Embed(title=f"⚙️ {config['nome']} - Canal Atualizado", description=f"O canal {after.mention} sofreu alterações (Nome, Permissões, etc).", color=0x950606, timestamp=discord.utils.utcnow())
            embed.set_footer(text=f"Segurança Ativa {config['nome']}", icon_url=before.guild.icon.url if before.guild.icon else None)
            await canal_logs.send(embed=embed)

@bot.event
async def on_thread_create(thread):
    config = obter_config(thread.guild.id)
    if config and (canal_logs := bot.get_channel(config["canal_logs"])):
        embed = discord.Embed(title=f"🧵 {config['nome']} - Novo Tópico Criado", description=f"O tópico {thread.mention} (`{thread.name}`) foi criado no canal {thread.parent.mention}.", color=0x950606, timestamp=discord.utils.utcnow())
        embed.set_footer(text=f"Segurança Ativa {config['nome']}", icon_url=thread.guild.icon.url if thread.guild.icon else None)
        await canal_logs.send(embed=embed)

@bot.event
async def on_thread_delete(thread):
    config = obter_config(thread.guild.id)
    if config and (canal_logs := bot.get_channel(config["canal_logs"])):
        embed = discord.Embed(title=f"🗑️ {config['nome']} - Tópico Apagado", description=f"Um tópico chamado `{thread.name}` foi apagado.", color=0x950606, timestamp=discord.utils.utcnow())
        embed.set_footer(text=f"Segurança Ativa {config['nome']}", icon_url=thread.guild.icon.url if thread.guild.icon else None)
        await canal_logs.send(embed=embed)

@bot.event
async def on_thread_update(before, after):
    config = obter_config(before.guild.id)
    if config and (canal_logs := bot.get_channel(config["canal_logs"])):
        if before.name != after.name or before.archived != after.archived:
            embed = discord.Embed(title=f"⚙️ {config['nome']} - Tópico Atualizado", description=f"O tópico {after.mention} sofreu alterações.", color=0x950606, timestamp=discord.utils.utcnow())
            embed.set_footer(text=f"Segurança Ativa {config['nome']}", icon_url=before.guild.icon.url if before.guild.icon else None)
            await canal_logs.send(embed=embed)

@bot.event
async def on_invite_create(invite):
    if not invite.guild: return
    config = obter_config(invite.guild.id)
    if config and (canal_logs := bot.get_channel(config["canal_logs"])):
        embed = discord.Embed(title=f"🔗 {config['nome']} - Criação de Convite", description=f"👤 **Criador:** {invite.inviter.mention if invite.inviter else 'Desconhecido'}\n🔗 **Código:** `{invite.code}`\n📍 **Canal:** {invite.channel.mention}", color=0x950606, timestamp=discord.utils.utcnow())
        embed.set_footer(text=f"Segurança Ativa {config['nome']}", icon_url=invite.guild.icon.url if invite.guild.icon else None)
        await canal_logs.send(embed=embed)

@bot.event
async def on_invite_delete(invite):
    if not invite.guild: return
    config = obter_config(invite.guild.id)
    if config and (canal_logs := bot.get_channel(config["canal_logs"])):
        embed = discord.Embed(title=f"🗑️ {config['nome']} - Convite Apagado", description=f"O convite com código `{invite.code}` do canal {invite.channel.mention} foi apagado.", color=0x950606, timestamp=discord.utils.utcnow())
        embed.set_footer(text=f"Segurança Ativa {config['nome']}", icon_url=invite.guild.icon.url if invite.guild.icon else None)
        await canal_logs.send(embed=embed)

@bot.event
async def on_guild_emojis_update(guild, before, after):
    config = obter_config(guild.id)
    if config and (canal_logs := bot.get_channel(config["canal_logs"])):
        if len(before) < len(after):
            novo = list(set(after) - set(before))[0]
            embed = discord.Embed(title=f"😀 {config['nome']} - Novo Emoji Adicionado", description=f"Emoji adicionado: {novo} (`{novo.name}`)", color=0x950606, timestamp=discord.utils.utcnow())
        elif len(before) > len(after):
            removido = list(set(before) - set(after))[0]
            embed = discord.Embed(title=f"🗑️ {config['nome']} - Emoji Apagado", description=f"O emoji `{removido.name}` foi deletado.", color=0x950606, timestamp=discord.utils.utcnow())
        else:
            embed = discord.Embed(title=f"⚙️ {config['nome']} - Emoji Atualizado", description="Um ou mais emojis foram renomeados ou atualizados.", color=0x950606, timestamp=discord.utils.utcnow())
        embed.set_footer(text=f"Segurança Ativa {config['nome']}", icon_url=guild.icon.url if guild.icon else None)
        await canal_logs.send(embed=embed)

@bot.event
async def on_guild_stickers_update(guild, before, after):
    config = obter_config(guild.id)
    if config and (canal_logs := bot.get_channel(config["canal_logs"])):
        if len(before) < len(after):
            novo = list(set(after) - set(before))[0]
            embed = discord.Embed(title=f"🖼️ {config['nome']} - Nova Figurinha Adicionada", description=f"Figurinha adicionada: `{novo.name}`", color=0x950606, timestamp=discord.utils.utcnow())
        elif len(before) > len(after):
            removido = list(set(before) - set(after))[0]
            embed = discord.Embed(title=f"🗑️ {config['nome']} - Figurinha Apagada", description=f"A figurinha `{removido.name}` foi deletada.", color=0x950606, timestamp=discord.utils.utcnow())
        else:
            embed = discord.Embed(title=f"⚙️ {config['nome']} - Figurinha Atualizada", description="Uma figurinha foi renomeada ou atualizada.", color=0x950606, timestamp=discord.utils.utcnow())
        embed.set_footer(text=f"Segurança Ativa {config['nome']}", icon_url=guild.icon.url if guild.icon else None)
        await canal_logs.send(embed=embed)

@bot.event
async def on_scheduled_event_create(event):
    config = obter_config(event.guild.id)
    if config and (canal_logs := bot.get_channel(config["canal_logs"])):
        embed = discord.Embed(title=f"📅 {config['nome']} - Novo Evento Criado", description=f"Evento: **{event.name}** foi criado.", color=0x950606, timestamp=discord.utils.utcnow())
        embed.set_footer(text=f"Segurança Ativa {config['nome']}", icon_url=event.guild.icon.url if event.guild.icon else None)
        await canal_logs.send(embed=embed)

@bot.event
async def on_scheduled_event_delete(event):
    config = obter_config(event.guild.id)
    if config and (canal_logs := bot.get_channel(config["canal_logs"])):
        embed = discord.Embed(title=f"🗑️ {config['nome']} - Evento Apagado", description=f"O evento **{event.name}** foi cancelado/apagado.", color=0x950606, timestamp=discord.utils.utcnow())
        embed.set_footer(text=f"Segurança Ativa {config['nome']}", icon_url=event.guild.icon.url if event.guild.icon else None)
        await canal_logs.send(embed=embed)

@bot.event
async def on_scheduled_event_update(before, after):
    config = obter_config(before.guild.id)
    if config and (canal_logs := bot.get_channel(config["canal_logs"])):
        if before.name != after.name or before.description != after.description or before.status != after.status:
            embed = discord.Embed(title=f"⚙️ {config['nome']} - Evento Atualizado", description=f"O evento **{after.name}** sofreu alterações (nome, descrição ou status).", color=0x950606, timestamp=discord.utils.utcnow())
            embed.set_footer(text=f"Segurança Ativa {config['nome']}", icon_url=before.guild.icon.url if before.guild.icon else None)
            await canal_logs.send(embed=embed)

@bot.event
async def on_bulk_message_delete(messages):
    if not messages: return
    guild = messages[0].guild
    config = obter_config(guild.id)
    if config and (canal_logs := bot.get_channel(config["canal_logs"])):
        embed = discord.Embed(title=f"🗑️ {config['nome']} - Apagar Muitas Mensagens (Purge)", description=f"**{len(messages)}** mensagens foram apagadas de uma só vez no canal {messages[0].channel.mention}.", color=0x950606, timestamp=discord.utils.utcnow())
        embed.set_footer(text=f"Segurança Ativa {config['nome']}", icon_url=guild.icon.url if guild.icon else None)
        await canal_logs.send(embed=embed)

@bot.event
async def on_guild_update(before, after):
    config = obter_config(before.id)
    if config and (canal_logs := bot.get_channel(config["canal_logs"])):
        if before.name != after.name or before.icon != after.icon:
            embed = discord.Embed(title=f"⚙️ {config['nome']} - Atualizar Servidor", description="As configurações gerais do servidor (Nome, Ícone, etc) foram alteradas.", color=0x950606, timestamp=discord.utils.utcnow())
            embed.set_footer(text=f"Segurança Ativa {config['nome']}", icon_url=after.icon.url if after.icon else None)
            await canal_logs.send(embed=embed)

@bot.event
async def on_webhooks_update(channel):
    config = obter_config(channel.guild.id)
    if config and (canal_logs := bot.get_channel(config["canal_logs"])):
        embed = discord.Embed(title=f"🪝 {config['nome']} - Webhook Atualizado", description=f"Os webhooks no canal {channel.mention} foram criados, atualizados ou apagados.", color=0x950606, timestamp=discord.utils.utcnow())
        embed.set_footer(text=f"Segurança Ativa {config['nome']}", icon_url=channel.guild.icon.url if channel.guild.icon else None)
        await canal_logs.send(embed=embed)

@bot.event
async def on_guild_integrations_update(guild):
    config = obter_config(guild.id)
    if config and (canal_logs := bot.get_channel(config["canal_logs"])):
        embed = discord.Embed(title=f"🔌 {config['nome']} - Integração Atualizada", description="As integrações (Bots, Twitch, YouTube) do servidor sofreram alterações.", color=0x950606, timestamp=discord.utils.utcnow())
        embed.set_footer(text=f"Segurança Ativa {config['nome']}", icon_url=guild.icon.url if guild.icon else None)
        await canal_logs.send(embed=embed)

@bot.event
async def on_automod_rule_create(rule):
    config = obter_config(rule.guild.id)
    if config and (canal_logs := bot.get_channel(config["canal_logs"])):
        embed = discord.Embed(title=f"🛡️ {config['nome']} - Nova Regra de Auto Moderação do Discord", description=f"Regra criada: `{rule.name}`", color=0x950606, timestamp=discord.utils.utcnow())
        embed.set_footer(text=f"Segurança Ativa {config['nome']}", icon_url=rule.guild.icon.url if rule.guild.icon else None)
        await canal_logs.send(embed=embed)

@bot.event
async def on_automod_rule_update(before, after):
    config = obter_config(before.guild.id)
    if config and (canal_logs := bot.get_channel(config["canal_logs"])):
        embed = discord.Embed(title=f"⚙️ {config['nome']} - Regra de Auto Moderação Atualizada", description=f"Regra alterada: `{after.name}`", color=0x950606, timestamp=discord.utils.utcnow())
        embed.set_footer(text=f"Segurança Ativa {config['nome']}", icon_url=before.guild.icon.url if before.guild.icon else None)
        await canal_logs.send(embed=embed)

@bot.event
async def on_automod_rule_delete(rule):
    config = obter_config(rule.guild.id)
    if config and (canal_logs := bot.get_channel(config["canal_logs"])):
        embed = discord.Embed(title=f"🗑️ {config['nome']} - Regra de Auto Moderação Apagada", description=f"A regra `{rule.name}` foi apagada.", color=0x950606, timestamp=discord.utils.utcnow())
        embed.set_footer(text=f"Segurança Ativa {config['nome']}", icon_url=rule.guild.icon.url if rule.guild.icon else None)
        await canal_logs.send(embed=embed)

@bot.event
async def on_automod_action(execution):
    config = obter_config(execution.guild.id)
    if config and (canal_logs := bot.get_channel(config["canal_logs"])):
        embed = discord.Embed(title=f"🚨 {config['nome']} - Auto Moderação do Discord Disparada", description=f"👤 **Membro:** {execution.member.mention if execution.member else 'Desconhecido'}\n📜 **Regra Bloqueada:** `{execution.rule.name}`\n📍 **Canal:** {execution.channel.mention if execution.channel else 'Desconhecido'}\n💬 **Conteúdo Flagrado:** `{execution.matched_content}`", color=0x950606, timestamp=discord.utils.utcnow())
        embed.set_footer(text=f"Segurança Ativa {config['nome']}", icon_url=execution.guild.icon.url if execution.guild.icon else None)
        await canal_logs.send(embed=embed)

# ==================== FIM DOS LOGS ADICIONADOS ====================

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild: 
        return
    config = obter_config(message.guild.id)
    if not config: 
        return

    texto_norm = normalizar_texto(message.content)
    # Remove ABSOLUTAMENTE TODOS OS ESPAÇOS para impedir burla como "c h e c k m y b i o"
    texto_junto = re.sub(r'\s+', '', texto_norm)
    
    # 1. Filtro de Termos Proibidos (Mensagens Fake / Ban Automático)
    for termo in TERMOS_BAN:
        if termo in texto_junto:
            bot.mensagens_ignoradas.add(message.id)
            try: await message.delete()
            except: pass
            
            # Executa banimento e manda para os logs sem exceção de Staff
            await executar_banimento(message.guild, message.author, bot.user, f"Tentativa de golpe (Mensagem Fake): `{termo}`", "Ban (Automático)")
            return

    # 2. Filtro de Palavrões / Xingamentos
    for palavrao in PALAVROES:
        if palavrao in texto_junto:
            bot.mensagens_ignoradas.add(message.id)
            try: await message.delete()
            except: pass
            
            await log_filtro_automod(message, "Palavrão/Xingamento Detectado", message.content)
            return 

    # Coleta URLs de mídias (Anexos + links de imagens na mensagem)
    urls_imagens = []
    if message.attachments:
        for anexo in message.attachments:
            filename_lower = anexo.filename.lower()
            if any(filename_lower.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp", ".gif"]):
                urls_imagens.append(anexo.url)
    
    links_no_texto = re.findall(r'(https?://\S+\.(?:png|jpg|jpeg|webp|gif)(?:\?\S+)?)', message.content)
    urls_imagens.extend(links_no_texto)

    # Pré-download das mídias para cache robusto (Anti-404 nos logs)
    if urls_imagens:
        attachments_data = []
        for idx, url in enumerate(urls_imagens):
            try:
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
                response = requests.get(url, headers=headers, timeout=5)
                if response.status_code == 200:
                    nome_arquivo = f"media_{idx}.png"
                    match = re.search(r'/([^/?#]+\.(?:png|jpg|jpeg|webp|gif))', url, re.IGNORECASE)
                    if match:
                        nome_arquivo = match.group(1)
                    attachments_data.append((response.content, nome_arquivo))
            except:
                pass
        if attachments_data:
            bot.midia_cache[message.id] = attachments_data
            if len(bot.midia_cache) > 300:
                # Remove o mais antigo do cache para evitar vazamento de memória
                bot.midia_cache.pop(next(iter(bot.midia_cache)))

    # 3. Filtro de Imagens Proibidas (Filtro por Hash)
    for url in urls_imagens:
        try:
            # Discord exige cabeçalho de navegador para descarregar mídias de forma confiável
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                # Converte para RGB para garantir que imagens em paleta de cores ou transparentes sejam computadas sem erro
                img = Image.open(BytesIO(response.content)).convert('RGB')
                img_avg_hash = imagehash.average_hash(img)
                img_p_hash = imagehash.phash(img)
                img_d_hash = imagehash.dhash(img)
                
                for hash_bloqueado in IMAGENS_BLOQUEADAS:
                    hash_alvo = imagehash.hex_to_hash(hash_bloqueado)
                    # Com distância Hamming <= 8 em qualquer algoritmo (Average, Perceptual ou Difference Hash)
                    if (img_avg_hash - hash_alvo <= 8) or (img_p_hash - hash_alvo <= 8) or (img_d_hash - hash_alvo <= 8):
                        bot.mensagens_ignoradas.add(message.id)
                        try: await message.delete()
                        except: pass
                        
                        # Executa banimento e envia prova
                        await executar_banimento(message.guild, message.author, bot.user, "Envio de imagem proibida.", "Ban (Automático)", url)
                        return
        except Exception as e:
            print(f"[Aviso Automod] Erro ao processar hash da imagem {url}: {e}")

    # 4. Filtro de Convites/Links Proibidos
    if re.search(r'(discord\.gg/|discord\.com/invite/)', message.content.lower()):
        bot.mensagens_ignoradas.add(message.id)
        try: await message.delete()
        except: pass
        
        try:
            bot.ultimos_mutes.add(message.author.id)
            await message.author.timeout(datetime.timedelta(hours=1), reason="Divulgação Automática.")
            await log_punicao_bonito(message.guild, message.author, bot.user, "Mute 1 Hora (Automático)", "Divulgação de link de convite.")
        except: pass
        return

@bot.event
async def on_message_delete(message):
    if message.author.bot or not message.guild: return
    if message.id in bot.mensagens_ignoradas:
        bot.mensagens_ignoradas.discard(message.id)
        return

    config = obter_config(message.guild.id)
    if config and (canal_logs := bot.get_channel(config["canal_logs"])):
        embed = discord.Embed(title=f"🗑️ {config['nome']} - Mensagem Apagada", color=0x950606, timestamp=discord.utils.utcnow())
        if message.author.display_avatar: embed.set_thumbnail(url=message.author.display_avatar.url)
            
        conteudo = message.content[:1000] if message.content else "Mensagem vazia ou apenas mídia"
        embed.description = f"👤 **Usuário:** {message.author.mention} ({message.author.id})\n💬 **Canal:** {message.channel.mention}\n\n**Conteúdo Original:**\n```{conteudo}```"
        
        # Faz o upload direto dos bytes guardados em cache para o canal de logs (Garante 100% que a mídia apareça)
        arquivos_enviar = []
        if message.id in bot.midia_cache:
            for i, (dados_binarios, nome_arquivo) in enumerate(bot.midia_cache[message.id]):
                file = discord.File(BytesIO(dados_binarios), filename=nome_arquivo)
                arquivos_enviar.append(file)
                # Configura a imagem do embed para usar o arquivo anexado
                embed.set_image(url=f"attachment://{nome_arquivo}")
                break # Mostra a primeira imagem anexada ampliada no embed
            del bot.midia_cache[message.id] # Remove do cache
        
        embed.set_footer(text=f"Segurança Ativa {config['nome']}", icon_url=message.guild.icon.url if message.guild.icon else None)
        
        if arquivos_enviar:
            await canal_logs.send(embed=embed, files=arquivos_enviar)
        else:
            await canal_logs.send(embed=embed)

@bot.event
async def on_message_edit(before, after):
    if before.author.bot or not before.guild or before.content == after.content: return

    config = obter_config(before.guild.id)
    if config and (canal_logs := bot.get_channel(config["canal_logs"])):
        embed = discord.Embed(title=f"📝 {config['nome']} - Mensagem Editada", color=0x950606, timestamp=discord.utils.utcnow())
        if before.author.display_avatar: embed.set_thumbnail(url=before.author.display_avatar.url)

        conteudo_antigo = before.content[:1000] if before.content else "Sem conteúdo"
        conteudo_novo = after.content[:1000] if after.content else "Sem conteúdo"

        embed.description = f"""👤 **Usuário:** {before.author.mention} ({before.author.id})
💬 **Canal:** {before.channel.mention}

**Conteúdo Anterior:**
```{conteudo_antigo}```

**Conteúdo Novo:**
```{conteudo_novo}```"""
        
        embed.set_footer(text=f"Segurança Ativa {config['nome']}", icon_url=before.guild.icon.url if before.guild.icon else None)
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

@bot.tree.command(name="bloquear_imagem", description="Bloqueia uma imagem adicionando seu hash à blacklist.")
@app_commands.default_permissions(administrator=True)
async def bloquear_imagem_slash(interaction: discord.Interaction, imagem: discord.Attachment):
    if not imagem.content_type or not imagem.content_type.startswith("image/"):
        return await interaction.response.send_message("❌ O arquivo precisa ser uma imagem válida.", ephemeral=True)
    
    await interaction.response.defer(ephemeral=True)
    try:
        dados = await imagem.read()
        img = Image.open(BytesIO(dados)).convert("RGB")
        h = str(imagehash.average_hash(img))
        
        if h not in IMAGENS_BLOQUEADAS:
            IMAGENS_BLOQUEADAS.append(h)
            
        embed = discord.Embed(
            title="⛔ IMAGEM REGISTRADA NA BLACKLIST", 
            description=f"A imagem foi computada com sucesso.\nQualquer pessoa que tentar postar sofrerá banimento imediato.\n\n**Hash Gerado:** `{h}`", 
            color=0x950606
        )
        embed.set_footer(text="Segurança Ativa", icon_url=bot.user.display_avatar.url if bot.user.display_avatar else None)
        await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Erro ao computar hash da imagem: {e}", ephemeral=True)

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
        embed = discord.Embed(
            title="🛡️ CENTRAL DE ATENDIMENTO - GHOUL", 
            description=(
                "**Denúncias:**\n"
                "↳ Denúncias, ajuda técnica e revisão de punições.\n\n"
                "**Suporte:**\n"
                "↳ Recorra a uma punição (warn/mute).\n\n"
                "**Dúvidas:**\n"
                "↳ Tire dúvidas sobre a comunidade ou regras do servidor.\n\n"
                "**Exposed:**\n"
                "↳ Falar sobre algum membro que está expondo outro membro.\n\n"
                "**Lembre-se:** Nossa equipe está pronta para investigar e resolver qualquer situação de forma rápida e justa. Sua privacidade será respeitada durante todo o processo!"
            ),
            color=0x950606
        )
        embed.set_image(url=IMAGENS_TICKETS["GHOUL"])
        view = ViewGhoul()
        
    elif painel.value == "kings":
        embed = discord.Embed(title="👑 CENTRAL DE ATENDIMENTO - BLOX KINGS", description="Selecione a categoria correta no menu abaixo para abrir o seu ticket.", color=0x950606)
        embed.set_image(url=IMAGENS_TICKETS["BLOX_KINGS"])
        view = ViewKings()
        
    elif painel.value == "nightware":
        embed = discord.Embed(title="🛍️ CENTRAL DE ATENDIMENTO - NIGHTWARE", description="Selecione uma opção no menu abaixo para abrir seu ticket.", color=0x950606)
        embed.set_image(url=IMAGENS_TICKETS["NIGHTWARE"])
        view = ViewNightware()
        
    elif painel.value == "cod":
        embed = discord.Embed(
            title="TICKET DE COLDAWN", 
            description=(
                "INFORMAMOS QUE A NOVA FUNÇÃO DO SERVIDOR \"GHOUL 👻\"\n"
                "JÁ ESTÁ DISPONÍVEL. PARA PARTICIPAR DO EVENTO\n"
                "\"LEVIATHAN\", É OBRIGATÓRIO ABRIR UM TICKET PARA\n"
                "COMPROVAR QUE NÃO SE ENCONTRA EM PERÍODO DE\n"
                "COOLDOWN. A COMPROVAÇÃO DO COOLDOWN DEVERÁ SER\n"
                "REALIZADA EXCLUSIVA"
            ), 
            color=0x950606
        )
        embed.set_image(url=IMAGENS_TICKETS["COD"])
        embed.set_footer(text="Desenvolvido por Ticket King", icon_url="https://cdn.discordapp.com/attachments/1183819407013707947/1469731813709578417/GHOUL_20260207_132912_0000.png")
        view = ViewValidar()

    await interaction.channel.send(embed=embed, view=view)
    await interaction.response.send_message(f"✅ Painel **{painel.name}** enviado com sucesso!", ephemeral=True)

@bot.event
async def on_ready():
    print(f"✅ Sistema perfeito! {bot.user.name} está online, comandos sincronizados e operando com cor #950606.")

TOKEN = os.getenv('TOKEN')
bot.run(TOKEN)
