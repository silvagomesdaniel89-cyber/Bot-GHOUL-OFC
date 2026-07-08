import os
import discord
import requests
import imagehash
from PIL import Image
from io import BytesIO
from flask import Flask
from threading import Thread

# Configuração para o Render não cair
app = Flask('')
@app.route('/')
def home(): return "Bot GHOUL SECURITY Online!"
def run(): app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
def keep_alive(): Thread(target=run).start()

# Configurações do Bot
TOKEN = os.environ.get('DISCORD_TOKEN')
ID_CANAL_LOGS = 1272293056812683345  # <--- COLOQUE O ID DO SEU CANAL AQUI!

IMAGENS_BLOQUEADAS = ['9977339a644d9a62', '936c6c4e946cd966', '9748a8dcbd4a2579', 'c48ff019712fe2c6']
CANAIS_IGNORADOS = [1272293056812683345] 

PALAVRAS_PROIBIDAS = PALAVRAS_PROIBIDAS = [
    # Palavrões de peso
    "arrombado", "vagabunda", "caralho", "bosta", "merda", "fdp", "fudido", "otario", "idiota", "buceta", "cuzao", "viado", "corno", "puta",
    
    # Frases e abreviações (estas são seguras, pois ninguém usa "vai tomar no cu" em contexto profissional/normal)
    "toma no cu", "tmnc", "toma no seu cu", "vai tomar no cu",
    "se foder", "sfoder", "se fode", "vai se foder",
    "vai se ferrar", "vsf", "pqp"
]

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

async def enviar_log(motivo, message):
    canal = client.get_channel(1272293056812683345)
    if canal:
        embed = discord.Embed(title="🚫 Mensagem Deletada", color=discord.Color.red())
        embed.add_field(name="👤 Autor", value=f"{message.author.mention} ({message.author.id})", inline=True)
        embed.add_field(name="💬 Canal", value=message.channel.mention, inline=True)
        embed.add_field(name="📝 Motivo", value=motivo, inline=False)
        embed.add_field(name="Conteúdo:", value=message.content[:1024] if message.content else "Anexo/Imagem", inline=False)
        embed.set_thumbnail(url=message.author.avatar.url if message.author.avatar else None)
        embed.set_footer(text=f"ID da Mensagem: {message.id} | {message.created_at.strftime('%H:%M')}")
        await canal.send(embed=embed)

@client.event
async def on_message(message):
    if message.author == client.user: return

    # 1. Filtro de Palavras
    conteudo = message.content.lower()
    if any(palavra in conteudo for palavra in PALAVRAS_PROIBIDAS):
        await message.delete()
        await enviar_log("Uso de termo proibido", message)
        return

    # 2. Filtro de Imagens
    if message.channel.id not in CANAIS_IGNORADOS and message.attachments:
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
