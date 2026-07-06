import os
import discord
import requests
import imagehash
from PIL import Image
from io import BytesIO
from flask import Flask
from threading import Thread

# =========================================================
# CONTROLE DE PORTA PARA O RENDER NÃO CAIR (100% OBRIGATÓRIO)
# =========================================================
app = Flask('')

@app.route('/')
def home():
    return "Bot GHOUL SECURITY Online!"

def run():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# =========================================================
# O SEU CÓDIGO ORIGINAL DE BUSCA POR HASH
# =========================================================
TOKEN = os.environ.get('DISCORD_TOKEN')

IMAGENS_BLOQUEADAS = [
    '9977339a644d9a62',
    '936c6c4e946cd966',
    '9748a8dcbd4a2579',
    'c48ff019712fe2c6',
]

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print('Bot GHOUL SECURITY online e vigiando por Hashes!')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    CANAIS_IGNORADOS = [1272293056812683345] 
    
    if message.channel.id in CANAIS_IGNORADOS:
        return

    if message.attachments:
        for attachment in message.attachments:
            if attachment.filename.lower().endswith(('png', 'jpg', 'jpeg')):
                try:
                    resposta = requests.get(attachment.url)
                    imagem = Image.open(BytesIO(resposta.content))
                    hash_atual = imagehash.phash(imagem)

                    for hash_bloqueado_str in IMAGENS_BLOQUEADAS:
                        hash_bloqueado = imagehash.hex_to_hash(hash_bloqueado_str)
                        
                        if (hash_atual - hash_bloqueado) < 5:
                            await message.delete()
                            print(f"Imagem bloqueada detectada e removida!")
                            break 
                except Exception as e:
                    print(f"Erro ao processar imagem: {e}")

# =========================================================
# LIGA O SERVIDOR DE PORTA E DEPOIS O BOT
# =========================================================
keep_alive()
client.run(TOKEN)
