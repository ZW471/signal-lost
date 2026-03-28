/* ================================================================
   SIGNAL LOST — Browser GUI Application

   Particle system, glitch effects, WebSocket game communication,
   typing animations, and panel rendering (matched to TUI).
   ================================================================ */

// ================================================================
// CONSTANTS — matched to TUI tui_viewer.py
// ================================================================

const ITEM_ICONS = {
  data_chip: '\u{1F4BE}', keycard: '\u{1F511}', disguise: '\u{1F3AD}',
  signal_artifact: '\u2726', evidence: '\u{1F4CE}', tool: '\u{1F527}',
  consumable: '\u{1F48A}',
};

const FACTION_COLORS = {
  nexus: 'red', listener: 'cyan', listeners: 'cyan',
  purist: 'yellow', purists: 'yellow', corporate: 'yellow',
  underground: 'green', independent: '', unknown: '', unaffiliated: '',
};

const TRUST_COLORS = {
  hostile: 'red', suspicious: 'orange', neutral: 'yellow',
  cautious_ally: 'cyan', trusted: 'green', devoted: 'green',
};

const TAG_COLORS = {
  movement: 'cyan', dialogue: 'yellow', discovery: 'green',
  danger: 'red', signal: 'magenta', system: '', trade: 'yellow',
};

const TIME_ICONS = {
  morning: '\u{1F305}', afternoon: '\u2600\uFE0F', evening: '\u{1F307}', night: '\u{1F319}',
};

const IMPLANT_COLORS = {
  active: 'green', overloaded: 'red', resonating: 'magenta', damaged: 'yellow',
};

// ================================================================
// i18n — LABELS & DATA TRANSLATION (matched to TUI LABELS dict)
// ================================================================

let currentLang = 'en'; // Set from settings

const LABELS = {
  en: {
    // Tabs
    tab_identity: 'ID', tab_knowledge: 'KNOW', tab_traces: 'TRACE',
    tab_district: 'LOC', tab_inventory: 'INV', tab_network: 'NPC',
    tab_world: 'WORLD', tab_log: 'LOG', tab_conversation: 'CONV',
    // Identity
    identity: 'IDENTITY', name: 'Name', alias: 'Alias', background: 'Background',
    status: 'STATUS', integrity: 'Integrity', credits: 'Credits',
    neural_implant: 'Neural Implant', disguise: 'Disguise', turn: 'Turn', time: 'Time',
    status_effects: 'STATUS EFFECTS', none: 'None',
    // Knowledge
    facts: 'FACTS', rumors: 'RUMORS', evidence: 'EVIDENCE',
    theories: 'THEORIES', connections: 'CONNECTIONS', none_discovered: 'None discovered',
    // Traces
    traces_of_truth: 'TRACES OF TRUTH', discovered: 'Discovered',
    no_traces: 'No traces discovered yet. Investigate the world to uncover the truth.',
    // District
    current_location: 'CURRENT LOCATION', district: 'District', area: 'Area',
    signal_strength: 'Signal', danger_level: 'Danger', nexus_patrol: 'NEXUS Patrol',
    description: 'DESCRIPTION', exits: 'EXITS', poi: 'POINTS OF INTEREST',
    npcs_present: 'NPCs PRESENT',
    // Inventory
    inventory: 'INVENTORY', slots: 'Slots', items: 'ITEMS', empty_slot: '(empty)',
    // Network
    npc_tracker: 'NPC TRACKER', faction: 'Faction', trust: 'Trust',
    last_seen: 'Last seen', quest: 'Quest', no_npcs: 'No NPCs encountered',
    // World
    nexus_alert: 'NEXUS ALERT', fragment_decay: 'FRAGMENT DECAY',
    district_access: 'DISTRICT ACCESS', global_events: 'GLOBAL EVENTS',
    world_nominal: 'World state nominal. No alerts.',
    period: 'Period', day: 'Day',
    alert_calm: 'CALM', alert_watchful: 'WATCHFUL', alert_alert: 'ALERT',
    alert_manhunt: 'MANHUNT', alert_lockdown: 'LOCKDOWN',
    decay_stable: 'STABLE', decay_fading: 'FADING',
    decay_critical: 'CRITICAL', decay_terminal: 'TERMINAL',
    // Log
    session_log: 'SESSION LOG', no_log: 'No log entries',
    // Conversation
    conversation_history: 'CONVERSATION HISTORY', no_conversation: 'No conversation yet',
    player_label: 'PLAYER', agent_label: 'AGENT',
    // Status bar
    location: 'LOCATION',
    // Chat
    chat_placeholder: 'What do you do?', processing: 'PROCESSING NEURAL INPUT',
    // Danger
    safe: 'Safe', low: 'Low', moderate: 'Moderate', high: 'High', extreme: 'Extreme',
  },
  zh: {
    tab_identity: '身份', tab_knowledge: '知识', tab_traces: '痕迹',
    tab_district: '区域', tab_inventory: '物品', tab_network: '人脉',
    tab_world: '世界', tab_log: '日志', tab_conversation: '对话',
    identity: '身份', name: '姓名', alias: '化名', background: '背景',
    status: '状态', integrity: '完整性', credits: '信用点',
    neural_implant: '神经植入体', disguise: '伪装', turn: '回合', time: '时间',
    status_effects: '状态效果', none: '无',
    facts: '事实', rumors: '传闻', evidence: '证据',
    theories: '推论', connections: '关联', none_discovered: '尚未发现',
    traces_of_truth: '真相痕迹', discovered: '已发现',
    no_traces: '尚未发现任何痕迹。探索世界以揭示真相。',
    current_location: '当前位置', district: '区域', area: '地点',
    signal_strength: '信号', danger_level: '危险', nexus_patrol: '连结巡逻',
    description: '描述', exits: '出口', poi: '兴趣点',
    npcs_present: '在场角色',
    inventory: '物品栏', slots: '槽位', items: '物品', empty_slot: '(空)',
    npc_tracker: '角色追踪', faction: '阵营', trust: '信任',
    last_seen: '上次出现', quest: '任务', no_npcs: '尚无已接触角色',
    nexus_alert: '连结警报', fragment_decay: '碎片衰变',
    district_access: '区域通行', global_events: '全局事件',
    world_nominal: '世界状态正常，无警报。',
    period: '时段', day: '日',
    alert_calm: '平静', alert_watchful: '警觉', alert_alert: '戒备',
    alert_manhunt: '追捕', alert_lockdown: '戒严',
    decay_stable: '稳定', decay_fading: '消散',
    decay_critical: '危机', decay_terminal: '终末',
    session_log: '事件日志', no_log: '无日志条目',
    conversation_history: '对话记录', no_conversation: '尚无对话',
    player_label: '玩家', agent_label: '引擎',
    location: '位置',
    chat_placeholder: '你想做什么？', processing: '正在处理神经输入',
    safe: '安全', low: '低', moderate: '中', high: '高', extreme: '极端',
  },
};

// Data-level translation maps (TUI _BG_ZH, _IMPLANT_ZH, etc.)
const DATA_ZH = {
  background: {
    'netrunner': '网行者', 'street_runner': '街头行者', 'street runner': '街头行者',
    'corporate_exile': '企业流亡者', 'corporate exile': '企业流亡者',
  },
  implant: {
    'active': '激活', 'overloaded': '过载', 'dormant': '休眠',
    'resonating': '共鸣', 'damaged': '损坏',
  },
  effect_name: {
    'signal sensitivity': '信号敏感', 'neural fatigue': '神经疲劳',
    'paranoia': '偏执', 'disorientation': '迷失方向',
    'echo memory': '回声记忆', 'fragment resonance': '碎片共鸣',
  },
  intensity: {
    'faint': '微弱', 'mild': '轻微', 'moderate': '中等',
    'strong': '强烈', 'overwhelming': '压倒性',
  },
  time: {
    'morning': '晨', 'afternoon': '午', 'evening': '夕', 'night': '夜',
  },
  trust_level: {
    'hostile': '敌对', 'suspicious': '怀疑', 'neutral': '中立',
    'cautious_ally': '谨慎盟友', 'trusted': '信任', 'devoted': '忠诚',
  },
  danger: {
    'safe': '安全', 'low': '低', 'moderate': '中', 'high': '高', 'extreme': '极端',
  },
  tag: {
    'movement': '移动', 'dialogue': '对话', 'discovery': '发现',
    'danger': '危险', 'signal': '信号', 'system': '系统', 'trade': '交易',
  },
  district_status: {
    'open': '开放', 'locked': '锁定', 'restricted': '限制',
  },
};

/** Get a label by key, fallback to English then to key itself */
function L(key) {
  return (LABELS[currentLang] && LABELS[currentLang][key]) || LABELS.en[key] || key;
}

/** Translate a data-level value. category is a key into DATA_ZH. */
function localizeData(category, value) {
  if (!value) return '';
  if (currentLang !== 'zh') return String(value);
  const map = DATA_ZH[category];
  if (!map) return String(value);
  return map[String(value).toLowerCase()] || String(value);
}

/** Set the UI language and refresh everything */
function setLanguage(lang) {
  currentLang = lang;
  // Update tab labels
  const tabKeys = ['identity','knowledge','traces','district','inventory','network','world','log','conversation'];
  const tabs = document.querySelectorAll('.panel-tab');
  tabs.forEach((tab, i) => {
    if (tabKeys[i]) tab.textContent = L('tab_' + tabKeys[i]);
  });
  // Update chat placeholder
  const chatInput = document.getElementById('chatInput');
  if (chatInput) chatInput.placeholder = L('chat_placeholder');
  // Update thinking text
  const thinkingText = document.querySelector('.thinking-text');
  if (thinkingText) thinkingText.textContent = L('processing');
  // Re-render all panels if we have cached session
  if (cachedSession) updateAllPanels(cachedSession);
}

let cachedSession = null; // Store last session for re-render on language change

// ================================================================
// PARTICLE SYSTEM
// ================================================================

const canvas = document.getElementById('particles');
const ctx = canvas.getContext('2d');
let particles = [];
let mouseX = 0, mouseY = 0;

function resizeCanvas() {
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
}

window.addEventListener('resize', resizeCanvas);
resizeCanvas();

class Particle {
  constructor() { this.reset(); }
  reset() {
    this.x = Math.random() * canvas.width;
    this.y = Math.random() * canvas.height;
    this.size = Math.random() * 2 + 0.5;
    this.speedX = (Math.random() - 0.5) * 0.5;
    this.speedY = Math.random() * 0.3 + 0.1;
    this.opacity = Math.random() * 0.5 + 0.1;
    this.color = Math.random() > 0.7 ? '#ff00ff' : '#00fff5';
    this.pulse = Math.random() * Math.PI * 2;
    this.pulseSpeed = Math.random() * 0.02 + 0.01;
  }
  update() {
    this.x += this.speedX; this.y += this.speedY; this.pulse += this.pulseSpeed;
    const dx = this.x - mouseX, dy = this.y - mouseY;
    const dist = Math.sqrt(dx * dx + dy * dy);
    if (dist < 100) { this.x += dx / dist * 2; this.y += dy / dist * 2; }
    if (this.y > canvas.height) this.y = 0;
    if (this.x < 0) this.x = canvas.width;
    if (this.x > canvas.width) this.x = 0;
  }
  draw() {
    const alpha = this.opacity * (0.5 + 0.5 * Math.sin(this.pulse));
    ctx.beginPath(); ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
    ctx.fillStyle = this.color; ctx.globalAlpha = alpha; ctx.fill();
    ctx.beginPath(); ctx.arc(this.x, this.y, this.size * 3, 0, Math.PI * 2);
    ctx.globalAlpha = alpha * 0.1; ctx.fill(); ctx.globalAlpha = 1;
  }
}

for (let i = 0; i < 120; i++) particles.push(new Particle());

function drawConnections() {
  for (let i = 0; i < particles.length; i++) {
    for (let j = i + 1; j < particles.length; j++) {
      const dx = particles[i].x - particles[j].x, dy = particles[i].y - particles[j].y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist < 120) {
        ctx.beginPath(); ctx.moveTo(particles[i].x, particles[i].y);
        ctx.lineTo(particles[j].x, particles[j].y);
        ctx.strokeStyle = '#00fff5'; ctx.globalAlpha = (1 - dist / 120) * 0.08;
        ctx.lineWidth = 0.5; ctx.stroke(); ctx.globalAlpha = 1;
      }
    }
  }
}

function animateParticles() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  particles.forEach(p => { p.update(); p.draw(); });
  drawConnections();
  requestAnimationFrame(animateParticles);
}
animateParticles();
document.addEventListener('mousemove', e => { mouseX = e.clientX; mouseY = e.clientY; });

// ================================================================
// GLITCH & AUDIO
// ================================================================

function triggerGlitch() {
  const o = document.getElementById('glitchOverlay');
  o.classList.remove('active'); void o.offsetWidth; o.classList.add('active');
  setTimeout(() => o.classList.remove('active'), 200);
}
setInterval(() => { if (Math.random() < 0.15) triggerGlitch(); }, 5000);

const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
function playBeep(freq = 880, duration = 0.05, volume = 0.03) {
  try {
    const osc = audioCtx.createOscillator(), gain = audioCtx.createGain();
    osc.type = 'square'; osc.frequency.value = freq;
    gain.gain.value = volume;
    gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + duration);
    osc.connect(gain); gain.connect(audioCtx.destination);
    osc.start(); osc.stop(audioCtx.currentTime + duration);
  } catch (e) {}
}

// ================================================================
// NOTIFICATION & SCREEN MANAGEMENT
// ================================================================

function notify(text, isError = false) {
  const el = document.getElementById('notification');
  el.textContent = text;
  el.className = 'notification show' + (isError ? ' error' : '');
  clearTimeout(el._timer);
  el._timer = setTimeout(() => el.className = 'notification', 3000);
}

function switchScreen(id) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  const t = document.getElementById(id);
  if (t) { t.classList.add('active'); triggerGlitch(); playBeep(1200, 0.04); }
}

// ================================================================
// BOOT SEQUENCE
// ================================================================

const bootMessages = [
  '[SYS] Initializing neural interface...',
  '[SYS] Loading kernel modules: mem_cortex, sig_proc, net_bridge',
  '[NET] Scanning local frequencies... 3 signals detected',
  '[SEC] NEXUS monitoring layer: ACTIVE',
  '[MEM] Memory fragments: 0 recovered',
  '[SYS] Checking implant firmware: v3.7.1 — NOMINAL',
  '[NET] Connecting to mesh network... ESTABLISHED',
  '[SIG] Signal trace protocol initialized',
  '[SYS] Loading world state from last checkpoint...',
  '[SEC] Encryption layer: AES-4096 QUANTUM-RESISTANT',
  '[SYS] Neural bridge calibration: 98.7%',
  '[OK ] System ready. Awaiting operator input.',
];

async function runBootSequence() {
  const log = document.getElementById('bootLog'), bar = document.getElementById('bootProgressBar');
  for (let i = 0; i < bootMessages.length; i++) {
    const line = document.createElement('div');
    line.className = 'line'; line.textContent = bootMessages[i];
    log.appendChild(line); log.scrollTop = log.scrollHeight;
    bar.style.width = ((i + 1) / bootMessages.length * 100) + '%';
    playBeep(600 + i * 50, 0.03, 0.02);
    await sleep(200 + Math.random() * 300);
  }
  await sleep(500);
  switchScreen('menuScreen');
  connectWebSocket();
}
function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

// ================================================================
// WEBSOCKET
// ================================================================

let ws = null, wsReconnectTimer = null;

function connectWebSocket() {
  const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
  ws = new WebSocket(`${protocol}://${location.host}/ws`);
  ws.onopen = () => { ws.send(JSON.stringify({ action: 'init' })); };
  ws.onmessage = (event) => handleServerMessage(JSON.parse(event.data));
  ws.onclose = () => {
    if (!wsReconnectTimer) wsReconnectTimer = setTimeout(() => { wsReconnectTimer = null; connectWebSocket(); }, 3000);
  };
  ws.onerror = () => {};
}

function sendWS(data) {
  if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(data));
  else notify('Connection lost. Reconnecting...', true);
}

// ================================================================
// STATE
// ================================================================

let cachedSaves = [];
let selectedBackground = 'street_runner';
let isFirstInput = true; // Track if first input after resume (to remove system message)
let resumeMessageEl = null; // Reference to the resume system message element

// ================================================================
// SERVER MESSAGE HANDLER
// ================================================================

function handleServerMessage(msg) {
  switch (msg.type) {
    case 'status':
      if (msg.has_session) document.getElementById('btnResume').style.display = '';
      if (msg.saves && msg.saves.length > 0) {
        document.getElementById('btnLoadGame').style.display = '';
        cachedSaves = msg.saves;
      }
      if (msg.provider) prefillProviderSettings(msg.provider);
      // Read language from settings
      if (msg.settings && msg.settings.language) {
        const lang = msg.settings.language.display || msg.settings.language.tui || 'en';
        document.getElementById('selectUiLanguage').value = lang;
        setLanguage(lang);
      }
      break;

    case 'game_started':
      switchScreen('gameScreen');
      if (msg.session) updateAllPanels(msg.session);
      enableInput();
      break;

    case 'thinking':
      showThinking();
      break;

    case 'narrative':
      hideThinking();
      const role = msg.role || 'agent';
      if (role === 'system') {
        // Resume message — will be removed after first player input
        resumeMessageEl = addTypingMessage(msg.text, role);
        isFirstInput = true;
      } else {
        addTypingMessage(msg.text, role);
      }
      break;

    case 'session_update':
      if (msg.session) updateAllPanels(msg.session);
      break;

    case 'game_over':
      setTimeout(() => showGameOver(msg.ending, msg.narrative), 2000);
      break;

    case 'saved':
      notify(`Saved: ${msg.save_name}`);
      closeSaveDialog();
      break;

    case 'provider_saved':
      notify(currentLang === 'zh' ? '设置已保存' : 'Settings saved');
      if (msg.provider) prefillProviderSettings(msg.provider);
      document.getElementById('settingsStatus').textContent = currentLang === 'zh' ? '已保存' : 'Saved';
      setTimeout(() => { document.getElementById('settingsStatus').textContent = ''; }, 2000);
      break;

    case 'error':
      hideThinking(); enableInput();
      notify(msg.message, true);
      addChatMessage(msg.message, 'system');
      break;
  }
}

// ================================================================
// SETTINGS (persistent provider config)
// ================================================================

function prefillProviderSettings(p) {
  if (p.provider) document.getElementById('selectProvider').value = p.provider;
  if (p.model) document.getElementById('inputModel').value = p.model;
  if (p.temperature != null) {
    document.getElementById('inputTemp').value = p.temperature;
    document.getElementById('tempValue').textContent = p.temperature;
  }
  if (p.base_url) document.getElementById('inputBaseUrl').value = p.base_url;
  onProviderChange();
}

function openSettings() {
  document.getElementById('settingsOverlay').style.display = 'flex';
  document.getElementById('settingsStatus').textContent = '';
  playBeep(1000, 0.04);
}

function closeSettings() {
  document.getElementById('settingsOverlay').style.display = 'none';
}

function saveSettings() {
  const lang = document.getElementById('selectUiLanguage').value;
  sendWS({ action: 'save_provider', provider: getProviderConfig(), language: lang });
  setLanguage(lang);
  document.getElementById('settingsStatus').textContent = currentLang === 'zh' ? '保存中...' : 'Saving...';
}

function onProviderChange() {
  const p = document.getElementById('selectProvider').value;
  document.getElementById('apiKeyGroup').style.display = p === 'lmstudio' ? 'none' : '';
  document.getElementById('baseUrlGroup').style.display = p === 'lmstudio' ? '' : 'none';
}

document.getElementById('inputTemp').addEventListener('input', function() {
  document.getElementById('tempValue').textContent = this.value;
});

function getProviderConfig() {
  const provider = document.getElementById('selectProvider').value;
  const config = { provider, model: document.getElementById('inputModel').value || 'gpt-4o',
    temperature: parseFloat(document.getElementById('inputTemp').value) };
  if (provider === 'lmstudio') config.base_url = document.getElementById('inputBaseUrl').value;
  else { const k = document.getElementById('inputApiKey').value; if (k) config.api_key = k; }
  return config;
}

// ================================================================
// MENU & GAME LAUNCH
// ================================================================

function showMenu() {
  // If in game, ask for confirmation first
  if (document.getElementById('gameScreen').classList.contains('active')) {
    requestReturnToMenu();
    return;
  }
  switchScreen('menuScreen');
}

function requestReturnToMenu() {
  const d = document.getElementById('confirmMenuDialog');
  document.getElementById('confirmMenuTitle').textContent = currentLang === 'zh' ? '// 返回主菜单？' : '// RETURN TO MENU?';
  document.getElementById('confirmMenuText').textContent = currentLang === 'zh' ? '未保存的进度将会丢失。' : 'Any unsaved progress will be lost.';
  document.getElementById('confirmMenuYes').textContent = currentLang === 'zh' ? '确认' : 'CONFIRM';
  document.getElementById('confirmMenuNo').textContent = currentLang === 'zh' ? '取消' : 'CANCEL';
  d.style.display = 'flex';
  playBeep(600, 0.04);
}

function confirmReturnToMenu() {
  document.getElementById('confirmMenuDialog').style.display = 'none';
  switchScreen('menuScreen');
}

function closeConfirmMenu() {
  document.getElementById('confirmMenuDialog').style.display = 'none';
}
function showNewGame() { switchScreen('newGameScreen'); playBeep(1000, 0.04); }

function showLoadGame() {
  const list = document.getElementById('savesList');
  list.innerHTML = '';
  if (cachedSaves.length === 0) {
    list.innerHTML = '<div class="panel-empty">No saved games found.</div>';
  } else {
    cachedSaves.forEach(save => {
      const el = document.createElement('div');
      el.className = 'save-entry';
      el.innerHTML = `<div><div class="save-name">${esc(save.name)}</div>
        <div class="save-info">${esc(save.player_name)} — Turn ${save.turn}</div></div>
        <div style="color:var(--cyan)">⟩</div>`;
      el.onclick = () => loadGame(save.name);
      list.appendChild(el);
    });
  }
  switchScreen('loadGameScreen');
}

function selectBg(btn) {
  document.querySelectorAll('.cyber-select').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  selectedBackground = btn.dataset.bg;
  playBeep(800, 0.03);
}

function startNewGame() {
  const config = {
    name: document.getElementById('inputName').value || 'Unknown',
    alias: document.getElementById('inputAlias').value || 'Unknown',
    background: selectedBackground,
    difficulty: document.getElementById('selectDifficulty').value,
    language: document.getElementById('selectLanguage').value,
  };
  clearChat(); isFirstInput = true; resumeMessageEl = null;
  sendWS({ action: 'new_game', config, provider: getProviderConfig() });
  switchScreen('gameScreen'); showThinking(); disableInput();
}

function resumeGame() {
  clearChat(); isFirstInput = true; resumeMessageEl = null;
  sendWS({ action: 'resume', provider: getProviderConfig() });
  switchScreen('gameScreen'); showThinking(); disableInput();
}

function loadGame(saveName) {
  clearChat(); isFirstInput = true; resumeMessageEl = null;
  sendWS({ action: 'load_game', save_name: saveName, provider: getProviderConfig() });
  switchScreen('gameScreen'); showThinking(); disableInput();
}

// ================================================================
// CHAT FUNCTIONS
// ================================================================

function clearChat() { document.getElementById('chatMessages').innerHTML = ''; }

function addChatMessage(text, role = 'agent') {
  const container = document.getElementById('chatMessages');
  const msg = document.createElement('div');
  msg.className = `chat-msg ${role}`;
  const prefixes = { player: '\u25B6 PLAYER', agent: '\u25C0 SIGNAL LOST', system: '\u25CF SYSTEM' };
  msg.innerHTML = `<div class="msg-prefix">${prefixes[role] || role.toUpperCase()}</div>
    <div class="msg-content">${esc(text)}</div>`;
  container.appendChild(msg);
  container.scrollTop = container.scrollHeight;
  playBeep(role === 'player' ? 1200 : 800, 0.03);
  return msg;
}

function addTypingMessage(text, role = 'agent') {
  const container = document.getElementById('chatMessages');
  const msg = document.createElement('div');
  msg.className = `chat-msg ${role}`;
  const prefixes = { player: '\u25B6 PLAYER', agent: '\u25C0 SIGNAL LOST', system: '\u25CF SYSTEM' };
  const contentEl = document.createElement('div');
  contentEl.className = 'msg-content typing';
  msg.innerHTML = `<div class="msg-prefix">${prefixes[role] || role.toUpperCase()}</div>`;
  msg.appendChild(contentEl);
  container.appendChild(msg);

  let i = 0; const speed = 8, interval = 20;
  function typeNext() {
    if (i < text.length) {
      contentEl.textContent += text.slice(i, i + speed);
      i += speed; container.scrollTop = container.scrollHeight;
      if (Math.random() < 0.05) playBeep(600 + Math.random() * 400, 0.02, 0.01);
      setTimeout(typeNext, interval);
    } else { contentEl.classList.remove('typing'); enableInput(); }
  }
  typeNext();
  return msg;
}

function sendMessage() {
  const input = document.getElementById('chatInput');
  const text = input.value.trim();
  if (!text) return;

  // Remove resume system message on first player input
  if (isFirstInput && resumeMessageEl) {
    resumeMessageEl.classList.add('fade-out');
    setTimeout(() => { if (resumeMessageEl && resumeMessageEl.parentNode) resumeMessageEl.parentNode.removeChild(resumeMessageEl); resumeMessageEl = null; }, 500);
    isFirstInput = false;
  }

  addChatMessage(text, 'player');
  input.value = '';
  disableInput();
  sendWS({ action: 'player_input', text });
}

function showThinking() {
  document.getElementById('thinkingIndicator').style.display = 'flex';
  document.getElementById('chatMessages').scrollTop = document.getElementById('chatMessages').scrollHeight;
}
function hideThinking() { document.getElementById('thinkingIndicator').style.display = 'none'; }
function enableInput() { const i = document.getElementById('chatInput'); i.disabled = false; i.focus(); }
function disableInput() { document.getElementById('chatInput').disabled = true; }

// ================================================================
// SAVE / LOAD
// ================================================================

function saveGame() { document.getElementById('saveDialog').style.display = 'flex'; document.getElementById('saveName').focus(); playBeep(1000, 0.04); }
function confirmSave() { sendWS({ action: 'save_game', save_name: document.getElementById('saveName').value.trim() || 'quicksave' }); }
function closeSaveDialog() { document.getElementById('saveDialog').style.display = 'none'; }

function showGameOver(ending, narrative) {
  triggerGlitch(); triggerGlitch();
  document.getElementById('gameOverEnding').textContent = ending ? `// ${ending.toUpperCase()}` : '// CONNECTION TERMINATED';
  document.getElementById('gameOverNarrative').textContent = narrative || '';
  document.getElementById('gameOverOverlay').style.display = 'flex';
  playBeep(200, 0.3, 0.05);
}

// ================================================================
// RESIZE HANDLE
// ================================================================

(function initResize() {
  const handle = document.getElementById('resizeHandle');
  const layout = document.getElementById('gameLayout');
  const chatPanel = document.getElementById('chatPanel');
  const infoPanel = document.getElementById('infoPanels');
  let isResizing = false;

  handle.addEventListener('mousedown', (e) => {
    isResizing = true;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
    e.preventDefault();
  });

  document.addEventListener('mousemove', (e) => {
    if (!isResizing) return;
    const layoutRect = layout.getBoundingClientRect();
    const pct = ((e.clientX - layoutRect.left) / layoutRect.width) * 100;
    const clamped = Math.max(25, Math.min(80, pct));
    chatPanel.style.flex = 'none';
    chatPanel.style.width = clamped + '%';
    infoPanel.style.flex = 'none';
    infoPanel.style.width = (100 - clamped) + '%';
  });

  document.addEventListener('mouseup', () => {
    if (isResizing) { isResizing = false; document.body.style.cursor = ''; document.body.style.userSelect = ''; }
  });
})();

// ================================================================
// PANEL RENDERING — matched to TUI tui_viewer.py
// ================================================================

function switchPanel(btn) {
  document.querySelectorAll('.panel-tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  btn.classList.add('active');
  document.getElementById('panel-' + btn.dataset.panel).classList.add('active');
  playBeep(900, 0.02);
}

function updateAllPanels(session) {
  cachedSession = session;
  updateStatusBar(session);
  updateIdentityPanel(session.player);
  updateKnowledgePanel(session.knowledge);
  updateTracesPanel(session.traces);
  updateDistrictPanel(session.location);
  updateInventoryPanel(session.inventory);
  updateNetworkPanel(session.npcs);
  updateWorldPanel(session.world_state);
  updateLogPanel(session.log);
  updateConversationPanel(session.conversation);
}

// ---------- STATUS BAR (matches TUI StatusBar) ----------

function updateStatusBar(session) {
  const p = session.player || {};
  const l = session.location || {};
  const integrity = p.integrity || {};

  // Alias
  setText('statAlias', p.alias || p.name || '—');

  // Integrity pips: filled █ and empty ░
  const cur = integrity.current || 0, max = integrity.max || 3;
  let pips = '';
  for (let i = 0; i < max; i++) {
    pips += i < cur ? '<span class="pip filled">\u2588</span>' : '<span class="pip empty">\u2591</span>';
  }
  document.getElementById('statIntegrityPips').innerHTML = pips;

  // Location
  setText('statLocation', l.district || l.area || '—');

  // Time with icon + translation
  const timeRaw = p.time || 'Morning';
  const timeStr = timeRaw.toLowerCase();
  const timeIcon = TIME_ICONS[timeStr] || '';
  const timeDisplay = localizeData('time', timeRaw);
  setText('statTime', `${timeIcon} ${timeDisplay}`);

  // Translate status bar labels
  setText('statLabelAlias', L('alias').toUpperCase());
  setText('statLabelIntegrity', L('integrity').toUpperCase());
  setText('statLabelLocation', L('location').toUpperCase());
  setText('statLabelTime', L('time').toUpperCase());
}

function countDiscoveredTraces(traces) {
  if (!traces) return 0;
  // Flat structure: { discovered: [...] }
  if (Array.isArray(traces.discovered)) return traces.discovered.length;
  const m = (traces.total_discovered || '0').toString().match(/(\d+)/);
  return m ? parseInt(m[0]) : 0;
}

// ---------- IDENTITY PANEL (matches TUI IdentityPanel) ----------

function updateIdentityPanel(player) {
  const p = player || {};
  const integrity = p.integrity || {};
  const cur = integrity.current || 0, max = integrity.max || 3;

  let pips = '';
  for (let i = 0; i < max; i++) {
    pips += i < cur ? '<span class="pip filled">\u2588</span>' : '<span class="pip empty">\u2591</span>';
  }

  const implantStatus = (p.neural_implant || 'Active').toLowerCase();
  const implantColor = IMPLANT_COLORS[implantStatus] || 'green';
  const implantDisplay = localizeData('implant', p.neural_implant);

  const timeStr = (p.time || '').toLowerCase();
  const timeIcon = TIME_ICONS[timeStr] || '';
  const timeDisplay = localizeData('time', p.time);
  const bgDisplay = localizeData('background', p.background);
  const disguiseVal = p.current_disguise || L('none');
  const disguiseIsNone = !p.current_disguise || p.current_disguise === 'None';

  let html = `
    <div class="panel-section">
      <div class="panel-section-title">${L('identity')}</div>
      <div class="panel-row"><span class="panel-key">${L('name')}</span><span class="panel-val cyan">${esc(p.name)}</span></div>
      <div class="panel-row"><span class="panel-key">${L('alias')}</span><span class="panel-val magenta">${esc(p.alias)}</span></div>
      <div class="panel-row"><span class="panel-key">${L('background')}</span><span class="panel-val">${esc(bgDisplay)}</span></div>
    </div>
    <div class="panel-section">
      <div class="panel-section-title">${L('status')}</div>
      <div class="panel-row"><span class="panel-key">${L('integrity')}</span><span class="panel-val">${pips}</span></div>
      <div class="panel-row"><span class="panel-key">${L('credits')}</span><span class="panel-val yellow">\u00A4 ${p.credits || 0}</span></div>
      <div class="panel-row"><span class="panel-key">${L('neural_implant')}</span><span class="panel-val ${implantColor}">${esc(implantDisplay)}</span></div>
      <div class="panel-row"><span class="panel-key">${L('disguise')}</span><span class="panel-val${disguiseIsNone ? ' dim' : ''}">${esc(disguiseIsNone ? L('none') : disguiseVal)}</span></div>
      <div class="panel-row"><span class="panel-key">${L('turn')}</span><span class="panel-val">${p.turn || 1}</span></div>
      <div class="panel-row"><span class="panel-key">${L('time')}</span><span class="panel-val">${timeIcon} ${esc(timeDisplay)}</span></div>
    </div>`;

  if (p.status_effects && p.status_effects.length > 0) {
    html += `<div class="panel-section"><div class="panel-section-title">${L('status_effects')}</div>
      ${p.status_effects.map(e => {
        let label;
        if (typeof e === 'string') {
          label = e;
        } else {
          const n = localizeData('effect_name', e.name || 'Unknown');
          const i = localizeData('intensity', e.intensity || '');
          label = `${n} — ${i}`;
        }
        return `<div class="panel-list-item" style="color:var(--yellow)">\u2022 ${esc(label)}</div>`;
      }).join('')}
    </div>`;
  }
  document.getElementById('panel-identity').innerHTML = html;
}

// ---------- KNOWLEDGE PANEL (matches TUI KnowledgePanel) ----------

function updateKnowledgePanel(knowledge) {
  const k = knowledge || {};
  let html = '';

  const sections = [
    { key: 'facts',   lkey: 'facts',       color: 'green',   prefix: '\u2713' },
    { key: 'rumors',  lkey: 'rumors',      color: 'yellow',  prefix: '?' },
    { key: 'evidence',lkey: 'evidence',    color: 'cyan',    prefix: '\u{1F4CE}' },
    { key: 'theories',lkey: 'theories',    color: 'magenta', prefix: '\u{1F4A1}' },
    { key: 'connections', lkey: 'connections', color: '', prefix: '\u{1F517}' },
  ];

  for (const sec of sections) {
    const items = k[sec.key] || [];
    html += `<div class="panel-section"><div class="panel-section-title">${L(sec.lkey)} (${items.length})</div>`;
    if (items.length === 0) {
      html += `<div class="panel-empty">${L('none_discovered')}</div>`;
    } else {
      for (const item of items) {
        const desc = typeof item === 'string' ? item : (item.description || item.text || JSON.stringify(item));
        const id = item.id ? `<span class="dim">[${item.id}]</span> ` : '';
        const source = item.source ? `<span class="dim"> — ${esc(item.source)}</span>` : '';
        // Rumor status prefix
        let pfx = sec.prefix;
        if (sec.key === 'rumors' && item.status) {
          pfx = item.status === 'confirmed' ? '\u2713' : (item.status === 'debunked' ? '\u2717' : '?');
        }
        html += `<div class="panel-list-item" style="color:var(--${sec.color || 'text'})">${pfx} ${id}${esc(desc)}${source}</div>`;
      }
    }
    html += `</div>`;
  }
  document.getElementById('panel-knowledge').innerHTML = html;
}

// ---------- TRACES PANEL (matches TUI TracesPanel — ONLY discovered) ----------

function updateTracesPanel(traces) {
  const t = traces || {};
  // Data is flat: { discovered: [{id, description, turn}, ...] }
  const discovered = t.discovered || [];

  let html = `<div class="panel-section">
    <div class="panel-section-title">${L('traces_of_truth')}</div>
    <div class="panel-row"><span class="panel-key">${L('discovered')}</span><span class="panel-val cyan">${discovered.length}</span></div>
  </div>`;

  if (discovered.length === 0) {
    html += `<div class="panel-empty">${L('no_traces')}</div>`;
  } else {
    html += `<div class="panel-section">`;
    for (const trace of discovered) {
      html += `<div class="trace-item discovered">
        <span class="dim" style="font-size:11px">${esc(trace.id)}</span>
        ${esc(trace.description)}
        ${trace.turn ? `<span class="dim"> (Turn ${trace.turn})</span>` : ''}
      </div>`;
    }
    html += `</div>`;
  }
  document.getElementById('panel-traces').innerHTML = html;
}

// ---------- DISTRICT PANEL (matches TUI DistrictPanel — no zone) ----------

function updateDistrictPanel(location) {
  const l = location || {};
  const dangerCls = dangerColor(l.danger_level);

  // Signal waveform
  const sigStr = parseInt(l.signal_strength) || 0;
  const sigBars = Math.round(sigStr / 10);
  let sigWave = '';
  for (let i = 0; i < 10; i++) sigWave += i < sigBars ? '\u2248' : '\u00B7';

  // NEXUS patrol color
  const patrolStr = (l.nexus_patrol || 'None').toLowerCase();
  const patrolColor = patrolStr === 'none' ? 'green' : (patrolStr.includes('light') ? 'yellow' : 'red');

  const dangerDisplay = localizeData('danger', l.danger_level);

  let html = `
    <div class="panel-section">
      <div class="panel-section-title">${L('current_location')}</div>
      <div class="panel-row"><span class="panel-key">${L('district')}</span><span class="panel-val ${dangerCls}">${esc(l.district)}</span></div>
      <div class="panel-row"><span class="panel-key">${L('area')}</span><span class="panel-val">${esc(l.area)}</span></div>
      <div class="panel-row"><span class="panel-key">${L('signal_strength')}</span><span class="panel-val magenta">${sigWave} ${esc(l.signal_strength)}</span></div>
      <div class="panel-row"><span class="panel-key">${L('danger_level')}</span><span class="panel-val ${dangerCls}">${esc(dangerDisplay)}</span></div>
      <div class="panel-row"><span class="panel-key">${L('nexus_patrol')}</span><span class="panel-val ${patrolColor}">${esc(l.nexus_patrol)}</span></div>
    </div>`;

  if (l.description) {
    html += `<div class="panel-section"><div class="panel-section-title">${L('description')}</div>
      <div class="panel-description">${esc(l.description)}</div></div>`;
  }

  if (l.exits) {
    html += `<div class="panel-section"><div class="panel-section-title">${L('exits')}</div>`;
    for (const [dir, desc] of Object.entries(l.exits)) {
      html += `<div class="panel-list-item">\u25B8 <span class="cyan" style="text-transform:uppercase">${esc(dir)}</span> — ${esc(desc)}</div>`;
    }
    html += `</div>`;
  }

  if (l.points_of_interest && l.points_of_interest.length > 0) {
    html += `<div class="panel-section"><div class="panel-section-title">${L('poi')}</div>`;
    for (const poi of l.points_of_interest) {
      html += `<div class="panel-list-item">\u2726 ${esc(poi)}</div>`;
    }
    html += `</div>`;
  }

  if (l.npcs_present && l.npcs_present.length > 0) {
    html += `<div class="panel-section"><div class="panel-section-title">${L('npcs_present')}</div>`;
    for (const npc of l.npcs_present) {
      html += `<div class="panel-list-item" style="color:var(--yellow)">\u25C8 ${esc(npc)}</div>`;
    }
    html += `</div>`;
  }
  document.getElementById('panel-district').innerHTML = html;
}

// ---------- INVENTORY PANEL (matches TUI InventoryPanel — 6 slots, icons) ----------

function updateInventoryPanel(inventory) {
  const inv = inventory || {};
  const slots = inv.slots || {};
  const items = inv.items || [];
  const maxSlots = slots.max || 6;
  const usedSlots = slots.used || items.length;

  let html = `
    <div class="panel-section">
      <div class="panel-section-title">${L('inventory')}</div>
      <div class="panel-row"><span class="panel-key">${L('credits')}</span><span class="panel-val yellow">\u00A4 ${inv.credits || 0}</span></div>
      <div class="panel-row"><span class="panel-key">${L('slots')}</span><span class="panel-val">${usedSlots} / ${maxSlots}</span></div>
    </div>
    <div class="panel-section"><div class="panel-section-title">${L('items')}</div>`;

  // Render all 6 slots
  for (let s = 1; s <= maxSlots; s++) {
    const item = items.find(i => i.slot === s);
    if (item) {
      const icon = ITEM_ICONS[(item.type || '').toLowerCase()] || '\u25A0';
      html += `<div class="inv-slot filled">
        <div class="inv-slot-header">${icon} <span class="cyan">[${s}] ${esc(item.item)}</span></div>
        <div class="inv-slot-type dim">${esc(item.type || '')}</div>
        <div class="inv-slot-desc">${esc(item.description || '')}</div>
      </div>`;
    } else {
      html += `<div class="inv-slot empty"><span class="dim">[${s}] ${L('empty_slot')}</span></div>`;
    }
  }
  html += `</div>`;
  document.getElementById('panel-inventory').innerHTML = html;
}

// ---------- NETWORK PANEL (matches TUI NetworkPanel — faction colors, trust bar) ----------

function updateNetworkPanel(npcs) {
  const n = npcs || {};
  const npcList = n.npcs || [];

  let html = `<div class="panel-section"><div class="panel-section-title">${L('npc_tracker')} (${npcList.length})</div>`;

  if (npcList.length === 0) {
    html += `<div class="panel-empty">${L('no_npcs')}</div>`;
  } else {
    for (const npc of npcList) {
      const trustLevel = extractEnglishKey(npc.trust_level || npc.trust || '').toLowerCase();
      const trustCls = TRUST_COLORS[trustLevel] || '';
      const factionKey = extractEnglishKey(npc.faction || '').toLowerCase();
      const factionCls = FACTION_COLORS[factionKey] || '';
      const trustDisplay = localizeData('trust_level', trustLevel);

      const trustValues = { hostile: 1, suspicious: 3, neutral: 5, cautious_ally: 7, trusted: 9, devoted: 11 };
      const trustVal = trustValues[trustLevel] || 5;
      let trustBar = '';
      for (let i = 0; i < 12; i++) {
        trustBar += i < trustVal ? '\u2588' : '\u2591';
      }

      html += `<div class="panel-list-item npc-entry">
        <div>\u25C8 <span class="cyan" style="font-weight:bold">${esc(npc.name || npc.id || 'Unknown')}</span></div>
        ${npc.faction ? `<div class="dim">${L('faction')}: <span class="${factionCls}">${esc(npc.faction)}</span></div>` : ''}
        <div>${L('trust')}: <span class="${trustCls}">${trustBar} ${esc(trustDisplay)}</span></div>
        ${npc.location_last_seen ? `<div class="dim">${L('last_seen')}: ${esc(npc.location_last_seen)}</div>` : ''}
        ${npc.quest_status && npc.quest_status !== 'none' ? `<div class="dim">${L('quest')}: ${esc(Array.isArray(npc.quest_status) ? npc.quest_status.join(', ') : npc.quest_status)}</div>` : ''}
        ${npc.notes ? `<div class="dim">${esc(npc.notes)}</div>` : ''}
      </div>`;
    }
  }
  html += `</div>`;
  document.getElementById('panel-network').innerHTML = html;
}

function extractEnglishKey(val) {
  if (!val) return '';
  const s = String(val);
  // Handle bilingual: "中立（Neutral）" or "Listeners / 听众"
  let m = s.match(/[（(]([A-Za-z_]+)[)）]/);
  if (m) return m[1];
  m = s.match(/([A-Za-z_]+)\s*[/／]/);
  if (m) return m[1].trim();
  m = s.match(/[/／]\s*([A-Za-z_]+)/);
  if (m) return m[1].trim();
  return s;
}

// ---------- WORLD PANEL (matches TUI WorldPanel — conditional alert/decay) ----------

function updateWorldPanel(worldState) {
  const w = worldState || {};
  const alert = w.nexus_alert || {};
  const decay = w.fragment_decay || {};
  const time = w.time || {};

  let html = '';

  // NEXUS Alert — only shown if > 0 (matches TUI)
  const alertVal = alert.current || 0;
  if (alertVal > 0) {
    const alertPct = Math.min(alertVal, 10) * 10;
    const alertStatusDisplay = localizeAlertStatus(alert.status);
    html += `<div class="panel-section"><div class="panel-section-title">${L('nexus_alert')}</div>
      <div class="panel-row"><span class="panel-key">${L('status')}</span>
        <span class="panel-val ${alertColor(alert.status)}">${esc(alertStatusDisplay)}</span></div>
      <div class="progress-bar"><div class="progress-fill alert-gradient" style="width:${alertPct}%"></div></div>
      <div class="dim" style="font-size:11px;text-align:right">${alertVal}%</div>
    </div>`;
  }

  // Fragment Decay — only shown if > 0 (matches TUI)
  const decayVal = decay.current || 0;
  if (decayVal > 0) {
    const decayPct = Math.min(decayVal, 10) * 10;
    const decayStatusDisplay = localizeDecayStatus(decay.status);
    html += `<div class="panel-section"><div class="panel-section-title">${L('fragment_decay')}</div>
      <div class="panel-row"><span class="panel-key">${L('status')}</span>
        <span class="panel-val">${esc(decayStatusDisplay)}</span></div>
      <div class="progress-bar"><div class="progress-fill decay-gradient" style="width:${decayPct}%"></div></div>
      <div class="dim" style="font-size:11px;text-align:right">${decayVal}%</div>
    </div>`;
  }

  // District access
  const districts = w.district_access || [];
  if (districts.length > 0) {
    html += `<div class="panel-section"><div class="panel-section-title">${L('district_access')}</div>`;
    for (const d of districts) {
      const icon = d.status === 'Open' ? '\u25C6' : (d.status === 'Restricted' ? '\u25D4' : '\u25CB');
      const statusColor = d.status === 'Open' ? 'green' : (d.status === 'Restricted' ? 'yellow' : 'red');
      const dName = currentLang === 'zh' && d.name_zh ? d.name_zh : d.name;
      const statusDisplay = localizeData('district_status', d.status);
      html += `<div class="panel-list-item"><div class="panel-row">
        <span>${icon} <span class="cyan">${esc(dName)}</span></span>
        <span class="panel-val ${statusColor}">${esc(statusDisplay)}</span>
      </div></div>`;
    }
    html += `</div>`;
  }

  // Period
  const period = time.period || '';
  if (period) {
    const tIcon = TIME_ICONS[period.toLowerCase()] || '';
    const periodDisplay = localizeData('time', period);
    html += `<div class="panel-section"><div class="panel-section-title">${L('time')}</div>
      <div class="panel-row"><span class="panel-key">${L('day')}</span><span class="panel-val">${time.day || 1}</span></div>
      <div class="panel-row"><span class="panel-key">${L('period')}</span><span class="panel-val">${tIcon} ${esc(periodDisplay)}</span></div>
    </div>`;
  }

  // Global events
  const events = w.global_events || [];
  if (events.length > 0) {
    html += `<div class="panel-section"><div class="panel-section-title">${L('global_events')}</div>`;
    for (const evt of events) {
      const evtText = typeof evt === 'string' ? evt : (evt.description || JSON.stringify(evt));
      html += `<div class="panel-list-item" style="color:var(--yellow)">\u25B8 ${esc(evtText)}</div>`;
    }
    html += `</div>`;
  }

  if (!html) html = `<div class="panel-empty">${L('world_nominal')}</div>`;
  document.getElementById('panel-world').innerHTML = html;
}

// ---------- LOG PANEL (matches TUI LogPanel — tags, expandable, reverse order) ----------

function updateLogPanel(log) {
  const l = log || {};
  const entries = l.entries || [];

  let html = `<div class="panel-section"><div class="panel-section-title">${L('session_log')} (${entries.length})</div>`;

  if (entries.length === 0) {
    html += `<div class="panel-empty">${L('no_log')}</div>`;
  } else {
    for (let i = entries.length - 1; i >= 0; i--) {
      const entry = entries[i];
      const tag = (entry.tag || (entry.signal ? 'signal' : 'system')).toLowerCase();
      const tagColor = TAG_COLORS[tag] || '';
      const tagLabel = localizeData('tag', tag).toUpperCase();

      html += `<div class="log-entry ${entry.signal ? 'signal' : ''} expandable" onclick="this.classList.toggle('expanded')">
        <div class="log-entry-header">
          <span class="log-tag ${tagColor}">[${esc(tagLabel.trim())}]</span>
          <span class="dim">T${entry.turn || '?'}</span>
          <span class="log-entry-title">${esc(entry.title || '')}</span>
          <span class="log-expand-icon">\u25B6</span>
        </div>
        <div class="log-entry-body">
          <div class="log-entry-desc">${esc(entry.text || entry.description || '')}</div>
        </div>
      </div>`;
    }
  }
  html += `</div>`;
  document.getElementById('panel-log').innerHTML = html;
}

// ---------- CONVERSATION PANEL (matches TUI ConversationPanel) ----------

function updateConversationPanel(conversation) {
  const conv = conversation || [];
  let html = `<div class="panel-section"><div class="panel-section-title">${L('conversation_history')} (${conv.length})</div>`;

  if (conv.length === 0) {
    html += `<div class="panel-empty">${L('no_conversation')}</div>`;
  } else {
    for (const entry of conv) {
      const isPlayer = entry.role === 'user' || entry.role === 'human';
      const roleLabel = isPlayer ? `\u25B6 ${L('player_label')}` : `\u25C0 ${L('agent_label')}`;
      const roleCls = isPlayer ? 'magenta' : 'cyan';
      html += `<div class="conv-entry">
        <div class="conv-header"><span class="dim">T${entry.turn || '?'}</span> <span class="${roleCls}">${roleLabel}</span></div>
        <div class="conv-content">${esc(entry.content || '')}</div>
      </div>`;
    }
  }
  html += `</div>`;
  document.getElementById('panel-conversation').innerHTML = html;
}

// ================================================================
// UTILITY FUNCTIONS
// ================================================================

function localizeAlertStatus(status) {
  const key = 'alert_' + (status || 'calm').toLowerCase();
  return L(key) || status || '';
}
function localizeDecayStatus(status) {
  const key = 'decay_' + (status || 'stable').toLowerCase();
  return L(key) || status || '';
}

function setText(id, text) { const el = document.getElementById(id); if (el) el.textContent = text || ''; }
function esc(text) { return escapeHtml(text || ''); }
function escapeHtml(text) { if (!text) return ''; const d = document.createElement('div'); d.textContent = String(text); return d.innerHTML; }

function dangerColor(level) {
  const l = (level || '').toLowerCase();
  if (l === 'safe') return 'green';
  if (l === 'low') return 'yellow';
  if (l === 'medium' || l === 'moderate') return 'orange';
  if (l === 'high') return 'red';
  if (l === 'critical' || l === 'extreme') return 'alert-critical';
  return 'cyan';
}

function alertColor(status) {
  const s = (status || '').toLowerCase();
  if (s === 'calm') return 'alert-calm';
  if (s === 'watchful' || s === 'low') return 'alert-low';
  if (s === 'alert' || s === 'medium' || s === 'elevated') return 'alert-medium';
  if (s === 'manhunt' || s === 'high') return 'alert-high';
  if (s === 'lockdown' || s === 'critical') return 'alert-critical';
  return '';
}

// ================================================================
// KEYBOARD SHORTCUTS
// ================================================================

document.addEventListener('keydown', (e) => {
  if (document.getElementById('gameScreen').classList.contains('active')) {
    const isInput = document.activeElement === document.getElementById('chatInput');
    const num = parseInt(e.key);
    if (num >= 1 && num <= 9 && !e.ctrlKey && !e.metaKey && !isInput) {
      const tabs = document.querySelectorAll('.panel-tab');
      if (tabs[num - 1]) { switchPanel(tabs[num - 1]); e.preventDefault(); }
    }
    if (e.key === 't' && !isInput) { document.getElementById('chatInput').focus(); e.preventDefault(); }
    if (e.key === 's' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); saveGame(); }
    if (e.key === 'Escape') { closeSaveDialog(); closeSettings(); closeConfirmMenu(); }
  }
});

// ================================================================
// STARTUP
// ================================================================

window.addEventListener('load', () => { runBootSequence(); });
