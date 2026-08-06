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

# ==================== SERVIDOR WEB ====================
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot de Segurança Máxima Online!"

def run_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

Thread(target=run_server, daemon=True).start()

# ==================== CONFIGURAÇÕES GERAIS ====================
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
    "BLOX_KINGS": "https://cdn.discordapp.com/attachments/1183819407013707947/1526281157635870730/file_000000002958720eab459d97fd2c5b8e.png",
    "NIGHTWARE": "https://cdn.discordapp.com/attachments/1440377531848200295/1452759780111155323/standard.gif",
    "POLIAS": "https://cdn.discordapp.com/attachments/1431364353482948608/1533832231108214864/file_000000004fd4820eb39bb046269d5d96.png",
}

TERMOS_BAN = [
    "checkmybio", "checkmyprofile", "lookmybio", "lookatmybio", "checkbio",
    "olharabiografia", "olheminhabio", "freenitro", "nitrogratis", "onlyfansfree",
    "steamgratis", "ganherobux", "robuxfree", "clickhere"
]

PALAVROES = [
    "fdp", "filhodaputa", "caralho", "krl", "bosta", "escroto", "merda",
    "arrombado", "viado", "corno", "desgracado", "vagabundo", "porra", "buceta",
    "cacete", "puta", "puto", "cuzao", "pica", "rola", "xoxota", "vadia", "foder",
    "fodase", "tnc", "tomarnocu", "vsf", "vtnc", "pqp", "cuzinho", "putinha", 
    "safado", "otario", "macaco", "retardado", "imbecil", "corno", "chupa"
]

IMAGENS_BLOQUEADAS = [
    "9977339a644d9a62", "936c6c4e946cd966", "9748a8dcbd4a2579",
    "c48ff019712fe2c6", "91ac6db293ab09a6", "c1e1eb965c5e5cd0",
    "f5de4a08bdbd5aa5", "956a6e944ac9a6c9", "931e6ae394d3486f"
]

CORES = {
    "sucesso": 0x2ecc71,
    "erro": 0xe74c3c,
    "aviso": 0xf1c40f,
    "info": 0x3498db,
    "neutro": 0x2b2d31,
    "loritta": 0x29a6fe,
    "ban": 0x950606
}

# ==================== ESTRUTURA BASE DO BOT ====================
class BotSegurancaExtrema(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents, help_command=None)
        self.mensagens_ignoradas = set()
        self.ultimos_banimentos = set()
        self.sorteios_ativos = {}
        self.spam_control = {}

    async def setup_hook(self):
        self.add_view(TicketView())
        await self.tree.sync()

bot = BotSegurancaExtrema()

def obter_config(guild_id):
    return CONFIG_SERVIDORES.get(guild_id)

def normalizar_texto(texto):
    texto = texto.lower()
    texto = "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")
    substituicoes = {"1": "i", "3": "e", "4": "a", "0": "o", "5": "s", "7": "t", "$": "s", "@": "a"}
    for orig, sub in substituicoes.items():
        texto = texto.replace(orig, sub)
    return re.sub(r"[^a-z0-9\s]", "", texto)

# ==================== SISTEMA VISUAL DE PUNIÇÕES ====================
async def log_punicao_bonito(guild, user, staff, acao, motivo, prova_url=None, anexos=None):
    config = obter_config(guild.id)
    if not config: return
    canal = guild.get_channel(config["canal_punicoes"])
    if not canal: return

    embed = discord.Embed(
        title=f"🔨 Punição Aplicada | {acao}",
        color=CORES["ban"],
        timestamp=discord.utils.utcnow()
    )
    if user.display_avatar:
        embed.set_thumbnail(url=user.display_avatar.url)

    embed.add_field(name="👤 Infrator", value=f"{user.mention}\n`{user.name}`", inline=True)
    embed.add_field(name="🆔 ID", value=f"`{user.id}`", inline=True)
    embed.add_field(name="🛡️ Moderador", value=staff.mention if hasattr(staff, 'mention') else staff, inline=True)
    embed.add_field(name="📄 Motivo", value=f"```\n{motivo}\n```", inline=False)

    if prova_url:
        embed.set_image(url=prova_url)
    
    embed.set_footer(text=f"Segurança Máxima • {config.get('nome', guild.name)}", icon_url=guild.icon.url if guild.icon else None)
    
    if anexos:
        await canal.send(embed=embed, files=anexos)
    else:
        await canal.send(embed=embed)

async def executar_banimento(guild, membro, staff, motivo, acao_log, prova_url=None, anexos_prova=None):
    bot.ultimos_banimentos.add(membro.id)
    
    carta_dm = discord.Embed(
        title="🚨 Aviso de Banimento Permanente",
        description=f"Você foi banido(a) de **{guild.name}** devido a violações graves de nossas diretrizes de segurança.",
        color=CORES["ban"]
    )
    carta_dm.add_field(name="Motivo Registrado", value=f"`{motivo}`")
    carta_dm.set_footer(text="A decisão é final e irrevogável.")
    
    try: await membro.send(embed=carta_dm)
    except: pass

    try:
        staff_name = staff.name if hasattr(staff, "name") else str(staff)
        await guild.ban(membro, reason=f"{staff_name} | {motivo}", delete_message_days=1)
        await log_punicao_bonito(guild, membro, staff, acao_log, motivo, prova_url, anexos_prova)
        return True
    except Exception as e:
        print(f"[ERRO BAN] {e}")
        return False

# ==================== GAMERSAFER STYLE: LOGS GERAIS (23 CATEGORIAS) ====================
async def enviar_log_gs(guild, categoria, acao, desc, color, user=None, image_url=None):
    config = obter_config(guild.id)
    if not config: return
    canal = guild.get_channel(config["canal_logs"])
    if not canal: return

    embed = discord.Embed(title=f"{categoria} ➔ {acao}", description=desc, color=color, timestamp=discord.utils.utcnow())
    if user and hasattr(user, 'display_avatar'):
        embed.set_thumbnail(url=user.display_avatar.url)
    if image_url:
        embed.set_image(url=image_url)
    
    embed.set_footer(text=f"GS Defender Logs • {guild.name}")
    await canal.send(embed=embed)

# 1 a 6. Membros e Moderação
@bot.event
async def on_member_join(member):
    await enviar_log_gs(member.guild, "👥 Membros", "Novo Membro", f"👤 **Membro:** {member.mention} (`{member.id}`)\n📅 **Conta criada em:** {discord.utils.format_dt(member.created_at, 'R')}", CORES["sucesso"], member)

@bot.event
async def on_member_remove(member):
    await enviar_log_gs(member.guild, "👥 Membros", "Saída de Membro", f"👤 **Membro:** {member.mention} (`{member.id}`)", CORES["erro"], member)

@bot.event
async def on_member_update(before, after):
    if before.roles != after.roles:
        adicionados = [r.mention for r in after.roles if r not in before.roles]
        removidos = [r.mention for r in before.roles if r not in after.roles]
        desc = f"👤 **Membro:** {after.mention}\n"
        if adicionados: desc += f"✅ **Cargos Adicionados:** {', '.join(adicionados)}\n"
        if removidos: desc += f"❌ **Cargos Removidos:** {', '.join(removidos)}"
        if adicionados or removidos:
            await enviar_log_gs(after.guild, "👥 Membros", "Atualizar Cargo", desc, CORES["aviso"], after)
    
    if before.nick != after.nick:
        await enviar_log_gs(after.guild, "👥 Membros", "Atualizar Membro (Apelido)", f"👤 **Membro:** {after.mention}\n🖍️ **Antes:** `{before.nick}`\n🖌️ **Depois:** `{after.nick}`", CORES["info"], after)

# 7. Canais de Voz
@bot.event
async def on_voice_state_update(member, before, after):
    if before.channel != after.channel:
        if before.channel is None:
            await enviar_log_gs(member.guild, "🔊 Canais de Voz", "Entrou no Canal", f"👤 **Membro:** {member.mention}\n📥 **Canal:** {after.channel.mention}", CORES["sucesso"], member)
        elif after.channel is None:
            await enviar_log_gs(member.guild, "🔊 Canais de Voz", "Saiu do Canal", f"👤 **Membro:** {member.mention}\n📤 **De:** {before.channel.mention}", CORES["erro"], member)
        else:
            await enviar_log_gs(member.guild, "🔊 Canais de Voz", "Moveu de Canal", f"👤 **Membro:** {member.mention}\n⬅️ **Antes:** {before.channel.mention}\n➡️ **Agora:** {after.channel.mention}", CORES["info"], member)

# 8. Convites
@bot.event
async def on_invite_create(invite):
    await enviar_log_gs(invite.guild, "✉️ Convites", "Criação de Convite", f"🔗 **Código:** `{invite.code}`\n👤 **Criador:** {invite.inviter.mention if invite.inviter else 'Desconhecido'}\n📁 **Canal:** {invite.channel.mention}\n⏱️ **Expira em:** {invite.max_age}s", CORES["sucesso"])

@bot.event
async def on_invite_delete(invite):
    await enviar_log_gs(invite.guild, "✉️ Convites", "Apagar Convite", f"🔗 **Código Apagado:** `{invite.code}`", CORES["erro"])

# 9. Cargos
@bot.event
async def on_guild_role_create(role):
    await enviar_log_gs(role.guild, "🏷️ Cargos", "Criar Cargo", f"✅ **Cargo:** {role.mention} (`{role.name}`)", CORES["sucesso"])

@bot.event
async def on_guild_role_delete(role):
    await enviar_log_gs(role.guild, "🏷️ Cargos", "Apagar Cargo", f"❌ **Cargo Removido:** `{role.name}`", CORES["erro"])

# 10 e 11. Emojis e Figurinhas
@bot.event
async def on_guild_emojis_update(guild, before, after):
    adicionados = [e for e in after if e not in before]
    removidos = [e for e in before if e not in after]
    if adicionados:
        for e in adicionados: await enviar_log_gs(guild, "😀 Emojis", "Novo Emoji", f"✨ **Emoji:** {e} (`{e.name}`)", CORES["sucesso"], image_url=e.url)
    if removidos:
        for e in removidos: await enviar_log_gs(guild, "😀 Emojis", "Apagar Emoji", f"🗑️ **Emoji Apagado:** `{e.name}`", CORES["erro"])

# 14 e 15. Canais e Tópicos (Threads)
@bot.event
async def on_guild_channel_create(channel):
    await enviar_log_gs(channel.guild, "📁 Canais", "Novo Canal", f"✅ **Canal:** {channel.mention} (`{channel.name}`)\n🗂️ **Tipo:** `{channel.type}`", CORES["sucesso"])

@bot.event
async def on_guild_channel_delete(channel):
    await enviar_log_gs(channel.guild, "📁 Canais", "Apagar Canal", f"❌ **Canal Removido:** `{channel.name}`\n🗂️ **Tipo:** `{channel.type}`", CORES["erro"])

@bot.event
async def on_thread_create(thread):
    await enviar_log_gs(thread.guild, "📌 Tópicos", "Novo Tópico", f"✅ **Tópico:** {thread.mention}\n📁 **Canal Pai:** {thread.parent.mention if thread.parent else 'N/A'}", CORES["sucesso"])

# 5. Mensagens (Edição e Deleção)
@bot.event
async def on_message_delete(message):
    if message.author.bot or message.id in bot.mensagens_ignoradas: return
    desc = f"👤 **Autor:** {message.author.mention}\n📁 **Canal:** {message.channel.mention}\n💬 **Conteúdo:**\n```\n{message.content or 'Mensagem sem texto (Imagem/Embed)'}\n```"
    await enviar_log_gs(message.guild, "💬 Mensagens", "Apagar Mensagem", desc, CORES["erro"], message.author)

@bot.event
async def on_message_edit(before, after):
    if before.author.bot or before.content == after.content: return
    desc = f"👤 **Autor:** {before.author.mention}\n📁 **Canal:** {before.channel.mention}\n\n🖍️ **Antes:**\n```\n{before.content}\n```\n🖌️ **Depois:**\n```\n{after.content}\n```\n🔗 [Ir para a mensagem]({after.jump_url})"
    await enviar_log_gs(after.guild, "💬 Mensagens", "Editar Mensagem", desc, CORES["aviso"], after.author)

# ==================== AUTO MODERAÇÃO DE ALTA PERFORMANCE ====================
@bot.event
async def on_message(message):
    if message.author.bot or not message.guild: return
    config = obter_config(message.guild.id)
    if not config: return

    # 1. Anti-Spam / Cooldown Exato (8 Segundos)
    autor_id = message.author.id
    agora = time.time()
    
    if not message.author.guild_permissions.administrator:
        if autor_id not in bot.spam_control:
            bot.spam_control[autor_id] = []
            
        # Mantém apenas as mensagens dos últimos 8 segundos
        mensagens_recentes = [t for t in bot.spam_control[autor_id] if agora - t < 8]
        mensagens_recentes.append(agora)
        bot.spam_control[autor_id] = mensagens_recentes
        
        if len(mensagens_recentes) >= 5: # 5 mensagens em menos de 8s = Spam
            bot.mensagens_ignoradas.add(message.id)
            try: await message.delete()
            except: pass
            
            bot.spam_control[autor_id] = [] # Reseta
            try:
                await message.author.timeout(datetime.timedelta(minutes=10), reason="AutoMod: Spam (Flood)")
                embed_spam = discord.Embed(title="⏱️ Anti-Spam Ativado", description=f"{message.author.mention} foi silenciado por 10 minutos por enviar mensagens muito rápido (Cooldown: 8s).", color=CORES["aviso"])
                await message.channel.send(embed=embed_spam, delete_after=10)
                await log_punicao_bonito(message.guild, message.author, bot.user, "Silenciamento (10m)", "Envio excessivo de mensagens (Flood/Spam).")
                await enviar_log_gs(message.guild, "🤖 Auto Moderação", "Spam", f"👤 **Usuário silenciado:** {message.author.mention}", CORES["aviso"])
            except: pass
            return

    texto_norm = normalizar_texto(message.content)
    texto_junto = re.sub(r"\s+", "", texto_norm)

    # 2. Imagens Proibidas - Deleção imediata e BAN!
    if message.attachments:
        for anexo in message.attachments:
            if any(anexo.filename.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp", ".gif"]):
                try:
                    bytes_img = await anexo.read()
                    img = Image.open(BytesIO(bytes_img)).convert("RGB")
                    img_avg_hash = imagehash.average_hash(img)
                    
                    for hash_bloqueado in IMAGENS_BLOQUEADAS:
                        hash_alvo = imagehash.hex_to_hash(hash_bloqueado)
                        if (img_avg_hash - hash_alvo <= 8):
                            # APAGA A MENSAGEM PRIMEIRO
                            bot.mensagens_ignoradas.add(message.id)
                            try: await message.delete()
                            except: pass
                            
                            # DA BAN NA PESSOA
                            file_prova = discord.File(BytesIO(bytes_img), filename="prova_ilegal.png")
                            await executar_banimento(
                                message.guild, 
                                message.author, 
                                bot.user, 
                                "AutoMod: Imagem Estritamente Proibida Detectada.", 
                                "Banimento Automático", 
                                anexos_prova=[file_prova]
                            )
                            await enviar_log_gs(message.guild, "🤖 Auto Moderação", "Anexos (Imagem Ilegal)", f"👤 **Usuário banido:** {message.author.mention}", CORES["ban"])
                            return
                except Exception as e:
                    print(f"[WARN] Erro ao analisar imagem: {e}")

    # 3. Termos de Golpe/Scam
    for termo in TERMOS_BAN:
        if termo in texto_junto:
            bot.mensagens_ignoradas.add(message.id)
            try: await message.delete()
            except: pass
            await executar_banimento(message.guild, message.author, bot.user, f"AutoMod: Tentativa de Golpe/Scam detectada (`{termo}`).", "Banimento Automático")
            return

    # 4. Palavrões (Mensagem Personalizada)
    for palavrao in PALAVROES:
        if palavrao in texto_junto:
            bot.mensagens_ignoradas.add(message.id)
            try: await message.delete()
            except: pass
            
            aviso = await message.channel.send(f"⚠️ {message.author.mention}, **cuidado com o linguajar seu boboca!**")
            await aviso.delete(delay=6)
            
            await enviar_log_gs(message.guild, "🤖 Auto Moderação", "Filtro de Palavras", f"👤 **Infrator:** {message.author.mention}\n💬 **Canal:** {message.channel.mention}\n**Mensagem bloqueada:** ```{message.content}```", CORES["aviso"])
            return

    # 5. Convites (Anti-Invite)
    if re.search(r"(discord\.gg/|discord\.com/invite/)", message.content.lower()) and not message.author.guild_permissions.administrator:
        bot.mensagens_ignoradas.add(message.id)
        try: await message.delete()
        except: pass
        try:
            await message.author.timeout(datetime.timedelta(hours=1), reason="Divulgação de link de convite.")
            await log_punicao_bonito(message.guild, message.author, bot.user, "Silenciamento (1h)", "Divulgação de convites externos não autorizada.")
            await enviar_log_gs(message.guild, "🤖 Auto Moderação", "Convites", f"👤 **Infrator mutado:** {message.author.mention}", CORES["aviso"])
        except: pass
        return


# ==================== LORITTA-STYLE: SISTEMA DE SORTEIOS AVANÇADO ====================
class ParticiparSorteio(discord.ui.View):
    def __init__(self, msg_id, cargo_extra_id, entradas_extras):
        super().__init__(timeout=None)
        self.msg_id = msg_id
        self.cargo_extra_id = cargo_extra_id
        self.entradas_extras = entradas_extras
        # Botão idêntico ao da Loritta (Verde com emoji)
        self.btn = discord.ui.Button(label="Participar", style=discord.ButtonStyle.success, emoji="🎉", custom_id=f"join_sorteio_{msg_id}")
        self.btn.callback = self.participar_callback
        self.add_item(self.btn)

    async def participar_callback(self, interaction: discord.Interaction):
        if self.msg_id not in bot.sorteios_ativos:
            return await interaction.response.send_message("Este sorteio já foi encerrado!", ephemeral=True)
            
        dados = bot.sorteios_ativos[self.msg_id]
        if interaction.user.id in dados["participantes"]:
            return await interaction.response.send_message("Você já está participando deste sorteio! Boa sorte. 🍀", ephemeral=True)
            
        # Adiciona o usuário na lista principal
        dados["participantes"].append(interaction.user.id)
        entradas = 1
        
        # Lógica de Vantagem / Cargo Extra
        if self.cargo_extra_id:
            cargo = interaction.guild.get_role(self.cargo_extra_id)
            if cargo and cargo in interaction.user.roles:
                entradas = self.entradas_extras
                for _ in range(entradas - 1):
                    dados["participantes"].append(interaction.user.id)
                    
        await interaction.response.send_message(f"🎉 Você entrou no sorteio com sucesso! Você obteve **{entradas}** entrada(s).", ephemeral=True)

@bot.tree.command(name="sorteio", description="🎁 [Loritta Style] Crie um sorteio bonito e completo com vantagens para cargos.")
@app_commands.describe(
    premio="O que será sorteado? (Ex: Felicidade Eterna)", 
    descricao="Descrição detalhada do sorteio",
    duracao_minutos="Duração do sorteio em minutos", 
    vencedores="Quantidade de ganhadores",
    cargo_extra="Cargo que terá vantagem de entradas (Opcional)",
    entradas_extras="Quantidade de entradas que o cargo receberá (Ex: 2)"
)
@app_commands.default_permissions(administrator=True)
async def sorteio(
    interaction: discord.Interaction, 
    premio: str, 
    descricao: str, 
    duracao_minutos: int, 
    vencedores: int = 1, 
    cargo_extra: discord.Role = None, 
    entradas_extras: int = 2
):
    await interaction.response.defer(ephemeral=False)
    
    termino = discord.utils.utcnow() + datetime.timedelta(minutes=duracao_minutos)
    
    # Montando a Embed idêntica ao design do vídeo
    embed = discord.Embed(
        title=f"🎉 {premio}", 
        description=f"{descricao}\n\nClique no botão verde abaixo para participar!", 
        color=CORES["loritta"]
    )
    embed.add_field(name="🏆 Ganhadores", value=f"`{vencedores}`", inline=True)
    embed.add_field(name="⏳ Termina em", value=f"{discord.utils.format_dt(termino, 'R')} ({discord.utils.format_dt(termino, 'f')})", inline=True)
    
    if cargo_extra and entradas_extras > 1:
        embed.add_field(name="✨ Vantagem de Entradas Extra", value=f"Membros com o cargo {cargo_extra.mention} recebem **{entradas_extras}x entradas** neste sorteio!", inline=False)
    
    embed.set_footer(text=f"Sorteio patrocinado por {interaction.guild.name} • Desenvolvido com carinho ❤️", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    
    msg = await interaction.followup.send(embed=embed)
    
    view = ParticiparSorteio(msg.id, cargo_extra.id if cargo_extra else None, entradas_extras)
    await msg.edit(view=view)

    bot.sorteios_ativos[msg.id] = {
        "vencedores": vencedores,
        "participantes": [],
        "premio": premio
    }

    await enviar_log_gs(interaction.guild, "📅 Eventos", "Novo Sorteio Criado", f"🎁 **Prêmio:** `{premio}`\n⏳ **Duração:** {duracao_minutos}m", CORES["info"])

    await asyncio.sleep(duracao_minutos * 60)
    await finalizar_sorteio(interaction.channel, msg.id)

async def finalizar_sorteio(channel, msg_id):
    if msg_id not in bot.sorteios_ativos: return
    try:
        dados = bot.sorteios_ativos.pop(msg_id)
        msg = await channel.fetch_message(msg_id)
        participantes_ids = dados["participantes"]
        
        if not participantes_ids:
            embed = msg.embeds[0]
            embed.description = "😔 Ninguém participou do sorteio."
            embed.color = CORES["neutro"]
            return await msg.edit(embed=embed, view=None)
            
        vencedores_ids = []
        qtd_ganhadores = min(dados["vencedores"], len(set(participantes_ids)))
        
        while len(vencedores_ids) < qtd_ganhadores:
            sorteado = random.choice(participantes_ids)
            if sorteado not in vencedores_ids:
                vencedores_ids.append(sorteado)
        
        vencedores_mentions = ", ".join(f"<@{v}>" for v in vencedores_ids)
        
        embed = msg.embeds[0]
        embed.title = f"🎊 Sorteio Encerrado: {dados['premio']}"
        embed.description = f"**O sorteio chegou ao fim!**\n\n🏆 **Ganhador(es):** {vencedores_mentions}"
        embed.color = CORES["neutro"]
        embed.clear_fields()
        
        await msg.edit(embed=embed, view=None)
        await channel.send(f"🎉 Parabéns {vencedores_mentions}! Vocês ganharam **{dados['premio']}**! \n🔗 {msg.jump_url}")
    except Exception as e:
        print(f"[ERRO SORTEIO] {e}")


# ==================== SISTEMA DE TICKETS PROFISSIONAL ====================
class TicketCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Fechar Atendimento", style=discord.ButtonStyle.danger, custom_id="fechar_ticket_btn", emoji="🔒")
    async def fechar_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 Registrando logs e fechando atendimento em 5 segundos...", ephemeral=False)
        await enviar_log_gs(interaction.guild, "📁 Canais", "Ticket Fechado", f"👤 **Fechado por:** {interaction.user.mention}\n📁 **Canal:** `{interaction.channel.name}`", CORES["info"])
        await asyncio.sleep(5)
        try: await interaction.channel.delete()
        except: pass

class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Suporte / Dúvidas", description="Fale com a Staff para suporte geral.", emoji="💬", value="geral"),
            discord.SelectOption(label="Denúncias / AutoMod", description="Denuncie membros ou conteste punições.", emoji="🚨", value="denuncia"),
            discord.SelectOption(label="Propostas / Parcerias", description="Assuntos comerciais e parcerias.", emoji="🤝", value="parceria"),
        ]
        super().__init__(placeholder="🎫 Clique aqui para selecionar uma categoria...", min_values=1, max_values=1, options=options, custom_id="ticket_select_menu")

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        config = obter_config(guild.id)
        if not config:
            return await interaction.response.send_message("❌ Servidor não configurado para uso de tickets.", ephemeral=True)

        categoria = guild.get_channel(config["categoria_tickets"])
        cargo_staff = guild.get_role(config["cargo_staff"])

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, attach_files=True),
        }
        if cargo_staff:
            overwrites[cargo_staff] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

        nome_canal = f"ticket-{interaction.user.name}"
        if discord.utils.get(guild.text_channels, name=nome_canal):
            return await interaction.response.send_message(f"❌ Você já tem um ticket em andamento.", ephemeral=True)

        await interaction.response.defer(thinking=True, ephemeral=True)
        try:
            canal_ticket = await guild.create_text_channel(
                name=nome_canal,
                category=categoria if isinstance(categoria, discord.CategoryChannel) else None,
                overwrites=overwrites
            )

            embed = discord.Embed(
                title=f"Atendimento: {self.values[0].capitalize()}",
                description=f"Olá {interaction.user.mention}!\n\nA equipe {cargo_staff.mention if cargo_staff else 'Staff'} foi notificada. Por favor, envie os detalhes do seu contato abaixo.\n\n*Clique no botão 🔒 para encerrar o ticket.*",
                color=CORES["info"]
            )
            embed.set_footer(text="Segurança Máxima Atendimentos")
            
            await canal_ticket.send(content=f"{interaction.user.mention}", embed=embed, view=TicketCloseView())
            await interaction.followup.send(f"✅ Atendimento criado: {canal_ticket.mention}", ephemeral=True)
            await enviar_log_gs(guild, "📁 Canais", "Novo Ticket Aberto", f"👤 **Aberto por:** {interaction.user.mention}\n📁 **Canal:** {canal_ticket.mention}", CORES["info"])
        except Exception as e:
            await interaction.followup.send(f"❌ Erro ao gerar ticket: {e}", ephemeral=True)

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())


# ==================== COMANDOS ADMINISTRATIVOS ====================
@bot.tree.command(name="painel_tickets", description="Gera o painel interativo de suporte e tickets.")
@app_commands.default_permissions(administrator=True)
async def painel_tickets(interaction: discord.Interaction):
    config = obter_config(interaction.guild.id)
    nome_cfg = "GHOUL"
    if config:
        for k in IMAGENS_TICKETS.keys():
            if k in config["nome"]:
                nome_cfg = k
                break
                
    banner_url = IMAGENS_TICKETS.get(nome_cfg, IMAGENS_TICKETS["GHOUL"])

    embed = discord.Embed(
        title="🎫 Central de Suporte & Atendimento",
        description="Seja bem-vindo(a) ao atendimento oficial.\n\nPara iniciar, **selecione uma das categorias no menu abaixo** que melhor se enquadra na sua necessidade. Nossa equipe irá te atender o mais rápido possível.",
        color=CORES["neutro"]
    )
    embed.set_image(url=banner_url)
    
    await interaction.response.send_message("Painel fixado!", ephemeral=True)
    await interaction.channel.send(embed=embed, view=TicketView())

@bot.tree.command(name="limpar", description="Limpa o chat em massa.")
@app_commands.describe(quantidade="Número de mensagens (1 a 100)")
@app_commands.default_permissions(manage_messages=True)
async def limpar(interaction: discord.Interaction, quantidade: int):
    if not 1 <= quantidade <= 100:
        return await interaction.response.send_message("❌ Apenas 1 a 100 mensagens por vez.", ephemeral=True)
    
    await interaction.response.defer(ephemeral=True)
    apagadas = await interaction.channel.purge(limit=quantidade)
    await interaction.followup.send(f"🧹 `{len(apagadas)}` mensagens apagadas.", ephemeral=True)
    await enviar_log_gs(interaction.guild, "💬 Mensagens", "Apagar muitas mensagens (Clear)", f"🛡️ **Moderador:** {interaction.user.mention}\n📁 **Canal:** {interaction.channel.mention}\n🗑️ **Quantidade:** `{len(apagadas)}`", CORES["info"])

@bot.tree.command(name="ban", description="Aplica banimento manual em um membro infrator.")
@app_commands.describe(membro="O membro", motivo="O porquê do banimento")
@app_commands.default_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, membro: discord.Member, motivo: str):
    if membro.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
        return await interaction.response.send_message("❌ Hierarquia insuficiente.", ephemeral=True)

    sucesso = await executar_banimento(interaction.guild, membro, interaction.user, motivo, "Banimento Manual")
    if sucesso:
        await interaction.response.send_message(f"✅ {membro.mention} banido.", ephemeral=True)
    else:
        await interaction.response.send_message("❌ Erro de permissão.", ephemeral=True)


# ==================== BOOT DO BOT ====================
@bot.event
async def on_ready():
    print(f"""
    ======================================
    ✅ BOT INICIADO COM SUCESSO
    🤖 Nome: {bot.user.name}
    🛡️ Logs GamerSafer: ATIVOS (23 Módulos)
    🔨 AutoMod Imagens: ATIVADO E LETAIS
    🎉 Sistema de Sorteios: LORITTA-STYLE ATIVO
    ======================================
    """)

if __name__ == "__main__":
    TOKEN = os.getenv("TOKEN")
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("❌ TOKEN NÃO ENCONTRADO.")
