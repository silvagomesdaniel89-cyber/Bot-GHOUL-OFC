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

ID_CANAL_LOGS = 1272293056812683345 # Canal onde avisa que apagou MENSAGEM
ID_CANAL_BANS = 1468415943251202252 # Canal onde avisa que deu BAN por imagem

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

# ==========================================
# 3. SISTEMA DE LOGS (IGUAIS AOS PRINTS)
# ==========================================

# LOG DE MENSAGEM APAGADA (XINGAMENTO)
async def enviar_log_delecao(message, motivo):
    canal = client.get_channel(ID_CANAL_LOGS)
    if canal:
        embed = discord.Embed(title="🚫 Mensagem Deletada", color=discord.Color.red())
        
        # Formatação idêntica ao print que você enviou
        embed.add_field(name="👤 Autor", value=f"{message.author.mention}\n({message.author.id})", inline=False)
        embed.add_field(name="💬 Canal", value=message.channel.mention, inline=False)
        embed.add_field(name="📝 Motivo", value=motivo, inline=False)
        
        # Se for texto mostra o texto, se for imagem mostra o aviso
        conteudo = message.content if message.content else "Anexo/Imagem"
        embed.add_field(name="Conteúdo:", value=conteudo, inline=False)
        
        embed.set_footer(text=f"ID da Mensagem: {message.id}")
        await canal.send(embed=embed)

# LOG DE BANIMENTO (IMAGEM HACKER/SCAM)
async def enviar_log_ban(member, url):
    canal = client.get_channel(ID_CANAL_BANS)
    if canal:
        # Formatação do texto do log de banimento
        texto_log = (
            f"**Id/Nick:** {member.id} ({member.name})\n"
            f"**Staff:** @GHOUL\n"
            f"**Ação:** ban\n"
            f"**Motivo:** Envio de imagem proibida\n"
            f"**Prova:**"
        )
        # Embed contendo a miniatura (prova)
        embed = discord.Embed(color=0x2f3136)
        embed.set_image(url=url) 
        
        await canal.send(content=texto_log, embed=embed)

# ==========================================
# 4. EVENTOS DO BOT (AÇÃO PRINCIPAL)
# ==========================================
@client.event
async def on_message(message):
    # Ignora se a mensagem for do próprio bot
    if message.author == client.user: 
        return
    
    # ----------------------------------------------------
    # AÇÃO 1: FILTRO DE PALAVRÕES (Apaga tudo, inclusive Staff)
    # ----------------------------------------------------
    conteudo = message.content.lower()
    if any(palavra in conteudo for palavra in PALAVRAS_PROIBIDAS):
        try:
            await message.delete()
            # Chama o Log de Deleção no canal 1272293056812683345
            await enviar_log_delecao(message, "Palavrão/Xingamento detectado")
        except Exception as e:
            print(f"Erro ao deletar palavrão: {e}")
        return # Para a execução aqui se já apagou

    # ----------------------------------------------------
    # AÇÃO 2: FILTRO DE IMAGENS (Apaga e dá Ban, inclusive Staff)
    # ----------------------------------------------------
    if message.attachments:
        for att in message.attachments:
            if att.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                try:
                    img = Image.open(BytesIO(requests.get(att.url).content))
                    hash_atual = imagehash.phash(img)
                    
                    for h_str in IMAGENS_BLOQUEADAS:
                        # Se a imagem bater com a lista
                        if (hash_atual - imagehash.hex_to_hash(h_str)) < 10:
                            url_img = att.url
                            await message.delete()
                            
                            # 1. Aplica o Banimento
                            await message.author.ban(reason="Envio de imagem proibida (Hacker/Scam)")
                            
                            # 2. Chama o Log de Ban no canal 1468415943251202252
                            await enviar_log_ban(message.author, url_img)
                            return
                except Exception as e:
                    print(f"Erro ao processar imagem: {e}")

# Inicia o bot
client.run(TOKEN)
