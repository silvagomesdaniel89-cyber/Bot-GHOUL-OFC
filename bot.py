import asyncio
import datetime
import os
import re
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

IMAGENS_TICKETS = {
    "GHOUL": "https://cdn.discordapp.com/attachments/1444429504838631586/1454170002746769530/Banner_ticket_20250205_120340_0000.png",
    "COD": "https://cdn.discordapp.com/attachments/1183819407013707947/1469731813709578417/GHOUL_20260207_132912_0000.png",
    "BLOX_KINGS": "https://cdn.discordapp.com/attachments/1183819407013707947/1526281157635870730/file_000000002958720eab459d97fd2c5b8e.png",
    "NIGHTWARE": "https://cdn.discordapp.com/attachments/1440377531848200295/1452759780111155323/standard.gif",
    "POLIAS": "https://cdn.discordapp.com/attachments/1431364353482948608/1533832231108214864/file_000000004fd4820eb39bb046269d5d96.png",
}

TERMOS_BAN = [
    "checkmybio",
    "checkmyprofile",
    "lookmybio",
    "lookatmybio",
    "checkbio",
    "olharabiografia",
    "olheminhabio",
    "freenitro",
    "nitrogratis",
    "onlyfansfree",
]

PALAVROES = [
    "fdp",
    "filhodaputa",
    "caralho",
    "krl",
    "bosta",
    "escroto",
    "merda",
    "arrombado",
    "viado",
    "corno",
    "desgracado",
    "vagabundo",
    "porra",
    "buceta",
    "cacete",
    "puta",
    "puto",
    "cuzao",
    "pica",
    "rola",
    "xoxota",
    "vadia",
    "foder",
    "fodase",
    "tnc",
    "tomarnocu",
    "vsf",
    "vtnc",
    "pqp",
]

IMAGENS_BLOQUEADAS = [
    "9977339a644d9a62",
    "936c6c4e946cd966",
    "9748a8dcbd4a2579",
    "c48ff019712fe2c6",
    "91ac6db293ab09a6",
    "c1e1eb965c5e5cd0",
    "f5de4a08bdbd5aa5",
    "956a6e944ac9a6c9",
    "931e6ae394d3486f",
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

  async def setup_hook(self):
    self.add_view(ViewGhoul())
    self.add_view(ViewKings())
    self.add_view(ViewNightware())
    self.add_view(ViewPolias())
    self.add_view(ViewValidar())
    self.add_view(ViewFechar())
    await self.tree.sync()


bot = MeuBot()


def obter_config(guild_id):
  return CONFIG_SERVIDORES.get(guild_id)


def normalizar_texto(texto):
  texto = texto.lower()
  texto = "".join(
      c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
  )
  substituicoes = {
      "1": "i",
      "3": "e",
      "4": "a",
      "0": "o",
      "5": "s",
      "7": "t",
      "$": "s",
      "@": "a",
  }
  for orig, sub in substituicoes.items():
    texto = texto.replace(orig, sub)
  return re.sub(r"[^a-z0-9\s]", "", texto)


# ==================== SISTEMA DE PUNIÇÕES E LOGS (#950606) ====================
async def log_punicao_bonito(guild, user, staff, acao, motivo, prova_url=None):
  config = obter_config(guild.id)
  if not config:
    return

  canal = guild.get_channel(config["canal_punicoes"])
  if not canal:
    try:
      canal = await guild.fetch_channel(config["canal_punicoes"])
    except:
      return

  embed = discord.Embed(
      title=f"🔨 {config['nome']} - Punição Aplicada",
      color=0x950606,
      timestamp=discord.utils.utcnow(),
  )
  if user.display_avatar:
    embed.set_thumbnail(url=user.display_avatar.url)

  description = (
      f"👤 **Usuário:** {user.mention}\n"
      f"📛 **Nick:** `{user.name}`\n"
      f"🆔 **ID:** `{user.id}`\n"
      f"🛡️ **Staff:** {staff.mention if hasattr(staff, 'mention') else staff}\n"
      f"🚨 **Ação:** `{acao}`\n"
      f"📄 **Motivo:** {motivo}\n"
  )
  embed.description = description

  if prova_url:
    embed.set_image(url=prova_url)

  embed.set_footer(
      text=f"Segurança Ativa {config['nome']}",
      icon_url=guild.icon.url if guild.icon else None,
  )
  await canal.send(embed=embed)


async def executar_banimento(
    guild, membro, staff, motivo, acao_log, prova_url=None
):
  config = obter_config(guild.id)
  nome_servidor = config["nome"] if config else guild.name
  bot.ultimos_banimentos.add(membro.id)

  carta_dm = (
      f"**{nome_servidor} | Aviso de Banimento**\n\n"
      f"Caro(a) {membro.mention},\n\n"
      f"Você foi banido(a) por violar as nossas regras.\n\n"
      f"**Motivo:** {motivo}\n\n"
      f"A decisão de banir permanece final e não será revertida sem uma"
      f" consideração significativa da nossa equipe.\n\n"
      f"*Atenciosamente,*\n"
      f"**Equipe de Moderação - {nome_servidor}**"
  )
  try:
    await membro.send(carta_dm)
  except:
    pass

  try:
    staff_name = staff.name if hasattr(staff, "name") else str(staff)
    await membro.ban(reason=f"{staff_name} | {motivo}")
    await log_punicao_bonito(guild, membro, staff, acao_log, motivo, prova_url)
    return True
  except Exception as e:
    print(
        f"[ERRO PERMISSÃO] Não foi possível banir o usuário {membro.name}"
        f" ({membro.id}). Detalhe: {e}"
    )
    return False


async def log_filtro_automod(message, ocorrencia, texto_original):
  config = obter_config(message.guild.id)
  if not config:
    return

  canal = message.guild.get_channel(config["canal_logs"])
  if not canal:
    try:
      canal = await message.guild.fetch_channel(config["canal_logs"])
    except:
      return

  embed = discord.Embed(
      title=f"🛡️ {config['nome']} - Filtro Automático",
      color=0x950606,
      timestamp=discord.utils.utcnow(),
  )
  if message.author.display_avatar:
    embed.set_thumbnail(url=message.author.display_avatar.url)

  embed.description = (
      f"👤 **Usuário:** {message.author.mention}\n"
      f"📛 **Nick:** `{message.author.name}`\n"
      f"🆔 **ID:** `{message.author.id}`\n"
      f"💬 **Canal:** {message.channel.mention}\n"
      f"🚨 **Ocorrência:** `{ocorrencia}`\n\n"
      f"**Mensagem Deletada:**\n```{texto_original}```"
  )

  embed.set_footer(
      text=f"Segurança Ativa {config['nome']}",
      icon_url=message.guild.icon.url if message.guild.icon else None,
  )
  await canal.send(embed=embed)


# ==================== DETECÇÃO DE AÇÕES DA STAFF E LOGS ====================
@bot.event
async def on_member_join(member):
  config = obter_config(member.guild.id)
  if config:
    canal_logs = member.guild.get_channel(config["canal_logs"])
    if canal_logs:
      embed = discord.Embed(
          title=f"📥 {config['nome']} - Membro Entrou",
          description=(
              f"👤 **Membro:** {member.mention} ({member.id})\nO usuário acaba"
              " de se juntar ao servidor."
          ),
          color=0x950606,
          timestamp=discord.utils.utcnow(),
      )
      if member.display_avatar:
        embed.set_thumbnail(url=member.display_avatar.url)
      embed.set_footer(
          text=f"Segurança Ativa {config['nome']}",
          icon_url=member.guild.icon.url if member.guild.icon else None,
      )
      await canal_logs.send(embed=embed)


@bot.event
async def on_member_remove(member):
  config = obter_config(member.guild.id)
  if config:
    canal_logs = member.guild.get_channel(config["canal_logs"])
    if canal_logs:
      embed = discord.Embed(
          title=f"📤 {config['nome']} - Membro Saiu",
          description=(
              f"👤 **Membro:** {member.mention} ({member.id})\nO usuário deixou"
              " o servidor."
          ),
          color=0x950606,
          timestamp=discord.utils.utcnow(),
      )
      if member.display_avatar:
        embed.set_thumbnail(url=member.display_avatar.url)
      embed.set_footer(
          text=f"Segurança Ativa {config['nome']}",
          icon_url=member.guild.icon.url if member.guild.icon else None,
      )
      await canal_logs.send(embed=embed)


@bot.event
async def on_member_ban(guild, user):
  if user.id in bot.ultimos_banimentos:
    bot.ultimos_banimentos.discard(user.id)
    return

  await asyncio.sleep(2)
  try:
    async for entry in guild.audit_logs(
        limit=5, action=discord.AuditLogAction.ban
    ):
      if entry.target.id == user.id:
        if entry.user.id == bot.user.id:
          return
        await log_punicao_bonito(
            guild,
            user,
            entry.user,
            "Banimento (Painel/Botão Direito)",
            entry.reason or "Nenhum motivo inserido.",
        )
        return
  except:
    pass


@bot.event
async def on_member_unban(guild, user):
  await asyncio.sleep(2)
  try:
    async for entry in guild.audit_logs(
        limit=5, action=discord.AuditLogAction.unban
    ):
      if entry.target.id == user.id:
        if entry.user.id == bot.user.id:
          return
        await log_punicao_bonito(
            guild,
            user,
            entry.user,
            "Desbanimento (Painel/Botão Direito)",
            entry.reason or "Nenhum motivo inserido.",
        )
        return
  except:
    pass


@bot.event
async def on_member_update(before, after):
  config = obter_config(before.guild.id)
  if not config:
    return
  canal_logs = before.guild.get_channel(config["canal_logs"])

  if before.timed_out_until != after.timed_out_until:
    if after.id in bot.ultimos_mutes:
      bot.ultimos_mutes.discard(after.id)
      return

    await asyncio.sleep(2)
    try:
      if after.timed_out_until is not None:
        async for entry in before.guild.audit_logs(
            limit=5, action=discord.AuditLogAction.member_update
        ):
          if entry.target.id == after.id and hasattr(
              entry.after, "timed_out_until"
          ):
            if entry.user.id == bot.user.id:
              return
            tempo = after.timed_out_until - discord.utils.utcnow()
            minutos = max(1, int(tempo.total_seconds() / 60))
            await log_punicao_bonito(
                before.guild,
                after,
                entry.user,
                f"Mute ({minutos} mins - Discord)",
                entry.reason or "Aplicado via painel/botão direito.",
            )
            return
      elif after.timed_out_until is None:
        async for entry in before.guild.audit_logs(
            limit=5, action=discord.AuditLogAction.member_update
        ):
          if (
              entry.target.id == after.id
              and hasattr(entry.before, "timed_out_until")
              and not hasattr(entry.after, "timed_out_until")
          ):
            if entry.user.id == bot.user.id:
              return
            await log_punicao_bonito(
                before.guild,
                after,
                entry.user,
                "Desmutado (Discord)",
                entry.reason or "Removido via painel/botão direito.",
            )
            return
    except:
      pass

  if before.nick != after.nick:
    if canal_logs:
      embed = discord.Embed(
          title=f"👤 {config['nome']} - Alteração de Apelido",
          color=0x950606,
          timestamp=discord.utils.utcnow(),
      )
      if after.display_avatar:
        embed.set_thumbnail(url=after.display_avatar.url)
      embed.description = (
          f"👤 **Membro:** {after.mention} ({after.id})\n🏷️ **Antigo:**"
          f" `{before.nick or before.name}`\n🏷️ **Novo:** `{after.nick or after.name}`"
      )
      embed.set_footer(
          text=f"Segurança Ativa {config['nome']}",
          icon_url=before.guild.icon.url if before.guild.icon else None,
      )
      await canal_logs.send(embed=embed)


# ==================== SISTEMA DE TICKETS (#950606) ====================
class DropdownGhoul(discord.ui.Select):

  def __init__(self):
    opcoes = [
        discord.SelectOption(
            label="Denúncias",
            value="denuncias",
            description="Denúncias, ajuda técnica e revisão.",
            emoji="🚨",
        ),
        discord.SelectOption(
            label="Suporte",
            value="suporte",
            description="Recorra a uma punição (warn/mute).",
            emoji="🛠️",
        ),
        discord.SelectOption(
            label="Dúvidas",
            value="duvidas",
            description="Tire dúvidas sobre a comunidade ou regras.",
            emoji="❓",
        ),
        discord.SelectOption(
            label="Exposed",
            value="exposed",
            description="Falar sobre membro expondo outro.",
            emoji="⚠️",
        ),
    ]
    super().__init__(
        placeholder="Selecione o setor do suporte...",
        min_values=1,
        max_values=1,
        options=opcoes,
        custom_id="sel_ghoul",
    )

  async def callback(self, interaction: discord.Interaction):
    await criar_canal_ticket(interaction, self.values[0])


class DropdownKings(discord.ui.Select):

  def __init__(self):
    opcoes = [
        discord.SelectOption(
            label="Robux",
            value="robux",
            description="Comprar Robux ou ver tabelas",
            emoji="💰",
        ),
        discord.SelectOption(
            label="Gamepass",
            value="gamepass",
            description="Comprar Gamepasses do Blox Fruits",
            emoji="📦",
        ),
        discord.SelectOption(
            label="Frutas Perm",
            value="frutas_perm",
            description="Comprar Frutas Permanentes",
            emoji="🍊",
        ),
        discord.SelectOption(
            label="Frutas Físicas",
            value="frutas_fisicas",
            description="Comprar Frutas Físicas (Inventário)",
            emoji="🍎",
        ),
        discord.SelectOption(
            label="Contas GHM/Fruta",
            value="contas",
            description="Geral, Fruta Inv ou Contas Random",
            emoji="💸",
        ),
    ]
    super().__init__(
        placeholder="Selecione a categoria correta no menu abaixo...",
        min_values=1,
        max_values=1,
        options=opcoes,
        custom_id="sel_kings",
    )

  async def callback(self, interaction: discord.Interaction):
    await criar_canal_ticket(interaction, self.values[0])


class DropdownNightware(discord.ui.Select):

  def __init__(self):
    opcoes = [
        discord.SelectOption(
            label="Comprar",
            value="compras",
            description="Adquirir produtos de nossa loja.",
            emoji="🛒",
        ),
        discord.SelectOption(
            label="Financeiro",
            value="financeiro",
            description="Tratar de pagamentos, reembolsos e faturamento.",
            emoji="💳",
        ),
        discord.SelectOption(
            label="Suporte",
            value="suporte",
            description="Atendimento geral para dúvidas e problemas.",
            emoji="🛠️",
        ),
    ]
    super().__init__(
        placeholder="Selecione a categoria...",
        min_values=1,
        max_values=1,
        options=opcoes,
        custom_id="sel_nightware",
    )

  async def callback(self, interaction: discord.Interaction):
    await criar_canal_ticket(interaction, self.values[0])


class DropdownPolias(discord.ui.Select):

  def __init__(self):
    opcoes = [
        discord.SelectOption(
            label="Suporte / Dúvidas",
            value="suporte",
            description="Suporte geral e dúvidas sobre o servidor.",
            emoji="🛠️",
        ),
        discord.SelectOption(
            label="Parcerias",
            value="parcerias",
            description="Faça parceria com o servidor POLIAS.",
            emoji="🤝",
        ),
        discord.SelectOption(
            label="Denúncias",
            value="denuncias",
            description="Denúncias e ajuda com membros.",
            emoji="🚨",
        ),
    ]
    super().__init__(
        placeholder="Selecione o setor de atendimento...",
        min_values=1,
        max_values=1,
        options=opcoes,
        custom_id="sel_polias",
    )

  async def callback(self, interaction: discord.Interaction):
    await criar_canal_ticket(interaction, self.values[0])


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

  @discord.ui.button(
      label="Validar",
      style=discord.ButtonStyle.danger,
      emoji="🎫",
      custom_id="btn_validar_cod",
  )
  async def validar(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    await criar_canal_ticket(interaction, "coldawn")


class ViewFechar(discord.ui.View):

  def __init__(self):
    super().__init__(timeout=None)

  @discord.ui.button(
      label="Fechar Ticket",
      style=discord.ButtonStyle.danger,
      emoji="🔒",
      custom_id="btn_fechar",
  )
  async def fechar(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    await interaction.response.send_message(
        "🔒 Fechando canal em 5 segundos...", ephemeral=True
    )
    await asyncio.sleep(5)
    await interaction.channel.delete()


async def criar_canal_ticket(interaction: discord.Interaction, setor: str):
  config = obter_config(interaction.guild.id)
  if not config or interaction.response.is_done():
    return
  categoria = discord.utils.get(
      interaction.guild.categories, id=config["categoria_tickets"]
  )
  cargo_staff = interaction.guild.get_role(config["cargo_staff"])

  overwrites = {
      interaction.guild.default_role: discord.PermissionOverwrite(
          view_channel=False
      ),
      interaction.user: discord.PermissionOverwrite(
          view_channel=True, send_messages=True, attach_files=True
      ),
      interaction.guild.me: discord.PermissionOverwrite(
          view_channel=True, send_messages=True, manage_channels=True
      ),
  }
  if cargo_staff:
    overwrites[cargo_staff] = discord.PermissionOverwrite(
        view_channel=True, send_messages=True
    )

  canal = await interaction.guild.create_text_channel(
      name=f"ticket-{interaction.user.name}-{setor}",
      category=categoria,
      overwrites=overwrites,
  )

  embed = discord.Embed(
      title=f"🚨 {config['nome']} - Atendimento",
      description=(
          f"Olá {interaction.user.mention},\n\nSeu ticket para"
          f" **{setor.upper()}** foi aberto com sucesso!\nDescreva"
          " detalhadamente o que precisa abaixo para que a equipe possa te"
          " responder."
      ),
      color=0x950606,
  )
  await canal.send(
      content=f"{interaction.user.mention} {cargo_staff.mention if cargo_staff else ''}",
      embed=embed,
      view=ViewFechar(),
  )
  await interaction.response.send_message(
      f"✅ Ticket criado em {canal.mention}!", ephemeral=True
  )


# ==================== AUTOMODERAÇÃO ATIVA E FORTE ====================
@bot.event
async def on_message(message):
  if message.author.bot or not message.guild:
    return
  config = obter_config(message.guild.id)
  if not config:
    return

  texto_norm = normalizar_texto(message.content)
  texto_junto = re.sub(r"\s+", "", texto_norm)

  # 1. Filtro de Termos Proibidos
  for termo in TERMOS_BAN:
    if termo in texto_junto:
      bot.mensagens_ignoradas.add(message.id)
      try:
        await message.delete()
      except:
        pass
      await executar_banimento(
          message.guild,
          message.author,
          bot.user,
          f"Tentativa de golpe (Mensagem Fake): `{termo}`",
          "Ban (Automático)",
      )
      return

  # 2. Filtro de Palavrões
  for palavrao in PALAVROES:
    if palavrao in texto_junto:
      bot.mensagens_ignoradas.add(message.id)
      try:
        await message.delete()
      except:
        pass
      await log_filtro_automod(
          message, "Palavrão/Xingamento Detectado", message.content
      )
      return

  # Coleta URLs de mídias
  urls_imagens = []
  if message.attachments:
    for anexo in message.attachments:
      filename_lower = anexo.filename.lower()
      if any(
          filename_lower.endswith(ext)
          for ext in [".png", ".jpg", ".jpeg", ".webp", ".gif"]
      ):
        urls_imagens.append(anexo.url)

  links_no_texto = re.findall(
      r"(https?://\S+\.(?:png|jpg|jpeg|webp|gif)(?:\?\S+)?)", message.content
  )
  urls_imagens.extend(links_no_texto)

  if urls_imagens:
    attachments_data = []
    for idx, url in enumerate(urls_imagens):
      try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                " (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        }
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
          nome_arquivo = f"media_{idx}.png"
          match = re.search(
              r"/([^/?#]+\.(?:png|jpg|jpeg|webp|gif))", url, re.IGNORECASE
          )
          if match:
            nome_arquivo = match.group(1)
          attachments_data.append((response.content, nome_arquivo))
      except:
        pass
    if attachments_data:
      bot.midia_cache[message.id] = attachments_data
      if len(bot.midia_cache) > 300:
        bot.midia_cache.pop(next(iter(bot.midia_cache)))

  # 3. Filtro de Imagens Proibidas (Hashed)
  for url in urls_imagens:
    try:
      headers = {
          "User-Agent": (
              "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
              " (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
          )
      }
      response = requests.get(url, headers=headers, timeout=10)
      if response.status_code == 200:
        img = Image.open(BytesIO(response.content)).convert("RGB")
        img_avg_hash = imagehash.average_hash(img)
        img_p_hash = imagehash.phash(img)
        img_d_hash = imagehash.dhash(img)

        for hash_bloqueado in IMAGENS_BLOQUEADAS:
          hash_alvo = imagehash.hex_to_hash(hash_bloqueado)
          if (
              (img_avg_hash - hash_alvo <= 8)
              or (img_p_hash - hash_alvo <= 8)
              or (img_d_hash - hash_alvo <= 8)
          ):
            bot.mensagens_ignoradas.add(message.id)
            try:
              await message.delete()
            except:
              pass
            await executar_banimento(
                message.guild,
                message.author,
                bot.user,
                "Envio de imagem proibida.",
                "Ban (Automático)",
                url,
            )
            return
    except Exception as e:
      print(f"[Aviso Automod] Erro ao processar hash da imagem {url}: {e}")

  # 4. Filtro de Convites
  if re.search(r"(discord\.gg/|discord\.com/invite/)", message.content.lower()):
    bot.mensagens_ignoradas.add(message.id)
    try:
      await message.delete()
    except:
      pass

    try:
      bot.ultimos_mutes.add(message.author.id)
      await message.author.timeout(
          datetime.timedelta(hours=1), reason="Divulgação Automática."
      )
      await log_punicao_bonito(
          message.guild,
          message.author,
          bot.user,
          "Mute 1 Hora (Automático)",
          "Divulgação de link de convite.",
      )
    except:
      pass
    return


@bot.event
async def on_message_delete(message):
  if message.author.bot or not message.guild:
    return
  if message.id in bot.mensagens_ignoradas:
    bot.mensagens_ignoradas.discard(message.id)
    return

  config = obter_config(message.guild.id)
  if config:
    canal_logs = message.guild.get_channel(config["canal_logs"])
    if canal_logs:
      embed = discord.Embed(
          title=f"🗑️ {config['nome']} - Mensagem Apagada",
          color=0x950606,
          timestamp=discord.utils.utcnow(),
      )
      if message.author.display_avatar:
        embed.set_thumbnail(url=message.author.display_avatar.url)

      conteudo = (
          message.content[:1000]
          if message.content
          else "Mensagem vazia ou apenas mídia"
      )
      embed.description = (
          f"👤 **Usuário:** {message.author.mention}"
          f" ({message.author.id})\n💬 **Canal:**"
          f" {message.channel.mention}\n\n**Conteúdo Original:**\n```{conteudo}```"
      )

      arquivos_enviar = []
      if message.id in bot.midia_cache:
        for i, (dados_binarios, nome_arquivo) in enumerate(
            bot.midia_cache[message.id]
        ):
          file = discord.File(BytesIO(dados_binarios), filename=nome_arquivo)
          arquivos_enviar.append(file)
          embed.set_image(url=f"attachment://{nome_arquivo}")
          break
        del bot.midia_cache[message.id]

      embed.set_footer(
          text=f"Segurança Ativa {config['nome']}",
          icon_url=message.guild.icon.url if message.guild.icon else None,
      )

      if arquivos_enviar:
        await canal_logs.send(embed=embed, files=arquivos_enviar)
      else:
        await canal_logs.send(embed=embed)


# ==================== COMANDOS DE BARRA (#950606) ====================
@bot.tree.command(
    name="mute", description="Silencia um membro no servidor temporariamente."
)
@app_commands.default_permissions(moderate_members=True)
async def mute_slash(
    interaction: discord.Interaction,
    membro: discord.Member,
    tempo_minutos: int,
    motivo: str = "Sem motivo especificado",
):
  await interaction.response.defer(ephemeral=True)
  try:
    bot.ultimos_mutes.add(membro.id)
    await membro.timeout(
        datetime.timedelta(minutes=tempo_minutos),
        reason=f"{interaction.user.name} | {motivo}",
    )
    await interaction.followup.send(
        f"✅ O usuário {membro.mention} foi silenciado por {tempo_minutos}"
        " minuto(s) com sucesso."
    )
    await log_punicao_bonito(
        interaction.guild,
        membro,
        interaction.user,
        f"Mute Comando ({tempo_minutos} mins)",
        motivo,
    )
  except Exception:
    await interaction.followup.send(
        "❌ Não foi possível mutar. Verifique se o meu cargo está acima do"
        " cargo desse usuário."
    )


@bot.tree.command(name="ban", description="Bane um membro do servidor.")
@app_commands.default_permissions(ban_members=True)
async def ban_slash(
    interaction: discord.Interaction,
    membro: discord.Member,
    motivo: str = "Sem motivo especificado",
):
  await interaction.response.defer(ephemeral=True)
  sucesso = await executar_banimento(
      interaction.guild, membro, interaction.user, motivo, "Banimento Comando"
  )
  if sucesso:
    await interaction.followup.send(
        f"🔨 O usuário {membro.mention} foi banido com sucesso."
    )
  else:
    await interaction.followup.send(
        "❌ Erro ao banir. Verifique se o meu cargo é superior ao da pessoa"
        " que você está tentando banir."
    )


@bot.tree.command(
    name="painel_tickets", description="Envia o painel de atendimento de tickets."
)
@app_commands.choices(
    painel=[
        app_commands.Choice(name="GHOUL", value="ghoul"),
        app_commands.Choice(name="BLOX KINGS", value="kings"),
        app_commands.Choice(name="NIGHTWARE", value="nightware"),
        app_commands.Choice(name="COD", value="cod"),
        app_commands.Choice(name="POLIAS", value="polias"),
    ]
)
@app_commands.default_permissions(administrator=True)
async def painel_slash(
    interaction: discord.Interaction, painel: app_commands.Choice[str]
):
  if painel.value == "ghoul":
    embed = discord.Embed(
        title="🛡️ CENTRAL DE ATENDIMENTO - GHOUL",
        description=(
            "**Denúncias:**\n↳ Denúncias, ajuda técnica e revisão de"
            " punições.\n\n**Suporte:**\n↳ Recorra a uma punição"
            " (warn/mute).\n\n**Dúvidas:**\n↳ Tire dúvidas sobre a comunidade ou"
            " regras do servidor.\n\n**Exposed:**\n↳ Falar sobre algum membro"
            " que está expondo outro membro.\n\n**Lembre-se:** Nossa equipe está"
            " pronta para investigar e resolver qualquer situação de forma"
            " rápida e justa. Sua privacidade será respeitada durante todo o"
            " processo!"
        ),
        color=0x950606,
    )
    embed.set_image(url=IMAGENS_TICKETS["GHOUL"])
    view = ViewGhoul()

  elif painel.value == "kings":
    embed = discord.Embed(
        title="👑 CENTRAL DE ATENDIMENTO - BLOX KINGS",
        description=(
            "Selecione a categoria correta no menu abaixo para abrir o seu"
            " ticket."
        ),
        color=0x950606,
    )
    embed.set_image(url=IMAGENS_TICKETS["BLOX_KINGS"])
    view = ViewKings()

  elif painel.value == "nightware":
    embed = discord.Embed(
        title="🛍️ CENTRAL DE ATENDIMENTO - NIGHTWARE",
        description=(
            "Selecione uma opção no menu abaixo para abrir seu ticket."
        ),
        color=0x950606,
    )
    embed.set_image(url=IMAGENS_TICKETS["NIGHTWARE"])
    view = ViewNightware()

  elif painel.value == "polias":
    embed = discord.Embed(
        title="🛡️ CENTRAL DE ATENDIMENTO - POLIAS",
        description=(
            "Selecione uma opção no menu abaixo para abrir seu ticket e falar"
            " com a nossa equipe."
        ),
        color=0x950606,
    )
    embed.set_image(url=IMAGENS_TICKETS["POLIAS"])
    view = ViewPolias()

  elif painel.value == "cod":
    embed = discord.Embed(
        title="TICKET DE COLDAWN",
        description=(
            "INFORMAMOS QUE A NOVA FUNÇÃO DO SERVIDOR \"GHOUL 👻\"\nJÁ ESTÁ"
            " DISPONÍVEL. PARA PARTICIPAR DO EVENTO\n\"LEVIATHAN\", É"
            " OBRIGATÓRIO ABRIR UM TICKET PARA\nCOMPROVAR QUE NÃO SE ENCONTRA"
            " EM PERÍODO DE\nCOOLDOWN. A COMPROVAÇÃO DO COOLDOWN DEVERÁ SER\nREALIZADA"
            " EXCLUSIVA"
        ),
        color=0x950606,
    )
    embed.set_image(url=IMAGENS_TICKETS["COD"])
    embed.set_footer(
        text="Desenvolvido por Ticket King",
        icon_url=(
            "https://cdn.discordapp.com/attachments/1183819407013707947/1469731813709578417/GHOUL_20260207_132912_0000.png"
        ),
    )
    view = ViewValidar()

  await interaction.channel.send(embed=embed, view=view)
  await interaction.response.send_message(
      f"✅ Painel **{painel.name}** enviado com sucesso!", ephemeral=True
  )


@bot.event
async def on_ready():
  print(
      f"✅ Sistema perfeito! {bot.user.name} está online, comandos"
      " sincronizados e operando com cor #950606."
  )


TOKEN = os.getenv("TOKEN")
if TOKEN:
  bot.run(TOKEN)
else:
  print("❌ ERRO: Token não encontrado no ambiente.")
