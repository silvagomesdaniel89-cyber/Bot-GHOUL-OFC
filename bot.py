import os
import discord
import requests
import imagehash
from PIL import Image
from io import BytesIO
from flask import Flask
from threading import Thread

# ==========================================
# 1. SERVIDOR WEB (Para manter online)
# ==========================================
app = Flask('')
@app.route('/')
def home(): return "Bot GHOUL SECURITY Online!"
def run(): app.run(host='0.0.0.0', port=8080)
Thread(target=run, daemon=True).start()

# ==========================================
# 2. CONFIGURAÇÕES E LISTAS
# ==========================================
TOKEN = os.environ.get('DISCORD_TOKEN')

ID_CANAL_LOGS = 1272293056812683345 # Canal de Deleção
ID_CANAL_BANS = 1468415943251202252 # Canal de Banimento

IMAGENS_BLOQUEADAS = ['9977339a644d9a62', '936c6c4e946cd966', '9748a8dcbd4a2579', 'c48ff019712fe2c6', '91ac6db293ab09a6']

PALAVRAS_PROIBIDAS = [
    "arrombado", "vagabunda", "caralho", "bosta", "merda", "fdp", "fudido", "otario", "idiota", 
    "buceta", "cuzao", "viado", "corno", "puta", "toma no cu", "tmnc", "toma no seu cu", 
    "vai tomar no cu", "se foder", "sfoder", "se fode", "vai se foder", "vai se ferrar", 
    "vsf", "pqp", "fds", "tomar no cu", "gay", "veado", "LGBT", "ELIGEBETE", 'eligebete", "Eligebete", "Vai se fuder", "fuder"
]

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
client = discord.Client(intents=intents)

# ==========================================
# 3. SISTEMA DE LOGS 
# ==========================================

# LOG DE MENSAGEM APAGADA (XINGAMENTO)
async def enviar_log_delecao(message, motivo):
    canal = client.get_channel(ID_CANAL_LOGS)
    if canal:
        embed = discord.Embed(title="🚫 Mensagem Deletada", color=discord.Color.red())
        embed.add_field(name="👤 Autor", value=f"{message.author.mention}\n({message.author.id})", inline=False)
        embed.add_field(name="💬 Canal", value=message.channel.mention, inline=False)
        embed.add_field(name="📝 Motivo", value=motivo, inline=False)
        
        conteudo = message.content if message.content else "Anexo/Imagem"
        embed.add_field(name="Conteúdo:", value=conteudo, inline=False)
        
        if message.author.display_avatar:
            embed.set_thumbnail(url=message.author.display_avatar.url)
            
        embed.set_footer(text=f"ID da Mensagem: {message.id}")
        await canal.send(embed=embed)

# LOG DE BANIMENTO COM IMAGEM FIXADA
async def enviar_log_ban(member, image_bytes):
    canal = client.get_channel(ID_CANAL_BANS)
    if canal:
        texto_log = (
            f"**Id/Nick:** {member.id}/{member.name}\n"
            f"**Staff:** @GHOUL\n"
            f"**Ação:** ban\n"
            f"**Motivo:** Hackeado\n"
            f"**Prova:**"
        )
        
        # Transforma os bytes baixados em um arquivo real para o Discord
        arquivo_imagem = discord.File(fp=BytesIO(image_bytes), filename="prova.png")
        
        embed = discord.Embed(color=0x2f3136)
        embed.set_image(url="attachment://prova.png") # Linka o arquivo no embed
        
        # Envia o texto, o arquivo e o embed juntos
        await canal.send(content=texto_log, file=arquivo_imagem, embed=embed)

# ==========================================
# 4. EVENTOS DO BOT
# ==========================================
@client.event
async def on_message(message):
    if message.author == client.user: 
        return
    
    # --- FILTRO 1: PALAVRÕES ---
    conteudo = message.content.lower()
    if any(palavra in conteudo for palavra in PALAVRAS_PROIBIDAS):
        try:
            await message.delete()
            await enviar_log_delecao(message, "Palavrão/Xingamento detectado")
        except Exception as e:
            print(f"Erro ao deletar: {e}")
        return

    # --- FILTRO 2: IMAGENS PROIBIDAS ---
    if message.attachments:
        for att in message.attachments:
            if att.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                try:
                    # Baixa o conteúdo da imagem da internet
                    img_data = requests.get(att.url).content
                    img = Image.open(BytesIO(img_data))
                    hash_atual = imagehash.phash(img)
                    
                    for h_str in IMAGENS_BLOQUEADAS:
                        if (hash_atual - imagehash.hex_to_hash(h_str)) < 10:
                            # 1. Apaga a mensagem original
                            await message.delete()
                            
                            # 2. Dá o Ban
                            await message.author.ban(reason="Hackeado")
                            
                            # 3. Envia o log passando os dados da imagem já baixados
                            await enviar_log_ban(message.author, img_data)
                            return
                except Exception as e:
                    print(f"Erro processando imagem: {e}")

client.run(TOKEN)
