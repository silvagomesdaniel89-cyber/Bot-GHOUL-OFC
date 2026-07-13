import os
import discord
import requests
import imagehash
import asyncio
from PIL import Image
from io import BytesIO
from flask import Flask
from datetime import timedelta
from threading import Thread

# ==========================================
# 1. SERVIDOR WEB (Para manter online no Render)
# ==========================================
app = Flask('')
@app.route('/')
def home(): return "Bot GHOUL SECURITY Online!"
def run(): app.run(host='0.0.0.0', port=8080)
Thread(target=run, daemon=True).start()

# ==========================================
# 2. CONFIGURAÇÕES MULTI-SERVIDORES e IDs
# ==========================================
TOKEN = os.environ.get('DISCORD_TOKEN')

# SUBSTITUA OS ZEROS PELOS IDS REAIS DO SEU DISCORD
CONFIG_SERVIDORES = {
    # 1. SERVIDOR GHOUL (Apenas Segurança)
    1143627184842493992: { 
        "LOGS_PUNICOES": 1272293056812683345, 
        "BANS": 1468415943251202252
    },
    
    # 2. SERVIDOR BLOX KINGS (Segurança + Auditoria Completa)
    1169685424738947172: { 
        "LOGS_PUNICOES": 1526255782222626907, 
        "BANS": 1526255782222626907,           
        "LOGS_GERAIS": 1526271422253629681     
    }
}

# 📍 CONFIGURAÇÃO DOS CANAIS DE TICKET (BLOX KINGS)
IDCATEGORIA_TICKETS = 1170495547426217995  
ID_CANAL_COMPRAR = 1169984890046001232     

# 📍 CONFIGURAÇÃO DOS CARGOS PARA PINGAR EM CADA TICKET (Substitua pelos IDs reais)
CARGOS_TICKETS = {
    "Robux": 1317249055058825236,
    "Gamepass": 1317249055058825236,
    "Frutas Perm": 1317249055058825236,
    "Frutas Físicas": 1317249055058825236,
    "Contas GHM/Fruta": 1317249055058825236,
    "Suporte / Dúvidas": 1317249055058825236
}

# LINK DO BANNER DA SUA LOJA
LINK_BANNER_LOJA = "https://cdn.discordapp.com/attachments/1183819407013707947/1526281157635870730/file_000000002958720eab459d97fd2c5b8e.png?ex=6a567398&is=6a552218&hm=48c72ace1d64adf01f929e392ddd9bd64dcd74e31ca0a18d75ae98a8c6f28550.jpg"

IMAGENS_BLOQUEADAS = ['9977339a644d9a62', '936c6c4e946cd966', '9748a8dcbd4a2579', 'c48ff019712fe2c6', '91ac6db293ab09a6']

PALAVRAS_PROIBIDAS = [
    "arrombado", "vagabunda", "caralho", "bosta", "merda", "fdp", "fudido", "otario", "idiota", 
    "buceta", "cuzao", "viado", "corno", "puta", "toma no cu", "tmnc", "toma no seu cu", 
    "vai tomar no cu", "se foder", "sfoder", "se fode", "vai se foder", "vai se ferrar", 
    "vsf", "pqp", "fds"
]

FRASES_SCAM = [
    "check my bio", "shes on cam", "she's squirting", "squirt", "look my bio", 
    "crypto casino", "free usdt", "withdrawal success", "check my bi0"
]

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True 
client = discord.Client(intents=intents)

# ==========================================
# 3. CLASSES E VIEWS DO SISTEMA DE TICKETS
# ==========================================
class TicketDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Robux", description="Comprar Robux ou ver tabelas", emoji="💰"),
            discord.SelectOption(label="Gamepass", description="Comprar Gamepasses do Blox Fruits", emoji="📦"),
            discord.SelectOption(label="Frutas Perm", description="Comprar Frutas Permanentes", emoji="🍊"),
            discord.SelectOption(label="Frutas Físicas", description="Comprar Frutas Físicas (Inventário)", emoji="🍎"),
            discord.SelectOption(label="Contas GHM/Fruta", description="Geral, Fruta Inv ou Contas Random", emoji="💸"),
            discord.SelectOption(label="Suporte / Dúvidas", description="Falar com a Staff do servidor", emoji="❓"),
        ]
        super().__init__(placeholder="Selecione uma opção para abrir um ticket...", min_values=1, max_values=1, options=options, custom_id="ticket_select")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        membro = interaction.user
        escolha = self.values[0]
        
        categoria = guild.get_channel(IDCATEGORIA_TICKETS)
        if not categoria:
            await interaction.followup.send("❌ Erro: Categoria de tickets não encontrada. Avise um Administrador.", ephemeral=True)
            return

        permissoes = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            membro: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        nome_canal = f"🎫-{escolha.lower().replace(' ', '-')}-{membro.name}"
        ticket_channel = await guild.create_text_channel(name=nome_canal, category=categoria, overwrites=permissoes)

        id_cargo = CARGOS_TICKETS.get(escolha, 0)
        mencao_cargo = f"<@&{id_cargo}>" if id_cargo != 0 else "@everyone"

        embed_ticket = discord.Embed(
            title=f"🏪 BLOX KINGS - Ticket de {escolha}",
            description=f"Olá {membro.mention}, obrigado por entrar em contato!\nA equipe responsável {mencao_cargo} já foi notificada.\n\n"
                        f"**Assunto selecionado:** `{escolha}`\n\n"
                        "Se veio fazer uma compra, envie o seu pedido para agilizar!",
            color=discord.Color.green()
        )
        if membro.display_avatar: embed_ticket.set_thumbnail(url=membro.display_avatar.url)
        embed_ticket.set_footer(text="Para fechar este ticket, clique no botão abaixo.")

        view_fechar = discord.ui.View(timeout=None)
        botao_fechar = discord.ui.Button(label="Fechar Ticket", style=discord.ButtonStyle.red, emoji="🔒", custom_id="fechar_ticket")
        
        async def fechar_callback(inter_fechar):
            await inter_fechar.response.send_message("Este ticket será deletado em 5 segundos...", ephemeral=False)
            await asyncio.sleep(5)
            await inter_fechar.channel.delete()

        botao_fechar.callback = fechar_callback
        view_fechar.add_item(botao_fechar)

        await ticket_channel.send(content=f"{membro.mention} | {mencao_cargo}", embed=embed_ticket, view=view_fechar)
        await interaction.followup.send(f"✅ Seu ticket de **{escolha}** foi aberto em: {ticket_channel.mention}", ephemeral=True)

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketDropdown())

# ==========================================
# 4. FUNÇÕES AUXILIARES DE LOGS (DESIGN PREMIUM)
# ==========================================
async def enviar_log_delecao(message, motivo):
    guild_id = message.guild.id
    if guild_id in CONFIG_SERVIDORES:
        canal_id = CONFIG_SERVIDORES[guild_id].get("LOGS_GERAIS") if "LOGS_GERAIS" in CONFIG_SERVIDORES[guild_id] else CONFIG_SERVIDORES[guild_id]["LOGS_PUNICOES"]
        canal = client.get_channel(canal_id)
        if canal:
            embed = discord.Embed(title="🛡️ GHOUL SECURITY - Filtro Automático", color=0xdd2e44, timestamp=message.created_at)
            embed.description = (
                f"👤 **Usuário:** {message.author.mention} (`{message.author.id}`)\n"
                f"💬 **Canal:** {message.channel.mention}\n"
                f"🚨 **Ocorrência:** `{motivo}`\n\n"
                f"**Mensagem Deletada:**\n"
                f"```css\n{message.content or 'Sem conteúdo de texto'}\n```"
            )
            if message.author.display_avatar: embed.set_thumbnail(url=message.author.display_avatar.url)
            embed.set_footer(text="Segurança Ativa Blox Kings")
            await canal.send(embed=embed)

async def enviar_log_ban(member, image_bytes, guild_id, motivo="Hackeado"):
    if guild_id in CONFIG_SERVIDORES:
        canal = client.get_channel(CONFIG_SERVIDORES[guild_id]["BANS"])
        if canal:
            texto_log = f"**Id/Nick:** {member.id}/{member.name}\n**Staff:** @GHOUL\n**Ação:** ban\n**Motivo:** {motivo}\n**Prova:**"
            embed = discord.Embed(color=0x2f3136)
            if image_bytes:
                arquivo = discord.File(fp=BytesIO(image_bytes), filename="prova.png")
                embed.set_image(url="attachment://prova.png")
                await canal.send(content=texto_log, file=arquivo, embed=embed)
            else:
                await canal.send(content=f"{texto_log} *Verifique o histórico ou logs gerais*")

# ==========================================
# 5. EVENTOS DO BOT (AUDITORIA LIMPA)
# ==========================================
@client.event
async def on_ready():
    print(f"Bot logado com sucesso como {client.user}")
    client.add_view(TicketView())

# 5.1. MENSAGEM DELETADA POR USUÁRIOS
@client.event
async def on_message_delete(message):
    if message.author.bot or not message.guild: return
    conteudo_lower = message.content.lower()
    if any(p in conteudo_lower for p in PALAVRAS_PROIBIDAS + FRASES_SCAM) or "discord.gg" in conteudo_lower or "discord.com/invite" in conteudo_lower: return
    
    guild_id = message.guild.id
    if guild_id in CONFIG_SERVIDORES and "LOGS_GERAIS" in CONFIG_SERVIDORES[guild_id]:
        canal = client.get_channel(CONFIG_SERVIDORES[guild_id]["LOGS_GERAIS"])
        if canal:
            embed = discord.Embed(title="🗑️ Mensagem Apagada", color=0xf47fff)
            embed.description = (
                f"👤 **Autor:** {message.author.mention} (`{message.author.id}`)\n"
                f"💬 **Canal:** {message.channel.mention}\n\n"
                f"**Conteúdo Original:**\n"
                f"```ini\n[{message.content or 'Sem texto / Imagem'}]\n```"
            )
            embed.set_footer(text="Logs Gerais Blox Kings")
            await canal.send(embed=embed)

# 5.2. MENSAGEM EDITADA
@client.event
async def on_message_edit(before, after):
    if before.author.bot or not before.guild or before.content == after.content: return
    guild_id = before.guild.id
    if guild_id in CONFIG_SERVIDORES and "LOGS_GERAIS" in CONFIG_SERVIDORES[guild_id]:
        canal = client.get_channel(CONFIG_SERVIDORES[guild_id]["LOGS_GERAIS"])
        if canal:
            embed = discord.Embed(title="✏️ Mensagem Editada", color=0x3b82f6)
            embed.description = (
                f"👤 **Autor:** {before.author.mention}\n"
                f"💬 **Canal:** {before.channel.mention}\n\n"
                f"**Antes:**\n```diff\n- {before.content or 'Vazio'}\n```\n"
                f"**Depois:**\n```diff\n+ {after.content or 'Vazio'}\n```"
            )
            embed.set_footer(text="Logs Gerais Blox Kings")
            await canal.send(embed=embed)

# 5.3. ALTERAÇÃO DE APELIDO
@client.event
async def on_member_update(before, after):
    guild_id = before.guild.id
    if guild_id in CONFIG_SERVIDORES and "LOGS_GERAIS" in CONFIG_SERVIDORES[guild_id]:
        canal = client.get_channel(CONFIG_SERVIDORES[guild_id]["LOGS_GERAIS"])
        if canal and before.nick != after.nick:
            embed = discord.Embed(title="👤 Apelido Alterado", color=0x9b59b6)
            embed.description = (
                f"👤 **Membro:** {before.mention} (`{before.id}`)\n\n"
                f"❌ **Antigo:** `{before.nick or before.name}`\n"
                f"✅ **Novo:** `{after.nick or after.name}`"
            )
            embed.set_footer(text="Logs Gerais Blox Kings")
            await canal.send(embed=embed)

# 5.4. TELEMETRIA E FILTROS DE SEGURANÇA
@client.event
async def on_message(message):
    if not message.author.bot and message.guild:
        print(f"[DIAGNÓSTICO] Mensagem de {message.author.name} no canal {message.channel.name} (ID: {message.channel.id}): '{message.content}'")

    if message.author == client.user or not message.guild: return
    conteudo = message.content.strip().lower()
    
    # COMANDO PARA SETAR O PAINEL DE TICKETS (Apenas Admins)
    if conteudo == "!setup_ticket":
        print(f"[DIAGNÓSTICO] Comando !setup_ticket detectado! Verificando permissões...")
        
        if not message.author.guild_permissions.administrator:
            print(f"[DIAGNÓSTICO] {message.author.name} não possui cargo administrativo.")
            return

        try:
            print(f"[DIAGNÓSTICO] Comparando Canal Atual ({message.channel.id}) com Canal Configurado ({ID_CANAL_COMPRAR})")
            
            if int(message.channel.id) != int(ID_CANAL_COMPRAR):
                print(f"[DIAGNÓSTICO] Comando abortado: ID de canal diferente.")
                await message.channel.send(f"❌ Esse comando só pode ser usado no canal <#{ID_CANAL_COMPRAR}>!", delete_after=5)
                await message.delete()
                return

            await message.delete()
            embed_painel = discord.Embed(
                title="🎫 CENTRAL DE ATENDIMENTO - BLOX KINGS",
                description="Precisa de ajuda, deseja comprar Robux, Frutas Permanentes ou Contas?\n"
                            "Selecione a categoria correta no menu abaixo para abrir o seu ticket.\n\n"
                            "⚠️ **Lembre-se:** Não abra tickets sem necessidade para evitar punições.",
                color=0x2f3136
            )
            embed_painel.set_image(url=LINK_BANNER_LOJA)
            await message.channel.send(embed=embed_painel, view=TicketView())
            print("✅ [SUCESSO] Painel de tickets enviado com sucesso!")
            return
        except Exception as e:
            print(f"❌ [ERRO CRÍTICO] Falha ao enviar painel de ticket: {e}")
            return

    # --- FILTRO 1: FRASE DE BOT HACKEADO (BAN IMEDIATO) ---
    if any(frase in conteudo for frase in FRASES_SCAM):
        try:
            await message.delete()
            await message.author.ban(reason="Bot de Spam / Conta Hackeada")
            await enviar_log_ban(message.author, None, message.guild.id, motivo="Postou Spam/Link Malicioso (Conta Hackeada)")
        except Exception as e: print(f"Erro no filtro de Scam: {e}")
        return

    # --- FILTRO 2: CONVITES DO DISCORD (MUTE DE 1 HORA) ---
    if "discord.gg/" in conteudo or "discord.com/invite/" in conteudo:
        try:
            await message.delete()
            duracao = timedelta(minutes=60)
            await message.author.timeout(duracao, reason="Envio de link de outro servidor")
            await enviar_log_ban(message, "Link de Servidor Detectado (Usuário Mutado por 1h)")
        except Exception as e: print(f"Erro ao aplicar mute por link: {e}")
        return

    # --- FILTRO 3: PALAVRÕES (APENAS DELETA A MENSAGEM, SEM APLICAR MUTE) ---
    if any(palavra in conteudo for palavra in PALAVRAS_PROIBIDAS):
        try:
            await message.delete()
            await enviar_log_delecao(message, "Palavrão/Xingamento detectado")
        except Exception as e: print(f"Erro ao deletar xingamento: {e}")
        return

    # --- FILTRO 4: IMAGENS PROIBIDAS ---
    if message.attachments:
        for att in message.attachments:
            if att.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                try:
                    img_data = requests.get(att.url).content
                    img = Image.open(BytesIO(img_data))
                    hash_atual = imagehash.phash(img)
                    for h_str in IMAGENS_BLOQUEADAS:
                        if (hash_atual - imagehash.hex_to_hash(h_str)) < 10:
                            await message.delete()
                            await message.author.ban(reason="Hackeado")
                            await enviar_log_ban(message.author, img_data, message.guild.id)
                            return
                except Exception as e: print(f"Erro processando imagem: {e}")

client.run(TOKEN)
