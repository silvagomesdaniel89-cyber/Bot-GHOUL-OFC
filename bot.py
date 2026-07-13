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
ID_CANAL_LOGS = 1272293056812683345 
ID_CANAL_BANS = 1468415943251202252 
IMAGENS_BLOQUEADAS = ['9977339a644d9a62', '936c6c4e946cd966', '9748a8dcbd4a2579', 'c48ff019712fe2c6', '91ac6db293ab09a6']
CANAIS_IGNORADOS = [1272293056812683345] 

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
client = discord.Client(intents=intents)

# --- Bot ---
@client.event
async def on_ready():
    print(f'Bot {client.user} esta pronto e monitorando!')

@client.event
async def on_message(message):
    # O bot ignora a si mesmo e administradores (para você poder testar sem ser banido)
    if message.author == client.user or message.author.guild_permissions.administrator: 
        return

    # 1. Filtro de Palavras
    conteudo = message.content.lower()
    palavras_proibidas = ["arrombado", "vagabunda", "caralho", "bosta", "merda", "fdp", "fudido", "vsf", "pqp"]
    for palavra in palavras_proibidas:
        if re.search(r'\b' + re.escape(palavra) + r'\b', conteudo):
            try:
                await message.delete()
                print(f"Palavra proibida deletada de {message.author}")
            except Exception as e:
                print(f"Erro ao deletar palavra: {e}")
            return

    # 2. Filtro de Imagens
    if message.channel.id not in CANAIS_IGNORADOS and message.attachments:
        for att in message.attachments:
            if att.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                try:
                    response = requests.get(att.url)
                    img = Image.open(BytesIO(response.content))
                    hash_atual = imagehash.phash(img)
                    
                    for h_str in IMAGENS_BLOQUEADAS:
                        if (hash_atual - imagehash.hex_to_hash(h_str)) < 10:
                            print(f"Imagem proibida detectada de {message.author}")
                            
                            # Tenta deletar e banir
                            try:
                                await message.delete()
                                await message.author.ban(reason="Uso de imagem proibida.")
                                
                                # Envia log de banimento com a imagem
                                canal_ban = client.get_channel(ID_CANAL_BANS)
                                if canal_ban:
                                    embed = discord.Embed(title="🔨 Usuário Banido", color=discord.Color.dark_red())
                                    embed.add_field(name="Usuário", value=message.author.mention, inline=True)
                                    embed.set_image(url=att.url)
                                    await canal_ban.send(embed=embed)
                            except Exception as e:
                                print(f"ERRO CRITICO AO BANIR/DELETAR: {e}")
                            return
                except Exception as e:
                    print(f"Erro no processamento da imagem: {e}")

if __name__ == "__main__":
    keep_alive()
    client.run(TOKEN)
