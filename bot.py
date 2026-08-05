import asyncio
import datetime
import os
import re
import random
import unicodedata
from io import BytesIO
from discord import app_commands
from discord.ext import commands
import discord
from flask import Flask
import imagehash
from PIL import Image
import requests
from threading import Thread

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

TERMOS_BAN = ["checkmybio", "checkmyprofile", "lookmybio", "lookatmybio", "checkbio", "olharabiografia", "olheminhabio", "freenitro", "nitrogratis", "onlyfansfree"]
PALAVROES = ["fdp", "filhodaputa", "caralho", "krl", "bosta", "escroto", "merda", "arrombado", "viado", "corno", "desgracado", "vagabundo", "porra", "buceta", "cacete", "puta", "puto", "cuzao", "pica", "rola", "xoxota", "vadia", "foder", "fodase", "tnc", "tomarnocu", "vsf", "vtnc", "pqp"]
IMAGENS_BLOQUEADAS_HASHES = ["9977339a644d9a62", "936c6c4e946cd966", "9748a8dcbd4a2579", "c48ff019712fe2c6", "91ac6db293ab09a6", "c1e1eb965c5e5cd0", "f5de4a08bdbd5aa5", "956a6e944ac9a6c9", "931e6ae394d3486f"]

# ==================== ESTRUTURA DO BOT ====================
class MeuBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents, help_command=None)
        self.mensagens_ignoradas = set()
        self.sorteios_ativos = {}
        self.configs_sorteio_temp = {}

    async def setup_hook(self):
        self.add_view(ViewGhoul())
        self.add_view(ViewKings())
        self.add_view(ViewNightware())
        self.add_view(ViewPolias())
        self.add_view(ViewValidar())
        self.add_view(ViewTicketCustomizado())
        self.add_view(ViewControlesTicket())
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

async def enviar_log(guild_id, embed, files=None):
    config = obter_config(guild_id)
    if not config: return
    guild = bot.get_guild(guild_id)
    if not guild: return
    canal = guild.get_channel(config["canal_logs"]) or await guild.fetch_channel(config["canal_logs"])
    if not canal: return
    if files:
        await canal.send(embed=embed, files=files)
    else:
        await canal.send(embed=embed)

# ==================== PUNIÇÕES E AUTOMODERAÇÃO ====================
async def log_punicao_bonito(guild, user, staff, acao, motivo, prova_url=None):
    config = obter_config(guild.id)
    if not config: return
    canal = guild.get_channel(config["canal_punicoes"]) 
    if not canal:
        try:
            canal = await guild.fetch_channel(config["canal_punicoes"])
        except:
            return

    embed = discord.Embed(title=f"🔨 {config['nome']} - Punição Aplicada", color=0x950606, timestamp=discord.utils.utcnow())
    if user.display_avatar: embed.set_thumbnail(url=user.display_avatar.url)
    embed.description = f"👤 **Usuário:** {user.mention}\n📛 **Nick:** `{user.name}`\n🆔 **ID:** `{user.id}`\n🛡️ **Staff:** {staff.mention if hasattr(staff, 'mention') else staff}\n🚨 **Ação:** `{acao}`\n📄 **Motivo:** {motivo}"
    if prova_url: embed.set_image(url=prova_url)
    embed.set_footer(text=f"Segurança Ativa {config['nome']}", icon_url=guild.icon.url if guild.icon else None)
    await canal.send(embed=embed)

async def executar_banimento(guild, membro, staff, motivo, acao_log, prova_url=None):
    config = obter_config(guild.id)
    nome_servidor = config["nome"] if config else guild.name
    try:
        await membro.send(f"**{nome_servidor} | Aviso de Banimento**\n\nCaro(a) {membro.mention},\nVocê foi banido(a).\n**Motivo:** {motivo}\n\n*Atenciosamente, Equipe {nome_servidor}*")
    except: pass
    try:
        staff_name = staff.name if hasattr(staff, "name") else str(staff)
        await membro.ban(reason=f"{staff_name} | {motivo}")
        await log_punicao_bonito(guild, membro, staff, acao_log, motivo, prova_url)
        return True
    except Exception as e:
        print(f"Erro ao banir membro: {e}")
        return False

@bot.event
async def on_member_ban(guild, user):
    await asyncio.sleep(1.5)
    async for entry in guild.audit_logs(limit=3, action=discord.AuditLogAction.ban):
        if entry.target.id == user.id:
            await log_punicao_bonito(guild, user, entry.user, "Banimento", entry.reason or "Sem motivo especificado")
            break

# ==================== COMANDO DE MUTE ====================
@bot.tree.command(name="mute", description="Silencia temporariamente um membro no servidor.")
@app_commands.default_permissions(moderate_members=True)
async def mute_slash(interaction: discord.Interaction, membro: discord.Member, minutos: int, *, motivo: str):
    await interaction.response.defer(ephemeral=True)
    tempo = datetime.timedelta(minutes=minutos)
    try:
        await membro.timeout(tempo, reason=f"{interaction.user} | {motivo}")
        await log_punicao_bonito(interaction.guild, membro, interaction.user, "Mute / Silenciamento", f"{motivo} (Duração: {minutos} minutos)")
        await interaction.followup.send(f"✅ O membro {membro.mention} foi silenciado por **{minutos} minutos**.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Não foi possível silenciar o membro: {e}", ephemeral=True)

# ==================== LOGS DE VOZ E CARGOS ====================
@bot.event
async def on_voice_state_update(member, before, after):
    config = obter_config(member.guild.id)
    if not config: return

    embed = discord.Embed(color=0x950606, timestamp=discord.utils.utcnow())
    if member.display_avatar: embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=f"Logs de Voz | {config['nome']}")

    if before.channel is None and after.channel is not None:
        embed.title = "🎙️ Usuário entrou no Canal de Voz"
        embed.description = f"👤 **Usuário:** {member.mention} ({member.id})\n🔊 **Canal:** {after.channel.mention}"
        await enviar_log(member.guild.id, embed)
    elif before.channel is not None and after.channel is None:
        desconectado_por = None
        await asyncio.sleep(1.5)
        try:
            async for entry in member.guild.audit_logs(limit=5, action=discord.AuditLogAction.member_disconnect):
                if entry.target.id == member.id and (discord.utils.utcnow() - entry.created_at).total_seconds() < 8:
                    desconectado_por = entry.user
                    break
        except Exception as e:
            print(f"Erro ao buscar audit log de voz: {e}")

        if desconectado_por:
            embed.title = "⚠️ Usuário desconectado da Call por um Staff"
            embed.description = f"👤 **Usuário:** {member.mention} (`{member.name}`)\n🛡️ **Staff:** {desconectado_por.mention}\n🔇 **Canal Anterior:** {before.channel.mention}"
        else:
            embed.title = "🚪 Usuário saiu do Canal de Voz"
            embed.description = f"👤 **Usuário:** {member.mention} ({member.id})\n🔇 **Canal Anterior:** {before.channel.mention}"
        await enviar_log(member.guild.id, embed)

@bot.event
async def on_member_update(before, after):
    config = obter_config(before.guild.id)
    if not config: return

    if before.roles != after.roles:
        added = [r.mention for r in after.roles if r not in before.roles]
        removed = [r.mention for r in before.roles if r not in after.roles]
        
        responsavel = "Usuário/Desconhecido"
        await asyncio.sleep(1.5)
        try:
            async for entry in before.guild.audit_logs(limit=5, action=discord.AuditLogAction.member_role_update):
                if entry.target.id == after.id and (discord.utils.utcnow() - entry.created_at).total_seconds() < 8:
                    responsavel = entry.user.mention
                    break
        except: pass

        embed = discord.Embed(title="🛡️ Atualização de Cargos", color=0x950606, timestamp=discord.utils.utcnow())
        embed.set_thumbnail(url=after.display_avatar.url if after.display_avatar else None)
        desc = f"👤 **Membro:** {after.mention} ({after.id})\n🛡️ **Autor da Ação:** {responsavel}\n"
        if added: desc += f"\n✅ **Cargos Adicionados:** {', '.join(added)}"
        if removed: desc += f"\n❌ **Cargos Removidos:** {', '.join(removed)}"
        embed.description = desc
        embed.set_footer(text=f"Logs de Cargos | {config['nome']}")
        await enviar_log(before.guild.id, embed)

@bot.event
async def on_raw_bulk_message_delete(payload):
    config = obter_config(payload.guild_id)
    if not config: return
    embed = discord.Embed(title="🗑️ Mensagens Apagadas em Massa", color=0x950606, timestamp=discord.utils.utcnow())
    embed.description = f"🧹 **Quantidade:** `{len(payload.message_ids)}` mensagens\n💬 **Canal:** <#{payload.channel_id}>"
    await enviar_log(payload.guild_id, embed)

@bot.tree.command(name="limpar", description="Apaga mensagens em massa no canal atual.")
@app_commands.default_permissions(manage_messages=True)
async def limpar_slash(interaction: discord.Interaction, quantidade: int):
    await interaction.response.defer(ephemeral=True)
    try:
        deleted = await interaction.channel.purge(limit=quantidade)
        await interaction.followup.send(f"✅ Sucesso! **{len(deleted)}** mensagens foram apagadas.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Erro ao apagar mensagens: {e}", ephemeral=True)

# ==================== SISTEMA DE TICKETS ====================
class ViewControlesTicket(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Reivindicar Ticket", style=discord.ButtonStyle.success, emoji="✋", custom_id="btn_reivindicar")
    async def reivindicar(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = obter_config(interaction.guild.id)
        if not config: return
        cargo_staff = interaction.guild.get_role(config["cargo_staff"])
        
        if cargo_staff not in interaction.user.roles and not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Apenas staffs podem reivindicar tickets!", ephemeral=True)
            
        embed = discord.Embed(title="✋ Ticket Reivindicado", description=f"O staff {interaction.user.mention} assumiu este atendimento!", color=0x2ecc71)
        button.disabled = True
        button.label = f"Assumido por {interaction.user.name}"
        await interaction.response.edit_message(view=self)
        await interaction.channel.send(embed=embed)

    @discord.ui.button(label="Fechar Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="btn_fechar_ticket")
    async def fechar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 Fechando canal em 5 segundos...", ephemeral=True)
        await asyncio.sleep(5)
        await interaction.channel.delete()

async def criar_canal_ticket(interaction: discord.Interaction, setor: str):
    config = obter_config(interaction.guild.id)
    if not config or interaction.response.is_done(): return
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
        description=f"Olá {interaction.user.mention},\n\nSeu ticket para **{setor.upper()}** foi aberto com sucesso!\nDescreva detalhadamente o que precisa.",
        color=0x950606,
    )
    await canal.send(content=f"{interaction.user.mention} {cargo_staff.mention if cargo_staff else ''}", embed=embed, view=ViewControlesTicket())
    await interaction.response.send_message(f"✅ Ticket criado em {canal.mention}!", ephemeral=True)

class ViewTicketCustomizado(discord.ui.View):
    def __init__(self, setor_nome="Geral"):
        super().__init__(timeout=None)
        self.setor_nome = setor_nome

    @discord.ui.button(label="Abrir Ticket", style=discord.ButtonStyle.primary, emoji="🎫", custom_id="btn_ticket_custom")
    async def abrir(self, interaction: discord.Interaction, button: discord.ui.Button):
        await criar_canal_ticket(interaction, self.setor_nome)

class ModalTicketCustomizado(discord.ui.Modal, title="Criar Painel de Ticket"):
    titulo = discord.ui.TextInput(label="Título do Embed", placeholder="Central de Atendimento", required=True)
    descricao = discord.ui.TextInput(label="Descrição", style=discord.TextStyle.paragraph, placeholder="Clique abaixo para abrir seu ticket.", required=True)
    setor = discord.ui.TextInput(label="Setor", placeholder="suporte", required=True)
    imagem_url = discord.ui.TextInput(label="URL da Imagem (Opcional)", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(title=self.titulo.value, description=self.descricao.value, color=0x950606)
        if self.imagem_url.value: embed.set_image(url=self.imagem_url.value)
        await interaction.channel.send(embed=embed, view=ViewTicketCustomizado(self.setor.value))
        await interaction.response.send_message("✅ Painel criado!", ephemeral=True)

@bot.tree.command(name="painel_customizado", description="Cria painel de ticket personalizado.")
@app_commands.default_permissions(administrator=True)
async def painel_custom(interaction: discord.Interaction):
    await interaction.response.send_modal(ModalTicketCustomizado())

class DropdownGhoul(discord.ui.Select):
    def __init__(self):
        opcoes = [
            discord.SelectOption(label="Denúncias", value="denuncias", emoji="🚨"),
            discord.SelectOption(label="Suporte", value="suporte", emoji="🛠️"),
            discord.SelectOption(label="Dúvidas", value="duvidas", emoji="❓"),
            discord.SelectOption(label="Exposed", value="exposed", emoji="⚠️"),
        ]
        super().__init__(placeholder="Selecione o setor...", options=opcoes, custom_id="sel_ghoul")
    async def callback(self, interaction: discord.Interaction):
        await criar_canal_ticket(interaction, self.values[0])

class ViewGhoul(discord.ui.View):
    def __init__(self): super().__init__(timeout=None); self.add_item(DropdownGhoul())

class DropdownKings(discord.ui.Select):
    def __init__(self):
        opcoes = [discord.SelectOption(label="Robux", value="robux", emoji="💰"), discord.SelectOption(label="Gamepass", value="gamepass", emoji="📦")]
        super().__init__(placeholder="Selecione...", options=opcoes, custom_id="sel_kings")
    async def callback(self, interaction: discord.Interaction):
        await criar_canal_ticket(interaction, self.values[0])

class ViewKings(discord.ui.View):
    def __init__(self): super().__init__(timeout=None); self.add_item(DropdownKings())

class DropdownNightware(discord.ui.Select):
    def __init__(self):
        opcoes = [discord.SelectOption(label="Comprar", value="compras", emoji="🛒"), discord.SelectOption(label="Suporte", value="suporte", emoji="🛠️")]
        super().__init__(placeholder="Selecione...", options=opcoes, custom_id="sel_nightware")
    async def callback(self, interaction: discord.Interaction):
        await criar_canal_ticket(interaction, self.values[0])

class ViewNightware(discord.ui.View):
    def __init__(self): super().__init__(timeout=None); self.add_item(DropdownNightware())

class DropdownPolias(discord.ui.Select):
    def __init__(self):
        opcoes = [discord.SelectOption(label="Suporte", value="suporte", emoji="🛠️"), discord.SelectOption(label="Parcerias", value="parcerias", emoji="🤝")]
        super().__init__(placeholder="Selecione...", options=opcoes, custom_id="sel_polias")
    async def callback(self, interaction: discord.Interaction):
        await criar_canal_ticket(interaction, self.values[0])

class ViewPolias(discord.ui.View):
    def __init__(self): super().__init__(timeout=None); self.add_item(DropdownPolias())

class ViewValidar(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Validar", style=discord.ButtonStyle.danger, emoji="🎫", custom_id="btn_validar_cod")
    async def validar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await criar_canal_ticket(interaction, "coldawn")

# ==================== AUTOMODERAÇÃO DE IMAGENS PROIBIDAS (BLINDADO) ====================
@bot.event
async def on_message(message):
    if message.author.bot or not message.guild: return
    config = obter_config(message.guild.id)
    if not config: return

    if message.attachments:
        for attachment in message.attachments:
            if any(attachment.filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.webp', '.gif']):
                try:
                    response = requests.get(attachment.url, timeout=7)
                    if response.status_code == 200:
                        img = Image.open(BytesIO(response.content))
                        h_atual = imagehash.average_hash(img)
                        
                        for hash_str in IMAGENS_BLOQUEADAS_HASHES:
                            h_bloq = imagehash.hex_to_hash(hash_str)
                            if h_atual - h_bloq <= 6:
                                bot.mensagens_ignoradas.add(message.id)
                                try: await message.delete()
                                except Exception as ex: print(f"Erro ao apagar img: {ex}")
                                
                                embed_log_img = discord.Embed(title=f"🚨 {config['nome']} - Imagem Proibida Bloqueada", color=0x950606, timestamp=discord.utils.utcnow())
                                embed_log_img.description = f"👤 **Usuário:** {message.author.mention} (`{message.author.name}`)\n💬 **Canal:** {message.channel.mention}\n⚡ **Ação:** `Deletada e Banido Instantaneamente`"
                                embed_log_img.set_image(url=attachment.url)
                                await enviar_log(message.guild.id, embed_log_img)

                                await executar_banimento(message.guild, message.author, bot.user, "Envio de Imagem Proibida / Automod", "Ban Automático (Imagem Proibida)", attachment.url)
                                return
                except Exception as e:
                    print(f"Erro no processamento de hash da imagem: {e}")

    texto_norm = normalizar_texto(message.content)
    texto_junto = re.sub(r"\s+", "", texto_norm)

    for palavrao in PALAVROES:
        if palavrao in texto_junto:
            bot.mensagens_ignoradas.add(message.id)
            try: await message.delete()
            except: pass
            aviso = await message.channel.send(f"{message.author.mention}, cuidado com o linguajar!")
            await asyncio.sleep(4)
            try: await aviso.delete()
            except: pass
            return

    for termo in TERMOS_BAN:
        if termo in texto_junto:
            bot.mensagens_ignoradas.add(message.id)
            try: await message.delete()
            except: pass
            await executar_banimento(message.guild, message.author, bot.user, f"Tentativa de golpe: `{termo}`", "Ban Automático")
            return

# ==================== SORTEIOS ESTILO LORITTA ====================
class SorteioParticiparView(discord.ui.View):
    def __init__(self, sorteio_id: str):
        super().__init__(timeout=None)
        self.sorteio_id = sorteio_id

    @discord.ui.button(label="Participar 🎉", style=discord.ButtonStyle.success, custom_id="btn_participar_sorteio")
    async def participar(self, interaction: discord.Interaction, button: discord.ui.Button):
        s_id = str(interaction.message.id)
        if s_id not in bot.sorteios_ativos:
            return await interaction.response.send_message("❌ Este sorteio já acabou ou é inválido!", ephemeral=True)
            
        dados = bot.sorteios_ativos[s_id]
        participantes = dados["participantes"]
        
        if dados.get("cargos_bloqueados"):
            if any(r.id in dados["cargos_bloqueados"] for r in interaction.user.roles):
                return await interaction.response.send_message("❌ Você possui um cargo bloqueado e não pode participar deste sorteio!", ephemeral=True)
                
        if dados.get("cargos_permitidos"):
            if not any(r.id in dados["cargos_permitidos"] for r in interaction.user.roles):
                return await interaction.response.send_message("❌ Você não possui os cargos necessários para participar deste sorteio!", ephemeral=True)

        if interaction.user.id in participantes:
            while interaction.user.id in participantes:
                participantes.remove(interaction.user.id)
            await interaction.response.send_message("🚪 Você saiu do sorteio.", ephemeral=True)
        else:
            participantes.append(interaction.user.id)
            if interaction.user.id in dados.get("entradas_extras", {}):
                extras = dados["entradas_extras"][interaction.user.id]
                for _ in range(extras):
                    participantes.append(interaction.user.id)
            await interaction.response.send_message("🎉 Você entrou no sorteio com sucesso! Boa sorte!", ephemeral=True)
            
        button.label = f"Participar 🎉 ({len(set(participantes))})"
        await interaction.message.edit(view=self)

    @discord.ui.button(label="Participantes", style=discord.ButtonStyle.secondary, custom_id="btn_ver_participantes")
    async def ver_participantes(self, interaction: discord.Interaction, button: discord.ui.Button):
        s_id = str(interaction.message.id)
        if s_id not in bot.sorteios_ativos:
            return await interaction.response.send_message("❌ Sorteio encerrado ou não encontrado.", ephemeral=True)
        part_unicos = list(set(bot.sorteios_ativos[s_id]["participantes"]))
        texto = ", ".join([f"<@{uid}>" for uid in part_unicos[:30]]) or "Nenhum participante ainda."
        if len(part_unicos) > 30: texto += f" e mais {len(part_unicos) - 30} usuários."
        await interaction.response.send_message(f"👥 **Total de Participantes Únicos:** `{len(part_unicos)}`\n\n{texto}", ephemeral=True)

class ModalSorteioGeral(discord.ui.Modal, title="Configurar Geral (Sorteio)"):
    premio = discord.ui.TextInput(label="Prêmio do Sorteio", placeholder="Ex: Kitsune Permanente", required=True)
    vencedores = discord.ui.TextInput(label="Quantidade de Vencedores", placeholder="1", default="1", required=True)
    duracao = discord.ui.TextInput(label="Duração em Minutos", placeholder="30", default="30", required=True)

    def __init__(self, guild_id):
        super().__init__()
        self.guild_id = guild_id

    async def on_submit(self, interaction: discord.Interaction):
        if self.guild_id not in bot.configs_sorteio_temp: bot.configs_sorteio_temp[self.guild_id] = {}
        bot.configs_sorteio_temp[self.guild_id]["premio"] = self.premio.value
        bot.configs_sorteio_temp[self.guild_id]["vencedores"] = int(self.vencedores.value)
        bot.configs_sorteio_temp[self.guild_id]["duracao"] = int(self.duracao.value)
        await interaction.response.send_message("✅ Configurações Gerais salvas com sucesso!", ephemeral=True)

class ModalSorteioAparencia(discord.ui.Modal, title="Configurar Aparência (Sorteio)"):
    descricao = discord.ui.TextInput(label="Descrição do Sorteio", style=discord.TextStyle.paragraph, placeholder="Insira as regras e detalhes...", required=False)
    cor_embed = discord.ui.TextInput(label="Cor da Embed (Hex)", placeholder="#950606", default="#950606", required=False)
    imagem_url = discord.ui.TextInput(label="URL da Imagem da Embed", placeholder="https://...", required=False)
    thumbnail_url = discord.ui.TextInput(label="URL da Thumbnail da Embed", placeholder="https://...", required=False)

    def __init__(self, guild_id):
        super().__init__()
        self.guild_id = guild_id

    async def on_submit(self, interaction: discord.Interaction):
        if self.guild_id not in bot.configs_sorteio_temp: bot.configs_sorteio_temp[self.guild_id] = {}
        bot.configs_sorteio_temp[self.guild_id]["descricao"] = self.descricao.value
        bot.configs_sorteio_temp[self.guild_id]["cor"] = self.cor_embed.value
        bot.configs_sorteio_temp[self.guild_id]["imagem"] = self.imagem_url.value
        bot.configs_sorteio_temp[self.guild_id]["thumbnail"] = self.thumbnail_url.value
        await interaction.response.send_message("✅ Aparência salva com sucesso!", ephemeral=True)

class ViewConfigCargosEntradas(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=120)
        self.guild_id = guild_id

    @discord.ui.select(cls=discord.ui.RoleSelect, placeholder="Selecione o cargo para Entradas Extras...", min_values=1, max_values=1)
    async def selecionar_cargo_extra(self, interaction: discord.Interaction, select: discord.ui.RoleSelect):
        cargo = select.values[0]
        if self.guild_id not in bot.configs_sorteio_temp: bot.configs_sorteio_temp[self.guild_id] = {}
        if "entradas_extras_map" not in bot.configs_sorteio_temp[self.guild_id]:
            bot.configs_sorteio_temp[self.guild_id]["entradas_extras_map"] = {}
        
        bot.configs_sorteio_temp[self.guild_id]["entradas_extras_map"][cargo.id] = 2
        await interaction.response.send_message(f"✅ Cargo {cargo.mention} configurado com entradas extras!", ephemeral=True)

class ViewConfigCanalSorteio(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=120)
        self.guild_id = guild_id

    @discord.ui.select(cls=discord.ui.ChannelSelect, placeholder="Selecione o Canal do Sorteio...", channel_types=[discord.ChannelType.text], min_values=1, max_values=1)
    async def selecionar_canal(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        canal = select.values[0]
        if self.guild_id not in bot.configs_sorteio_temp: bot.configs_sorteio_temp[self.guild_id] = {}
        bot.configs_sorteio_temp[self.guild_id]["canal_id"] = canal.id
        await interaction.response.send_message(f"✅ Canal de Sorteio definido para {canal.mention}!", ephemeral=True)

class SorteioSetupView(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=300)
        self.guild_id = guild_id

    @discord.ui.button(label="Geral", style=discord.ButtonStyle.primary, emoji="⚙️", custom_id="btn_s_geral")
    async def fn_geral(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalSorteioGeral(self.guild_id))

    @discord.ui.button(label="Aparência", style=discord.ButtonStyle.secondary, emoji="🎨", custom_id="btn_s_aparencia")
    async def fn_aparencia(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalSorteioAparencia(self.guild_id))

    @discord.ui.button(label="Canal", style=discord.ButtonStyle.secondary, emoji="📢", custom_id="btn_s_canal")
    async def canal_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Selecione o canal onde o sorteio será enviado:", view=ViewConfigCanalSorteio(self.guild_id), ephemeral=True)

    @discord.ui.button(label="Entradas Extras", style=discord.ButtonStyle.secondary, emoji="🎟️", custom_id="btn_s_extras")
    async def extras_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Selecione o cargo para dar entradas extras:", view=ViewConfigCargosEntradas(self.guild_id), ephemeral=True)

    @discord.ui.button(label="Lançar Sorteio 🚀", style=discord.ButtonStyle.success, emoji="🎉", custom_id="btn_s_lancar")
    async def lancar(self, interaction: discord.Interaction, button: discord.ui.Button):
        dados = bot.configs_sorteio_temp.get(self.guild_id, {})
        premio = dados.get("premio", "Prêmio Surpresa")
        vencedores = dados.get("vencedores", 1)
        duracao = dados.get("duracao", 30)
        descricao = dados.get("descricao", "Clique no botão abaixo para participar do sorteio!")
        cor_hex = dados.get("cor", "#950606").replace("#", "")
        cor_int = int(cor_hex, 16) if cor_hex else 0x950606
        imagem = dados.get("imagem")
        thumbnail = dados.get("thumbnail")
        canal_id = dados.get("canal_id", interaction.channel.id)

        canal_alvo = interaction.guild.get_channel(canal_id) or interaction.channel
        tempo_final = discord.utils.utcnow() + datetime.timedelta(minutes=duracao)
        timestamp_formatado = f"<t:{int(tempo_final.timestamp())}:R>"

        embed = discord.Embed(
            title=f"🎉 {premio} 🎉",
            description=f"{descricao}\n\n**Ganhador(es):** {vencedores}\n**Acabará em:** {timestamp_formatado}",
            color=cor_int
        )
        if imagem: embed.set_image(url=imagem)
        if thumbnail: embed.set_thumbnail(url=thumbnail)
        embed.set_footer(text=f"Sorteio criado por {interaction.user.name}", icon_url=interaction.user.display_avatar.url)

        msg = await canal_alvo.send(embed=embed, view=SorteioParticiparView(""))
        
        bot.sorteios_ativos[str(msg.id)] = {
            "premio": premio,
            "vencedores": vencedores,
            "participantes": [],
            "cargos_bloqueados": dados.get("cargos_bloqueados", []),
            "cargos_permitidos": dados.get("cargos_permitidos", []),
            "entradas_extras": {}
        }

        await interaction.response.send_message(f"🚀 Sorteio lançado com sucesso em {canal_alvo.mention}!", ephemeral=True)
        bot.loop.create_task(self.encerrar_sorteio_automatico(canal_alvo, msg.id, duracao))

    async def encerrar_sorteio_automatico(self, canal, msg_id, duracao_minutos):
        await asyncio.sleep(duracao_minutos * 60)
        s_id = str(msg_id)
        if s_id not in bot.sorteios_ativos: return
        dados = bot.sorteios_ativos[s_id]
        participantes = list(set(dados["participantes"]))
        
        try:
            msg = await canal.fetch_message(msg_id)
            if not participantes:
                embed = msg.embeds[0]
                embed.description += "\n\n❌ **Sorteio Encerrado!** Ninguém participou."
                await msg.edit(embed=embed, view=None)
                await canal.send(f"❌ O sorteio de **{dados['premio']}** foi cancelado pois não houve participantes.")
                return

            ganhadores = random.sample(participantes, min(dados["vencedores"], len(participantes)))
            texto_ganhadores = ", ".join([f"<@{uid}>" for uid in ganhadores])
            
            embed = msg.embeds[0]
            embed.description += f"\n\n🏆 **Sorteio Encerrado!**\n**Ganhador(es):** {texto_ganhadores}"
            await msg.edit(embed=embed, view=None)
            await canal.send(f"🎉 Parabéns {texto_ganhadores}! Vocês ganharam o sorteio de **{dados['premio']}**!")
        except:
            pass

@bot.tree.command(name="sorteio_setup", description="Abre o painel interativo de configuração de sorteios.")
@app_commands.default_permissions(manage_events=True)
async def sorteio_setup_slash(interaction: discord.Interaction):
    bot.configs_sorteio_temp[interaction.guild.id] = {}
    embed = discord.Embed(
        title="🎉 Configurador de Sorteios",
        description="Utilize os botões abaixo para configurar o **Geral**, **Aparência**, **Canal**, **Entradas Extras** e em seguida clique em **Lançar Sorteio**!",
        color=0x950606
    )
    await interaction.response.send_message(embed=embed, view=SorteioSetupView(interaction.guild.id), ephemeral=True)

# ==================== COMANDO DE ROLETAR / REROLL ====================
@bot.tree.command(name="roletar", description="Sorteia um novo vencedor para um sorteio existente através do ID da mensagem.")
@app_commands.default_permissions(manage_events=True)
async def roletar_slash(interaction: discord.Interaction, message_id: str):
    await interaction.response.defer(ephemeral=True)
    s_id = message_id.strip()
    if s_id not in bot.sorteios_ativos:
        return await interaction.followup.send("❌ Sorteio não encontrado nos registros ativos.", ephemeral=True)
    
    dados = bot.sorteios_ativos[s_id]
    participantes = list(set(dados["participantes"]))
    if not participantes:
        return await interaction.followup.send("❌ Não há participantes neste sorteio para roletar.", ephemeral=True)
    
    novo_ganhador = random.choice(participantes)
    await interaction.followup.send(f"🎲 Novo vencedor roletado com sucesso para o prêmio **{dados['premio']}**: <@{novo_ganhador}>!", ephemeral=False)

@bot.event
async def on_ready():
    print(f"✅ Bot totalmente corrigido e operando! {bot.user.name} está online.")

TOKEN = os.getenv("TOKEN")
if TOKEN:
    bot.run(TOKEN)
else:
    print("❌ ERRO: Token não encontrado no ambiente.")
