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

def run(): 
    # Usando porta 8080 padrão para evitar erros no Render
    app.run(host='0.0.0.0', port=8080)

def keep_alive(): 
    t = Thread(target=run)
    t.daemon = True # Garante que o thread feche se o bot fechar
    t.start()

# --- Configurações ---
TOKEN = os.environ.get('DISCORD_TOKEN')
ID_CANAL_LOGS = 1272293056812683345 
IMAGENS_BLOQUEADAS = ['9977339a644d9a62', '936c6c4e946cd966', '9748a8dcbd4a2579', 'c48ff019712fe2c6', '91ac6db293ab09a6']
CANAIS_IGNORADOS = [1272293056812683345] 

PALAVRAS_PROIBIDAS = [
    "arrombado", "vagabunda", "caralho", "bosta", "merda", "fdp", "fudido", "otario", "idiota", "buceta", "cuzao", "viado", "corno", "puta",
    "toma no cu", "tmnc", "toma no seu cu", "vai tomar no cu", "se foder", "sfoder", "se fode", "vai se foder", "vai se ferrar", "vsf", "pqp"
]

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# --- Eventos ---
@client.event
async def on_ready():
    print(f'Bot {client.user} está online!')

@client.event
async def on_message(message):
    if message.author == client.user: return
    
    # Filtro de Palavras
    conteudo = message.content.lower()
    for palavra in PALAVRAS_PROIBIDAS:
        if re.search(r'\b' + re.escape(palavra) + r'\b', conteudo):
            await message.delete()
            return

    # Filtro de Imagens
    if message.channel.id not in CANAIS_IGNORADOS and message.attachments:
        for att in message.attachments:
            if att.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                try:
                    img = Image.open(BytesIO(requests.get(att.url).content))
                    hash_atual = imagehash.phash(img)
                    for h_str in IMAGENS_BLOQUEADAS:
                        if (hash_atual - imagehash.hex_to_hash(h_str)) < 10:
                            await message.delete()
                            return
                except: pass

# --- Inicialização ---
if __name__ == "__main__":
    keep_alive()
    if TOKEN:
        client.run(TOKEN)
    else:
        print("Erro: Token não encontrado nas variáveis de ambiente!")
