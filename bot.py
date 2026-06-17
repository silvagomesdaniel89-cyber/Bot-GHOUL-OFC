import os
import discord
import requests
from io import BytesIO
import imagehash
from PIL import Image

# Configuração dos Intents
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print('Bot GHOUL SECURITY online e vigiando!')

@client.event
async def on_message(message):
    # 1. Ignorar mensagens do próprio bot
    if message.author == client.user:
        return

    # 2. Lista de canais ignorados (O bot não fará nada aqui)
    CANAIS_IGNORADOS = [1272293056812683345] 
    
    if message.channel.id in CANAIS_IGNORADOS:
        return

    # 3. Verificação de imagens
    if message.attachments:
        for attachment in message.attachments:
            if attachment.filename.lower().endswith(('png', 'jpg', 'jpeg')):
                try:
                    # Aqui entra a sua lógica de processamento de imagem
                    # Exemplo simples de verificação (adicione a sua lógica aqui):
                    resposta = requests.get(attachment.url)
                    imagem = Image.open(BytesIO(resposta.content))
                    hash_atual = imagehash.phash(imagem)
                    
                    # (Coloque aqui o seu loop de verificação de hash)
                    
                except Exception as e:
                    print(f"Erro ao processar imagem: {e}")

# --- CONFIGURAÇÃO PARA A NUVEM ---
# O bot vai buscar o token em uma variável de ambiente chamada DISCORD_TOKEN
# Assim seu token fica seguro e não precisa ficar escrito no código.
TOKEN = os.environ.get('DISCORD_TOKEN')

from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "O bot está online!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# Certifique-se de que esta linha esteja logo abaixo do código acima:
keep_alive()

if TOKEN:
    client.run(TOKEN)
else:
    print("ERRO: O token não foi encontrado. Configure a variável DISCORD_TOKEN.")
