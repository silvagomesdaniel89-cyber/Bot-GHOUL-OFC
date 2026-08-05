import asyncio
import datetime
import os
import re
import sqlite3
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

# ==================== BANCO DE DADOS ====================
db = sqlite3.connect("seguranca_maxima.db", check_same_thread=False)
cursor = db.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS tickets (user_id INTEGER PRIMARY KEY, channel_id INTEGER)")
db.commit()

# ==================== SERVIDOR WEB ====================
app = Flask(__name__)
@app.route("/")
def home(): return "Sistema Definitivo Operante!"
Thread(target=lambda: app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080))), daemon=True).start()

# ==================== CONFIGURAÇÕES ====================
CONFIG_SERVIDORES = {
    1143627184842493992: {"nome": "GHOUL SECURITY", "canal_logs": 1272293056812683345, "canal_punicoes": 1468415943251202252, "categoria_tickets": 1527037033057353728, "cargo_staff": 1274081192450195671},
    1169685424738947172: {"nome": "BLOX KINGS", "canal_logs": 1526271422253629681, "canal_punicoes": 1526255782222626907, "categoria_tickets": 1170495547426217995, "cargo_staff": 1317249055058825236},
    1331323352840933497: {"nome": "NIGHTWARE STORE", "canal_logs": 1527037894743687168, "canal_punicoes": 1527038039111635114, "categoria_tickets": 1331327159448375356, "cargo_staff": 1333982207701684294},
    1489007277267620013: {"nome": "POLIAS", "canal_logs": 1489007278693814453, "canal_punicoes": 1533828688213311608, "categoria_tickets": 1533834644569456681, "cargo_staff": 1489007277267620020},
}

IMAGENS_TICKETS = {
    "GHOUL": "https://cdn.discordapp.com/attachments/1444429504838631586/1454170002746769530/Banner_ticket_20250205_120340_0000.png",
    "BLOX_KINGS": "https://cdn.discordapp.com/attachments/1183819407013707947/1526281157635870730/file_000000002958720eab459d97fd2c5b8e.png",
    "NIGHTWARE": "https://cdn.discordapp.com/attachments/1440377531848200295/1452759780111155323/standard.gif",
    "POLIAS": "https://cdn.discordapp.com/attachments/1431364353482948608/1533832231108214864/file_000000004fd4820eb39bb046269d5d96.png",
}

IMAGENS_BLOQUEADAS = ["9977339a644d9a62", "936c6c4e946cd966", "9748a8dcbd4a2579", "c48ff019712fe2c6"]
COR_EMBED = 0x2b2d31
COR_PUNICAO = 0xff3b3b
COR_LOG = 0xa3a3a3

# ==================== BOT CORE & ANTI-CRASH ====================
class MeuBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
        self.mensagens_ignoradas = set()
        self.spam_control = {}
        self.sorteios_ativos = {}

    async def setup_hook(self):
        self.add_view(TicketView())
        await self.tree.sync()
        
    async def on_command_error(self, ctx, error):
        # Evita que o bot quebre no console por erros bobos de permissão
        if isinstance(error, commands.MissingPermissions):
            pass

bot = MeuBot()
def obter_config(guild_id): return CONFIG_SERVIDORES.get(guild_id)

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ Você não tem permissão para usar isso.", ephemeral=True)
    else:
        print(f"Erro no comando ignorado para não crachar: {error}")

async def enviar_log(guild, title, description, user=None, color=COR_LOG):
    config = obter_config(guild.id)
    if not config: return
    canal = guild.get_channel(config["canal_logs"])
    if not canal: return
    embed = discord.Embed(title=title, description=description, color=color, timestamp=discord.utils.utcnow())
    if user and hasattr(user, 'display_avatar'): embed.set_thumbnail(url=user.display_avatar.url)
    await canal.send(embed=embed)

async def log_punicao(guild, user, staff, acao, motivo, anexos=None):
    config = obter_config(guild.id)
    if not config: return
    canal = guild.get_channel(config["canal_punicoes"])
    if not canal: return
    embed = discord.Embed(title=f"🔨 {acao}", color=COR_PUNICAO, timestamp=discord.utils.utcnow())
    if hasattr(user, 'display_avatar'): embed.set_thumbnail(url=user.display_avatar.url)
    embed.add_field(name="Membro", value=f"{user.mention if hasattr(user, 'mention') else user} (`{user.id}`)", inline=True)
    embed.add_field(name="Staff", value=f"{staff.mention if hasattr(staff, 'mention') else staff}", inline=True)
    embed.add_field(name="Motivo", value=f"```{motivo}```", inline=False)
    await canal.send(embed=embed, files=anexos) if anexos else await canal.send(embed=embed)

# ==================== AUTOMOD DE IMAGEM & SPAM ====================
@bot.event
async def on_message(message):
    if message.author.bot or not message.guild: return
    config = obter_config(message.guild.id)
    if not config: return

    # BLOQUEIO DE IMAGENS (Deleta e Bane Simultaneamente)
    if message.attachments:
        for anexo in message.attachments:
            if any(anexo.filename.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp"]):
                try:
                    bytes_img = await anexo.read()
                    img = Image.open(BytesIO(bytes_img)).convert("RGB")
                    hash_atual = imagehash.average_hash(img)
                    
                    for hash_block in IMAGENS_BLOQUEADAS:
                        if (hash_atual - imagehash.hex_to_hash(hash_block) <= 8):
                            bot.mensagens_ignoradas.add(message.id)
                            try:
                                await asyncio.gather(
                                    message.delete(),
                                    message.guild.ban(message.author, reason="AutoMod: Imagem Proibida.")
                                )
                                file_prova = discord.File(BytesIO(bytes_img), filename="SPOILER_prova_ilegal.png")
                                await log_punicao(message.guild, message.author, bot.user, "Ban Automático (Imagem Hash)", "Envio de mídia proibida.", anexos=[file_prova])
                            except discord.Forbidden:
                                await log_punicao(message.guild, message.author, bot.user, "Falha ao Banir", "Imagem proibida detectada, mas o bot não tem permissão de banir este usuário.")
                            return
                except: pass

    if message.author.guild_permissions.administrator: return

    # ANTI-SPAM (8 Segundos)
    agora = time.time()
    bot.spam_control.setdefault(message.author.id, [])
    mensagens_recentes = [t for t in bot.spam_control[message.author.id] if agora - t < 8]
    mensagens_recentes.append(agora)
    bot.spam_control[message.author.id] = mensagens_recentes
    
    if len(mensagens_recentes) > 5:
        bot.mensagens_ignoradas.add(message.id)
        try: await message.delete()
        except: pass
        bot.spam_control[message.author.id] = []
        try:
            await message.author.timeout(datetime.timedelta(minutes=15), reason="AutoMod: Flood")
            await enviar_log(message.guild, "🛡️ Auto Moderação - Spam", f"{message.author.mention} silenciado por 15m (Limite 8s).", message.author, 0xffa500)
        except: pass

# ==================== O MEGA SISTEMA DE LOGS ====================
@bot.event
async def on_audit_log_entry_create(entry: discord.AuditLogEntry):
    if entry.user.id == bot.user.id: return
    if entry.action == discord.AuditLogAction.ban:
        await log_punicao(entry.guild, entry.target, entry.user, "Banimento Manual", entry.reason or "Sem motivo.")
    elif entry.action == discord.AuditLogAction.kick:
        await log_punicao(entry.guild, entry.target, entry.user, "Expulsão Manual", entry.reason or "Sem motivo.")
    elif entry.action == discord.AuditLogAction.member_update and hasattr(entry.after, "timed_out_until"):
        if entry.after.timed_out_until:
            await log_punicao(entry.guild, entry.target, entry.user, "Castigo Aplicado", f"Motivo: {entry.reason or 'Nenhum'}")

@bot.event
async def on_message_delete(message):
    if message.author.bot or message.id in bot.mensagens_ignoradas: return
    await enviar_log(message.guild, "Mensagens - Apagar", f"🗑️ Em {message.channel.mention}\n👤 {message.author.mention}\n💬 ```{message.content or 'Mídia'}```", message.author, 0xff5555)

@bot.event
async def on_message_edit(before, after):
    if before.author.bot or before.content == after.content: return
    await enviar_log(before.guild, "Mensagens - Editar", f"📝 Em {before.channel.mention} [Ir]({after.jump_url})\n👤 {before.author.mention}\n**Antes:** ```{before.content}```\n**Depois:** ```{after.content}```", before.author, 0x55aaff)

@bot.event
async def on_member_join(member):
    alt = "⚠️ **CONTA SUSPEITA (Criada há menos de 7 dias)**\n" if (discord.utils.utcnow() - member.created_at).days < 7 else ""
    await enviar_log(member.guild, "Membros - Entrada", f"📥 {member.mention} (`{member.id}`)\n{alt}📅 Conta de: {discord.utils.format_dt(member.created_at, 'R')}", member, 0x55ff55)

@bot.event
async def on_member_remove(member): await enviar_log(member.guild, "Membros - Saída", f"📤 {member.mention} (`{member.id}`)", member, 0xff5555)
@bot.event
async def on_voice_state_update(member, before, after):
    if before.channel != after.channel:
        if not before.channel: await enviar_log(member.guild, "🔊 Voz - Entrou", f"{member.mention} entrou em {after.channel.mention}", member, 0x55ff55)
        elif not after.channel: await enviar_log(member.guild, "🔊 Voz - Saiu", f"{member.mention} saiu de {before.channel.mention}", member, 0xff5555)
        else: await enviar_log(member.guild, "🔊 Voz - Moveu", f"{member.mention} foi de {before.channel.mention} para {after.channel.mention}", member, 0x55aaff)

@bot.event
async def on_guild_channel_create(channel): await enviar_log(channel.guild, "📁 Canais - Criar", f"Canal {channel.mention} criado.", color=0x55ff55)
@bot.event
async def on_guild_channel_delete(channel): await enviar_log(channel.guild, "📁 Canais - Apagar", f"Canal `{channel.name}` apagado.", color=0xff5555)
@bot.event
async def on_guild_role_create(role): await enviar_log(role.guild, "🏷️ Cargos - Criar", f"Cargo {role.mention} criado.", color=0x55ff55)
@bot.event
async def on_guild_role_delete(role): await enviar_log(role.guild, "🏷️ Cargos - Apagar", f"Cargo `{role.name}` apagado.", color=0xff5555)
@bot.event
async def on_invite_create(invite): await enviar_log(invite.guild, "✉️ Convites - Criado", f"Por {invite.inviter.mention} para {invite.channel.mention}\nLink: {invite.url}", invite.inviter, 0x55ff55)
@bot.event
async def on_thread_create(thread): await enviar_log(thread.guild, "📌 Tópicos - Criado", f"Tópico {thread.mention} criado em {thread.parent.mention}.", color=0x55ff55)
@bot.event
async def on_guild_emojis_update(guild, before, after): 
    if len(after) > len(before): await enviar_log(guild, "😀 Emojis - Novo", "Um novo emoji adicionado.", color=0x55ff55)
@bot.event
async def on_webhooks_update(channel): await enviar_log(channel.guild, "🔗 Webhooks - Atualizado", f"Webhooks modificados em {channel.mention}.", color=0x55aaff)

# ==================== TICKETS (1 por pessoa + /close) ====================
class TicketSelect(discord.ui.Select):
    def __init__(self):
        super().__init__(placeholder="🎫 Selecione o setor...", options=[
            discord.SelectOption(label="Suporte Geral", emoji="💬", value="geral"),
            discord.SelectOption(label="Denúncias", emoji="🚨", value="denuncia")
        ])

    async def callback(self, interaction: discord.Interaction):
        guild, user = interaction.guild, interaction.user
        cursor.execute("SELECT channel_id FROM tickets WHERE user_id = ?", (user.id,))
        res = cursor.fetchone()
        
        if res and guild.get_channel(res[0]):
            return await interaction.response.send_message(f"❌ Você já possui um ticket: <#{res[0]}>.", ephemeral=True)
        
        await interaction.response.defer(ephemeral=True)
        cat = guild.get_channel(obter_config(guild.id)["categoria_tickets"])
        staff = guild.get_role(obter_config(guild.id)["cargo_staff"])
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }
        if staff: overwrites[staff] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
        
        canal = await guild.create_text_channel(name=f"ticket-{user.name}", category=cat, overwrites=overwrites)
        
        cursor.execute("DELETE FROM tickets WHERE user_id = ?", (user.id,))
        cursor.execute("INSERT INTO tickets (user_id, channel_id) VALUES (?, ?)", (user.id, canal.id))
        db.commit()

        embed = discord.Embed(title="Atendimento", description=f"{user.mention}, use `/close` ou o botão para fechar.", color=COR_EMBED)
        view = discord.ui.View()
        btn = discord.ui.Button(label="Fechar Ticket", style=discord.ButtonStyle.danger, emoji="🔒")
        async def close_cb(i): await fechar_ticket(i, canal)
        btn.callback = close_cb
        view.add_item(btn)

        await canal.send(content=f"{staff.mention if staff else ''}", embed=embed, view=view)
        await interaction.followup.send(f"✅ Ticket criado: {canal.mention}", ephemeral=True)

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())

@bot.tree.command(name="painel_tickets", description="Gera o painel de tickets.")
@app_commands.default_permissions(administrator=True)
async def painel_tickets(interaction: discord.Interaction):
    cfg = obter_config(interaction.guild.id)
    url = IMAGENS_TICKETS[next((k for k in IMAGENS_TICKETS if k in cfg["nome"]), "GHOUL")]
    emb = discord.Embed(title="🎫 Central de Atendimento", description="Selecione abaixo para abrir seu ticket.", color=COR_EMBED)
    emb.set_image(url=url)
    await interaction.channel.send(embed=emb, view=TicketView())
    await interaction.response.send_message("Painel enviado!", ephemeral=True)

async def fechar_ticket(interaction, channel):
    cursor.execute("DELETE FROM tickets WHERE channel_id = ?", (channel.id,))
    db.commit()
    await interaction.response.send_message("🔒 Fechando ticket em 5 segundos...")
    await asyncio.sleep(5)
    try: await channel.delete()
    except: pass

@bot.tree.command(name="close", description="Fecha o ticket atual.")
async def cmd_close(interaction: discord.Interaction):
    cursor.execute("SELECT user_id FROM tickets WHERE channel_id = ?", (interaction.channel.id,))
    if not cursor.fetchone() and not interaction.channel.name.startswith("ticket-"):
        return await interaction.response.send_message("❌ Apenas dentro de tickets.", ephemeral=True)
    await fechar_ticket(interaction, interaction.channel)

# ==================== SORTEIO INTERATIVO & REROLL ====================
class SetupSorteioModal(discord.ui.Modal):
    def __init__(self, view, tipo):
        super().__init__(title=f"Setup - {tipo}")
        self.view_origem = view
        self.tipo = tipo
        if tipo == "Geral":
            self.titulo = discord.ui.TextInput(label="Nome", default=view.dados["titulo"])
            self.desc = discord.ui.TextInput(label="Prêmio", style=discord.TextStyle.paragraph, default=view.dados["desc"])
            self.add_item(self.titulo)
            self.add_item(self.desc)
        elif tipo == "Configs":
            self.minutos = discord.ui.TextInput(label="Duração (Minutos)", default=str(view.dados["minutos"]))
            self.ganhadores = discord.ui.TextInput(label="Ganhadores", default=str(view.dados["ganhadores"]))
            self.add_item(self.minutos)
            self.add_item(self.ganhadores)
        elif tipo == "Entradas":
            self.entradas = discord.ui.TextInput(label="Entradas Extras", default=str(view.dados["qtd_extras"]))
            self.add_item(self.entradas)

    async def on_submit(self, interaction: discord.Interaction):
        if self.tipo == "Geral":
            self.view_origem.dados["titulo"] = self.titulo.value
            self.view_origem.dados["desc"] = self.desc.value
        elif self.tipo == "Configs":
            self.view_origem.dados["minutos"] = int(self.minutos.value)
            self.view_origem.dados["ganhadores"] = int(self.ganhadores.value)
        elif self.tipo == "Entradas":
            self.view_origem.dados["qtd_extras"] = int(self.entradas.value)
        await self.view_origem.atualizar_painel(interaction)

class CargoExtraSelect(discord.ui.RoleSelect):
    def __init__(self, view_origem):
        super().__init__(placeholder="Cargo com vantagem...", custom_id="cargo_sorteio")
        self.view_origem = view_origem
    async def callback(self, interaction: discord.Interaction):
        self.view_origem.dados["cargo_extra"] = self.values[0]
        await interaction.response.send_modal(SetupSorteioModal(self.view_origem, "Entradas"))

class LorittaGiveawayView(discord.ui.View):
    def __init__(self, interaction_original):
        super().__init__(timeout=300)
        self.dados = {"titulo": "Sorteio", "desc": "Prêmio incrivel", "minutos": 60, "ganhadores": 1, "cargo_extra": None, "qtd_extras": 2, "cor": 0x29a6fe}
        
    def gerar_embed(self):
        embed = discord.Embed(title="⚙️ Painel do Sorteio", description=f"**{self.dados['titulo']}**\n```{self.dados['desc']}```", color=self.dados["cor"])
        embed.add_field(name="Duração", value=f"{self.dados['minutos']} min", inline=True)
        embed.add_field(name="Ganhadores", value=str(self.dados["ganhadores"]), inline=True)
        cargo_txt = f"{self.dados['cargo_extra'].mention} (+{self.dados['qtd_extras']})" if self.dados["cargo_extra"] else "Nenhum"
        embed.add_field(name="Cargo Boost", value=cargo_txt, inline=False)
        return embed

    async def atualizar_painel(self, interaction): await interaction.response.edit_message(embed=self.gerar_embed(), view=self)

    @discord.ui.button(label="Aparência", style=discord.ButtonStyle.primary, emoji="🎨")
    async def btn_geral(self, interaction, button): await interaction.response.send_modal(SetupSorteioModal(self, "Geral"))

    @discord.ui.button(label="Tempo/Ganhadores", style=discord.ButtonStyle.secondary, emoji="⏱️")
    async def btn_configs(self, interaction, button): await interaction.response.send_modal(SetupSorteioModal(self, "Configs"))

    @discord.ui.button(label="Cargo Vantagem", style=discord.ButtonStyle.success, emoji="✨")
    async def btn_cargo(self, interaction, button):
        view = discord.ui.View().add_item(CargoExtraSelect(self))
        await interaction.response.send_message("Escolha o cargo:", view=view, ephemeral=True)

    @discord.ui.button(label="Iniciar Sorteio", style=discord.ButtonStyle.success, emoji="✅", row=1)
    async def btn_iniciar(self, interaction, button):
        termino = discord.utils.utcnow() + datetime.timedelta(minutes=self.dados["minutos"])
        emb = discord.Embed(title=f"🎉 SORTEIO: {self.dados['titulo']}", description=f"{self.dados['desc']}\nReaja com 🎉!", color=self.dados["cor"])
        emb.add_field(name="Ganhadores", value=str(self.dados["ganhadores"]))
        emb.add_field(name="Termina", value=discord.utils.format_dt(termino, 'R'))
        if self.dados["cargo_extra"]: emb.add_field(name="✨ Vantagem", value=f"{self.dados['cargo_extra'].mention} = **{self.dados['qtd_extras']}x entradas**", inline=False)
        
        await interaction.response.edit_message(content="Iniciado!", embed=None, view=None)
        msg = await interaction.channel.send(embed=emb)
        await msg.add_reaction("🎉")
        
        bot.sorteios_ativos[msg.id] = {"ganhadores": self.dados["ganhadores"], "cargo_id": self.dados["cargo_extra"].id if self.dados["cargo_extra"] else None, "extras": self.dados["qtd_extras"]}
        self.stop()
        await asyncio.sleep(self.dados["minutos"] * 60)
        
        try:
            msg_final = await msg.channel.fetch_message(msg.id)
            dados = bot.sorteios_ativos.pop(msg.id, None)
            if not dados: return
            
            reaction = discord.utils.get(msg_final.reactions, emoji="🎉")
            users = [u async for u in reaction.users() if not u.bot]
            if not users: return await msg_final.channel.send("Sorteio cancelado (ninguém participou).")
            
            parts = []
            for u in users:
                parts.append(u)
                if dados["cargo_id"] and isinstance(u, discord.Member) and any(r.id == dados["cargo_id"] for r in u.roles):
                    parts.extend([u] * (dados["extras"] - 1))
            
            vencedores = random.sample(list(set(parts)), min(dados["ganhadores"], len(set(parts))))
            mentions = ", ".join(v.mention for v in vencedores)
            
            emb_final = msg_final.embeds[0]
            emb_final.description = f"**ENCERRADO**\n👑 **Ganhadores:** {mentions}"
            await msg_final.edit(embed=emb_final)
            await msg_final.channel.send(f"🎊 Parabéns {mentions}! Você ganhou **{self.dados['titulo']}**!")
        except Exception as e: print(f"Erro ao finalizar sorteio: {e}")

@bot.tree.command(name="sorteio", description="Cria um sorteio interativo.")
@app_commands.default_permissions(administrator=True)
async def cmd_sorteio(interaction: discord.Interaction):
    view = LorittaGiveawayView(interaction)
    await interaction.response.send_message(embed=view.gerar_embed(), view=view, ephemeral=True)

@bot.tree.command(name="reroll", description="Sorteia um novo vencedor para um sorteio.")
@app_commands.describe(mensagem_id="ID da mensagem do sorteio")
@app_commands.default_permissions(administrator=True)
async def cmd_reroll(interaction: discord.Interaction, mensagem_id: str):
    await interaction.response.defer()
    try:
        msg = await interaction.channel.fetch_message(int(mensagem_id))
        reaction = discord.utils.get(msg.reactions, emoji="🎉")
        if not reaction:
            return await interaction.followup.send("❌ Não achei a reação 🎉 nessa mensagem.")
            
        users = [u async for u in reaction.users() if not u.bot]
        if not users:
            return await interaction.followup.send("❌ Ninguém participou deste sorteio.")
            
        novo_vencedor = random.choice(users)
        
        # Opcional: Atualizar a embed original com o novo ganhador
        if msg.embeds:
            emb = msg.embeds[0]
            emb.description = f"**ENCERRADO (Reroll)**\n👑 **Novo Ganhador:** {novo_vencedor.mention}"
            await msg.edit(embed=emb)
            
        await interaction.followup.send(f"🎲 **REROLL!** O novo vencedor é: {novo_vencedor.mention}! Parabéns!")
    except discord.NotFound:
        await interaction.followup.send("❌ Mensagem não encontrada neste canal. Certifique-se de usar o comando no mesmo canal do sorteio.")
    except Exception as e:
        await interaction.followup.send(f"❌ Ocorreu um erro: {e}")

# ==================== START ====================
@bot.event
async def on_ready(): print("✅ Bot Definitivo Online! (Com Reroll e Anti-Crash integrados)")

if __name__ == "__main__":
    TOKEN = os.getenv("TOKEN")
    if TOKEN: bot.run(TOKEN)
    else: print("❌ TOKEN não encontrado.")
