import asyncio
import datetime
import os
import re
import unicodedata
import random
from io import BytesIO
from threading import Thread

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Modal, TextInput
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

    async def setup_hook(self):
        self.add_view(ViewGhoul())
        self.add_view(ViewKings())
        self.add_view(ViewNightware())
        self.add_view(ViewPolias())
        self.add_view(ViewValidar())
        # ViewFechar(Ticket) não precisa ser adicionada aqui pois criamos dinamicamente
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

# ==================== SISTEMA DE PUNIÇÕES E LOGS ====================
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
        f"Você foi banido(a) por violar as nossas regras.\n\n"
        f"**Motivo:** {motivo}\n\n"
        f"A decisão de banir permanece final.\n\n"
        f"*Equipe de Moderação - {nome_servidor}*"
    )
    try: await membro.send(carta_dm)
    except: pass

    try:
        staff_name = staff.name if hasattr(staff, "name") else str(staff)
        await guild.ban(membro, reason=f"{staff_name} | {motivo}")
        await log_punicao_bonito(guild, membro, staff, acao_log, motivo, prova_url, anexos_prova)
        return True
    except Exception as e:
        print(f"[ERRO PERMISSÃO BAN] {e}")
        return False

# ==================== TODOS OS LOGS AVANÇADOS ====================
async def enviar_log_avancado(guild, title, description, user=None, image_url=None, files=None):
    config = obter_config(guild.id)
    if not config: return
    canal = guild.get_channel(config["canal_logs"])
    if not canal: return

    embed = discord.Embed(title=title, description=description, color=0x950606, timestamp=discord.utils.utcnow())
    if user and user.display_avatar:
        embed.set_thumbnail(url=user.display_avatar.url)
    if image_url:
        embed.set_image(url=image_url)
    embed.set_footer(text=f"Segurança Ativa {config['nome']}", icon_url=guild.icon.url if guild.icon else None)
    
    if files: await canal.send(embed=embed, files=files)
    else: await canal.send(embed=embed)

@bot.event
async def on_voice_state_update(member, before, after):
    # Log: Entrou, Saiu ou Moveu de Call
    if before.channel != after.channel:
        if before.channel is None:
            await enviar_log_avancado(member.guild, "🔊 Membro entrou na Call/Palco", f"👤 **Membro:** {member.mention}\n📥 **Entrou em:** {after.channel.mention}", member)
        elif after.channel is None:
            # Check if disconnected by staff
            await asyncio.sleep(1)
            desconectado_por = None
            async for entry in member.guild.audit_logs(limit=3, action=discord.AuditLogAction.member_disconnect):
                if entry.target.id == member.id and (discord.utils.utcnow() - entry.created_at).total_seconds() < 10:
                    desconectado_por = entry.user
                    break
            
            if desconectado_por:
                await enviar_log_avancado(member.guild, "🚫 Membro Desconectado da Call", f"👤 **Membro:** {member.mention}\n📤 **Canal:** {before.channel.mention}\n🛡️ **Staff responsável:** {desconectado_por.mention}", member)
            else:
                await enviar_log_avancado(member.guild, "🔇 Membro saiu da Call/Palco", f"👤 **Membro:** {member.mention}\n📤 **Saiu de:** {before.channel.mention}", member)
        else:
            await enviar_log_avancado(member.guild, "🔄 Membro moveu de Call", f"👤 **Membro:** {member.mention}\n⬅️ **Antes:** {before.channel.mention}\n➡️ **Agora:** {after.channel.mention}", member)

@bot.event
async def on_user_update(before, after):
    # Log: Avatar update
    if before.avatar != after.avatar:
        for guild in bot.guilds:
            if guild.get_member(after.id) and obter_config(guild.id):
                desc = f"👤 **Usuário:** {after.mention}\nO usuário alterou sua foto de perfil."
                embed = discord.Embed(title="🖼️ Alteração de Avatar", description=desc, color=0x950606)
                if before.avatar: embed.set_thumbnail(url=before.avatar.url) # Foto antiga na thumbnail
                if after.avatar: embed.set_image(url=after.avatar.url) # Foto nova maior
                
                canal_logs = guild.get_channel(obter_config(guild.id)["canal_logs"])
                if canal_logs: await canal_logs.send(embed=embed)

@bot.event
async def on_member_update(before, after):
    config = obter_config(before.guild.id)
    if not config: return
    
    # Log: Cargos Adicionados ou Removidos
    if before.roles != after.roles:
        adicionados = [r for r in after.roles if r not in before.roles]
        removidos = [r for r in before.roles if r not in after.roles]
        
        await asyncio.sleep(1)
        staff = None
        async for entry in before.guild.audit_logs(limit=3, action=discord.AuditLogAction.member_role_update):
            if entry.target.id == after.id and (discord.utils.utcnow() - entry.created_at).total_seconds() < 10:
                staff = entry.user
                break
                
        if adicionados:
            cargos_str = ", ".join([r.mention for r in adicionados])
            desc = f"👤 **Membro:** {after.mention}\n➕ **Cargo(s) Adicionado(s):** {cargos_str}"
            if staff: desc += f"\n🛡️ **Adicionado por:** {staff.mention}"
            await enviar_log_avancado(before.guild, "🔰 Cargos Atualizados (Adição)", desc, after)
            
        if removidos:
            cargos_str = ", ".join([r.mention for r in removidos])
            desc = f"👤 **Membro:** {after.mention}\n➖ **Cargo(s) Removido(s):** {cargos_str}"
            if staff: desc += f"\n🛡️ **Removido por:** {staff.mention}"
            await enviar_log_avancado(before.guild, "🔰 Cargos Atualizados (Remoção)", desc, after)

    # Log: Timeout
    if before.timed_out_until != after.timed_out_until:
        if after.id in bot.ultimos_mutes: bot.ultimos_mutes.discard(after.id); return
        await asyncio.sleep(2)
        if after.timed_out_until is not None:
            async for entry in before.guild.audit_logs(limit=5, action=discord.AuditLogAction.member_update):
                if entry.target.id == after.id and hasattr(entry.after, "timed_out_until"):
                    tempo = after.timed_out_until - discord.utils.utcnow()
                    minutos = max(1, int(tempo.total_seconds() / 60))
                    await log_punicao_bonito(before.guild, after, entry.user, f"Mute ({minutos} mins)", entry.reason or "Sem motivo")
                    return
        elif after.timed_out_until is None:
            async for entry in before.guild.audit_logs(limit=5, action=discord.AuditLogAction.member_update):
                if entry.target.id == after.id and not hasattr(entry.after, "timed_out_until"):
                    await log_punicao_bonito(before.guild, after, entry.user, "Desmutado", entry.reason or "Sem motivo")
                    return

@bot.event
async def on_member_join(member):
    await enviar_log_avancado(member.guild, "📥 Membro Entrou", f"👤 **Membro:** {member.mention} ({member.id})\nO usuário acaba de se juntar ao servidor.", member)

@bot.event
async def on_member_remove(member):
    await enviar_log_avancado(member.guild, "📤 Membro Saiu", f"👤 **Membro:** {member.mention} ({member.id})\nO usuário deixou o servidor.", member)


@bot.event
async def on_bulk_message_delete(messages):
    if not messages: return
    guild = messages[0].guild
    await enviar_log_avancado(guild, "🧹 Limpeza de Mensagens em Massa", f"💬 **Canal:** {messages[0].channel.mention}\n🗑️ **Quantidade apagada:** `{len(messages)}` mensagens.")


# ==================== SISTEMA DE TICKETS COM REIVINDICAÇÃO ====================
class ViewTicket(discord.ui.View):
    def __init__(self, staff_role_id=None):
        super().__init__(timeout=None)
        self.staff_role_id = staff_role_id

    @discord.ui.button(label="Reivindicar", style=discord.ButtonStyle.success, emoji="🙋", custom_id="btn_reivindicar")
    async def reivindicar(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Apenas staff pode reivindicar
        if self.staff_role_id and not any(r.id == self.staff_role_id for r in interaction.user.roles) and not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Você não tem permissão para reivindicar este ticket.", ephemeral=True)
        
        button.disabled = True
        button.label = f"Reivindicado por {interaction.user.display_name}"
        await interaction.response.edit_message(view=self)
        await interaction.channel.send(f"✅ Ticket reivindicado por {interaction.user.mention}! Apenas ele(a) e os administradores farão o atendimento agora.")

    @discord.ui.button(label="Fechar Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="btn_fechar")
    async def fechar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 Fechando canal em 5 segundos...", ephemeral=True)
        await asyncio.sleep(5)
        try: await interaction.channel.delete()
        except: pass

async def criar_canal_ticket(interaction: discord.Interaction, setor: str, cat_id=None, role_id=None):
    config = obter_config(interaction.guild.id)
    if not config and not cat_id: return
    if interaction.response.is_done(): return
    
    categoria_id = cat_id or config["categoria_tickets"]
    cargo_id = role_id or config["cargo_staff"]
    
    categoria = discord.utils.get(interaction.guild.categories, id=int(categoria_id))
    cargo_staff = interaction.guild.get_role(int(cargo_id))

    overwrites = {
        interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
        interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True),
        interaction.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
    }
    if cargo_staff:
        overwrites[cargo_staff] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

    canal = await interaction.guild.create_text_channel(
        name=f"ticket-{interaction.user.name}",
        category=categoria,
        overwrites=overwrites
    )

    embed = discord.Embed(
        title="🚨 Ticket Criado",
        description=f"Olá {interaction.user.mention},\n\nSeu ticket para **{setor.upper()}** foi aberto com sucesso!\nDescreva o que precisa.",
        color=0x950606
    )
    await canal.send(content=f"{interaction.user.mention} {cargo_staff.mention if cargo_staff else ''}", embed=embed, view=ViewTicket(staff_role_id=int(cargo_id)))
    await interaction.response.send_message(f"✅ Ticket criado em {canal.mention}!", ephemeral=True)


# ==================== FILTRO AUTOMOD (Forte) ====================
@bot.event
async def on_message(message):
    if message.author.bot or not message.guild: return
    config = obter_config(message.guild.id)
    if not config: return

    texto_norm = normalizar_texto(message.content)
    texto_junto = re.sub(r"\s+", "", texto_norm)

    # Cache imediato de anexos para o on_message_delete
    if message.attachments:
        dados_anexos = []
        for anexo in message.attachments:
            if any(anexo.filename.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp", ".gif"]):
                try:
                    bytes_img = await anexo.read()
                    dados_anexos.append((bytes_img, anexo.filename))
                except: pass
        if dados_anexos:
            bot.midia_cache[message.id] = dados_anexos
            if len(bot.midia_cache) > 200: bot.midia_cache.pop(next(iter(bot.midia_cache)))

    # 1. Filtro Termos
    for termo in TERMOS_BAN:
        if termo in texto_junto:
            bot.mensagens_ignoradas.add(message.id)
            try: await message.delete()
            except: pass
            await executar_banimento(message.guild, message.author, bot.user, f"Golpe (Mensagem Fake): `{termo}`", "Ban (Automático)")
            return

    # 2. Palavrões
    for palavrao in PALAVROES:
        if palavrao in texto_junto:
            bot.mensagens_ignoradas.add(message.id)
            try: await message.delete()
            except: pass
            await message.channel.send(f"{message.author.mention} cuidado com o linguajar seu boboca!", delete_after=5)
            await enviar_log_avancado(message.guild, "🛡️ Filtro Automático - Palavrão", f"👤 **Usuário:** {message.author.mention}\n💬 **Canal:** {message.channel.mention}\n**Mensagem Deletada:**\n```{message.content}```")
            return

    # 3. Imagens Proibidas
    if message.id in bot.midia_cache:
        for bytes_img, nome_arq in bot.midia_cache[message.id]:
            try:
                img = Image.open(BytesIO(bytes_img)).convert("RGB")
                img_avg_hash = imagehash.average_hash(img)
                
                for hash_bloqueado in IMAGENS_BLOQUEADAS:
                    hash_alvo = imagehash.hex_to_hash(hash_bloqueado)
                    if (img_avg_hash - hash_alvo <= 8):
                        bot.mensagens_ignoradas.add(message.id)
                        try: await message.delete()
                        except: pass
                        
                        file_prova = discord.File(BytesIO(bytes_img), filename="prova.png")
                        await executar_banimento(message.guild, message.author, bot.user, "Envio de imagem proibida.", "Ban (Automático)", anexos_prova=[file_prova])
                        return
            except Exception as e:
                print(f"Erro hash: {e}")

    # 4. Convites
    if re.search(r"(discord\.gg/|discord\.com/invite/)", message.content.lower()):
        bot.mensagens_ignoradas.add(message.id)
        try: await message.delete()
        except: pass
        bot.ultimos_mutes.add(message.author.id)
        try:
            await message.author.timeout(datetime.timedelta(hours=1), reason="Divulgação Automática.")
            await log_punicao_bonito(message.guild, message.author, bot.user, "Mute 1 Hora", "Divulgação de link de convite.")
        except: pass
        return

@bot.event
async def on_message_delete(message):
    if message.author.bot or not message.guild: return
    if message.id in bot.mensagens_ignoradas:
        bot.mensagens_ignoradas.discard(message.id)
        return

    conteudo = message.content[:1000] if message.content else "Mensagem vazia ou contendo apenas mídia."
    desc = f"👤 **Usuário:** {message.author.mention} ({message.author.id})\n💬 **Canal:** {message.channel.mention}\n\n**Conteúdo:**\n```{conteudo}```"
    
    arquivos = []
    if message.id in bot.midia_cache:
        for bytes_img, nome_arq in bot.midia_cache[message.id]:
            arquivos.append(discord.File(BytesIO(bytes_img), filename=nome_arq))
            break # Envia a 1ª imagem

    await enviar_log_avancado(message.guild, "🗑️ Mensagem Apagada", desc, message.author, image_url=f"attachment://{arquivos[0].filename}" if arquivos else None, files=arquivos if arquivos else None)


# ==================== INTERAÇÕES GLOBAIS (PAINEL CUSTOMIZADO) ====================
@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.component:
        if interaction.data.get("custom_id", "").startswith("tktcustom_"):
            # Ex: tktcustom_12345678_87654321
            partes = interaction.data["custom_id"].split("_")
            if len(partes) == 3:
                cat_id = partes[1]
                role_id = partes[2]
                await criar_canal_ticket(interaction, "Atendimento", cat_id, role_id)


# ==================== COMANDOS DE BARRA ====================

@bot.tree.command(name="mute", description="Silencia um membro no servidor temporariamente.")
@app_commands.default_permissions(moderate_members=True)
async def mute_slash(interaction: discord.Interaction, membro: discord.Member, tempo_minutos: int, motivo: str = "Sem motivo"):
    await interaction.response.defer(ephemeral=True)
    try:
        bot.ultimos_mutes.add(membro.id)
        await membro.timeout(datetime.timedelta(minutes=tempo_minutos), reason=f"{interaction.user.name} | {motivo}")
        await interaction.followup.send(f"✅ O usuário {membro.mention} foi silenciado por {tempo_minutos} minuto(s).")
        await log_punicao_bonito(interaction.guild, membro, interaction.user, f"Mute Comando ({tempo_minutos} mins)", motivo)
    except Exception:
        await interaction.followup.send("❌ Erro ao mutar. Verifique as permissões/cargos.")

@bot.tree.command(name="ban", description="Bane um membro do servidor.")
@app_commands.default_permissions(ban_members=True)
async def ban_slash(interaction: discord.Interaction, membro: discord.Member, motivo: str = "Sem motivo"):
    await interaction.response.defer(ephemeral=True)
    sucesso = await executar_banimento(interaction.guild, membro, interaction.user, motivo, "Ban Comando")
    if sucesso: await interaction.followup.send(f"🔨 {membro.mention} banido com sucesso.")
    else: await interaction.followup.send("❌ Erro ao banir. Verifique a hierarquia de cargos.")

@bot.tree.command(name="limpar", description="Apaga mensagens em massa no chat.")
@app_commands.default_permissions(manage_messages=True)
async def limpar(interaction: discord.Interaction, quantidade: int):
    await interaction.response.defer(ephemeral=True)
    try:
        apagadas = await interaction.channel.purge(limit=quantidade)
        await interaction.followup.send(f"✅ Foram apagadas {len(apagadas)} mensagens com sucesso!", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Erro ao apagar mensagens: {e}", ephemeral=True)

@bot.tree.command(name="criar_painel", description="Cria um painel customizado de tickets (Ex: painel de Segurança)")
@app_commands.default_permissions(administrator=True)
async def criar_painel(interaction: discord.Interaction, titulo: str, descricao: str, categoria_id: str, cargo_staff_id: str, imagem_url: str = None):
    try:
        cat = int(categoria_id)
        role = int(cargo_staff_id)
    except ValueError:
        return await interaction.response.send_message("❌ O ID da Categoria e do Cargo devem ser apenas números!", ephemeral=True)

    embed = discord.Embed(title=titulo, description=descricao, color=0x950606)
    if imagem_url: embed.set_image(url=imagem_url)

    view = discord.ui.View(timeout=None)
    view.add_item(discord.ui.Button(label="Abrir Ticket", style=discord.ButtonStyle.primary, emoji="🎫", custom_id=f"tktcustom_{cat}_{role}"))

    await interaction.channel.send(embed=embed, view=view)
    await interaction.response.send_message("✅ Painel criado com sucesso!", ephemeral=True)


# ==================== SISTEMA DE SORTEIO ====================
@bot.tree.command(name="sorteio", description="Inicia um sorteio com multiplicadores de cargo.")
@app_commands.describe(cargo_extra="Cargo que terá o dobro de chances de ganhar.")
@app_commands.default_permissions(administrator=True)
async def sorteio(interaction: discord.Interaction, titulo: str, descricao: str, minutos: int, ganhadores: int, cargo_extra: discord.Role = None):
    termino = discord.utils.utcnow() + datetime.timedelta(minutes=minutos)
    
    embed = discord.Embed(title=f"🎉 SORTEIO: {titulo}", description=f"{descricao}\n\nReaja com 🎉 para participar!", color=0x950606)
    embed.add_field(name="Ganhadores", value=str(ganhadores))
    embed.add_field(name="Termina em", value=discord.utils.format_dt(termino, 'R'))
    if cargo_extra:
        embed.add_field(name="✨ Vantagem", value=f"Membros com {cargo_extra.mention} têm **2X mais chances**!", inline=False)
        
    await interaction.response.send_message("Sorteio iniciado!", ephemeral=True)
    msg = await interaction.channel.send(embed=embed)
    await msg.add_reaction("🎉")

    bot.sorteios_ativos[msg.id] = {
        "ganhadores": ganhadores,
        "cargo_extra_id": cargo_extra.id if cargo_extra else None
    }

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
            participantes.append(u)
            # Verifica o peso extra
            if dados["cargo_extra_id"] and isinstance(u, discord.Member):
                if any(r.id == dados["cargo_extra_id"] for r in u.roles):
                    participantes.append(u) # Adiciona de novo (Peso 2)

        vencedores = []
        qtd_ganhadores = min(dados["ganhadores"], len(set(participantes)))
        
        while len(vencedores) < qtd_ganhadores:
            sorteado = random.choice(participantes)
            if sorteado not in vencedores:
                vencedores.append(sorteado)
        
        vencedores_mentions = ", ".join(v.mention for v in vencedores)
        embed = msg.embeds[0]
        embed.description = f"**SORTEIO ENCERRADO**\n\nGanhadores: {vencedores_mentions}"
        await msg.edit(embed=embed)
        await channel.send(f"🎊 Parabéns {vencedores_mentions}! Vocês ganharam o sorteio **{embed.title.replace('🎉 SORTEIO: ', '')}**! (Link: {msg.jump_url})")
    except Exception as e:
        print(f"Erro sorteio: {e}")

@bot.tree.command(name="roletar", description="Sorteia novamente o ganhador de um sorteio antigo.")
@app_commands.default_permissions(administrator=True)
async def roletar(interaction: discord.Interaction, id_mensagem: str):
    await interaction.response.defer()
    try:
        msg = await interaction.channel.fetch_message(int(id_mensagem))
        reaction = discord.utils.get(msg.reactions, emoji="🎉")
        if not reaction:
            return await interaction.followup.send("❌ Não achei reações de 🎉 nessa mensagem.")
            
        users = [user async for user in reaction.users() if not user.bot]
        if not users:
            return await interaction.followup.send("❌ Ninguém participou desse sorteio.")
            
        vencedor = random.choice(users)
        await interaction.followup.send(f"🎲 **NOVO RESULTADO!** O novo ganhador roletado foi: {vencedor.mention}!")
    except Exception as e:
        await interaction.followup.send(f"❌ Erro ao roletar: Certifique-se de usar o comando no mesmo canal do sorteio. ({e})")


# ==================== CLASSES DOS PAINEIS ANTIGOS ====================
class DropdownGhoul(discord.ui.Select):
    def __init__(self):
        opcoes = [
            discord.SelectOption(label="Denúncias", value="denuncias", description="Denúncias e ajuda técnica.", emoji="🚨"),
            discord.SelectOption(label="Suporte", value="suporte", description="Recorra a uma punição.", emoji="🛠️"),
            discord.SelectOption(label="Dúvidas", value="duvidas", description="Tire dúvidas sobre as regras.", emoji="❓"),
            discord.SelectOption(label="Exposed", value="exposed", description="Falar sobre membro expondo outro.", emoji="⚠️"),
        ]
        super().__init__(placeholder="Selecione o setor...", min_values=1, max_values=1, options=opcoes, custom_id="sel_ghoul")
    async def callback(self, interaction: discord.Interaction): await criar_canal_ticket(interaction, self.values[0])

class DropdownKings(discord.ui.Select):
    def __init__(self):
        opcoes = [
            discord.SelectOption(label="Robux", value="robux", emoji="💰"),
            discord.SelectOption(label="Gamepass", value="gamepass", emoji="📦"),
            discord.SelectOption(label="Frutas Perm", value="frutas_perm", emoji="🍊"),
            discord.SelectOption(label="Frutas Físicas", value="frutas_fisicas", emoji="🍎"),
            discord.SelectOption(label="Contas", value="contas", emoji="💸"),
        ]
        super().__init__(placeholder="Selecione a categoria...", min_values=1, max_values=1, options=opcoes, custom_id="sel_kings")
    async def callback(self, interaction: discord.Interaction): await criar_canal_ticket(interaction, self.values[0])

class DropdownNightware(discord.ui.Select):
    def __init__(self):
        opcoes = [
            discord.SelectOption(label="Comprar", value="compras", emoji="🛒"),
            discord.SelectOption(label="Financeiro", value="financeiro", emoji="💳"),
            discord.SelectOption(label="Suporte", value="suporte", emoji="🛠️"),
        ]
        super().__init__(placeholder="Selecione a categoria...", min_values=1, max_values=1, options=opcoes, custom_id="sel_nightware")
    async def callback(self, interaction: discord.Interaction): await criar_canal_ticket(interaction, self.values[0])

class DropdownPolias(discord.ui.Select):
    def __init__(self):
        opcoes = [
            discord.SelectOption(label="Suporte", value="suporte", emoji="🛠️"),
            discord.SelectOption(label="Parcerias", value="parcerias", emoji="🤝"),
            discord.SelectOption(label="Denúncias", value="denuncias", emoji="🚨"),
        ]
        super().__init__(placeholder="Selecione o setor...", min_values=1, max_values=1, options=opcoes, custom_id="sel_polias")
    async def callback(self, interaction: discord.Interaction): await criar_canal_ticket(interaction, self.values[0])

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

class ViewPolias(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(DropdownPolias())

class ViewValidar(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="Validar", style=discord.ButtonStyle.danger, emoji="🎫", custom_id="btn_validar_cod")
    async def validar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await criar_canal_ticket(interaction, "coldawn")

@bot.tree.command(name="painel_tickets", description="Envia o painel de atendimento base de tickets.")
@app_commands.choices(painel=[
    app_commands.Choice(name="GHOUL", value="ghoul"),
    app_commands.Choice(name="BLOX KINGS", value="kings"),
    app_commands.Choice(name="NIGHTWARE", value="nightware"),
    app_commands.Choice(name="COD", value="cod"),
    app_commands.Choice(name="POLIAS", value="polias"),
])
@app_commands.default_permissions(administrator=True)
async def painel_slash(interaction: discord.Interaction, painel: app_commands.Choice[str]):
    if painel.value == "ghoul":
        embed = discord.Embed(title="🛡️ CENTRAL DE ATENDIMENTO - GHOUL", description="**Denúncias:**\n↳ Denúncias, ajuda técnica e revisão.\n\n**Suporte:**\n↳ Recorra a uma punição.\n\n**Dúvidas:**\n↳ Tire dúvidas.\n\n**Exposed:**\n↳ Falar sobre membro expondo outro.", color=0x950606)
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
    elif painel.value == "polias":
        embed = discord.Embed(title="🛡️ CENTRAL DE ATENDIMENTO - POLIAS", description="Selecione uma opção no menu abaixo para abrir seu ticket e falar com a nossa equipe.", color=0x950606)
        embed.set_image(url=IMAGENS_TICKETS["POLIAS"])
        view = ViewPolias()
    elif painel.value == "cod":
        embed = discord.Embed(title="TICKET DE COLDAWN", description="INFORMAMOS QUE A NOVA FUNÇÃO DO SERVIDOR \"GHOUL 👻\"\nJÁ ESTÁ DISPONÍVEL...", color=0x950606)
        embed.set_image(url=IMAGENS_TICKETS["COD"])
        view = ViewValidar()

    await interaction.channel.send(embed=embed, view=view)
    await interaction.response.send_message(f"✅ Painel **{painel.name}** enviado com sucesso!", ephemeral=True)


@bot.event
async def on_ready():
    print(f"✅ Sistema perfeito! {bot.user.name} online, logs completos e Sorteios Ativos!")

TOKEN = os.getenv("TOKEN")
if TOKEN: bot.run(TOKEN)
else: print("❌ ERRO: Token não encontrado.")
