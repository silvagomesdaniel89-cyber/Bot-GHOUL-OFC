import os
import discord
import requests
import imagehash
from PIL import Image
from io import BytesIO
from flask import Flask
from threading import Thread

# --- Servidor Web ---
app = Flask('')
@app.route('/')
def home(): return "Bot GHOUL SECURITY Online!"
def run(): app.run(host='0.0.0.0', port=8080)
Thread(target=run, daemon=True).start()

TOKEN = os.environ.get('DISCORD_TOKEN')
ID_CANAL_BANS = 1468415943251202252 
IMAGENS_BLOQUEADAS = ['9977339a644d9a62', '936c6c4e946cd966', '9748a8dcbd4a2579', 'c48ff019712fe2c6', '91ac6db293ab09a6']
PALAVRAS_PROIBIDAS = [
    "arrombado", "vagabunda", "caralho", "bosta", "merda", "fdp", "fudido", "otario", "idiota", 
    "buceta", "cuzao", "viado", "corno", "puta", "toma no cu", "tmnc", "toma no seu cu", 
    "vai tomar no cu", "se foder", "sfoder", "se fode", "vai se foder", "vai se ferrar", 
    "vsf", "pqp", "fds"
]

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
client = discord.Client(intents=intents)

async def log_banimento(member, url):
    canal = client.get_channel(ID_CANAL_BANS)
    if canal:
        texto_log = (
            f"**Id/Nick:** {member.id} ({member.name})\n"
            f"**Staff:** @GHOUL\n"
            f"**Ação:** ban\n"
            f"**Motivo:** Envio de imagem proibida\n"
            f"**Prova:**"
        )
        embed = discord.Embed(color=0x2f3136)
        embed.set_image(url=url)
        await canal.send(texto_log, embed=embed)

@client.event
async def on_message(message):
    if message.author == client.user: return
    
    conteudo = message.content.lower()
    if any(palavra in conteudo for palavra in PALAVRAS_PROIBIDAS):
        try: await message.delete()
        except: pass
        return

    if message.attachments:
        for att in message.attachments:
            if att.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                try:
                    img = Image.open(BytesIO(requests.get(att.url).content))
                    hash_atual = imagehash.phash(img)
                    for h_str in IMAGENS_BLOQUEADAS:
                        if (hash_atual - imagehash.hex_to_hash(h_str)) < 10:
                            await message.delete()
                            await message.author.ban(reason="Envio de imagem proibida")
                            await log_banimento(message.author, att.url)
                            return
                except: pass

client.run(TOKEN)
