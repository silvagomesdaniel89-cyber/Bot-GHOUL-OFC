import os
import discord
import requests
import imagehash
import asyncio
from PIL import Image
from io import BytesIO
from flask import Flask
from datetime import timedelta
from threading import Thread

# --- SERVIDOR WEB ---
app = Flask('')
@app.route('/')
def home(): return "Bot GHOUL SECURITY Online!"
def run(): app.run(host='0.0.0.0', port=8080)
Thread(target=run, daemon=True).start()

# --- CONFIGURAÇÕES ---
TOKEN = os.environ.get('DISCORD_TOKEN')

CONFIG_SERVIDORES = {
    1143627184842493992: { "LOGS_PUNICOES": 1272293056812683345, "BANS": 1468415943251202252 },
    1169685424738947172: { "LOGS_PUNICOES": 1526255782222626907, "BANS": 1526255782222626907, "LOGS_GERAIS": 1526271422253629681 }
}

IDCATEGORIA_TICKETS = 1170495547426217995  
ID_CANAL_COMPRAR = 1169984890046001232     

CARGOS_TICKETS = {
    "Robux": 1317249055058825236, "Gamepass": 1317249055058825236,
    "Frutas Perm": 1317249055058825236, "Frutas Físicas": 1317249055058825236,
    "Contas GHM/Fruta": 1317249055058825236, "Suporte / Dúvidas": 1317249055058825236
}

LINK_BANNER_LOJA = "https://cdn.discordapp.com/attachments/1183819407013707947/1526281157635870730/file_000000002958720eab459d97fd2c5b8e.png?ex=6a567398&is=6a552218&hm=48c72ace1d64adf01f929e392ddd9bd64dcd74e31ca0a18d75ae98a8c6f28550"
IMAGENS_BLOQUEADAS = ['9977339a644d9a62', '936c6c4e946cd966', '9748a8dcbd4a2579', 'c48ff019712fe2c6', '91ac6db293ab09a6']

PALAVRAS_PROIBIDAS = [
    "puta que pariu", "puta", "filha da puta", "fdp", "desgraçado", "desgracado", "resto de aborto", 
    "pau no cu", "caralho", "buceta", "pica", "cu", "trouxa", "arrombado", "arrombada", "cara de cu", 
    "porra", "cuzão", "cuzao", "fudido", "foda", "fuder", "foder", "vai tomar no cu", "vai tomar no seu cu", 
    "toma no cu", "tmnc", "tomar no cu", "imbecil", "vagabundo", "vagabunda", "sáfado", "safado", "corno", 
    "gay", "viadinho", "viado", "veado", "lixo", "vadia", "vagina", "idiota", "otario", "se foder", 
    "sfoder", "se fode", "vai se foder", "vai se fuder", "vai se ferrar", "vsf", "pqp", "fds", 
    "lgbt", "eligebete"
]

FRASES_SCAM = ["check my bio", "shes on cam", "she's squirting", "squirt", "look my bio", "crypto casino", "free usdt", "withdrawal success", "check my bi0"]

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
client = discord.Client(intents=intents)

# --- FUNÇÕES DE LOG ---
async def enviar_log_punicao_unificado(member, guild_id, acao, motivo, message=None, image_bytes=None):
    canal = client.get_channel(CONFIG_SERVIDORES[guild_id]["BANS"])
    if canal:
        embed = discord.Embed(color=0x2f3136, title=f"🚨 PUNIÇÃO: {acao.upper()}")
        embed.add_field(name="Usuário", value=f"{member.name} ({member.id})", inline=True)
        embed.add_field(name="Motivo", value=motivo, inline=True)
        if message: embed.add_field(name="Mensagem Flagrada", value=f"```css\n{message.content}```", inline=False)
        if image_bytes:
            arquivo = discord.File(fp=BytesIO(image_bytes), filename="prova.png")
            embed.set_image(url="attachment://prova.png")
            await canal.send(embed=embed, file=arquivo)
        else: await canal.send(embed=embed)

async def enviar_log_delecao_simples(message, motivo):
    guild_id = message.guild.id
    canal = client.get_channel(CONFIG_SERVIDORES[guild_id]["LOGS_GERAIS"])
    if canal:
        embed = discord.Embed(title="🗑️ Mensagem Apagada (Xingamento)", color=0xdd2e44)
        embed.add_field(name="Autor", value=f"{message.author.mention}", inline=True)
        embed.add_field(name="Conteúdo", value=f"```css\n{message.content}```", inline=False)
        await canal.send(embed=embed)

# --- EVENTOS ---
@client.event
async def on_ready():
    print(f"BOT ONLINE: {client.user}")

@client.event
async def on_message(message):
    if message.author == client.user or not message.guild: return
    conteudo = message.content.strip().lower()

    # 1. SETUP TICKET
    if conteudo == "!setup_ticket" and message.author.guild_permissions.administrator:
        if int(message.channel.id) == int(ID_CANAL_COMPRAR):
            await message.delete()
            embed = discord.Embed(title="🎫 CENTRAL DE ATENDIMENTO", description="Selecione sua categoria abaixo.", color=0x2f3136)
            embed.set_image(url=LINK_BANNER_LOJA)
            await message.channel.send(embed=embed, view=TicketView())
        return

    # 2. FILTRO SCAM
    if any(frase in conteudo for frase in FRASES_SCAM):
        await message.delete()
        await message.author.timeout(timedelta(days=7), reason="Scam detectado")
        await enviar_log_punicao_unificado(message.author, message.guild.id, "Mute 7 Dias", "Frase Scam", message)
        return

    # 3. FILTRO LINKS
    if "discord.gg/" in conteudo or "discord.com/invite/" in conteudo:
        await message.delete()
        await message.author.timeout(timedelta(minutes=60), reason="Divulgação")
        await enviar_log_punicao_unificado(message.author, message.guild.id, "Mute 1 Hora", "Link de servidor", message)
        return

    # 4. FILTRO PALAVRÕES
    # Verifica se a mensagem contém ALGUMA das palavras proibidas
    if any(p in conteudo for p in PALAVRAS_PROIBIDAS):
        await message.delete()
        await enviar_log_delecao_simples(message, "Palavrão/Termo Proibido")
        print(f"[LOG] Palavrão deletado de {message.author.name}")
        return

    # 5. FILTRO IMAGENS
    if message.attachments:
        for att in message.attachments:
            if att.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                img_data = requests.get(att.url).content
                img = Image.open(BytesIO(img_data))
                hash_atual = imagehash.phash(img)
                for h_str in IMAGENS_BLOQUEADAS:
                    if (hash_atual - imagehash.hex_to_hash(h_str)) < 10:
                        await message.delete()
                        await message.author.ban(reason="Imagem proibida")
                        await enviar_log_punicao_unificado(message.author, message.guild.id, "BAN", "Imagem bloqueada", message, img_data)
                        return

client.run(TOKEN)
