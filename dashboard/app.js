// ========== STATE ==========
let currentView = 'grid';
let filters = {
  status: 'all',
  phase: 'all',
  passive: 'all',
  search: ''
};

const PHASE_COLORS = {
  1: '#1f6feb',
  2: '#238636',
  3: '#d97706',
  4: '#dc2626'
};

const STATUS_COLORS = {
  done: '#34d399',
  next: '#fbbf24',
  planned: '#6b7a96'
};

const STATUS_LABELS = {
  done: '已完成',
  next: '进行中',
  planned: '计划中'
};

const PASSIVE_LABELS = {
  yes: '纯被动',
  no: '非被动',
  partial: '部分被动',
  analysis: '分析型',
  display: '展示型',
  tbd: '待定'
};

const PHASE_LABELS = {
  1: '第一阶段',
  2: '第二阶段',
  3: '第三阶段',
  4: '第四阶段'
};

const PHASE_TITLE_LABELS = {
  1: '二维基础研究',
  2: '二维机构升级',
  3: '三维扩展验证',
  4: '硬件落地'
};

const TAG_LABELS = {
  'mujoco': 'MuJoCo',
  'contact': '接触',
  'baseline': '基线',
  'limit-cycle': '极限环',
  'pure-passive': '纯被动',
  'theory': '理论',
  'poincare': 'Poincare',
  'knee': '膝关节',
  'proof': '证明',
  'hybrid-dynamics': '混合动力学',
  'key-evidence': '关键证据',
  'presentation': '展示',
  'real-contact': '真实接触',
  'failure-analysis': '失败分析',
  'quasi-passive': '准被动',
  'assist': '辅助',
  'stable': '稳定',
  'ankle': '踝关节',
  'rolling-foot': '滚动足',
  'terrain': '地形',
  'robustness': '鲁棒性',
  'basin-scan': '吸引域扫描',
  'energy': '能量',
  'floquet': 'Floquet',
  'analysis': '分析',
  'sensitivity': '敏感性',
  'tolerance': '容差',
  'decision-gate': '决策门',
  'control': '控制',
  'archived': '已归档',
  'lessons': '经验',
  'bang-bang': 'Bang-Bang',
  'energy-target': '能量目标',
  'key-result': '关键结果',
  'grid-search': '网格搜索',
  'optimization': '优化',
  'arms': '摆臂',
  'mechanism': '机构',
  'recovery': '恢复',
  'root-cause': '根因',
  'monotonicity': '单调性',
  'spring': '弹簧',
  'elastic': '弹性',
  'direct-drive': '直驱',
  'resonance': '共振',
  'motor': '电机',
  'dynamics': '动力学',
  'friction': '摩擦',
  'compensation': '补偿',
  'sensor': '传感器',
  'estimation': '状态估计',
  'next-up': '下一步',
  'lateral': '侧向',
  'coronal-plane': '冠状面',
  'negative-result': '负结果',
  'abduction': '外展',
  'active-lateral': '主动侧向',
  'step-width': '步宽',
  'perturbation': '扰动',
  'hardware': '硬件',
  'motor-selection': '电机选型',
  'parameter-estimation': '参数辨识',
  'domain-randomization': '域随机化',
  'transfer': '迁移',
  'field-test': '实地测试',
  'final': '最终验证'
};

const VERSION_TITLE_LABELS = {
  V01: 'MuJoCo 指南针步态初始搭建',
  V02: '无膝轮极限环对照',
  V03: '指南针步态极限环对照',
  V04: '带膝行走器极限环',
  V05: '混合动力学纯被动证明',
  V06: 'MVE 最小机械表达',
  V07: '真实接触纯被动探索',
  V08: '准被动弱补能探索',
  V09: '准被动稳定行走',
  V10: '滚动足仿生步态',
  V11: '地形与扰动鲁棒性',
  V12: '能量与 CoT 横向分析',
  V13: '参数敏感性图谱',
  'V13.5': '髋部控制律重设计（已归档）',
  V13b: 'Floquet 长程极限环辨识',
  'V13.6': '事件驱动 FSM 髋部控制',
  'V13.6.1': 'FSM 阶段参数搜索',
  V14: '被动摆臂（孤立点验证）',
  V14b: 'FSM + 被动摆臂回流',
  V14c: '摆臂质量减重扫描',
  V15: '髋部 SEA / 弹性肌腱',
  'V15.1': 'SEA 直驱实现',
  V16: '一阶电机动力学（L1）',
  'V13.7': '前馈摩擦补偿',
  V17: '传感器闭环 / 状态估计',
  V18: '三维侧向被动稳定探索',
  V19: '髋外展辅助',
  V20: '步宽调节控制',
  V21: '三维扰动鲁棒性量化',
  V22: '硬件设计 v1',
  V23: '系统辨识',
  V24: '仿真到现实迁移',
  V25: '实地行走验证'
};

function statusLabel(status) {
  return STATUS_LABELS[status] || status || '未知';
}

function passiveLabel(passive) {
  return PASSIVE_LABELS[passive] || passive || '未知';
}

function phaseLabel(phase) {
  return PHASE_LABELS[phase.id || phase] || `第${phase.id || phase}阶段`;
}

function phaseTitle(phase) {
  return PHASE_TITLE_LABELS[phase.id || phase] || phase.title || '';
}

function tagLabel(tag) {
  return TAG_LABELS[tag] || tag;
}

function versionTitle(version) {
  return VERSION_TITLE_LABELS[version.id] || version.title;
}

function getVersionFolder(version) {
  const overrides = {
    V17: 'v17_state_estimation',
    V15: 'v15_1_sea_direct'
  };
  return overrides[version.id] || version.folder || '';
}

function mujocoPageUrl(id) {
  const url = new URL('mujoco.html', window.location.href);
  url.searchParams.set('id', id);
  url.searchParams.set('ui', 'launcher');
  return url.href;
}

function mujocoPageHref(id) {
  return `mujoco.html?id=${encodeURIComponent(id)}&ui=launcher`;
}

function openMujocoPage(id, event) {
  if (event) {
    event.preventDefault();
    event.stopPropagation();
  }
  window.location.assign(mujocoPageUrl(id));
}

window.openMujocoPage = openMujocoPage;

// ========== INIT ==========
document.addEventListener('DOMContentLoaded', () => {
  initViewSwitcher();
  initFilters();
  initSearch();
  updateStats();
  updatePhaseProgress();
  renderCurrentView();
});

// ========== SIDEBAR TOGGLE ==========
function toggleSidebar() {
  const sidebar = document.getElementById('sidebar');
  const toggle = document.getElementById('sidebar-toggle');
  sidebar.classList.toggle('collapsed');
  toggle.textContent = sidebar.classList.contains('collapsed') ? '▶' : '◀';
}

window.toggleSidebar = toggleSidebar;

// ========== VIEW SWITCHER ==========
function initViewSwitcher() {
  document.querySelectorAll('.view-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const view = btn.dataset.view;
      switchView(view);
    });
  });
}

function switchView(view) {
  currentView = view;

  // Update buttons
  document.querySelectorAll('.view-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.view === view);
  });

  // Toggle views
  document.getElementById('grid-view').classList.toggle('hidden', view !== 'grid');
  document.getElementById('timeline-view').classList.toggle('hidden', view !== 'timeline');
  document.getElementById('graph-view').classList.toggle('hidden', view !== 'graph');
  document.getElementById('compare-view').classList.toggle('hidden', view !== 'compare');
  document.getElementById('trends-view').classList.toggle('hidden', view !== 'trends');
  document.getElementById('heatmap-view').classList.toggle('hidden', view !== 'heatmap');

  renderCurrentView();
}

// ========== FILTERS ==========
function initFilters() {
  document.querySelectorAll('.filter-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      const filterType = chip.dataset.filter;
      const filterValue = chip.dataset.value;

      // Update active state
      document.querySelectorAll(`.filter-chip[data-filter="${filterType}"]`).forEach(c => {
        c.classList.remove('active');
      });
      chip.classList.add('active');

      // Update filter state
      filters[filterType] = filterValue;

      renderCurrentView();
    });
  });
}

function initSearch() {
  const searchInput = document.getElementById('search');
  searchInput.addEventListener('input', (e) => {
    filters.search = e.target.value.toLowerCase();
    renderCurrentView();
  });
}

function filterVersions(versions) {
  return versions.filter(v => {
    // Status filter
    if (filters.status !== 'all' && v.status !== filters.status) return false;

    // Phase filter
    if (filters.phase !== 'all' && v.phase !== parseInt(filters.phase)) return false;

    // Passive filter
    if (filters.passive !== 'all' && v.passive !== filters.passive) return false;

    // Search filter
    if (filters.search) {
      const searchStr = filters.search;
      const searchable = `${v.id} ${versionTitle(v)} ${v.title} ${v.desc} ${v.findings} ${v.tags.join(' ')}`.toLowerCase();
      if (!searchable.includes(searchStr)) return false;
    }

    return true;
  });
}

// ========== STATS ==========
function updateStats() {
  const done = VERSIONS.filter(v => v.status === 'done').length;
  const next = VERSIONS.filter(v => v.status === 'next').length;
  const planned = VERSIONS.filter(v => v.status === 'planned').length;
  const progress = Math.round((done / VERSIONS.length) * 100);

  document.getElementById('stat-done').textContent = done;
  document.getElementById('stat-next').textContent = next;
  document.getElementById('stat-planned').textContent = planned;
  document.getElementById('stat-progress').textContent = progress + '%';
}

function updatePhaseProgress() {
  const container = document.getElementById('phase-progress-container');
  container.innerHTML = '';

  PHASES.forEach(phase => {
    const phaseVersions = VERSIONS.filter(v => v.phase === phase.id);
    const done = phaseVersions.filter(v => v.status === 'done').length;
    const progress = Math.round((done / phaseVersions.length) * 100);

    const html = `
      <div class="phase-progress">
        <div class="phase-header">
          <div class="phase-name">
            <span class="phase-dot" style="background: ${phase.color}"></span>
            ${phaseLabel(phase)}
          </div>
          <div class="phase-count">${done}/${phaseVersions.length} · ${progress}%</div>
        </div>
        <div class="phase-bar">
          <div class="phase-bar-fill" style="width: ${progress}%; background: ${phase.color}"></div>
        </div>
      </div>
    `;

    container.innerHTML += html;
  });
}

// ========== RENDER ==========
function renderCurrentView() {
  const filtered = filterVersions(VERSIONS);

  switch(currentView) {
    case 'grid':
      renderGridView(filtered);
      break;
    case 'timeline':
      renderTimelineView(filtered);
      break;
    case 'graph':
      renderGraphView(filtered);
      break;
    case 'compare':
      renderCompareView();
      break;
    case 'trends':
      renderTrendsView();
      break;
    case 'heatmap':
      renderHeatmapView();
      break;
  }
}

// ========== GRID VIEW ==========
function renderGridView(versions) {
  const container = document.getElementById('grid-view');

  if (versions.length === 0) {
    container.innerHTML = '<div style="text-align:center;color:var(--text-muted);padding:40px">没有符合当前筛选条件的版本</div>';
    return;
  }

  container.innerHTML = versions.map(v => {
    const phaseColor = PHASE_COLORS[v.phase];
    const statusColor = STATUS_COLORS[v.status];
    const phase = PHASES.find(p => p.id === v.phase);

    // Extract key metrics from findings if available
    let keyMetric = '';
    if (v.findings.includes('CoT')) {
      const match = v.findings.match(/CoT[=:\s]+([\d.]+)/);
      if (match) keyMetric = `CoT: ${match[1]}`;
    } else if (v.findings.match(/(\d+)\/(\d+)/)) {
      const match = v.findings.match(/(\d+)\/(\d+)/);
      if (match) keyMetric = `成功率: ${match[1]}/${match[2]}`;
    }

    return `
      <div class="version-card" onclick="if (!event.target.closest('[data-no-detail]')) openDetail('${v.id}')" data-status="${v.status}" style="--phase1: ${phaseColor}">
        <div class="card-header">
          <div class="version-id" style="color: ${phaseColor}">${v.id}</div>
          <div class="version-title">${versionTitle(v)}</div>
          <div class="status-badge" style="background: ${statusColor}; color: ${v.status === 'planned' ? 'var(--text)' : '#000'}">${statusLabel(v.status)}</div>
        </div>

        <div class="card-desc">${v.desc}</div>

        <div class="card-meta">
          <div class="card-meta-item">
            <span>📅</span> ${v.date}
          </div>
          <div class="card-meta-item">
            <span>📍</span> ${phaseLabel(phase)}
          </div>
          ${v.passive !== 'tbd' ? `
            <div class="card-meta-item">
              <span>${v.passive === 'yes' ? '✅' : v.passive === 'no' ? '⚙️' : '⚡'}</span> ${passiveLabel(v.passive)}
            </div>
          ` : ''}
          ${keyMetric ? `
            <div class="card-meta-item" style="color: var(--accent); font-weight: 600;">
              ${keyMetric}
            </div>
          ` : ''}
        </div>

        <div class="card-tags">
          ${v.tags.slice(0, 4).map(tag => `<span class="tag">${tagLabel(tag)}</span>`).join('')}
          ${v.tags.length > 4 ? `<span class="tag">+${v.tags.length - 4}</span>` : ''}
        </div>

        <div class="card-actions">
          <a class="inline-action" href="${mujocoPageHref(v.id)}" data-mujoco-id="${v.id}" data-no-detail title="打开 ${v.id} 的 MuJoCo 仿真入口">MuJoCo 仿真</a>
        </div>

        ${v.status === 'done' && v.findings ? `
          <div class="key-finding">
            <strong style="color: var(--accent)">💡</strong> ${v.findings}
          </div>
        ` : ''}
      </div>
    `;
  }).join('');
}

// ========== TIMELINE VIEW ==========
function renderTimelineView(versions) {
  const container = document.getElementById('timeline-view');

  if (versions.length === 0) {
    container.innerHTML = '<div style="text-align:center;color:var(--text-muted);padding:40px">没有符合当前筛选条件的版本</div>';
    return;
  }

  // Group by phase
  const byPhase = {};
  PHASES.forEach(p => byPhase[p.id] = []);
  versions.forEach(v => byPhase[v.phase].push(v));

  container.innerHTML = PHASES.map(phase => {
    const phaseVersions = byPhase[phase.id];
    if (phaseVersions.length === 0) return '';

    return `
      <div class="timeline-phase">
        <div class="timeline-phase-header">
          <div class="timeline-phase-badge" style="background: ${phase.color}">${phaseLabel(phase)}</div>
          <div class="timeline-phase-title">${phaseTitle(phase)}</div>
          <div style="color: var(--text-muted); font-size: 0.8rem; margin-left: auto;">${phase.desc}</div>
        </div>

        <div class="timeline-items">
          ${phaseVersions.map(v => {
            const statusColor = STATUS_COLORS[v.status];
            return `
              <div class="timeline-item" style="--dot-color: ${statusColor}" onclick="if (!event.target.closest('[data-no-detail]')) openDetail('${v.id}')">
                <style>.timeline-item[onclick*="${v.id}"]::before { background: ${statusColor} !important; }</style>
                <div class="timeline-card" style="cursor: pointer; border-left: 3px solid ${phase.color}">
                  <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
                    <div class="version-id" style="color: ${phase.color}">${v.id}</div>
                    <div class="version-title" style="flex: 1">${versionTitle(v)}</div>
                    <div style="font-size: 0.7rem; color: var(--text-dim)">${v.date}</div>
                    <a class="inline-action compact" href="${mujocoPageHref(v.id)}" data-mujoco-id="${v.id}" data-no-detail title="打开 ${v.id} 的 MuJoCo 仿真入口">MuJoCo</a>
                  </div>
                  <div style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 8px;">${v.desc}</div>
                  ${v.status === 'done' ? `
                    <div style="font-size: 0.7rem; color: var(--text-muted); padding: 8px; background: var(--surface2); border-radius: 4px;">
                      <strong style="color: var(--accent)">关键发现：</strong> ${v.findings}
                    </div>
                  ` : ''}
                  <div style="display: flex; gap: 4px; margin-top: 8px; flex-wrap: wrap;">
                    ${v.tags.map(tag => `<span class="tag">${tagLabel(tag)}</span>`).join('')}
                  </div>
                </div>
              </div>
            `;
          }).join('')}
        </div>
      </div>
    `;
  }).join('');
}

// ========== GRAPH VIEW (Progress Roadmap Version) ==========
const NW = 100, NH = 38, GX = 132, PHASE_GAP = 118, OFFX = 120, OFFY = 86;
const GRAPH_STORAGE_KEY = 'limit-cycle-dashboard.graph-state.v2';

let graphState = {
  vpX: 0,
  vpY: 0,
  scale: 1,
  positions: {},
  savedPositions: {},
  nodeGroups: {},
  collapsedPhases: new Set(),
  phaseSummaryByVersion: {},
  legendCollapsed: false,
  controlsCollapsed: false,
  hasSavedViewport: false,
  draggingId: null,
  dragOffX: 0,
  dragOffY: 0,
  dragMoved: false,
  activePointerId: null,
  panning: false,
  panX: 0,
  panY: 0,
  panVpX: 0,
  panVpY: 0
};

function validGraphPoint(point) {
  return point &&
    Number.isFinite(point.x) &&
    Number.isFinite(point.y) &&
    Math.abs(point.x) < 100000 &&
    Math.abs(point.y) < 100000;
}

function roundGraphPoint(point) {
  return {
    x: Math.round(point.x * 10) / 10,
    y: Math.round(point.y * 10) / 10
  };
}

function defaultGraphPosition(node) {
  return {
    x: OFFX + node.col * GX,
    y: OFFY + node.row * PHASE_GAP
  };
}

function summaryIdForPhase(phaseId) {
  return `phase-${phaseId}`;
}

function isSummaryNodeId(id) {
  return typeof id === 'string' && id.startsWith('phase-');
}

function isPhaseCollapsed(phaseId) {
  return graphState.collapsedPhases.has(String(phaseId));
}

function resolveGraphNodeId(versionId) {
  return graphState.phaseSummaryByVersion[versionId] || versionId;
}

function loadGraphState() {
  try {
    const raw = localStorage.getItem(GRAPH_STORAGE_KEY);
    if (!raw) return;

    const saved = JSON.parse(raw);
    if (saved && typeof saved === 'object') {
      graphState.savedPositions = Object.fromEntries(
        Object.entries(saved.positions || {}).filter(([, point]) => validGraphPoint(point))
      );

      graphState.collapsedPhases = new Set(
        (saved.collapsedPhases || [])
          .map(id => String(id))
          .filter(id => PHASES.some(phase => String(phase.id) === id))
      );
      graphState.legendCollapsed = Boolean(saved.legendCollapsed);
      graphState.controlsCollapsed = Boolean(saved.controlsCollapsed);

      if (saved.viewport &&
          Number.isFinite(saved.viewport.vpX) &&
          Number.isFinite(saved.viewport.vpY) &&
          Number.isFinite(saved.viewport.scale)) {
        graphState.vpX = saved.viewport.vpX;
        graphState.vpY = saved.viewport.vpY;
        graphState.scale = Math.max(0.3, Math.min(3, saved.viewport.scale));
        graphState.hasSavedViewport = true;
      }
    }
  } catch (err) {
    graphState.savedPositions = {};
    graphState.collapsedPhases = new Set();
    graphState.legendCollapsed = false;
    graphState.controlsCollapsed = false;
    graphState.hasSavedViewport = false;
  }
}

function saveGraphState() {
  try {
    const positions = { ...graphState.savedPositions };
    Object.entries(graphState.positions).forEach(([id, point]) => {
      if (validGraphPoint(point)) {
        positions[id] = roundGraphPoint(point);
      }
    });

    graphState.savedPositions = positions;
    graphState.hasSavedViewport = true;

    localStorage.setItem(GRAPH_STORAGE_KEY, JSON.stringify({
      positions,
      collapsedPhases: Array.from(graphState.collapsedPhases),
      legendCollapsed: graphState.legendCollapsed,
      controlsCollapsed: graphState.controlsCollapsed,
      viewport: {
        vpX: Math.round(graphState.vpX * 10) / 10,
        vpY: Math.round(graphState.vpY * 10) / 10,
        scale: Math.round(graphState.scale * 1000) / 1000
      },
      updatedAt: new Date().toISOString()
    }));
  } catch (err) {
    // localStorage 不可用时只保持当前会话状态。
  }
}

function updateGraphLegend() {
  const legend = document.getElementById('graph-legend');
  const toggle = document.getElementById('graph-legend-toggle');
  if (!legend || !toggle) return;

  legend.classList.toggle('collapsed', graphState.legendCollapsed);
  toggle.textContent = graphState.legendCollapsed ? '▸' : '▾';
  toggle.title = graphState.legendCollapsed ? '展开图例' : '收起图例';
  toggle.setAttribute('aria-expanded', String(!graphState.legendCollapsed));
}

function toggleGraphLegend(event) {
  if (event) {
    event.preventDefault();
    event.stopPropagation();
  }

  graphState.legendCollapsed = !graphState.legendCollapsed;
  updateGraphLegend();
  saveGraphState();
}

function updateGraphToolbar() {
  const toolbar = document.getElementById('graph-toolbar');
  const toggle = document.getElementById('graph-toolbar-toggle');
  if (!toolbar || !toggle) return;

  toolbar.classList.toggle('collapsed', graphState.controlsCollapsed);
  toggle.textContent = graphState.controlsCollapsed ? '⋯' : '⌄';
  toggle.title = graphState.controlsCollapsed ? '展开路径图工具' : '收起路径图工具';
  toggle.setAttribute('aria-expanded', String(!graphState.controlsCollapsed));
}

function toggleGraphToolbar(event) {
  if (event) {
    event.preventDefault();
    event.stopPropagation();
  }

  graphState.controlsCollapsed = !graphState.controlsCollapsed;
  updateGraphToolbar();
  saveGraphState();
}

function toggleGraphPhase(phaseId, event) {
  if (event) {
    event.preventDefault();
    event.stopPropagation();
  }

  const key = String(phaseId);
  if (graphState.collapsedPhases.has(key)) {
    graphState.collapsedPhases.delete(key);
  } else {
    graphState.collapsedPhases.add(key);
  }

  saveGraphState();
  renderCurrentView();
}

loadGraphState();

// Build layout from the current research progress in data.js.
// X follows version order inside each phase; Y follows phase lanes.
function buildProgressLayout(versions) {
  const nodes = [];
  graphState.phaseSummaryByVersion = {};

  PHASES.forEach(phase => {
    const phaseVersions = versions
      .filter(v => v.phase === phase.id)
      .sort((a, b) => VERSIONS.findIndex(v => v.id === a.id) - VERSIONS.findIndex(v => v.id === b.id));

    if (phaseVersions.length === 0) return;

    if (isPhaseCollapsed(phase.id)) {
      const summaryId = summaryIdForPhase(phase.id);
      phaseVersions.forEach(v => {
        graphState.phaseSummaryByVersion[v.id] = summaryId;
      });
      nodes.push({
        id: summaryId,
        summary: true,
        phase,
        versions: phaseVersions,
        counts: {
          done: phaseVersions.filter(v => v.status === 'done').length,
          next: phaseVersions.filter(v => v.status === 'next').length,
          planned: phaseVersions.filter(v => v.status === 'planned').length
        },
        col: 0,
        row: phase.id - 1
      });
      return;
    }

    phaseVersions.forEach((v, idx) => nodes.push({
        id: v.id,
        version: v,
        col: idx,
        row: phase.id - 1
      }));
  });
  return nodes;
}

function graphBounds(positions) {
  const values = Object.values(positions);
  if (values.length === 0) return null;

  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  values.forEach(p => {
    minX = Math.min(minX, p.x);
    minY = Math.min(minY, p.y);
    maxX = Math.max(maxX, p.x + NW);
    maxY = Math.max(maxY, p.y + NH);
  });

  return { minX, minY, maxX, maxY, width: maxX - minX, height: maxY - minY };
}

function fitGraphToContainer(container) {
  const bounds = graphBounds(graphState.positions);
  if (!bounds) return;

  const padding = 72;
  const scaleX = (container.clientWidth - padding * 2) / bounds.width;
  const scaleY = (container.clientHeight - padding * 2) / bounds.height;
  graphState.scale = Math.max(0.35, Math.min(scaleX, scaleY, 1.1));
  graphState.vpX = (container.clientWidth - bounds.width * graphState.scale) / 2 - bounds.minX * graphState.scale;
  graphState.vpY = (container.clientHeight - bounds.height * graphState.scale) / 2 - bounds.minY * graphState.scale;
}

function updateGraphPhaseControls(versions = VERSIONS) {
  const container = document.getElementById('graph-phase-controls');
  if (!container) return;

  container.innerHTML = '';
  PHASES.forEach(phase => {
    const phaseVersions = versions.filter(v => v.phase === phase.id);
    const collapsed = isPhaseCollapsed(phase.id);
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = `graph-phase-btn${collapsed ? ' collapsed' : ''}`;
    btn.disabled = phaseVersions.length === 0;
    btn.textContent = collapsed ? '▸' : '▾';
    btn.title = `${collapsed ? '展开' : '收起'}${phaseLabel(phase)}`;
    btn.setAttribute('aria-label', `${collapsed ? '展开' : '收起'}${phaseLabel(phase)}`);
    btn.style.setProperty('--phase-color', phase.color);
    btn.addEventListener('click', e => toggleGraphPhase(phase.id, e));
    container.appendChild(btn);
  });
}

function renderGraphView(versions) {
  let svg = document.getElementById('graph-svg');
  const container = document.getElementById('graph-view');
  const width = container.clientWidth;
  const height = container.clientHeight;

  const freshSvg = svg.cloneNode(false);
  svg.replaceWith(freshSvg);
  svg = freshSvg;
  svg.setAttribute('width', width);
  svg.setAttribute('height', height);

  const graphVersions = versions;
  updateGraphPhaseControls(graphVersions);
  updateGraphLegend();
  updateGraphToolbar();

  if (graphVersions.length === 0) {
    svg.innerHTML = '<text x="50%" y="50%" text-anchor="middle" fill="var(--text-muted)">没有符合当前筛选条件的版本</text>';
    return;
  }

  const layout = buildProgressLayout(graphVersions);

  graphState.positions = {};
  layout.forEach(node => {
    const saved = graphState.savedPositions[node.id];
    graphState.positions[node.id] = validGraphPoint(saved) ? { ...saved } : defaultGraphPosition(node);
  });

  if (!graphState.hasSavedViewport) {
    fitGraphToContainer(container);
  }

  // Clear and setup
  svg.innerHTML = '';
  const NS = 'http://www.w3.org/2000/svg';

  // Create defs with simplified styling
  const defs = document.createElementNS(NS, 'defs');

  // Simple arrow markers without glow
  Object.entries(PHASE_COLORS).forEach(([phase, color]) => {
    const marker = document.createElementNS(NS, 'marker');
    marker.setAttribute('id', `arr${phase}`);
    marker.setAttribute('markerWidth', '6');
    marker.setAttribute('markerHeight', '6');
    marker.setAttribute('refX', '5');
    marker.setAttribute('refY', '3');
    marker.setAttribute('orient', 'auto');
    const path = document.createElementNS(NS, 'path');
    path.setAttribute('d', 'M0,0 L6,3 L0,6 Z');
    path.setAttribute('fill', color);
    path.setAttribute('opacity', '0.7');
    marker.appendChild(path);
    defs.appendChild(marker);
  });

  const markerP = document.createElementNS(NS, 'marker');
  markerP.setAttribute('id', 'arrP');
  markerP.setAttribute('markerWidth', '6');
  markerP.setAttribute('markerHeight', '6');
  markerP.setAttribute('refX', '5');
  markerP.setAttribute('refY', '3');
  markerP.setAttribute('orient', 'auto');
  const pathP = document.createElementNS(NS, 'path');
  pathP.setAttribute('d', 'M0,0 L6,3 L0,6 Z');
  pathP.setAttribute('fill', '#4a5568');
  pathP.setAttribute('opacity', '0.5');
  markerP.appendChild(pathP);
  defs.appendChild(markerP);

  svg.appendChild(defs);

  // Main group
  const rootG = document.createElementNS(NS, 'g');
  const bandLayer = document.createElementNS(NS, 'g');
  const edgeLayer = document.createElementNS(NS, 'g');
  const gateLayer = document.createElementNS(NS, 'g');
  const nodeLayer = document.createElementNS(NS, 'g');

  rootG.appendChild(bandLayer);
  rootG.appendChild(edgeLayer);
  rootG.appendChild(gateLayer);
  rootG.appendChild(nodeLayer);
  svg.appendChild(rootG);

  function applyVP() {
    rootG.setAttribute('transform', `translate(${graphState.vpX},${graphState.vpY}) scale(${graphState.scale})`);
  }

  function svgPt(e) {
    const rect = svg.getBoundingClientRect();
    return {
      x: (e.clientX - rect.left - graphState.vpX) / graphState.scale,
      y: (e.clientY - rect.top - graphState.vpY) / graphState.scale
    };
  }

  function drawPhaseBands() {
    bandLayer.innerHTML = '';
    const bounds = graphBounds(graphState.positions);
    if (!bounds) return;

    PHASES.forEach(phase => {
      const phaseVersions = graphVersions.filter(v => v.phase === phase.id);
      if (phaseVersions.length === 0) return;

      const laneY = OFFY + (phase.id - 1) * PHASE_GAP - 24;
      const laneX = bounds.minX - 52;
      const laneWidth = bounds.width + 104;

      const rect = document.createElementNS(NS, 'rect');
      rect.setAttribute('x', laneX);
      rect.setAttribute('y', laneY);
      rect.setAttribute('width', laneWidth);
      rect.setAttribute('height', 86);
      rect.setAttribute('rx', '8');
      rect.setAttribute('fill', phase.color);
      rect.setAttribute('opacity', '0.045');
      bandLayer.appendChild(rect);
    });
  }

  // Draw edges based on actual deps
  function drawEdges() {
    edgeLayer.innerHTML = '';
    const drawnEdges = new Set();

    graphVersions.forEach(v => {
      const targetId = resolveGraphNodeId(v.id);
      const tp = graphState.positions[targetId];
      if (!tp) return;

      v.deps.forEach(depId => {
        const sourceId = resolveGraphNodeId(depId);
        if (sourceId === targetId || !graphState.positions[sourceId]) return;

        const edgeKey = `${sourceId}->${targetId}`;
        if (drawnEdges.has(edgeKey)) return;
        drawnEdges.add(edgeKey);

        const sp = graphState.positions[sourceId];
        const sx = sp.x + NW;
        const sy = sp.y + NH / 2;
        const tx = tp.x;
        const ty = tp.y + NH / 2;

        const color = v.status === 'planned' ? '#4a5568' : PHASE_COLORS[v.phase];
        const opacity = v.status === 'planned' ? 0.3 : (v.status === 'next' ? 0.85 : 0.58);
        const arrowId = v.status === 'planned' ? 'arrP' : `arr${v.phase}`;

        const dx = tx - sx;
        const dy = ty - sy;
        const cx1 = sx + Math.max(48, Math.abs(dx) * 0.45);
        const cx2 = tx - Math.max(48, Math.abs(dx) * 0.45);
        const d = `M${sx},${sy} C${cx1},${sy} ${cx2},${ty} ${tx},${ty}`;

        const path = document.createElementNS(NS, 'path');
        path.setAttribute('d', d);
        path.setAttribute('fill', 'none');
        path.setAttribute('stroke', color);
        path.setAttribute('stroke-width', v.status === 'next' ? '3' : '2');
        path.setAttribute('opacity', opacity);
        path.setAttribute('marker-end', `url(#${arrowId})`);
        if (v.status === 'planned') {
          path.setAttribute('stroke-dasharray', '4,4');
        }
        edgeLayer.appendChild(path);
      });
    });
  }

  // Draw gates (decision points) - simplified
  function drawGates() {
    gateLayer.innerHTML = '';
    const drawnGates = new Set();

    GATES.forEach(g => {
      const nodeId = resolveGraphNodeId(g.after);
      if (!graphState.positions[nodeId]) return;

      const gateKey = `${nodeId}-${g.after}`;
      if (drawnGates.has(gateKey)) return;
      drawnGates.add(gateKey);

      const p = graphState.positions[nodeId];
      const gx = p.x + NW + 18;
      const gy = p.y + NH / 2;
      const s = 7;
      const col = g.status === 'passed' ? '#34d399' : '#f59e0b';

      const grp = document.createElementNS(NS, 'g');
      grp.style.cursor = 'help';

      const poly = document.createElementNS(NS, 'polygon');
      poly.setAttribute('points', `${gx},${gy - s} ${gx + s},${gy} ${gx},${gy + s} ${gx - s},${gy}`);
      poly.setAttribute('fill', col);
      poly.setAttribute('opacity', '0.8');
      grp.appendChild(poly);

      const lt = document.createElementNS(NS, 'text');
      lt.textContent = g.status === 'passed' ? '✓' : '?';
      lt.setAttribute('x', gx);
      lt.setAttribute('y', gy + 3);
      lt.setAttribute('text-anchor', 'middle');
      lt.setAttribute('font-size', '8');
      lt.setAttribute('fill', '#0a0e14');
      lt.setAttribute('font-weight', '700');
      lt.setAttribute('pointer-events', 'none');
      grp.appendChild(lt);

      const title = document.createElementNS(NS, 'title');
      title.textContent = g.text;
      grp.appendChild(title);

      gateLayer.appendChild(grp);
    });
  }

  function updateNodePos(id) {
    const p = graphState.positions[id];
    const grp = graphState.nodeGroups[id];
    if (!p || !grp) return;

    const nodeBody = grp.querySelector('.node-body');
    const nodeStripe = grp.querySelector('.node-stripe');
    const idLabel = grp.querySelector('.node-id-label');
    const titleLabel = grp.querySelector('.node-title-label');
    const statusLabelEl = grp.querySelector('.node-status-label');
    const simBg = grp.querySelector('.node-sim-bg');
    const simLabel = grp.querySelector('.node-sim-label');

    if (nodeBody) {
      nodeBody.setAttribute('x', p.x);
      nodeBody.setAttribute('y', p.y);
    }
    if (nodeStripe) {
      nodeStripe.setAttribute('x', p.x);
      nodeStripe.setAttribute('y', p.y + 2);
    }
    if (idLabel) {
      idLabel.setAttribute('x', p.x + 8);
      idLabel.setAttribute('y', p.y + 14);
    }
    if (titleLabel) {
      titleLabel.setAttribute('x', p.x + 8);
      titleLabel.setAttribute('y', p.y + 28);
    }
    if (statusLabelEl) {
      statusLabelEl.setAttribute('x', p.x + NW - 8);
      statusLabelEl.setAttribute('y', p.y + 30);
    }
    if (simBg) {
      simBg.setAttribute('x', p.x + NW - 30);
      simBg.setAttribute('y', p.y + 4);
    }
    if (simLabel) {
      simLabel.setAttribute('x', p.x + NW - 17);
      simLabel.setAttribute('y', p.y + 13);
    }
  }

  function makeDraggable(grp, id) {
    const startDrag = e => {
      if (e.button !== 0 || e.target.closest('.node-sim-button')) return;
      if (graphState.draggingId) return;
      e.preventDefault();
      e.stopPropagation();

      const pt = svgPt(e);
      graphState.draggingId = id;
      graphState.dragMoved = false;
      graphState.activePointerId = e.pointerId ?? null;
      graphState.dragOffX = pt.x - graphState.positions[id].x;
      graphState.dragOffY = pt.y - graphState.positions[id].y;
      if (typeof grp.setPointerCapture === 'function' && e.pointerId !== undefined) {
        grp.setPointerCapture(e.pointerId);
      }
      grp.style.cursor = 'grabbing';
      svg.style.cursor = 'grabbing';
    };

    grp.addEventListener('pointerdown', startDrag);
    grp.addEventListener('mousedown', startDrag);
  }

  // Draw nodes
  graphState.nodeGroups = {};

  function drawSummaryNode(node) {
    const p = graphState.positions[node.id];
    const phase = node.phase;

    const grp = document.createElementNS(NS, 'g');
    grp.classList.add('node-g', 'summary-node');
    grp.style.cursor = 'grab';
    graphState.nodeGroups[node.id] = grp;

    const rect = document.createElementNS(NS, 'rect');
    rect.setAttribute('x', p.x);
    rect.setAttribute('y', p.y);
    rect.setAttribute('width', NW);
    rect.setAttribute('height', NH);
    rect.setAttribute('rx', '6');
    rect.setAttribute('fill', 'rgba(18, 22, 31, 0.96)');
    rect.setAttribute('stroke', phase.color);
    rect.setAttribute('stroke-width', '2');
    rect.setAttribute('stroke-dasharray', '5,3');
    rect.classList.add('node-body');
    grp.appendChild(rect);

    const stripe = document.createElementNS(NS, 'rect');
    stripe.setAttribute('x', p.x);
    stripe.setAttribute('y', p.y + 2);
    stripe.setAttribute('width', 3);
    stripe.setAttribute('height', NH - 4);
    stripe.setAttribute('rx', '1.5');
    stripe.setAttribute('fill', phase.color);
    stripe.setAttribute('opacity', '0.95');
    stripe.setAttribute('pointer-events', 'none');
    stripe.classList.add('node-stripe');
    grp.appendChild(stripe);

    const tid = document.createElementNS(NS, 'text');
    tid.textContent = phaseLabel(phase);
    tid.setAttribute('x', p.x + 8);
    tid.setAttribute('y', p.y + 14);
    tid.setAttribute('font-size', '9');
    tid.setAttribute('font-weight', '700');
    tid.setAttribute('fill', phase.color);
    tid.setAttribute('pointer-events', 'none');
    tid.classList.add('node-id-label');
    grp.appendChild(tid);

    const ttl = document.createElementNS(NS, 'text');
    ttl.textContent = `${node.versions.length} 个版本`;
    ttl.setAttribute('x', p.x + 8);
    ttl.setAttribute('y', p.y + 28);
    ttl.setAttribute('font-size', '7.5');
    ttl.setAttribute('fill', '#8892a4');
    ttl.setAttribute('pointer-events', 'none');
    ttl.classList.add('node-title-label');
    grp.appendChild(ttl);

    const st = document.createElementNS(NS, 'text');
    st.textContent = '展开';
    st.setAttribute('x', p.x + NW - 8);
    st.setAttribute('y', p.y + 30);
    st.setAttribute('text-anchor', 'end');
    st.setAttribute('font-size', '7');
    st.setAttribute('font-weight', '700');
    st.setAttribute('fill', '#60a5fa');
    st.setAttribute('pointer-events', 'none');
    st.classList.add('node-status-label');
    grp.appendChild(st);

    const nodeTitle = document.createElementNS(NS, 'title');
    nodeTitle.textContent = `${phaseLabel(phase)}已收起，包含 ${node.versions.length} 个版本。点击展开。`;
    grp.appendChild(nodeTitle);

    grp.addEventListener('click', e => {
      e.stopPropagation();
      if (graphState.dragMoved) {
        graphState.dragMoved = false;
        return;
      }
      toggleGraphPhase(phase.id, e);
    });

    makeDraggable(grp, node.id);
    nodeLayer.appendChild(grp);
  }

  function drawVersionNode(node) {
    const v = node.version;
    const p = graphState.positions[node.id];
    const pc = PHASE_COLORS[v.phase];
    const isPlanned = v.status === 'planned';
    const isNext = v.status === 'next';

    const grp = document.createElementNS(NS, 'g');
    grp.classList.add('node-g');
    grp.style.cursor = 'grab';
    graphState.nodeGroups[node.id] = grp;

    const rect = document.createElementNS(NS, 'rect');
    rect.setAttribute('x', p.x);
    rect.setAttribute('y', p.y);
    rect.setAttribute('width', NW);
    rect.setAttribute('height', NH);
    rect.setAttribute('rx', '6');
    rect.setAttribute('fill', isPlanned ? '#161b27' : (isNext ? '#26220f' : '#1e2433'));
    rect.setAttribute('stroke', isNext ? '#fbbf24' : isPlanned ? '#3d4460' : pc);
    rect.setAttribute('stroke-width', isNext ? '2.6' : '1.5');
    if (isPlanned) rect.setAttribute('stroke-dasharray', '4,3');
    rect.classList.add('node-body');
    grp.appendChild(rect);

    const stripe = document.createElementNS(NS, 'rect');
    stripe.setAttribute('x', p.x);
    stripe.setAttribute('y', p.y + 2);
    stripe.setAttribute('width', 3);
    stripe.setAttribute('height', NH - 4);
    stripe.setAttribute('rx', '1.5');
    stripe.setAttribute('fill', STATUS_COLORS[v.status] || '#3d4460');
    stripe.setAttribute('opacity', '0.9');
    stripe.setAttribute('pointer-events', 'none');
    stripe.classList.add('node-stripe');
    grp.appendChild(stripe);

    const tid = document.createElementNS(NS, 'text');
    tid.textContent = v.id;
    tid.setAttribute('x', p.x + 8);
    tid.setAttribute('y', p.y + 14);
    tid.setAttribute('font-size', '9');
    tid.setAttribute('font-weight', '700');
    tid.setAttribute('font-family', 'monospace');
    tid.setAttribute('fill', isNext ? '#fbbf24' : pc);
    tid.setAttribute('pointer-events', 'none');
    tid.classList.add('node-id-label');
    grp.appendChild(tid);

    const title = versionTitle(v);
    const short = title.length > 14 ? title.slice(0, 12) + '…' : title;
    const ttl = document.createElementNS(NS, 'text');
    ttl.textContent = short;
    ttl.setAttribute('x', p.x + 8);
    ttl.setAttribute('y', p.y + 28);
    ttl.setAttribute('font-size', '7.5');
    ttl.setAttribute('fill', '#8892a4');
    ttl.setAttribute('pointer-events', 'none');
    ttl.classList.add('node-title-label');
    grp.appendChild(ttl);

    if (v.status !== 'done') {
      const st = document.createElementNS(NS, 'text');
      st.textContent = v.status === 'next' ? '进行中' : '计划';
      st.setAttribute('x', p.x + NW - 8);
      st.setAttribute('y', p.y + 30);
      st.setAttribute('text-anchor', 'end');
      st.setAttribute('font-size', '7');
      st.setAttribute('font-weight', '700');
      st.setAttribute('fill', STATUS_COLORS[v.status] || '#8892a4');
      st.setAttribute('pointer-events', 'none');
      st.classList.add('node-status-label');
      grp.appendChild(st);
    }

    const simBtn = document.createElementNS(NS, 'g');
    simBtn.classList.add('node-sim-button');
    simBtn.style.cursor = 'pointer';

    const simRect = document.createElementNS(NS, 'rect');
    simRect.setAttribute('x', p.x + NW - 30);
    simRect.setAttribute('y', p.y + 4);
    simRect.setAttribute('width', 26);
    simRect.setAttribute('height', 13);
    simRect.setAttribute('rx', '3');
    simRect.setAttribute('fill', 'rgba(96, 165, 250, 0.15)');
    simRect.setAttribute('stroke', 'rgba(96, 165, 250, 0.4)');
    simRect.setAttribute('stroke-width', '1');
    simRect.classList.add('node-sim-bg');
    simBtn.appendChild(simRect);

    const simText = document.createElementNS(NS, 'text');
    simText.textContent = '仿真';
    simText.setAttribute('x', p.x + NW - 17);
    simText.setAttribute('y', p.y + 13);
    simText.setAttribute('text-anchor', 'middle');
    simText.setAttribute('font-size', '7');
    simText.setAttribute('font-weight', '600');
    simText.setAttribute('fill', '#60a5fa');
    simText.setAttribute('pointer-events', 'none');
    simText.classList.add('node-sim-label');
    simBtn.appendChild(simText);

    simBtn.addEventListener('pointerdown', e => e.stopPropagation());
    simBtn.addEventListener('mousedown', e => e.stopPropagation());
    simBtn.addEventListener('click', e => openMujocoPage(v.id, e));
    grp.appendChild(simBtn);

    const nodeTitle = document.createElementNS(NS, 'title');
    nodeTitle.textContent = `${v.id} · ${statusLabel(v.status)} · ${versionTitle(v)}`;
    grp.appendChild(nodeTitle);

    grp.addEventListener('click', (e) => {
      e.stopPropagation();
      if (graphState.dragMoved) {
        graphState.dragMoved = false;
        return;
      }
      openDetail(v.id);
    });

    makeDraggable(grp, node.id);
    nodeLayer.appendChild(grp);
  }

  layout.forEach(node => {
    if (!graphState.positions[node.id]) return;
    if (node.summary) {
      drawSummaryNode(node);
    } else {
      drawVersionNode(node);
    }
  });

  // Pan and zoom
  const startPan = e => {
    if (e.button !== 0 || e.target.closest('.node-g')) return;
    if (graphState.panning) return;
    e.preventDefault();
    graphState.panning = true;
    graphState.activePointerId = e.pointerId ?? null;
    graphState.panX = e.clientX;
    graphState.panY = e.clientY;
    graphState.panVpX = graphState.vpX;
    graphState.panVpY = graphState.vpY;
    if (typeof svg.setPointerCapture === 'function' && e.pointerId !== undefined) {
      svg.setPointerCapture(e.pointerId);
    }
    svg.style.cursor = 'grabbing';
  };

  const moveGraph = e => {
    if (graphState.draggingId) {
      e.preventDefault();
      const pt = svgPt(e);
      graphState.positions[graphState.draggingId].x = pt.x - graphState.dragOffX;
      graphState.positions[graphState.draggingId].y = pt.y - graphState.dragOffY;
      graphState.dragMoved = true;
      updateNodePos(graphState.draggingId);
      drawEdges();
      drawGates();
      return;
    }

    if (graphState.panning) {
      e.preventDefault();
      graphState.vpX = graphState.panVpX + (e.clientX - graphState.panX);
      graphState.vpY = graphState.panVpY + (e.clientY - graphState.panY);
      applyVP();
    }
  };

  const endGraphGesture = () => {
    const shouldSave = graphState.draggingId || graphState.panning;

    if (graphState.draggingId && graphState.nodeGroups[graphState.draggingId]) {
      graphState.nodeGroups[graphState.draggingId].style.cursor = 'grab';
    }
    graphState.draggingId = null;
    graphState.activePointerId = null;
    graphState.panning = false;
    svg.style.cursor = 'default';

    if (shouldSave) {
      saveGraphState();
    }
  };

  svg.addEventListener('pointerdown', startPan);
  svg.addEventListener('mousedown', startPan);
  svg.addEventListener('pointermove', moveGraph);
  svg.addEventListener('mousemove', moveGraph);
  svg.addEventListener('pointerup', endGraphGesture);
  svg.addEventListener('mouseup', endGraphGesture);
  svg.addEventListener('pointercancel', endGraphGesture);
  svg.addEventListener('mouseleave', endGraphGesture);

  // Zoom with mouse wheel
  svg.addEventListener('wheel', e => {
    e.preventDefault();
    const rect = svg.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    const newScale = Math.max(0.3, Math.min(3, graphState.scale * delta));

    // Zoom towards mouse position
    const worldX = (mouseX - graphState.vpX) / graphState.scale;
    const worldY = (mouseY - graphState.vpY) / graphState.scale;

    graphState.scale = newScale;
    graphState.vpX = mouseX - worldX * graphState.scale;
    graphState.vpY = mouseY - worldY * graphState.scale;

    applyVP();
    saveGraphState();
  });

  drawPhaseBands();
  drawEdges();
  drawGates();
  applyVP();

  // Subtle hover effect
  Object.values(graphState.nodeGroups).forEach(nodeGrp => {
    nodeGrp.addEventListener('mouseenter', function() {
      this.style.opacity = '0.85';
    });
    nodeGrp.addEventListener('mouseleave', function() {
      this.style.opacity = '1';
    });
  });
}

// Graph control functions
function resetGraphView() {
  graphState.vpX = 0;
  graphState.vpY = 0;
  graphState.scale = 1;
  graphState.hasSavedViewport = true;
  saveGraphState();
  renderCurrentView();
}

function fitGraphView() {
  const positions = Object.values(graphState.positions);
  if (positions.length === 0) return;

  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  positions.forEach(p => {
    minX = Math.min(minX, p.x);
    minY = Math.min(minY, p.y);
    maxX = Math.max(maxX, p.x + NW);
    maxY = Math.max(maxY, p.y + NH);
  });

  const container = document.getElementById('graph-view');
  const padding = 80;
  const contentWidth = maxX - minX;
  const contentHeight = maxY - minY;
  const scaleX = (container.clientWidth - padding * 2) / contentWidth;
  const scaleY = (container.clientHeight - padding * 2) / contentHeight;

  graphState.scale = Math.min(scaleX, scaleY, 1.2);
  graphState.vpX = (container.clientWidth - contentWidth * graphState.scale) / 2 - minX * graphState.scale;
  graphState.vpY = (container.clientHeight - contentHeight * graphState.scale) / 2 - minY * graphState.scale;
  graphState.hasSavedViewport = true;
  saveGraphState();

  renderCurrentView();
}

// ========== DETAIL PANEL ==========
function openDetail(id) {
  const v = VERSIONS.find(ver => ver.id === id);
  if (!v) return;

  const phase = PHASES.find(p => p.id === v.phase);
  const phaseColor = PHASE_COLORS[v.phase];
  const statusColor = STATUS_COLORS[v.status];

  document.getElementById('detail-id').textContent = v.id;
  document.getElementById('detail-id').style.background = phaseColor;
  document.getElementById('detail-id').style.color = '#000';

  document.getElementById('detail-title').textContent = versionTitle(v);

  const body = document.getElementById('detail-body');
  body.innerHTML = `
    <div class="detail-section">
      <div style="display: inline-block; padding: 4px 10px; background: ${statusColor}; color: ${v.status === 'planned' ? 'var(--text)' : '#000'}; border-radius: 4px; font-size: 0.75rem; font-weight: 700; margin-bottom: 12px;">
        ${statusLabel(v.status)}
      </div>
      <a class="inline-action" style="margin-left: 8px;" href="${mujocoPageHref(v.id)}" data-mujoco-id="${v.id}" data-no-detail>打开 MuJoCo 仿真</a>
    </div>

    <div class="detail-section">
      <h4>版本描述</h4>
      <p>${v.desc}</p>
    </div>

    ${v.findings ? `
      <div class="detail-section">
        <h4>关键发现</h4>
        <p style="background: var(--surface2); padding: 12px; border-left: 3px solid var(--accent); border-radius: 4px;">${v.findings}</p>
      </div>
    ` : ''}

    <div class="detail-section">
      <h4>元数据</h4>
      <table class="detail-table">
        <tr>
          <td>阶段</td>
          <td><span style="color: ${phaseColor}; font-weight: 600">${phaseLabel(phase)}</span> — ${phaseTitle(phase)}</td>
        </tr>
        <tr>
          <td>被动性</td>
          <td>${passiveLabel(v.passive)}</td>
        </tr>
        <tr>
          <td>日期</td>
          <td>${v.date}</td>
        </tr>
        <tr>
          <td>目录</td>
          <td><code style="font-size: 0.75rem">${getVersionFolder(v) || '—'}</code></td>
        </tr>
        <tr>
          <td>依赖</td>
          <td>${v.deps.length ? v.deps.map(d => `<span style="color: var(--accent); cursor: pointer;" onclick="openDetail('${d}')">${d}</span>`).join(', ') : '—'}</td>
        </tr>
      </table>
    </div>

    <div class="detail-section">
      <h4>标签</h4>
      <div style="display: flex; flex-wrap: wrap; gap: 6px;">
        ${v.tags.map(tag => `<span class="tag">${tagLabel(tag)}</span>`).join('')}
      </div>
    </div>

    ${v.deps.length > 0 ? `
      <div class="detail-section">
        <h4>依赖链</h4>
        <div style="font-size: 0.8rem; color: var(--text-muted);">
          ${buildDependencyChain(v.id).map(step => `<div style="padding: 4px 0;">${step}</div>`).join('')}
        </div>
      </div>
    ` : ''}
  `;

  document.getElementById('detail-panel').classList.add('open');
}

function closeDetail() {
  document.getElementById('detail-panel').classList.remove('open');
}

function buildDependencyChain(id) {
  const chain = [];
  const visited = new Set();

  function trace(vId, level = 0) {
    if (visited.has(vId)) return;
    visited.add(vId);

    const v = VERSIONS.find(ver => ver.id === vId);
    if (!v) return;

    const indent = '→ '.repeat(level);
    chain.push(`${indent}<span style="color: ${PHASE_COLORS[v.phase]}">${v.id}</span> ${versionTitle(v)}`);

    v.deps.forEach(depId => trace(depId, level + 1));
  }

  trace(id);
  return chain;
}

// Close panel on Escape
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    closeDetail();
  }
});

// ========== COMPARE VIEW ==========
let compareState = {
  selected: []
};

function renderCompareView() {
  const container = document.getElementById('compare-view');

  const doneVersions = VERSIONS.filter(v => v.status === 'done');

  container.innerHTML = `
    <div class="compare-view">
      <div class="compare-header">
        <h2 style="font-size: 1.5rem; margin-bottom: 8px;">版本对比</h2>
        <p style="color: var(--text-muted); font-size: 0.85rem;">选择 2-4 个已完成版本进行并排比较</p>
      </div>

      <div class="compare-selector">
        <div class="version-selector">
          <label>版本 1</label>
          <select id="compare-v1" onchange="updateCompare()">
            <option value="">请选择</option>
            ${doneVersions.map(v => `<option value="${v.id}">${v.id} - ${versionTitle(v)}</option>`).join('')}
          </select>
        </div>
        <div class="version-selector">
          <label>版本 2</label>
          <select id="compare-v2" onchange="updateCompare()">
            <option value="">请选择</option>
            ${doneVersions.map(v => `<option value="${v.id}">${v.id} - ${versionTitle(v)}</option>`).join('')}
          </select>
        </div>
        <div class="version-selector">
          <label>版本 3（可选）</label>
          <select id="compare-v3" onchange="updateCompare()">
            <option value="">请选择</option>
            ${doneVersions.map(v => `<option value="${v.id}">${v.id} - ${versionTitle(v)}</option>`).join('')}
          </select>
        </div>
        <div class="version-selector">
          <label>版本 4（可选）</label>
          <select id="compare-v4" onchange="updateCompare()">
            <option value="">请选择</option>
            ${doneVersions.map(v => `<option value="${v.id}">${v.id} - ${versionTitle(v)}</option>`).join('')}
          </select>
        </div>
      </div>

      <div id="compare-results" class="compare-grid"></div>
    </div>
  `;
}

function updateCompare() {
  const ids = ['compare-v1', 'compare-v2', 'compare-v3', 'compare-v4']
    .map(id => document.getElementById(id)?.value)
    .filter(v => v);

  const resultsDiv = document.getElementById('compare-results');

  if (ids.length < 2) {
    resultsDiv.innerHTML = '<p style="text-align: center; color: var(--text-muted); padding: 40px;">请至少选择 2 个版本进行对比</p>';
    return;
  }

  const versions = ids.map(id => VERSIONS.find(v => v.id === id)).filter(v => v);

  resultsDiv.innerHTML = versions.map(v => {
    const phaseColor = PHASE_COLORS[v.phase];
    const metrics = extractMetrics(v);
    const phase = PHASES.find(p => p.id === v.phase);

    return `
      <div class="compare-card" style="border-left: 4px solid ${phaseColor}">
        <div class="compare-card-header">
          <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
            <div class="version-id" style="color: ${phaseColor}">${v.id}</div>
            <div style="font-weight: 600; font-size: 0.9rem;">${versionTitle(v)}</div>
            <a class="inline-action compact" href="${mujocoPageHref(v.id)}" data-mujoco-id="${v.id}" data-no-detail title="打开 ${v.id} 的 MuJoCo 仿真入口">MuJoCo</a>
          </div>
          <div style="font-size: 0.75rem; color: var(--text-muted);">${v.desc}</div>
        </div>

        <div class="compare-metric">
          <span class="compare-metric-label">阶段</span>
          <span class="compare-metric-value" style="color: ${phaseColor}">${phaseLabel(phase)}</span>
        </div>

        <div class="compare-metric">
          <span class="compare-metric-label">日期</span>
          <span class="compare-metric-value">${v.date}</span>
        </div>

        <div class="compare-metric">
          <span class="compare-metric-label">被动性</span>
          <span class="compare-metric-value">${passiveLabel(v.passive)}</span>
        </div>

        ${metrics.cot ? `
          <div class="compare-metric">
            <span class="compare-metric-label">CoT</span>
            <span class="compare-metric-value" style="color: var(--done)">${metrics.cot}</span>
          </div>
        ` : ''}

        ${metrics.successRate ? `
          <div class="compare-metric">
            <span class="compare-metric-label">成功率</span>
            <span class="compare-metric-value" style="color: var(--next)">${metrics.successRate}</span>
          </div>
        ` : ''}

        ${metrics.floquet ? `
          <div class="compare-metric">
            <span class="compare-metric-label">最大 Floquet</span>
            <span class="compare-metric-value" style="color: var(--accent)">${metrics.floquet}</span>
          </div>
        ` : ''}

        ${metrics.forward ? `
          <div class="compare-metric">
            <span class="compare-metric-label">前进距离</span>
            <span class="compare-metric-value">${metrics.forward}</span>
          </div>
        ` : ''}

        <div class="compare-metric">
          <span class="compare-metric-label">依赖数</span>
          <span class="compare-metric-value">${v.deps.length || '无'}</span>
        </div>

        <div class="compare-metric">
          <span class="compare-metric-label">标签</span>
          <span class="compare-metric-value" style="font-size: 0.7rem;">${v.tags.slice(0, 3).map(tagLabel).join('、')}${v.tags.length > 3 ? '...' : ''}</span>
        </div>

        ${v.findings ? `
          <div style="margin-top: 16px; padding: 12px; background: var(--surface2); border-radius: 6px; border-left: 3px solid var(--accent);">
            <div style="font-size: 0.7rem; font-weight: 600; color: var(--accent); margin-bottom: 4px;">关键发现</div>
            <div style="font-size: 0.75rem; line-height: 1.5; color: var(--text-muted);">${v.findings}</div>
          </div>
        ` : ''}
      </div>
    `;
  }).join('');
}

function extractMetrics(version) {
  const metrics = {};
  const findings = version.findings || '';

  // Extract CoT
  const cotMatch = findings.match(/CoT[=:\s]+([\d.]+)/);
  if (cotMatch) metrics.cot = cotMatch[1];

  // Extract success rate
  const successMatch = findings.match(/(\d+)\/(\d+)/);
  if (successMatch) {
    const rate = ((parseInt(successMatch[1]) / parseInt(successMatch[2])) * 100).toFixed(1);
    metrics.successRate = `${successMatch[1]}/${successMatch[2]} (${rate}%)`;
  }

  // Extract Floquet multiplier
  const floquetMatch = findings.match(/max\|lambda\|[=:\s]+([\d.]+)/i);
  if (floquetMatch) metrics.floquet = floquetMatch[1];

  // Extract forward distance
  const forwardMatch = findings.match(/forward[=:\s]+([\d.]+)\s*m/i);
  if (forwardMatch) metrics.forward = forwardMatch[1] + ' m';

  return metrics;
}

// ========== TRENDS VIEW ==========
function renderTrendsView() {
  const container = document.getElementById('trends-view');

  // 提取带有 CoT 指标的版本
  const cotData = VERSIONS
    .filter(v => v.status === 'done' && v.findings)
    .map(v => {
      const metrics = extractMetrics(v);
      return metrics.cot ? { id: v.id, phase: v.phase, cot: parseFloat(metrics.cot), title: versionTitle(v) } : null;
    })
    .filter(v => v);

  // 提取带有成功率指标的版本
  const successData = VERSIONS
    .filter(v => v.status === 'done' && v.findings)
    .map(v => {
      const match = v.findings.match(/(\d+)\/(\d+)/);
      if (match) {
        const rate = (parseInt(match[1]) / parseInt(match[2])) * 100;
        return { id: v.id, phase: v.phase, rate, title: versionTitle(v) };
      }
      return null;
    })
    .filter(v => v);

  container.innerHTML = `
    <div class="trends-view">
      <h2 style="font-size: 1.5rem; margin-bottom: 24px;">能耗与性能趋势</h2>

      ${cotData.length > 0 ? `
        <div class="chart-container">
          <div class="chart-title">运输成本（CoT）演化</div>
          <div class="chart-canvas" id="cot-chart"></div>
        </div>
      ` : ''}

      ${successData.length > 0 ? `
        <div class="chart-container">
          <div class="chart-title">各版本成功率</div>
          <div class="chart-canvas" id="success-chart"></div>
        </div>
      ` : ''}

      <div class="chart-container">
        <div class="chart-title">各阶段已完成版本数</div>
        <div class="chart-canvas" id="timeline-chart"></div>
      </div>
    </div>
  `;

  if (cotData.length > 0) {
    renderCotChart(cotData);
  }

  if (successData.length > 0) {
    renderSuccessChart(successData);
  }

  renderTimelineChart();
}

function renderCotChart(data) {
  const canvas = document.getElementById('cot-chart');
  if (!canvas) return;

  const width = canvas.clientWidth;
  const height = 400;
  const padding = { top: 40, right: 40, bottom: 60, left: 60 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  const maxCot = Math.max(...data.map(d => d.cot)) * 1.1;
  const minCot = Math.min(...data.map(d => d.cot)) * 0.9;

  let html = `
    <svg width="${width}" height="${height}" style="background: transparent;">
      <defs>
        <linearGradient id="cotGrad" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" style="stop-color: rgba(96, 165, 250, 0.6); stop-opacity: 1" />
          <stop offset="100%" style="stop-color: rgba(96, 165, 250, 0.1); stop-opacity: 1" />
        </linearGradient>
      </defs>

      <!-- 坐标轴 -->
      <line x1="${padding.left}" y1="${padding.top}" x2="${padding.left}" y2="${height - padding.bottom}"
            stroke="rgba(45, 53, 72, 0.8)" stroke-width="2"/>
      <line x1="${padding.left}" y1="${height - padding.bottom}" x2="${width - padding.right}" y2="${height - padding.bottom}"
            stroke="rgba(45, 53, 72, 0.8)" stroke-width="2"/>

      <!-- Y 轴标签 -->
      <text x="${padding.left - 10}" y="${padding.top}" text-anchor="end" fill="#8892a4" font-size="11">${maxCot.toFixed(3)}</text>
      <text x="${padding.left - 10}" y="${height - padding.bottom}" text-anchor="end" fill="#8892a4" font-size="11">${minCot.toFixed(3)}</text>
      <text x="${padding.left - 45}" y="${height / 2}" text-anchor="middle" fill="#e8ecf4" font-size="13" font-weight="600" transform="rotate(-90, ${padding.left - 45}, ${height / 2})">运输成本 CoT</text>

      <!-- 网格线 -->
      ${[0, 0.25, 0.5, 0.75, 1].map(frac => {
        const y = padding.top + chartHeight * frac;
        return `<line x1="${padding.left}" y1="${y}" x2="${width - padding.right}" y2="${y}" stroke="rgba(45, 53, 72, 0.3)" stroke-width="1" stroke-dasharray="4,4"/>`;
      }).join('')}
  `;

  // 绘制数据点和折线
  const xDivisor = Math.max(data.length - 1, 1);
  const points = data.map((d, i) => {
    const x = data.length === 1
      ? padding.left + chartWidth / 2
      : padding.left + (chartWidth / xDivisor) * i;
    const y = padding.top + chartHeight * (1 - (d.cot - minCot) / (maxCot - minCot));
    return { x, y, d };
  });

  // 面积填充
  const areaPath = `M ${points[0].x},${height - padding.bottom} ` +
    points.map(p => `L ${p.x},${p.y}`).join(' ') +
    ` L ${points[points.length - 1].x},${height - padding.bottom} Z`;
  html += `<path d="${areaPath}" fill="url(#cotGrad)" opacity="0.5"/>`;

  // 折线
  const linePath = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x},${p.y}`).join(' ');
  html += `<path d="${linePath}" fill="none" stroke="#60a5fa" stroke-width="3"/>`;

  // 数据点
  points.forEach(p => {
    const color = PHASE_COLORS[p.d.phase];
    html += `
      <circle cx="${p.x}" cy="${p.y}" r="6" fill="${color}" stroke="#0a0e14" stroke-width="2">
        <title>${p.d.id}: CoT=${p.d.cot}</title>
      </circle>
    `;
  });

  // X 轴标签
  points.forEach((p, i) => {
    html += `
      <text x="${p.x}" y="${height - padding.bottom + 20}" text-anchor="middle" fill="#8892a4" font-size="10" font-weight="600">${p.d.id}</text>
    `;
  });

  html += `</svg>`;
  canvas.innerHTML = html;
}

function renderSuccessChart(data) {
  const canvas = document.getElementById('success-chart');
  if (!canvas) return;

  const width = canvas.clientWidth;
  const height = 400;
  const padding = { top: 40, right: 40, bottom: 60, left: 60 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  let html = `
    <svg width="${width}" height="${height}" style="background: transparent;">
      <!-- 坐标轴 -->
      <line x1="${padding.left}" y1="${padding.top}" x2="${padding.left}" y2="${height - padding.bottom}"
            stroke="rgba(45, 53, 72, 0.8)" stroke-width="2"/>
      <line x1="${padding.left}" y1="${height - padding.bottom}" x2="${width - padding.right}" y2="${height - padding.bottom}"
            stroke="rgba(45, 53, 72, 0.8)" stroke-width="2"/>

      <!-- Y 轴标签 -->
      <text x="${padding.left - 10}" y="${padding.top}" text-anchor="end" fill="#8892a4" font-size="11">100%</text>
      <text x="${padding.left - 10}" y="${height - padding.bottom}" text-anchor="end" fill="#8892a4" font-size="11">0%</text>
      <text x="${padding.left - 45}" y="${height / 2}" text-anchor="middle" fill="#e8ecf4" font-size="13" font-weight="600" transform="rotate(-90, ${padding.left - 45}, ${height / 2})">成功率</text>
  `;

  // 柱状图
  const barWidth = Math.min(40, chartWidth / data.length * 0.8);
  data.forEach((d, i) => {
    const x = padding.left + (chartWidth / data.length) * i + (chartWidth / data.length - barWidth) / 2;
    const barHeight = (chartHeight * d.rate / 100);
    const y = height - padding.bottom - barHeight;
    const color = PHASE_COLORS[d.phase];

    html += `
      <rect x="${x}" y="${y}" width="${barWidth}" height="${barHeight}"
            fill="${color}" opacity="0.8" rx="4">
        <title>${d.id}: ${d.rate.toFixed(1)}%</title>
      </rect>
      <text x="${x + barWidth / 2}" y="${y - 5}" text-anchor="middle" fill="${color}" font-size="11" font-weight="700">${d.rate.toFixed(0)}%</text>
      <text x="${x + barWidth / 2}" y="${height - padding.bottom + 20}" text-anchor="middle" fill="#8892a4" font-size="10" font-weight="600">${d.id}</text>
    `;
  });

  html += `</svg>`;
  canvas.innerHTML = html;
}

function renderTimelineChart() {
  const canvas = document.getElementById('timeline-chart');
  if (!canvas) return;

  const width = canvas.clientWidth;
  const height = 400;
  const padding = { top: 40, right: 40, bottom: 40, left: 60 };

  const phaseData = PHASES.map(phase => ({
    ...phase,
    versions: VERSIONS.filter(v => v.phase === phase.id && v.status === 'done')
  })).filter(p => p.versions.length > 0);

  const maxVersions = Math.max(...phaseData.map(p => p.versions.length));
  const barHeight = 50;
  const spacing = 20;

  const totalHeight = phaseData.length * (barHeight + spacing) + padding.top + padding.bottom;

  let html = `
    <svg width="${width}" height="${totalHeight}" style="background: transparent;">
  `;

  phaseData.forEach((phase, i) => {
    const y = padding.top + i * (barHeight + spacing);
    const barWidth = (width - padding.left - padding.right) * (phase.versions.length / maxVersions);

    html += `
      <text x="${padding.left - 10}" y="${y + barHeight / 2 + 5}" text-anchor="end" fill="${phase.color}" font-size="12" font-weight="700">${phaseLabel(phase)}</text>
      <rect x="${padding.left}" y="${y}" width="${barWidth}" height="${barHeight}"
            fill="${phase.color}" opacity="0.3" rx="6"/>
      <text x="${padding.left + barWidth + 10}" y="${y + barHeight / 2 + 5}" fill="#e8ecf4" font-size="13" font-weight="600">${phase.versions.length} 个版本</text>
    `;

    // 版本点
    phase.versions.forEach((v, j) => {
      const cx = padding.left + (barWidth / phase.versions.length) * (j + 0.5);
      const cy = y + barHeight / 2;
      html += `
        <circle cx="${cx}" cy="${cy}" r="6" fill="${phase.color}" stroke="#0a0e14" stroke-width="2">
          <title>${v.id}: ${versionTitle(v)}</title>
        </circle>
      `;
    });
  });

  html += `</svg>`;
  canvas.innerHTML = html;
}

// ========== HEATMAP VIEW ==========
function renderHeatmapView() {
  const container = document.getElementById('heatmap-view');

  container.innerHTML = `
    <div class="heatmap-view">
      <h2 style="font-size: 1.5rem; margin-bottom: 24px;">参数敏感性分析</h2>

      <div class="heatmap-container">
        <div class="heatmap-title">V13 参数空间成功率（切片 C：6x6 网格）</div>
        <p style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 16px;">
          足半径 × 腿长参数扫描，成功率 16.7%（6/36 个网格）
        </p>
        <div id="heatmap-v13"></div>
        <div class="heatmap-legend">
          <span style="color: var(--text-muted);">失败</span>
          <div class="heatmap-legend-gradient"></div>
          <span style="color: var(--text-muted);">成功</span>
        </div>
      </div>

      <div class="heatmap-container">
        <div class="heatmap-title">V13.6 FSM 控制器成功率（切片 C：6x6 网格）</div>
        <p style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 16px;">
          同一参数空间切换为事件驱动 FSM 后，成功率 11.1%（4/36 个网格）
        </p>
        <div id="heatmap-v136"></div>
        <div class="heatmap-legend">
          <span style="color: var(--text-muted);">失败</span>
          <div class="heatmap-legend-gradient"></div>
          <span style="color: var(--text-muted);">成功</span>
        </div>
      </div>

      <div class="heatmap-container">
        <div class="heatmap-title">V14c 摆臂质量敏感性（6x6 网格）</div>
        <p style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 16px;">
          摆臂质量与参数联合扫描，显示质量增加会单调削弱稳定性
        </p>
        <div id="heatmap-v14c"></div>
        <div class="heatmap-legend">
          <span style="color: var(--text-muted);">失败</span>
          <div class="heatmap-legend-gradient"></div>
          <span style="color: var(--text-muted);">成功</span>
        </div>
      </div>

      <div class="heatmap-container">
        <div class="heatmap-title">V16 电机库仑摩擦 τ_C 共振模式</div>
        <p style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 16px;">
          库仑摩擦扫描呈非单调共振：成功带 {0, 0.034, 0.27+}，失败带 [0.013, 0.20]
        </p>
        <div id="heatmap-v16"></div>
        <div class="heatmap-legend">
          <span style="color: var(--text-muted);">失败</span>
          <div class="heatmap-legend-gradient"></div>
          <span style="color: var(--text-muted);">成功</span>
        </div>
      </div>
    </div>
  `;

  // 根据关键发现绘制示意热力图
  renderHeatmap('heatmap-v13', generateV13Data());
  renderHeatmap('heatmap-v136', generateV136Data());
  renderHeatmap('heatmap-v14c', generateV14cData());
  renderHeatmap('heatmap-v16', generateV16Data());
}

function generateV13Data() {
  // V13：6/36 成功，集中在角落带
  const data = Array(6).fill(0).map(() => Array(6).fill(0));
  // 成功格集中在角落和边缘
  data[0][5] = 1;
  data[1][4] = 1;
  data[1][5] = 1;
  data[2][4] = 1;
  data[2][5] = 1;
  data[3][5] = 1;
  return data;
}

function generateV136Data() {
  // V13.6：4/36 成功，向中心移动
  const data = Array(6).fill(0).map(() => Array(6).fill(0));
  data[2][2] = 1;
  data[2][3] = 1;
  data[3][2] = 1;
  data[3][3] = 1;
  return data;
}

function generateV14cData() {
  // V14c：5/36 成功，随摆臂质量单调下降
  const data = Array(6).fill(0).map(() => Array(6).fill(0));
  // 第 0 行质量最低，成功最多
  data[0][1] = 1;
  data[0][2] = 1;
  data[0][3] = 1;
  data[0][4] = 1;
  // 第 1 行仍有少量成功
  data[1][2] = 1;
  return data;
}

function generateV16Data() {
  // V16：非单调共振模式
  const data = Array(1).fill(0).map(() => Array(10).fill(0));
  // 成功带：0、0.034、0.27+
  data[0][0] = 1; // τ_C = 0
  data[0][1] = 1; // τ_C = 0.034
  data[0][2] = 0; // 失败带起点
  data[0][3] = 0;
  data[0][4] = 0;
  data[0][5] = 0;
  data[0][6] = 0; // 失败带终点（0.20）
  data[0][7] = 1; // 0.27+ 成功带
  data[0][8] = 1;
  data[0][9] = 1;
  return data;
}

function renderHeatmap(containerId, data) {
  const container = document.getElementById(containerId);
  if (!container) return;

  const rows = data.length;
  const cols = data[0].length;

  container.innerHTML = `
    <div class="heatmap-grid" style="grid-template-columns: repeat(${cols}, 1fr); max-width: ${cols * 60}px;">
      ${data.flat().map((val, i) => {
        const row = Math.floor(i / cols);
        const col = i % cols;
        const color = val === 1
          ? 'rgba(52, 211, 153, 0.8)'
          : 'rgba(220, 38, 38, 0.8)';
        const label = val === 1 ? '✓' : '✗';
        return `
          <div class="heatmap-cell" style="background: ${color};" title="[${row},${col}]: ${val === 1 ? '成功' : '失败'}">
            ${label}
          </div>
        `;
      }).join('')}
    </div>
  `;
}

window.switchView = switchView;
window.resetGraphView = resetGraphView;
window.fitGraphView = fitGraphView;
window.toggleGraphPhase = toggleGraphPhase;
window.toggleGraphLegend = toggleGraphLegend;
window.toggleGraphToolbar = toggleGraphToolbar;
window.openDetail = openDetail;
window.closeDetail = closeDetail;
window.updateCompare = updateCompare;
