import os
import discord
import requests
import imagehash
import re
from PIL import Image
from io import BytesIO
from flask import Flask
from threading import Thread

# --- Configuração do servidor Web (Render) ---
app = Flask('')
@app.route('/')
def home(): return "Bot GHOUL SECURITY Online!"
def run(): app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
def keep_alive(): Thread(target=run).start()

# --- Configurações do Bot ---
TOKEN = os.environ.get('DISCORD_TOKEN')
ID_CANAL_LOGS = 1272293056812683345 
IMAGENS_BLOQUEADAS = ['9977339a644d9a62', '936c6c4e946cd966', '9748a8dcbd4a2579', 'c48ff019712fe2c6']
CANAIS_IGNORADOS = [1272293056812683345] 

PALAVRAS_PROIBIDAS = [
    "arrombado", "vagabunda", "caralho", "bosta", "merda", "fdp", "fudido", "otario", "idiota", "buceta", "cuzao", "viado", "corno", "puta",
    "toma no cu", "tmnc", "toma no seu cu", "vai tomar no cu", "se foder", "sfoder", "se fode", "vai se foder", "vai se ferrar", "vsf", "pqp", "fds"
]

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# --- Sistema de Tickets ---
class SelectTicket(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Suporte", description="Contestar punição ou falar com o dono", emoji="👑"),
            discord.SelectOption(label="Denúncias", description="Denunciar alguém ou rever punições", emoji="🪓"),
            discord.SelectOption(label="Dúvidas", description="Perguntar algo sobre o servidor", emoji="☀️"),
            discord.SelectOption(label="Exposed", description="Expor alguém fazendo algo errado", emoji="🌙"),
        ]
        super().__init__(placeholder="Selecione o motivo do ticket...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        nome_canal = f"ticket-{self.values[0].lower()}-{interaction.user.name}"
        categoria = discord.utils.get(interaction.guild.categories, name="Tickets")
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        canal = await interaction.guild.create_text_channel(nome_canal, overwrites=overwrites, category=categoria if categoria else None)
        await interaction.response.send_message(f"Seu ticket de **{self.values[0]}** foi criado em {canal.mention}!", ephemeral=True)
        await canal.send(f"Olá {interaction.user.mention}, bem-vindo ao ticket de {self.values[0]}. Um responsável virá te atender.")

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(SelectTicket())

# --- Funções Auxiliares ---
async def enviar_log(motivo, message):
    canal = client.get_channel(ID_CANAL_LOGS)
    if canal:
        embed = discord.Embed(title="🚫 Mensagem Deletada", color=discord.Color.red())
        embed.add_field(name="👤 Autor", value=message.author.mention, inline=True)
        embed.add_field(name="💬 Canal", value=message.channel.mention, inline=True)
        embed.add_field(name="📝 Motivo", value=motivo, inline=False)
        embed.add_field(name="Conteúdo:", value=message.content[:1024] if message.content else "Anexo", inline=False)
        await canal.send(embed=embed)

@client.event
async def on_ready():
    client.add_view(TicketView())
    print(f'Bot {client.user} está online e operacional!')

@client.event
async def on_message(message):
    if message.author == client.user: return

    # 1. Comando de Setup de Tickets
    if message.content == "!setup_ticket" and message.author.guild_permissions.administrator:
        embed = discord.Embed(title="Suporte GHOUL", description="Selecione uma opção abaixo para abrir seu ticket.", color=discord.Color.blue())
        await message.channel.send(embed=embed, view=TicketView())
        return

    # 2. Filtro de Palavras (Regex)
    conteudo = message.content.lower()
    for palavra in PALAVRAS_PROIBIDAS:
        padrao = r'\b' + re.escape(palavra.lower()) + r'\b'
        if re.search(padrao, conteudo):
            await message.delete()
            await enviar_log("Termo proibido", message)
            return

    # 3. Filtro de Imagens (Similaridade)
    if message.channel.id not in CANAIS_IGNORADOS and message.attachments:
        for attachment in message.attachments:
            if attachment.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                try:
                    response = requests.get(attachment.url)
                    img = Image.open(BytesIO(response.content))
                    hash_atual = imagehash.phash(img)
                    for h_str in IMAGENS_BLOQUEADAS:
                        if (hash_atual - imagehash.hex_to_hash(h_str)) < 10:
                            await message.delete()
                            await enviar_log("Imagem similar detectada", message)
                            return
                except Exception as e:
                    print(f"Erro ao processar imagem: {e}")

keep_alive()
client.run(TOKEN)    if message.channel.id not in CANAIS_IGNORADOS and message.attachments:
        for attachment in message.attachments:
            if attachment.filename.lower().endswith(('png', 'jpg', 'jpeg')):
                try:
                    resp = requests.get(attachment.url)
                    img = Image.open(BytesIO(resp.content))
                    hash_atual = imagehash.phash(img)
                    for h_str in IMAGENS_BLOQUEADAS:
                        if (hash_atual - imagehash.hex_to_hash(h_str)) < 5:
                            await message.delete()
                            await enviar_log("Imagem proibida detectada", message)
                            return
                except: pass

keep_alive()
client.run(TOKEN)
