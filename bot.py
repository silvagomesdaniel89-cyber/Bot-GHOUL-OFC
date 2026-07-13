import os
import discord
import requests
import imagehash
import re
from PIL import Image
from io import BytesIO
from flask import Flask
from threading import Thread

# --- Servidor Web ---
app = Flask('')
@app.route('/')
def home(): return "Bot GHOUL SECURITY Online!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): 
    t = Thread(target=run, daemon=True)
    t.start()

# --- Configurações ---
TOKEN = os.environ.get('DISCORD_TOKEN')
ID_CANAL_LOGS = 1272293056812683345  # Canal de deleções
ID_CANAL_BANS = 1468415943251202252  # Canal de banimentos
IMAGENS_BLOQUEADAS = ['9977339a644d9a62', '936c6c4e946cd966', '9748a8dcbd4a2579', 'c48ff019712fe2c6', '91ac6db293ab09a6']
CANAIS_IGNORADOS = [1272293056812683345] 

intents = discord.Intents.default()
intents.message_content = True
intents.members = True # ESSENCIAL PARA BANIR
client = discord.Client(intents=intents)

# --- Funções de Log ---
async def enviar_log_delecao(motivo, message):
    canal = client.get_channel(ID_CANAL_LOGS)
    if canal:
        embed = discord.Embed(title="🚫 Mensagem Deletada", color=discord.Color.red())
        embed.add_field(name="Autor", value=f"{message.author.mention}", inline=True)
        embed.add_field(name="Motivo", value=motivo, inline=False)
        await canal.send(embed=embed)

async def enviar_log_ban(member, motivo, url_imagem):
    canal = client.get_channel(ID_CANAL_BANS)
    if canal:
        embed = discord.Embed(title="🔨 Usuário Banido", color=discord.Color.dark_red())
        embed.add_field(name="Usuário", value=f"{member.name} ({member.id})", inline=True)
        embed.add_field(name="Motivo", value=motivo, inline=False)
        if url_imagem: embed.set_image(url=url_imagem)
        await canal.send(embed=embed)

# --- Bot ---
@client.event
async def on_ready():
    print(f'Bot {client.user} está online!')

@client.event
async def on_message(message):
    if message.author == client.user or message.author.guild_permissions.administrator: 
        return

    # 1. Filtro de Palavras
    conteudo = message.content.lower()
    palavras_proibidas = ["arrombado", "vagabunda", "caralho", "bosta", "merda", "fdp", "fudido", "vsf", "pqp"]
    for palavra in palavras_proibidas:
        if re.search(r'\b' + re.escape(palavra) + r'\b', conteudo):
            await message.delete()
            await enviar_log_delecao("Palavrão detectado", message)
            return

    # 2. Filtro de Imagens
    if message.channel.id not in CANAIS_IGNORADOS and message.attachments:
        for att in message.attachments:
            if att.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                try:
                    img = Image.open(BytesIO(requests.get(att.url).content))
                    hash_atual = imagehash.phash(img)
                    for h_str in IMAGENS_BLOQUEADAS:
                        if (hash_atual - imagehash.hex_to_hash(h_str)) < 10:
                            url_da_imagem = att.url
                            await message.delete()
                            try:
                                await message.author.ban(reason="Uso de imagem proibida")
                                await enviar_log_ban(message.author, "Banido automaticamente.", url_da_imagem)
                            except Exception as e:
                                print(f"Erro ao banir: {e}")
                            return
                except: pass

if __name__ == "__main__":
    keep_alive()
    client.run(TOKEN)
