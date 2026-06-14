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
  '晨': '\u{1F305}', '午': '\u2600\uFE0F', '夕': '\u{1F307}', '夜': '\u{1F319}',
};

const IMPLANT_COLORS = {
  active: 'green', overloaded: 'red', resonating: 'magenta', damaged: 'yellow',
  '激活': 'green', '过载': 'red', '共鸣': 'magenta', '损坏': 'yellow',
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
    // Search
    search_placeholder: 'Search…', no_search_results: 'No matches',
    // Status bar
    location: 'LOCATION',
    // Chat
    chat_placeholder: 'What do you do?', processing: 'PROCESSING NEURAL INPUT',
    thinking_hint: '// link resolving — review your INTEL panels while you wait',
    thinking_lines: [
      'PARSING NEURAL INPUT…',
      'CROSS-REFERENCING THE GRID…',
      'ROUTING THROUGH DEAD CHANNELS…',
      'THE CITY LISTENS…',
      'DECRYPTING SIGNAL FRAGMENTS…',
      'COMPILING RESPONSE…',
      'STILL TRACING — DEEP LINK…',
    ],
    // Danger
    safe: 'Safe', low: 'Low', moderate: 'Moderate', high: 'High', extreme: 'Extreme',
    // Menu & UI
    game_title: 'SIGNAL LOST',
    menu_new_game: 'NEW GAME', menu_resume: 'RESUME',
    menu_load_game: 'LOAD GAME', menu_settings: 'SETTINGS',
    menu_footer: 'NEXUS MONITORING ACTIVE',
    // New game screen
    config_title: '// IDENTITY CONFIGURATION',
    label_designation: 'DESIGNATION', label_alias: 'ALIAS', label_background: 'BACKGROUND',
    label_difficulty: 'DIFFICULTY', label_language: 'LANGUAGE',
    placeholder_name: 'Enter name...', placeholder_alias: 'Enter alias...',
    bg_street_runner: 'Street Runner', bg_corporate_exile: 'Corporate Exile', bg_netrunner: 'Netrunner',
    diff_paranoid: 'Easy', diff_cautious: 'Medium',
    diff_standard: 'Hard', diff_reckless: 'Very Hard',
    diff_paranoid_desc: 'More forgiving, extra integrity',
    diff_cautious_desc: 'Balanced experience',
    diff_standard_desc: 'The intended challenge',
    diff_reckless_desc: 'One mistake can be fatal',
    btn_initialize: 'INITIALIZE', btn_back: 'BACK',
    // Load game screen
    load_title: '// LOAD SAVED SESSION',
    resume_title: '// RESUME SESSION',
    no_saves: 'No saved games found.',
    // Save dialog
    save_title: '// SAVE SESSION', label_save_name: 'SAVE NAME',
    btn_save: 'SAVE', btn_cancel: 'CANCEL',
    // Confirm menu dialog
    confirm_menu_title: '// RETURN TO MENU?',
    confirm_menu_text: 'Any unsaved progress will be lost.',
    btn_confirm: 'CONFIRM',
    // Settings
    settings_title: '// SETTINGS', label_ui_language: 'UI LANGUAGE',
    settings_provider_title: '// LLM PROVIDER',
    label_provider: 'PROVIDER', label_model: 'MODEL',
    label_api_key: 'API KEY', label_base_url: 'BASE URL', label_temperature: 'TEMPERATURE',
    settings_langsmith_title: '// LANGSMITH TRACING',
    label_langsmith_key: 'API KEY', label_langsmith_project: 'PROJECT NAME',
    settings_usage_title: '// USAGE TRACKING', label_show_tokens: 'Show token usage in conversation',
    settings_audio_title: '// AUDIO', label_music_volume: 'MUSIC VOLUME',
    settings_gameplay_title: '// GAMEPLAY',
    label_suggested_actions: 'Suggest actions each turn',
    label_predict_outcome: 'Pre-compute suggested actions (instant replies, extra LLM calls)',
    btn_close: 'CLOSE',
    settings_saved: 'Settings saved', saving: 'Saving...', saved: 'Saved',
    // Chat prefixes
    chat_player: '\u25B6 PLAYER', chat_agent: '\u25C0 SIGNAL LOST', chat_system: '\u25CF SYSTEM',
    // Game over
    game_over_reconnect: 'RECONNECT', game_over_fallback: '// CONNECTION TERMINATED',
    // Connection
    connection_lost: 'Connection lost. Reconnecting...',
    // Tutorial
    tutorial_step: 'STEP', tutorial_skip: 'SKIP', tutorial_next: 'NEXT', tutorial_finish: 'GOT IT',
    // Companion (implant side-channel Q&A)
    companion_title: 'NEURAL LINK',
    companion_tagline: '// private channel · changes nothing',
    companion_placeholder: 'Ask, or think out loud…',
    companion_open: 'Neural Link — ask the implant',
    companion_close: 'Close',
    companion_you: '▶ YOU',
    companion_implant: '◈ IMPLANT',
    companion_thinking: 'listening…',
    companion_intro: 'A quiet channel opens behind your left ear. Ask what you like, or just think out loud — this stays in your head. Nothing said here touches the world.',
    companion_error: 'Static. The link drops for a moment — try again.',
    companion_no_session: 'The implant has nothing to hold onto yet. Begin a session first.',
    // Boot
    boot_sub: '// NEURAL INTERFACE v3.7.1',
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
    search_placeholder: '搜索…', no_search_results: '无匹配项',
    location: '位置',
    chat_placeholder: '你想做什么？', processing: '正在处理神经输入',
    thinking_hint: '// 链路解析中 —— 可在等待时查看右侧情报面板',
    thinking_lines: [
      '解析神经输入…',
      '比对城市网格…',
      '穿行废弃信道…',
      '城市正在倾听…',
      '解密信号碎片…',
      '编译回应…',
      '深度追踪中…',
    ],
    safe: '安全', low: '低', moderate: '中', high: '高', extreme: '极端',
    // Menu & UI
    game_title: '信号遗失',
    menu_new_game: '新游戏', menu_resume: '继续',
    menu_load_game: '载入存档', menu_settings: '设置',
    menu_footer: 'NEXUS监控已激活',
    // New game screen
    config_title: '// 身份配置',
    label_designation: '姓名', label_alias: '化名', label_background: '背景',
    label_difficulty: '难度', label_language: '语言',
    placeholder_name: '输入姓名...', placeholder_alias: '输入化名...',
    bg_street_runner: '街头行者', bg_corporate_exile: '企业流亡者', bg_netrunner: '网行者',
    diff_paranoid: '简单', diff_cautious: '中等',
    diff_standard: '困难', diff_reckless: '极难',
    diff_paranoid_desc: '更宽容，额外完整性',
    diff_cautious_desc: '均衡体验',
    diff_standard_desc: '预期的挑战',
    diff_reckless_desc: '一步失误即可致命',
    btn_initialize: '初始化', btn_back: '返回',
    // Load game screen
    load_title: '// 载入存档',
    resume_title: '// 继续游戏',
    no_saves: '未找到存档。',
    // Save dialog
    save_title: '// 保存游戏', label_save_name: '存档名称',
    btn_save: '保存', btn_cancel: '取消',
    // Confirm menu dialog
    confirm_menu_title: '// 返回主菜单？',
    confirm_menu_text: '未保存的进度将会丢失。',
    btn_confirm: '确认',
    // Settings
    settings_title: '// 设置', label_ui_language: '界面语言',
    settings_provider_title: '// 语言模型',
    label_provider: '提供商', label_model: '模型',
    label_api_key: 'API密钥', label_base_url: '地址', label_temperature: '温度',
    settings_langsmith_title: '// LangSmith 记录',
    label_langsmith_key: 'API密钥', label_langsmith_project: '项目名称',
    settings_usage_title: '// 用量追踪', label_show_tokens: '在对话中显示令牌用量',
    settings_audio_title: '// 音频', label_music_volume: '音乐音量',
    settings_gameplay_title: '// 玩法',
    label_suggested_actions: '每回合推荐行动',
    label_predict_outcome: '预计算推荐行动（点击即时响应，但会增加 LLM 调用）',
    btn_close: '关闭',
    settings_saved: '设置已保存', saving: '保存中...', saved: '已保存',
    // Chat prefixes
    chat_player: '\u25B6 玩家', chat_agent: '\u25C0 信号遗失', chat_system: '\u25CF 系统',
    // Game over
    game_over_reconnect: '重新连接', game_over_fallback: '// 连接已终止',
    // Connection
    connection_lost: '连接已断开，正在重连...',
    // Tutorial
    tutorial_step: '步骤', tutorial_skip: '跳过', tutorial_next: '下一步', tutorial_finish: '知道了',
    // Companion (implant side-channel Q&A)
    companion_title: '神经链接',
    companion_tagline: '// 私密信道 · 不影响世界',
    companion_placeholder: '提问，或自言自语…',
    companion_open: '神经链接 —— 询问植入体',
    companion_close: '关闭',
    companion_you: '▶ 你',
    companion_implant: '◈ 植入体',
    companion_thinking: '聆听中…',
    companion_intro: '左耳后方，一道安静的信道接通了。想问什么都行，或只是自言自语——这只停留在你的脑海里，不会影响外面的世界。',
    companion_error: '一阵杂讯，链接短暂中断——再试一次。',
    companion_no_session: '植入体还没有可依凭的记忆，请先开始一局游戏。',
    // Boot
    boot_sub: '// 神经接口 v3.7.1',
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

const DIRECTION_ZH = {
  north: '北', south: '南', east: '东', west: '西',
  northeast: '东北', northwest: '西北', southeast: '东南', southwest: '西南',
  up: '上', down: '下',
};

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
  localStorage.setItem('signal_lost_ui_lang', lang);
  const menuLangSel = document.getElementById('selectMenuLanguage');
  if (menuLangSel) menuLangSel.value = lang;
  // Update tab labels
  const tabKeys = ['identity','knowledge','traces','district','inventory','network','world','log','conversation'];
  const tabs = document.querySelectorAll('.panel-tab');
  tabs.forEach((tab, i) => {
    if (tabKeys[i]) tab.textContent = L('tab_' + tabKeys[i]);
  });
  // Chat
  const chatInput = document.getElementById('chatInput');
  if (chatInput) chatInput.placeholder = L('chat_placeholder');
  // Implant companion chrome
  applyCompanionLanguage();
  // Panel search inputs
  ['knowledge', 'traces', 'log', 'conversation'].forEach(k => {
    const si = document.getElementById('search-' + k);
    if (si) si.placeholder = L('search_placeholder');
  });
  const thinkingText = document.querySelector('.thinking-text');
  // If the wait ticker is mid-cycle, re-render its current line in the new
  // language; otherwise fall back to the resting label.
  if (thinkingText) thinkingText.textContent = (_thinkingTimer || _thinkingLineIdx > 0) ? _thinkingLineText() : L('processing');
  const thinkingHint = document.getElementById('thinkingHint');
  if (thinkingHint) thinkingHint.textContent = L('thinking_hint');

  // Game title (boot logo, menu h1, game over h1)
  const title = L('game_title');
  const bootLogo = document.querySelector('.logo-glitch');
  if (bootLogo) { bootLogo.textContent = title; bootLogo.dataset.text = title; }
  const menuTitle = document.querySelector('#menuScreen .glitch-text');
  if (menuTitle) { menuTitle.textContent = title; menuTitle.dataset.text = title; }
  const gameOverTitle = document.querySelector('.game-over-title');
  if (gameOverTitle) { gameOverTitle.textContent = title; gameOverTitle.dataset.text = title; }
  document.title = title;

  // Boot subtitle
  const bootSub = document.querySelector('.logo-sub');
  if (bootSub) bootSub.textContent = L('boot_sub');

  // Menu screen
  setText('btnNewGame', L('menu_new_game'), '.cyber-btn-text');
  setText('btnLoadGame', L('menu_load_game'), '.cyber-btn-text');
  setText('btnSettings', L('menu_settings'), '.cyber-btn-text');
  const menuFooter = document.querySelector('.menu-footer');
  if (menuFooter) menuFooter.innerHTML = '<span class="blink">_</span> ' + L('menu_footer');

  // New game screen
  const configTitle = document.querySelector('#newGameScreen .config-title');
  if (configTitle) configTitle.textContent = L('config_title');
  // Labels
  _setLabelsInForm('#newGameScreen', [
    ['DESIGNATION', 'label_designation'], ['ALIAS', 'label_alias'],
    ['BACKGROUND', 'label_background'], ['DIFFICULTY', 'label_difficulty'],
    ['LANGUAGE', 'label_language'],
  ]);
  // Default values + placeholders for new game form
  const inputName = document.getElementById('inputName');
  if (inputName) {
    inputName.placeholder = L('placeholder_name');
    // Update default value if user hasn't customized it
    const defaults = { en: 'Kael', zh: '凯尔' };
    const oldDefaults = Object.values(defaults);
    if (!inputName.value || oldDefaults.includes(inputName.value)) {
      inputName.value = defaults[lang] || defaults.en;
    }
  }
  const inputAlias = document.getElementById('inputAlias');
  if (inputAlias) {
    inputAlias.placeholder = L('placeholder_alias');
    const defaults = { en: 'Ghost', zh: '幽灵' };
    const oldDefaults = Object.values(defaults);
    if (!inputAlias.value || oldDefaults.includes(inputAlias.value)) {
      inputAlias.value = defaults[lang] || defaults.en;
    }
  }
  // Sync session language selector with UI language
  const selectLang = document.getElementById('selectLanguage');
  if (selectLang) selectLang.value = lang;
  // Background select buttons
  document.querySelectorAll('.cyber-select').forEach(btn => {
    const bg = btn.dataset.bg;
    const nameEl = btn.querySelector('.select-name');
    const descEl = btn.querySelector('.select-desc');
    if (bg && nameEl && descEl) {
      if (lang === 'zh') {
        nameEl.textContent = L('bg_' + bg);
        descEl.textContent = '';
      } else {
        const bgNames = { street_runner: 'Street Runner', corporate_exile: 'Corporate Exile', netrunner: 'Netrunner' };
        const bgZh = { street_runner: '街头行者', corporate_exile: '企业流亡者', netrunner: '网行者' };
        nameEl.textContent = bgNames[bg] || bg;
        descEl.textContent = bgZh[bg] || '';
      }
    }
  });
  // Difficulty options
  const diffSelect = document.getElementById('selectDifficulty');
  if (diffSelect) {
    const diffs = ['paranoid', 'cautious', 'standard', 'reckless'];
    Array.from(diffSelect.options).forEach((opt, i) => {
      if (diffs[i]) opt.textContent = L('diff_' + diffs[i]) + ' — ' + L('diff_' + diffs[i] + '_desc');
    });
  }
  // Initialize / Back buttons
  _setBtnText('#newGameScreen', 0, L('btn_initialize'));
  _setBtnText('#newGameScreen', 1, L('btn_back'));

  // Load game screen
  const loadTitle = document.querySelector('#loadGameScreen .config-title');
  if (loadTitle) loadTitle.textContent = L('load_title');
  _setBtnText('#loadGameScreen', 0, L('btn_back'));

  // Save dialog
  const saveTitle = document.querySelector('#saveDialog .config-title');
  if (saveTitle) saveTitle.textContent = L('save_title');
  const saveLabel = document.querySelector('#saveDialog .cyber-label');
  if (saveLabel) saveLabel.textContent = L('label_save_name');
  const saveBtns = document.querySelectorAll('#saveDialog .cyber-btn-text');
  if (saveBtns[0]) saveBtns[0].textContent = L('btn_save');
  if (saveBtns[1]) saveBtns[1].textContent = L('btn_cancel');

  // Confirm menu dialog
  document.getElementById('confirmMenuTitle').textContent = L('confirm_menu_title');
  document.getElementById('confirmMenuText').textContent = L('confirm_menu_text');
  document.getElementById('confirmMenuYes').textContent = L('btn_confirm');
  document.getElementById('confirmMenuNo').textContent = L('btn_cancel');

  // Settings overlay
  const settingsTitle = document.querySelector('#settingsOverlay .config-title');
  if (settingsTitle) settingsTitle.textContent = L('settings_title');
  _setLabelsInOverlay('#settingsOverlay', [
    [0, 'label_provider'], [1, 'label_model'],
    [2, 'label_api_key'], [3, 'label_base_url'], [4, 'label_temperature'],
    [5, 'label_langsmith_key'], [6, 'label_langsmith_project'],
    [8, 'label_music_volume'],
  ]);
  const subtitles = document.querySelectorAll('#settingsOverlay .config-subtitle');
  if (subtitles[0]) subtitles[0].textContent = L('settings_provider_title');
  if (subtitles[1]) subtitles[1].textContent = L('settings_langsmith_title');
  if (subtitles[2]) subtitles[2].textContent = L('settings_usage_title');
  if (subtitles[3]) subtitles[3].textContent = L('settings_audio_title');
  if (subtitles[4]) subtitles[4].textContent = L('settings_gameplay_title');
  // Localize checkbox label (preserve the <input> inside)
  const chkLabel = document.querySelector('#chkShowTokens');
  if (chkLabel && chkLabel.parentNode) {
    const lbl = chkLabel.parentNode;
    // Keep checkbox, replace text
    lbl.childNodes.forEach(n => { if (n.nodeType === 3) n.textContent = ' ' + L('label_show_tokens'); });
  }
  // Gameplay feature toggle labels (translated by id, not index)
  const lblSA = document.getElementById('lblSuggestedActions');
  if (lblSA) lblSA.textContent = L('label_suggested_actions');
  const lblPO = document.getElementById('lblPredictOutcome');
  if (lblPO) lblPO.textContent = L('label_predict_outcome');
  const settingsBtns = document.querySelectorAll('#settingsOverlay .cyber-btn-text');
  if (settingsBtns[0]) settingsBtns[0].textContent = L('btn_save');
  if (settingsBtns[1]) settingsBtns[1].textContent = L('btn_close');

  // Game over
  const reconnectBtn = document.querySelector('#gameOverOverlay .cyber-btn-text');
  if (reconnectBtn) reconnectBtn.textContent = L('game_over_reconnect');

  // Status bar: info-panel toggle tooltip + the consolidated nav menu labels.
  const isZhUI = lang === 'zh';
  const infoBtn = document.getElementById('btnInfoPanels');
  if (infoBtn) infoBtn.title = isZhUI ? '信息面板' : 'Info Panels';
  const navBtn = document.getElementById('btnNavMenu');
  if (navBtn) navBtn.title = isZhUI ? '菜单' : 'Menu';
  const navLabels = isZhUI
    ? { navItemTutorial: '教程', navItemSave: '保存游戏', navItemSettings: '设置', navItemMenu: '主菜单' }
    : { navItemTutorial: 'Tutorial', navItemSave: 'Save Game', navItemSettings: 'Settings', navItemMenu: 'Main Menu' };
  Object.entries(navLabels).forEach(([id, label]) => { const el = document.getElementById(id); if (el) el.textContent = label; });

  // Re-render all panels if we have cached session
  if (cachedSession) updateAllPanels(cachedSession);
}

/** Helper: set text inside a button's .cyber-btn-text by parent+index */
function _setBtnText(containerSel, idx, text) {
  const btns = document.querySelectorAll(containerSel + ' .form-actions .cyber-btn-text');
  if (btns[idx]) btns[idx].textContent = text;
}

/** Helper: set cyber-label text by index within a container */
function _setLabelsInForm(containerSel, pairs) {
  const labels = document.querySelectorAll(containerSel + ' .cyber-label');
  for (const [_origText, lkey] of pairs) {
    for (const lbl of labels) {
      // Match by the original English text or just set all matching ones
      if (lbl.textContent.trim().toUpperCase() === _origText || lbl.dataset.lkey === lkey) {
        lbl.textContent = L(lkey);
        lbl.dataset.lkey = lkey; // mark for future updates
      }
    }
  }
}

/** Helper: set labels by index in settings overlay */
function _setLabelsInOverlay(containerSel, indexPairs) {
  const labels = document.querySelectorAll(containerSel + ' .cyber-label');
  for (const [idx, lkey] of indexPairs) {
    if (labels[idx]) labels[idx].textContent = L(lkey);
  }
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
  // Music: play menu track on menu/boot screens, game music handled by updateAllPanels
  if (id === 'menuScreen' || id === 'bootScreen' || id === 'newGameScreen' || id === 'loadGameScreen') {
    MusicEngine.playMenu();
  }
}

// ================================================================
// BOOT SEQUENCE
// ================================================================

const BOOT_MESSAGES = {
  en: [
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
  ],
  zh: [
    '[系统] 正在初始化神经接口...',
    '[系统] 加载内核模块：mem_cortex, sig_proc, net_bridge',
    '[网络] 扫描本地频率... 检测到3个信号',
    '[安全] NEXUS监控层：已激活',
    '[记忆] 记忆碎片：已恢复0个',
    '[系统] 检查植入体固件：v3.7.1 — 正常',
    '[网络] 连接网格网络... 已建立',
    '[信号] 信号追踪协议已初始化',
    '[系统] 从上次检查点加载世界状态...',
    '[安全] 加密层：AES-4096 量子抗性',
    '[系统] 神经桥校准：98.7%',
    '[完成] 系统就绪，等待操作员输入。',
  ],
};

async function runBootSequence() {
  const log = document.getElementById('bootLog'), bar = document.getElementById('bootProgressBar');
  const msgs = BOOT_MESSAGES[currentLang] || BOOT_MESSAGES.en;
  for (let i = 0; i < msgs.length; i++) {
    const line = document.createElement('div');
    line.className = 'line'; line.textContent = msgs[i];
    log.appendChild(line); log.scrollTop = log.scrollHeight;
    bar.style.width = ((i + 1) / msgs.length * 100) + '%';
    playBeep(600 + i * 50, 0.03, 0.02);
    await sleep(200 + Math.random() * 300);
  }
  await sleep(500);
  switchScreen('menuScreen');
  connectWebSocket();
  connectCompanionWS();
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
  else notify(L('connection_lost'), true);
}

// ================================================================
// IMPLANT COMPANION — side-channel "ask the implant" Q&A
// A private inner channel to the neural implant, the in-game cousin of
// `btw`. It runs over its OWN WebSocket so it never blocks (or is blocked
// by) the main game turn. The transcript lives only here, in memory — it
// is never persisted server-side and is wiped on a new session or reload,
// and nothing asked here ever affects the world state.
// ================================================================

let companionWS = null, companionWSTimer = null;
let companionOpen = false;
let companionPending = false;       // an answer is in flight
let companionHistory = [];          // [{role:'user'|'implant', content}], in-memory only
let companionIntroShown = false;

function connectCompanionWS() {
  const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
  companionWS = new WebSocket(`${protocol}://${location.host}/ws/companion`);
  companionWS.onmessage = (event) => {
    let msg; try { msg = JSON.parse(event.data); } catch (e) { return; }
    if (msg.type === 'companion_reply') handleCompanionReply(msg);
  };
  companionWS.onclose = () => {
    if (!companionWSTimer) companionWSTimer = setTimeout(() => { companionWSTimer = null; connectCompanionWS(); }, 3000);
  };
  companionWS.onerror = () => {};
}

/** Wipe the aside transcript — called when a new session begins. */
function resetCompanion() {
  companionHistory = [];
  companionIntroShown = false;
  companionPending = false;
  const box = document.getElementById('companionMessages');
  if (box) box.innerHTML = '';
  hideCompanionThinking();
  const send = document.getElementById('companionSend');
  if (send) send.disabled = false;
  if (companionOpen) closeCompanion();
}

function toggleCompanion() { companionOpen ? closeCompanion() : openCompanion(); }

function openCompanion() {
  const panel = document.getElementById('companionPanel');
  const fab = document.getElementById('companionFab');
  if (!panel) return;
  companionOpen = true;
  panel.classList.add('open');
  panel.setAttribute('aria-hidden', 'false');
  if (fab) fab.classList.add('hidden');
  if (!companionIntroShown) {
    addCompanionMessage(L('companion_intro'), 'system');
    companionIntroShown = true;
  }
  setTimeout(() => { const i = document.getElementById('companionInput'); if (i) i.focus(); }, 60);
}

function closeCompanion() {
  const panel = document.getElementById('companionPanel');
  const fab = document.getElementById('companionFab');
  companionOpen = false;
  if (panel) { panel.classList.remove('open'); panel.setAttribute('aria-hidden', 'true'); }
  if (fab) fab.classList.remove('hidden');
}

function addCompanionMessage(text, role) {
  const box = document.getElementById('companionMessages');
  if (!box) return null;
  const prefixes = { user: L('companion_you'), implant: L('companion_implant'), system: '◈', error: '◈' };
  const el = document.createElement('div');
  el.className = `companion-msg ${role}`;
  el.innerHTML = `<div class="companion-msg-prefix">${esc(prefixes[role] || '')}</div>` +
                 `<div class="companion-msg-body">${esc(text)}</div>`;
  box.appendChild(el);
  box.scrollTop = box.scrollHeight;
  return el;
}

function showCompanionThinking() {
  const t = document.getElementById('companionThinking');
  if (t) {
    const label = t.querySelector('#companionThinkingText');
    if (label) label.textContent = L('companion_thinking');
    t.style.display = 'flex';
  }
  const box = document.getElementById('companionMessages');
  if (box) box.scrollTop = box.scrollHeight;
}

function hideCompanionThinking() {
  const t = document.getElementById('companionThinking');
  if (t) t.style.display = 'none';
}

function sendCompanionMessage() {
  const input = document.getElementById('companionInput');
  if (!input || companionPending) return;
  const text = input.value.trim();
  if (!text) return;

  // Send only PRIOR turns as context (server caps too); the new question is
  // passed separately, so slice before pushing to avoid duplicating it.
  const history = companionHistory.slice(-8);

  addCompanionMessage(text, 'user');
  companionHistory.push({ role: 'user', content: text });
  input.value = '';
  companionPending = true;
  const send = document.getElementById('companionSend');
  if (send) send.disabled = true;
  showCompanionThinking();

  if (companionWS && companionWS.readyState === WebSocket.OPEN) {
    companionWS.send(JSON.stringify({ action: 'ask', text, history }));
  } else {
    hideCompanionThinking();
    companionPending = false;
    if (send) send.disabled = false;
    addCompanionMessage(L('companion_error'), 'error');
  }
}

function handleCompanionReply(msg) {
  hideCompanionThinking();
  companionPending = false;
  const send = document.getElementById('companionSend');
  if (send) send.disabled = false;
  if (msg.error) {
    addCompanionMessage(msg.code === 'no_session' ? L('companion_no_session') : L('companion_error'), 'error');
    return;
  }
  const text = (msg.text || '').trim() || L('companion_error');
  addCompanionMessage(text, 'implant');
  companionHistory.push({ role: 'implant', content: text });
}

/** Refresh the companion's static chrome when the UI language changes. */
function applyCompanionLanguage() {
  const set = (id, prop, val) => { const el = document.getElementById(id); if (el) el[prop] = val; };
  set('companionTitle', 'textContent', L('companion_title'));
  set('companionTagline', 'textContent', L('companion_tagline'));
  set('companionThinkingText', 'textContent', L('companion_thinking'));
  const input = document.getElementById('companionInput');
  if (input) input.placeholder = L('companion_placeholder');
  const fab = document.getElementById('companionFab');
  if (fab) fab.title = L('companion_open');
  const closeBtn = document.getElementById('companionClose');
  if (closeBtn) closeBtn.title = L('companion_close');
}

// ================================================================
// STATE
// ================================================================

let cachedSaves = [];
let cachedSessions = [];
let selectedBackground = 'street_runner';
let isFirstInput = true; // Track if first input after resume (to remove system message)
let pendingTutorial = false; // Show tutorial after new game starts
let _firstSceneArmed = false; // New game in progress: hold the opening scene until the tutorial ends
let _pendingFirstScene = null; // Buffered opening 'narrative' payload, revealed on endTutorial
let resumeMessageEl = null; // Reference to the resume system message element
let discoveryEls = []; // Track discovery notification elements (ephemeral)
let _cachedFeatures = null; // Latest gameplay feature flags from the server

// ================================================================
// SERVER MESSAGE HANDLER
// ================================================================

function handleServerMessage(msg) {
  switch (msg.type) {
    case 'status':
      cachedSessions = msg.sessions || [];
      if (msg.saves && msg.saves.length > 0) {
        document.getElementById('btnLoadGame').style.display = '';
        cachedSaves = msg.saves;
      } else {
        document.getElementById('btnLoadGame').style.display = 'none';
      }
      if (msg.provider) prefillProviderSettings(msg.provider);
      if (msg.langsmith) prefillLangsmithSettings(msg.langsmith);
      if (msg.settings && msg.settings.features) _cachedFeatures = msg.settings.features;
      // Read language from settings
      if (msg.settings && msg.settings.language) {
        const lang = msg.settings.language.display || msg.settings.language.tui || 'en';
        document.getElementById('selectMenuLanguage').value = lang;
        setLanguage(lang);
      }
      break;

    case 'game_started':
      switchScreen('gameScreen');
      MusicEngine.preloadAll();
      resetCompanion();  // fresh session → wipe any prior aside transcript
      if (msg.session) updateAllPanels(msg.session);
      if (pendingTutorial) { pendingTutorial = false; setTimeout(startTutorial, 600); }
      break;

    case 'thinking':
      clearSuggestedActions();
      showThinking();
      break;

    case 'narrative':
      // New game: the tutorial masks the first-turn wait. Buffer the opening
      // scene (and its suggested actions) and reveal it the instant the tutorial
      // ends — never type it out behind the overlay. Falls through to normal
      // rendering if the tutorial is already done (slow first turn).
      if (_firstSceneArmed && (msg.role || 'agent') === 'system') {
        hideThinking();
        _pendingFirstScene = msg;
        break;
      }
      hideThinking();
      const role = msg.role || 'agent';
      if (role === 'system') {
        // Resume message — will be removed after first player input
        resumeMessageEl = addTypingMessage(msg.text, role, null, msg.elapsed_seconds, msg.suggested_actions);
        isFirstInput = true;
      } else {
        addTypingMessage(msg.text, role, msg.usage, msg.elapsed_seconds, msg.suggested_actions);
      }
      break;

    case 'session_update':
      if (msg.session) updateAllPanels(msg.session);
      break;

    case 'prediction_ready':
      markPredictionReady(msg.text);
      break;

    case 'discovery':
      showDiscoveryNotification(msg);
      break;

    case 'knowledge_added':
      showKnowledgeNotification(msg.entry_type);
      break;

    case 'game_over':
      clearSuggestedActions();
      setTimeout(() => showGameOver(msg.ending, msg.narrative), 2000);
      break;

    case 'saved':
      notify(`${L('saved')}: ${msg.save_name}`);
      closeSaveDialog();
      break;

    case 'provider_saved':
      notify(L('settings_saved'));
      if (msg.provider) prefillProviderSettings(msg.provider);
      if (msg.langsmith) prefillLangsmithSettings(msg.langsmith);
      if (msg.features) _cachedFeatures = msg.features;
      document.getElementById('settingsStatus').textContent = L('saved');
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

function prefillLangsmithSettings(ls) {
  if (!ls) return;
  if (ls.project) document.getElementById('inputLangsmithProject').value = ls.project;
  // Don't prefill the API key for security — just show placeholder if set
  if (ls.enabled) document.getElementById('inputLangsmithKey').placeholder = '••••••• (configured)';
}

// Token display preference (persisted in localStorage)
function _showTokens() {
  return localStorage.getItem('signal_lost_show_tokens') === '1';
}

// Format cost calculated by the backend from actual LangGraph API usage metadata
function _getCost(usage) {
  return (usage && typeof usage.cost === 'number') ? usage.cost : 0;
}

function _formatCost(cost) {
  if (cost < 0.01) return '$' + cost.toFixed(4);
  return '$' + cost.toFixed(3);
}

let _settingsSnapshot = null; // snapshot before opening settings

function openSettings() {
  document.getElementById('settingsOverlay').style.display = 'flex';
  document.getElementById('settingsStatus').textContent = '';
  // Sync music volume slider
  const vol = MusicEngine.getVolume();
  document.getElementById('inputMusicVolume').value = vol;
  document.getElementById('musicVolValue').textContent = Math.round(vol * 100) + '%';
  // Snapshot ALL form state so cancel can restore
  _settingsSnapshot = {
    volume: vol,
    provider: document.getElementById('selectProvider').value,
    model: document.getElementById('inputModel').value,
    temperature: document.getElementById('inputTemp').value,
    apiKey: document.getElementById('inputApiKey').value,
    baseUrl: document.getElementById('inputBaseUrl').value,
    langsmithKey: document.getElementById('inputLangsmithKey').value,
    langsmithProject: document.getElementById('inputLangsmithProject').value,
    showTokens: _showTokens(),
  };
  // Sync token tracking checkbox
  document.getElementById('chkShowTokens').checked = _showTokens();
  // Sync gameplay feature checkboxes from the latest server-known flags.
  // Both default ON to match settings/default.json — so the boxes reflect the
  // real default even if the server flags haven't been received yet (a value is
  // only treated as off when the server explicitly reports false).
  const _feats = _cachedFeatures || {};
  const _sa = _feats.suggested_actions !== false;
  const _po = _feats.predict_outcome !== false;
  document.getElementById('chkSuggestedActions').checked = _sa;
  document.getElementById('chkPredictOutcome').checked = _po;
  _settingsSnapshot.suggestedActions = _sa;
  _settingsSnapshot.predictOutcome = _po;
  // Show cumulative usage stats if available
  _updateUsageStats();
  playBeep(1000, 0.04);
}

function closeSettings() {
  // Restore to pre-open state (cancel = discard all unsaved changes)
  if (_settingsSnapshot) {
    MusicEngine.setVolume(_settingsSnapshot.volume);
    document.getElementById('selectProvider').value = _settingsSnapshot.provider;
    document.getElementById('inputModel').value = _settingsSnapshot.model;
    document.getElementById('inputTemp').value = _settingsSnapshot.temperature;
    document.getElementById('tempValue').textContent = _settingsSnapshot.temperature;
    document.getElementById('inputApiKey').value = _settingsSnapshot.apiKey;
    document.getElementById('inputBaseUrl').value = _settingsSnapshot.baseUrl;
    document.getElementById('inputLangsmithKey').value = _settingsSnapshot.langsmithKey;
    document.getElementById('inputLangsmithProject').value = _settingsSnapshot.langsmithProject;
    document.getElementById('chkShowTokens').checked = _settingsSnapshot.showTokens;
    document.getElementById('chkSuggestedActions').checked = _settingsSnapshot.suggestedActions;
    document.getElementById('chkPredictOutcome').checked = _settingsSnapshot.predictOutcome;
    onProviderChange(); // re-sync field visibility for restored provider
    _settingsSnapshot = null;
  }
  document.getElementById('settingsOverlay').style.display = 'none';
}

function saveSettings() {
  const payload = { action: 'save_provider', provider: getProviderConfig() };
  const lsKey = document.getElementById('inputLangsmithKey').value;
  const lsProject = document.getElementById('inputLangsmithProject').value;
  if (lsKey || lsProject) {
    payload.langsmith = {};
    if (lsKey) payload.langsmith.api_key = lsKey;
    if (lsProject) payload.langsmith.project = lsProject;
  }
  // Save token display preference
  localStorage.setItem('signal_lost_show_tokens',
    document.getElementById('chkShowTokens').checked ? '1' : '0');
  // Gameplay feature toggles (persisted server-side in custom.json + session)
  payload.features = {
    suggested_actions: document.getElementById('chkSuggestedActions').checked,
    predict_outcome: document.getElementById('chkPredictOutcome').checked,
  };
  _cachedFeatures = Object.assign({}, _cachedFeatures || {}, payload.features);
  sendWS(payload);
  _settingsSnapshot = null;  // Mark as saved so close doesn't revert
  document.getElementById('settingsStatus').textContent = L('saving');
  document.getElementById('settingsOverlay').style.display = 'none';
}

let _cachedUsage = null;

function _updateUsageStats() {
  const u = _cachedUsage;
  const el = document.getElementById('usageStats');
  if (!el) return;
  if (!u || !u.total_calls) {
    el.innerHTML = '<span class="dim" style="font-size:11px">No usage data yet</span>';
    return;
  }
  const costStr = typeof u.cost === 'number' ? ` &nbsp;|&nbsp; Cost: <span class="cyan">${_formatCost(u.cost)}</span>` : '';
  el.innerHTML = `<div style="font-size:11px;color:var(--text-dim);line-height:1.6">
    LLM calls: <span class="cyan">${u.total_calls}</span> &nbsp;|&nbsp;
    Input: <span class="cyan">${(u.input_tokens || 0).toLocaleString()}</span> &nbsp;|&nbsp;
    Output: <span class="cyan">${(u.output_tokens || 0).toLocaleString()}</span> &nbsp;|&nbsp;
    Total: <span class="cyan">${(u.total_tokens || 0).toLocaleString()}</span> tokens${costStr}
  </div>`;
}

const DEFAULT_MODELS = {
  anthropic: 'claude-sonnet-4-6-20250514',
  'claude-code': 'sonnet',
  codex: 'gpt-5.5',
  openai: 'gpt-5.4',
  openrouter: 'openai/gpt-5.4',
  local: '[model]',
  lmstudio: '[model]',
};

// Providers that authenticate via a CLI's own OAuth flow — no API-key field needed.
const OAUTH_CLI_PROVIDERS = new Set(['claude-code', 'codex']);

let _lastProvider = null; // tracks provider to detect actual switches

function onProviderChange() {
  const p = document.getElementById('selectProvider').value;
  const hideApiKey = (p === 'local' || OAUTH_CLI_PROVIDERS.has(p));
  document.getElementById('apiKeyGroup').style.display = hideApiKey ? 'none' : '';
  document.getElementById('baseUrlGroup').style.display = (p === 'local' || p === 'openrouter') ? '' : 'none';
  // Only update model when the provider actually changes (not on initial load)
  if (_lastProvider !== null && _lastProvider !== p) {
    document.getElementById('inputModel').value = DEFAULT_MODELS[p] || '';
  }
  // Refresh the base-url placeholder/default for this provider
  const baseUrlInput = document.getElementById('inputBaseUrl');
  if (p === 'openrouter') {
    baseUrlInput.placeholder = 'https://openrouter.ai/api/v1';
    if (!baseUrlInput.value || baseUrlInput.value === 'http://localhost:1234/v1') {
      baseUrlInput.value = 'https://openrouter.ai/api/v1';
    }
  } else if (p === 'local') {
    baseUrlInput.placeholder = 'http://localhost:1234/v1';
    if (!baseUrlInput.value || baseUrlInput.value === 'https://openrouter.ai/api/v1') {
      baseUrlInput.value = 'http://localhost:1234/v1';
    }
  }
  // Refresh the API-key placeholder for this provider
  const apiKeyInput = document.getElementById('inputApiKey');
  if (apiKeyInput) {
    if (p === 'openrouter') apiKeyInput.placeholder = 'sk-or-...';
    else if (p === 'anthropic') apiKeyInput.placeholder = 'sk-ant-...';
    else apiKeyInput.placeholder = 'sk-...';
  }
  _lastProvider = p;
}

document.getElementById('inputTemp').addEventListener('input', function() {
  document.getElementById('tempValue').textContent = this.value;
});

function getProviderConfig() {
  const provider = document.getElementById('selectProvider').value;
  const config = {
    provider,
    model: document.getElementById('inputModel').value || DEFAULT_MODELS[provider] || 'gpt-5.4',
    temperature: parseFloat(document.getElementById('inputTemp').value),
  };
  if (provider === 'local') {
    config.base_url = document.getElementById('inputBaseUrl').value;
  } else if (provider === 'openrouter') {
    const baseUrl = document.getElementById('inputBaseUrl').value;
    if (baseUrl) config.base_url = baseUrl;
    const k = document.getElementById('inputApiKey').value;
    if (k) config.api_key = k;
  } else if (!OAUTH_CLI_PROVIDERS.has(provider)) {
    const k = document.getElementById('inputApiKey').value;
    if (k) config.api_key = k;
  }
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
  document.getElementById('confirmMenuTitle').textContent = L('confirm_menu_title');
  document.getElementById('confirmMenuText').textContent = L('confirm_menu_text');
  document.getElementById('confirmMenuYes').textContent = L('btn_confirm');
  document.getElementById('confirmMenuNo').textContent = L('btn_cancel');
  d.style.display = 'flex';
  playBeep(600, 0.04);
}

function confirmReturnToMenu() {
  document.getElementById('confirmMenuDialog').style.display = 'none';
  switchScreen('menuScreen');
  // Refresh saves/sessions list from server
  sendWS({ action: 'init' });
}

function closeConfirmMenu() {
  document.getElementById('confirmMenuDialog').style.display = 'none';
}
function showNewGame() { switchScreen('newGameScreen'); playBeep(1000, 0.04); }

function showLoadGame() {
  const list = document.getElementById('savesList');
  list.innerHTML = '';
  if (cachedSaves.length === 0) {
    list.innerHTML = `<div class="panel-empty">${L('no_saves')}</div>`;
  } else {
    cachedSaves.forEach(save => {
      const el = document.createElement('div');
      el.className = 'save-entry';
      const turnLabel = L('turn');
      el.innerHTML = `<div><div class="save-name">${esc(save.name)}</div>
        <div class="save-info">${esc(save.player_name)} — ${turnLabel} ${save.turn}</div></div>
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
  clearChat(); isFirstInput = true; pendingTutorial = true; resumeMessageEl = null;
  _firstSceneArmed = true; _pendingFirstScene = null; // hold opening scene until tutorial ends
  sendWS({ action: 'new_game', config, provider: getProviderConfig() });
  switchScreen('gameScreen'); showThinking(); disableInput();
}

function resumeGame(sessionName) {
  if (!sessionName) {
    if (cachedSessions.length === 1) {
      sessionName = cachedSessions[0].name;
    } else if (cachedSessions.length > 1) {
      showResumeSessionPicker();
      return;
    } else {
      return;
    }
  }
  clearChat(); isFirstInput = true; resumeMessageEl = null;
  _firstSceneArmed = false; _pendingFirstScene = null; // resume/load shows no tutorial — render scene immediately
  sendWS({ action: 'resume', session_name: sessionName, provider: getProviderConfig() });
  switchScreen('gameScreen'); showThinking(); disableInput();
}

function showResumeSessionPicker() {
  const list = document.getElementById('savesList');
  list.innerHTML = '';
  const loadTitle = document.querySelector('#loadGameScreen .config-title');
  if (loadTitle) loadTitle.textContent = L('resume_title');
  cachedSessions.forEach(sess => {
    const el = document.createElement('div');
    el.className = 'save-entry';
    const turnLabel = L('turn');
    el.innerHTML = `<div><div class="save-name">${esc(sess.name)}</div>
      <div class="save-info">${esc(sess.player_name)} — ${turnLabel} ${sess.turn}</div></div>
      <div style="color:var(--cyan)">⟩</div>`;
    el.onclick = () => resumeGame(sess.name);
    list.appendChild(el);
  });
  switchScreen('loadGameScreen');
}

function loadGame(saveName) {
  clearChat(); isFirstInput = true; resumeMessageEl = null;
  _firstSceneArmed = false; _pendingFirstScene = null; // resume/load shows no tutorial — render scene immediately
  sendWS({ action: 'load_game', save_name: saveName, provider: getProviderConfig() });
  switchScreen('gameScreen'); showThinking(); disableInput();
}

// ================================================================
// CHAT FUNCTIONS
// ================================================================

function clearChat() { document.getElementById('chatMessages').innerHTML = ''; discoveryEls = []; }

function showDiscoveryNotification(msg) {
  const container = document.getElementById('chatMessages');
  const el = document.createElement('div');
  el.className = 'chat-msg discovery-notification';
  const label = currentLang === 'zh' ? '◈ 痕迹发现' : '◈ TRACE DISCOVERED';
  el.innerHTML = `
    <div class="discovery-badge">
      <span class="discovery-label">${label}</span>
    </div>
    <div class="discovery-text">${esc(msg.description)}</div>
  `;
  container.appendChild(el);
  container.scrollTop = container.scrollHeight;
  discoveryEls.push(el);
}

// Track active knowledge toasts for vertical stacking
let _activeToasts = [];

function showKnowledgeNotification(entryType) {
  const labels = {
    fact:       { en: 'New fact discovered',     zh: '新事实已记录' },
    rumor:      { en: 'New rumor discovered',    zh: '新传闻已记录' },
    evidence:   { en: 'New evidence collected',  zh: '新证据已收集' },
    theory:     { en: 'New theory formed',       zh: '新理论已形成' },
    connection: { en: 'New connection found',    zh: '新关联已发现' },
  };
  const lang = currentLang === 'zh' ? 'zh' : 'en';
  const label = (labels[entryType] || labels.fact)[lang];

  const el = document.createElement('div');
  el.className = 'knowledge-toast';
  el.textContent = label;

  // Stack vertically above existing toasts
  const baseBottom = 24;
  const toastHeight = 40; // approximate height of each toast + gap
  const offset = baseBottom + _activeToasts.length * toastHeight;
  el.style.bottom = offset + 'px';

  document.body.appendChild(el);
  _activeToasts.push(el);

  requestAnimationFrame(() => el.classList.add('visible'));

  setTimeout(() => {
    el.classList.add('fading');
    setTimeout(() => {
      el.remove();
      _activeToasts = _activeToasts.filter(t => t !== el);
      // Reposition remaining toasts
      _activeToasts.forEach((t, i) => {
        t.style.bottom = (baseBottom + i * toastHeight) + 'px';
      });
    }, 500);
  }, 3000);
}

function _chatPrefixes() {
  return { player: L('chat_player'), agent: L('chat_agent'), system: L('chat_system'), warning: L('chat_agent') };
}

function addChatMessage(text, role = 'agent') {
  const container = document.getElementById('chatMessages');
  const msg = document.createElement('div');
  msg.className = `chat-msg ${role}`;
  const prefixes = _chatPrefixes();
  msg.innerHTML = `<div class="msg-prefix">${prefixes[role] || role.toUpperCase()}</div>
    <div class="msg-content">${esc(text)}</div>`;
  container.appendChild(msg);
  // Scroll to the START of the new message, not the bottom
  msg.scrollIntoView({ behavior: 'smooth', block: 'start' });
  playBeep(role === 'player' ? 1200 : 800, 0.03);
  return msg;
}

function addTypingMessage(text, role = 'agent', usage = null, elapsedSeconds = null, suggestedActions = null) {
  const container = document.getElementById('chatMessages');
  const msg = document.createElement('div');
  msg.className = `chat-msg ${role}`;
  const prefixes = _chatPrefixes();
  const contentEl = document.createElement('div');
  contentEl.className = 'msg-content typing';
  msg.innerHTML = `<div class="msg-prefix">${prefixes[role] || role.toUpperCase()}</div>`;
  msg.appendChild(contentEl);
  container.appendChild(msg);
  // Scroll to the START of the new message
  msg.scrollIntoView({ behavior: 'smooth', block: 'start' });

  let i = 0; const speed = 8, interval = 20;
  function typeNext() {
    if (i < text.length) {
      contentEl.textContent += text.slice(i, i + speed);
      i += speed;
      // Only auto-scroll if user is near the bottom (within 200px)
      if (container.scrollHeight - container.scrollTop - container.clientHeight < 200) {
        container.scrollTop = container.scrollHeight;
      }
      if (Math.random() < 0.05) playBeep(600 + Math.random() * 400, 0.02, 0.01);
      setTimeout(typeNext, interval);
    } else {
      contentEl.classList.remove('typing');
      // Build info line: time always shown, tokens optional
      const infoParts = [];
      if (elapsedSeconds != null) {
        infoParts.push(`${elapsedSeconds}s`);
      }
      if (usage && usage.total && _showTokens()) {
        const cost = _getCost(usage);
        infoParts.push(`${usage.total.toLocaleString()} tokens · ${_formatCost(cost)}`);
      }
      if (infoParts.length > 0) {
        const infoEl = document.createElement('div');
        infoEl.className = 'msg-tokens';
        infoEl.textContent = infoParts.join(' · ');
        msg.appendChild(infoEl);
      }
      enableInput();
      // Render quick-pick action buttons once the narration finishes typing.
      renderSuggestedActions(suggestedActions);
    }
  }
  // Agent narration gets a brief "incoming transmission" decrypt flash first;
  // resume/system messages type out plainly.
  if (role === 'agent') {
    _decryptReveal(msg, contentEl, typeNext);
  } else {
    typeNext();
  }
  return msg;
}

// ----------------------------------------------------------------------------
// Suggested actions (quick-pick buttons)
// ----------------------------------------------------------------------------

// Action texts whose pre-computed outcome has landed (prediction_ready). Lets a
// button render straight to "ready" when its prediction finished before the
// buttons were drawn — which is the norm for the buffered opening scene, where
// predictions complete while the player is still reading the tutorial.
let _readyPredictions = new Set();

function clearSuggestedActions() {
  const c = document.getElementById('suggestedActions');
  if (c) c.innerHTML = '';
  _readyPredictions.clear();
}

function renderSuggestedActions(actions) {
  const c = document.getElementById('suggestedActions');
  if (!c) return;
  // The suggested-action buttons live below the scrollable chat and shrink it
  // when they appear, which would otherwise clip the tail of the just-typed
  // message. Note whether the chat was pinned to the bottom BEFORE the buttons
  // render, so we can re-pin it afterward (but never yank a user who scrolled up).
  const chat = document.getElementById('chatMessages');
  const wasPinned = chat ? (chat.scrollHeight - chat.scrollTop - chat.clientHeight < 120) : false;
  c.innerHTML = '';
  // Respect the feature flag, in case it was disabled mid-turn.
  if (_cachedFeatures && _cachedFeatures.suggested_actions === false) return;
  if (!Array.isArray(actions) || actions.length === 0) return;
  // When outcome pre-computation is on, buttons start "pending" and brighten to
  // "ready" (instant reply) once their prediction lands (prediction_ready msg).
  const predicting = !!(_cachedFeatures && _cachedFeatures.predict_outcome);
  actions.slice(0, 3).forEach((a, idx) => {
    const text = (a && (a.text || a)) ? (a.text || a) : '';
    if (!text) return;
    // A prediction may already be ready (e.g. it finished during the tutorial).
    const ready = predicting && _readyPredictions.has(text);
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'suggested-action-btn' + (ready ? ' ready' : (predicting ? ' pending' : ''));
    btn.dataset.action = text;
    btn.textContent = text;
    btn.title = ready ? (text + ' — ready (instant)')
              : (predicting ? (text + ' — pre-computing…') : text);
    btn.onclick = () => chooseSuggestedAction(text);
    c.appendChild(btn);
  });
  // Re-pin to the bottom now that the buttons have taken their space, so the
  // end of the latest message stays visible above them.
  if (wasPinned && chat) {
    requestAnimationFrame(() => { chat.scrollTop = chat.scrollHeight; });
  }
}

function markPredictionReady(text) {
  if (!text) return;
  _readyPredictions.add(text); // remember, so a later render can start "ready"
  document.querySelectorAll('#suggestedActions .suggested-action-btn').forEach(btn => {
    if (btn.dataset.action === text) {
      btn.classList.remove('pending');
      btn.classList.add('ready');
      btn.title = text + ' — ready (instant)';
    }
  });
}

function chooseSuggestedAction(text) {
  const input = document.getElementById('chatInput');
  if (input.disabled) return;
  text = (text || '').trim();
  if (!text) return;

  // Mirror sendMessage()'s cleanup of ephemeral UI.
  if (isFirstInput && resumeMessageEl) {
    resumeMessageEl.classList.add('fade-out');
    setTimeout(() => { if (resumeMessageEl && resumeMessageEl.parentNode) resumeMessageEl.parentNode.removeChild(resumeMessageEl); resumeMessageEl = null; }, 500);
    isFirstInput = false;
  }
  discoveryEls.forEach(el => {
    el.classList.add('fade-out');
    setTimeout(() => { if (el.parentNode) el.parentNode.removeChild(el); }, 500);
  });
  discoveryEls = [];

  clearSuggestedActions();
  _setPendingPlayer(addChatMessage(text, 'player'));
  input.value = '';
  disableInput();
  sendWS({ action: 'player_input', text });
}

function sendMessage() {
  const input = document.getElementById('chatInput');
  if (input.disabled) return;
  const text = input.value.trim();
  if (!text) return;

  // Remove resume system message on first player input
  if (isFirstInput && resumeMessageEl) {
    resumeMessageEl.classList.add('fade-out');
    setTimeout(() => { if (resumeMessageEl && resumeMessageEl.parentNode) resumeMessageEl.parentNode.removeChild(resumeMessageEl); resumeMessageEl = null; }, 500);
    isFirstInput = false;
  }

  // Remove ephemeral discovery notifications
  discoveryEls.forEach(el => {
    el.classList.add('fade-out');
    setTimeout(() => { if (el.parentNode) el.parentNode.removeChild(el); }, 500);
  });
  discoveryEls = [];

  clearSuggestedActions();
  _setPendingPlayer(addChatMessage(text, 'player'));
  input.value = '';
  disableInput();
  sendWS({ action: 'player_input', text });
}

// ----------------------------------------------------------------------------
// Wait experience: status ticker, ambient audio, optimistic echo
// Custom (typed) input can't be pre-computed, so it always pays the full LLM
// wait. These keep the screen alive during it. All are cleared in hideThinking,
// the single chokepoint hit by both the 'narrative' and 'error' handlers, so a
// cached instant reply simply flashes through them harmlessly.
// ----------------------------------------------------------------------------
let _thinkingTimer = null;     // ticker interval (null once parked or stopped)
let _thinkingLineIdx = 0;      // current ticker line
let _ambientTimer = null;      // ambient-beep interval
let _pendingPlayerEl = null;   // the in-flight player command line

function _thinkingLineList() {
  return (LABELS[currentLang] && LABELS[currentLang].thinking_lines) || LABELS.en.thinking_lines || [];
}
function _thinkingLineText() {
  const lines = _thinkingLineList();
  if (!lines.length) return L('processing');
  return lines[Math.min(_thinkingLineIdx, lines.length - 1)];
}
function _renderThinkingLine() {
  const el = document.querySelector('.thinking-text');
  if (el) el.textContent = _thinkingLineText();
}
function _startThinkingTicker() {
  _stopThinkingTicker();
  _thinkingLineIdx = 0;
  _renderThinkingLine();
  const hint = document.getElementById('thinkingHint');
  if (hint) hint.textContent = L('thinking_hint');
  _thinkingTimer = setInterval(() => {
    const lines = _thinkingLineList();
    if (_thinkingLineIdx >= lines.length - 1) {
      // Reached the final "still tracing" line — park there (CSS keeps it
      // pulsing) and stop ticking so a long wait never looks frozen.
      clearInterval(_thinkingTimer); _thinkingTimer = null;
      return;
    }
    _thinkingLineIdx++;
    _renderThinkingLine();
  }, 2600);
}
function _stopThinkingTicker() {
  if (_thinkingTimer) { clearInterval(_thinkingTimer); _thinkingTimer = null; }
  _thinkingLineIdx = 0;
}

function _startAmbient() {
  _stopAmbient();
  _ambientTimer = setInterval(() => {
    // Honour the music mute toggle (isMuted is a function — call it).
    if (typeof MusicEngine !== 'undefined' && typeof MusicEngine.isMuted === 'function' && MusicEngine.isMuted()) return;
    if (Math.random() < 0.5) playBeep(150 + Math.random() * 130, 0.05 + Math.random() * 0.05, 0.006);
  }, 650);
}
function _stopAmbient() {
  if (_ambientTimer) { clearInterval(_ambientTimer); _ambientTimer = null; }
}

function _setPendingPlayer(el) {
  _clearPendingPlayer();
  if (el) { el.classList.add('pending'); _pendingPlayerEl = el; }
}
function _clearPendingPlayer() {
  if (_pendingPlayerEl) { _pendingPlayerEl.classList.remove('pending'); _pendingPlayerEl = null; }
}

const _DECRYPT_GLYPHS = '▓▒░#@%&/\\|<>=+*01';
/** Brief "signal locking in" scramble before an agent message types out. */
function _decryptReveal(msg, contentEl, done) {
  msg.classList.add('decrypting');
  playBeep(420, 0.05, 0.02);
  setTimeout(() => playBeep(900, 0.06, 0.02), 90); // two-tone lock-in
  const width = 14;
  let frames = 0;
  const t = setInterval(() => {
    let s = '';
    for (let k = 0; k < width; k++) s += _DECRYPT_GLYPHS[Math.floor(Math.random() * _DECRYPT_GLYPHS.length)];
    contentEl.textContent = s;
    if (++frames >= 6) { // ~6 * 50ms ≈ 300ms
      clearInterval(t);
      contentEl.textContent = '';
      msg.classList.remove('decrypting');
      done();
    }
  }, 50);
}

function showThinking() {
  document.getElementById('thinkingIndicator').style.display = 'flex';
  document.getElementById('chatMessages').scrollTop = document.getElementById('chatMessages').scrollHeight;
  _startThinkingTicker();
  _startAmbient();
  const tabs = document.querySelector('.panel-tabs');
  if (tabs) tabs.classList.add('hint-pulse');
}
function hideThinking() {
  document.getElementById('thinkingIndicator').style.display = 'none';
  _stopThinkingTicker();
  _stopAmbient();
  _clearPendingPlayer();
  const tabs = document.querySelector('.panel-tabs');
  if (tabs) tabs.classList.remove('hint-pulse');
}
function enableInput() { const i = document.getElementById('chatInput'); i.disabled = false; i.focus(); document.querySelector('.send-btn').disabled = false; document.querySelectorAll('.suggested-action-btn').forEach(b => b.disabled = false); }
function disableInput() { document.getElementById('chatInput').disabled = true; document.querySelector('.send-btn').disabled = true; document.querySelectorAll('.suggested-action-btn').forEach(b => b.disabled = true); }

// ================================================================
// SAVE / LOAD
// ================================================================

function _defaultSaveName() {
  const now = new Date();
  const mm = String(now.getMonth() + 1).padStart(2, '0');
  const dd = String(now.getDate()).padStart(2, '0');
  const yyyy = now.getFullYear();
  const hh = String(now.getHours()).padStart(2, '0');
  const mi = String(now.getMinutes()).padStart(2, '0');
  const alias = (cachedSession?.player?.alias || cachedSession?.player?.name || 'Unknown');
  return `${mm}-${dd}-${yyyy} ${hh}:${mi} ${alias}`;
}
function saveGame() { const el = document.getElementById('saveName'); el.value = _defaultSaveName(); document.getElementById('saveDialog').style.display = 'flex'; el.focus(); el.select(); playBeep(1000, 0.04); }
function confirmSave() { sendWS({ action: 'save_game', save_name: document.getElementById('saveName').value.trim() || _defaultSaveName() }); }
function closeSaveDialog() { document.getElementById('saveDialog').style.display = 'none'; }

function showGameOver(ending, narrative) {
  triggerGlitch(); triggerGlitch();
  document.getElementById('gameOverEnding').textContent = ending ? `// ${ending.toUpperCase()}` : L('game_over_fallback');
  document.getElementById('gameOverNarrative').textContent = narrative || '';
  document.getElementById('gameOverOverlay').style.display = 'flex';
  playBeep(200, 0.3, 0.05);
}

// ================================================================
// TUTORIAL
// ================================================================

let tutorialStep = 0;
let tutorialActive = false;

const TUTORIAL_STEPS = {
  en: [
    { target: '#chatPanel', text: 'This is the <b>Command Terminal</b>. Type actions here to interact with the world — talk to NPCs, investigate locations, hack systems, or anything you can imagine.', pos: 'right' },
    { target: '.info-panels', text: 'This is the <b>Info Panel</b>. It tracks everything about your character and the world. Use the tabs above to switch views.', pos: 'left' },
    { target: '[data-panel="identity"]', text: '<b>ID</b> — Your identity card. Shows your name, background, integrity (health), credits, and status effects.', pos: 'below', activateTab: 'identity' },
    { target: '[data-panel="knowledge"]', text: '<b>KNOW</b> — Everything you\'ve learned: facts, rumors, evidence, theories, and connections between them.', pos: 'below', activateTab: 'knowledge' },
    { target: '[data-panel="traces"]', text: '<b>TRACE</b> — Fragments of truth you\'ve uncovered. The deeper you dig, the more you\'ll find.', pos: 'below', activateTab: 'traces' },
    { target: '[data-panel="district"]', text: '<b>LOC</b> — Your current location, danger level, signal strength, nearby exits, and points of interest.', pos: 'below', activateTab: 'district' },
    { target: '[data-panel="inventory"]', text: '<b>INV</b> — Items you\'re carrying. Limited slots, so choose wisely.', pos: 'below', activateTab: 'inventory' },
    { target: '[data-panel="network"]', text: '<b>NPC</b> — People you\'ve met. Track their faction, trust level, location, and quests.', pos: 'below', activateTab: 'network' },
    { target: '[data-panel="world"]', text: '<b>WORLD</b> — Global state: NEXUS alert level, fragment decay, and district access status.', pos: 'below', activateTab: 'world' },
    { target: '[data-panel="log"]', text: '<b>LOG</b> — Session log of key events: discoveries, encounters, and world changes. A quick recap of what happened.', pos: 'below', activateTab: 'log' },
    { target: '[data-panel="conversation"]', text: '<b>CONV</b> — Full conversation history. Scroll back through everything you and the system have said.', pos: 'below', activateTab: 'conversation' },
    { target: '#chatNeuralBtn, #companionFab', text: '<b>NEURAL LINK</b> — Tap your implant anytime to ask questions or just think out loud. It only knows what you already know — no spoilers — and nothing you say here touches the world or gets saved. It won\'t interrupt the game.', pos: 'above' },
    { target: '#chatInput', text: 'You\'re ready. Type your first action and press Enter. Explore, investigate, and survive. Good luck, operative.', pos: 'above' },
  ],
  zh: [
    { target: '#chatPanel', text: '这是<b>命令终端</b>。在这里输入行动来与世界互动——与NPC对话、调查地点、入侵系统，或任何你能想象的事。', pos: 'right' },
    { target: '.info-panels', text: '这是<b>信息面板</b>。它追踪你角色和世界的一切信息。使用上方的标签切换视图。', pos: 'left' },
    { target: '[data-panel="identity"]', text: '<b>身份</b> — 你的身份卡。显示姓名、背景、完整性（生命值）、信用点和状态效果。', pos: 'below', activateTab: 'identity' },
    { target: '[data-panel="knowledge"]', text: '<b>知识</b> — 你所了解的一切：事实、传闻、证据、推论以及它们之间的关联。', pos: 'below', activateTab: 'knowledge' },
    { target: '[data-panel="traces"]', text: '<b>痕迹</b> — 你发现的真相碎片。挖得越深，发现越多。', pos: 'below', activateTab: 'traces' },
    { target: '[data-panel="district"]', text: '<b>区域</b> — 当前位置、危险等级、信号强度、附近出口和兴趣点。', pos: 'below', activateTab: 'district' },
    { target: '[data-panel="inventory"]', text: '<b>物品</b> — 你携带的物品。槽位有限，请明智选择。', pos: 'below', activateTab: 'inventory' },
    { target: '[data-panel="network"]', text: '<b>人脉</b> — 你遇到的人。追踪他们的阵营、信任度、位置和任务。', pos: 'below', activateTab: 'network' },
    { target: '[data-panel="world"]', text: '<b>世界</b> — 全局状态：连结警报等级、碎片衰变和区域通行状况。', pos: 'below', activateTab: 'world' },
    { target: '[data-panel="log"]', text: '<b>日志</b> — 关键事件记录：发现、遭遇和世界变化。快速回顾发生的一切。', pos: 'below', activateTab: 'log' },
    { target: '[data-panel="conversation"]', text: '<b>对话</b> — 完整对话记录。回顾你和系统之间的所有交流。', pos: 'below', activateTab: 'conversation' },
    { target: '#chatNeuralBtn, #companionFab', text: '<b>神经链接</b> — 随时点击植入体提问，或只是自言自语。它只知道你已知的事——不会剧透——你在这里说的一切都不会影响世界，也不会被保存。它也不会打断游戏进程。', pos: 'above' },
    { target: '#chatInput', text: '准备就绪。输入你的第一个行动并按回车。探索、调查、生存。祝你好运，特工。', pos: 'above' },
  ],
};

function startTutorial() {
  tutorialStep = 0;
  tutorialActive = true;
  document.getElementById('tutorialOverlay').style.display = 'block';
  showTutorialStep();
  playBeep(1000, 0.03);
}

function endTutorial() {
  tutorialActive = false;
  document.getElementById('tutorialOverlay').style.display = 'none';
  // Restore ID tab
  const idTab = document.querySelector('[data-panel="identity"]');
  if (idTab) switchPanel(idTab);
  playBeep(600, 0.03);
  _revealFirstScene();
}

// Reveal the buffered opening scene once the tutorial is dismissed. Clearing
// _firstSceneArmed first means that if the first turn hasn't returned yet, the
// 'narrative' handler will render it normally (with the live thinking indicator)
// instead of re-buffering it.
function _revealFirstScene() {
  _firstSceneArmed = false;
  const msg = _pendingFirstScene;
  _pendingFirstScene = null;
  if (!msg) return;
  hideThinking();
  const role = msg.role || 'agent';
  resumeMessageEl = addTypingMessage(msg.text, role, null, msg.elapsed_seconds, msg.suggested_actions);
  isFirstInput = true;
}

function nextTutorialStep() {
  tutorialStep++;
  const steps = TUTORIAL_STEPS[currentLang] || TUTORIAL_STEPS.en;
  if (tutorialStep >= steps.length) {
    endTutorial();
    return;
  }
  showTutorialStep();
  playBeep(900, 0.02);
}

function showTutorialStep() {
  const steps = TUTORIAL_STEPS[currentLang] || TUTORIAL_STEPS.en;
  const step = steps[tutorialStep];
  const overlay = document.getElementById('tutorialOverlay');
  const highlight = document.getElementById('tutorialHighlight');
  const tooltip = document.getElementById('tutorialTooltip');
  const textEl = document.getElementById('tutorialText');
  const indicator = document.getElementById('tutorialStepIndicator');
  const skipBtn = document.getElementById('tutorialSkip');
  const nextBtn = document.getElementById('tutorialNext');

  // Activate tab if needed
  if (step.activateTab) {
    const tabBtn = document.querySelector(`[data-panel="${step.activateTab}"]`);
    if (tabBtn) switchPanel(tabBtn);
  }

  // Resolve to the first VISIBLE match so multi-selector targets (e.g. the
  // inline neural button on mobile vs. the floating FAB on desktop) land on
  // whichever element is actually shown.
  let target = null;
  for (const el of document.querySelectorAll(step.target)) {
    if (el.getClientRects().length) { target = el; break; }
  }
  if (!target) { nextTutorialStep(); return; }

  const rect = target.getBoundingClientRect();

  // Position highlight
  highlight.style.left = rect.left - 4 + 'px';
  highlight.style.top = rect.top - 4 + 'px';
  highlight.style.width = rect.width + 8 + 'px';
  highlight.style.height = rect.height + 8 + 'px';

  // Set content
  const isLast = tutorialStep === steps.length - 1;
  indicator.textContent = `${L('tutorial_step')} ${tutorialStep + 1} / ${steps.length}`;
  textEl.innerHTML = step.text;
  skipBtn.textContent = L('tutorial_skip');
  nextBtn.textContent = isLast ? L('tutorial_finish') : L('tutorial_next');

  // Position tooltip
  tooltip.style.animation = 'none';
  tooltip.offsetHeight; // force reflow
  tooltip.style.animation = '';

  // Reset positioning
  tooltip.style.left = '';
  tooltip.style.right = '';
  tooltip.style.top = '';
  tooltip.style.bottom = '';

  const tooltipW = 340;
  const margin = 16;

  if (step.pos === 'right') {
    tooltip.style.left = Math.min(rect.right + margin, window.innerWidth - tooltipW - margin) + 'px';
    tooltip.style.top = rect.top + 'px';
  } else if (step.pos === 'left') {
    tooltip.style.left = Math.max(rect.left - tooltipW - margin, margin) + 'px';
    tooltip.style.top = rect.top + 'px';
  } else if (step.pos === 'below') {
    tooltip.style.left = Math.max(margin, Math.min(rect.left, window.innerWidth - tooltipW - margin)) + 'px';
    tooltip.style.top = rect.bottom + margin + 'px';
  } else if (step.pos === 'above') {
    // Clamp horizontally so the tooltip stays on-screen even for a target near
    // the right edge (e.g. the bottom-right companion button).
    tooltip.style.left = Math.max(margin, Math.min(rect.left, window.innerWidth - tooltipW - margin)) + 'px';
    tooltip.style.bottom = (window.innerHeight - rect.top + margin) + 'px';
  }
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

  function startResize(e) {
    isResizing = true;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
    e.preventDefault();
  }

  function moveResize(clientX) {
    if (!isResizing) return;
    const layoutRect = layout.getBoundingClientRect();
    const pct = ((clientX - layoutRect.left) / layoutRect.width) * 100;
    const clamped = Math.max(25, Math.min(80, pct));
    chatPanel.style.flex = 'none';
    chatPanel.style.width = clamped + '%';
    infoPanel.style.flex = 'none';
    infoPanel.style.width = (100 - clamped) + '%';
  }

  function endResize() {
    if (isResizing) { isResizing = false; document.body.style.cursor = ''; document.body.style.userSelect = ''; }
  }

  // Mouse (desktop)
  handle.addEventListener('mousedown', startResize);
  document.addEventListener('mousemove', (e) => moveResize(e.clientX));
  document.addEventListener('mouseup', endResize);

  // Touch (iPad / touchscreens) — mirror the mouse flow. passive:false so we can
  // preventDefault and stop the page from scrolling mid-drag.
  handle.addEventListener('touchstart', startResize, { passive: false });
  document.addEventListener('touchmove', (e) => {
    if (!isResizing) return;
    if (e.touches[0]) moveResize(e.touches[0].clientX);
    e.preventDefault();
  }, { passive: false });
  document.addEventListener('touchend', endResize);
  document.addEventListener('touchcancel', endResize);
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

// ---------- MOBILE INFO-PANEL DRAWER ----------
// On phones the info panels collapse into a slide-in drawer. These toggle a
// `.panels-open` class on #gameLayout; the CSS only reacts to it at mobile
// widths, so the desktop two-column layout is untouched.
function toggleInfoPanels() {
  const layout = document.getElementById('gameLayout');
  if (!layout) return;
  layout.classList.contains('panels-open') ? closeInfoPanels() : openInfoPanels();
}

function openInfoPanels() {
  const layout = document.getElementById('gameLayout');
  const btn = document.getElementById('btnInfoPanels');
  if (!layout) return;
  layout.classList.add('panels-open');
  if (btn) btn.classList.add('active');
  playBeep(700, 0.02);
}

function closeInfoPanels() {
  const layout = document.getElementById('gameLayout');
  const btn = document.getElementById('btnInfoPanels');
  if (!layout) return;
  layout.classList.remove('panels-open');
  if (btn) btn.classList.remove('active');
}

// Consolidated top-right nav menu (Tutorial / Save / Settings / Main Menu).
function toggleNavMenu(ev) {
  if (ev) ev.stopPropagation();
  const menu = document.getElementById('navMenu');
  const btn = document.getElementById('btnNavMenu');
  if (!menu) return;
  const open = menu.classList.toggle('open');
  menu.setAttribute('aria-hidden', String(!open));
  if (btn) btn.setAttribute('aria-expanded', String(open));
  playBeep(700, 0.02);
}

function closeNavMenu() {
  const menu = document.getElementById('navMenu');
  const btn = document.getElementById('btnNavMenu');
  if (menu && menu.classList.contains('open')) {
    menu.classList.remove('open');
    menu.setAttribute('aria-hidden', 'true');
    if (btn) btn.setAttribute('aria-expanded', 'false');
  }
}

function navMenuAction(which) {
  closeNavMenu();
  if (which === 'tutorial') startTutorial();
  else if (which === 'save') saveGame();
  else if (which === 'settings') openSettings();
  else if (which === 'menu') showMenu();
}

// Dismiss the nav menu on outside click or Escape.
document.addEventListener('click', (e) => {
  const wrap = document.querySelector('.nav-menu-wrap');
  if (wrap && !wrap.contains(e.target)) closeNavMenu();
});
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeNavMenu(); });

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
  // Cache usage data for settings display
  if (session.usage) _cachedUsage = session.usage;
  // Update background music based on current district (only while in-game)
  if (document.getElementById('gameScreen').classList.contains('active')) {
    MusicEngine.updateFromSession(session);
  }
}

// ---------- STATUS BAR (matches TUI StatusBar) ----------

function updateStatusBar(session) {
  const p = session.player || {};
  const l = session.location || {};
  const integrity = p.integrity || {};

  // Integrity pips: filled █ and empty ░
  const cur = integrity.current || 0, max = integrity.max || 3;
  let pips = '';
  for (let i = 0; i < max; i++) {
    pips += i < cur ? '<span class="pip filled">\u2588</span>' : '<span class="pip empty">\u2591</span>';
  }
  document.getElementById('statIntegrityPips').innerHTML = pips;

  // Location (district + area)
  setText('statLocation', l.district || '—');
  setText('statArea', l.area || '—');

  // Translate status bar labels
  setText('statLabelIntegrity', L('integrity').toUpperCase());
  setText('statLabelLocation', L('location').toUpperCase());
  setText('statLabelArea', L('area').toUpperCase());
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
  const disguiseIsNone = !p.current_disguise || p.current_disguise === 'None' || p.current_disguise === '无';

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
  document.getElementById('panel-knowledge-body').innerHTML = html;
  applyPanelSearch('knowledge');
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
    for (let i = 0; i < discovered.length; i++) {
      const trace = discovered[i];
      html += `<div class="trace-item discovered">
        <span class="dim" style="font-size:11px">TRACE-${String(i + 1).padStart(2, '0')}</span>
        ${esc(trace.description)}
        ${trace.turn ? `<span class="dim"> (${L('turn')} ${trace.turn})</span>` : ''}
      </div>`;
    }
    html += `</div>`;
  }
  document.getElementById('panel-traces-body').innerHTML = html;
  applyPanelSearch('traces');
}

// ---------- LOCATION IMAGES (assets/locations/*.png served at /assets) ----------
// The live location carries a fixed `district` (one of the 8 canonical districts)
// but a free-text `area` authored by the LLM, so we resolve cover art from the
// bundled manifest: prefer a specific landmark named in the area (scoped to the
// district), else the district establishing shot, else the Neo-Kowloon world shot.
// Names are matched in either language. Art is optional — the panel works without it.
const LOCATION_IMG_BASE = '/assets/locations/';
let LOCATION_MANIFEST = null;          // { locations: [...] } once loaded
let _locationManifestPending = false;

function loadLocationManifest() {
  if (LOCATION_MANIFEST || _locationManifestPending) return;
  _locationManifestPending = true;
  fetch(`${LOCATION_IMG_BASE}manifest.json`)
    .then(r => (r.ok ? r.json() : null))
    .then(m => {
      LOCATION_MANIFEST = (m && Array.isArray(m.locations)) ? m : null;
      // Re-render now that art is available (first render likely had none yet).
      if (LOCATION_MANIFEST && cachedSession && cachedSession.location) {
        updateDistrictPanel(cachedSession.location);
      }
    })
    .catch(() => { /* art is optional */ })
    .finally(() => { _locationManifestPending = false; });
}

// Strip whitespace/punctuation so free text and manifest names compare cleanly.
function _locNorm(s) {
  return String(s || '').toLowerCase()
    .replace(/[\s’'"“”·・.,，、。—–\-_/\\|()（）【】「」\[\]]/g, '');
}

// True when `hay` contains this entry's canonical name (either language). Used for
// the canonical `district` field, which is curated (and may be an "EN / 中文" pair),
// so a plain substring test is safe there.
function _locNameInText(entry, hay) {
  if (!hay) return false;
  for (const raw of [entry.name, entry.name_zh]) {
    const n = _locNorm(raw);
    if (n.length >= 2 && hay.includes(n)) return true;
  }
  return false;
}

// True when the free-text `area` actually names this place — ANCHORED so that a short
// generic word (e.g. 盲区 "blind spot", 中庭 "atrium") used descriptively mid-sentence
// does NOT resolve to a specific landmark the player isn't at. The area must lead with
// the name (the usual phrasing when you're at a place, e.g. "雨巷的尽头", "The Void back
// booth"); a plain substring match is only trusted for long, specific names (>=5 norm
// chars: e.g. 子午线俱乐部, publicterminal) that are unlikely to appear by coincidence.
function _areaNamesPlace(entry, areaN) {
  if (!areaN) return false;
  for (const raw of [entry.name, entry.name_zh]) {
    const n = _locNorm(raw);
    if (n.length < 2) continue;
    if (areaN.startsWith(n)) return true;
    if (n.length >= 5 && areaN.includes(n)) return true;
  }
  return false;
}

function locationImageEntry(location) {
  if (!LOCATION_MANIFEST) return null;
  const l = location || {};
  const areaN = _locNorm(l.area);
  const districtN = _locNorm(l.district);
  const entries = LOCATION_MANIFEST.locations;

  // Resolve the district entry (canonical field, then a mention in the area text).
  let districtEntry = entries.find(e => e.category === 'district' && _locNameInText(e, districtN))
    || (areaN ? entries.find(e => e.category === 'district' && _areaNamesPlace(e, areaN)) : null);

  // Prefer a landmark named in the free-text area, scoped to the resolved district
  // to avoid cross-district name collisions.
  if (areaN) {
    const scoped = entries.filter(e => e.category === 'landmark'
      && (!districtEntry || e.district === districtEntry.district));
    const landmark = scoped.find(e => _areaNamesPlace(e, areaN));
    if (landmark) return landmark;
  }

  if (districtEntry) return districtEntry;
  return entries.find(e => e.category === 'world') || null;
}

// ---------- DISTRICT PANEL (matches TUI DistrictPanel — no zone) ----------

function updateDistrictPanel(location) {
  loadLocationManifest();
  const l = location || {};
  const dangerCls = dangerColor(l.danger_level);

  let html = `
    <div class="panel-section">
      <div class="panel-section-title">${L('current_location')}</div>
      <div class="panel-row"><span class="panel-key">${L('district')}</span><span class="panel-val ${dangerCls}">${esc(l.district)}</span></div>
      <div class="panel-row"><span class="panel-key">${L('area')}</span><span class="panel-val">${esc(l.area)}</span></div>`;

  // Signal — only show if present
  if (l.signal_strength != null && l.signal_strength !== '' && l.signal_strength !== 0) {
    const sigStr = parseInt(l.signal_strength) || 0;
    const sigBars = Math.round(sigStr / 10);
    let sigWave = '';
    for (let i = 0; i < 10; i++) sigWave += i < sigBars ? '\u2248' : '\u00B7';
    html += `<div class="panel-row"><span class="panel-key">${L('signal_strength')}</span><span class="panel-val magenta">${sigWave} ${esc(l.signal_strength)}</span></div>`;
  }

  // Danger — only show if present
  if (l.danger_level) {
    const dangerDisplay = localizeData('danger', l.danger_level);
    html += `<div class="panel-row"><span class="panel-key">${L('danger_level')}</span><span class="panel-val ${dangerCls}">${esc(dangerDisplay)}</span></div>`;
  }

  // NEXUS patrol — only show if present
  if (l.nexus_patrol) {
    const patrolStr = l.nexus_patrol.toLowerCase();
    const patrolColor = (patrolStr === 'none' || patrolStr === '无') ? 'green' : (patrolStr.includes('light') || patrolStr.includes('轻') ? 'yellow' : 'red');
    html += `<div class="panel-row"><span class="panel-key">${L('nexus_patrol')}</span><span class="panel-val ${patrolColor}">${esc(l.nexus_patrol)}</span></div>`;
  }

  html += `</div>`;

  const imgEntry = locationImageEntry(l);
  if (l.description || imgEntry) {
    html += `<div class="panel-section"><div class="panel-section-title">${L('description')}</div>`;
    if (imgEntry) {
      const cap = currentLang === 'zh' && imgEntry.name_zh ? imgEntry.name_zh : imgEntry.name;
      html += `<div class="location-image-frame">
        <img class="location-image" src="${LOCATION_IMG_BASE}${esc(imgEntry.file)}" alt="${esc(cap)}" loading="lazy"
             onerror="this.closest('.location-image-frame').style.display='none'">
        <div class="location-image-caption">${esc(cap)}</div>
      </div>`;
    }
    if (l.description) {
      html += `<div class="panel-description">${esc(l.description)}</div>`;
    }
    html += `</div>`;
  }

  if (l.exits) {
    html += `<div class="panel-section"><div class="panel-section-title">${L('exits')}</div>`;
    for (const [dir, desc] of Object.entries(l.exits)) {
      const dirDisplay = currentLang === 'zh' ? (DIRECTION_ZH[dir.toLowerCase()] || dir) : dir;
      html += `<div class="panel-list-item">\u25B8 <span class="cyan" style="text-transform:uppercase">${esc(dirDisplay)}</span> — ${esc(desc)}</div>`;
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

  // Accept both npcs_present and npcs_here
  const npcsHere = l.npcs_present || l.npcs_here || [];
  if (npcsHere.length > 0) {
    html += `<div class="panel-section"><div class="panel-section-title">${L('npcs_present')}</div>`;
    for (const npc of npcsHere) {
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

// ---------- NPC AVATARS (assets/characters/*.png served at /assets) ----------
// NPC objects carry no stable id — only a (possibly localized) name, which in
// this game is often descriptive (e.g. "修理摊老板" = repair-stall owner). So we
// resolve a face by: canonical character -> role keyword (in name+occupation)
// -> faction -> district, falling back to a generic civilian. The panel shows
// faction/trust as text alongside, so the avatar only needs a plausible face.
const AVATAR_BASE = '/assets/characters/';
const AVATAR_FALLBACK = 'civilian';   // generic face when nothing else matches
const AVATAR_ERR = 'unknown';         // silhouette shown if a png fails to load

// Canonical named characters: match English id OR localized display name.
const NAMED_AVATARS = [
  { id: 'mira',      match: ['mira', '米拉'] },
  { id: 'ghost',     match: ['ghost', '幽灵'] },
  { id: 'orin',      match: ['orin', '欧林', '奥林'] },
  { id: 'patch',     match: ['patch', '帕奇', '补丁'] },
  { id: 'lian',      match: ['senator lian', 'lian', '莲参议员', '莲议员', '连议员'] },
  { id: 'echo',      match: ['echo', '回声'] },
  { id: 'architect', match: ['architect', '建筑师', 'shen wei', '沈卫'] },
  { id: 'player',    match: ['player', '玩家'] },
];

// role keyword -> archetype, matched against name + occupation text (first wins).
const ROLE_AVATARS = [
  { id: 'red_circuit',      kw: ['red circuit', 'gang', 'syndicate', 'thug', 'enforcer', 'smuggler', '红环', '帮派'] },
  { id: 'nexus_sentinel',   kw: ['sentinel', 'guard', 'security', 'soldier', 'patrol', '哨兵', '警卫', '保安'] },
  { id: 'fixer',            kw: ['fixer', 'broker', 'kingpin', '中间人', '掮客'] },
  { id: 'neon_dealer',      kw: ['dealer', 'bartender', 'bouncer', 'club', 'parlor', 'hacker', 'netrunner', 'stim', '酒保', '酒吧', '黑客', '保镖'] },
  { id: 'sprawl_vendor',    kw: ['vendor', 'merchant', 'shop', 'noodle', 'cook', 'trader', 'peddl', 'stall', 'parts', '商', '摊', '贩', '面', '机械', '修械', '修理', '信使', '厨'] },
  { id: 'street_kid',       kw: ['kid', 'child', 'youth', 'orphan', 'urchin', '少年', '少女', '青年', '年轻', '孩', '童'] },
  { id: 'scavenger',        kw: ['scavenger', 'scav', 'salvage', 'hunter', 'guide', 'wanderer', '拾荒', '猎', '向导', '流浪'] },
  { id: 'fragment_touched', kw: ['fragment', 'touched', 'resonan', '共鸣', '碎片'] },
  { id: 'nexus_staff',      kw: ['nexus', 'corporate', 'executive', 'director', 'researcher', 'scientist', '研究', '主管'] },
  { id: 'chrome_elite',     kw: ['senator', 'politician', 'aide', 'tutor', 'lobby', 'elite', 'noble', 'staffer', '议员', '政客', '助理', '名流'] },
  { id: 'listener',         kw: ['listener', '聆听', '听众'] },
  { id: 'purist',           kw: ['purist', 'surgeon', '纯净', '净化', '外科'] },
];

// faction substring -> archetype (handles decorated strings like "聆听者（疑似）").
const FACTION_AVATARS = [
  { id: 'nexus_staff', kw: ['nexus', 'corporate'] },
  { id: 'listener',    kw: ['listener', '聆听', '听众'] },
  { id: 'purist',      kw: ['purist', '纯净', '净化'] },
  { id: 'fixer',       kw: ['underground', '红环', '跑线'] },
  { id: 'civilian',    kw: ['unaffiliated', 'independent', '无所属'] },
];

// district / location keyword -> archetype (first match wins).
const DISTRICT_AVATARS = [
  { id: 'nexus_staff',  kw: ['sector 7', 'sector7', 'nexus tower', '第七区'] },
  { id: 'neon_dealer',  kw: ['neon row', 'neon', '霓虹'] },
  { id: 'scavenger',    kw: ['undercroft', '底渊', '地下轨道', '废弃站台', '腹道'] },
  { id: 'chrome_elite', kw: ['chrome heights', 'chrome', 'spire', '镀金', '尖塔'] },
];

function _avNorm(s) { return String(s || '').toLowerCase(); }
function _avHit(list, text) {
  for (const e of list) if (e.kw.some(k => text.includes(k))) return e.id;
  return null;
}

function npcAvatarId(npc) {
  const name = _avNorm(npc.name || npc.id);
  for (const c of NAMED_AVATARS) {
    if (c.match.some(m => name.includes(_avNorm(m)))) return c.id;
  }
  const roleText = _avNorm(`${npc.name || ''} ${npc.occupation || ''} ${npc.role || ''} ${npc.archetype || ''} ${npc.type || ''}`);
  const byRole = _avHit(ROLE_AVATARS, roleText);
  if (byRole) return byRole;

  const faction = _avNorm(npc.faction);
  const byFaction = faction && _avHit(FACTION_AVATARS, faction);
  if (byFaction) return byFaction;

  const loc = _avNorm(`${npc.location_last_seen || ''} ${npc.location || ''}`);
  const byDistrict = loc && _avHit(DISTRICT_AVATARS, loc);
  if (byDistrict) return byDistrict;

  return AVATAR_FALLBACK;
}

function npcAvatarImg(npc) {
  const id = npcAvatarId(npc);
  const fb = `${AVATAR_BASE}${AVATAR_ERR}.png`;
  return `<img class="npc-avatar" src="${AVATAR_BASE}${id}.png" alt="" loading="lazy" `
       + `onerror="this.onerror=null;this.src='${fb}'">`;
}

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

      // Short identity the player has formed — may be inaccurate, gated to what
      // they've learned. Falls back to occupation/role for legacy saves that
      // predate the LLM-maintained `description` field.
      const npcIdentity = npc.description || npc.occupation || npc.role || '';

      html += `<div class="panel-list-item npc-entry">
        ${npcAvatarImg(npc)}
        <div class="npc-info">
          <div><span class="cyan" style="font-weight:bold">${esc(npc.name || npc.id || 'Unknown')}</span></div>
          ${npcIdentity ? `<div class="npc-identity">${esc(npcIdentity)}</div>` : ''}
          ${npc.faction ? `<div class="dim">${L('faction')}: <span class="${factionCls}">${esc(npc.faction)}</span></div>` : ''}
          <div>${L('trust')}: <span class="${trustCls}">${trustBar} ${esc(trustDisplay)}</span></div>
          ${npc.location_last_seen ? `<div class="dim">${L('last_seen')}: ${esc(npc.location_last_seen)}</div>` : ''}
          ${npc.quest_status && npc.quest_status !== 'none' ? `<div class="dim">${L('quest')}: ${esc(Array.isArray(npc.quest_status) ? npc.quest_status.join(', ') : npc.quest_status)}</div>` : ''}
          ${npc.notes ? `<div class="dim">${esc(npc.notes)}</div>` : ''}
        </div>
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
      const statusLower = (d.status || '').toLowerCase();
      const isOpen = statusLower === 'open' || d.status === '开放';
      const isRestricted = statusLower === 'restricted' || d.status === '限制出入';
      const icon = isOpen ? '\u25C6' : (isRestricted ? '\u25D4' : '\u25CB');
      const statusColor = isOpen ? 'green' : (isRestricted ? 'yellow' : 'red');
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
  document.getElementById('panel-log-body').innerHTML = html;
  applyPanelSearch('log');
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
      let tokenHtml = '';
      if (entry.tokens && _showTokens()) {
        const t = entry.tokens;
        const cost = typeof t.cost === 'number' ? t.cost : 0;
        tokenHtml = `<span class="conv-tokens">${(t.total || 0).toLocaleString()} tok · ${_formatCost(cost)}</span>`;
      }
      html += `<div class="conv-entry">
        <div class="conv-header"><span class="dim">T${entry.turn || '?'}</span> <span class="${roleCls}">${roleLabel}</span>${tokenHtml}</div>
        <div class="conv-content">${esc(entry.content || '')}</div>
      </div>`;
    }
  }
  html += `</div>`;
  document.getElementById('panel-conversation-body').innerHTML = html;
  applyPanelSearch('conversation');
}

// ================================================================
// PANEL SEARCH — filter + highlight in KNOW / TRACE / LOG / CONV
// ================================================================

// Each searchable panel maps to the record element it filters and the section
// wrapper that should collapse when none of its records survive the filter.
const PANEL_SEARCH_RECORDS = {
  knowledge:    '.panel-list-item',
  traces:       '.trace-item',
  log:          '.log-entry',
  conversation: '.conv-entry',
};

function onPanelSearch(key) {
  applyPanelSearch(key);
}

function clearPanelSearch(key) {
  const input = document.getElementById('search-' + key);
  if (input) input.value = '';
  applyPanelSearch(key);
  if (input) input.focus();
}

// Re-run the active query against the freshly rendered body. Called after every
// panel re-render (so highlighting/filtering survives session updates) and on
// every keystroke. Reads the live input value as the source of truth.
function applyPanelSearch(key) {
  const sel = PANEL_SEARCH_RECORDS[key];
  const body = document.getElementById('panel-' + key + '-body');
  const input = document.getElementById('search-' + key);
  if (!sel || !body) return;
  const query = (input ? input.value : '').trim().toLowerCase();

  // Toggle the clear (✕) button visibility.
  const wrap = input && input.closest('.panel-search');
  if (wrap) wrap.classList.toggle('has-query', !!query);

  // Reset: drop old highlights, un-hide everything, collapse any entries WE
  // auto-expanded for a prior search (manual expands have no marker), remove
  // old "no results".
  _clearHighlights(body);
  body.querySelectorAll('.search-expanded').forEach(el => el.classList.remove('expanded', 'search-expanded'));
  body.querySelectorAll(sel).forEach(el => { el.style.display = ''; });
  body.querySelectorAll('.panel-section, .panel-empty').forEach(el => { el.style.display = ''; });
  const oldMsg = body.querySelector('.search-no-results');
  if (oldMsg) oldMsg.remove();

  if (!query) return;  // empty query → default full view

  // Filter records and highlight matches in the survivors.
  let visible = 0;
  body.querySelectorAll(sel).forEach(rec => {
    if (rec.textContent.toLowerCase().includes(query)) {
      rec.style.display = '';
      // Log entries hide their matched text in a collapsed body — open it so
      // the highlight is visible (tag it so we can collapse it again on reset).
      if (key === 'log' && !rec.classList.contains('expanded')) {
        rec.classList.add('expanded', 'search-expanded');
      }
      _highlightTextNodes(rec, query);
      visible++;
    } else {
      rec.style.display = 'none';
    }
  });

  // Empty-state placeholders ("None discovered") are noise during a search.
  body.querySelectorAll('.panel-empty').forEach(el => { el.style.display = 'none'; });

  // Collapse category sections that now show no records (including ones that
  // were always empty), but leave summary headers — sections with neither
  // records nor an empty-state placeholder, e.g. the traces "Discovered N" row.
  body.querySelectorAll('.panel-section').forEach(section => {
    const recs = section.querySelectorAll(sel);
    const hasEmpty = section.querySelector('.panel-empty');
    const anyVisible = Array.from(recs).some(r => r.style.display !== 'none');
    if ((recs.length || hasEmpty) && !anyVisible) {
      section.style.display = 'none';
    }
  });

  if (visible === 0) {
    const msg = document.createElement('div');
    msg.className = 'search-no-results';
    msg.textContent = L('no_search_results');
    body.appendChild(msg);
  }
}

// Wrap case-insensitive occurrences of `query` in <mark> within an element's
// text nodes only — never touches element tags, so escaped HTML stays intact.
function _highlightTextNodes(root, query) {
  if (!query) return;
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
    acceptNode(node) {
      if (!node.nodeValue || !node.nodeValue.toLowerCase().includes(query)) return NodeFilter.FILTER_REJECT;
      if (node.parentNode && node.parentNode.nodeName === 'MARK') return NodeFilter.FILTER_REJECT;
      return NodeFilter.FILTER_ACCEPT;
    }
  });
  const targets = [];
  while (walker.nextNode()) targets.push(walker.currentNode);
  for (const node of targets) {
    const text = node.nodeValue;
    const lower = text.toLowerCase();
    const frag = document.createDocumentFragment();
    let i = 0, idx;
    while ((idx = lower.indexOf(query, i)) !== -1) {
      if (idx > i) frag.appendChild(document.createTextNode(text.slice(i, idx)));
      const mark = document.createElement('mark');
      mark.className = 'search-hl';
      mark.textContent = text.slice(idx, idx + query.length);
      frag.appendChild(mark);
      i = idx + query.length;
    }
    if (i < text.length) frag.appendChild(document.createTextNode(text.slice(i)));
    node.parentNode.replaceChild(frag, node);
  }
}

// Unwrap every highlight back to plain text and re-merge split text nodes.
function _clearHighlights(root) {
  root.querySelectorAll('mark.search-hl').forEach(m => {
    const parent = m.parentNode;
    if (!parent) return;
    parent.replaceChild(document.createTextNode(m.textContent), m);
    parent.normalize();
  });
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

function setText(id, text, childSel) {
  const el = document.getElementById(id);
  if (!el) return;
  if (childSel) { const c = el.querySelector(childSel); if (c) c.textContent = text || ''; }
  else el.textContent = text || '';
}
function esc(text) { return escapeHtml(text || ''); }
function escapeHtml(text) { if (!text) return ''; const d = document.createElement('div'); d.textContent = String(text); return d.innerHTML; }

function dangerColor(level) {
  const l = (level || '').toLowerCase();
  if (l === 'safe' || l === '安全') return 'green';
  if (l === 'low' || l === '低') return 'yellow';
  if (l === 'medium' || l === 'moderate' || l === '中') return 'orange';
  if (l === 'high' || l === '高') return 'red';
  if (l === 'critical' || l === 'extreme' || l === '极端') return 'alert-critical';
  return 'cyan';
}

function alertColor(status) {
  const s = (status || '').toLowerCase();
  if (s === 'calm' || s === '平静') return 'alert-calm';
  if (s === 'watchful' || s === 'low' || s === '警觉') return 'alert-low';
  if (s === 'alert' || s === 'medium' || s === 'elevated' || s === '戒备') return 'alert-medium';
  if (s === 'manhunt' || s === 'high' || s === '追捕') return 'alert-high';
  if (s === 'lockdown' || s === 'critical' || s === '戒严') return 'alert-critical';
  return '';
}

// ================================================================
// KEYBOARD SHORTCUTS
// ================================================================

document.addEventListener('keydown', (e) => {
  if (document.getElementById('gameScreen').classList.contains('active')) {
    // Check if any overlay dialog is open — only allow Escape when overlays are visible
    const overlayOpen = ['settingsOverlay', 'confirmMenuDialog', 'saveDialog'].some(
      id => { const el = document.getElementById(id); return el && el.style.display !== 'none' && el.style.display !== ''; }
    );
    if (e.key === 'Escape') {
      if (companionOpen) { closeCompanion(); return; }
      closeSaveDialog(); closeSettings(); closeConfirmMenu(); return;
    }
    // Block all other keybindings when an overlay is open
    if (overlayOpen) return;

    // Don't let game shortcuts fire while typing in ANY field (chat, companion,
    // or the panel search bars) — number keys must type, not switch tabs.
    const active = document.activeElement;
    const isInput = !!active && (
      active.tagName === 'INPUT' ||
      active.tagName === 'TEXTAREA' ||
      active.isContentEditable
    );
    const num = parseInt(e.key);
    if (num >= 1 && num <= 9 && !e.ctrlKey && !e.metaKey && !isInput) {
      const tabs = document.querySelectorAll('.panel-tab');
      if (tabs[num - 1]) { switchPanel(tabs[num - 1]); e.preventDefault(); }
    }
    if (e.key === 't' && !isInput) { document.getElementById('chatInput').focus(); e.preventDefault(); }
    if (e.key === 's' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); saveGame(); }
  }
});

// ================================================================
// STARTUP
// ================================================================

window.addEventListener('load', () => {
  // Restore saved UI language before boot
  const savedLang = localStorage.getItem('signal_lost_ui_lang');
  if (savedLang && (savedLang === 'en' || savedLang === 'zh')) {
    setLanguage(savedLang);
  }
  runBootSequence();
});

// Start music on first user interaction (browsers require gesture for AudioContext)
function _initMusicOnce() {
  if (audioCtx.state === 'suspended') audioCtx.resume();
  // Only play menu music if we're on a menu screen; skip if already in-game
  const onMenu = ['menuScreen', 'bootScreen', 'newGameScreen', 'loadGameScreen']
    .some(id => { const el = document.getElementById(id); return el && el.classList.contains('active'); });
  if (onMenu) MusicEngine.playMenu();
  MusicEngine.preloadAll();
  document.removeEventListener('click', _initMusicOnce);
  document.removeEventListener('keydown', _initMusicOnce);
}
document.addEventListener('click', _initMusicOnce, { once: false });
document.addEventListener('keydown', _initMusicOnce, { once: false });
