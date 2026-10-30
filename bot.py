import os
import re
import asyncio
import datetime
import unicodedata
from io import BytesIO
from threading import Thread
from urllib.parse import urlparse

import aiohttp
import discord
import imagehash
from discord import app_commands
from discord.ext import commands
from flask import Flask
from PIL import Image, ImageFile

# Aceita imagens "cortadas"/levemente corrompidas (o Discord ainda exibe, então o bot também precisa analisar)
ImageFile.LOAD_TRUNCATED_IMAGES = True

# ==================== SERVIDOR WEB PARA MANTER ONLINE ====================
app = Flask(__name__)
@app.route('/')
def home(): 
    return "Bot online e operando com perfeição!"

def run_server(): 
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

Thread(target=run_server, daemon=True).start()

# ==================== CONFIGURAÇÕES DOS SERVIDORES ====================
CONFIG_SERVIDORES = {
    1143627184842493992: {
        "nome": "GHOUL SECURITY", 
        "canal_logs": 1272293056812683345, 
        "canal_punicoes": 1468415943251202252, 
        "categoria_tickets": 1527037033057353728, 
        "cargo_staff": 1274081192450195671
    },
    1169685424738947172: {
        "nome": "BLOX KINGS", 
        "canal_logs": 1526271422253629681, 
        "canal_punicoes": 1526255782222626907, 
        "categoria_tickets": 1170495547426217995, 
        "cargo_staff": 1317249055058825236
    },
    1331323352840933497: {
        "nome": "NIGHTWARE STORE", 
        "canal_logs": 1527037894743687168, 
        "canal_punicoes": 1527038039111635114, 
        "categoria_tickets": 1331327159448375356, 
        "cargo_staff": 1333982207701684294
    }
}

IMAGENS_TICKETS = {
    "GHOUL": "https://cdn.discordapp.com/attachments/1444429504838631586/1454170002746769530/Banner_ticket_20250205_120340_0000.png",
    "COD": "https://cdn.discordapp.com/attachments/1183819407013707947/1469731813709578417/GHOUL_20260207_132912_0000.png",
    "BLOX_KINGS": "https://cdn.discordapp.com/attachments/1183819407013707947/1526281157635870730/file_000000002958720eab459d97fd2c5b8e.png",
    "NIGHTWARE": "https://cdn.discordapp.com/attachments/1440377531848200295/1452759780111155323/standard.gif"
}

# ==================== LISTAS E AJUSTES DOS FILTROS ====================
# COMO ESCREVER AS LISTAS DE TEXTO (TERMOS_BAN e PALAVROES):
#   - Palavra solta ("rola"): só pega a palavra INTEIRA (rola, rolas, r0la, r o l a, p.o.r.r.a)
#     e NUNCA um pedaço de outra palavra (enrolando, desenrolado, computador, picanha...).
#   - Expressão ("tomar no cu"): escreva COM ESPAÇOS. Pega com espaço, hífen ou tudo junto ("tomarnocu").
#   - Não precisa se preocupar com acento, maiúscula, número no lugar de letra (p0rr4)
#     nem letra repetida (porrrra). O plural com "s" também já é pego sozinho.

TERMOS_BAN = [
    "check my bio", "check my profile", "look my bio", "look at my bio",
    "check bio", "olhar a biografia", "olhe minha bio", "free nitro",
    "nitro gratis", "onlyfans free"
]

PALAVROES = [
    "fdp", "filho da puta", "filha da puta", "caralho", "krl", "bosta",
    "escroto", "escrota", "merda", "arrombado", "arrombada", "viado",
    "corno", "corna", "desgracado", "desgracada", "vagabundo", "vagabunda",
    "porra", "buceta", "cacete", "puta", "puto", "putaria", "putinha",
    "cuzao", "cuzoes", "pica", "rola", "xoxota", "vadia", "foder",
    "foda se", "tnc", "tomar no cu", "vsf", "vtnc", "pqp"
]

IMAGENS_BLOQUEADAS = [
    '9977339a644d9a62', '936c6c4e946cd966', '9748a8dcbd4a2579', 
    'c48ff019712fe2c6', '91ac6db293ab09a6', 'c1e1eb965c5e5cd0', 'f5de4a08bdbd5aa5', '956a6e944ac9a6c9', '931e6ae394d3486f'
]

# Quão "parecida" a imagem precisa ser para levar ban. É a distância entre os hashes (0 a 64):
#   0 = idêntica | menor = mais rígido | maior = pega mais variações (recorte, compressão, redimensionada),
#   mas aumenta o risco de banir imagem inocente.
# Use o comando /testar_imagem para ver a distância real de uma imagem antes de mexer nisso.
LIMITE_HASH = 8

NOME_CANAL_REGISTRO = "imagens-bloqueadas"   # canal privado onde o bot guarda a lista do /bloquear_imagem
LIMITE_IMAGENS_REGISTRADAS = 150             # máximo de imagens bloqueadas por comando

LIMITE_DOWNLOAD = 25 * 1024 * 1024   # ignora arquivos maiores que isso
LIMITE_CACHE = 8 * 1024 * 1024       # só guarda no cache (log de mensagem apagada) imagens até esse tamanho
EXT_IMAGEM = (".png", ".apng", ".jpg", ".jpeg", ".jfif", ".webp", ".gif", ".bmp", ".tif", ".tiff")
URL_REGEX = re.compile(r'https?://[^\s<>|"\']+', re.IGNORECASE)
HEADERS_NAVEGADOR = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# ==================== FILTRO DE TEXTO (PALAVRA INTEIRA) ====================
# Por que existe: o filtro antigo juntava a frase inteira sem espaços ("fiqueienrolandoumpouco") e procurava
# o palavrão DENTRO do texto, então "enrolando" e "desenrolado" (que têm "rola") eram apagados.
# Agora o texto é separado em palavras e só vale quando a palavra INTEIRA é o palavrão.
LEET = str.maketrans({'0': 'o', '1': 'i', '3': 'e', '4': 'a', '5': 's', '7': 't', '$': 's', '@': 'a'})
LEET_ARROBA_PREFIXO = str.maketrans({'0': 'o', '1': 'i', '3': 'e', '4': 'a', '5': 's', '7': 't', '$': 's', '@': ' '})

def limpar_texto(texto, arroba_e_letra=True):
    """Minúsculo, sem acento, sem caracteres invisíveis e com número/símbolo trocado por letra (p0rr4 -> porra)."""
    texto = re.sub(r'<a?:\w+:\d+>|<(?:@[!&]?|#)\d+>', ' ', texto)  # emojis customizados e menções não contam
    texto = unicodedata.normalize('NFKD', texto.lower())
    texto = ''.join(c for c in texto if unicodedata.category(c) not in ('Mn', 'Cf'))
    return texto.translate(LEET if arroba_e_letra else LEET_ARROBA_PREFIXO)

def reduzir(texto):
    """Junta letras repetidas: porrrra -> pora (a lista também é reduzida, então 'porra' continua casando)."""
    return re.sub(r'(.)\1+', r'\1', texto)

def tokenizar(texto, arroba_e_letra=True):
    """Quebra o texto em palavras (só letras). 'pica-pau' vira uma palavra só, e 'p-o-r-r-a' também."""
    limpo = re.sub(r'(?<=[a-z])-(?=[a-z])', '', limpar_texto(texto, arroba_e_letra))
    return re.findall(r'[a-z]+', limpo)

def compilar_lista(entradas):
    """Separa a lista em palavras soltas e expressões (as com espaço)."""
    palavras, frases = {}, []
    for entrada in entradas:
        partes = re.findall(r'[a-z]+', limpar_texto(entrada))
        if not partes:
            continue
        junto = reduzir(''.join(partes))
        if len(partes) == 1:
            palavras[junto] = entrada
        else:
            frases.append((junto, entrada))
    return palavras, frases

def achar_na_lista(texto, lista):
    """Devolve o item da lista que aparece no texto (ou None). Só vale palavra INTEIRA, nunca pedaço de outra palavra."""
    achado = _achar(tokenizar(texto), lista)
    if achado is None and '@' in texto:
        # "@rola": aqui o @ é só um prefixo (tipo menção), não a letra "a"
        achado = _achar(tokenizar(texto, arroba_e_letra=False), lista)
    return achado

def _achar(tokens, lista):
    palavras, frases = lista
    if not tokens:
        return None
    reduzidos = [reduzir(t) for t in tokens]

    # 1) Palavra solta inteira (aceita plural com "s": putas, rolas...)
    for r in reduzidos:
        if r in palavras:
            return palavras[r]
        if len(r) > 1 and r.endswith('s') and r[:-1] in palavras:
            return palavras[r[:-1]]

    # 2) Expressões com várias palavras (separadas, coladas, com hífen, letra por letra...)
    for junto, entrada in frases:
        limite = len(junto) + 3
        for i, r in enumerate(reduzidos):
            if not junto.startswith(r):
                continue
            atual = ""
            for j in range(i, min(len(tokens), i + limite)):
                for ch in tokens[j]:
                    if not atual or atual[-1] != ch:
                        atual += ch
                if atual == junto:
                    return entrada
                if not junto.startswith(atual):
                    break

    # 3) Letras soltas ("p o r r a", "f.d.p", "k_r_l"): junta SÓ as letras que estão sozinhas
    corrida = []
    for t in tokens + ['']:
        if len(t) == 1:
            corrida.append(t)
            continue
        if len(corrida) >= 3:
            junta = reduzir(''.join(corrida))
            for forma, entrada in palavras.items():
                if forma in junta:
                    return entrada
        corrida = []
    return None

TERMOS_BAN_C = compilar_lista(TERMOS_BAN)
PALAVROES_C = compilar_lista(PALAVROES)

# ==================== ANÁLISE DE IMAGENS (HASH) ====================
# Cada item da lista: (hash_em_texto, ImageHash, algoritmo_exigido, origem)
#   - Hashes do código (IMAGENS_BLOQUEADAS): não dá pra saber de qual tipo cada um é, então são comparados
#     com os 3 tipos (algoritmo_exigido = None).
#   - Imagens bloqueadas pelo /bloquear_imagem: o tipo de cada hash é conhecido, então só comparam com o MESMO tipo.
ALGORITMOS = ("average", "phash", "dhash")

HASHES_FIXOS = []
for _hex in IMAGENS_BLOQUEADAS:
    try:
        _h = imagehash.hex_to_hash(_hex)
        if _h.hash.shape != (8, 8):
            raise ValueError("o hash precisa ter 16 caracteres (tamanho padrão 8x8)")
        HASHES_FIXOS.append((_hex, _h, None, "lista"))
    except Exception as _erro:
        print(f"[Aviso] Hash ignorado ({_hex}): {_erro}")

HASHES_BLOQUEADOS = list(HASHES_FIXOS)   # lista em uso: fixos + os do /bloquear_imagem

def reconstruir_hashes(registradas):
    """Junta a lista do código com as imagens bloqueadas por comando. Troca a lista de uma vez (seguro com threads)."""
    global HASHES_BLOQUEADOS
    novos = list(HASHES_FIXOS)
    for e in registradas:
        for alg in ALGORITMOS:
            novos.append((e["hashes"][alg], imagehash.hex_to_hash(e["hashes"][alg]), alg, e["nome"]))
    HASHES_BLOQUEADOS = novos

def avaliar_imagem(dados):
    """
    Roda em OUTRA THREAD (não trava o bot). Calcula os hashes da imagem (e de alguns frames, se for
    GIF/WEBP animado) e compara com a lista bloqueada.
    Retorna (frames, melhor, menores):
      melhor  = (distancia, algoritmo, hash_bloqueado, origem) da imagem bloqueada mais próxima
      menores = menor distância encontrada em cada algoritmo
    """
    frames = []
    with Image.open(BytesIO(dados)) as img:
        total = max(1, getattr(img, "n_frames", 1))
        for i in sorted({0, total // 3, (total * 2) // 3, total - 1}):
            try:
                img.seek(i)
            except EOFError:
                break
            rgb = img.convert("RGB")
            frames.append({
                "average": imagehash.average_hash(rgb),
                "phash": imagehash.phash(rgb),
                "dhash": imagehash.dhash(rgb),
            })

    alvos = HASHES_BLOQUEADOS   # "foto" da lista neste momento
    melhor = None
    menores = {alg: None for alg in ALGORITMOS}
    for hashes in frames:
        for algoritmo, h in hashes.items():
            for hex_alvo, alvo, alg_exigido, origem in alvos:
                if alg_exigido and alg_exigido != algoritmo:
                    continue
                dist = int(h - alvo)
                if menores[algoritmo] is None or dist < menores[algoritmo]:
                    menores[algoritmo] = dist
                if melhor is None or dist < melhor[0]:
                    melhor = (dist, algoritmo, hex_alvo, origem)
    return frames, melhor, menores

def eh_hash_liso(hashes):
    """True se a imagem tem quase nenhum detalhe (uma cor só, degradê...): o hash dela bateria com muita imagem inocente."""
    def bits(alg):
        return bin(int(str(hashes[alg]), 16)).count("1")
    return not (4 <= bits("average") <= 60 and 4 <= bits("dhash") <= 60 and bits("phash") >= 16)

def limpar_nome(nome):
    """Nome simples (letras, números, espaço, - . ( )), numa linha só e com no máximo 50 caracteres."""
    nome = re.sub(r'[^\w\s\-.()]', '', nome or '')
    return re.sub(r'\s+', ' ', nome).strip()[:50]

def proximo_nome_livre(usados):
    n = 1
    while f"imagem-{n}" in usados:
        n += 1
    return f"imagem-{n}"

# Formato da mensagem que guarda cada imagem bloqueada no canal de registro (só os hashes, NUNCA a imagem)
REGISTRO_RE = re.compile(
    r"Imagem bloqueada\*\* — (?P<nome>[^\n]*)\n"
    r"`average` `(?P<average>[0-9a-f]{16})`\n"
    r"`phash` `(?P<phash>[0-9a-f]{16})`\n"
    r"`dhash` `(?P<dhash>[0-9a-f]{16})`\n"
    r"👤 Por: <@(?P<por>\d+)> • <t:(?P<quando>\d+):f>"
)

def montar_registro(nome, hashes_hex, user_id, quando):
    return (
        f"🚫 **Imagem bloqueada** — {nome}\n"
        f"`average` `{hashes_hex['average']}`\n"
        f"`phash` `{hashes_hex['phash']}`\n"
        f"`dhash` `{hashes_hex['dhash']}`\n"
        f"👤 Por: <@{user_id}> • <t:{int(quando)}:f>\n"
        f"-# Não apague esta mensagem: é ela que guarda a lista. Para desbloquear, use /desbloquear_imagem."
    )

def ler_registro(texto):
    m = REGISTRO_RE.search(texto or "")
    if not m:
        return None
    return {
        "nome": m.group("nome").strip(),
        "hashes": {alg: m.group(alg) for alg in ALGORITMOS},
        "por": int(m.group("por")),
        "quando": int(m.group("quando")),
    }

def nome_seguro(nome):
    """Nome de arquivo seguro para anexar no Discord (só letras/números + extensão de imagem)."""
    base, ext = os.path.splitext(nome or "")
    ext = ext.lower() if ext.lower() in EXT_IMAGEM else ".png"
    base = re.sub(r'[^A-Za-z0-9_-]', '_', base)[:40] or "imagem"
    return base + ext

def coletar_fontes_imagem(message, so_embeds=False):
    """Lista (url, nome, anexo) de tudo que parece imagem na mensagem: anexos, encaminhadas, links e prévias."""
    fontes = []

    if not so_embeds:
        anexos = list(message.attachments)
        # Mensagem ENCAMINHADA: os anexos ficam dentro do "snapshot" da mensagem original
        for snap in (getattr(message, "message_snapshots", None) or []):
            anexos.extend(getattr(snap, "attachments", None) or [])
        for a in anexos:
            tipo = (a.content_type or "").lower()
            if tipo.startswith("image/") or a.filename.lower().endswith(EXT_IMAGEM):
                fontes.append((a.url, a.filename, a))

        # Links diretos para imagem escritos no texto
        for url in URL_REGEX.findall(message.content or ""):
            url = url.rstrip(".,;:!?)]}")
            try:
                caminho = urlparse(url).path
            except ValueError:
                continue
            if caminho.lower().endswith(EXT_IMAGEM):
                fontes.append((url, os.path.basename(caminho), None))

    # Prévias de link (embeds): o Discord gera depois, e avisa editando a mensagem
    for emb in message.embeds:
        for midia in (emb.image, emb.thumbnail):
            url = getattr(midia, "proxy_url", None) or getattr(midia, "url", None)
            if url:
                fontes.append((url, "previa.png", None))

    unicas, vistas = [], set()
    for fonte in fontes:
        if fonte[0] not in vistas:
            vistas.add(fonte[0])
            unicas.append(fonte)
    return unicas[:10]

# ==================== ESTRUTURA DO BOT ====================
class MeuBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents, help_command=None)
        self.mensagens_ignoradas = set()
        self.ultimos_banimentos = set() 
        self.ultimos_mutes = set()
        self.banindo = set()       # quem está sendo banido agora (evita ban duplicado quando chegam várias imagens juntas)
        self.midia_cache = {}      # Cache temporário de mídias deletadas
        self.sessao_http = None    # sessão para baixar imagens SEM travar o bot
        self.imagens_registradas = {}    # imagens bloqueadas pelo /bloquear_imagem (id da mensagem do registro -> dados)
        self.registro_carregado = False
        self.trava_registro = None       # evita dois comandos mexendo na lista ao mesmo tempo (criada no setup_hook)

    async def setup_hook(self):
        self.sessao_http = aiohttp.ClientSession()
        self.trava_registro = asyncio.Lock()
        self.add_view(ViewGhoul())
        self.add_view(ViewKings())
        self.add_view(ViewNightware())
        self.add_view(ViewValidar())
        self.add_view(ViewFechar())
        await self.tree.sync()

    async def close(self):
        if self.sessao_http:
            await self.sessao_http.close()
        await super().close()

bot = MeuBot()

def obter_config(guild_id): 
    return CONFIG_SERVIDORES.get(guild_id)

# ==================== SISTEMA DE PUNIÇÕES E LOGS (#950606) ====================
async def log_punicao_bonito(guild, user, staff, acao, motivo, prova_url=None, prova_arquivo=None):
    config = obter_config(guild.id)
    if not config or not (canal := bot.get_channel(config["canal_punicoes"])): 
        return

    embed = discord.Embed(
        title=f"🔨 {config['nome']} - Punição Aplicada", 
        color=0x950606, 
        timestamp=discord.utils.utcnow()
    )
    if user.display_avatar: 
        embed.set_thumbnail(url=user.display_avatar.url)
    
    # Layout de punição super compacto, limpo e direto conforme solicitado
    description = (
        f"👤 **Usuário:** {user.mention}\n"
        f"📛 **Nick:** `{user.name}`\n"
        f"🆔 **ID:** `{user.id}`\n"
        f"🛡️ **Staff:** {staff.mention}\n"
        f"🚨 **Ação:** `{acao}`\n"
        f"📄 **Motivo:** {motivo}\n"
    )
    embed.description = description

    arquivo = None
    if prova_arquivo:
        # A imagem vai ANEXADA no log: o link do Discord morre quando a mensagem é apagada
        dados, nome = prova_arquivo
        arquivo = discord.File(BytesIO(dados), filename=nome)
        embed.set_image(url=f"attachment://{nome}")
    elif prova_url:
        embed.set_image(url=prova_url)

    embed.set_footer(text=f"Segurança Ativa {config['nome']}", icon_url=guild.icon.url if guild.icon else None)

    try:
        if arquivo:
            await canal.send(embed=embed, file=arquivo)
        else:
            await canal.send(embed=embed)
    except discord.HTTPException:
        if not arquivo:
            raise
        # Arquivo grande demais para o canal: manda o log sem anexar
        if prova_url:
            embed.set_image(url=prova_url)
        else:
            embed.remove_image()
        await canal.send(embed=embed)

async def log_falha_ban(guild, membro, motivo, erro):
    """Avisa no canal de logs quando o bot NÃO conseguiu banir (antes só aparecia no console)."""
    config = obter_config(guild.id)
    if not config or not (canal := bot.get_channel(config["canal_logs"])): 
        return
    embed = discord.Embed(
        title=f"⚠️ {config['nome']} - Falha ao Banir", 
        color=0x950606, 
        timestamp=discord.utils.utcnow()
    )
    embed.description = (
        f"👤 **Usuário:** {membro.mention} (`{membro.id}`)\n"
        f"📄 **Motivo do ban:** {motivo}\n"
        f"❌ **Erro:** `{type(erro).__name__}`\n\n"
        f"Confira se o cargo do bot está **acima** do cargo dessa pessoa e se ele tem a permissão **Banir Membros**. "
        f"Ninguém consegue banir o dono do servidor."
    )
    embed.set_footer(text=f"Segurança Ativa {config['nome']}", icon_url=guild.icon.url if guild.icon else None)
    await canal.send(embed=embed)

async def executar_banimento(guild, membro, staff, motivo, acao_log, prova_url=None, prova_arquivo=None):
    config = obter_config(guild.id)
    nome_servidor = config["nome"] if config else guild.name

    if membro.id in bot.banindo:
        return True  # já tem um ban em andamento para essa pessoa (ex.: várias imagens de uma vez)
    bot.banindo.add(membro.id)
    bot.ultimos_banimentos.add(membro.id)

    try:
        carta_dm = (
            f"**{nome_servidor} | Aviso de Banimento**\n\n"
            f"Caro(a) {membro.mention},\n\n"
            f"Você foi banido(a) por violar as nossas regras.\n\n"
            f"**Motivo:** {motivo}\n\n"
            f"A decisão de banir permanece final e não será revertida sem uma consideração significativa da nossa equipe.\n\n"
            f"*Atenciosamente,*\n"
            f"**Equipe de Moderação - {nome_servidor}**"
        )
        try:
            await membro.send(carta_dm)
        except Exception: 
            pass 

        try:
            await membro.ban(reason=f"{staff.name} | {motivo}")
        except Exception as e:
            bot.ultimos_banimentos.discard(membro.id)
            print(f"[ERRO PERMISSÃO] Não foi possível banir o usuário {membro.name} ({membro.id}). Detalhe: {e}")
            try:
                await log_falha_ban(guild, membro, motivo, e)
            except Exception:
                pass
            return False

        try:
            await log_punicao_bonito(guild, membro, staff, acao_log, motivo, prova_url, prova_arquivo)
        except Exception as e:
            print(f"[Aviso] {membro.name} foi banido, mas o log da punição falhou: {e}")
        return True
    finally:
        bot.banindo.discard(membro.id)

async def log_filtro_automod(message, ocorrencia, texto_original):
    config = obter_config(message.guild.id)
    if not config or not (canal := bot.get_channel(config["canal_logs"])): 
        return

    embed = discord.Embed(
        title=f"🛡️ {config['nome']} - Filtro Automático", 
        color=0x950606, 
        timestamp=discord.utils.utcnow()
    )
    if message.author.display_avatar: 
        embed.set_thumbnail(url=message.author.display_avatar.url)
    
    embed.description = (
        f"👤 **Usuário:** {message.author.mention}\n"
        f"📛 **Nick:** `{message.author.name}`\n"
        f"🆔 **ID:** `{message.author.id}`\n"
        f"💬 **Canal:** {message.channel.mention}\n"
        f"🚨 **Ocorrência:** `{ocorrencia}`\n\n"
        f"**Mensagem Deletada:**\n"
        f"```{texto_original}```"
    )
    
    embed.set_footer(text=f"Segurança Ativa {config['nome']}", icon_url=message.guild.icon.url if message.guild.icon else None)
    await canal.send(embed=embed)

# ==================== DETECÇÃO DE AÇÕES DA STAFF E LOGS DIVERSOS ====================
@bot.event
async def on_member_join(member):
    config = obter_config(member.guild.id)
    if config and (canal_logs := bot.get_channel(config["canal_logs"])):
        embed = discord.Embed(
            title=f"📥 {config['nome']} - Membro Entrou",
            description=f"👤 **Membro:** {member.mention} ({member.id})\nO usuário acaba de se juntar ao servidor.",
            color=0x950606,
            timestamp=discord.utils.utcnow()
        )
        if member.display_avatar:
            embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"Segurança Ativa {config['nome']}", icon_url=member.guild.icon.url if member.guild.icon else None)
        await canal_logs.send(embed=embed)

@bot.event
async def on_member_remove(member):
    config = obter_config(member.guild.id)
    if config and (canal_logs := bot.get_channel(config["canal_logs"])):
        embed = discord.Embed(
            title=f"📤 {config['nome']} - Membro Saiu",
            description=f"👤 **Membro:** {member.mention} ({member.id})\nO usuário deixou o servidor.",
            color=0x950606,
            timestamp=discord.utils.utcnow()
        )
        if member.display_avatar:
            embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"Segurança Ativa {config['nome']}", icon_url=member.guild.icon.url if member.guild.icon else None)
        await canal_logs.send(embed=embed)

@bot.event
async def on_member_ban(guild, user):
    if user.id in bot.ultimos_banimentos:
        bot.ultimos_banimentos.discard(user.id)
        return 

    await asyncio.sleep(2)
    try:
        async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.ban):
            if entry.target.id == user.id:
                if entry.user.id == bot.user.id: 
                    return 
                await log_punicao_bonito(guild, user, entry.user, "Banimento (Painel/Botão Direito)", entry.reason or "Nenhum motivo inserido.")
                return
    except: pass

@bot.event
async def on_member_unban(guild, user):
    await asyncio.sleep(2)
    try:
        async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.unban):
            if entry.target.id == user.id:
                if entry.user.id == bot.user.id: 
                    return
                await log_punicao_bonito(guild, user, entry.user, "Desbanimento (Painel/Botão Direito)", entry.reason or "Nenhum motivo inserido.")
                return
    except: pass

@bot.event
async def on_member_update(before, after):
    config = obter_config(before.guild.id)
    if not config: return
    canal_logs = bot.get_channel(config["canal_logs"])

    # Log de Mute (Timeout)
    if before.timed_out_until != after.timed_out_until:
        if after.id in bot.ultimos_mutes:
            bot.ultimos_mutes.discard(after.id)
            return

        await asyncio.sleep(2)
        try:
            if after.timed_out_until is not None:
                async for entry in before.guild.audit_logs(limit=5, action=discord.AuditLogAction.member_update):
                    if entry.target.id == after.id and hasattr(entry.after, 'timed_out_until'):
                        if entry.user.id == bot.user.id: return
                        tempo = after.timed_out_until - discord.utils.utcnow()
                        minutos = max(1, int(tempo.total_seconds() / 60))
                        await log_punicao_bonito(before.guild, after, entry.user, f"Mute ({minutos} mins - Discord)", entry.reason or "Aplicado via painel/botão direito.")
                        return
            elif after.timed_out_until is None:
                async for entry in before.guild.audit_logs(limit=5, action=discord.AuditLogAction.member_update):
                    if entry.target.id == after.id and hasattr(entry.before, 'timed_out_until') and not hasattr(entry.after, 'timed_out_until'):
                        if entry.user.id == bot.user.id: return
                        await log_punicao_bonito(before.guild, after, entry.user, "Desmutado (Discord)", entry.reason or "Removido via painel/botão direito.")
                        return
        except: pass

    # Log de Nickname
    if before.nick != after.nick:
        if canal_logs:
            embed = discord.Embed(
                title=f"👤 {config['nome']} - Alteração de Apelido",
                color=0x950606,
                timestamp=discord.utils.utcnow()
            )
            if after.display_avatar: embed.set_thumbnail(url=after.display_avatar.url)
            embed.description = f"👤 **Membro:** {after.mention} ({after.id})\n🏷️ **Antigo:** `{before.nick or before.name}`\n🏷️ **Novo:** `{after.nick or after.name}`"
            embed.set_footer(text=f"Segurança Ativa {config['nome']}", icon_url=before.guild.icon.url if before.guild.icon else None)
            await canal_logs.send(embed=embed)

    # Log de Avatar do Servidor (Guild Specific Avatar)
    if before.guild_avatar != after.guild_avatar:
        if canal_logs:
            embed = discord.Embed(
                title=f"🖼️ {config['nome']} - Alteração de Avatar do Servidor",
                color=0x950606,
                timestamp=discord.utils.utcnow()
            )
            avatar_antigo = before.guild_avatar.url if before.guild_avatar else (before.avatar.url if before.avatar else before.default_avatar.url)
            avatar_novo = after.guild_avatar.url if after.guild_avatar else (after.avatar.url if after.avatar else after.default_avatar.url)
            
            embed.description = (
                f"👤 **Membro:** {after.mention} ({after.id})\n"
                f"📸 **Avatar Anterior:** [Clique para abrir]({avatar_antigo})\n"
                f"✨ **Avatar Novo:** [Clique para abrir]({avatar_novo})\n\n"
                f"*O membro mudou sua foto de perfil específica neste servidor.*"
            )
            embed.set_thumbnail(url=avatar_antigo)
            embed.set_image(url=avatar_novo)
            embed.set_footer(text=f"Segurança Ativa {config['nome']}", icon_url=before.guild.icon.url if before.guild.icon else None)
            await canal_logs.send(embed=embed)

@bot.event
async def on_user_update(before, after):
    for guild in bot.guilds:
        config = obter_config(guild.id)
        if not config: continue
        member = guild.get_member(after.id)
        if not member: continue
        canal_logs = bot.get_channel(config["canal_logs"])
        if not canal_logs: continue

        # Nome Global
        if before.name != after.name:
            embed = discord.Embed(title=f"👤 {config['nome']} - Alteração de Nome Global", color=0x950606, timestamp=discord.utils.utcnow())
            if after.display_avatar: embed.set_thumbnail(url=after.display_avatar.url)
            embed.description = f"👤 **Membro:** {member.mention} ({member.id})\n📛 **Antigo:** `{before.name}`\n📛 **Novo:** `{after.name}`"
            embed.set_footer(text=f"Segurança Ativa {config['nome']}", icon_url=guild.icon.url if guild.icon else None)
            await canal_logs.send(embed=embed)

        # Avatar Global (Corrige o bug de não mostrar o antigo e novo lado a lado)
        if before.avatar != after.avatar:
            embed = discord.Embed(
                title=f"🖼️ {config['nome']} - Alteração de Avatar", 
                color=0x950606, 
                timestamp=discord.utils.utcnow()
            )
            
            # Garante que pegamos as URLs corretas mesmo após a alteração
            avatar_antigo_url = before.avatar.url if before.avatar else before.default_avatar.url
            avatar_novo_url = after.avatar.url if after.avatar else after.default_avatar.url

            embed.description = (
                f"👤 **Membro:** {member.mention} ({member.id})\n"
                f"📸 **Avatar Anterior:** [Clique para abrir]({avatar_antigo_url})\n"
                f"✨ **Avatar Novo:** [Clique para abrir]({avatar_novo_url})\n\n"
                f"*O membro alterou sua foto de perfil global. O avatar anterior está na miniatura (canto direito) e o novo está ampliado abaixo.*"
            )
            # Mostra o antigo como uma miniatura pequena no canto e o novo gigante abaixo!
            embed.set_thumbnail(url=avatar_antigo_url)
            embed.set_image(url=avatar_novo_url)
            embed.set_footer(text=f"Segurança Ativa {config['nome']}", icon_url=guild.icon.url if guild.icon else None)
            await canal_logs.send(embed=embed)

@bot.event
async def on_voice_state_update(member, before, after):
    config = obter_config(member.guild.id)
    if not config or not (canal_logs := bot.get_channel(config["canal_logs"])): return

    embed = discord.Embed(color=0x950606, timestamp=discord.utils.utcnow())
    if member.display_avatar: embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=f"Segurança Ativa {config['nome']}", icon_url=member.guild.icon.url if member.guild.icon else None)

    if before.channel is None and after.channel is not None:
        tipo = "Palco 🎤" if isinstance(after.channel, discord.StageChannel) else "Canal de Voz 🔊"
        embed.title = f"🔊 {config['nome']} - Entrada em Call"
        embed.description = f"👤 **Membro:** {member.mention} ({member.id})\n📥 **Conectou em:** {after.channel.mention} ({after.channel.name})\n🏷️ **Tipo:** `{tipo}`"
        await canal_logs.send(embed=embed)

    elif before.channel is not None and after.channel is None:
        tipo = "Palco 🎤" if isinstance(before.channel, discord.StageChannel) else "Canal de Voz 🔊"
        embed.title = f"🔇 {config['nome']} - Saída de Call"
        embed.description = f"👤 **Membro:** {member.mention} ({member.id})\n📤 **Desconectou de:** {before.channel.mention} ({before.channel.name})\n🏷️ **Tipo:** `{tipo}`"
        await canal_logs.send(embed=embed)

    elif before.channel is not None and after.channel is not None and before.channel.id != after.channel.id:
        tipo_antigo = "Palco 🎤" if isinstance(before.channel, discord.StageChannel) else "Canal de Voz 🔊"
        tipo_novo = "Palco 🎤" if isinstance(after.channel, discord.StageChannel) else "Canal de Voz 🔊"
        embed.title = f"🔁 {config['nome']} - Movimentação de Call"
        embed.description = f"👤 **Membro:** {member.mention} ({member.id})\n📤 **Anterior:** {before.channel.mention} (`{tipo_antigo}`)\n📥 **Novo:** {after.channel.mention} (`{tipo_novo}`)"
        await canal_logs.send(embed=embed)

# ==================== SISTEMA DE TICKETS (#950606) ====================
class DropdownGhoul(discord.ui.Select):
    def __init__(self):
        opcoes = [
            discord.SelectOption(label="Denúncias", value="denuncias", description="Denúncias, ajuda técnica e revisão.", emoji="🚨"), 
            discord.SelectOption(label="Suporte", value="suporte", description="Recorra a uma punição (warn/mute).", emoji="🛠️"), 
            discord.SelectOption(label="Dúvidas", value="duvidas", description="Tire dúvidas sobre a comunidade ou regras.", emoji="❓"),
            discord.SelectOption(label="Exposed", value="exposed", description="Falar sobre membro expondo outro.", emoji="⚠️")
        ]
        super().__init__(placeholder="Selecione o setor do suporte...", min_values=1, max_values=1, options=opcoes, custom_id="sel_ghoul")
    async def callback(self, interaction: discord.Interaction): 
        await criar_canal_ticket(interaction, self.values[0])

class DropdownKings(discord.ui.Select):
    def __init__(self):
        opcoes = [
            discord.SelectOption(label="Robux", value="robux", description="Comprar Robux ou ver tabelas", emoji="💰"), 
            discord.SelectOption(label="Gamepass", value="gamepass", description="Comprar Gamepasses do Blox Fruits", emoji="📦"), 
            discord.SelectOption(label="Frutas Perm", value="frutas_perm", description="Comprar Frutas Permanentes", emoji="🍊"),
            discord.SelectOption(label="Frutas Físicas", value="frutas_fisicas", description="Comprar Frutas Físicas (Inventário)", emoji="🍎"),
            discord.SelectOption(label="Contas GHM/Fruta", value="contas", description="Geral, Fruta Inv ou Contas Random", emoji="💸")
        ]
        super().__init__(placeholder="Selecione a categoria correta no menu abaixo...", min_values=1, max_values=1, options=opcoes, custom_id="sel_kings")
    async def callback(self, interaction: discord.Interaction): 
        await criar_canal_ticket(interaction, self.values[0])

class DropdownNightware(discord.ui.Select):
    def __init__(self):
        opcoes = [
            discord.SelectOption(label="Comprar", value="compras", description="Adquirir produtos de nossa loja.", emoji="🛒"), 
            discord.SelectOption(label="Financeiro", value="financeiro", description="Tratar de pagamentos, reembolsos e faturamento.", emoji="💳"), 
            discord.SelectOption(label="Suporte", value="suporte", description="Atendimento geral para dúvidas e problemas.", emoji="🛠️")
        ]
        super().__init__(placeholder="Selecione a categoria...", min_values=1, max_values=1, options=opcoes, custom_id="sel_nightware")
    async def callback(self, interaction: discord.Interaction): 
        await criar_canal_ticket(interaction, self.values[0])

class ViewGhoul(discord.ui.View):
    def __init__(self): 
        super().__init__(timeout=None)
        self.add_item(DropdownGhoul())

class ViewKings(discord.ui.View):
    def __init__(self): 
        super().__init__(timeout=None)
        self.add_item(DropdownKings())

class ViewNightware(discord.ui.View):
    def __init__(self): 
        super().__init__(timeout=None)
        self.add_item(DropdownNightware())

class ViewValidar(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="Validar", style=discord.ButtonStyle.danger, emoji="🎫", custom_id="btn_validar_cod")
    async def validar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await criar_canal_ticket(interaction, "coldawn")

class ViewFechar(discord.ui.View):
    def __init__(self): 
        super().__init__(timeout=None)
    @discord.ui.button(label="Fechar Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="btn_fechar")
    async def fechar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 Fechando canal em 5 segundos...", ephemeral=True)
        await asyncio.sleep(5)
        await interaction.channel.delete()

async def criar_canal_ticket(interaction: discord.Interaction, setor: str):
    config = obter_config(interaction.guild.id)
    if not config or interaction.response.is_done(): 
        return
    categoria = discord.utils.get(interaction.guild.categories, id=config["categoria_tickets"])
    cargo_staff = interaction.guild.get_role(config["cargo_staff"])
    
    overwrites = {
        interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
        interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True),
        interaction.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
    }
    if cargo_staff: 
        overwrites[cargo_staff] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

    canal = await interaction.guild.create_text_channel(name=f"ticket-{interaction.user.name}-{setor}", category=categoria, overwrites=overwrites)
    
    embed = discord.Embed(
        title=f"🚨 {config['nome']} - Atendimento", 
        description=(
            f"Olá {interaction.user.mention},\n\n"
            f"Seu ticket para **{setor.upper()}** foi aberto com sucesso!\n"
            f"Descreva detalhadamente o que precisa abaixo para que a equipe possa te responder."
        ), 
        color=0x950606
    )
    await canal.send(content=f"{interaction.user.mention} {cargo_staff.mention if cargo_staff else ''}", embed=embed, view=ViewFechar())
    await interaction.response.send_message(f"✅ Ticket criado em {canal.mention}!", ephemeral=True)

# ==================== VERIFICAÇÃO DE IMAGENS NO CHAT ====================
async def baixar_imagem(url, anexo=None):
    """Baixa a imagem SEM travar o bot (o requests.get antigo congelava o bot inteiro durante o download)."""
    if anexo is not None:
        if anexo.size and anexo.size > LIMITE_DOWNLOAD:
            return None
        try:
            return await anexo.read()
        except Exception:
            pass  # se falhar, tenta pelo link abaixo
    try:
        timeout = aiohttp.ClientTimeout(total=15)
        async with bot.sessao_http.get(url, headers=HEADERS_NAVEGADOR, timeout=timeout) as resp:
            if resp.status != 200:
                return None
            if resp.content_length and resp.content_length > LIMITE_DOWNLOAD:
                return None
            dados = bytearray()
            async for pedaco in resp.content.iter_chunked(65536):
                dados.extend(pedaco)
                if len(dados) > LIMITE_DOWNLOAD:
                    return None
            return bytes(dados)
    except Exception:
        return None

def guardar_no_cache(message_id, dados, nome):
    """Guarda a 1ª imagem da mensagem para o log de 'Mensagem Apagada' (o link do Discord morre ao apagar)."""
    if len(dados) > LIMITE_CACHE:
        return
    bot.midia_cache[message_id] = [(dados, nome_seguro(nome))]
    if len(bot.midia_cache) > 300:
        # Remove o mais antigo do cache para evitar vazamento de memória
        bot.midia_cache.pop(next(iter(bot.midia_cache)))

async def checar_imagens_proibidas(message, so_embeds=False):
    """Confere as imagens da mensagem. Se alguma for parecida com a lista, apaga e bane. Retorna True se baniu."""
    fontes = coletar_fontes_imagem(message, so_embeds)
    if not fontes:
        return False

    baixados = await asyncio.gather(*(baixar_imagem(url, anexo) for url, _, anexo in fontes))
    loop = asyncio.get_running_loop()

    for (url, nome, _), dados in zip(fontes, baixados):
        if not dados:
            continue
        try:
            # Cálculo pesado numa thread separada: o bot continua respondendo normalmente
            _, melhor, _ = await loop.run_in_executor(None, avaliar_imagem, dados)
        except Exception as e:
            print(f"[Aviso Automod] Erro ao analisar a imagem {url}: {e}")
            continue

        if melhor and melhor[0] <= LIMITE_HASH:
            dist, algoritmo, _, origem = melhor
            bot.mensagens_ignoradas.add(message.id)
            try: await message.delete()
            except: pass

            # Executa banimento e envia a imagem como prova (anexada no log, não depende do link)
            await executar_banimento(
                message.guild, message.author, bot.user,
                "Envio de imagem proibida.",
                f"Ban (Automático) • {algoritmo} dist. {dist} • {origem}",
                prova_url=url,
                prova_arquivo=(dados, nome_seguro(nome))
            )
            return True

    if not so_embeds:
        for (_, nome, _), dados in zip(fontes, baixados):
            if dados:
                guardar_no_cache(message.id, dados, nome)
                break
    return False

# ==================== IMAGENS BLOQUEADAS PELO COMANDO (lista guardada no Discord) ====================
# Cada /bloquear_imagem vira UMA mensagem (só com os códigos/hashes, sem a imagem) no canal privado #imagens-bloqueadas.
# Quando o bot liga, ele lê esse canal e recarrega a lista. Assim nada se perde se a hospedagem apagar arquivos.
async def obter_canal_registro(guild, criar=False):
    canal = discord.utils.get(guild.text_channels, name=NOME_CANAL_REGISTRO)
    if canal or not criar:
        return canal

    config = obter_config(guild.id) or {}
    canal_logs = bot.get_channel(config.get("canal_logs", 0))
    cargo_staff = guild.get_role(config.get("cargo_staff", 0))
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
    }
    if cargo_staff:
        overwrites[cargo_staff] = discord.PermissionOverwrite(view_channel=True, send_messages=False, read_message_history=True)
    return await guild.create_text_channel(
        NOME_CANAL_REGISTRO,
        overwrites=overwrites,
        category=canal_logs.category if canal_logs else None,
        topic="Lista de imagens bloqueadas do bot. NÃO apague as mensagens daqui (para desbloquear use /desbloquear_imagem).",
        reason="Registro de imagens bloqueadas"
    )

async def carregar_registros():
    """Lê o canal #imagens-bloqueadas de cada servidor e recarrega a lista (chamado quando o bot liga)."""
    carregadas = {}
    for guild in bot.guilds:
        if not obter_config(guild.id):
            continue
        canal = await obter_canal_registro(guild)
        if not canal:
            continue
        try:
            async for msg in canal.history(limit=None, oldest_first=True):
                if msg.author.id != bot.user.id:
                    continue
                dados = ler_registro(msg.content)
                if dados:
                    dados.update(msg_id=msg.id, canal_id=canal.id)
                    carregadas[msg.id] = dados
        except Exception as e:
            print(f"[Aviso] Não consegui ler o canal #{NOME_CANAL_REGISTRO} de {guild.name}: {e}")
    bot.imagens_registradas = carregadas
    reconstruir_hashes(carregadas.values())
    print(f"[Imagens] {len(carregadas)} imagem(ns) bloqueada(s) por comando carregada(s).")

async def registrar_imagem(guild, user, dados, nome=None):
    """Bloqueia uma imagem (usado pelo /bloquear_imagem). Retorna (ok, texto_para_o_admin)."""
    loop = asyncio.get_running_loop()
    try:
        frames, melhor, _ = await loop.run_in_executor(None, avaliar_imagem, dados)
    except Exception as e:
        return False, f"❌ Não consegui ler essa imagem: `{e}`"
    if not frames:
        return False, "❌ Não consegui calcular os hashes dessa imagem."

    if melhor and melhor[0] <= LIMITE_HASH:
        dist, alg, _, origem = melhor
        quem = "uma imagem da lista fixa do código" if origem == "lista" else f"`{origem}`"
        return False, f"ℹ️ Essa imagem **já é bloqueada**: é parecida com {quem} (`{alg}`, distância {dist}). Não precisei adicionar."

    # Em GIF animado, usa o primeiro frame que tenha detalhe (o 1º às vezes é só uma tela preta)
    escolhido = next((f for f in frames if not eh_hash_liso(f)), None)
    if escolhido is None:
        return False, "❌ Essa imagem tem quase nenhum detalhe (uma cor só, degradê...). Bloquear ela baniria muita gente inocente."

    async with bot.trava_registro:
        if len(bot.imagens_registradas) >= LIMITE_IMAGENS_REGISTRADAS:
            return False, f"❌ Limite de {LIMITE_IMAGENS_REGISTRADAS} imagens atingido. Remova alguma com `/desbloquear_imagem`."
        usados = {e["nome"].lower() for e in bot.imagens_registradas.values()}
        nome = limpar_nome(nome) or proximo_nome_livre(usados)
        if nome.lower() in usados:
            return False, f"❌ Já existe uma imagem chamada `{nome}`. Escolha outro nome."

        canal_ja_existia = await obter_canal_registro(guild) is not None
        try:
            canal = await obter_canal_registro(guild, criar=True)
            hashes_hex = {alg: str(escolhido[alg]) for alg in ALGORITMOS}
            quando = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
            msg = await canal.send(
                montar_registro(nome, hashes_hex, user.id, quando),
                allowed_mentions=discord.AllowedMentions.none()
            )
        except discord.HTTPException as e:  # inclui Forbidden (sem permissão)
            return False, (
                f"❌ Não consegui guardar a lista no canal `#{NOME_CANAL_REGISTRO}` ({type(e).__name__}). "
                f"Crie um canal com esse nome (só para staff), dê ao bot permissão de ver e enviar mensagens nele e tente de novo."
            )
        bot.imagens_registradas[msg.id] = {
            "nome": nome, "hashes": hashes_hex, "por": user.id, "quando": quando,
            "msg_id": msg.id, "canal_id": canal.id
        }
        reconstruir_hashes(bot.imagens_registradas.values())

    texto = (
        f"✅ **Imagem bloqueada** como `{nome}`.\n"
        f"Quem enviar essa imagem (ou uma parecida), em qualquer servidor do bot, leva ban automático."
    )
    if not canal_ja_existia:
        texto += (
            f"\n\n📁 Criei o canal privado `#{NOME_CANAL_REGISTRO}` para guardar a lista "
            f"(só os códigos, não a imagem). **Não apague as mensagens dele.**"
        )
    return True, texto

async def remover_imagem(nome):
    """Desbloqueia pelo nome (usado pelo /desbloquear_imagem). Retorna (ok, texto_para_o_admin)."""
    async with bot.trava_registro:
        chave = (nome or "").strip().lower()
        alvos = [e for e in bot.imagens_registradas.values() if e["nome"].lower() == chave]
        if not alvos:
            return False, f"❌ Não achei nenhuma imagem bloqueada chamada `{nome}`. Veja os nomes com `/listar_imagens`."
        falhas = 0
        for e in alvos:
            bot.imagens_registradas.pop(e["msg_id"], None)
            try:
                canal = bot.get_channel(e["canal_id"]) or await bot.fetch_channel(e["canal_id"])
                await canal.get_partial_message(e["msg_id"]).delete()
            except discord.NotFound:
                pass  # a mensagem já tinha sido apagada
            except Exception as ex:
                falhas += 1
                print(f"[Aviso] Não consegui apagar a mensagem de registro de '{e['nome']}': {ex}")
        reconstruir_hashes(bot.imagens_registradas.values())

    texto = f"✅ A imagem `{alvos[0]['nome']}` foi desbloqueada."
    if falhas:
        texto += (
            f"\n⚠️ Não consegui apagar a mensagem dela no canal `#{NOME_CANAL_REGISTRO}`. "
            f"Apague manualmente, senão ela volta a ser bloqueada quando o bot reiniciar."
        )
    return True, texto

def esquecer_imagens_apagadas(ids):
    """Se alguém apagar a mensagem de registro direto no canal, a imagem deixa de ser bloqueada."""
    mudou = False
    for mid in ids:
        if bot.imagens_registradas.pop(mid, None) is not None:
            mudou = True
    if mudou:
        reconstruir_hashes(bot.imagens_registradas.values())

@bot.event
async def on_raw_message_delete(payload):
    esquecer_imagens_apagadas([payload.message_id])

@bot.event
async def on_raw_bulk_message_delete(payload):
    esquecer_imagens_apagadas(payload.message_ids)

# ==================== AUTOMODERAÇÃO ATIVA E FORTE ====================
@bot.event
async def on_message(message):
    if message.author.bot or not message.guild: 
        return
    config = obter_config(message.guild.id)
    if not config: 
        return

    # 1. Filtro de Termos Proibidos (Mensagens Fake / Ban Automático) - sem exceção de Staff
    termo = achar_na_lista(message.content, TERMOS_BAN_C)
    if termo:
        bot.mensagens_ignoradas.add(message.id)
        try: await message.delete()
        except: pass
        
        # Executa banimento e manda para os logs sem exceção de Staff
        await executar_banimento(message.guild, message.author, bot.user, f"Tentativa de golpe (Mensagem Fake): `{termo}`", "Ban (Automático)")
        return

    # 2. Filtro de Imagens Proibidas (Hash) - ANTES do palavrão, senão uma mensagem com palavrão + imagem
    #    proibida só tinha o texto apagado e a imagem nunca era conferida.
    try:
        if await checar_imagens_proibidas(message):
            return
    except Exception as e:
        print(f"[Aviso Automod] Erro na checagem de imagens: {e}")

    # 3. Filtro de Palavrões / Xingamentos (só palavra INTEIRA)
    palavrao = achar_na_lista(message.content, PALAVROES_C)
    if palavrao:
        bot.mensagens_ignoradas.add(message.id)
        try: await message.delete()
        except: pass
        
        await log_filtro_automod(message, f"Palavrão/Xingamento Detectado ({palavrao})", message.content)
        return 

    # 4. Filtro de Convites/Links Proibidos
    if re.search(r'(discord\.gg/|discord\.com/invite/)', message.content.lower()):
        bot.mensagens_ignoradas.add(message.id)
        try: await message.delete()
        except: pass
        
        try:
            bot.ultimos_mutes.add(message.author.id)
            await message.author.timeout(datetime.timedelta(hours=1), reason="Divulgação Automática.")
            await log_punicao_bonito(message.guild, message.author, bot.user, "Mute 1 Hora (Automático)", "Divulgação de link de convite.")
        except: pass
        return

@bot.event
async def on_message_delete(message):
    if message.author.bot or not message.guild: return
    midias = bot.midia_cache.pop(message.id, None)  # sempre limpa o cache dessa mensagem
    if message.id in bot.mensagens_ignoradas:
        bot.mensagens_ignoradas.discard(message.id)
        return

    config = obter_config(message.guild.id)
    if config and (canal_logs := bot.get_channel(config["canal_logs"])):
        embed = discord.Embed(title=f"🗑️ {config['nome']} - Mensagem Apagada", color=0x950606, timestamp=discord.utils.utcnow())
        if message.author.display_avatar: embed.set_thumbnail(url=message.author.display_avatar.url)
            
        conteudo = message.content[:1000] if message.content else "Mensagem vazia ou apenas mídia"
        embed.description = f"👤 **Usuário:** {message.author.mention} ({message.author.id})\n💬 **Canal:** {message.channel.mention}\n\n**Conteúdo Original:**\n```{conteudo}```"
        
        # Faz o upload direto dos bytes guardados em cache para o canal de logs (Garante 100% que a mídia apareça)
        arquivos_enviar = []
        if midias:
            dados_binarios, nome_arquivo = midias[0]
            arquivos_enviar.append(discord.File(BytesIO(dados_binarios), filename=nome_arquivo))
            # Mostra a primeira imagem anexada ampliada no embed
            embed.set_image(url=f"attachment://{nome_arquivo}")
        
        embed.set_footer(text=f"Segurança Ativa {config['nome']}", icon_url=message.guild.icon.url if message.guild.icon else None)
        
        try:
            if arquivos_enviar:
                await canal_logs.send(embed=embed, files=arquivos_enviar)
            else:
                await canal_logs.send(embed=embed)
        except discord.HTTPException:
            if not arquivos_enviar:
                raise
            embed.remove_image()  # arquivo grande demais para o canal: manda o log sem a imagem
            await canal_logs.send(embed=embed)

@bot.event
async def on_message_edit(before, after):
    if after.author.bot or not after.guild: return

    # O Discord "edita" a mensagem quando termina de gerar a prévia de um link (embed): confere as imagens da prévia
    if len(after.embeds) > len(before.embeds):
        try:
            if await checar_imagens_proibidas(after, so_embeds=True):
                return
        except Exception as e:
            print(f"[Aviso Automod] Erro ao checar a prévia do link: {e}")

    if before.content == after.content: return

    config = obter_config(before.guild.id)
    if config and (canal_logs := bot.get_channel(config["canal_logs"])):
        embed = discord.Embed(title=f"📝 {config['nome']} - Mensagem Editada", color=0x950606, timestamp=discord.utils.utcnow())
        if before.author.display_avatar: embed.set_thumbnail(url=before.author.display_avatar.url)

        conteudo_antigo = before.content[:1000] if before.content else "Sem conteúdo"
        conteudo_novo = after.content[:1000] if after.content else "Sem conteúdo"

        embed.description = f"""👤 **Usuário:** {before.author.mention} ({before.author.id})
💬 **Canal:** {before.channel.mention}

**Conteúdo Anterior:**
```{conteudo_antigo}```

**Conteúdo Novo:**
```{conteudo_novo}```"""
        
        embed.set_footer(text=f"Segurança Ativa {config['nome']}", icon_url=before.guild.icon.url if before.guild.icon else None)
        await canal_logs.send(embed=embed)

# ==================== COMANDOS DE BARRA (#950606) ====================
@bot.tree.command(name="mute", description="Silencia um membro no servidor temporariamente.")
@app_commands.default_permissions(moderate_members=True)
async def mute_slash(interaction: discord.Interaction, membro: discord.Member, tempo_minutos: int, motivo: str = "Sem motivo especificado"):
    await interaction.response.defer(ephemeral=True)
    try:
        bot.ultimos_mutes.add(membro.id)
        await membro.timeout(datetime.timedelta(minutes=tempo_minutos), reason=f"{interaction.user.name} | {motivo}")
        await interaction.followup.send(f"✅ O usuário {membro.mention} foi silenciado por {tempo_minutos} minuto(s) com sucesso.")
        await log_punicao_bonito(interaction.guild, membro, interaction.user, f"Mute Comando ({tempo_minutos} mins)", motivo)
    except Exception:
        await interaction.followup.send("❌ Não foi possível mutar. Verifique se o meu cargo está acima do cargo desse usuário.")

@bot.tree.command(name="ban", description="Bane um membro do servidor permanentemente.")
@app_commands.default_permissions(ban_members=True)
async def ban_slash(interaction: discord.Interaction, membro: discord.Member, motivo: str = "Sem motivo especificado"):
    await interaction.response.defer(ephemeral=True)
    sucesso = await executar_banimento(interaction.guild, membro, interaction.user, motivo, "Banimento Comando")
    if sucesso:
        await interaction.followup.send(f"🔨 O usuário {membro.mention} foi banido com sucesso.")
    else:
        await interaction.followup.send("❌ Erro ao banir. Verifique se o meu cargo é superior ao da pessoa que você está tentando banir.")

MSG_SEM_PERMISSAO = "❌ Só administradores dos servidores configurados no bot podem usar esse comando."

def eh_admin(interaction):
    """Confere de verdade quem usou o comando: administrador E em servidor configurado no bot.
    (A lista de imagens vale para todos os servidores, então um admin de um servidor qualquer onde o bot
    foi adicionado não pode mexer nela. O default_permissions sozinho não protege: o servidor pode mudá-lo.)"""
    return (
        interaction.guild is not None
        and obter_config(interaction.guild.id) is not None
        and interaction.user.guild_permissions.administrator
    )

async def avisar_erro_comando(interaction, nome_comando, erro):
    print(f"[ERRO] /{nome_comando}: {erro!r}")
    try:
        await interaction.followup.send(f"❌ Deu um erro inesperado (`{type(erro).__name__}`). Tente de novo; se repetir, veja o console do bot.")
    except Exception:
        pass

@bot.tree.command(name="bloquear_imagem", description="Bloqueia uma imagem: quem enviar ela (ou uma parecida) leva ban automático.")
@app_commands.describe(imagem="A imagem que deve ser bloqueada", nome="Um nome para você identificar depois (opcional)")
@app_commands.default_permissions(administrator=True)
async def bloquear_imagem_slash(interaction: discord.Interaction, imagem: discord.Attachment, nome: str = None):
    await interaction.response.defer(ephemeral=True)
    try:
        if not eh_admin(interaction):
            await interaction.followup.send(MSG_SEM_PERMISSAO)
            return
        tipo = (imagem.content_type or "").lower()
        if not (tipo.startswith("image/") or imagem.filename.lower().endswith(EXT_IMAGEM)):
            await interaction.followup.send("❌ Esse arquivo não parece ser uma imagem.")
            return
        if imagem.size > LIMITE_DOWNLOAD:
            await interaction.followup.send("❌ Essa imagem é grande demais.")
            return
        dados = await imagem.read()
        _, texto = await registrar_imagem(interaction.guild, interaction.user, dados, nome)
        await interaction.followup.send(texto)
    except Exception as e:
        await avisar_erro_comando(interaction, "bloquear_imagem", e)

@bot.tree.command(name="desbloquear_imagem", description="Tira uma imagem da lista de bloqueadas.")
@app_commands.describe(nome="Escolha a imagem na lista")
@app_commands.default_permissions(administrator=True)
async def desbloquear_imagem_slash(interaction: discord.Interaction, nome: str):
    await interaction.response.defer(ephemeral=True)
    try:
        if not eh_admin(interaction):
            await interaction.followup.send(MSG_SEM_PERMISSAO)
            return
        _, texto = await remover_imagem(nome)
        await interaction.followup.send(texto)
    except Exception as e:
        await avisar_erro_comando(interaction, "desbloquear_imagem", e)

@desbloquear_imagem_slash.autocomplete("nome")
async def autocompletar_imagens(interaction: discord.Interaction, atual: str):
    if not eh_admin(interaction):
        return []
    atual = atual.lower()
    nomes = sorted({e["nome"] for e in bot.imagens_registradas.values() if atual in e["nome"].lower()})
    return [app_commands.Choice(name=n[:100], value=n[:100]) for n in nomes[:25]]

@bot.tree.command(name="listar_imagens", description="Mostra as imagens bloqueadas pelo comando /bloquear_imagem.")
@app_commands.default_permissions(administrator=True)
async def listar_imagens_slash(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    try:
        if not eh_admin(interaction):
            await interaction.followup.send(MSG_SEM_PERMISSAO)
            return
        entradas = sorted(bot.imagens_registradas.values(), key=lambda e: e["quando"])
        linhas = [f"• **{e['nome']}** — <@{e['por']}> — <t:{e['quando']}:d>" for e in entradas]
        texto = (
            f"🚫 **Imagens bloqueadas por comando:** {len(entradas)}/{LIMITE_IMAGENS_REGISTRADAS}\n"
            f"📌 **Hashes fixos no código:** {len(HASHES_FIXOS)}\n\n"
            + ("\n".join(linhas) if linhas else "_Nenhuma ainda. Use /bloquear_imagem._")
        )
        if len(texto) > 1900:
            arquivo = discord.File(BytesIO(texto.encode("utf-8")), filename="imagens_bloqueadas.txt")
            await interaction.followup.send("A lista é grande, segue em arquivo:", file=arquivo)
        else:
            await interaction.followup.send(texto)
    except Exception as e:
        await avisar_erro_comando(interaction, "listar_imagens", e)

@bot.tree.command(name="testar_imagem", description="Mostra os hashes de uma imagem e se o bot a baniria (não bloqueia nada).")
@app_commands.default_permissions(administrator=True)
async def testar_imagem_slash(interaction: discord.Interaction, imagem: discord.Attachment):
    await interaction.response.defer(ephemeral=True)
    try:
        if not eh_admin(interaction):
            await interaction.followup.send(MSG_SEM_PERMISSAO)
            return
        dados = await imagem.read()
        try:
            frames, melhor, menores = await asyncio.get_running_loop().run_in_executor(None, avaliar_imagem, dados)
        except Exception as e:
            await interaction.followup.send(f"❌ Não consegui ler essa imagem: `{type(e).__name__}`")
            return
        if not frames:
            await interaction.followup.send("❌ Não consegui calcular os hashes dessa imagem.")
            return

        h = frames[0]
        texto = (
            "**Hashes desta imagem** (para bloquear ela, use `/bloquear_imagem`):\n"
            f"```\naverage: {h['average']}\nphash:   {h['phash']}\ndhash:   {h['dhash']}\n```"
        )
        if melhor is None:
            texto += "\nNão há nenhuma imagem na lista de bloqueadas, então nada seria banido."
        else:
            dist, alg, _, origem = melhor
            texto += (
                f"\n**Menor distância até a lista** (0 = igual, limite atual = {LIMITE_HASH}):\n"
                f"```\naverage: {menores['average']}\nphash:   {menores['phash']}\ndhash:   {menores['dhash']}\n```"
            )
            if dist <= LIMITE_HASH:
                texto += f"\n🚫 **Seria BANIDA** — `{alg}`, distância {dist}, parecida com `{origem}`."
            else:
                texto += f"\n✅ **Não seria banida** — a mais próxima ficou a {dist} de distância (`{alg}`, `{origem}`)."
        await interaction.followup.send(texto)
    except Exception as e:
        await avisar_erro_comando(interaction, "testar_imagem", e)

@bot.tree.command(name="painel_tickets", description="Envia o painel de atendimento de tickets no canal.")
@app_commands.choices(painel=[
    app_commands.Choice(name="GHOUL", value="ghoul"),
    app_commands.Choice(name="BLOX KINGS", value="kings"),
    app_commands.Choice(name="NIGHTWARE", value="nightware"),
    app_commands.Choice(name="COD", value="cod")
])
@app_commands.default_permissions(administrator=True)
async def painel_slash(interaction: discord.Interaction, painel: app_commands.Choice[str]):
    if painel.value == "ghoul":
        embed = discord.Embed(
            title="🛡️ CENTRAL DE ATENDIMENTO - GHOUL", 
            description=(
                "**Denúncias:**\n"
                "↳ Denúncias, ajuda técnica e revisão de punições.\n\n"
                "**Suporte:**\n"
                "↳ Recorra a uma punição (warn/mute).\n\n"
                "**Dúvidas:**\n"
                "↳ Tire dúvidas sobre a comunidade ou regras do servidor.\n\n"
                "**Exposed:**\n"
                "↳ Falar sobre algum membro que está expondo outro membro.\n\n"
                "**Lembre-se:** Nossa equipe está pronta para investigar e resolver qualquer situação de forma rápida e justa. Sua privacidade será respeitada durante todo o processo!"
            ),
            color=0x950606
        )
        embed.set_image(url=IMAGENS_TICKETS["GHOUL"])
        view = ViewGhoul()
        
    elif painel.value == "kings":
        embed = discord.Embed(title="👑 CENTRAL DE ATENDIMENTO - BLOX KINGS", description="Selecione a categoria correta no menu abaixo para abrir o seu ticket.", color=0x950606)
        embed.set_image(url=IMAGENS_TICKETS["BLOX_KINGS"])
        view = ViewKings()
        
    elif painel.value == "nightware":
        embed = discord.Embed(title="🛍️ CENTRAL DE ATENDIMENTO - NIGHTWARE", description="Selecione uma opção no menu abaixo para abrir seu ticket.", color=0x950606)
        embed.set_image(url=IMAGENS_TICKETS["NIGHTWARE"])
        view = ViewNightware()
        
    elif painel.value == "cod":
        embed = discord.Embed(
            title="TICKET DE COLDAWN", 
            description=(
                "INFORMAMOS QUE A NOVA FUNÇÃO DO SERVIDOR \"GHOUL 👻\"\n"
                "JÁ ESTÁ DISPONÍVEL. PARA PARTICIPAR DO EVENTO\n"
                "\"LEVIATHAN\", É OBRIGATÓRIO ABRIR UM TICKET PARA\n"
                "COMPROVAR QUE NÃO SE ENCONTRA EM PERÍODO DE\n"
                "COOLDOWN. A COMPROVAÇÃO DO COOLDOWN DEVERÁ SER\n"
                "REALIZADA EXCLUSIVA"
            ), 
            color=0x950606
        )
        embed.set_image(url=IMAGENS_TICKETS["COD"])
        embed.set_footer(text="Desenvolvido por Ticket King", icon_url="https://cdn.discordapp.com/attachments/1183819407013707947/1469731813709578417/GHOUL_20260207_132912_0000.png")
        view = ViewValidar()

    await interaction.channel.send(embed=embed, view=view)
    await interaction.response.send_message(f"✅ Painel **{painel.name}** enviado com sucesso!", ephemeral=True)

@bot.event
async def on_ready():
    if not bot.registro_carregado:
        bot.registro_carregado = True
        try:
            await carregar_registros()
        except Exception as e:
            print(f"[Aviso] Erro ao carregar as imagens bloqueadas: {e}")
    print(f"✅ Sistema perfeito! {bot.user.name} está online, comandos sincronizados e operando com cor #950606.")

TOKEN = os.getenv('TOKEN')
bot.run(TOKEN)
