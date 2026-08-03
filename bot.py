import os
import discord
import requests
import imagehash
import asyncio
import re
import random
import unicodedata
import datetime
from discord.ext import commands, tasks
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
    "POLIAS": "https://cdn.discordapp.com/attachments/1431364353482948608/1533832231108214864/file_000000004fd4820eb39bb046269d5d96.png?ex=6a71ec15&is=6a709a95&hm=ef81b6bd0f737f70605dcb5f3814926b699c8a091209c990f48bbe2fa1e70c3d"
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
    'c48ff019712fe2c6', '91ac6db293ab09a6', 'c1e1eb965c5e5cd0', 
    'f5de4a08bdbd5aa5', '956a6e944ac9a6c9', '931e6ae394d3486f'
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

# ==================== SISTEMA DE PUNIÇÕES E LOGS GS ====================

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
    if prova_url: embed.set_image(url=prova_url)  
    embed.set_footer(text=f"Segurança Ativa {config['nome']}", icon_url=guild.icon.url if guild.icon else None)  
    await canal.send(embed=embed)

async def executar_banimento(guild, membro, staff, motivo, acao_log, prova_url=None):
    config = obter_config(guild.id)
    nome_servidor = config["nome"] if config else guild.name
    bot.ultimos_banimentos.add(membro.id)

    carta_dm = (  
        f"**{nome_servidor} | Aviso de Banimento**\n\n"  
        f"Caro(a) {membro.mention},\n\n"  
        f"Você foi banido(a) do servidor **{nome_servidor}** por violar nossas diretrizes de segurança.\n\n"  
        f"**Motivo:** {motivo}\n\n"  
        f"*Atenciosamente,*\n**Equipe de Moderação - {nome_servidor}**"  
    )  
    try: await membro.send(carta_dm)  
    except: pass   

    try:  
        await membro.ban(reason=f"{staff.name if hasattr(staff, 'name') else staff} | {motivo}")  
        await log_punicao_bonito(guild, membro, staff, acao_log, motivo, prova_url)  
        return True  
    except Exception as e:  
        print(f"[ERRO BAN] {membro.name}: {e}")  
        return False

# 1. Filtro de Termos de Ban Direto
    for termo in TERMOS_BAN:  
        if termo in texto_junto:  
            bot.mensagens_ignoradas.add(message.id)  
            try: await message.delete()  
            except: pass  
            
            # Mensagem no chat para o usuário puxando a orelha
            try:
                aviso_chat = await message.channel.send(f"{message.author.mention}, você não pode mandar link ou termo proibido aqui seu jumento! 🐴")
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
            
            # Mensagem no chat para o palavrão
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
# ... [dentro do evento on_message] ...

    # Verificação de Imagens Proibidas -> APAGA, LOGA E DEPOIS TENTA BANIR
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
                        # 1. APAGA A MENSAGEM PRIMEIRO (Não importa o cargo)
                        bot.mensagens_ignoradas.add(message.id)  
                        try: 
                            await message.delete()  
                        except discord.Forbidden: 
                            pass # Bot sem permissão de apagar mensagens no canal
                        
                        # 2. GERA O LOG DE DELEÇÃO IMEDIATAMENTE
                        await enviar_log_gs(
                            message.guild, 
                            "⚠️ Imagem Proibida Deletada", 
                            f"👤 **Autor:** {message.author.mention}\n💬 **Canal:** {message.channel.mention}\n✅ **Ação:** A imagem foi apagada com sucesso, mesmo que a punição falhe.", 
                            color=0x950606, 
                            imagem=url
                        )
                        
                        # 3. TENTA EXECUTAR O BANIMENTO
                        # Se o membro tiver cargo maior, a função 'executar_banimento' vai falhar
                        # e enviar um log de erro de hierarquia, mas a imagem já foi apagada acima!
                        await executar_banimento(
                            message.guild, 
                            message.author, 
                            bot.user, 
                            "Envio de Imagem Proibida/Golpe/NSFW", 
                            "Ban Automático", 
                            url
                        )  
                        return  
        except Exception as e:
            print(f"[ERRO HASH IMAGEM]: {e}")

# ==================== SISTEMA DE LOGS ESTILO GAMERSAFER / GS ====================

@bot.event
async def on_message_edit(before, after):
    if before.author.bot or not before.guild or before.content == after.content: return
    desc = (
        f"👤 **Autor:** {before.author.mention} (`{before.author.id}`)\n"
        f"💬 **Canal:** {before.channel.mention}\n\n"
        f"📝 **Antes:**\n```{before.content[:800]}```\n"
        f"✏️ **Depois:**\n```{after.content[:800]}```"
    )
    await enviar_log_gs(before.guild, "Mensagem Editada", desc, thumbnail=before.author.display_avatar.url if before.author.display_avatar else None)

@bot.event
async def on_member_join(member):
    desc = f"📥 **Membro Entrou:** {member.mention}\n📛 **Nome:** `{member.name}`\n🆔 **ID:** `{member.id}`\n📅 **Conta Criada em:** <t:{int(member.created_at.timestamp())}:R>"
    await enviar_log_gs(member.guild, "Novo Membro", desc, color=0x2ecc71, thumbnail=member.display_avatar.url if member.display_avatar else None)

@bot.event
async def on_member_remove(member):
    desc = f"📤 **Membro Saiu:** {member.mention}\n📛 **Nome:** `{member.name}`\n🆔 **ID:** `{member.id}`"
    await enviar_log_gs(member.guild, "Saída de Membro", desc, color=0xe74c3c, thumbnail=member.display_avatar.url if member.display_avatar else None)

@bot.event
async def on_member_ban(guild, user):
    desc = f"🔨 **Membro Banido:** {user.mention}\n📛 **Nome:** `{user.name}`\n🆔 **ID:** `{user.id}`"
    await enviar_log_gs(guild, "Membro Banido", desc, color=0x950606)

@bot.event
async def on_member_unban(guild, user):
    desc = f"🔓 **Membro Desbanido:** {user.name}\n🆔 **ID:** `{user.id}`"
    await enviar_log_gs(guild, "Membro Desbanido", desc, color=0x3498db)

@bot.event
async def on_member_update(before, after):
    if before.roles == after.roles: return
    added_roles = [r for r in after.roles if r not in before.roles]
    removed_roles = [r for r in before.roles if r not in after.roles]
    if not added_roles and not removed_roles: return

    desc = f"👤 **Membro:** {after.mention} (`{after.name}`)\n"
    if added_roles: desc += f"➕ **Cargos Adicionados:** {', '.join([r.mention for r in added_roles])}\n"
    if removed_roles: desc += f"➖ **Cargos Removidos:** {', '.join([r.mention for r in removed_roles])}\n"

    try:
        async for entry in after.guild.audit_logs(limit=2, action=discord.AuditLogAction.member_role_update):
            if entry.target.id == after.id:
                desc += f"🛡️ **Modificado por:** {entry.user.mention}\n"
                break
    except: pass

    await enviar_log_gs(after.guild, "Cargo de Membro Atualizado", desc, thumbnail=after.display_avatar.url if after.display_avatar else None)

@bot.event
async def on_voice_state_update(member, before, after):
    if before.channel == after.channel: return
    if before.channel is None and after.channel is not None:
        desc = f"👤 **Membro:** {member.mention} (`{member.name}`)\n📢 **Canal:** {after.channel.mention}"
        await enviar_log_gs(member.guild, "Entrou na Call", desc, thumbnail=member.display_avatar.url if member.display_avatar else None)
    elif before.channel is not None and after.channel is None:
        desc = f"👤 **Membro:** {member.mention} (`{member.name}`)\n📢 **Canal:** {before.channel.mention}"
        await enviar_log_gs(member.guild, "Saiu da Call", desc, color=0xe74c3c, thumbnail=member.display_avatar.url if member.display_avatar else None)
    elif before.channel != after.channel:
        desc = f"👤 **Membro:** {member.mention} (`{member.name}`)\n📤 **De:** {before.channel.mention}\n📥 **Para:** {after.channel.mention}"
        await enviar_log_gs(member.guild, "Moveu de Call", desc, color=0xf1c40f, thumbnail=member.display_avatar.url if member.display_avatar else None)

@bot.event
async def on_guild_channel_create(channel):
    desc = f"📁 **Canal Criado:** {channel.name}\n🆔 **ID:** `{channel.id}`\n📂 **Tipo:** `{channel.type}`"
    await enviar_log_gs(channel.guild, "Novo Canal Criado", desc, color=0x2ecc71)

@bot.event
async def on_guild_channel_delete(channel):
    desc = f"🗑️ **Canal Deletado:** `{channel.name}`\n🆔 **ID:** `{channel.id}`"
    await enviar_log_gs(channel.guild, "Canal Deletado", desc, color=0xe74c3c)

@bot.event
async def on_guild_role_create(role):
    desc = f"👑 **Cargo Criado:** {role.mention}\n🆔 **ID:** `{role.id}`"
    await enviar_log_gs(role.guild, "Novo Cargo Criado", desc, color=0x2ecc71)

@bot.event
async def on_guild_role_delete(role):
    desc = f"🗑️ **Cargo Deletado:** `{role.name}`\n🆔 **ID:** `{role.id}`"
    await enviar_log_gs(role.guild, "Cargo Deletado", desc, color=0xe74c3c)

@bot.event
async def on_invite_create(invite):
    desc = f"✉️ **Convite Criado:** `{invite.code}`\n👤 **Criador:** {invite.inviter.mention if invite.inviter else 'Desconhecido'}\n📌 **Canal:** {invite.channel.mention}"
    await enviar_log_gs(invite.guild, "Novo Convite Criado", desc)

@bot.event
async def on_thread_create(thread):
    desc = f"🧵 **Tópico/Thread Criado:** {thread.mention}\n📌 **Canal Pai:** {thread.parent.mention}"
    await enviar_log_gs(thread.guild, "Novo Tópico Criado", desc)

# ==================== TICKETS ====================

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

class ViewPainelDinamico(discord.ui.View):
    def __init__(self, nome_botao: str, mensagem_interna: str):
        super().__init__(timeout=None)
        self.mensagem_interna = mensagem_interna
        self.add_item(discord.ui.Button(label=nome_botao, style=discord.ButtonStyle.primary, emoji="🎫", custom_id="btn_abrir_dinamico"))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:  
        if interaction.data.get("custom_id") == "btn_abrir_dinamico":  
            await criar_canal_ticket(interaction, "atendimento", self.mensagem_interna)  
        return True

class ModalCriarPainel(discord.ui.Modal, title="Criar Painel de Ticket"):
    titulo_embed = discord.ui.TextInput(label="Título do Embed", placeholder="Ex: CENTRAL DE ATENDIMENTO", required=True)
    desc_embed = discord.ui.TextInput(label="Descrição do Embed", style=discord.TextStyle.paragraph, max_length=4000, required=True)
    nome_botao = discord.ui.TextInput(label="Nome do Botão de Abrir", default="Abrir Ticket", required=True)
    mensagem_interna = discord.ui.TextInput(label="Mensagem dentro do Ticket", style=discord.TextStyle.paragraph, placeholder="Ex: Olá, descreva em detalhes seu suporte...", required=True)
    imagem_embed = discord.ui.TextInput(label="URL da Imagem/Banner (Opcional)", placeholder="https://link.com/imagem.png", required=False)

    async def on_submit(self, interaction: discord.Interaction):  
        embed = discord.Embed(title=self.titulo_embed.value, description=self.desc_embed.value, color=0x950606)  
        if self.imagem_embed.value:
            embed.set_image(url=self.imagem_embed.value)
            
        view = ViewPainelDinamico(self.nome_botao.value, self.mensagem_interna.value)  
        await interaction.channel.send(embed=embed, view=view)  
        await interaction.response.send_message("✅ Painel criado com sucesso!", ephemeral=True)

async def criar_canal_ticket(interaction: discord.Interaction, setor: str, mensagem_personalizada: str = None):
    config = obter_config(interaction.guild.id)
    if not config: return

    nome_esperado = f"ticket-{interaction.user.name.lower()}"  
      
    for canal_existente in interaction.guild.text_channels:  
        if canal_existente.name.startswith(f"ticket-{interaction.user.name.lower()}"):  
            return await interaction.response.send_message(f"❌ Você já possui um ticket aberto em {canal_existente.mention}! Feche-o antes de abrir outro.", ephemeral=True)  

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
      
    embed = discord.Embed(  
        title=f"🚨 {config['nome']} - Atendimento",   
        description=f"Olá {interaction.user.mention},\n\n{desc_msg}",   
        color=0x950606  
    )  
      
    await canal.send(content=f"{interaction.user.mention} {cargo_staff.mention if cargo_staff else ''}", embed=embed, view=ViewControleTicket())  
    await interaction.response.send_message(f"✅ Ticket criado em {canal.mention}!", ephemeral=True)

# ==================== TICKETS FIXOS (GHOUL, BLOX KINGS, NIGHTWARE, POLIAS) ====================

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
        await criar_canal_ticket(interaction, self.values[0], "Olá! Caso queira parceria ou suporte, detalhe abaixo o que você precisa para que nossa equipe possa te ajudar.")

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

# ==================== AUTOMODERAÇÃO & BANIMENTO POR IMAGEM ====================

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
            await executar_banimento(message.guild, message.author, bot.user, f"Divulgação/Mensagem Suspeita: `{termo}`", "Ban Automático (Texto)")  
            return  

    # 2. Filtro de Palavrões
    for palavrao in PALAVROES:  
        if palavrao in texto_junto:  
            bot.mensagens_ignoradas.add(message.id)  
            try: await message.delete()  
            except: pass  
            await enviar_log_gs(
                message.guild, 
                "Palavrão Detectado", 
                f"👤 **Membro:** {message.author.mention}\n💬 **Canal:** {message.channel.mention}\n📝 **Texto:** ```{message.content}```", 
                color=0xe67e22
            )  
            return   

    # 3. Processamento de Imagens e Mídia
    urls_imagens = []  
    if message.attachments:  
        for anexo in message.attachments:  
            if any(anexo.filename.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp", ".gif"]):  
                urls_imagens.append(anexo.url)  
      
    links_no_texto = re.findall(r'(https?://\S+\.(?:png|jpg|jpeg|webp|gif)(?:\?\S+)?)', message.content)  
    urls_imagens.extend(links_no_texto)  

    if urls_imagens:  
        attachments_data = []  
        for idx, url in enumerate(urls_imagens):  
            try:  
                headers = {"User-Agent": "Mozilla/5.0"}  
                response = requests.get(url, headers=headers, timeout=5)  
                if response.status_code == 200:  
                    nome_arquivo = f"media_{idx}.png"  
                    match = re.search(r'/([^/?#]+\.(?:png|jpg|jpeg|webp|gif))', url, re.IGNORECASE)  
                    if match: nome_arquivo = match.group(1)  
                    attachments_data.append((response.content, nome_arquivo))  
            except: pass  
              
        if attachments_data:  
            bot.midia_cache[message.id] = attachments_data  
            if len(bot.midia_cache) > 300: bot.midia_cache.pop(next(iter(bot.midia_cache)))  

    # Verificação de Imagens Proibidas -> BAN AUTOMÁTICO
    for url in urls_imagens:  
        try:  
            headers = {"User-Agent": "Mozilla/5.0"}  
            response = requests.get(url, headers=headers, timeout=10)  
            if response.status_code == 200:  
                img = Image.open(BytesIO(response.content)).convert('RGB')  
                img_avg_hash = imagehash.average_hash(img)  
                  
                for hash_bloqueado in IMAGENS_BLOQUEADAS:  
                    hash_alvo = imagehash.hex_to_hash(hash_bloqueado)  
                    if (img_avg_hash - hash_alvo <= 8):  
                        bot.mensagens_ignoradas.add(message.id)  
                        try: await message.delete()  
                        except: pass  
                        # BANIMENTO IMEDIATO AO DETECTAR IMAGEM PROIBIDA
                        await executar_banimento(message.guild, message.author, bot.user, "Envio de Imagem Proibida/NSFW/Ofensiva", "Ban Automático (Imagem Proibida)", url)  
                        return  
        except Exception as e:
            print(f"[ERRO PROCESSANDO HASH IMAGEM]: {e}")

    # 4. Anti-Invite
    if re.search(r'(discord\.gg/|discord\.com/invite/)', message.content.lower()):  
        bot.mensagens_ignoradas.add(message.id)  
        try: await message.delete()  
        except: pass  
        try:  
            bot.ultimos_mutes.add(message.author.id)  
            await message.author.timeout(datetime.timedelta(hours=1), reason="Divulgação Automática.")  
            await log_punicao_bonito(message.guild, message.author, bot.user, "Mute 1 Hora", "Divulgação de convite de servidor.")  
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
        embed.description = f"👤 **Usuário:** {message.author.mention} (`{message.author.id}`)\n💬 **Canal:** {message.channel.mention}\n\n**Conteúdo Original:**\n```{conteudo}```"  
          
        arquivos_enviar = []  
        if message.id in bot.midia_cache:  
            for i, (dados_binarios, nome_arquivo) in enumerate(bot.midia_cache[message.id]):  
                file = discord.File(BytesIO(dados_binarios), filename=nome_arquivo)  
                arquivos_enviar.append(file)  
            del bot.midia_cache[message.id]   
          
        embed.set_footer(text=f"Segurança Ativa {config['nome']}", icon_url=message.guild.icon.url if message.guild.icon else None)  
          
        if arquivos_enviar:  
            embed.set_image(url=f"attachment://{arquivos_enviar[0].filename}")  
            await canal_logs.send(embed=embed, files=arquivos_enviar)   
        else:  
            await canal_logs.send(embed=embed)

# ==================== SISTEMA DE SORTEIO ESTILO LORITTA ====================

class ModalSorteio(discord.ui.Modal, title="Configurar Sorteio"):
    premio = discord.ui.TextInput(label="Prêmio (Ex: Permanent Kitsune)", required=True)
    duracao = discord.ui.TextInput(label="Tempo (Ex: 10m, 2h, 7d)", placeholder="m = minutos, h = horas, d = dias", required=True)
    ganhadores = discord.ui.TextInput(label="Quantidade de Ganhadores", default="1", required=True)
    multiplicadores = discord.ui.TextInput(
        label="Multiplicadores por Cargo (ID_CARGO:MULT)",
        style=discord.TextStyle.paragraph,
        placeholder="Ex: 123456789:3, 987654321:2 (Separe por vírgula)",
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):  
        await interaction.response.send_message("🎉 Gerando sorteio...", ephemeral=True)  
          
        tempo_str = self.duracao.value.lower().strip()  
        multiplicador = 60 if 'm' in tempo_str else 3600 if 'h' in tempo_str else 86400 if 'd' in tempo_str else 1  
        segundos = int(re.sub(r'\D', '', tempo_str)) * multiplicador  
        fim = discord.utils.utcnow() + datetime.timedelta(seconds=segundos)  
          
        dict_mult = {}  
        if self.multiplicadores.value:  
            for par in self.multiplicadores.value.split(","):  
                try:  
                    cargo_id, mult = par.split(":")  
                    dict_mult[int(cargo_id.strip())] = int(mult.strip())  
                except: pass  

        embed = discord.Embed(
            title=f"🎁 Sorteio: {self.premio.value}", 
            description=(
                f"Reaja com 🎉 para participar!\n\n"
                f"**Termina em:** <t:{int(fim.timestamp())}:R> (<t:{int(fim.timestamp())}:F>)\n"
                f"**Ganhadores:** {self.ganhadores.value}"
            ), 
            color=0x950606
        )  
          
        if dict_mult:  
            txt_mult = "\n".join([f"<@&{c}> -> {m}x entradas" for c, m in dict_mult.items()])  
            embed.add_field(
                name="Entradas Extras:", 
                value=f"{txt_mult}\n\nSe você possuir mais de um cargo, receberá a maior quantidade de entradas!",
                inline=False
            )  
              
        msg = await interaction.channel.send(embed=embed)  
        await msg.add_reaction("🎉")  
          
        asyncio.create_task(finalizar_sorteio(interaction.channel, msg.id, self.premio.value, int(self.ganhadores.value), segundos, dict_mult))

async def finalizar_sorteio(canal, msg_id, premio, num_ganhadores, delay, dict_mult):
    await asyncio.sleep(delay)
    try:
        msg = await canal.fetch_message(msg_id)
        users = [user async for user in msg.reactions[0].users() if not user.bot]

        if not users:  
            return await canal.send("Ninguém participou do sorteio. 😔")  
              
        pool = []  
        for u in users:  
            chances = 1  
            if hasattr(u, "roles"):  
                for role in u.roles:  
                    if role.id in dict_mult:  
                        chances = max(chances, dict_mult[role.id])  
            pool.extend([u] * chances)   
              
        vencedores = random.sample(pool, min(len(set(pool)), num_ganhadores))  
        mensoes = ", ".join([v.mention for v in vencedores])  
          
        embed_fim = discord.Embed(title=f"🎉 Sorteio Encerrado: {premio}", description=f"**Ganhador(es):** {mensoes}\nObrigado a todos que participaram!", color=0x950606)  
        await msg.edit(embed=embed_fim)  
        await canal.send(f"Parabéns {mensoes}! Vocês ganharam **{premio}**! Entrem em contato com a Staff.")  
    except Exception as e:  
        print(f"Erro ao finalizar sorteio: {e}")

# ==================== COMANDOS SLASH ====================

@bot.tree.command(name="criar_painel", description="Abre o formulário para criar um painel de ticket dinâmico.")
@app_commands.default_permissions(administrator=True)
async def criar_painel_slash(interaction: discord.Interaction):
    await interaction.response.send_modal(ModalCriarPainel())

@bot.tree.command(name="sorteio", description="Inicia um sorteio com multiplicador por cargos.")
@app_commands.default_permissions(administrator=True)
async def sorteio_slash(interaction: discord.Interaction):
    await interaction.response.send_modal(ModalSorteio())

@bot.tree.command(name="roletar", description="Sorteia um novo vencedor para um sorteio encerrado.")
@app_commands.describe(id_mensagem="O ID da mensagem do sorteio")
@app_commands.default_permissions(administrator=True)
async def roletar_slash(interaction: discord.Interaction, id_mensagem: str):
    try:
        msg = await interaction.channel.fetch_message(int(id_mensagem))
        reaction = discord.utils.get(msg.reactions, emoji="🎉")
        if not reaction:
            return await interaction.response.send_message("❌ Não encontrei a reação 🎉 nesta mensagem.", ephemeral=True)
            
        users = [user async for user in reaction.users() if not user.bot]
        if not users:
            return await interaction.response.send_message("❌ Nenhum usuário participou deste sorteio.", ephemeral=True)
            
        novo_vencedor = random.choice(users)
        await interaction.response.send_message(f"🎲 **REROLL!** O novo vencedor do sorteio é {novo_vencedor.mention}! Parabéns!", ephemeral=False)
        
    except discord.NotFound:
        await interaction.response.send_message("❌ Mensagem não encontrada neste canal.", ephemeral=True)
    except ValueError:
        await interaction.response.send_message("❌ ID de mensagem inválido.", ephemeral=True)

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
    print(f"✅ Sistema perfeito! {bot.user.name} está online.")

TOKEN = os.getenv('TOKEN')
if TOKEN:
    bot.run(TOKEN)
else:
    print("❌ ERRO: Token não encontrado no ambiente.")
