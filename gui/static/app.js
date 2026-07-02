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

// ----------------------------------------------------------------
// BANDED-GAUGE THRESHOLDS — mirror engine/game_data.py
// ALERT_THRESHOLDS / DECAY_THRESHOLDS (do NOT edit game_data.py; copy only).
// Each entry: threshold + bilingual escalation effect for the WORLD-panel caption.
// ----------------------------------------------------------------
const ALERT_THRESHOLDS = [
  { threshold: 25,  effect: 'Increased patrols in Sector 7 and Chrome Heights', effect_zh: '第七区和镀金台巡逻增加' },
  { threshold: 50,  effect: 'Sector 7 lockdown, Chrome Heights restricted',      effect_zh: '第七区封锁，镀金台限制出入' },
  { threshold: 75,  effect: 'NEXUS raids Undercroft, Neon Row restricted',       effect_zh: 'NEXUS突袭底渊，霓虹街限制出入' },
  { threshold: 90,  effect: 'Full manhunt, only The Sprawl is safe',             effect_zh: '全城搜捕，仅蔓城尚属安全' },
  // In-world phrasing only — do NOT name ending/branch outcomes here (that would
  // leak meta-information the narrative never states). Softened from game_data's
  // 'Capture — funneled to Order ending or death'.
  { threshold: 100, effect: 'Capture is all but certain',                        effect_zh: '被捕几乎无可避免' },
];
const DECAY_THRESHOLDS = [
  { threshold: 25,  effect: 'Echo manifestations weaker',      effect_zh: '回响显现减弱' },
  { threshold: 50,  effect: 'Signal artifacts lose potency',   effect_zh: '信号遗物失去效力' },
  // In-world phrasing only — do NOT name ending outcomes ('good endings') here.
  // Softened from game_data's 'Good endings much harder' / 'impossible'.
  { threshold: 75,  effect: 'The signal frays past recovery',  effect_zh: '信号残缺，几近无法复原' },
  { threshold: 100, effect: 'The signal is all but lost',      effect_zh: '信号近乎彻底湮灭' },
];

// Tick positions (%) for the banded mini-gauges and the cyan→yellow→orange→red ramp.
const GAUGE_TICKS = [25, 50, 75, 90];
// value (0-100) → CSS var color for the fill. Bands: <25 cyan, <50 yellow, <75 orange, ≥75 red.
function gaugeBandColor(v) {
  if (v >= 75) return 'var(--red)';
  if (v >= 50) return 'var(--orange)';
  if (v >= 25) return 'var(--yellow)';
  return 'var(--cyan)';
}
/** Nearest escalation AT-OR-ABOVE the current value, for the "next: X at N" caption.
 *  Returns {threshold, effect, effect_zh} or null if already at/above the top band. */
function nextEscalation(thresholds, value) {
  for (const t of thresholds) {
    if (value < t.threshold) return t;
  }
  return null;
}
/** Localized escalation effect text for a threshold entry. */
function escalationEffect(entry) {
  if (!entry) return '';
  return (currentLang === 'zh' && entry.effect_zh) ? entry.effect_zh : entry.effect;
}

/** One-line band caption: current band consequence + next escalation, bilingual.
 *  e.g. "Watchful · next: Sector 7 lockdown, Chrome Heights restricted at 50".
 *  `statusDisplay` is already localized (server status_zh or label map) and safe
 *  to escape here. Returns an escaped HTML fragment. */
function bandCaption(thresholds, value, statusDisplay) {
  const v = Math.max(0, Math.min(100, Number(value) || 0));
  const nxt = nextEscalation(thresholds, v);
  const head = esc(statusDisplay || '');
  if (!nxt) {
    // Already in the top band — no further escalation to warn about.
    return `<div class="band-caption dim">${head} · ${esc(L('hud_band_max'))}</div>`;
  }
  const eff = escalationEffect(nxt);
  // "next: <effect> at <threshold>" / "下一级：<effect> @ <threshold>"
  const nextLbl = esc(L('hud_next'));
  return `<div class="band-caption dim">${head} · ${nextLbl}: ${esc(eff)} @ ${nxt.threshold}</div>`;
}

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
    // Trace Ladder — descent gauge + layer bands (flavor names bilingual;
    // the traces.json scaffold ships English-only, so names route through L()).
    descent: 'DESCENT', trace_locked: 'LOCKED',
    trace_layer_1: 'The Surface', trace_layer_2: 'The Conspiracy',
    trace_layer_3: 'The Severance Truth', trace_layer_4: 'The Mirror',
    trace_layer_5: 'The Full Truth',
    // Toasts + discovery ceremony
    toast_dismiss: 'Dismiss',
    toast_more: 'more',
    trace_uncovered: 'TRACE UNCOVERED',
    kn_fact: 'New fact discovered', kn_rumor: 'New rumor discovered',
    kn_evidence: 'New evidence collected', kn_theory: 'New theory formed',
    kn_connection: 'New connection found',
    // Roll chip — inline mechanical beat before narration (optional frame)
    roll_success: 'SUCCESS', roll_failure: 'FAILURE',
    roll_vs: 'vs', roll_modifiers: 'Modifiers',
    // Meter "why" — one-line cause under a HUD/WORLD meter that moved
    meter_why: 'why',
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
    hud_nexus: 'NEXUS', hud_signal: 'SIGNAL', hud_time: 'TIME',
    hud_day: 'Day', hud_next: 'next', hud_band_max: 'critical band',
    hud_coherence: 'SIGNAL COHERENCE',
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
    diff_paranoid: 'Easy', diff_cautious: 'Normal',
    diff_standard: 'Standard', diff_reckless: 'Very Hard',
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
    no_usage_data: 'No usage data yet',
    settings_audio_title: '// AUDIO', label_music_volume: 'MUSIC VOLUME',
    label_sfx_volume: 'SFX VOLUME',
    settings_gameplay_title: '// GAMEPLAY',
    label_suggested_actions: 'Suggest actions each turn',
    label_predict_outcome: 'Pre-compute suggested actions (instant replies, extra LLM calls)',
    btn_close: 'CLOSE',
    settings_saved: 'Settings saved', saving: 'Saving...', saved: 'Saved',
    tokens_unit: 'tokens', tokens_short: 'tok',
    // Usage stats (settings overlay)
    usage_llm_calls: 'LLM calls', usage_input: 'Input', usage_output: 'Output',
    usage_total: 'Total', usage_cost: 'Cost',
    // Data panels drawer + nav menu (game chrome)
    data_panels: '// DATA PANELS',
    nav_tutorial: 'Tutorial', nav_save: 'Save Game',
    nav_settings: 'Settings', nav_menu: 'Main Menu',
    nav_info_panels: 'Info Panels', nav_menu_tip: 'Menu',
    // Suggested-action chip tooltips (predict_outcome)
    sa_ready: 'ready (instant)', sa_pending: 'pre-computing…',
    // Death-cause endings
    death_collapse: 'NEURAL COLLAPSE', death_capture: 'CAPTURED BY NEXUS',
    death_unknown: 'DEATH',
    death_reconnect_nudge: '— You can RECONNECT from an autosave (every 5 turns) or a manual save.',
    // Chat prefixes
    chat_player: '\u25B6 PLAYER', chat_agent: '\u25C0 SIGNAL LOST', chat_system: '\u25CF SYSTEM',
    // Game over
    game_over_reconnect: 'RECONNECT', game_over_fallback: '// CONNECTION TERMINATED',
    // Connection
    connection_lost: 'Connection lost. Reconnecting...',
    reconnecting_inline: '// link dropped — reconnecting… your input is held',
    link_quiet: '// the link went quiet — no reply came back. Retry your last action?',
    skip_hint: '▸ skip',
    // Error-recovery UX (wave 2c)
    busy_no_confirm: "didn't confirm — try again",
    retry_last_action: '↻ Retry last action',
    conn_degraded: '// link degraded — reconnecting…',
    error_generic: 'Something went wrong. Try again.',
    // Accounts / auth
    auth_title: '// ACCESS TERMINAL',
    auth_sign_in: 'SIGN IN', auth_register: 'REGISTER', auth_sign_out: 'SIGN OUT',
    auth_username: 'USERNAME', auth_password: 'PASSWORD',
    auth_username_placeholder: 'Enter a username',
    auth_password_placeholder: 'Enter a password',
    auth_signed_in_as: 'Signed in as', auth_signed_out: 'Signed out',
    auth_err_username_required: 'Enter a username.',
    auth_err_password_required: 'Enter a password.',
    auth_err_username_taken: 'That username is taken.',
    auth_err_username_too_long: 'Username is too long (max 32).',
    auth_err_username_invalid: 'Username has invalid characters.',
    auth_err_password_too_short: 'Password must be at least 4 characters.',
    auth_err_invalid_credentials: 'Wrong username or password.',
    auth_err_generic: 'Could not sign in. Try again.',
    conflict_title: '// ACCOUNT ALREADY ACTIVE',
    conflict_text: 'This account is already signed in on another session. Continue here and disconnect the other one?',
    conflict_yes: 'CONTINUE HERE', conflict_no: 'CANCEL',
    kicked_title: '// SESSION ENDED',
    kicked_text: 'This account was opened in another session. You have been signed out here.',
    kicked_reload: 'RECONNECT',
    // Tutorial
    tutorial_step: 'STEP', tutorial_skip: 'SKIP', tutorial_next: 'NEXT', tutorial_finish: 'GOT IT',
    // Empty-state teaching hints (second line under each .panel-empty).
    // Spoiler-safe: they describe the loop, never undiscovered content.
    empty_trace: 'No traces discovered yet.',
    empty_trace_hint: 'Discoveries appear here, grouped by depth. ▓ = sealed truths.',
    empty_know: 'Nothing learned yet.',
    empty_know_hint: 'Rumors you verify become facts.',
    empty_npc_hint: 'Contacts you meet — and how far they trust you.',
    empty_area: 'No districts mapped yet.',
    empty_area_hint: 'Districts unlock as you travel and earn access.',
    empty_items_hint: 'Gear you pick up lives here — slots are limited.',
    empty_world_hint: 'Alerts and shifts across the city surface here.',
    empty_log_hint: 'A running recap of what you have done.',
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
    companion_timeout: 'The signal fades to silence — no answer came back. Try again.',
    companion_offline: 'The main link is down. Reconnect to the city before the implant can reach it.',
    // Boot
    boot_sub: '// NEURAL INTERFACE v3.7.1',
    // Input history + verb autocomplete + shortcut cheat-sheet (wave 3b)
    verb_look: 'look', verb_go: 'go', verb_talk: 'talk', verb_examine: 'examine',
    verb_use: 'use', verb_verify: 'verify', verb_hack: 'hack', verb_hide: 'hide',
    shortcuts_title: '// SHORTCUTS',
    shortcut_panels: 'Switch info panel',
    shortcut_focus_input: 'Focus command input',
    shortcut_save: 'Save game',
    shortcut_skip: 'Skip / finish narration',
    shortcut_history: 'Previous / next command',
    shortcut_complete: 'Complete verb suggestion',
    shortcut_cheatsheet: 'Show this cheat-sheet',
    shortcut_close_dialog: 'Close dialog / menu',
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
    descent: '深潜', trace_locked: '未解封',
    trace_layer_1: '表层', trace_layer_2: '阴谋',
    trace_layer_3: '断离真相', trace_layer_4: '镜像',
    trace_layer_5: '完整真相',
    toast_dismiss: '关闭',
    toast_more: '更多',
    trace_uncovered: '痕迹揭示',
    kn_fact: '新事实已记录', kn_rumor: '新传闻已记录',
    kn_evidence: '新证据已收集', kn_theory: '新理论已形成',
    kn_connection: '新关联已发现',
    // Roll chip — inline mechanical beat before narration (optional frame)
    roll_success: '成功', roll_failure: '失败',
    roll_vs: '对', roll_modifiers: '修正',
    // Meter "why" — one-line cause under a HUD/WORLD meter that moved
    meter_why: '原因',
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
    hud_nexus: '连结', hud_signal: '信号', hud_time: '时间',
    hud_day: '第', hud_next: '下一级', hud_band_max: '危险区间',
    hud_coherence: '信号一致性',
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
    diff_paranoid: '简单', diff_cautious: '普通',
    diff_standard: '标准', diff_reckless: '极难',
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
    no_usage_data: '暂无用量数据',
    settings_audio_title: '// 音频', label_music_volume: '音乐音量',
    label_sfx_volume: '音效音量',
    settings_gameplay_title: '// 玩法',
    label_suggested_actions: '每回合推荐行动',
    label_predict_outcome: '预计算推荐行动（点击即时响应，但会增加 LLM 调用）',
    btn_close: '关闭',
    settings_saved: '设置已保存', saving: '保存中...', saved: '已保存',
    tokens_unit: '令牌', tokens_short: '令牌',
    // Usage stats (settings overlay)
    usage_llm_calls: '调用次数', usage_input: '输入', usage_output: '输出',
    usage_total: '合计', usage_cost: '花费',
    // Data panels drawer + nav menu (game chrome)
    data_panels: '// 数据面板',
    nav_tutorial: '教程', nav_save: '保存游戏',
    nav_settings: '设置', nav_menu: '主菜单',
    nav_info_panels: '信息面板', nav_menu_tip: '菜单',
    // Suggested-action chip tooltips (predict_outcome)
    sa_ready: '即时', sa_pending: '预计算中…',
    // Death-cause endings
    death_collapse: '神经崩溃', death_capture: '被NEXUS擒获',
    death_unknown: '死亡',
    death_reconnect_nudge: '— 你可以从自动存档（每5回合）或手动存档重新连接。',
    // Chat prefixes
    chat_player: '\u25B6 玩家', chat_agent: '\u25C0 信号遗失', chat_system: '\u25CF 系统',
    // Game over
    game_over_reconnect: '重新连接', game_over_fallback: '// 连接已终止',
    // Connection
    connection_lost: '连接已断开，正在重连...',
    reconnecting_inline: '// 链路中断 —— 正在重连…你的输入已保留',
    link_quiet: '// 链路陷入沉默 —— 没有收到回应。重试上一步操作？',
    skip_hint: '▸ 跳过',
    // Error-recovery UX (wave 2c)
    busy_no_confirm: '未收到确认 —— 请重试',
    retry_last_action: '↻ 重试上一动作',
    conn_degraded: '// 链路降级 —— 正在重连…',
    error_generic: '发生错误，请重试。',
    // Accounts / auth
    auth_title: '// 接入终端',
    auth_sign_in: '登录', auth_register: '注册', auth_sign_out: '退出登录',
    auth_username: '用户名', auth_password: '密码',
    auth_username_placeholder: '请输入用户名',
    auth_password_placeholder: '请输入密码',
    auth_signed_in_as: '已登录为', auth_signed_out: '已退出登录',
    auth_err_username_required: '请输入用户名。',
    auth_err_password_required: '请输入密码。',
    auth_err_username_taken: '该用户名已被占用。',
    auth_err_username_too_long: '用户名过长（最多32个字符）。',
    auth_err_username_invalid: '用户名包含无效字符。',
    auth_err_password_too_short: '密码至少需要4个字符。',
    auth_err_invalid_credentials: '用户名或密码错误。',
    auth_err_generic: '登录失败，请重试。',
    conflict_title: '// 账号已在使用',
    conflict_text: '该账号已在另一个会话中登录。是否在此处继续并断开另一个会话？',
    conflict_yes: '在此处继续', conflict_no: '取消',
    kicked_title: '// 会话已结束',
    kicked_text: '该账号已在另一个会话中打开，你已在此处登出。',
    kicked_reload: '重新连接',
    // Tutorial
    tutorial_step: '步骤', tutorial_skip: '跳过', tutorial_next: '下一步', tutorial_finish: '知道了',
    // Empty-state teaching hints (second line under each .panel-empty).
    empty_trace: '尚未发现任何痕迹。',
    empty_trace_hint: '发现的痕迹按深度分层显示。▓ = 封存的真相。',
    empty_know: '尚无所得。',
    empty_know_hint: '你核实的传闻会成为事实。',
    empty_npc_hint: '你遇见的联系人——以及他们对你的信任程度。',
    empty_area: '尚未探明任何区域。',
    empty_area_hint: '随着你的行动与取得权限，区域会逐步解锁。',
    empty_items_hint: '拾取的装备会存放于此——槽位有限。',
    empty_world_hint: '全城的警报与变动会在此浮现。',
    empty_log_hint: '你所作所为的实时回顾。',
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
    companion_timeout: '信号渐渐归于沉寂——没有回应传回。请再试一次。',
    companion_offline: '主链路已中断。请先重新连接城市，植入体才能接入。',
    // Boot
    boot_sub: '// 神经接口 v3.7.1',
    // Input history + verb autocomplete + shortcut cheat-sheet (wave 3b)
    verb_look: '查看', verb_go: '前往', verb_talk: '交谈', verb_examine: '检查',
    verb_use: '使用', verb_verify: '核实', verb_hack: '入侵', verb_hide: '躲藏',
    shortcuts_title: '// 快捷键',
    shortcut_panels: '切换信息面板',
    shortcut_focus_input: '聚焦指令输入框',
    shortcut_save: '保存游戏',
    shortcut_skip: '跳过／完成叙述',
    shortcut_history: '上一条／下一条指令',
    shortcut_complete: '补全动词建议',
    shortcut_cheatsheet: '显示此快捷键表',
    shortcut_close_dialog: '关闭对话框／菜单',
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

/** Walk every keyed element and set its text/placeholder from LABELS.
 *  This is the single source of truth for static chrome — [data-i18n] sets
 *  textContent, [data-i18n-placeholder] sets the placeholder attribute. New
 *  strings only need the attribute in index.html + a LABELS entry; no per-
 *  element JS. Dynamic labels (title/dataset.text, toggled submit labels,
 *  per-render panels) keep their bespoke handlers below. */
function applyStaticI18n(root) {
  const scope = root || document;
  scope.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.dataset.i18n;
    if (key) el.textContent = L(key);
  });
  scope.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
    const key = el.dataset.i18nPlaceholder;
    if (key) el.placeholder = L(key);
  });
}

/** Set the UI language and refresh everything */
function setLanguage(lang) {
  currentLang = lang;
  localStorage.setItem('signal_lost_ui_lang', lang);
  // Single-pass: every element carrying a data-i18n / data-i18n-placeholder key
  // (menu, new-game, load, settings, all dialogs, panel tabs, drawer, auth) is
  // updated from LABELS. Bespoke handlers below cover only what can't be keyed.
  applyStaticI18n();
  // Reflect language on <html> for correct CJK line-breaking, font selection
  // (html[lang="zh"] tuning) and screen-reader pronunciation.
  document.documentElement.lang = lang === 'zh' ? 'zh' : 'en';
  // Language selectors sync from one source of truth (currentLang): the menu
  // dropdown and the new-game session-language select both reflect the UI lang.
  const menuLangSel = document.getElementById('selectMenuLanguage');
  if (menuLangSel) menuLangSel.value = lang;
  // Error-recovery chrome (wave 2c): relabel the degraded chip, any inline
  // "didn't confirm" notes, and standing retry cards on a language switch.
  if (_connChipEl) _connChipEl.textContent = L('conn_degraded');
  document.querySelectorAll('.busy-note').forEach(n => { n.textContent = L('busy_no_confirm'); });
  document.querySelectorAll('.retry-card-btn .cyber-btn-text').forEach(b => { b.textContent = L('retry_last_action'); });
  // Implant companion chrome (sets titles/placeholders — not data-i18n-able)
  applyCompanionLanguage();
  // Input-history verb chips (wave 3b): drop the stale-language build so the
  // next focus/input re-renders localized chips; refresh a visible cheat-sheet.
  const _verbRow = document.getElementById('verbChips');
  if (_verbRow) { _verbRow.dataset.built = ''; const ci = document.getElementById('chatInput'); if (ci && typeof _updateVerbChips === 'function') _updateVerbChips(ci); }
  if (typeof _renderShortcutSheet === 'function') _renderShortcutSheet();
  // Wait ticker: if mid-cycle, re-render its current line in the new language;
  // otherwise fall back to the resting label. (.thinking-text is a live ticker,
  // .thinkingHint is static so data-i18n could own it, but it shares this block.)
  const thinkingText = document.querySelector('.thinking-text');
  if (thinkingText) thinkingText.textContent = (_thinkingTimer || _thinkingLineIdx > 0) ? _thinkingLineText() : L('processing');
  const thinkingHint = document.getElementById('thinkingHint');
  if (thinkingHint) thinkingHint.textContent = L('thinking_hint');

  // Game title (boot logo, menu h1, game over h1) — each needs dataset.text too
  // for the glitch effect, so these stay bespoke rather than plain data-i18n.
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

  // Menu footer carries a leading <span class="blink">, so it's rebuilt here
  // rather than keyed (data-i18n would clobber the span).
  const menuFooter = document.querySelector('.menu-footer');
  if (menuFooter) menuFooter.innerHTML = '<span class="blink">_</span> ' + L('menu_footer');

  // Account widget + auth dialog (renders widget + toggles submit label)
  applyAuthLanguage();

  // New game screen: default character-name/alias values track the language
  // only while the player hasn't customized them (placeholders are data-i18n).
  const inputName = document.getElementById('inputName');
  if (inputName) {
    const defaults = { en: 'Kael', zh: '凯尔' };
    const oldDefaults = Object.values(defaults);
    if (!inputName.value || oldDefaults.includes(inputName.value)) {
      inputName.value = defaults[lang] || defaults.en;
    }
  }
  const inputAlias = document.getElementById('inputAlias');
  if (inputAlias) {
    const defaults = { en: 'Ghost', zh: '幽灵' };
    const oldDefaults = Object.values(defaults);
    if (!inputAlias.value || oldDefaults.includes(inputAlias.value)) {
      inputAlias.value = defaults[lang] || defaults.en;
    }
  }
  // Sync session language selector with UI language (source of truth: currentLang)
  const selectLang = document.getElementById('selectLanguage');
  if (selectLang) selectLang.value = lang;
  // Background select buttons. The subtitle must stay in the CURRENT language —
  // it used to show the Chinese name even in EN mode (a visible i18n leak), so
  // use a short same-language role tagline instead of the other-language name.
  const bgNames = {
    en: { street_runner: 'Street Runner', corporate_exile: 'Corporate Exile', netrunner: 'Netrunner' },
    zh: { street_runner: '街头行者', corporate_exile: '企业流亡者', netrunner: '网行者' },
  };
  const bgTagline = {
    en: { street_runner: 'Street ops · black markets · debts',
          corporate_exile: 'Insider turned fugitive',
          netrunner: 'Deep-dive hacker · signal-chaser' },
    zh: { street_runner: '街头生存 · 黑市 · 债务',
          corporate_exile: '叛逃的内部人',
          netrunner: '深潜黑客 · 信号追猎者' },
  };
  document.querySelectorAll('.cyber-select').forEach(btn => {
    const bg = btn.dataset.bg;
    const nameEl = btn.querySelector('.select-name');
    const descEl = btn.querySelector('.select-desc');
    if (bg && nameEl && descEl) {
      const l = (lang === 'zh') ? 'zh' : 'en';
      nameEl.textContent = (bgNames[l][bg]) || bg;
      descEl.textContent = (bgTagline[l][bg]) || '';
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
  // NOTE: new-game labels/buttons, load-screen, save/confirm/settings/auth
  // dialogs, panel tabs, panel-search + input placeholders, and all
  // data-i18n[-placeholder] chrome are already localized by applyStaticI18n()
  // at the top of this function — no per-element handlers needed here.

  // Status bar: info-panel toggle tooltip + nav menu tooltips. These are title
  // ATTRIBUTES on the icon buttons (not visible text), so they can't ride
  // data-i18n; the nav-menu ITEM labels are keyed in HTML and handled above.
  const infoBtn = document.getElementById('btnInfoPanels');
  if (infoBtn) infoBtn.title = L('nav_info_panels');
  const navBtn = document.getElementById('btnNavMenu');
  if (navBtn) navBtn.title = L('nav_menu_tip');

  // Re-render all panels if we have cached session
  if (cachedSession) updateAllPanels(cachedSession);
}

let cachedSession = null; // Store last session for re-render on language change

// ================================================================
// PARTICLE SYSTEM
// ================================================================

// Read the reduced-motion preference once. When set, we skip the ambient
// particle/glitch loops entirely (CSS also neutralizes keyframe animations).
const prefersReducedMotion = window.matchMedia
  && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

const canvas = document.getElementById('particles');
const ctx = canvas.getContext('2d');
let particles = [];
let mouseX = 0, mouseY = 0;
let _particleRAF = null;

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
  _particleRAF = requestAnimationFrame(animateParticles);
}

function startParticles() {
  if (prefersReducedMotion || _particleRAF !== null) return;
  _particleRAF = requestAnimationFrame(animateParticles);
}

function stopParticles() {
  if (_particleRAF !== null) { cancelAnimationFrame(_particleRAF); _particleRAF = null; }
}

// Skip the ambient particle field entirely for reduced-motion users.
if (!prefersReducedMotion) startParticles();

// Pause the rAF loop while the tab is hidden and resume on return
// (mirrors MusicEngine's visibility handling) to save CPU/battery.
document.addEventListener('visibilitychange', () => {
  if (document.hidden) stopParticles();
  else startParticles();
});

document.addEventListener('mousemove', e => { mouseX = e.clientX; mouseY = e.clientY; });

// ================================================================
// GLITCH & AUDIO
// ================================================================

function triggerGlitch() {
  const o = document.getElementById('glitchOverlay');
  o.classList.remove('active'); void o.offsetWidth; o.classList.add('active');
  setTimeout(() => o.classList.remove('active'), 200);
}
// The ambient random-glitch flash is decorative; skip it for reduced-motion users.
if (!prefersReducedMotion) {
  setInterval(() => { if (Math.random() < 0.15) triggerGlitch(); }, 5000);
}

// SFX now live on ONE bus inside MusicEngine (single mute state + persisted
// SFX-volume slider). playBeep is a thin category-tagged shim over
// MusicEngine.sfx so every existing call site keeps working; the bus itself
// honours mute, so the scattered `_musicMuted()` guards around beeps are gone.
//   category: 'ui' (default) | 'ambient' | 'discovery'
function playBeep(freq = 880, duration = 0.05, volume = 0.03, category = 'ui') {
  if (typeof MusicEngine === 'undefined' || typeof MusicEngine.sfx !== 'function') return;
  MusicEngine.sfx(freq, duration, volume, category);
}

// ================================================================
// NOTIFICATION & SCREEN MANAGEMENT
// ================================================================

// ================================================================
// UNIFIED TOAST STACK
// One flex-column host (#toastStack) owns every transient notification:
// system notices (notify), knowledge-added toasts, and future kinds. Natural
// flex stacking — no hardcoded height math. The companion FAB keeps its own
// bottom-right lane; the stack sits bottom-center (top-center on narrow
// viewports, handled purely in CSS).
// ================================================================
const TOAST_MAX_VISIBLE = 4;   // cap simultaneous toasts; rest counted as overflow
let _toastOverflow = 0;        // how many toasts were suppressed while at cap

function _toastStack() { return document.getElementById('toastStack'); }

/** Update / show / hide the "+N more" overflow chip at the top of the stack. */
function _renderToastOverflow() {
  const stack = _toastStack();
  if (!stack) return;
  let chip = stack.querySelector('.toast-overflow');
  if (_toastOverflow > 0) {
    if (!chip) {
      chip = document.createElement('div');
      chip.className = 'toast-overflow';
      stack.insertBefore(chip, stack.firstChild);
    }
    chip.textContent = '+' + _toastOverflow + ' ' + L('toast_more');
  } else if (chip) {
    chip.remove();
  }
}

/**
 * Route a transient notification through the single stack.
 *   kind : 'info' | 'error' | 'knowledge' (accent styling only)
 *   html : pre-escaped HTML string for the body (callers MUST esc() interpolations)
 *   opts : { duration=3000 }
 */
function addToast(kind, html, opts = {}) {
  const stack = _toastStack();
  if (!stack) return null;
  const visible = stack.querySelectorAll('.toast').length;
  if (visible >= TOAST_MAX_VISIBLE) {
    // At cap — count this one as overflow rather than piling up off-screen.
    _toastOverflow++;
    _renderToastOverflow();
    return null;
  }

  const duration = opts.duration != null ? opts.duration : 3000;
  const el = document.createElement('div');
  el.className = 'toast toast-' + (kind || 'info');
  el.setAttribute('role', kind === 'error' ? 'alert' : 'status');
  el.innerHTML =
    `<span class="toast-body">${html}</span>` +
    `<button class="toast-dismiss" aria-label="${esc(L('toast_dismiss'))}" ` +
    `onclick="dismissToast(this.parentNode)">&times;</button>`;

  stack.appendChild(el);
  _renderToastOverflow();
  requestAnimationFrame(() => el.classList.add('toast-in'));

  // Auto-dismiss timer with pause-on-hover. We track remaining time so a hover
  // mid-life doesn't reset the clock.
  el._remaining = duration;
  el._start = Date.now();
  const arm = () => {
    el._start = Date.now();
    el._timer = setTimeout(() => dismissToast(el), el._remaining);
  };
  el.addEventListener('mouseenter', () => {
    if (el._timer) { clearTimeout(el._timer); el._timer = null; el._remaining -= (Date.now() - el._start); }
  });
  el.addEventListener('mouseleave', () => { if (el._remaining > 0) arm(); });
  arm();
  return el;
}

/** Remove a toast with its exit animation, then drain one overflow slot. */
function dismissToast(el) {
  if (!el || el._dismissing) return;
  el._dismissing = true;
  if (el._timer) { clearTimeout(el._timer); el._timer = null; }
  el.classList.remove('toast-in');
  el.classList.add('toast-out');
  // Registered on BOTH transitionend and a setTimeout fallback, so guard against
  // running twice — otherwise one dismissal would drain two overflow slots.
  let finished = false;
  const fin = () => {
    if (finished) return;
    finished = true;
    if (el.parentNode) el.parentNode.removeChild(el);
    if (_toastOverflow > 0) { _toastOverflow--; _renderToastOverflow(); }
  };
  if (prefersReducedMotion) { fin(); }
  else { el.addEventListener('transitionend', fin, { once: true }); setTimeout(fin, 500); }
}

function notify(text, isError = false) {
  addToast(isError ? 'error' : 'info', esc(text));
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

// --- Auth state -----------------------------------------------------------
let authToken = null;     // session token from register/login (also in localStorage)
let currentUser = null;   // username once the server confirms the bind
let pendingIntent = null; // action to run after a sign-in prompt ('newgame' | 'loadgame')
let conflictUsername = null; // account awaiting a takeover confirmation
let wasKicked = false;    // true after being kicked → stop auto-reconnect

function connectWebSocket() {
  const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
  ws = new WebSocket(`${protocol}://${location.host}/ws`);
  ws.onopen = () => {
    sendInit();
    // If we dropped mid-game and just reconnected, ask the server to repaint the
    // panels/state so stale pre-drop content is refreshed (additive action).
    // The degraded chip stays up until that refresh actually lands (handled in
    // the 'refresh'/full-state message path); with no active game there's
    // nothing to repaint, so clear it right away on reopen.
    if (document.getElementById('gameScreen').classList.contains('active')) {
      sendWS({ action: 'refresh' });
    } else {
      clearConnDegraded();
    }
  };
  ws.onmessage = (event) => {
    let msg;
    try { msg = JSON.parse(event.data); }
    catch (e) { console.warn('[ws] dropping malformed frame', e); return; }
    handleServerMessage(msg);
  };
  ws.onclose = () => {
    if (wasKicked) return;  // kicked elsewhere — don't fight the new session
    // Surface the persistent degraded chip (distinct from transient toasts) so
    // the outage stays visible for the whole reconnect window, not 3 seconds.
    showConnDegraded();
    if (!wsReconnectTimer) wsReconnectTimer = setTimeout(() => { wsReconnectTimer = null; connectWebSocket(); }, 3000);
  };
  ws.onerror = (e) => {
    console.warn('[ws] socket error — link degraded', e);
    // Degraded-state hook: the onclose handler drives reconnection. Raise the
    // persistent chip here too (onerror can fire without an onclose) so the
    // player sees the link is unstable without waiting on a vanishing toast.
    showConnDegraded();
  };
}

/** Send the init/bind handshake, carrying the stored token if we have one. */
function sendInit(force) {
  const payload = { action: 'init' };
  if (authToken) payload.token = authToken;
  if (force) payload.force = true;
  if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(payload));
}

/** Send over the main socket. Returns true if the frame was written, false if
 *  the socket is not open (caller keeps the user's input and shows a notice). */
function sendWS(data) {
  if (ws && ws.readyState === WebSocket.OPEN) { ws.send(JSON.stringify(data)); return true; }
  notify(L('connection_lost'), true);
  return false;
}

/** Whether the main socket is currently open (safe to send a game action). */
function wsOpen() { return !!(ws && ws.readyState === WebSocket.OPEN); }

/** Append an inline, bilingual "reconnecting…" system line to the chat so the
 *  player sees why their input didn't go through. Deduped by showSystemNotice. */
function showReconnectingNotice() {
  showSystemNotice(L('reconnecting_inline'));
}

// ================================================================
// IN-FLIGHT DISCIPLINE — busy() button lock + confirmation-or-timeout
// A button that fires a WS action shouldn't fire again until the server's
// reply lands (double-clicks sent duplicate register/save frames). busy()
// disables the button, shows an inline spinner glyph, and arms a 10s
// watchdog: if the expected reply key never resolves, it re-enables the
// button and drops a bilingual "didn't confirm — try again" note *inline*
// beside it (never a vanishing toast). No overlay is closed on the caller's
// behalf — the caller decides when (and only ever after confirmation).
// ================================================================
const BUSY_TIMEOUT_MS = 10000;
// Live controllers keyed by their confirmation token (a WS reply type). A
// single pending controller per token; a new busy() on the same token
// supersedes the old one so a stale watchdog can't fire against fresh UI.
const _busyByToken = {};

/**
 * Lock a button while a WS round-trip is in flight.
 *   btn   : the <button> element (or null → no-op controller)
 *   token : the WS reply `type` we expect back (e.g. 'saved'); resolveBusy(token)
 *           on arrival re-enables and clears the watchdog. Falsy → caller must
 *           call the returned controller's .done()/.fail() manually.
 * Returns { done, fail } so a synchronous failure (e.g. validation) can release.
 */
function busy(btn, token) {
  if (!btn) return { done() {}, fail() {} };
  // Supersede any prior pending controller on this same button/token.
  if (token && _busyByToken[token]) _busyByToken[token].fail(true);

  const label = btn.querySelector('.cyber-btn-text');
  const prevDisabled = btn.disabled;
  const prevHTML = label ? label.innerHTML : btn.innerHTML;
  btn.disabled = true;
  btn.classList.add('is-busy');
  // Clear any leftover inline note from a previous failed attempt.
  _clearBusyNote(btn);
  const spinner = `<span class="busy-spinner" aria-hidden="true"></span>`;
  if (label) label.innerHTML = spinner + label.innerHTML;
  else btn.innerHTML = spinner + btn.innerHTML;

  let settled = false;
  const restore = () => {
    btn.disabled = prevDisabled;
    btn.classList.remove('is-busy');
    if (label) label.innerHTML = prevHTML; else btn.innerHTML = prevHTML;
  };
  const ctrl = {
    /** Success: silently restore the button, clear the watchdog. */
    done() {
      if (settled) return; settled = true;
      clearTimeout(ctrl._timer);
      if (token && _busyByToken[token] === ctrl) delete _busyByToken[token];
      restore();
    },
    /** Failure/timeout: restore + show the inline retry note. `quiet` skips
     *  the note (used when a newer busy() supersedes this one). */
    fail(quiet) {
      if (settled) return; settled = true;
      clearTimeout(ctrl._timer);
      if (token && _busyByToken[token] === ctrl) delete _busyByToken[token];
      restore();
      if (!quiet) _showBusyNote(btn);
    },
  };
  ctrl._timer = setTimeout(() => ctrl.fail(), BUSY_TIMEOUT_MS);
  if (token) _busyByToken[token] = ctrl;
  return ctrl;
}

/** Resolve the pending busy controller for a given WS reply token, if any. */
function resolveBusy(token) {
  const ctrl = token && _busyByToken[token];
  if (ctrl) ctrl.done();
}

// Token of a dialog-scoped action (save / settings-save) awaiting its reply.
// The server answers a *failed* save with a generic {type:'error'} frame that
// carries no token, so we remember which dialog action is in flight and let the
// 'error' handler release that button's lock (showing the inline note where the
// user acted) instead of leaking it into the chat retry card and stranding the
// spinner until the 10s watchdog. Cleared on the matching success reply.
let _pendingDialogToken = null;
/** Fail the pending dialog-scoped busy lock on error; true if one was handled. */
function failPendingDialogAction() {
  const token = _pendingDialogToken;
  if (!token) return false;
  _pendingDialogToken = null;
  const ctrl = _busyByToken[token];
  if (ctrl) ctrl.fail();  // restore the button + show the inline retry note in-place
  return true;
}

/** Drop a bilingual "didn't confirm — try again" note right after the button. */
function _showBusyNote(btn) {
  _clearBusyNote(btn);
  const note = document.createElement('div');
  note.className = 'busy-note';
  note.setAttribute('role', 'alert');
  note.textContent = L('busy_no_confirm');
  btn._busyNote = note;
  // Prefer placing it inside the button's action row so it sits beside it.
  const host = btn.parentNode || btn;
  host.appendChild(note);
}
function _clearBusyNote(btn) {
  if (btn && btn._busyNote && btn._busyNote.parentNode) {
    btn._busyNote.parentNode.removeChild(btn._busyNote);
  }
  if (btn) btn._busyNote = null;
}

// ================================================================
// CONNECTION-DEGRADED CHIP — persistent status near the input bar
// Distinct from transient toasts: it stays put while the link is down,
// pulses (unless reduced-motion) while reconnecting, and clears only once
// the socket reopens AND the post-reconnect refresh handshake completes.
// ================================================================
let _connChipEl = null;

/** Lazily create the degraded-status chip and mount it above the input bar. */
function _ensureConnChip() {
  if (_connChipEl && _connChipEl.parentNode) return _connChipEl;
  const bar = document.querySelector('.chat-input-container');
  if (!bar) return null;
  const chip = document.createElement('div');
  chip.id = 'connChip';
  chip.className = 'conn-chip';
  chip.setAttribute('role', 'status');
  chip.setAttribute('aria-live', 'polite');
  chip.textContent = L('conn_degraded');
  // Insert directly before the input row so it reads as an input-bar status.
  bar.parentNode.insertBefore(chip, bar);
  _connChipEl = chip;
  return chip;
}

/** Show the degraded chip (link error/close). Idempotent; refreshes its text
 *  so a language switch mid-outage relabels it. */
function showConnDegraded() {
  const chip = _ensureConnChip();
  if (!chip) return;
  chip.textContent = L('conn_degraded');
  chip.classList.add('visible');
  chip.classList.toggle('pulsing', !prefersReducedMotion);
}

/** Clear the degraded chip once the link is healthy again. */
function clearConnDegraded() {
  if (!_connChipEl) return;
  _connChipEl.classList.remove('visible', 'pulsing');
}

// ================================================================
// ACCOUNTS — register / sign in / sign out (bottom-left widget)
// ================================================================

const AUTH_TOKEN_KEY = 'signal_lost_token';
const AUTH_USER_KEY = 'signal_lost_username';
let authMode = 'signin'; // 'signin' | 'register'

/** Render the bottom-left account widget for the current auth state. */
function renderAccountWidget() {
  const label = document.getElementById('accountLabel');
  const dot = document.getElementById('accountDot');
  const btn = document.getElementById('accountBtn');
  if (!label || !btn) return;
  if (currentUser) {
    label.textContent = currentUser;
    dot.classList.add('online');
    btn.classList.add('signed-in');
  } else {
    label.textContent = L('auth_sign_in');
    dot.classList.remove('online');
    btn.classList.remove('signed-in');
    closeAccountMenu();
  }
}

/** Refresh dynamic auth/account chrome when the UI language changes. The static
 *  auth strings (title, tab labels, field labels, cancel button, placeholders)
 *  are keyed via data-i18n[-placeholder] and handled by applyStaticI18n(); only
 *  the account-widget label and the mode-dependent submit label live here. */
function applyAuthLanguage() {
  renderAccountWidget();
  const submit = document.getElementById('authSubmitLabel');
  if (submit) submit.textContent = authMode === 'register' ? L('auth_register') : L('auth_sign_in');
}

/** Click on the account button: open the auth modal (logged out) or the
 *  sign-out dropdown (logged in). */
function onAccountButton(event) {
  if (event) event.stopPropagation();
  if (currentUser) toggleAccountMenu();
  else openAuth('signin');
}

function toggleAccountMenu() {
  const menu = document.getElementById('accountMenu');
  const btn = document.getElementById('accountBtn');
  if (!menu) return;
  const open = menu.classList.toggle('open');
  menu.setAttribute('aria-hidden', open ? 'false' : 'true');
  if (btn) btn.setAttribute('aria-expanded', open ? 'true' : 'false');
}
function closeAccountMenu() {
  const menu = document.getElementById('accountMenu');
  const btn = document.getElementById('accountBtn');
  if (menu) { menu.classList.remove('open'); menu.setAttribute('aria-hidden', 'true'); }
  if (btn) btn.setAttribute('aria-expanded', 'false');
}
// Dismiss the account dropdown when clicking elsewhere.
document.addEventListener('click', (e) => {
  const w = document.getElementById('accountWidget');
  if (w && !w.contains(e.target)) closeAccountMenu();
});

/** Require a signed-in user before *intent*. Returns true if already signed in;
 *  otherwise stashes the intent, opens the sign-in modal, and returns false. */
function requireAuth(intent) {
  if (currentUser) return true;
  pendingIntent = intent || null;
  openAuth('signin');
  return false;
}

function openAuth(mode) {
  switchAuthTab(mode || 'signin');
  setAuthError('');
  document.getElementById('authPassword').value = '';
  openDialog(document.getElementById('authOverlay'), { initialFocus: 'authUsername' });
  playBeep(700, 0.04);
}
function closeAuth() {
  closeDialog(document.getElementById('authOverlay'));
  pendingIntent = null;
}

function switchAuthTab(mode) {
  authMode = (mode === 'register') ? 'register' : 'signin';
  const tabSignin = document.getElementById('authTabSignin');
  const tabReg = document.getElementById('authTabRegister');
  if (tabSignin) tabSignin.classList.toggle('active', authMode === 'signin');
  if (tabReg) tabReg.classList.toggle('active', authMode === 'register');
  const submit = document.getElementById('authSubmitLabel');
  if (submit) submit.textContent = authMode === 'register' ? L('auth_register') : L('auth_sign_in');
  const pass = document.getElementById('authPassword');
  if (pass) pass.setAttribute('autocomplete', authMode === 'register' ? 'new-password' : 'current-password');
  setAuthError('');
}

function setAuthError(text) {
  const el = document.getElementById('authError');
  if (el) el.textContent = text || '';
}

function submitAuth() {
  // The Enter-key handlers are bound to the (never-disabled) input fields, so a
  // second Enter can re-enter this before 'auth_result' lands. busy() only locks
  // the button, so guard on it here — otherwise the keyboard path defeats the
  // in-flight lock and fires a duplicate register/login frame.
  const btn = document.querySelector('#authOverlay .cyber-btn.accent');
  if (btn && btn.disabled) return;
  const username = (document.getElementById('authUsername').value || '').trim();
  const password = document.getElementById('authPassword').value || '';
  if (!username) { setAuthError(L('auth_err_username_required')); return; }
  if (!password) { setAuthError(L('auth_err_password_required')); return; }
  setAuthError('');
  // Lock the submit button until 'auth_result' lands (or 10s elapses) so a
  // double-click can't fire duplicate register/login frames. Both tabs share
  // this one button, so this covers sign-in and register alike.
  const b = busy(btn, 'auth_result');
  if (!sendWS({ action: authMode === 'register' ? 'register' : 'login', username, password })) { b.fail(); }
}

/** Handle the server's auth_result for a register/login attempt. */
function handleAuthResult(msg) {
  if (!msg.ok) {
    setAuthError(authErrorText(msg.error));
    return;
  }
  // Credentials accepted → store token and claim the active-session slot.
  authToken = msg.token;
  localStorage.setItem(AUTH_TOKEN_KEY, authToken);
  document.getElementById('authOverlay').style.display = 'none';
  // currentUser is set once the server confirms the bind (status/authed); a
  // pending sign-in intent is also run there. A 'session_conflict' may arrive
  // instead, prompting a takeover.
  sendInit();
}

function authErrorText(code) {
  const map = {
    username_taken: L('auth_err_username_taken'),
    username_required: L('auth_err_username_required'),
    username_too_long: L('auth_err_username_too_long'),
    username_invalid: L('auth_err_username_invalid'),
    password_too_short: L('auth_err_password_too_short'),
    password_required: L('auth_err_password_required'),
    invalid_credentials: L('auth_err_invalid_credentials'),
  };
  return map[code] || L('auth_err_generic');
}

function doLogout() {
  closeAccountMenu();
  sendWS({ action: 'logout', token: authToken });
  authToken = null;
  currentUser = null;
  localStorage.removeItem(AUTH_TOKEN_KEY);
  localStorage.removeItem(AUTH_USER_KEY);
  cachedSessions = [];
  cachedSaves = [];
  // Wipe the previous player's game data so nothing leaks into the next sign-in
  // (e.g. a language change on the menu re-renders panels from cachedSession).
  cachedSession = null;
  clearChat();
  resetCompanion();
  ['identity', 'district', 'inventory', 'network', 'world'].forEach(p => {
    const el = document.getElementById('panel-' + p); if (el) el.innerHTML = '';
  });
  ['knowledge', 'traces', 'log', 'conversation'].forEach(p => {
    const el = document.getElementById('panel-' + p + '-body'); if (el) el.innerHTML = '';
  });
  const lb = document.getElementById('btnLoadGame');
  if (lb) lb.style.display = 'none';
  renderAccountWidget();
  // If a game/sub-screen is open, return to the menu.
  switchScreen('menuScreen');
  notify(L('auth_signed_out'));
}

// --- Session-conflict (same account opened twice) -------------------------

function showSessionConflict(username) {
  conflictUsername = username || null;
  // The auth dialog (if open) is superseded by this interrupt.
  const auth = document.getElementById('authOverlay');
  if (auth.style.display !== 'none' && auth.style.display !== '') closeDialog(auth);
  document.getElementById('conflictTitle').textContent = L('conflict_title');
  document.getElementById('conflictText').textContent = L('conflict_text');
  document.getElementById('conflictYes').textContent = L('conflict_yes');
  document.getElementById('conflictNo').textContent = L('conflict_no');
  openDialog(document.getElementById('sessionConflictDialog'), { dismissible: false });
  playBeep(500, 0.05);
}
function confirmTakeover() {
  closeDialog(document.getElementById('sessionConflictDialog'));
  sendInit(true); // force takeover → server kicks the older session
}
function closeConflict() {
  closeDialog(document.getElementById('sessionConflictDialog'));
  conflictUsername = null;
  pendingIntent = null;  // abandon any deferred New Game / Load intent
}

// --- Kicked (this connection was taken over elsewhere) --------------------

function showKicked() {
  wasKicked = true;
  document.getElementById('kickedTitle').textContent = L('kicked_title');
  document.getElementById('kickedText').textContent = L('kicked_text');
  document.getElementById('kickedReload').textContent = L('kicked_reload');
  // Hide any other overlays so the kicked notice is unambiguous. Route through
  // closeDialog so the dialog stack is unwound (falls back to a plain hide for
  // any that were opened the legacy way).
  ['authOverlay', 'sessionConflictDialog', 'saveDialog', 'settingsOverlay'].forEach(id => {
    const el = document.getElementById(id); if (el) closeDialog(el);
  });
  openDialog(document.getElementById('kickedOverlay'), { dismissible: false });
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
let companionHistory = [];          // [{role:'user'|'implant', content}]
let companionIntroShown = false;
let _companionReplyTimer = null;    // 30s no-answer watchdog

// Companion transcript persistence (wave 3b). The aside used to live only in
// memory and vanish on reload; it now round-trips through localStorage (rolling
// ~40 entries) so a refresh doesn't erase the side-channel. Still wiped on a
// NEW session (resetCompanion) since it's session-scoped context.
const _COMPANION_HISTORY_KEY = 'signal_lost_companion_history';
const _COMPANION_HISTORY_MAX = 40;
const COMPANION_REPLY_TIMEOUT_MS = 30000;

function _saveCompanionHistory() {
  try {
    localStorage.setItem(_COMPANION_HISTORY_KEY,
      JSON.stringify(companionHistory.slice(-_COMPANION_HISTORY_MAX)));
  } catch (e) {}
}
function _loadCompanionHistory() {
  try {
    const raw = localStorage.getItem(_COMPANION_HISTORY_KEY);
    if (!raw) return [];
    const arr = JSON.parse(raw);
    if (!Array.isArray(arr)) return [];
    return arr.filter(m => m && typeof m.content === 'string' &&
      (m.role === 'user' || m.role === 'implant')).slice(-_COMPANION_HISTORY_MAX);
  } catch (e) { return []; }
}
function _clearCompanionHistoryStore() {
  try { localStorage.removeItem(_COMPANION_HISTORY_KEY); } catch (e) {}
}

/** Restore a persisted transcript into the panel (called on load). */
function restoreCompanionHistory() {
  companionHistory = _loadCompanionHistory();
  if (!companionHistory.length) return;
  const box = document.getElementById('companionMessages');
  if (box) {
    box.innerHTML = '';
    for (const m of companionHistory) {
      addCompanionMessage(m.content, m.role === 'user' ? 'user' : 'implant');
    }
  }
  companionIntroShown = true;   // don't replay the intro over restored history
}

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
  _clearCompanionHistoryStore();   // session-scoped → drop the persisted copy too
  companionIntroShown = false;
  companionPending = false;
  _clearCompanionReplyTimer();
  const box = document.getElementById('companionMessages');
  if (box) box.innerHTML = '';
  hideCompanionThinking();
  const send = document.getElementById('companionSend');
  if (send) send.disabled = false;
  if (companionOpen) closeCompanion();
}

/** Cancel the pending 30s reply watchdog, if armed. */
function _clearCompanionReplyTimer() {
  if (_companionReplyTimer) { clearTimeout(_companionReplyTimer); _companionReplyTimer = null; }
}

/** Re-enable the composer and hide the thinking indicator (shared teardown). */
function _companionResetPending() {
  companionPending = false;
  _clearCompanionReplyTimer();
  hideCompanionThinking();
  const send = document.getElementById('companionSend');
  if (send) send.disabled = false;
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

  // Gate on MAIN-socket health: the companion runs its own socket, but its
  // answers depend on the live game session the main link owns. wsOpen() is the
  // single source of truth for link health (shared with sendMessage/retry), so
  // if the city link is down we surface the bilingual offline line and hold the
  // question rather than firing into a dead session.
  if (!wsOpen()) {
    addCompanionMessage(L('companion_offline'), 'error');
    return;
  }

  // Send only PRIOR turns as context (server caps too); the new question is
  // passed separately, so slice before pushing to avoid duplicating it.
  const history = companionHistory.slice(-8);

  addCompanionMessage(text, 'user');
  companionHistory.push({ role: 'user', content: text });
  _saveCompanionHistory();
  input.value = '';
  companionPending = true;
  const send = document.getElementById('companionSend');
  if (send) send.disabled = true;
  showCompanionThinking();

  if (companionWS && companionWS.readyState === WebSocket.OPEN) {
    companionWS.send(JSON.stringify({ action: 'ask', text, history, token: authToken }));
    // Arm the 30s no-answer watchdog: if no reply lands, restore the composer
    // and drop a bilingual retry line so the panel never strands "listening…".
    _clearCompanionReplyTimer();
    _companionReplyTimer = setTimeout(() => {
      _companionReplyTimer = null;
      if (!companionPending) return;
      _companionResetPending();
      addCompanionMessage(L('companion_timeout'), 'error');
    }, COMPANION_REPLY_TIMEOUT_MS);
  } else {
    _companionResetPending();
    addCompanionMessage(L('companion_error'), 'error');
  }
}

function handleCompanionReply(msg) {
  // A reply landed → cancel the watchdog and re-enable the composer.
  _companionResetPending();
  if (msg.error) {
    addCompanionMessage(msg.code === 'no_session' ? L('companion_no_session') : L('companion_error'), 'error');
    return;
  }
  const text = (msg.text || '').trim() || L('companion_error');
  addCompanionMessage(text, 'implant');
  companionHistory.push({ role: 'implant', content: text });
  _saveCompanionHistory();
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
  // Any well-formed inbound frame proves the link is healthy again — clear the
  // degraded chip. onopen fires a 'refresh' when a game is active, so the first
  // reply after a reconnect (its session_update, or any other frame) lands here
  // and retires the chip; this is the "reopen + refresh success" clear.
  clearConnDegraded();
  switch (msg.type) {
    case 'status': {
      const wasAuthed = !!currentUser;
      if (msg.authed) {
        currentUser = msg.username || null;
        conflictUsername = null;
        // Remember the identity so the next refresh auto-logs in without a flash.
        if (currentUser) localStorage.setItem(AUTH_USER_KEY, currentUser);
        // A bind just succeeded → close the auth modal.
        const authOv = document.getElementById('authOverlay');
        if (authOv && authOv.style.display !== 'none') authOv.style.display = 'none';
        if (!wasAuthed && currentUser) notify(`${L('auth_signed_in_as')} ${currentUser}`);
      } else {
        currentUser = null;
        // Token absent/expired server-side — drop it locally.
        if (authToken) { authToken = null; localStorage.removeItem(AUTH_TOKEN_KEY); }
        localStorage.removeItem(AUTH_USER_KEY);
      }
      renderAccountWidget();

      cachedSessions = msg.sessions || [];
      if (msg.saves && msg.saves.length > 0) {
        document.getElementById('btnLoadGame').style.display = '';
        cachedSaves = msg.saves;
      } else {
        document.getElementById('btnLoadGame').style.display = 'none';
        cachedSaves = [];
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

      // Run any action that was deferred until sign-in.
      if (currentUser && pendingIntent) {
        const intent = pendingIntent; pendingIntent = null;
        if (intent === 'newgame') showNewGame();
        else if (intent === 'loadgame') showLoadGame();
      }
      break;
    }

    case 'game_started':
      switchScreen('gameScreen');
      MusicEngine.preloadAll();
      // Only a NEW game wipes the session-scoped aside. Resume / load / autoresume
      // (mode==='resume') keep the just-restored transcript so reloading the page
      // and then resuming the SAME session doesn't erase the side-channel.
      if (msg.mode !== 'resume') resetCompanion();
      if (msg.session) updateAllPanels(msg.session);
      if (pendingTutorial) { pendingTutorial = false; setTimeout(startTutorial, 600); }
      break;

    case 'thinking':
      clearSuggestedActions();
      showThinking();
      // A new turn began — drop last turn's meter-why reasons so a stale cause
      // can't linger under a meter that didn't move this turn.
      _clearMeterReasons();
      break;

    case 'roll':
      // Optional mechanical beat: a compact chip per skill check, rendered inline
      // in the chat flow BEFORE the upcoming narration. Additive/optional frame —
      // may arrive between 'thinking' and 'narrative', or never. Degrade silently
      // on a malformed payload. NOT skippable text: standalone element, so it
      // sits outside the typewriter generation-guard entirely.
      renderRollChips(msg.rolls);
      break;

    case 'narrative':
      // A narrative reply means the last action resolved — clear the retry
      // offer and the stored command so a later error can't re-send stale text.
      _lastPlayerInput = null;
      _dismissRetryCard();
      if (_firstSceneArmed) {
        // Buffered opening scene: the tutorial masks the first-turn wait. Hold the
        // scene regardless of its role (system OR agent — the backend has labelled
        // it both ways) and reveal it the instant the tutorial ends, never typing
        // it out behind the overlay. Park the wait experience; leave input as-is
        // (the tutorial owns the screen). Clear the hang watchdog.
        _clearWatchdog();
        hideThinking();
        _pendingFirstScene = msg;
        break;
      }
      endTurnUI();
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

    case 'suggested_actions':
      // Reconnect resync: the server re-emits the last narrative's suggested
      // actions as a standalone frame so the chips repaint immediately without
      // waiting for the next full turn. Additive to the narrative render path.
      renderSuggestedActions(msg.suggested_actions || []);
      break;

    case 'state_delta':
      // Additive to session_update (which already repaints the panels): a
      // state_delta reports WHICH end-gating meters moved this turn, so we
      // pulse just those HUD gauges. Gated behind prefersReducedMotion.
      flashChangedMeters(msg);
      // Optional reasons:{alert?,integrity?,decay?} → surface WHY a meter moved
      // as a HUD tooltip + WORLD-panel subtext (persists until next turn).
      // Absent block → reasons cleared; the meters just show their value.
      _ingestMeterReasons(msg.reasons);
      _applyMeterReasons();
      // NOTE: traces_added / knowledge_added arrays are intentionally NOT
      // consumed here. The dedicated per-item 'discovery' and 'knowledge_added'
      // frames (sent just before this delta) already own the discovery ceremony
      // and knowledge toast. Toasting again from these arrays would double-fire
      // the ceremony — so the delta carries them for diffing only, and this
      // handler deliberately leaves them to the ceremony path. See the
      // 'discovery' / 'knowledge_added' cases below.
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

    case 'system_notice':
      showSystemNotice(msg.text);
      break;

    case 'game_over':
      // Release the wait experience immediately — otherwise the 2600ms ticker
      // and 650ms ambient beep intervals leak for the life of the page while the
      // 2s overlay delay runs and beyond.
      endTurnUI();
      resetPredictions();
      setTimeout(() => showGameOver(msg.ending, msg.narrative, msg.death_cause), 2000);
      break;

    case 'saved':
      _pendingDialogToken = null;
      resolveBusy('saved');           // release the SAVE button's in-flight lock
      notify(`${L('saved')}: ${msg.save_name}`);
      closeSaveDialog();
      break;

    case 'provider_saved':
      _pendingDialogToken = null;
      resolveBusy('provider_saved');  // release the settings SAVE button
      notify(L('settings_saved'));
      if (msg.provider) prefillProviderSettings(msg.provider);
      if (msg.langsmith) prefillLangsmithSettings(msg.langsmith);
      if (msg.features) _cachedFeatures = msg.features;
      document.getElementById('settingsStatus').textContent = L('saved');
      setTimeout(() => { document.getElementById('settingsStatus').textContent = ''; }, 2000);
      // Overlay stays open until *now* — the save is confirmed, so it's honest
      // to close it (saveSettings no longer closes it optimistically).
      closeDialog(document.getElementById('settingsOverlay'));
      break;

    case 'error':
      // A save/settings-save failure also arrives as a generic {type:'error'}.
      // Scope it to the dialog the user acted in: release that button's lock
      // (inline "try again" note appears in place) and surface the message as a
      // toast over the still-open modal — NOT the chat retry card, which sits
      // behind the modal and could offer to re-send an unrelated game action.
      if (failPendingDialogAction()) {
        notify(msg.message || L('error_generic'), true);
        break;
      }
      _finalizeActiveTyper();  // snap any in-flight narration to done first
      endTurnUI();
      // Recoverable turn error → an inline retry card in the chat (not a
      // vanishing toast) so the player can re-send their last action.
      showRetryCard(msg.message);
      break;

    case 'auth_result':
      // A reply arrived (ok or not) → release the auth button's lock either way;
      // handleAuthResult renders the specific error text on failure.
      resolveBusy('auth_result');
      handleAuthResult(msg);
      break;

    case 'session_conflict':
      showSessionConflict(msg.username);
      break;

    case 'kicked':
      showKicked();
      break;

    case 'auth_required':
      // Server rejected a game action for lack of a session — prompt sign-in.
      openAuth('signin');
      break;

    default:
      // Unknown/typo'd or newer-protocol message type — ignore, never fatal,
      // but warn so frontend/backend drift is visible during development.
      console.warn('[ws] ignoring unknown message type:', msg && msg.type);
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
  openDialog(document.getElementById('settingsOverlay'), { onClose: _closeSettingsInternal });
  document.getElementById('settingsStatus').textContent = '';
  // Sync music volume slider
  const vol = MusicEngine.getVolume();
  document.getElementById('inputMusicVolume').value = vol;
  document.getElementById('musicVolValue').textContent = Math.round(vol * 100) + '%';
  // Sync SFX volume slider (separate persisted channel)
  const sfxVol = MusicEngine.getSfxVolume();
  const sfxSlider = document.getElementById('inputSfxVolume');
  if (sfxSlider) sfxSlider.value = sfxVol;
  const sfxValEl = document.getElementById('sfxVolValue');
  if (sfxValEl) sfxValEl.textContent = Math.round(sfxVol * 100) + '%';
  // Snapshot ALL form state so cancel can restore
  _settingsSnapshot = {
    volume: vol,
    sfxVolume: sfxVol,
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

// Public close (button / Esc): unwinds the dialog stack + restores focus,
// which in turn calls _closeSettingsInternal to hide + revert form state.
function closeSettings() { closeDialog(document.getElementById('settingsOverlay')); }

// Actual hide + snapshot revert. Called by the dialog manager on close; also
// safe to call directly (e.g. showKicked force-hide) since it's idempotent.
function _closeSettingsInternal() {
  // Restore to pre-open state (cancel = discard all unsaved changes)
  if (_settingsSnapshot) {
    MusicEngine.setVolume(_settingsSnapshot.volume);
    if (_settingsSnapshot.sfxVolume != null) MusicEngine.setSfxVolume(_settingsSnapshot.sfxVolume);
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
  // Lock the SAVE button until the server confirms ('provider_saved') or the 10s
  // watchdog fires. Do NOT close the overlay optimistically — it stays open so a
  // silent failure surfaces as an inline note here rather than vanishing.
  const btn = document.querySelector('#settingsOverlay .cyber-btn.accent');
  const b = busy(btn, 'provider_saved');
  _pendingDialogToken = 'provider_saved';  // let an 'error' reply unlock it in-place
  document.getElementById('settingsStatus').textContent = L('saving');
  if (!sendWS(payload)) {
    _pendingDialogToken = null;
    b.fail();
    document.getElementById('settingsStatus').textContent = '';
    return;
  }
  _settingsSnapshot = null;  // Mark as saved so a later close doesn't revert
}

let _cachedUsage = null;

function _updateUsageStats() {
  const u = _cachedUsage;
  const el = document.getElementById('usageStats');
  if (!el) return;
  if (!u || !u.total_calls) {
    el.innerHTML = `<span class="dim" style="font-size:11px">${L('no_usage_data')}</span>`;
    return;
  }
  const costStr = typeof u.cost === 'number' ? ` &nbsp;|&nbsp; ${esc(L('usage_cost'))}: <span class="cyan">${_formatCost(u.cost)}</span>` : '';
  el.innerHTML = `<div style="font-size:11px;color:var(--text-dim);line-height:1.6">
    ${esc(L('usage_llm_calls'))}: <span class="cyan">${u.total_calls}</span> &nbsp;|&nbsp;
    ${esc(L('usage_input'))}: <span class="cyan">${(u.input_tokens || 0).toLocaleString()}</span> &nbsp;|&nbsp;
    ${esc(L('usage_output'))}: <span class="cyan">${(u.output_tokens || 0).toLocaleString()}</span> &nbsp;|&nbsp;
    ${esc(L('usage_total'))}: <span class="cyan">${(u.total_tokens || 0).toLocaleString()}</span> ${esc(L('tokens_unit'))}${costStr}
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
  document.getElementById('confirmMenuTitle').textContent = L('confirm_menu_title');
  document.getElementById('confirmMenuText').textContent = L('confirm_menu_text');
  document.getElementById('confirmMenuYes').textContent = L('btn_confirm');
  document.getElementById('confirmMenuNo').textContent = L('btn_cancel');
  openDialog(document.getElementById('confirmMenuDialog'));
  playBeep(600, 0.04);
}

function confirmReturnToMenu() {
  closeDialog(document.getElementById('confirmMenuDialog'));
  switchScreen('menuScreen');
  // Refresh saves/sessions list from server
  sendWS({ action: 'init' });
}

function closeConfirmMenu() {
  closeDialog(document.getElementById('confirmMenuDialog'));
}
function showNewGame() {
  if (!requireAuth('newgame')) return;
  switchScreen('newGameScreen'); playBeep(1000, 0.04);
}

function showLoadGame() {
  if (!requireAuth('loadgame')) return;
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
  // Make the whole UI follow the language you're PLAYING in — otherwise an
  // English game shows Chinese chrome (and vice-versa) when the display default
  // differs from the chosen game language.
  if (config.language) setLanguage(config.language);
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

// ----------------------------------------------------------------------------
// ROLL CHIP — inline mechanical beat (optional {type:'roll'} frame)
// A compact chip per skill check, rendered in the chat flow before the upcoming
// narration. Count-up of result → target, green/red success flash, expandable
// modifier breakdown, rising/falling two-tone via the 'ui' SFX bus. Motion is
// gated behind prefersReducedMotion (instant fill, no animation). This is a
// standalone element, NOT skippable typewriter text — it never touches the
// generation-guard (_activeTyper) and is never finalized/cleared by a skip.
// ----------------------------------------------------------------------------

/** Bilingual skill label from a roll entry, following the field_zh pattern
 *  (server supplies label + label_zh). Falls back to the raw skill token. */
function _rollLabel(r) {
  const zh = (currentLang === 'zh' && r && r.label_zh) ? r.label_zh : (r && r.label);
  return zh || (r && r.skill) || '';
}

/** Count a numeric element up from 0 → value over ~duration ms (rAF-driven).
 *  Reduced-motion / tiny values snap straight to the final number. */
function _countUp(el, value, duration) {
  if (!el) return;
  const end = Number(value) || 0;
  if (prefersReducedMotion || Math.abs(end) < 2 || !duration) {
    el.textContent = String(end);
    return;
  }
  const start = performance.now();
  let settled = false;
  function step(now) {
    if (settled) return;
    const t = Math.min(1, (now - start) / duration);
    // easeOutCubic — decelerate into the final value
    const eased = 1 - Math.pow(1 - t, 3);
    el.textContent = String(Math.round(end * eased));
    if (t < 1) requestAnimationFrame(step);
    else { settled = true; el.textContent = String(end); }
  }
  requestAnimationFrame(step);
  // Safety net: requestAnimationFrame is paused while the tab is backgrounded,
  // which would freeze the count-up at 0. Snap to the final value once the
  // animation window has elapsed regardless of whether rAF ever ticked, so a
  // roll result is never stuck mid-count in a hidden/throttled tab.
  setTimeout(() => { if (!settled) { settled = true; el.textContent = String(end); } }, duration + 60);
}

function renderRollChips(rolls) {
  // Degrade silently: nothing to show on a missing/empty/malformed payload.
  if (!Array.isArray(rolls) || rolls.length === 0) return;
  const container = document.getElementById('chatMessages');
  if (!container) return;

  const wrap = document.createElement('div');
  wrap.className = 'chat-msg roll-beat';

  rolls.forEach((r, idx) => {
    if (!r || typeof r !== 'object') return;
    const success = !!r.success;
    const result = Number(r.result) || 0;
    const target = Number(r.target) || 0;
    const label = _rollLabel(r);
    const mods = Array.isArray(r.modifiers) ? r.modifiers.filter(Boolean) : [];

    const chip = document.createElement('div');
    chip.className = 'roll-chip ' + (success ? 'roll-ok' : 'roll-fail')
      + (prefersReducedMotion ? ' reduced' : '');

    const outcome = success ? L('roll_success') : L('roll_failure');
    const glyph = success ? '▲' : '▼';   // ▲ rising / ▼ falling

    // Pass/fail-only mechanic beats (cipher decrypts, Signal scans) carry no
    // numeric check — the engine records them with target:0, result:0 — so the
    // "result vs target" row would render a meaningless "0 vs 0". Suppress it;
    // the label + SUCCESS/FAILURE tag are the real signal for those beats.
    const hasNums = !(target === 0 && result === 0);

    // Header: skill label + outcome tag. Body: result vs target (result counts up).
    let inner =
      '<div class="roll-chip-head">' +
        '<span class="roll-chip-skill">' + esc(label) + '</span>' +
        '<span class="roll-chip-outcome">' + esc(glyph + ' ' + outcome) + '</span>' +
      '</div>';
    if (hasNums) {
      inner +=
        '<div class="roll-chip-nums">' +
          '<span class="roll-chip-result">0</span>' +
          '<span class="roll-chip-vs">' + esc(L('roll_vs')) + '</span>' +
          '<span class="roll-chip-target">' + esc(String(target)) + '</span>' +
        '</div>';
    }

    // Expandable modifier breakdown — e.g. "Lockpick +15". Collapsed by default;
    // a click toggles it. Only rendered when the roll actually carries modifiers.
    if (mods.length > 0) {
      let rows = '';
      for (const m of mods) {
        const src = (m && m.source != null) ? String(m.source) : '';
        const val = Number(m && m.value) || 0;
        const sign = val >= 0 ? '+' : '';
        rows += '<span class="roll-mod-row"><span class="roll-mod-src">' + esc(src)
              + '</span><span class="roll-mod-val ' + (val >= 0 ? 'pos' : 'neg') + '">'
              + esc(sign + val) + '</span></span>';
      }
      inner +=
        '<button type="button" class="roll-chip-toggle" aria-expanded="false">'
          + esc(L('roll_modifiers')) + ' ▸</button>'
        + '<div class="roll-chip-mods" hidden>' + rows + '</div>';
    }

    chip.innerHTML = inner;

    // Wire the modifier toggle (no inline handler → CSP-safe, esc()'d content).
    const toggle = chip.querySelector('.roll-chip-toggle');
    const modsBox = chip.querySelector('.roll-chip-mods');
    if (toggle && modsBox) {
      toggle.addEventListener('click', () => {
        const open = modsBox.hasAttribute('hidden');
        if (open) { modsBox.removeAttribute('hidden'); toggle.setAttribute('aria-expanded', 'true'); }
        else { modsBox.setAttribute('hidden', ''); toggle.setAttribute('aria-expanded', 'false'); }
        toggle.innerHTML = esc(L('roll_modifiers')) + (open ? ' ▾' : ' ▸');
      });
    }

    wrap.appendChild(chip);

    // Stagger the count-up + success flash so multiple chips land in sequence.
    const delay = prefersReducedMotion ? 0 : idx * 220;
    setTimeout(() => {
      const resEl = chip.querySelector('.roll-chip-result');
      _countUp(resEl, result, 480);
      // Rising/falling two-tone via the shared 'ui' SFX bus (honours mute).
      if (success) {
        playBeep(520, 0.05, 0.03, 'ui');
        setTimeout(() => playBeep(780, 0.06, 0.035, 'ui'), 90);
      } else {
        playBeep(440, 0.05, 0.03, 'ui');
        setTimeout(() => playBeep(300, 0.07, 0.035, 'ui'), 90);
      }
      // Green/red success flash — a one-shot class the CSS animates.
      if (!prefersReducedMotion) {
        chip.classList.add('roll-flash');
        chip.addEventListener('animationend', () => chip.classList.remove('roll-flash'), { once: true });
      }
    }, delay);
  });

  // If every entry was malformed, nothing got appended — bail without an empty row.
  if (!wrap.querySelector('.roll-chip')) return;
  container.appendChild(wrap);
  container.scrollTop = container.scrollHeight;
}

function showDiscoveryNotification(msg) {
  const container = document.getElementById('chatMessages');
  const el = document.createElement('div');
  el.className = 'chat-msg discovery-notification';
  const label = '◈ ' + L('trace_uncovered');
  el.innerHTML = `
    <div class="discovery-badge">
      <span class="discovery-label">${esc(label)}</span>
    </div>
    <div class="discovery-text">${esc(msg.description)}</div>
  `;
  container.appendChild(el);
  container.scrollTop = container.scrollHeight;
  discoveryEls.push(el);
  // The persistent chat entry above is the log record; the ceremony below is
  // the moment — a centered banner that lands, then flies to the TRACE tab.
  playDiscoveryCeremony(msg);
}

/** Bilingual layer name for a discovery payload. Prefer the numeric layer (its
 *  flavor name is bilingual in LABELS); fall back to the server's player-known
 *  layer_name string. Both are already discovered → no spoiler risk. */
function _discoveryLayerName(msg) {
  const n = Number(msg && msg.layer);
  if (n >= 1 && n <= 5) return L('trace_layer_' + n);
  return (msg && msg.layer_name) ? String(msg.layer_name) : '';
}

/**
 * DISCOVERY CEREMONY — the core loop is knowledge discovery, so it must LAND.
 * A centered banner holds ~1.6s, then animates toward the TRACE tab, which
 * pulses until the player opens it. Intensity scales with layer depth (L1 clean
 * cyan flash → L4/L5 heavier glitch shimmer). All motion is gated behind
 * prefersReducedMotion (→ simple fade). Two-tone unlock beep respects music mute.
 */
function playDiscoveryCeremony(msg) {
  const layer = Math.min(5, Math.max(1, Number(msg && msg.layer) || 1));
  const layerName = _discoveryLayerName(msg);

  // Two-tone unlock cue via the shared SFX bus (discovery category); the bus
  // honours the single mute state, so no per-call mute check is needed here.
  // Deeper layers ring a touch lower + longer.
  {
    const base = 760 - (layer - 1) * 40;
    playBeep(base, 0.07, 0.025, 'discovery');
    setTimeout(() => playBeep(base + 320, 0.09, 0.03, 'discovery'), 110);
  }

  const banner = document.createElement('div');
  banner.className = 'discovery-ceremony depth-' + layer + (prefersReducedMotion ? ' reduced' : '');
  const title = '◈ ' + L('trace_uncovered');
  banner.innerHTML =
    `<span class="ceremony-title" data-text="${esc(title)}">${esc(title)}</span>` +
    `<span class="ceremony-sep">—</span>` +
    `<span class="ceremony-layer">${esc(layerName)}</span>`;
  document.body.appendChild(banner);

  const tab = document.querySelector('.panel-tab[data-panel="traces"]');

  // Reduced motion: quiet fade in/out, then pulse the tab. No flight.
  if (prefersReducedMotion) {
    requestAnimationFrame(() => banner.classList.add('show'));
    setTimeout(() => {
      banner.classList.remove('show');
      setTimeout(() => banner.remove(), 400);
      _pulseTraceTab();
    }, 1600);
    return;
  }

  requestAnimationFrame(() => banner.classList.add('show'));
  // Hold, then fly toward the TRACE tab and hand off to the tab pulse.
  setTimeout(() => {
    if (tab) {
      const from = banner.getBoundingClientRect();
      const to = tab.getBoundingClientRect();
      const dx = (to.left + to.width / 2) - (from.left + from.width / 2);
      const dy = (to.top + to.height / 2) - (from.top + from.height / 2);
      banner.style.setProperty('--fly-x', dx + 'px');
      banner.style.setProperty('--fly-y', dy + 'px');
    }
    banner.classList.add('fly');
    setTimeout(() => { banner.remove(); _pulseTraceTab(); }, 620);
  }, 1600);
}

/** Make the TRACE tab pulse until the player opens it (cleared in switchPanel). */
function _pulseTraceTab() {
  const tab = document.querySelector('.panel-tab[data-panel="traces"]');
  if (tab && !tab.classList.contains('active')) tab.classList.add('trace-pulse');
}

function showSystemNotice(text) {
  if (!text) return;
  const container = document.getElementById('chatMessages');
  // Skip exact duplicates of the most recent system notice — the same meter
  // change was sometimes emitted twice in a turn, stacking identical lines.
  const last = container.querySelector('.chat-msg.system-notice:last-of-type .system-notice-text');
  if (last && last.textContent === text) return;
  const el = document.createElement('div');
  el.className = 'chat-msg system-notice';
  el.innerHTML = `<div class="system-notice-text">${esc(text)}</div>`;
  container.appendChild(el);
  container.scrollTop = container.scrollHeight;
}

// Knowledge-added: a quieter sibling of the discovery ceremony. No banner, no
// flight — just a distinct-accent toast in the shared stack. Natural flex
// stacking (no height math), so wrapped 中文 lines can no longer overlap.
const _KN_LABEL_KEYS = {
  fact: 'kn_fact', rumor: 'kn_rumor', evidence: 'kn_evidence',
  theory: 'kn_theory', connection: 'kn_connection',
};
function showKnowledgeNotification(entryType) {
  const key = _KN_LABEL_KEYS[entryType] || _KN_LABEL_KEYS.fact;
  addToast('knowledge', esc(L(key)));
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

/** Render a SAFE markdown subset (bold, italic, inline code, bullets, line
 *  breaks). HTML is escaped first so narration can never inject markup. */
function renderMarkdown(text) {
  let h = String(text || '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  // bullet lines: "- foo" / "* foo" / "• foo" -> • foo
  h = h.replace(/^[\t ]*[-*•]\s+(.*)$/gm, '<span class="md-li">• $1</span>');
  h = h.replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>');   // **bold**
  h = h.replace(/`([^`\n]+)`/g, '<code>$1</code>');             // `code`
  h = h.replace(/(^|[^*\w])\*([^*\n]+)\*(?=[^*\w]|$)/g, '$1<em>$2</em>'); // *italic*
  h = h.replace(/\n/g, '<br>');
  return h;
}

// The narrative is fully interactive the instant it hits the DOM — the
// typewriter is pure eye-candy over already-committed state. A per-typer
// generation id lets a newer narrative/error cancel+finalize any prior
// in-flight typer, and lets a click / Esc / Space skip straight to the end.
let _typerGen = 0;              // increments per typewriter; the live one owns _activeTyper
let _activeTyper = null;        // { finalize } for the currently-typing message, or null

/** Cancel+finalize the in-flight typewriter (if any). Idempotent. */
function _finalizeActiveTyper() {
  if (_activeTyper && typeof _activeTyper.finalize === 'function') _activeTyper.finalize();
}

function addTypingMessage(text, role = 'agent', usage = null, elapsedSeconds = null, suggestedActions = null) {
  // A new message supersedes any prior in-flight typer — snap it to done first.
  _finalizeActiveTyper();

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

  const myGen = ++_typerGen;
  let i = 0; const speed = 8, interval = 20;
  let timer = null;         // setTimeout handle for the next type step
  let skipHintTimer = null; // delay handle for the '▸ skip' affordance
  let skipHintEl = null;    // '▸ skip' affordance, added ~800ms into long type-outs
  let decryptTimer = null;  // setInterval handle for the decrypt scramble (agent role)
  let done = false;

  // Stash the full text + a skip() handle on the element so a click can finalize.
  msg._fullText = text;

  function _removeSkipHint() {
    if (skipHintEl && skipHintEl.parentNode) skipHintEl.parentNode.removeChild(skipHintEl);
    skipHintEl = null;
  }

  function finalize() {
    if (done) return;
    done = true;
    if (timer) { clearTimeout(timer); timer = null; }
    if (skipHintTimer) { clearTimeout(skipHintTimer); }
    // Kill the in-flight decrypt scramble too — otherwise its next tick (and its
    // frame-6 `contentEl.textContent = ''`) would clobber the committed markdown
    // to blank when a skip/supersede fires inside the ~300ms decrypt window.
    if (decryptTimer) { clearInterval(decryptTimer); decryptTimer = null; }
    _removeSkipHint();
    contentEl.classList.remove('typing');
    msg.classList.remove('skippable');
    // Re-render with the safe markdown subset so **bold**/lists/`code` render.
    contentEl.innerHTML = renderMarkdown(text);
    // Build info line: time always shown, tokens optional
    const infoParts = [];
    if (elapsedSeconds != null) infoParts.push(`${elapsedSeconds}s`);
    if (usage && usage.total && _showTokens()) {
      const cost = _getCost(usage);
      infoParts.push(`${usage.total.toLocaleString()} ${L('tokens_unit')} · ${_formatCost(cost)}`);
    }
    if (infoParts.length > 0) {
      const infoEl = document.createElement('div');
      infoEl.className = 'msg-tokens';
      infoEl.textContent = infoParts.join(' · ');
      msg.appendChild(infoEl);
    }
    if (_activeTyper && _activeTyper.gen === myGen) _activeTyper = null;
    // Keep the chat pinned to the end of the now-complete message if we were near it.
    if (container.scrollHeight - container.scrollTop - container.clientHeight < 200) {
      container.scrollTop = container.scrollHeight;
    }
  }
  msg._skip = finalize;

  function typeNext() {
    if (done) return;
    if (i < text.length) {
      contentEl.textContent += text.slice(i, i + speed);
      i += speed;
      // Only auto-scroll if user is near the bottom (within 200px)
      if (container.scrollHeight - container.scrollTop - container.clientHeight < 200) {
        container.scrollTop = container.scrollHeight;
      }
      // Decrypt/typing chatter — the SFX bus honours mute for us.
      if (Math.random() < 0.05) playBeep(600 + Math.random() * 400, 0.02, 0.01, 'ambient');
      timer = setTimeout(typeNext, interval);
    } else {
      finalize();
    }
  }

  // Register this typer so Esc/Space (global) and a newer message can finalize it.
  _activeTyper = { gen: myGen, finalize };

  // Interactive immediately: input + suggested actions render up front so the
  // typewriter never gates play. A click anywhere on the typing message skips it.
  enableInput();
  renderSuggestedActions(suggestedActions);
  msg.classList.add('skippable');
  msg.addEventListener('click', () => { if (!done) finalize(); });

  // Fade in a subtle '▸ skip' hint only for long type-outs (~800ms in).
  if (text.length > speed * (800 / interval)) {
    skipHintTimer = setTimeout(() => {
      if (done) return;
      skipHintEl = document.createElement('div');
      skipHintEl.className = 'skip-hint';
      skipHintEl.textContent = L('skip_hint');
      msg.appendChild(skipHintEl);
      requestAnimationFrame(() => { if (skipHintEl) skipHintEl.classList.add('visible'); });
    }, 800);
  }

  // Agent narration gets a brief "incoming transmission" decrypt flash first;
  // resume/system messages type out plainly. Guard the callback against a skip
  // that fired during the ~300ms decrypt window.
  if (role === 'agent') {
    decryptTimer = _decryptReveal(msg, contentEl, () => {
      decryptTimer = null; // scramble finished on its own; nothing left to cancel
      if (!done) typeNext();
    });
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
//
// Race note: the backend emits `prediction_ready` for the CURRENT turn's
// suggestions right after the narrative. That message can land in the window
// between a `thinking` (which tears down the old chips) and the next
// `renderSuggestedActions` (which draws the new ones). If clearSuggestedActions
// wiped this set, that early arrival would be forgotten and the chip would draw
// as "pending" forever. So the teardown paths split:
//   • clearSuggestedActions()  → DOM only; PRESERVES ready arrivals.
//   • resetPredictions()       → DOM + set; only when the current suggestions
//                                are truly spent (player committed / game over).
// renderSuggestedActions then prunes the set to just the incoming action texts,
// dropping any stale ready-flags from a prior turn while keeping fresh ones.
let _readyPredictions = new Set();

// ----------------------------------------------------------------------------
// METER "WHY" — an in-world, one-line cause for a meter move this turn.
// state_delta may optionally carry reasons:{alert?,integrity?,decay?}, each an
// {en,zh}. We stash the RAW pairs here and resolve the language at render time
// (inside _applyMeterReasons), so a mid-turn language switch re-localizes the
// HUD tooltip and WORLD '· why' subtext like every other panel string.
// Persists until the NEXT turn: cleared when the player acts (thinking frame).
// Bilingual via the en/zh fields; a meter with no reason is simply omitted.
// ----------------------------------------------------------------------------
let _meterReasons = { alert: null, integrity: null, decay: null };

/** Pick the localized reason string from an {en,zh} pair, or '' if absent. */
function _reasonText(pair) {
  if (!pair || typeof pair !== 'object') return '';
  const zh = (currentLang === 'zh') ? pair.zh : null;
  return String(zh || pair.en || '').trim();
}

/** Validate an {en,zh} reason pair for storage; null when empty/malformed. */
function _reasonPair(pair) {
  if (!pair || typeof pair !== 'object') return null;
  const en = (typeof pair.en === 'string') ? pair.en.trim() : '';
  const zh = (typeof pair.zh === 'string') ? pair.zh.trim() : '';
  if (!en && !zh) return null;
  return { en: en || zh, zh: zh || en };
}

/** Ingest a state_delta's optional reasons block. Only known keys are read;
 *  a missing key leaves the prior turn's reason cleared (we reset per turn).
 *  Stores the raw {en,zh} pairs — language is resolved at render time. */
function _ingestMeterReasons(reasons) {
  _meterReasons = { alert: null, integrity: null, decay: null };
  if (!reasons || typeof reasons !== 'object') return;
  _meterReasons.alert = _reasonPair(reasons.alert);
  _meterReasons.integrity = _reasonPair(reasons.integrity);
  _meterReasons.decay = _reasonPair(reasons.decay);
}

/** Clear the standing reasons at the start of a new turn (player acted). */
function _clearMeterReasons() {
  _meterReasons = { alert: null, integrity: null, decay: null };
}

/** Append the stored reason (if any) to a HUD gauge's title/aria tooltip, and
 *  refresh the WORLD-panel subtext. Called after state_delta stores reasons
 *  (session_update already repainted the panels a frame earlier) and again from
 *  the panel/status renderers so the reason persists across re-renders. */
function _applyMeterReasons() {
  const hud = [
    ['integrity', 'statIntegrityPips'],
    ['alert', 'statNexusGauge'],
    ['decay', 'statDecayGauge'],
  ];
  for (const [key, id] of hud) {
    const el = document.getElementById(id);
    if (!el) continue;
    const reason = _reasonText(_meterReasons[key]);
    // Preserve the base tooltip (value/status) set by the renderers; append the
    // cause on a second line. dataset.baseTitle holds the pristine base.
    let base = el.dataset.baseTitle;
    if (base == null) { base = el.getAttribute('title') || ''; el.dataset.baseTitle = base; }
    if (reason) {
      const full = base ? (base + ' · ' + L('meter_why') + ': ' + reason) : reason;
      el.setAttribute('title', full);
      el.setAttribute('aria-label', full);
    } else if (base) {
      el.setAttribute('title', base);
      el.setAttribute('aria-label', base);
    }
  }
  // WORLD-panel subtext lines are (re)written inline by updateWorldPanel; just
  // patch the existing nodes so a bare state_delta (no session repaint) updates.
  _patchWorldReasonSubtext('nexus_alert', _reasonText(_meterReasons.alert));
  _patchWorldReasonSubtext('fragment_decay', _reasonText(_meterReasons.decay));
}

/** Insert/update/remove a '· why' subtext under a WORLD-panel meter caption.
 *  Idempotent — safe to call on every render and on a bare state_delta. */
function _patchWorldReasonSubtext(meterKey, reason) {
  const host = document.querySelector('.world-meter-reason[data-meter="' + meterKey + '"]');
  if (!host) return;
  if (reason) {
    host.innerHTML = '<span class="world-meter-reason-why">· ' + esc(L('meter_why'))
      + '</span> ' + esc(reason);
    host.hidden = false;
  } else {
    host.innerHTML = '';
    host.hidden = true;
  }
}

/** Pulse the HUD gauges whose value moved this turn, per a state_delta frame.
 *  session_update already repainted the numbers; this only draws the eye to
 *  WHICH end-gating meter changed. No-op under prefersReducedMotion. */
function flashChangedMeters(delta) {
  if (prefersReducedMotion || !delta) return;
  const map = [
    ['integrity', 'statIntegrityPips'],
    ['nexus_alert', 'statNexusGauge'],
    ['fragment_decay', 'statDecayGauge'],
  ];
  for (const [key, id] of map) {
    const pair = delta[key];
    if (!pair || pair.from === pair.to) continue;
    const el = document.getElementById(id);
    if (!el) continue;
    // Restart the animation cleanly if it's already mid-pulse.
    el.classList.remove('meter-flash');
    void el.offsetWidth;                       // force reflow → replay
    el.classList.add('meter-flash');
    el.addEventListener('animationend', () => el.classList.remove('meter-flash'),
      { once: true });
  }
}

/** Tear down the on-screen chips but KEEP any prediction_ready arrivals, so a
 *  prediction that landed during the clear→render gap still lights its chip. */
function clearSuggestedActions() {
  const c = document.getElementById('suggestedActions');
  if (c) c.innerHTML = '';
}

/** Hard reset: chips gone AND the ready set emptied. Use only when the current
 *  suggestion set is spent (player sent an action, game over) — never on the
 *  per-turn `thinking` teardown, which must not lose an in-flight arrival. */
function resetPredictions() {
  clearSuggestedActions();
  _readyPredictions.clear();
}

/** Bilingual chip tooltip: base text plus a state suffix (ready/pending). */
function _saTitle(text, state) {
  if (state === 'ready') return `${text} — ${L('sa_ready')}`;
  if (state === 'pending') return `${text} — ${L('sa_pending')}`;
  return text;
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
  // Resolve the incoming action texts up front, then prune _readyPredictions to
  // just this set. That drops stale ready-flags carried over from a prior turn
  // while PRESERVING any prediction_ready that arrived for one of THESE actions
  // during the clear→render gap (the race the split teardown protects).
  const shown = actions.slice(0, 3)
    .map(a => (a && (a.text || a)) ? (a.text || a) : '')
    .filter(Boolean);
  const shownSet = new Set(shown);
  _readyPredictions.forEach(t => { if (!shownSet.has(t)) _readyPredictions.delete(t); });
  shown.forEach(text => {
    // A prediction may already be ready (e.g. it finished during the tutorial).
    const ready = predicting && _readyPredictions.has(text);
    const state = ready ? 'ready' : (predicting ? 'pending' : '');
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'suggested-action-btn' + (state ? ' ' + state : '');
    btn.dataset.action = text;
    btn.textContent = text;
    btn.title = _saTitle(text, state);
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
      btn.title = _saTitle(text, 'ready');
    }
  });
}

function chooseSuggestedAction(text) {
  const input = document.getElementById('chatInput');
  if (input.disabled) return;
  text = (text || '').trim();
  if (!text) return;

  // Guard the socket first — don't tear down the suggested actions or disable
  // input if the frame can't be sent. Leave everything interactive for a retry.
  if (!wsOpen()) { showReconnectingNotice(); return; }

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

  _pushHistory(text);   // a chosen suggestion is a committed command too
  resetPredictions();  // player committed → the current suggestions are spent
  _setPendingPlayer(addChatMessage(text, 'player'));
  input.value = '';
  disableInput();
  _sendPlayerInput(text);
}

// ================================================================
// INPUT HISTORY + VERB AUTOCOMPLETE (wave 3b)
//
// ArrowUp/Down cycles previously-sent commands (last 50, persisted). On an
// EMPTY input, a subtle row of curated bilingual verb chips appears; Tab
// completes the current ghost suggestion. All motion stays terminal-quiet.
// Arrows are never hijacked while a dialog is open or mid-IME-composition
// (中文 input via e.isComposing), so composing a candidate isn't disturbed.
// ================================================================
const _HISTORY_KEY = 'signal_lost_input_history';
const _HISTORY_MAX = 50;
let sentHistory = [];         // oldest → newest; capped at _HISTORY_MAX
let _historyCursor = -1;      // -1 = live (typing); 0..n-1 = browsing history
let _historyDraft = '';       // the live draft stashed when browsing begins
let _ghostVerb = '';          // current ghost-completed verb, or '' if none

/** Curated verbs (localized via LABELS). These are the ghost/chip candidates. */
const _VERB_KEYS = [
  'verb_look', 'verb_go', 'verb_talk', 'verb_examine',
  'verb_use', 'verb_verify', 'verb_hack', 'verb_hide',
];
function _verbList() { return _VERB_KEYS.map(k => L(k)); }

function _loadHistory() {
  try {
    const raw = localStorage.getItem(_HISTORY_KEY);
    if (!raw) return;
    const arr = JSON.parse(raw);
    if (Array.isArray(arr)) sentHistory = arr.filter(x => typeof x === 'string').slice(-_HISTORY_MAX);
  } catch (e) { sentHistory = []; }
}
function _saveHistory() {
  try { localStorage.setItem(_HISTORY_KEY, JSON.stringify(sentHistory.slice(-_HISTORY_MAX))); } catch (e) {}
}
/** Record a committed command (dedup consecutive repeats) and reset the cursor. */
function _pushHistory(text) {
  const t = (text || '').trim();
  if (!t) return;
  if (sentHistory[sentHistory.length - 1] !== t) {
    sentHistory.push(t);
    if (sentHistory.length > _HISTORY_MAX) sentHistory = sentHistory.slice(-_HISTORY_MAX);
    _saveHistory();
  }
  _historyCursor = -1;
  _historyDraft = '';
}

/** True when a modal dialog is open (arrows/keys must not be hijacked). */
function _anyDialogOpen() { return _dialogStack.length > 0; }

/** Move through history. dir = -1 (older, ArrowUp) or +1 (newer, ArrowDown). */
function _historyStep(input, dir) {
  if (!sentHistory.length) return;
  if (_historyCursor === -1) {
    // Entering history from the live draft — stash it so ArrowDown can return.
    if (dir > 0) return;                    // ArrowDown on live draft: nothing newer
    _historyDraft = input.value;
    _historyCursor = sentHistory.length - 1;
  } else {
    _historyCursor += dir;
  }
  if (_historyCursor >= sentHistory.length) {
    // Past the newest entry — restore the live draft.
    _historyCursor = -1;
    input.value = _historyDraft;
  } else {
    if (_historyCursor < 0) _historyCursor = 0;   // clamp at oldest
    input.value = sentHistory[_historyCursor];
  }
  _clearVerbGhost(input);
  // Put the caret at the end so the recalled line is ready to edit/send.
  const end = input.value.length;
  try { input.setSelectionRange(end, end); } catch (e) {}
}

// ---- Verb ghost suggestion + chips (empty-input affordance) ----

/** Longest verb whose start matches the typed token (case-insensitive), else ''. */
function _verbMatch(value) {
  const v = (value || '').trim();
  if (!v || /\s/.test(v)) return '';         // only suggest on a bare first token
  const lower = v.toLowerCase();
  for (const verb of _verbList()) {
    const vl = verb.toLowerCase();
    if (vl.length > v.length && vl.startsWith(lower)) return verb;
  }
  return '';
}

function _ghostEl() { return document.getElementById('inputGhost'); }

/** Paint the ghost completion (dim tail) behind the input, or clear it. */
function _updateVerbGhost(input) {
  const ghost = _ghostEl();
  if (!ghost) return;
  const match = _verbMatch(input.value);
  _ghostVerb = match;
  if (match) {
    // Show the typed prefix as invisible spacer + the dim remaining tail.
    ghost.innerHTML = `<span class="ghost-typed">${esc(input.value)}</span>` +
                      `<span class="ghost-tail">${esc(match.slice(input.value.length))}</span>`;
    ghost.classList.add('visible');
  } else {
    ghost.classList.remove('visible');
    ghost.innerHTML = '';
  }
}
function _clearVerbGhost(input) {
  _ghostVerb = '';
  const ghost = _ghostEl();
  if (ghost) { ghost.classList.remove('visible'); ghost.innerHTML = ''; }
}

/** Tab accepts the ghost: fill the verb + a trailing space, ready for an object. */
function _acceptVerbGhost(input) {
  if (!_ghostVerb) return false;
  input.value = _ghostVerb + ' ';
  _clearVerbGhost(input);
  const end = input.value.length;
  try { input.setSelectionRange(end, end); } catch (e) {}
  _updateVerbChips(input);
  return true;
}

/** Render / hide the verb-chip row. Chips show only on an EMPTY, focused input
 *  so they never clutter the terminal while the player is typing. */
function _updateVerbChips(input) {
  const row = document.getElementById('verbChips');
  if (!row) return;
  const empty = !input.value;
  const focused = document.activeElement === input;
  if (!empty || !focused || input.disabled) {
    row.classList.remove('visible');
    row.setAttribute('aria-hidden', 'true');
    return;
  }
  if (!row.dataset.built || row.dataset.lang !== currentLang) {
    row.innerHTML = _verbList().map(v =>
      `<button type="button" class="verb-chip" tabindex="-1" ` +
      `onmousedown="event.preventDefault()" onclick="applyVerbChip('${esc(v)}')">${esc(v)}</button>`
    ).join('');
    row.dataset.built = '1';
    row.dataset.lang = currentLang;
  }
  row.classList.add('visible');
  row.setAttribute('aria-hidden', 'false');
}

/** Clicking a chip drops the verb + space into the input and re-focuses it. */
function applyVerbChip(verb) {
  const input = document.getElementById('chatInput');
  if (!input || input.disabled) return;
  input.value = verb + ' ';
  input.focus();
  const end = input.value.length;
  try { input.setSelectionRange(end, end); } catch (e) {}
  _clearVerbGhost(input);
  _updateVerbChips(input);
}

/** Wire the chat input: history nav, ghost completion, chip visibility. */
function _initInputHistory() {
  const input = document.getElementById('chatInput');
  if (!input) return;
  _loadHistory();

  input.addEventListener('keydown', (e) => {
    // Never hijack while a dialog is up or mid-IME-composition (中文 candidates).
    if (_anyDialogOpen() || e.isComposing || e.keyCode === 229) return;
    if (e.key === 'ArrowUp') { e.preventDefault(); _historyStep(input, -1); _updateVerbChips(input); return; }
    if (e.key === 'ArrowDown') { e.preventDefault(); _historyStep(input, +1); _updateVerbChips(input); return; }
    if (e.key === 'Tab' && _ghostVerb) { if (_acceptVerbGhost(input)) e.preventDefault(); return; }
  });

  // Typing resets the history cursor to the live line and refreshes the ghost.
  input.addEventListener('input', () => {
    _historyCursor = -1;
    _updateVerbGhost(input);
    _updateVerbChips(input);
  });
  input.addEventListener('focus', () => { _updateVerbChips(input); _updateVerbGhost(input); });
  input.addEventListener('blur', () => {
    // Defer so a chip's mousedown-click can land before we hide the row.
    setTimeout(() => { _updateVerbChips(input); }, 120);
  });
}

function sendMessage() {
  const input = document.getElementById('chatInput');
  if (input.disabled) return;
  const text = input.value.trim();
  if (!text) return;

  // Guard the socket BEFORE any optimistic UI. If it's closed, keep the typed
  // text in the box, surface a bilingual "reconnecting…" line, and leave the
  // input enabled so the player can resend once the link is back.
  if (!wsOpen()) { showReconnectingNotice(); return; }

  _pushHistory(text);
  _clearVerbGhost(input);

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

  resetPredictions();  // player committed → the current suggestions are spent
  _setPendingPlayer(addChatMessage(text, 'player'));
  input.value = '';
  _updateVerbChips(input);   // input cleared → drop the chip row while disabled
  disableInput();
  _sendPlayerInput(text);
}

// ================================================================
// RETRY LAST ACTION — recoverable turn errors get an inline chat card
// The last player_input is stashed on send and cleared on a successful
// 'narrative'. When a turn-level {type:'error'} arrives, we render an inline
// card (chat visual language, not a toast) carrying the error text plus a
// bilingual "↻ Retry last action" button that re-sends the stored input.
// ================================================================
let _lastPlayerInput = null;   // most recent player command awaiting a reply

/** Stash the command (for retry) and send it over the wire. */
function _sendPlayerInput(text) {
  _lastPlayerInput = text;
  _dismissRetryCard();  // a fresh action supersedes any standing retry offer
  sendWS({ action: 'player_input', text });
}

let _retryCardEl = null;

/** Render (or replace) the inline retry card at the end of the chat log. */
function showRetryCard(message) {
  _dismissRetryCard();
  const container = document.getElementById('chatMessages');
  if (!container) return;
  const card = document.createElement('div');
  card.className = 'chat-msg retry-card';
  card.setAttribute('role', 'alert');
  const canRetry = !!_lastPlayerInput;
  const btnHtml = canRetry
    ? `<button class="cyber-btn retry-card-btn" onclick="retryLastAction()">` +
      `<span class="cyber-btn-text">${esc(L('retry_last_action'))}</span></button>`
    : '';
  card.innerHTML =
    `<div class="msg-prefix">${esc(L('chat_system'))}</div>` +
    `<div class="msg-content">${esc(message || '')}</div>` +
    btnHtml;
  container.appendChild(card);
  _retryCardEl = card;
  card.scrollIntoView({ behavior: prefersReducedMotion ? 'auto' : 'smooth', block: 'start' });
  playBeep(400, 0.04);
}

/** Remove the standing retry card, if any. */
function _dismissRetryCard() {
  if (_retryCardEl && _retryCardEl.parentNode) _retryCardEl.parentNode.removeChild(_retryCardEl);
  _retryCardEl = null;
}

/** Re-send the stored last player command (from the retry card button). */
function retryLastAction() {
  const text = _lastPlayerInput;
  if (!text) { _dismissRetryCard(); return; }
  if (!wsOpen()) { showReconnectingNotice(); return; }
  _dismissRetryCard();
  resetPredictions();  // re-sending the last action → old suggestions are spent
  _setPendingPlayer(addChatMessage(text, 'player'));
  disableInput();
  _sendPlayerInput(text);
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
    // The SFX bus honours the single mute state — no per-tick check needed.
    if (Math.random() < 0.5) playBeep(150 + Math.random() * 130, 0.05 + Math.random() * 0.05, 0.006, 'ambient');
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
/** Brief "signal locking in" scramble before an agent message types out.
 *  Returns the setInterval id so the caller (finalize) can cancel it if a
 *  skip/supersede fires inside the ~300ms window. */
function _decryptReveal(msg, contentEl, done) {
  msg.classList.add('decrypting');
  // Decrypt lock-in two-tone via the shared SFX bus (it honours mute).
  playBeep(420, 0.05, 0.02, 'ambient');
  setTimeout(() => playBeep(900, 0.06, 0.02, 'ambient'), 90); // two-tone lock-in
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
  return t;
}

// A turn can hang: the server may drop mid-turn, or emit a terminal message
// (game_over) that never routes through hideThinking. This watchdog guarantees
// the UI is released after WATCHDOG_MS so the player is never stuck with the
// ticker + ambient beeps running forever and input disabled.
let _turnWatchdog = null;
const _WATCHDOG_MS = 90000;

function _armWatchdog() {
  _clearWatchdog();
  // Opening turn while the tutorial is still up: the real first scene is
  // genuinely in flight and buffered until the tutorial is dismissed, and slow
  // models can legitimately exceed the 90s deadline. Firing here would enable
  // input behind the overlay and leave a bogus 'link went quiet' notice stuck
  // above the opening scene. Don't watchdog the buffered first scene.
  if (_firstSceneArmed) return;
  _turnWatchdog = setTimeout(() => {
    _turnWatchdog = null;
    endTurnUI();
    // Surface a recoverable, bilingual system line — the player can retry.
    showSystemNotice(L('link_quiet'));
  }, _WATCHDOG_MS);
}
function _clearWatchdog() {
  if (_turnWatchdog) { clearTimeout(_turnWatchdog); _turnWatchdog = null; }
}

function showThinking() {
  document.getElementById('thinkingIndicator').style.display = 'flex';
  document.getElementById('chatMessages').scrollTop = document.getElementById('chatMessages').scrollHeight;
  _startThinkingTicker();
  _startAmbient();
  _armWatchdog();
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

/** Idempotent end-of-turn cleanup: stop the wait experience and re-enable input.
 *  Safe to call from any turn-terminating handler (narrative / error / game_over)
 *  and from the watchdog. Clears the hang watchdog too. */
function endTurnUI() {
  _clearWatchdog();
  hideThinking();
  enableInput();
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
function saveGame() {
  const el = document.getElementById('saveName');
  el.value = _defaultSaveName();
  openDialog(document.getElementById('saveDialog'), { initialFocus: 'saveName' });
  requestAnimationFrame(() => { try { el.select(); } catch (_) {} });
  playBeep(1000, 0.04);
}
function confirmSave() {
  const name = document.getElementById('saveName').value.trim() || _defaultSaveName();
  const btn = document.querySelector('#saveDialog .cyber-btn.accent');
  const b = busy(btn, 'saved');           // released by the 'saved' reply / 10s timeout
  _pendingDialogToken = 'saved';          // let an 'error' reply unlock it in-place
  if (!sendWS({ action: 'save_game', save_name: name })) { _pendingDialogToken = null; b.fail(); }
}
function closeSaveDialog() { closeDialog(document.getElementById('saveDialog')); }

function showGameOver(ending, narrative, deathCause) {
  triggerGlitch(); triggerGlitch();
  let label = ending ? `// ${ending.toUpperCase()}` : L('game_over_fallback');
  if (ending === 'death' && deathCause) {
    // Death-cause labels route through LABELS (death_collapse / death_capture /
    // death_unknown); an unrecognized cause falls back to the generic key.
    const causeKeys = { collapse: 'death_collapse', capture: 'death_capture', unknown: 'death_unknown' };
    label = `// ${L(causeKeys[deathCause] || 'death_unknown')}`;
  }
  document.getElementById('gameOverEnding').textContent = label;
  let narr = narrative || '';
  // DEATH is a failure state, not a full story ending — nudge toward reloading.
  if (ending === 'death') {
    narr += (narr ? '\n\n' : '') + L('death_reconnect_nudge');
  }
  document.getElementById('gameOverNarrative').textContent = narr;
  openDialog(document.getElementById('gameOverOverlay'), { dismissible: false });
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
  // Preserve token usage for an agent-role opening; system openings carry none.
  const usage = role === 'system' ? null : (msg.usage || null);
  resumeMessageEl = addTypingMessage(msg.text, role, usage, msg.elapsed_seconds, msg.suggested_actions);
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

// Resolve the current step's target to the first VISIBLE match, so multi-selector
// targets (e.g. the inline neural button on mobile vs. the floating FAB on
// desktop) land on whichever element is actually shown. Returns null if the
// target has no on-screen box (removed, hidden, or zero-size).
function _resolveTutorialTarget(step) {
  for (const el of document.querySelectorAll(step.target)) {
    if (el.getClientRects().length) return el;
  }
  return null;
}

function showTutorialStep() {
  const steps = TUTORIAL_STEPS[currentLang] || TUTORIAL_STEPS.en;
  const step = steps[tutorialStep];
  const textEl = document.getElementById('tutorialText');
  const indicator = document.getElementById('tutorialStepIndicator');
  const skipBtn = document.getElementById('tutorialSkip');
  const nextBtn = document.getElementById('tutorialNext');

  // Activate tab if needed
  if (step.activateTab) {
    const tabBtn = document.querySelector(`[data-panel="${step.activateTab}"]`);
    if (tabBtn) switchPanel(tabBtn);
  }

  // If the highlighted element no longer exists (or is hidden), skip this step
  // gracefully rather than pinning the box to a stale location.
  const target = _resolveTutorialTarget(step);
  if (!target) { nextTutorialStep(); return; }

  // Set content (position is applied by _positionTutorialStep, which also runs
  // on window resize/scroll while the tutorial is active).
  const isLast = tutorialStep === steps.length - 1;
  indicator.textContent = `${L('tutorial_step')} ${tutorialStep + 1} / ${steps.length}`;
  textEl.innerHTML = step.text;
  skipBtn.textContent = L('tutorial_skip');
  nextBtn.textContent = isLast ? L('tutorial_finish') : L('tutorial_next');

  // Replay the tooltip entrance animation for this step.
  const tooltip = document.getElementById('tutorialTooltip');
  tooltip.style.animation = 'none';
  tooltip.offsetHeight; // force reflow
  tooltip.style.animation = '';

  _positionTutorialStep();
}

// Position the highlight box + tooltip against the current step's live target
// geometry. Called on step entry AND on window resize/scroll/tab-switch so the
// box tracks a target that moved. Guards a vanished target by advancing the step.
function _positionTutorialStep() {
  if (!tutorialActive) return;
  const steps = TUTORIAL_STEPS[currentLang] || TUTORIAL_STEPS.en;
  const step = steps[tutorialStep];
  if (!step) return;

  const highlight = document.getElementById('tutorialHighlight');
  const tooltip = document.getElementById('tutorialTooltip');

  const target = _resolveTutorialTarget(step);
  if (!target) { nextTutorialStep(); return; }

  const rect = target.getBoundingClientRect();

  // Position highlight
  highlight.style.left = rect.left - 4 + 'px';
  highlight.style.top = rect.top - 4 + 'px';
  highlight.style.width = rect.width + 8 + 'px';
  highlight.style.height = rect.height + 8 + 'px';

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

// Keep the highlight/tooltip glued to their target when the viewport changes
// under a live tutorial: window resize, or scrolling inside any panel that the
// highlighted element rides in. rAF-throttled so a scroll storm coalesces into
// one layout pass. Registered once; the tutorialActive guard makes it a no-op
// otherwise. Scroll uses capture:true to catch inner scroll containers (the
// info-panel body), which don't bubble scroll events.
let _tutorialRepositionQueued = false;
function _scheduleTutorialReposition() {
  if (!tutorialActive || _tutorialRepositionQueued) return;
  _tutorialRepositionQueued = true;
  requestAnimationFrame(() => {
    _tutorialRepositionQueued = false;
    _positionTutorialStep();
  });
}
window.addEventListener('resize', _scheduleTutorialReposition);
window.addEventListener('scroll', _scheduleTutorialReposition, { capture: true, passive: true });

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
  // Opening the TRACE tab acknowledges any pending discovery — stop its pulse.
  if (btn.dataset.panel === 'traces') btn.classList.remove('trace-pulse');
  document.getElementById('panel-' + btn.dataset.panel).classList.add('active');
  playBeep(900, 0.02);
  // A tab switch can move the highlighted tutorial target (a panel tab or its
  // content) — re-glue the highlight box to its new geometry.
  _scheduleTutorialReposition();
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

function navMenuIsOpen() {
  const menu = document.getElementById('navMenu');
  return !!(menu && menu.classList.contains('open'));
}

function navMenuAction(which) {
  closeNavMenu();
  if (which === 'tutorial') startTutorial();
  else if (which === 'save') saveGame();
  else if (which === 'settings') openSettings();
  else if (which === 'menu') showMenu();
}

// Dismiss the nav menu on outside click. (Escape is handled by the single
// keydown router in the KEYBOARD SHORTCUTS section below.)
document.addEventListener('click', (e) => {
  const wrap = document.querySelector('.nav-menu-wrap');
  if (wrap && !wrap.contains(e.target)) closeNavMenu();
});

// Two-line teaching empty state: bare line (already localized/escaped upstream)
// plus a spoiler-safe hint that teaches the loop. Both strings route through L().
// `mainKey` may be a pre-resolved string or a label key; `hintKey` is a label key.
function panelEmptyHint(mainKey, hintKey) {
  const main = (mainKey && LABELS.en[mainKey]) ? L(mainKey) : (mainKey || '');
  return `<div class="panel-empty">${esc(main)}`
       + `<span class="panel-empty-hint">${esc(L(hintKey))}</span></div>`;
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
  const w = session.world_state || {};
  const integrity = p.integrity || {};

  // Integrity pips: filled █ and empty ░
  const cur = integrity.current || 0, max = integrity.max || 3;
  let pips = '';
  for (let i = 0; i < max; i++) {
    pips += i < cur ? '<span class="pip filled">█</span>' : '<span class="pip empty">░</span>';
  }
  const pipsEl = document.getElementById('statIntegrityPips');
  if (pipsEl) {
    pipsEl.innerHTML = pips;
    // Icon-only mode (<480px) hides the label, so keep an accessible tooltip.
    const pipTitle = L('integrity').toUpperCase() + ': ' + cur + ' / ' + max;
    pipsEl.setAttribute('title', pipTitle);
    pipsEl.setAttribute('aria-label', L('integrity').toUpperCase() + ' ' + cur + ' / ' + max);
    pipsEl.dataset.baseTitle = pipTitle;
  }

  // --- Banded mini-gauges (mirror WORLD panel semantics) ---
  const alert = w.nexus_alert || {};
  const alertVal = Math.max(0, Math.min(100, Number(alert.current) || 0));
  const alertStatus = (currentLang === 'zh' && alert.status_zh) ? alert.status_zh : localizeAlertStatus(alert.status);
  renderBandedGauge('statNexusGauge', alertVal,
    L('hud_nexus') + ' · ' + alertStatus + ' · ' + alertVal + '%');

  // Fragment decay — always shown (no >0 guard), framed as signal coherence.
  const decay = w.fragment_decay || {};
  const decayVal = Math.max(0, Math.min(100, Number(decay.current) || 0));
  const decayStatus = (currentLang === 'zh' && decay.status_zh) ? decay.status_zh : localizeDecayStatus(decay.status);
  renderBandedGauge('statDecayGauge', decayVal,
    L('hud_coherence') + ' · ' + decayStatus + ' · ' + decayVal + '%');

  // --- In-world clock: "Day N · <period> · HH:MM" with a thin fill
  //     for the progress through the current 360-min period. ---
  const t = w.time || {};
  const day = t.day || 1;
  const periodDisplay = localizeData('time', t.period) || t.period || '';
  const pIcon = TIME_ICONS[(t.period || '').toLowerCase()] || '';
  const clockStr = t.clock || '';
  const parts = [];
  parts.push(L('hud_day') + ' ' + day);
  if (periodDisplay) parts.push((pIcon ? pIcon + ' ' : '') + periodDisplay);
  if (clockStr) parts.push(clockStr);
  const clockEl = document.getElementById('statClock');
  if (clockEl) {
    // period_minutes runs 0-360 within a period; thin fill shows progress.
    const pm = Math.max(0, Math.min(360, Number(t.period_minutes) || 0));
    const pct = Math.round((pm / 360) * 100);
    clockEl.innerHTML = '<span class="hud-clock-text">' + esc(parts.join(' · ')) + '</span>' +
      '<span class="hud-clock-fill" style="width:' + pct + '%"></span>';
    clockEl.setAttribute('title', parts.join(' · '));
  }

  // Location (district + area) — set title on truncated values for full text.
  const districtVal = l.district || '—';
  const areaVal = l.area || '—';
  setText('statLocation', districtVal);
  setText('statArea', areaVal);
  const locEl = document.getElementById('statLocation');
  if (locEl) locEl.setAttribute('title', districtVal);
  const areaEl = document.getElementById('statArea');
  if (areaEl) areaEl.setAttribute('title', areaVal);

  // Translate status bar labels
  setText('statLabelIntegrity', L('integrity').toUpperCase());
  setText('statLabelNexus', L('hud_nexus').toUpperCase());
  setText('statLabelDecay', L('hud_signal').toUpperCase());
  setText('statLabelClock', L('hud_time').toUpperCase());
  setText('statLabelLocation', L('location').toUpperCase());
  setText('statLabelArea', L('area').toUpperCase());

  // Re-apply any standing meter-why reasons onto the freshly-rendered gauge
  // tooltips (the renderers above reset dataset.baseTitle). Persists the cause
  // across a mid-turn session repaint (e.g. reconnect resync) until next turn.
  _applyMeterReasons();
}

/** Render a banded mini-gauge into `elId`: a track with tick marks at 25/50/75/90
 *  and a fill whose color follows the cyan->yellow->orange->red ramp. `label` is the
 *  bilingual tooltip/aria text. */
function renderBandedGauge(elId, value, label) {
  const el = document.getElementById(elId);
  if (!el) return;
  const v = Math.max(0, Math.min(100, Number(value) || 0));
  const color = gaugeBandColor(v);
  let ticks = '';
  for (const tk of GAUGE_TICKS) {
    ticks += '<span class="hud-gauge-tick" style="left:' + tk + '%"></span>';
  }
  el.innerHTML =
    '<span class="hud-gauge-track">' + ticks +
      '<span class="hud-gauge-fill" style="width:' + v + '%;background:' + color +
      ';box-shadow:0 0 6px ' + color + '"></span>' +
    '</span>';
  el.setAttribute('title', label);
  el.setAttribute('aria-label', label);
  // Refresh the pristine base so _applyMeterReasons appends the cause onto the
  // just-rendered value/status, not a stale one from a prior render.
  el.dataset.baseTitle = label;
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

  // Whole-panel teaching empty: when nothing has been learned in any section,
  // lead with a single two-line hint that teaches the loop before the (compact)
  // per-section "None discovered" rows.
  const totalKnown = sections.reduce((n, sec) => n + ((k[sec.key] || []).length), 0);
  if (totalKnown === 0) {
    html += panelEmptyHint('empty_know', 'empty_know_hint');
  }

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

// ---------- TRACES PANEL — Layered Trace Ladder + Descent depth gauge ----------
//
// The five real story layers (The Surface → The Full Truth) render as labeled
// bands. Each *discovered* trace is bucketed under its TRUE layer by parsing the
// L# from its real id (TRACE-L3-07 → layer 3) — ids are never renumbered. Layers
// deeper than the player's reached depth render as ONE sealed row (counts only);
// we never emit '[???]' text or any undiscovered trace name (hard spoiler rule).
//
// Per-layer denominators come from the server-reconciled scaffold (traces.layers
// [*].progress, canonically synced to engine LIVE_TRACES_PER_LAYER) — never a
// hard-coded 47.

// Parse the layer number from a trace id like "TRACE-L3-07" → 3; null if absent.
function traceLayerNum(id) {
  const m = /-L(\d+)-/.exec(String(id || ''));
  return m ? parseInt(m[1], 10) : null;
}

// Parse the layer number from a scaffold layer key like "layer_3_severance" → 3.
function scaffoldLayerNum(key) {
  const m = /layer[_-]?(\d+)/i.exec(String(key || ''));
  return m ? parseInt(m[1], 10) : null;
}

// Deepest layer the player has reached: max L# across discovered ids, 0 if none.
// Replicates the engine's depth derivation without touching hidden gate keys.
function computeDeepestLayer(session) {
  const discovered = (session && session.traces && session.traces.discovered) || [];
  let deepest = 0;
  for (const tr of discovered) {
    const n = traceLayerNum(tr && tr.id);
    if (n && n > deepest) deepest = n;
  }
  return deepest;
}

const TRACE_LADDER_LAYERS = 5;

// Compact 0-5 Descent gauge: current layer's flavor name lit, deeper segments
// unlit and UNLABELED (spoiler-safe — no deeper layer names revealed).
function renderDescentGauge(deepest) {
  let segs = '';
  for (let n = 1; n <= TRACE_LADDER_LAYERS; n++) {
    const reached = n <= deepest;
    const isCurrent = n === deepest;
    // Only the CURRENT (deepest reached) layer is named; reached-but-shallower
    // layers stay lit-but-unlabeled, deeper layers unlit-and-unlabeled.
    const label = isCurrent ? esc(L('trace_layer_' + n)) : '';
    const cls = 'descent-seg' + (reached ? ' reached' : '') + (isCurrent ? ' current' : '');
    segs += `<span class="${cls}" style="--depth:${n}">${label}</span>`;
  }
  return `<div class="descent-gauge" role="img" aria-label="${esc(L('descent'))} ${deepest}/${TRACE_LADDER_LAYERS}">
    <span class="descent-label">${esc(L('descent'))}</span>
    <span class="descent-track">${segs}</span>
  </div>`;
}

// Segmented progress bar for one layer: `total` pips, `count` filled. Neon fill
// intensifies with depth (dim cyan at L1 → hot magenta at L5) via --depth.
function renderTraceSegments(count, total, layerNum) {
  const n = Math.max(0, Number(total) || 0);
  const c = Math.max(0, Math.min(n, Number(count) || 0));
  let pips = '';
  for (let i = 0; i < n; i++) {
    pips += `<span class="trace-seg${i < c ? ' on' : ''}"></span>`;
  }
  return `<span class="trace-segbar" style="--depth:${layerNum}">${pips}</span>`;
}

// Parse "3/8" style progress → {count, total}. Falls back to slot count.
function parseLayerProgress(layer, discoveredCount) {
  const raw = String((layer && layer.progress) || '');
  const m = /(\d+)\s*\/\s*(\d+)/.exec(raw);
  if (m) return { count: parseInt(m[1], 10), total: parseInt(m[2], 10) };
  const slots = (layer && layer.traces && typeof layer.traces === 'object')
    ? Object.keys(layer.traces).length : 0;
  return { count: discoveredCount, total: slots };
}

function updateTracesPanel(traces) {
  const t = traces || {};
  const discovered = Array.isArray(t.discovered) ? t.discovered : [];
  const layersObj = (t.layers && typeof t.layers === 'object') ? t.layers : {};

  // Build an ordered [1..5] view of the scaffold layers (key → number).
  const layerEntries = Object.entries(layersObj)
    .map(([key, layer]) => ({ num: scaffoldLayerNum(key), layer }))
    .filter(e => e.num != null)
    .sort((a, b) => a.num - b.num);

  // Bucket discovered traces under their TRUE layer by real-id L# parsing.
  const byLayer = {};
  for (const tr of discovered) {
    const n = traceLayerNum(tr && tr.id);
    if (!n) continue;
    (byLayer[n] = byLayer[n] || []).push(tr);
  }

  const deepest = computeDeepestLayer({ traces: t });

  // Header: title + total + Descent gauge.
  let html = `<div class="panel-section">
    <div class="panel-section-title">${L('traces_of_truth')}</div>
    <div class="panel-row"><span class="panel-key">${L('discovered')}</span><span class="panel-val cyan">${discovered.length}</span></div>
    ${renderDescentGauge(deepest)}
  </div>`;

  if (discovered.length === 0 && deepest === 0) {
    html += panelEmptyHint('empty_trace', 'empty_trace_hint');
    document.getElementById('panel-traces-body').innerHTML = html;
    applyPanelSearch('traces');
    return;
  }

  // Render each of the five bands in depth order.
  for (const { num, layer } of layerEntries) {
    const bucket = byLayer[num] || [];
    const prog = parseLayerProgress(layer, bucket.length);
    const total = prog.total;
    const name = esc(L('trace_layer_' + num));

    if (num > deepest) {
      // Sealed row: counts only. NEVER the gated layer flavor name (that would
      // spoil the plot twists) — render a neutral redacted placeholder instead,
      // matching the descent gauge which leaves deeper layers unlabeled.
      html += `<div class="trace-band locked" style="--depth:${num}">
        <div class="trace-band-header">
          <span class="trace-band-name locked-name">▓▓▓▓▓</span>
          <span class="trace-band-lock">[${esc(L('trace_locked'))}] ? / ${total}</span>
        </div>
      </div>`;
      continue;
    }

    // Open band: name, segmented bar, count, and the real discovered traces.
    html += `<div class="trace-band open" style="--depth:${num}">
      <div class="trace-band-header">
        <span class="trace-band-name">${name}</span>
        <span class="trace-band-count">${bucket.length} / ${total}</span>
      </div>
      ${renderTraceSegments(bucket.length, total, num)}`;

    // Discovered trace lines — keep REAL ids, do not renumber.
    for (const tr of bucket) {
      const id = esc(tr && tr.id ? tr.id : '');
      const desc = esc((tr && tr.description) || '');
      const turn = tr && tr.turn
        ? `<span class="dim"> (${esc(L('turn'))} ${esc(tr.turn)})</span>` : '';
      html += `<div class="trace-item discovered" style="--depth:${num}">
        <span class="trace-item-id">${id}</span>
        <span class="trace-item-desc">${desc}${turn}</span>
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

  // Teaching hint above the slot grid when the pack is empty.
  if (items.length === 0) {
    html += `<div class="panel-empty-lead panel-empty-hint">${esc(L('empty_items_hint'))}</div>`;
  }

  // Render all slots. Items are stored without a stable `slot` field, so render
  // them by position; an item's display name may be under `name` or `item`.
  const slotCount = Math.max(maxSlots, items.length);
  for (let s = 1; s <= slotCount; s++) {
    const item = items.find(i => i.slot === s) || items[s - 1];
    if (item) {
      const itemName = item.name || item.item || '?';
      const icon = ITEM_ICONS[(item.type || '').toLowerCase()] || '\u25A0';
      html += `<div class="inv-slot filled">
        <div class="inv-slot-header">${icon} <span class="cyan">[${s}] ${esc(itemName)}</span></div>
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

// Collapse duplicate NPC entries (the engine occasionally promotes the same
// person twice — e.g. once from a scene mention and once from update_npc — so the
// tracker showed "Mira" twice with diverging trust/notes). Key by normalized name
// and merge so the richest, non-empty fields win.
function _dedupNpcList(list) {
  const seen = new Map();
  for (const npc of list) {
    if (!npc || typeof npc !== 'object') continue;
    const key = _avNorm(npc.name || npc.id).replace(/\s+/g, '');
    if (!key) { continue; }
    const prev = seen.get(key);
    if (!prev) { seen.set(key, { ...npc }); continue; }
    const merged = { ...prev };
    for (const [k, v] of Object.entries(npc)) {
      const empty = v == null || v === '' || v === 'none'
        || (Array.isArray(v) && v.length === 0);
      if (!empty) merged[k] = v;  // later/non-empty value wins
    }
    seen.set(key, merged);
  }
  return [...seen.values()];
}

function updateNetworkPanel(npcs) {
  const n = npcs || {};
  const npcList = _dedupNpcList(n.npcs || []);

  let html = `<div class="panel-section"><div class="panel-section-title">${L('npc_tracker')} (${npcList.length})</div>`;

  if (npcList.length === 0) {
    html += panelEmptyHint('no_npcs', 'empty_npc_hint');
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

  // NEXUS Alert — always shown (a primary fail meter; capture at 100). Runs 0-100.
  const alertVal = Math.max(0, Math.min(100, alert.current || 0));
  {
    const alertPct = alertVal;
    // Prefer server-supplied status_zh in 中文; fall back to the label map.
    const alertStatusDisplay = (currentLang === 'zh' && alert.status_zh)
      ? alert.status_zh : localizeAlertStatus(alert.status);
    html += `<div class="panel-section"><div class="panel-section-title">${L('nexus_alert')}</div>
      <div class="panel-row"><span class="panel-key">${L('status')}</span>
        <span class="panel-val ${alertColor(alert.status)}">${esc(alertStatusDisplay)}</span></div>
      <div class="progress-bar"><div class="progress-fill alert-gradient" style="width:${alertPct}%"></div></div>
      <div class="dim" style="font-size:11px;text-align:right">${alertVal}%</div>
      ${bandCaption(ALERT_THRESHOLDS, alertVal, alertStatusDisplay)}
      <div class="world-meter-reason" data-meter="nexus_alert" hidden></div>
    </div>`;
  }

  // Fragment Decay — always shown, framed as signal coherence (no >0 guard).
  const decayVal = Math.max(0, Math.min(100, decay.current || 0));
  {
    const decayStatusDisplay = (currentLang === 'zh' && decay.status_zh)
      ? decay.status_zh : localizeDecayStatus(decay.status);
    html += `<div class="panel-section"><div class="panel-section-title">${L('fragment_decay')}</div>
      <div class="panel-row"><span class="panel-key">${L('status')}</span>
        <span class="panel-val">${esc(decayStatusDisplay)}</span></div>
      <div class="progress-bar"><div class="progress-fill decay-gradient" style="width:${decayVal}%"></div></div>
      <div class="dim" style="font-size:11px;text-align:right">${decayVal}%</div>
      ${bandCaption(DECAY_THRESHOLDS, decayVal, decayStatusDisplay)}
      <div class="world-meter-reason" data-meter="fragment_decay" hidden></div>
    </div>`;
  }

  // District access
  const districts = w.district_access || [];
  if (districts.length === 0) {
    html += `<div class="panel-section"><div class="panel-section-title">${L('district_access')}</div>`
          + panelEmptyHint('empty_area', 'empty_area_hint')
          + `</div>`;
  } else {
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

  if (!html) html = panelEmptyHint('world_nominal', 'empty_world_hint');
  document.getElementById('panel-world').innerHTML = html;
  // The innerHTML rewrite recreated the (hidden) reason hosts — refill them from
  // the standing meter-why store so a mid-turn repaint keeps the cause visible.
  _applyMeterReasons();
}

// ---------- LOG PANEL (matches TUI LogPanel — tags, expandable, reverse order) ----------

function updateLogPanel(log) {
  const l = log || {};
  const entries = l.entries || [];

  let html = `<div class="panel-section"><div class="panel-section-title">${L('session_log')} (${entries.length})</div>`;

  if (entries.length === 0) {
    html += panelEmptyHint('no_log', 'empty_log_hint');
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
        tokenHtml = `<span class="conv-tokens">${(t.total || 0).toLocaleString()} ${esc(L('tokens_short'))} · ${_formatCost(cost)}</span>`;
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
// DIALOG MANAGER — shared open/close, focus trap, deterministic stack
// ================================================================
// One mechanism behind every modal overlay. Each entry is the .overlay
// element plus whether Esc may dismiss it and how to close it. The
// stack's LAST entry is the topmost dialog — Esc and the focus trap
// only ever act on that one.
const _dialogStack = [];

const _FOCUSABLE_SEL = [
  'a[href]', 'button:not([disabled])', 'input:not([disabled])',
  'select:not([disabled])', 'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',');

function _dialogFocusables(el) {
  return Array.from(el.querySelectorAll(_FOCUSABLE_SEL))
    .filter(n => n.offsetParent !== null || n === document.activeElement);
}

/**
 * Open a modal overlay: reveal it, remember the invoker, move focus in,
 * and register it as the topmost trap target.
 *   opts.dismissible  — Esc / backdrop may close it (default true)
 *   opts.onClose      — called by closeDialog() to hide it (defaults to
 *                       toggling style.display); keeps per-dialog cleanup
 *                       (e.g. settings snapshot restore) working.
 *   opts.initialFocus — element (or id) to focus instead of the first focusable
 *   opts.display      — display value used to reveal (default 'flex')
 */
function openDialog(el, opts) {
  if (!el) return;
  opts = opts || {};
  // Already open? just re-focus.
  if (_dialogStack.some(e => e.el === el)) return;
  const invoker = document.activeElement;
  el.style.display = opts.display || 'flex';
  const entry = {
    el,
    dismissible: opts.dismissible !== false,
    onClose: typeof opts.onClose === 'function' ? opts.onClose : null,
    invoker: (invoker && invoker !== document.body) ? invoker : null,
  };
  _dialogStack.push(entry);
  // Focus the requested target, else the first focusable in the card.
  let target = opts.initialFocus;
  if (typeof target === 'string') target = document.getElementById(target);
  if (!target) {
    const card = el.querySelector('.dialog') || el;
    target = _dialogFocusables(card)[0] || card;
  }
  // Defer so display:flex has taken effect (offsetParent is live).
  requestAnimationFrame(() => { try { target.focus(); } catch (_) {} });
}

/** Close a modal overlay: hide it, unwind the stack, restore focus. */
function closeDialog(el) {
  if (!el) return;
  const idx = _dialogStack.findIndex(e => e.el === el);
  if (idx === -1) {
    // Not tracked (opened the legacy way) — just hide it.
    el.style.display = 'none';
    return;
  }
  const entry = _dialogStack.splice(idx, 1)[0];
  if (entry.onClose) entry.onClose();
  else el.style.display = 'none';
  // Restore focus to whoever opened it, if still in the document.
  const inv = entry.invoker;
  if (inv && document.contains(inv)) {
    requestAnimationFrame(() => { try { inv.focus(); } catch (_) {} });
  }
}

/** The topmost open dialog entry, or null. */
function _topDialog() {
  return _dialogStack.length ? _dialogStack[_dialogStack.length - 1] : null;
}

// ================================================================
// SHORTCUT CHEAT-SHEET (wave 3b)
// A '?' on an empty input (with no dialog open) documents the existing
// bindings. Built through the shared openDialog() manager; all rows are
// keyed via LABELS so the sheet is fully bilingual. Additive: it documents
// bindings that already exist — it introduces none.
// ================================================================
const _SHORTCUT_ROWS = [
  { keys: ['1', '–', '9'], label: 'shortcut_panels' },
  { keys: ['t'], label: 'shortcut_focus_input' },
  { keys: ['↑', '↓'], label: 'shortcut_history' },
  { keys: ['Tab'], label: 'shortcut_complete' },
  { keys: ['Space'], label: 'shortcut_skip' },
  { keys: ['Ctrl', '+', 'S'], label: 'shortcut_save' },
  { keys: ['?'], label: 'shortcut_cheatsheet' },
  { keys: ['Esc'], label: 'shortcut_close_dialog' },
];

/** (Re)build the cheat-sheet body from LABELS in the current language. */
function _renderShortcutSheet() {
  const body = document.getElementById('shortcutSheetBody');
  if (!body) return;
  body.innerHTML = _SHORTCUT_ROWS.map(row => {
    const keys = row.keys.map(k => `<kbd class="shortcut-key">${esc(k)}</kbd>`).join('');
    return `<div class="shortcut-row">` +
           `<span class="shortcut-keys">${keys}</span>` +
           `<span class="shortcut-desc">${esc(L(row.label))}</span>` +
           `</div>`;
  }).join('');
}

function openShortcutSheet() {
  const el = document.getElementById('shortcutSheet');
  if (!el) return;
  const titleEl = document.getElementById('shortcutSheetTitle');
  if (titleEl) titleEl.textContent = L('shortcuts_title');
  _renderShortcutSheet();
  openDialog(el);
}
function closeShortcutSheet() { closeDialog(document.getElementById('shortcutSheet')); }

/** Trap Tab / Shift+Tab within the topmost dialog card. */
function _dialogTrapTab(e) {
  const top = _topDialog();
  if (!top) return;
  const card = top.el.querySelector('.dialog') || top.el;
  const items = _dialogFocusables(card);
  if (items.length === 0) { e.preventDefault(); return; }
  const first = items[0], last = items[items.length - 1];
  const active = document.activeElement;
  // If focus somehow escaped the dialog, pull it back in.
  if (!card.contains(active)) {
    e.preventDefault();
    (e.shiftKey ? last : first).focus();
    return;
  }
  if (e.shiftKey && active === first) { e.preventDefault(); last.focus(); }
  else if (!e.shiftKey && active === last) { e.preventDefault(); first.focus(); }
}

// ================================================================
// KEYBOARD SHORTCUTS
// ================================================================

// SINGLE keydown router. Order of authority (highest first):
//   1. Tab / Shift+Tab while a modal dialog is open → focus trap
//   2. Escape → close the topmost DISMISSIBLE dialog, else the nav menu,
//      else the companion panel, else skip the in-flight typewriter
//   3. any modal dialog open → swallow everything else (no game shortcuts)
//   4. game shortcuts (only on the game screen): Space skip, 1-9 tabs,
//      t focus chat, Ctrl/Cmd+S save
document.addEventListener('keydown', (e) => {
  const top = _topDialog();

  // (1) Focus trap — keep Tab cycling inside the topmost dialog card.
  if (e.key === 'Tab' && top) { _dialogTrapTab(e); return; }

  // (2) Escape router.
  if (e.key === 'Escape') {
    if (top) {
      if (top.dismissible) closeDialog(top.el);
      return; // a modal is up (dismissible or not) — Esc goes no further
    }
    if (navMenuIsOpen()) { closeNavMenu(); return; }
    if (companionOpen) { closeCompanion(); return; }
    // Nothing to close — if narration is typing out, Esc skips it to the end.
    if (_activeTyper) { _finalizeActiveTyper(); e.preventDefault(); return; }
    return;
  }

  // (3) A modal dialog owns all other keys while it is open.
  if (top) return;

  // (4) Game shortcuts — only while actually playing.
  if (!document.getElementById('gameScreen').classList.contains('active')) return;

  // Don't let game shortcuts fire while typing in ANY field (chat, companion,
  // or the panel search bars) — number keys must type, not switch tabs.
  const active = document.activeElement;
  const isInput = !!active && (
    active.tagName === 'INPUT' ||
    active.tagName === 'TEXTAREA' ||
    active.isContentEditable
  );
  // Space skips the in-flight typewriter — but only when the player isn't
  // focused in a text field (there Space must type a literal space).
  if ((e.key === ' ' || e.code === 'Space') && _activeTyper && !isInput) {
    _finalizeActiveTyper(); e.preventDefault(); return;
  }
  const num = parseInt(e.key);
  if (num >= 1 && num <= 9 && !e.ctrlKey && !e.metaKey && !isInput) {
    const tabs = document.querySelectorAll('.panel-tab');
    if (tabs[num - 1]) { switchPanel(tabs[num - 1]); e.preventDefault(); }
  }
  if (e.key === 't' && !isInput) { document.getElementById('chatInput').focus(); e.preventDefault(); }
  if (e.key === 's' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); saveGame(); }
  // '?' opens the shortcut cheat-sheet — allowed either outside any field, or
  // while focused in the EMPTY chat input (so it doesn't hijack typed '?'). No
  // dialog is open here (step (3) already returned), matching the spec.
  if (e.key === '?' && !e.ctrlKey && !e.metaKey && !e.altKey) {
    const chat = document.getElementById('chatInput');
    const inEmptyChat = active === chat && chat && !chat.value;
    if (!isInput || inEmptyChat) { e.preventDefault(); openShortcutSheet(); }
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
  // Restore a saved session token for auto-login; the ws 'init' handshake
  // validates it. Optimistically show the stored username so the menu doesn't
  // flash "sign in" before the server confirms (status authed) or clears it.
  authToken = localStorage.getItem(AUTH_TOKEN_KEY) || null;
  if (authToken) currentUser = localStorage.getItem(AUTH_USER_KEY) || null;
  renderAccountWidget();
  _initInputHistory();   // wire input history nav + verb autocomplete
  restoreCompanionHistory();   // repaint any persisted companion transcript
  runBootSequence();
});

// Start music on first user interaction (browsers require gesture for AudioContext)
function _initMusicOnce() {
  // Resume the shared SFX AudioContext on the first user gesture (autoplay).
  if (typeof MusicEngine !== 'undefined' && typeof MusicEngine.resumeSfx === 'function') MusicEngine.resumeSfx();
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
