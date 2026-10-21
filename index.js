// Bot de transmissão: Discord + página web (vídeo via LiveKit Cloud).
// Regras: só staff compartilha tela, e só 1 pessoa por vez em cada sala.
const path = require('path');
const crypto = require('crypto');
const express = require('express');
const {
  Client, GatewayIntentBits, Events, EmbedBuilder, PermissionsBitField,
  ActionRowBuilder, ButtonBuilder, ButtonStyle, MessageFlags,
} = require('discord.js');
const { AccessToken, RoomServiceClient } = require('livekit-server-sdk');

const { DISCORD_TOKEN, LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET, PORT = 3000 } = process.env;
for (const k of ['DISCORD_TOKEN', 'LIVEKIT_URL', 'LIVEKIT_API_KEY', 'LIVEKIT_API_SECRET']) {
  if (!process.env[k]) { console.error(`Falta a variável de ambiente ${k}`); process.exit(1); }
}
// No Render, RENDER_EXTERNAL_URL já vem pronta (https://seu-servico.onrender.com).
const BASE_URL = (process.env.BASE_URL || process.env.RENDER_EXTERNAL_URL || `http://localhost:${PORT}`).replace(/\/$/, '');

// Staff = quem tem um destes cargos (IDs separados por vírgula na variável STAFF_ROLE_IDS).
// Se a variável não existir, staff = quem tem a permissão "Gerenciar mensagens" (admins incluídos).
const STAFF_ROLE_IDS = (process.env.STAFF_ROLE_IDS || process.env.STAFF_ROLE_ID || '')
  .split(',').map((s) => s.trim()).filter(Boolean);

const rooms = new RoomServiceClient(LIVEKIT_URL.replace(/^ws/, 'http'), LIVEKIT_API_KEY, LIVEKIT_API_SECRET);
const client = new Client({ intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildVoiceStates] });
const EPHEMERAL = MessageFlags.Ephemeral;

// Fontes de mídia do LiveKit (números do protocolo).
const SRC_CAMERA = 1, SRC_MIC = 2, SRC_SCREEN = 3, SRC_SCREEN_AUDIO = 4;

// Acessos pessoais: código -> { uid, name, ch, chName, guildId, exp }
const pending = new Map();
// Sessões da página (para pedir/devolver a vez de compartilhar): id -> { uid, ch, guildId, exp }
const sessions = new Map();
// Quem está com a vez de compartilhar tela: canal -> { uid, since }
const sharers = new Map();

setInterval(() => {
  const now = Date.now();
  for (const [k, v] of pending) if (v.exp < now) pending.delete(k);
  for (const [k, v] of sessions) if (v.exp < now) sessions.delete(k);
}, 60_000);

async function isStaff(guildId, uid) {
  const guild = client.guilds.cache.get(guildId);
  if (!guild) return false;
  const m = await guild.members.fetch(uid).catch(() => null);
  if (!m) return false;
  if (STAFF_ROLE_IDS.length) return m.roles.cache.some((r) => STAFF_ROLE_IDS.includes(r.id));
  return m.permissions.has(PermissionsBitField.Flags.ManageMessages);
}

// Liga/desliga a permissão de publicar tela para uma pessoa na sala.
function setTela(room, uid, on) {
  return rooms.updateParticipant(room, uid, {
    permission: {
      canSubscribe: true,
      canPublish: true,
      canPublishData: true,
      canPublishSources: on ? [SRC_CAMERA, SRC_MIC, SRC_SCREEN, SRC_SCREEN_AUDIO] : [SRC_CAMERA, SRC_MIC],
    },
  });
}

// Confere se o dono da vez ainda vale; se sumiu ou nunca começou a transmitir, libera.
async function limpaVezSeVazia(room) {
  const lock = sharers.get(room);
  if (!lock) return;
  try {
    const parts = await rooms.listParticipants(room);
    const p = parts.find((x) => x.identity === lock.uid);
    if (!p) { sharers.delete(room); return; }
    const transmitindo = p.tracks.some((t) => t.source === SRC_SCREEN);
    if (!transmitindo && Date.now() - lock.since > 30_000) {
      sharers.delete(room);
      try { await setTela(room, lock.uid, false); } catch { /* ignorar */ }
    }
  } catch {
    sharers.delete(room); // sala não existe mais
  }
}

// ---------- Discord ----------
client.once(Events.ClientReady, async (c) => {
  await c.application.commands.set([{
    name: 'transmitir',
    description: 'Abre uma sala de transmissão (tela e câmera) para quem está na sua call',
    dmPermission: false,
  }]);
  console.log(`Bot online como ${c.user.tag} | ${BASE_URL}`);
});

client.on(Events.InteractionCreate, async (i) => {
  try {
    // 1) /transmitir -> posta o aviso com o botão
    if (i.isChatInputCommand() && i.commandName === 'transmitir') {
      const vc = i.member?.voice?.channel;
      if (!vc) {
        return i.reply({ content: 'Entre em uma call de voz e use /transmitir de novo.', flags: EPHEMERAL });
      }
      const embed = new EmbedBuilder()
        .setColor(0x5865f2)
        .setTitle('Sala de transmissão pronta')
        .setDescription(`${i.user} abriu ${vc}. Todos na call podem assistir. Só a staff pode compartilhar a tela, uma pessoa por vez.`)
        .addFields({ name: 'Privacidade', value: 'Só membros presentes nesta call podem entrar. A transmissão não é gravada.' })
        .setFooter({ text: 'A sala termina quando a call esvaziar' })
        .setTimestamp();
      const row = new ActionRowBuilder().addComponents(
        new ButtonBuilder().setCustomId(`join:${vc.id}`).setLabel('Abrir transmissão').setStyle(ButtonStyle.Primary),
      );
      return i.reply({ embeds: [embed], components: [row] });
    }

    // 2) clique no botão -> confere se está na call e entrega um link pessoal
    if (i.isButton() && i.customId.startsWith('join:')) {
      const ch = i.customId.slice(5);
      if (i.member.voice.channelId !== ch) {
        return i.reply({ content: 'Só quem está nesta call pode entrar. Entre na call e clique de novo.', flags: EPHEMERAL });
      }
      const code = crypto.randomUUID();
      pending.set(code, {
        uid: i.user.id,
        name: i.member.displayName,
        ch,
        chName: i.guild.channels.cache.get(ch)?.name || 'call',
        guildId: i.guildId,
        exp: Date.now() + 10 * 60_000,
      });
      const link = new ButtonBuilder().setStyle(ButtonStyle.Link).setLabel('Entrar na sala').setURL(`${BASE_URL}/sala?c=${code}`);
      return i.reply({
        content: 'Seu acesso está pronto. O link é pessoal e vale por 10 minutos.',
        components: [new ActionRowBuilder().addComponents(link)],
        flags: EPHEMERAL,
      });
    }
  } catch (err) {
    console.error('Erro na interação:', err);
  }
});

// Saiu da call -> sai da sala. Call vazia -> encerra a sala.
client.on(Events.VoiceStateUpdate, async (oldS, newS) => {
  if (!oldS.channelId || oldS.channelId === newS.channelId) return;
  const room = oldS.channelId;
  if (sharers.get(room)?.uid === oldS.id) sharers.delete(room); // devolve a vez
  try { await rooms.removeParticipant(room, oldS.id); } catch { /* não estava na sala */ }
  const humans = oldS.channel?.members.filter((m) => !m.user.bot).size ?? 0;
  if (humans === 0) {
    sharers.delete(room);
    try { await rooms.deleteRoom(room); } catch { /* sala já não existe */ }
  }
});

// ---------- Web ----------
const app = express();
app.disable('x-powered-by');
app.get('/health', (_req, res) => res.send('ok')); // use este endereço no monitor de uptime
app.get('/livekit-client.js', (_req, res) => res.sendFile(require.resolve('livekit-client'), { maxAge: '1d' }));
app.get('/sala', (_req, res) => res.sendFile(path.join(__dirname, 'public', 'sala.html')));

app.get('/api/join', async (req, res) => {
  try {
    const p = pending.get(String(req.query.c || ''));
    if (!p || p.exp < Date.now()) {
      return res.status(401).json({ error: 'Esse link expirou. Volte ao Discord e clique em "Abrir transmissão" de novo.' });
    }
    // Confere de novo, agora, se a pessoa ainda está na call.
    const state = client.guilds.cache.get(p.guildId)?.voiceStates.cache.get(p.uid);
    if (state?.channelId !== p.ch) {
      return res.status(403).json({ error: 'Você precisa estar na call do Discord para entrar na sala.' });
    }
    const staff = await isStaff(p.guildId, p.uid);

    // Todo mundo entra podendo só câmera e microfone. A tela é liberada sob demanda (/api/tela/pedir).
    const at = new AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET, { identity: p.uid, name: p.name, ttl: '4h' });
    at.addGrant({
      roomJoin: true, room: p.ch, canSubscribe: true,
      canPublish: true, canPublishSources: [SRC_CAMERA, SRC_MIC], // precisa ser número, não texto
    });

    const session = crypto.randomUUID();
    sessions.set(session, { uid: p.uid, ch: p.ch, guildId: p.guildId, exp: Date.now() + 4 * 3600_000 });

    res.json({ url: LIVEKIT_URL, token: await at.toJwt(), channel: p.chName, staff, session });
  } catch (err) {
    console.error('Erro em /api/join:', err);
    res.status(500).json({ error: 'Erro interno: ' + (err && err.message ? err.message : String(err)) });
  }
});

// Pede a vez de compartilhar a tela: só staff, só se ninguém estiver transmitindo.
app.post('/api/tela/pedir', async (req, res) => {
  try {
    const s = sessions.get(String(req.query.s || ''));
    if (!s || s.exp < Date.now()) return res.status(401).json({ error: 'Sessão expirada. Abra a sala de novo pelo Discord.' });

    const state = client.guilds.cache.get(s.guildId)?.voiceStates.cache.get(s.uid);
    if (state?.channelId !== s.ch) return res.status(403).json({ error: 'Você precisa estar na call do Discord.' });
    if (!(await isStaff(s.guildId, s.uid))) return res.status(403).json({ error: 'Só a staff pode compartilhar a tela.' });

    if (sharers.has(s.ch) && sharers.get(s.ch).uid !== s.uid) await limpaVezSeVazia(s.ch);
    const atual = sharers.get(s.ch);
    if (atual && atual.uid !== s.uid) {
      return res.status(409).json({ error: 'Já tem uma tela sendo compartilhada. Espere a pessoa parar.' });
    }
    // Sem "await" entre a checagem acima e o set abaixo, então dois pedidos não passam juntos.
    sharers.set(s.ch, { uid: s.uid, since: Date.now() });
    try {
      await setTela(s.ch, s.uid, true);
    } catch (err) {
      sharers.delete(s.ch);
      console.error('Erro ao liberar tela:', err);
      return res.status(500).json({ error: 'Não foi possível liberar a tela. Tente de novo.' });
    }
    res.json({ ok: true });
  } catch (err) {
    console.error('Erro em /api/tela/pedir:', err);
    res.status(500).json({ error: 'Erro interno. Tente de novo em instantes.' });
  }
});

// Devolve a vez (ao parar de compartilhar).
app.post('/api/tela/parar', async (req, res) => {
  try {
    const s = sessions.get(String(req.query.s || ''));
    if (!s) return res.json({ ok: true });
    if (sharers.get(s.ch)?.uid === s.uid) {
      sharers.delete(s.ch);
      try { await setTela(s.ch, s.uid, false); } catch { /* já saiu da sala */ }
    }
    res.json({ ok: true });
  } catch (err) {
    console.error('Erro em /api/tela/parar:', err);
    res.json({ ok: true });
  }
});

process.on('unhandledRejection', (e) => console.error('unhandledRejection:', e));
app.listen(PORT, () => console.log(`Servidor web na porta ${PORT}`));
client.login(DISCORD_TOKEN);
