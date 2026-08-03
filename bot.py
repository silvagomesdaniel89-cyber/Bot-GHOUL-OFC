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
    },
    1489007277267620013: {
        "nome": "POLIAS",
        "canal_logs": 1489007278693814453,
        "canal_punicoes": 1533828688213311608,
        "categoria_tickets": 1533834644569456681,
        "cargo_staff": 1489007277267620020
    }
}

IMAGENS_TICKETS = {
    "GHOUL": "https://cdn.discordapp.com/attachments/1444429504838631586/1454170002746769530/Banner_ticket_20250205_120340_0000.png",
    "COD": "https://cdn.discordapp.com/attachments/1183819407013707947/1469731813709578417/GHOUL_20260207_132912_0000.png",
    "BLOX_KINGS": "https://cdn.discordapp.com/attachments/1183819407013707947/1526281157635870730/file_000000002958720eab459d97fd2c5b8e.png",
    "NIGHTWARE": "https://cdn.discordapp.com/attachments/1440377531848200295/1452759780111155323/standard.gif",
    "POLIAS": "https://cdn.discordapp.com/attachments/1431364353482948608/1533832231108214864/file_000000004fd4820eb39bb046269d5d96.png"
}

TERMOS_BAN = [
    "checkmybio", "checkmyprofile", "lookmybio", "lookatmybio",
    "checkbio", "olharabiografia", "olheminhabio", "freenitro",
    "nitrogratis", "onlyfansfree", "hokuwin", "withdrawalsuccess"
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
    'c48ff019712fe2c6', '91ac6db293ab09a6', 'c1e1eb965c5e5cd0', 
    'f5de4a08bdbd5aa5', '956a6e944ac9a6c9', '931e6ae394d3486f'
]

# ==================== ESTRUTURA DO BOT ====================

class MeuBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents, help_command=None)
        self.mensagens_ignoradas = set()

    async def setup_hook(self):  
        self.add_view(ViewGhoul())  
        self.add_view(ViewKings())  
        self.add_view(ViewNightware())  
        self.add_view(ViewPolias())
        self.add_view(ViewValidar())  
        self.add_view(ViewControleTicket())  
        await self.tree.sync()

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

def is_staff(user: discord.Member, guild: discord.Guild) -> bool:
    if user.guild_permissions.administrator: return True
    config = obter_config(guild.id)
    if not config: return False
    cargo_id = config.get("cargo_staff")
    return any(role.id == cargo_id for role in user.roles)

# ==================== SISTEMA DE LOGS E PUNIÇÕES ====================

async def enviar_log_gs(guild, titulo, descricao, cor=0x950606, thumbnail=None, imagem=None, arquivos=None):
    config = obter_config(guild.id)
    if not config or not (canal := bot.get_channel(config["canal_logs"])):
        return
    embed = discord.Embed(title=f"🛡️ {config['nome']} - {titulo}", description=descricao, color=cor, timestamp=discord.utils.utcnow())
    if thumbnail: embed.set_thumbnail(url=thumbnail)
    if imagem: embed.set_image(url=imagem)
    embed.set_footer(text=f"Segurança Ativa GS | {config['nome']}", icon_url=guild.icon.url if guild.icon else None)
    if arquivos:
        await canal.send(embed=embed, files=arquivos)
    else:
        await canal.send(embed=embed)

async def log_punicao_bonito(guild, user, staff, acao, motivo, prova_url=None):
    config = obter_config(guild.id)
    if not config or not (canal := bot.get_channel(config["canal_punicoes"])):
        return

    embed = discord.Embed(  
        title=f"🔨 {config['nome']} - Punição Aplicada",   
        color=0x950606,   
        timestamp=discord.utils.utcnow()  
    )  
    if hasattr(user, 'display_avatar') and user.display_avatar:   
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
    if prova_url: embed.set_image(url=prova_url)  
    embed.set_footer(text=f"Segurança Ativa {config['nome']}", icon_url=guild.icon.url if guild.icon else None)  
    await canal.send(embed=embed)

async def executar_banimento(guild, membro, staff, motivo, acao_log, prova_url=None):
    config = obter_config(guild.id)
    nome_servidor = config["nome"] if config else guild.name

    dm_enviada = False
    carta_dm = (  
        f"⚠️ **{nome_servidor} | Aviso de Banimento**\n\n"  
        f"Caro(a) {membro.mention},\n\n"  
        f"Você foi banido(a) do servidor **{nome_servidor}** por violar nossas diretrizes de segurança.\n\n"  
        f"📄 **Motivo:** {motivo}\n\n"  
        f"*Atenciosamente,*\n**Equipe de Segurança - {nome_servidor}**"  
    )  
    try: 
        await membro.send(carta_dm)
        dm_enviada = True
    except Exception as e:  
        print(f"[DM FALHOU] {membro.name}: {e}")

    try:  
        await membro.ban(reason=f"{staff.name if hasattr(staff, 'name') else staff} | {motivo}")  
        await log_punicao_bonito(guild, membro, staff, acao_log, motivo, prova_url)  
        if not dm_enviada:
            await enviar_log_gs(guild, "Aviso de DM Privada", f"⚠️ O membro {membro.mention} foi banido, mas tem DMs fechadas no PV.", color=0xf1c40f)
        return True  
    except Exception as e:  
        print(f"[ERRO BAN] {membro.name}: {e}")
        await enviar_log_gs(
            guild, 
            "❌ FALHA AO BANIR MEMBRO", 
            f"Não foi possível banir o membro {membro.mention} (`{membro.id}`).\n\n"
            f"📌 **Motivo do Erro:** O cargo do membro é igual/superior ao do Bot ou o Bot não tem permissão de Banir Administradores.\n"
            f"🛠️ **Detalhe:** `{e}`", 
            color=0xe74c3c
        )
        return False

# ==================== AUTOMODERAÇÃO CORRIGIDA ====================

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild: return
    config = obter_config(message.guild.id)
    if not config: return

    texto_norm = normalizar_texto(message.content)  
    texto_junto = re.sub(r'\s+', '', texto_norm)  

    # 1. Filtro de Termos de Ban Direto
    for termo in TERMOS_BAN:  
        if termo in texto_junto:  
            bot.mensagens_ignoradas.add(message.id)  
            try: await message.delete()  
            except: pass  
            
            try:
                aviso_chat = await message.channel.send(f"{message.author.mention}, você não pode mandar link seu jumento! 🐴")
                await asyncio.sleep(5)
                await aviso_chat.delete()
            except: pass

            await enviar_log_gs(
                message.guild, 
                "Mensagem Apagada (Termo Proibido)", 
                f"👤 **Autor:** {message.author.mention}\n💬 **Canal:** {message.channel.mention}\n📝 **Texto:** ```{message.content[:800]}```",
                color=0x950606
            )
            await executar_banimento(message.guild, message.author, bot.user, f"Divulgação/Mensagem Suspeita: `{termo}`", "Ban Automático (Texto)")  
            return  

    # 2. Filtro de Palavrões
    for palavrao in PALAVROES:  
        if palavrao in texto_junto:  
            bot.mensagens_ignoradas.add(message.id)  
            try: await message.delete()  
            except: pass  
            
            try:
                aviso_chat = await message.channel.send(f"{message.author.mention}, cuidado com seu linguajar seu boboca! 🫵")
                await asyncio.sleep(5)
                await aviso_chat.delete()
            except: pass

            await enviar_log_gs(
                message.guild, 
                "Mensagem Apagada (Palavrão)", 
                f"👤 **Membro:** {message.author.mention}\n💬 **Canal:** {message.channel.mention}\n📝 **Texto:** ```{message.content[:800]}```", 
                color=0xe67e22
            )  
            return   

    # 3. Processamento de Imagens e Mídia
    urls_imagens = []  
    if message.attachments:  
        for anexo in message.attachments:  
            if (anexo.content_type and "image" in anexo.content_type) or any(anexo.filename.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp", ".gif"]):  
                urls_imagens.append(anexo.url)  
      
    links_no_texto = re.findall(r'https?://\S+', message.content)  
    for link in links_no_texto:
        if any(ext in link.lower() for ext in ['.png', '.jpg', '.jpeg', '.webp', '.gif', 'cdn.discordapp.com', 'media.discordapp.net']):
            urls_imagens.append(link)

    # Verificação de Imagens Proibidas -> APAGA, LOGA E TENTA BANIR
    for url in urls_imagens:  
        try:  
            headers = {"User-Agent": "Mozilla/5.0"}  
            response = requests.get(url, headers=headers, timeout=5)  
            if response.status_code == 200:  
                img = Image.open(BytesIO(response.content)).convert('RGB')  
                img_avg_hash = imagehash.average_hash(img)  
                  
                for hash_bloqueado in IMAGENS_BLOQUEADAS:  
                    hash_alvo = imagehash.hex_to_hash(hash_bloqueado)  
                    if (img_avg_hash - hash_alvo <= 8):  
                        bot.mensagens_ignoradas.add(message.id)  
                        try: await message.delete()  
                        except: pass  
                        
                        try:
                            aviso_chat = await message.channel.send(f"{message.author.mention}, você não pode mandar imagem proibida/golpe seu jumento! 🐴")
                            await asyncio.sleep(5)
                            await aviso_chat.delete()
                        except: pass

                        await enviar_log_gs(
                            message.guild, 
                            "⚠️ Imagem Proibida Deletada", 
                            f"👤 **Autor:** {message.author.mention}\n💬 **Canal:** {message.channel.mention}\n✅ **Ação:** A imagem foi apagada com sucesso.", 
                            color=0x950606, 
                            imagem=url
                        )
                        await executar_banimento(message.guild, message.author, bot.user, "Envio de Imagem Proibida/Golpe/NSFW", "Ban Automático (Imagem Proibida)", url)  
                        return  
        except Exception as e:
            print(f"[ERRO HASH IMAGEM]: {e}")

    # 4. Anti-Invite com Mute Corrigido e Aviso no Chat
    if re.search(r'(discord\.gg/|discord\.com/invite/)', message.content.lower()):  
        bot.mensagens_ignoradas.add(message.id)  
        try: await message.delete()  
        except: pass  
        
        try:
            aviso_chat = await message.channel.send(f"{message.author.mention}, você não pode mandar link seu jumento! 🐴")
            await asyncio.sleep(5)
            await aviso_chat.delete()
        except: pass

        await enviar_log_gs(
            message.guild, 
            "Mensagem Apagada (Convite)", 
            f"👤 **Autor:** {message.author.mention}\n💬 **Canal:** {message.channel.mention}\n📝 **Texto:** ```{message.content[:800]}```", 
            color=0xe74c3c
        )

        try:
            await message.author.send(f"⚠️ **{message.guild.name}** | Você recebeu um Mute de 1 hora por divulgar convites de outros servidores.")
        except: pass

        try:  
            await message.author.timeout(datetime.timedelta(hours=1), reason="Divulgação Automática de Convite.")  
            await log_punicao_bonito(message.guild, message.author, bot.user, "Mute 1 Hora", "Divulgação de convite de servidor.")  
        except Exception as e:  
            await enviar_log_gs(
                message.guild, 
                "❌ FALHA AO MUTAR MEMBRO", 
                f"Não foi possível mutar {message.author.mention}.\n📌 O cargo do Bot deve estar **acima** do membro na hierarquia de cargos!\nErro: `{e}`",
                color=0xe74c3c
            )
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
        embed.description = f"👤 **Usuário:** {message.author.mention} (`{message.author.id}`)\n💬 **Canal:** {message.channel.mention}\n\n**Conteúdo Original:**\n```{conteudo}```"  
        embed.set_footer(text=f"Segurança Ativa {config['nome']}", icon_url=message.guild.icon.url if message.guild.icon else None)  
        await canal_logs.send(embed=embed)

# ==================== TICKETS & PAINÉIS FIXOS ====================

class ViewControleTicket(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Reivindicar", style=discord.ButtonStyle.success, emoji="🙋‍♂️", custom_id="btn_reivindicar_ticket")  
    async def reivindicar(self, interaction: discord.Interaction, button: discord.ui.Button):  
        if not is_staff(interaction.user, interaction.guild):  
            return await interaction.response.send_message("❌ Apenas membros da Staff podem reivindicar tickets.", ephemeral=True)  
          
        config = obter_config(interaction.guild.id)  
        cargo_staff = interaction.guild.get_role(config["cargo_staff"]) if config else None  
          
        overwrites = interaction.channel.overwrites  
        if cargo_staff:  
            overwrites[cargo_staff] = discord.PermissionOverwrite(view_channel=False)  
        overwrites[interaction.user] = discord.PermissionOverwrite(view_channel=True, send_messages=True)  
          
        await interaction.channel.edit(overwrites=overwrites)  
        button.disabled = True  
        button.label = f"Reivindicado por {interaction.user.name}"  
        await interaction.response.edit_message(view=self)  
          
        embed = discord.Embed(description=f"✅ O atendimento foi assumido por {interaction.user.mention}.", color=0x950606)  
        await interaction.channel.send(embed=embed)  

    @discord.ui.button(label="Fechar Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="btn_fechar_ticket_novo")  
    async def fechar(self, interaction: discord.Interaction, button: discord.ui.Button):  
        if not is_staff(interaction.user, interaction.guild):  
            return await interaction.response.send_message("❌ Apenas membros da Staff podem fechar tickets.", ephemeral=True)  
          
        await interaction.response.send_message("🔒 Este ticket será fechado e deletado em 5 segundos...", ephemeral=False)  
        await asyncio.sleep(5)  
        try: await interaction.channel.delete()  
        except: pass

async def criar_canal_ticket(interaction: discord.Interaction, setor: str, mensagem_personalizada: str = None):
    config = obter_config(interaction.guild.id)
    if not config: return

    nome_esperado = f"ticket-{interaction.user.name.lower()}"  
      
    for canal_existente in interaction.guild.text_channels:  
        if canal_existente.name.startswith(f"ticket-{interaction.user.name.lower()}"):  
            return await interaction.response.send_message(f"❌ Você já possui um ticket aberto em {canal_existente.mention}!", ephemeral=True)  

    categoria = discord.utils.get(interaction.guild.categories, id=config["categoria_tickets"])  
    cargo_staff = interaction.guild.get_role(config["cargo_staff"])  
      
    overwrites = {  
        interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),  
        interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True),  
        interaction.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)  
    }  
    if cargo_staff:   
        overwrites[cargo_staff] = discord.PermissionOverwrite(view_channel=True, send_messages=True)  

    canal = await interaction.guild.create_text_channel(name=f"{nome_esperado}-{setor}", category=categoria, overwrites=overwrites)  
    desc_msg = mensagem_personalizada if mensagem_personalizada else f"Seu ticket para **{setor.upper()}** foi aberto com sucesso!\nDescreva detalhadamente o que precisa."  
      
    embed = discord.Embed(title=f"🚨 {config['nome']} - Atendimento", description=f"Olá {interaction.user.mention},\n\n{desc_msg}", color=0x950606)  
    await canal.send(content=f"{interaction.user.mention} {cargo_staff.mention if cargo_staff else ''}", embed=embed, view=ViewControleTicket())  
    await interaction.response.send_message(f"✅ Ticket criado em {canal.mention}!", ephemeral=True)

class DropdownGhoul(discord.ui.Select):
    def __init__(self):
        opcoes = [
            discord.SelectOption(label="Denúncias", value="denuncias", emoji="🚨"),
            discord.SelectOption(label="Suporte", value="suporte", emoji="🛠️"),
            discord.SelectOption(label="Dúvidas", value="duvidas", emoji="❓"),
            discord.SelectOption(label="Exposed", value="exposed", emoji="⚠️")
        ]
        super().__init__(placeholder="Selecione o setor do suporte...", min_values=1, max_values=1, options=opcoes, custom_id="sel_ghoul")
    async def callback(self, interaction: discord.Interaction):
        await criar_canal_ticket(interaction, self.values[0])

class DropdownKings(discord.ui.Select):
    def __init__(self):
        opcoes = [
            discord.SelectOption(label="Robux", value="robux", emoji="💰"),
            discord.SelectOption(label="Gamepass", value="gamepass", emoji="📦"),
            discord.SelectOption(label="Frutas Perm", value="frutas_perm", emoji="🍊"),
            discord.SelectOption(label="Frutas Físicas", value="frutas_fisicas", emoji="🍎"),
            discord.SelectOption(label="Contas GHM/Fruta", value="contas", emoji="💸")
        ]
        super().__init__(placeholder="Selecione a categoria...", min_values=1, max_values=1, options=opcoes, custom_id="sel_kings")
    async def callback(self, interaction: discord.Interaction):
        await criar_canal_ticket(interaction, self.values[0])

class DropdownNightware(discord.ui.Select):
    def __init__(self):
        opcoes = [
            discord.SelectOption(label="Comprar", value="compras", emoji="🛒"),
            discord.SelectOption(label="Financeiro", value="financeiro", emoji="💳"),
            discord.SelectOption(label="Suporte", value="suporte", emoji="🛠️")
        ]
        super().__init__(placeholder="Selecione a categoria...", min_values=1, max_values=1, options=opcoes, custom_id="sel_nightware")
    async def callback(self, interaction: discord.Interaction):
        await criar_canal_ticket(interaction, self.values[0])

class DropdownPolias(discord.ui.Select):
    def __init__(self):
        opcoes = [
            discord.SelectOption(label="Parcerias", value="parcerias", emoji="🤝"),
            discord.SelectOption(label="Suporte / Dúvidas", value="suporte", emoji="🛠️")
        ]
        super().__init__(placeholder="Selecione o tipo de atendimento...", min_values=1, max_values=1, options=opcoes, custom_id="sel_polias")
    async def callback(self, interaction: discord.Interaction):
        await criar_canal_ticket(interaction, self.values[0], "Olá! Caso queira parceria ou suporte, detalhe abaixo o que você precisa.")

class ViewGhoul(discord.ui.View):
    def __init__(self): super().__init__(timeout=None); self.add_item(DropdownGhoul())
class ViewKings(discord.ui.View):
    def __init__(self): super().__init__(timeout=None); self.add_item(DropdownKings())
class ViewNightware(discord.ui.View):
    def __init__(self): super().__init__(timeout=None); self.add_item(DropdownNightware())
class ViewPolias(discord.ui.View):
    def __init__(self): super().__init__(timeout=None); self.add_item(DropdownPolias())
class ViewValidar(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Validar", style=discord.ButtonStyle.danger, emoji="🎫", custom_id="btn_validar_cod")
    async def validar(self, interaction: discord.Interaction, button: discord.ui.Button): await criar_canal_ticket(interaction, "coldawn")

# ==================== COMANDOS SLASH ====================

@bot.tree.command(name="painel_antigo", description="Envia os painéis fixos do servidor.")
@app_commands.choices(painel=[
    app_commands.Choice(name="GHOUL", value="ghoul"),
    app_commands.Choice(name="BLOX KINGS", value="kings"),
    app_commands.Choice(name="NIGHTWARE", value="nightware"),
    app_commands.Choice(name="POLIAS", value="polias"),
    app_commands.Choice(name="COD", value="cod")
])
@app_commands.default_permissions(administrator=True)
async def painel_slash(interaction: discord.Interaction, painel: app_commands.Choice[str]):
    if painel.value == "ghoul":
        embed = discord.Embed(title="🛡️ CENTRAL DE ATENDIMENTO - GHOUL", description="Selecione o suporte abaixo.", color=0x950606)
        embed.set_image(url=IMAGENS_TICKETS["GHOUL"])
        view = ViewGhoul()
    elif painel.value == "kings":
        embed = discord.Embed(title="👑 CENTRAL DE ATENDIMENTO - BLOX KINGS", description="Selecione a categoria desejada.", color=0x950606)
        embed.set_image(url=IMAGENS_TICKETS["BLOX_KINGS"])
        view = ViewKings()
    elif painel.value == "nightware":
        embed = discord.Embed(title="🛍️ CENTRAL DE ATENDIMENTO - NIGHTWARE", description="Selecione uma opção de atendimento.", color=0x950606)
        embed.set_image(url=IMAGENS_TICKETS["NIGHTWARE"])
        view = ViewNightware()
    elif painel.value == "polias":
        embed = discord.Embed(title="🛡️ CENTRAL DE ATENDIMENTO - POLIAS", description="Caso queira parceria ou suporte, selecione abaixo.", color=0x950606)
        embed.set_image(url=IMAGENS_TICKETS["POLIAS"])
        view = ViewPolias()
    elif painel.value == "cod":
        embed = discord.Embed(title="TICKET DE COLDAWN", description="Validação de suporte.", color=0x950606)
        embed.set_image(url=IMAGENS_TICKETS["COD"])
        view = ViewValidar()

    await interaction.channel.send(embed=embed, view=view)  
    await interaction.response.send_message(f"✅ Painel **{painel.name}** enviado com sucesso!", ephemeral=True)

@bot.event
async def on_ready():
    print(f"✅ Sistema corrigido e online! Logado como {bot.user.name}.")

TOKEN = os.getenv('TOKEN')
if TOKEN:
    bot.run(TOKEN)
else:
    print("❌ ERRO: Token não encontrado no ambiente.")
