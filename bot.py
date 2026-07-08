import os
import discord
import requests
import imagehash
from PIL import Image
from io import BytesIO
from flask import Flask
from threading import Thread

# =========================================================
# CONFIGURAÇÕES DE SERVIDOR (PARA O RENDER NÃO CAIR)
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
# CONFIGURAÇÕES DO BOT E LISTAS DE BLOQUEIO
# =========================================================
TOKEN = os.environ.get('DISCORD_TOKEN')

# Adicione aqui os hashes das imagens que quer bloquear
IMAGENS_BLOQUEADAS = [
    '9977339a644d9a62',
    '936c6c4e946cd966',
    '9748a8dcbd4a2579',
    'c48ff019712fe2c6',
]

# Lista de palavras e abreviações proibidas
PALAVRAS_PROIBIDAS = [
    "corno", "viado", "puta", "poha", "porra", "caralho", "bosta", 
    "merda", "fdp", "fudido", "arrombado", "otario", "idiota", 
    "vagabunda", "cu", "buceta", "pau", "cuzão",
    "toma no cu", "tmnc", "toma no seu cu", "vai tomar no cu",
    "se foder", "sfoder", "se fode", "vai se foder",
    "vai se ferrar", "vsf", "pqp"
]

CANAIS_IGNORADOS = [1272293056812683345] 

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print('Bot GHOUL SECURITY online e vigiando por Hashes e Palavras!')

# =========================================================
# LÓGICA DE MODERAÇÃO
# =========================================================
@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # 1. FILTRO DE PALAVRAS
    conteudo = message.content.lower()
    if any(palavra in conteudo for palavra in PALAVRAS_PROIBIDAS):
        try:
            await message.delete()
            print(f"Mensagem de {message.author} deletada por termo proibido.")
            return # Para aqui se a mensagem for deletada
        except:
            pass

    # 2. FILTRO DE IMAGENS (Hash)
    if message.channel.id not in CANAIS_IGNORADOS and message.attachments:
        for attachment in message.attachments:
            if attachment.filename.lower().endswith(('png', 'jpg', 'jpeg')):
                try:
                    resposta = requests.get(attachment.url)
                    imagem = Image.open(BytesIO(resposta.content))
                    hash_atual = imagehash.phash(imagem)
                    
                    # Log útil para descobrir novos hashes se necessário
                    # print(f"Hash da imagem enviada: {hash_atual}")

                    for hash_bloqueado_str in IMAGENS_BLOQUEADAS:
                        hash_bloqueado = imagehash.hex_to_hash(hash_bloqueado_str)
                        if (hash_atual - hash_bloqueado) < 5:
                            await message.delete()
                            print(f"Imagem bloqueada detectada e removida!")
                            return 
                except Exception as e:
                    print(f"Erro ao processar imagem: {e}")

# =========================================================
# INICIALIZAÇÃO
# =========================================================
keep_alive()
client.run(TOKEN)
