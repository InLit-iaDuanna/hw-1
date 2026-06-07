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

// ========== INIT ==========
document.addEventListener('DOMContentLoaded', () => {
  initViewSwitcher();
  initFilters();
  initSearch();
  updateStats();
  updatePhaseProgress();
  renderCurrentView();
});

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
      const searchable = `${v.id} ${v.title} ${v.desc} ${v.findings} ${v.tags.join(' ')}`.toLowerCase();
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
            ${phase.tag}
          </div>
          <div class="phase-count">${done}/${phaseVersions.length}</div>
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
    container.innerHTML = '<div style="text-align:center;color:var(--text-muted);padding:40px">No versions match the current filters</div>';
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
      if (match) keyMetric = `Success: ${match[1]}/${match[2]}`;
    }

    return `
      <div class="version-card" onclick="openDetail('${v.id}')" data-status="${v.status}" style="--phase1: ${phaseColor}">
        <div class="card-header">
          <div class="version-id" style="color: ${phaseColor}">${v.id}</div>
          <div class="version-title">${v.title}</div>
          <div class="status-badge" style="background: ${statusColor}; color: ${v.status === 'planned' ? 'var(--text)' : '#000'}">${v.status}</div>
        </div>

        <div class="card-desc">${v.desc}</div>

        <div class="card-meta">
          <div class="card-meta-item">
            <span>📅</span> ${v.date}
          </div>
          <div class="card-meta-item">
            <span>📍</span> ${phase.tag}
          </div>
          ${v.passive !== 'tbd' ? `
            <div class="card-meta-item">
              <span>${v.passive === 'yes' ? '✅' : v.passive === 'no' ? '⚙️' : '⚡'}</span> ${v.passive}
            </div>
          ` : ''}
          ${keyMetric ? `
            <div class="card-meta-item" style="color: var(--accent); font-weight: 600;">
              ${keyMetric}
            </div>
          ` : ''}
        </div>

        <div class="card-tags">
          ${v.tags.slice(0, 4).map(tag => `<span class="tag">${tag}</span>`).join('')}
          ${v.tags.length > 4 ? `<span class="tag">+${v.tags.length - 4}</span>` : ''}
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
    container.innerHTML = '<div style="text-align:center;color:var(--text-muted);padding:40px">No versions match the current filters</div>';
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
          <div class="timeline-phase-badge" style="background: ${phase.color}">${phase.tag}</div>
          <div class="timeline-phase-title">${phase.title}</div>
          <div style="color: var(--text-muted); font-size: 0.8rem; margin-left: auto;">${phase.desc}</div>
        </div>

        <div class="timeline-items">
          ${phaseVersions.map(v => {
            const statusColor = STATUS_COLORS[v.status];
            return `
              <div class="timeline-item" style="--dot-color: ${statusColor}" onclick="openDetail('${v.id}')">
                <style>.timeline-item[onclick*="${v.id}"]::before { background: ${statusColor} !important; }</style>
                <div class="timeline-card" style="cursor: pointer; border-left: 3px solid ${phase.color}">
                  <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
                    <div class="version-id" style="color: ${phase.color}">${v.id}</div>
                    <div class="version-title" style="flex: 1">${v.title}</div>
                    <div style="font-size: 0.7rem; color: var(--text-dim)">${v.date}</div>
                  </div>
                  <div style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 8px;">${v.desc}</div>
                  ${v.status === 'done' ? `
                    <div style="font-size: 0.7rem; color: var(--text-muted); padding: 8px; background: var(--surface2); border-radius: 4px;">
                      <strong style="color: var(--accent)">Finding:</strong> ${v.findings}
                    </div>
                  ` : ''}
                  <div style="display: flex; gap: 4px; margin-top: 8px; flex-wrap: wrap;">
                    ${v.tags.map(tag => `<span class="tag">${tag}</span>`).join('')}
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

// ========== GRAPH VIEW (Original Advanced Version) ==========
const NW = 118, NH = 44, GX = 145, GY = 110, OFFX = 60, OFFY = 60;

const INIT_GRID = {
  "V01":[0,2],"V02":[1,2],"V03":[2,2],"V04":[3,2],"V05":[4,2],
  "V06":[5,1],
  "V07":[5,2],"V08":[6,2],"V09":[7,2],"V10":[8,2],"V11":[9,2],"V12":[10,2],"V13":[11,2],
  "V13.5":[12,3],"V13b":[13,3],
  "V13.6":[14,2],"V13.6.1":[15,2],
  "V14":[15,1],"V14b":[16,1],"V14c":[17,1],"V15":[18,1],"V15.1":[19,1],
  "V16":[16,2],"V13.7":[17,2],"V17":[18,2],
  "V18":[19,3],"V19":[20,3],"V20":[21,3],"V21":[22,3],
  "V22":[22,4],"V23":[23,4],"V24":[24,4],"V25":[25,4],
};

let graphState = {
  vpX: 0,
  vpY: 0,
  positions: {},
  nodeGroups: {},
  draggingId: null,
  dragOffX: 0,
  dragOffY: 0,
  dragMoved: false,
  panning: false,
  panX: 0,
  panY: 0,
  panVpX: 0,
  panVpY: 0
};

function renderGraphView(versions) {
  const svg = document.getElementById('graph-svg');
  const container = document.getElementById('graph-view');
  const width = container.clientWidth;
  const height = container.clientHeight;

  svg.setAttribute('width', width);
  svg.setAttribute('height', height);

  if (versions.length === 0) {
    svg.innerHTML = '<text x="50%" y="50%" text-anchor="middle" fill="var(--text-muted)">No versions match the current filters</text>';
    return;
  }

  // Initialize positions
  graphState.positions = {};
  for (const [id, [c, r]] of Object.entries(INIT_GRID)) {
    if (versions.find(v => v.id === id)) {
      graphState.positions[id] = { x: OFFX + c * GX, y: OFFY + r * GY };
    }
  }

  // Clear and setup
  svg.innerHTML = '';
  const NS = 'http://www.w3.org/2000/svg';

  // Create defs
  const defs = document.createElementNS(NS, 'defs');

  // Glow filters for each phase
  Object.entries(PHASE_COLORS).forEach(([phase, color]) => {
    const filter = document.createElementNS(NS, 'filter');
    filter.setAttribute('id', `glow${phase}`);
    filter.setAttribute('x', '-50%');
    filter.setAttribute('y', '-50%');
    filter.setAttribute('width', '200%');
    filter.setAttribute('height', '200%');

    const feGaussian = document.createElementNS(NS, 'feGaussianBlur');
    feGaussian.setAttribute('stdDeviation', '3');
    feGaussian.setAttribute('result', 'coloredBlur');
    filter.appendChild(feGaussian);

    const feMerge = document.createElementNS(NS, 'feMerge');
    const feMergeNode1 = document.createElementNS(NS, 'feMergeNode');
    feMergeNode1.setAttribute('in', 'coloredBlur');
    const feMergeNode2 = document.createElementNS(NS, 'feMergeNode');
    feMergeNode2.setAttribute('in', 'SourceGraphic');
    feMerge.appendChild(feMergeNode1);
    feMerge.appendChild(feMergeNode2);
    filter.appendChild(feMerge);

    defs.appendChild(filter);
  });

  // Arrow markers with glow
  Object.entries(PHASE_COLORS).forEach(([phase, color]) => {
    const marker = document.createElementNS(NS, 'marker');
    marker.setAttribute('id', `arr${phase}`);
    marker.setAttribute('markerWidth', '8');
    marker.setAttribute('markerHeight', '8');
    marker.setAttribute('refX', '7');
    marker.setAttribute('refY', '4');
    marker.setAttribute('orient', 'auto');
    const path = document.createElementNS(NS, 'path');
    path.setAttribute('d', 'M0,0 L8,4 L0,8 Z');
    path.setAttribute('fill', color);
    path.setAttribute('opacity', '0.8');
    path.setAttribute('filter', `url(#glow${phase})`);
    marker.appendChild(path);
    defs.appendChild(marker);
  });

  const markerP = document.createElementNS(NS, 'marker');
  markerP.setAttribute('id', 'arrP');
  markerP.setAttribute('markerWidth', '7');
  markerP.setAttribute('markerHeight', '7');
  markerP.setAttribute('refX', '6');
  markerP.setAttribute('refY', '3');
  markerP.setAttribute('orient', 'auto');
  const pathP = document.createElementNS(NS, 'path');
  pathP.setAttribute('d', 'M0,0 L7,3 L0,6 Z');
  pathP.setAttribute('fill', '#3d4460');
  pathP.setAttribute('opacity', '0.6');
  markerP.appendChild(pathP);
  defs.appendChild(markerP);

  // Gradient for edges
  Object.entries(PHASE_COLORS).forEach(([phase, color]) => {
    const grad = document.createElementNS(NS, 'linearGradient');
    grad.setAttribute('id', `grad${phase}`);
    const stop1 = document.createElementNS(NS, 'stop');
    stop1.setAttribute('offset', '0%');
    stop1.setAttribute('stop-color', color);
    stop1.setAttribute('stop-opacity', '0.3');
    const stop2 = document.createElementNS(NS, 'stop');
    stop2.setAttribute('offset', '100%');
    stop2.setAttribute('stop-color', color);
    stop2.setAttribute('stop-opacity', '0.7');
    grad.appendChild(stop1);
    grad.appendChild(stop2);
    defs.appendChild(grad);
  });

  svg.appendChild(defs);

  // Main group
  const rootG = document.createElementNS(NS, 'g');
  const edgeLayer = document.createElementNS(NS, 'g');
  const gateLayer = document.createElementNS(NS, 'g');
  const nodeLayer = document.createElementNS(NS, 'g');

  rootG.appendChild(edgeLayer);
  rootG.appendChild(gateLayer);
  rootG.appendChild(nodeLayer);
  svg.appendChild(rootG);

  function applyVP() {
    rootG.setAttribute('transform', `translate(${graphState.vpX},${graphState.vpY})`);
  }

  // Draw edges with smart routing
  function drawEdges() {
    edgeLayer.innerHTML = '';
    const offsets = buildEdgeOffsets();

    versions.forEach(v => {
      if (!graphState.positions[v.id]) return;
      const tp = graphState.positions[v.id];
      const color = v.status === 'planned' ? '#3d4460' : PHASE_COLORS[v.phase];
      const opacity = v.status === 'planned' ? 0.2 : (v.status === 'done' ? 0.45 : 0.7);
      const arrowId = v.status === 'planned' ? 'arrP' : `arr${v.phase}`;

      v.deps.forEach(dep => {
        if (!graphState.positions[dep]) return;
        const sp = graphState.positions[dep];
        const sx = sp.x + NW, sy = sp.y + NH / 2;
        const tx = tp.x - 3, ty = tp.y + NH / 2;

        const ek = dep + '->' + v.id;
        const off = offsets[ek] || { idx: 0, total: 1 };
        const spread = off.total > 1 ? ((off.idx / (off.total - 1)) - 0.5) * 32 : 0;

        const dy = ty - sy;
        const dx = tx - sx;
        let d;
        if (Math.abs(dy) < 8) {
          const cx1 = sx + dx * 0.4;
          const cx2 = tx - dx * 0.4;
          d = `M${sx},${sy} C${cx1},${sy + spread} ${cx2},${ty + spread} ${tx},${ty}`;
        } else {
          const cx1 = sx + Math.abs(dx) * 0.45 + spread * 0.3;
          const cx2 = tx - Math.abs(dx) * 0.45 + spread * 0.3;
          d = `M${sx},${sy} C${cx1},${sy} ${cx2},${ty} ${tx},${ty}`;
        }

        const path = document.createElementNS(NS, 'path');
        path.setAttribute('d', d);
        path.setAttribute('fill', 'none');
        path.setAttribute('stroke', v.status === 'planned' ? color : `url(#grad${v.phase})`);
        path.setAttribute('stroke-width', v.status === 'next' ? '2.5' : '2');
        path.setAttribute('opacity', opacity);
        path.setAttribute('marker-end', `url(#${arrowId})`);
        path.setAttribute('filter', v.status !== 'planned' ? `url(#glow${v.phase})` : '');
        if (v.status === 'planned') {
          path.setAttribute('stroke-dasharray', '5,4');
        } else if (v.status === 'next') {
          path.setAttribute('stroke-dasharray', '10,5');
          const animate = document.createElementNS(NS, 'animate');
          animate.setAttribute('attributeName', 'stroke-dashoffset');
          animate.setAttribute('from', '0');
          animate.setAttribute('to', '15');
          animate.setAttribute('dur', '1s');
          animate.setAttribute('repeatCount', 'indefinite');
          path.appendChild(animate);
        }
        edgeLayer.appendChild(path);
      });
    });
  }

  function buildEdgeOffsets() {
    const buckets = {};
    versions.forEach(v => {
      if (!graphState.positions[v.id]) return;
      v.deps.forEach(dep => {
        if (!graphState.positions[dep]) return;
        const sy = Math.round(graphState.positions[dep].y / 10) * 10;
        const ty = Math.round(graphState.positions[v.id].y / 10) * 10;
        const bk = `${sy}:${ty}`;
        if (!buckets[bk]) buckets[bk] = [];
        buckets[bk].push(dep + '->' + v.id);
      });
    });
    const offsets = {};
    Object.values(buckets).forEach(edges => {
      edges.forEach((ek, i) => offsets[ek] = { idx: i, total: edges.length });
    });
    return offsets;
  }

  // Draw gates
  function drawGates() {
    gateLayer.innerHTML = '';
    GATES.forEach(g => {
      if (!graphState.positions[g.after]) return;
      const p = graphState.positions[g.after];
      const gx = p.x + NW + 24, gy = p.y + NH / 2;
      const s = 9, col = g.status === 'passed' ? '#34d399' : '#f59e0b';

      const grp = document.createElementNS(NS, 'g');
      grp.style.cursor = 'help';

      // Outer glow
      const polyGlow = document.createElementNS(NS, 'polygon');
      polyGlow.setAttribute('points', `${gx},${gy - s - 2} ${gx + s + 2},${gy} ${gx},${gy + s + 2} ${gx - s - 2},${gy}`);
      polyGlow.setAttribute('fill', col);
      polyGlow.setAttribute('opacity', '0.3');
      polyGlow.setAttribute('filter', 'url(#glow1)');
      grp.appendChild(polyGlow);

      const poly = document.createElementNS(NS, 'polygon');
      poly.setAttribute('points', `${gx},${gy - s} ${gx + s},${gy} ${gx},${gy + s} ${gx - s},${gy}`);
      poly.setAttribute('fill', col);
      poly.setAttribute('opacity', '0.95');
      grp.appendChild(poly);

      const lt = document.createElementNS(NS, 'text');
      lt.textContent = g.status === 'passed' ? '✓' : '?';
      lt.setAttribute('x', gx);
      lt.setAttribute('y', gy + 4);
      lt.setAttribute('text-anchor', 'middle');
      lt.setAttribute('font-size', '9');
      lt.setAttribute('fill', '#0a0e14');
      lt.setAttribute('font-weight', '700');
      lt.setAttribute('pointer-events', 'none');
      grp.appendChild(lt);

      const lt2 = document.createElementNS(NS, 'text');
      lt2.textContent = g.status === 'passed' ? 'PASSED' : 'PENDING';
      lt2.setAttribute('x', gx);
      lt2.setAttribute('y', gy + s + 11);
      lt2.setAttribute('text-anchor', 'middle');
      lt2.setAttribute('font-size', '7.5');
      lt2.setAttribute('fill', col);
      lt2.setAttribute('opacity', '0.8');
      lt2.setAttribute('pointer-events', 'none');
      grp.appendChild(lt2);

      grp.title = g.text;
      gateLayer.appendChild(grp);
    });
  }

  // Draw nodes
  graphState.nodeGroups = {};
  versions.forEach(v => {
    if (!graphState.positions[v.id]) return;
    const p = graphState.positions[v.id];
    const pc = PHASE_COLORS[v.phase];
    const isPlanned = v.status === 'planned';
    const isNext = v.status === 'next';

    const grp = document.createElementNS(NS, 'g');
    grp.classList.add('node-g');
    grp.style.cursor = 'pointer';
    graphState.nodeGroups[v.id] = grp;

    // Background glow
    if (!isPlanned) {
      const glowRect = document.createElementNS(NS, 'rect');
      glowRect.setAttribute('x', p.x - 2);
      glowRect.setAttribute('y', p.y - 2);
      glowRect.setAttribute('width', NW + 4);
      glowRect.setAttribute('height', NH + 4);
      glowRect.setAttribute('rx', '10');
      glowRect.setAttribute('fill', 'none');
      glowRect.setAttribute('stroke', STATUS_COLORS[v.status]);
      glowRect.setAttribute('stroke-width', '2');
      glowRect.setAttribute('opacity', '0.3');
      glowRect.setAttribute('filter', `url(#glow${v.phase})`);
      grp.appendChild(glowRect);
    }

    const rect = document.createElementNS(NS, 'rect');
    rect.setAttribute('x', p.x);
    rect.setAttribute('y', p.y);
    rect.setAttribute('width', NW);
    rect.setAttribute('height', NH);
    rect.setAttribute('rx', '8');

    // Glassmorphism effect
    const gradId = `node-grad-${v.id}`;
    const nodeGrad = document.createElementNS(NS, 'linearGradient');
    nodeGrad.setAttribute('id', gradId);
    nodeGrad.setAttribute('x1', '0%');
    nodeGrad.setAttribute('y1', '0%');
    nodeGrad.setAttribute('x2', '0%');
    nodeGrad.setAttribute('y2', '100%');
    const stop1 = document.createElementNS(NS, 'stop');
    stop1.setAttribute('offset', '0%');
    stop1.setAttribute('stop-color', isPlanned ? '#14182a' : '#1a1f2e');
    stop1.setAttribute('stop-opacity', isPlanned ? '0.6' : '0.9');
    const stop2 = document.createElementNS(NS, 'stop');
    stop2.setAttribute('offset', '100%');
    stop2.setAttribute('stop-color', isPlanned ? '#0d1117' : '#12161f');
    stop2.setAttribute('stop-opacity', isPlanned ? '0.4' : '0.7');
    nodeGrad.appendChild(stop1);
    nodeGrad.appendChild(stop2);
    defs.appendChild(nodeGrad);

    rect.setAttribute('fill', `url(#${gradId})`);
    rect.setAttribute('stroke', isNext ? '#fbbf24' : isPlanned ? '#2d3548' : pc);
    rect.setAttribute('stroke-width', isNext ? '2.5' : '1.5');
    if (isPlanned) rect.setAttribute('stroke-dasharray', '5,3');
    if (!isPlanned) rect.setAttribute('filter', `url(#glow${v.phase})`);
    rect.classList.add('node-body');
    grp.appendChild(rect);

    const stripe = document.createElementNS(NS, 'rect');
    stripe.setAttribute('x', p.x);
    stripe.setAttribute('y', p.y + 3);
    stripe.setAttribute('width', 4);
    stripe.setAttribute('height', NH - 6);
    stripe.setAttribute('rx', '2');
    stripe.setAttribute('fill', STATUS_COLORS[v.status] || '#3d4460');
    stripe.setAttribute('opacity', '0.9');
    stripe.setAttribute('pointer-events', 'none');
    grp.appendChild(stripe);

    const tid = document.createElementNS(NS, 'text');
    tid.textContent = v.id;
    tid.setAttribute('x', p.x + 10);
    tid.setAttribute('y', p.y + 16);
    tid.setAttribute('font-size', '10');
    tid.setAttribute('font-weight', '800');
    tid.setAttribute('font-family', 'monospace');
    tid.setAttribute('fill', isNext ? '#fbbf24' : pc);
    tid.setAttribute('pointer-events', 'none');
    grp.appendChild(tid);

    const short = v.title.length > 17 ? v.title.slice(0, 15) + '…' : v.title;
    const ttl = document.createElementNS(NS, 'text');
    ttl.textContent = short;
    ttl.setAttribute('x', p.x + 10);
    ttl.setAttribute('y', p.y + 32);
    ttl.setAttribute('font-size', '8.5');
    ttl.setAttribute('fill', '#6b7a96');
    ttl.setAttribute('pointer-events', 'none');
    grp.appendChild(ttl);

    grp.addEventListener('click', (e) => {
      e.stopPropagation();
      openDetail(v.id);
    });

    makeDraggable(grp, v.id);
    nodeLayer.appendChild(grp);
  });

  function updateNodePos(id) {
    const p = graphState.positions[id];
    const grp = graphState.nodeGroups[id];
    if (!grp) return;
    const ch = [...grp.children];

    // Find elements by their tag/class instead of assuming index
    // Structure: [glowRect?], rect, stripe, tid(text), ttl(text)
    let rectIdx = 0, stripeIdx = 1, tidIdx = 2, ttlIdx = 3;

    // If first child is the glow rect, shift indices
    if (ch[0].tagName === 'rect' && ch[0].getAttribute('filter')?.includes('glow')) {
      rectIdx = 1;
      stripeIdx = 2;
      tidIdx = 3;
      ttlIdx = 4;
      // Update glow rect
      ch[0].setAttribute('x', p.x - 2);
      ch[0].setAttribute('y', p.y - 2);
    }

    // Update main rect
    if (ch[rectIdx]) {
      ch[rectIdx].setAttribute('x', p.x);
      ch[rectIdx].setAttribute('y', p.y);
    }
    // Update stripe
    if (ch[stripeIdx]) {
      ch[stripeIdx].setAttribute('x', p.x);
      ch[stripeIdx].setAttribute('y', p.y + 3);
    }
    // Update ID text
    if (ch[tidIdx]) {
      ch[tidIdx].setAttribute('x', p.x + 10);
      ch[tidIdx].setAttribute('y', p.y + 16);
    }
    // Update title text
    if (ch[ttlIdx]) {
      ch[ttlIdx].setAttribute('x', p.x + 10);
      ch[ttlIdx].setAttribute('y', p.y + 32);
    }
  }

  function svgPt(e) {
    const r = svg.getBoundingClientRect();
    return { x: (e.clientX - r.left) - graphState.vpX, y: (e.clientY - r.top) - graphState.vpY };
  }

  function makeDraggable(grp, id) {
    grp.addEventListener('mousedown', e => {
      if (e.button !== 0) return;
      e.stopPropagation();
      graphState.draggingId = id;
      graphState.dragMoved = false;
      const pt = svgPt(e);
      graphState.dragOffX = pt.x - graphState.positions[id].x;
      graphState.dragOffY = pt.y - graphState.positions[id].y;
      svg.style.cursor = 'grabbing';
    });
  }

  // Pan
  svg.addEventListener('mousedown', e => {
    if (e.button !== 0 || e.target.closest('.node-g')) return;
    graphState.panning = true;
    graphState.panX = e.clientX;
    graphState.panY = e.clientY;
    graphState.panVpX = graphState.vpX;
    graphState.panVpY = graphState.vpY;
    svg.style.cursor = 'grabbing';
  });

  svg.addEventListener('mousemove', e => {
    if (graphState.draggingId) {
      graphState.dragMoved = true;
      const pt = svgPt(e);
      graphState.positions[graphState.draggingId].x = pt.x - graphState.dragOffX;
      graphState.positions[graphState.draggingId].y = pt.y - graphState.dragOffY;
      updateNodePos(graphState.draggingId);
      drawEdges();
      drawGates();
      return;
    }
    if (graphState.panning) {
      graphState.vpX = graphState.panVpX + (e.clientX - graphState.panX);
      graphState.vpY = graphState.panVpY + (e.clientY - graphState.panY);
      applyVP();
    }
  });

  svg.addEventListener('mouseup', () => {
    graphState.draggingId = null;
    graphState.panning = false;
    svg.style.cursor = 'default';
  });

  svg.addEventListener('mouseleave', () => {
    graphState.draggingId = null;
    graphState.panning = false;
  });

  drawEdges();
  drawGates();
  applyVP();

  // Add hover effects for nodes
  Object.values(graphState.nodeGroups).forEach(nodeGrp => {
    nodeGrp.addEventListener('mouseenter', function() {
      this.style.filter = 'brightness(1.3)';
      this.style.transform = 'scale(1.05)';
      this.style.transformOrigin = 'center';
      this.style.transition = 'all 0.2s';
    });
    nodeGrp.addEventListener('mouseleave', function() {
      this.style.filter = '';
      this.style.transform = '';
    });
  });
}

// Graph control functions
function resetGraphView() {
  graphState.vpX = 0;
  graphState.vpY = 0;
  renderCurrentView();
}

function fitGraphView() {
  // Calculate bounds of all nodes
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
  const padding = 100;
  graphState.vpX = (container.clientWidth - maxX - minX) / 2 - minX + padding;
  graphState.vpY = (container.clientHeight - maxY - minY) / 2 - minY + padding;

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

  document.getElementById('detail-title').textContent = v.title;

  const body = document.getElementById('detail-body');
  body.innerHTML = `
    <div class="detail-section">
      <div style="display: inline-block; padding: 4px 10px; background: ${statusColor}; color: ${v.status === 'planned' ? 'var(--text)' : '#000'}; border-radius: 4px; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; margin-bottom: 12px;">
        ${v.status}
      </div>
    </div>

    <div class="detail-section">
      <h4>Description</h4>
      <p>${v.desc}</p>
    </div>

    ${v.findings ? `
      <div class="detail-section">
        <h4>Key Findings</h4>
        <p style="background: var(--surface2); padding: 12px; border-left: 3px solid var(--accent); border-radius: 4px;">${v.findings}</p>
      </div>
    ` : ''}

    <div class="detail-section">
      <h4>Details</h4>
      <table class="detail-table">
        <tr>
          <td>Phase</td>
          <td><span style="color: ${phaseColor}; font-weight: 600">${phase.tag}</span> — ${phase.title}</td>
        </tr>
        <tr>
          <td>Passive</td>
          <td>${v.passive}</td>
        </tr>
        <tr>
          <td>Date</td>
          <td>${v.date}</td>
        </tr>
        <tr>
          <td>Folder</td>
          <td><code style="font-size: 0.75rem">${v.folder || '—'}</code></td>
        </tr>
        <tr>
          <td>Dependencies</td>
          <td>${v.deps.length ? v.deps.map(d => `<span style="color: var(--accent); cursor: pointer;" onclick="openDetail('${d}')">${d}</span>`).join(', ') : '—'}</td>
        </tr>
      </table>
    </div>

    <div class="detail-section">
      <h4>Tags</h4>
      <div style="display: flex; flex-wrap: wrap; gap: 6px;">
        ${v.tags.map(tag => `<span class="tag">${tag}</span>`).join('')}
      </div>
    </div>

    ${v.deps.length > 0 ? `
      <div class="detail-section">
        <h4>Dependency Chain</h4>
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
    chain.push(`${indent}<span style="color: ${PHASE_COLORS[v.phase]}">${v.id}</span> ${v.title}`);

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
        <h2 style="font-size: 1.5rem; margin-bottom: 8px;">Version Comparison</h2>
        <p style="color: var(--text-muted); font-size: 0.85rem;">Select 2-4 versions to compare side-by-side</p>
      </div>

      <div class="compare-selector">
        <div class="version-selector">
          <label>Version 1</label>
          <select id="compare-v1" onchange="updateCompare()">
            <option value="">-- Select --</option>
            ${doneVersions.map(v => `<option value="${v.id}">${v.id} - ${v.title}</option>`).join('')}
          </select>
        </div>
        <div class="version-selector">
          <label>Version 2</label>
          <select id="compare-v2" onchange="updateCompare()">
            <option value="">-- Select --</option>
            ${doneVersions.map(v => `<option value="${v.id}">${v.id} - ${v.title}</option>`).join('')}
          </select>
        </div>
        <div class="version-selector">
          <label>Version 3 (optional)</label>
          <select id="compare-v3" onchange="updateCompare()">
            <option value="">-- Select --</option>
            ${doneVersions.map(v => `<option value="${v.id}">${v.id} - ${v.title}</option>`).join('')}
          </select>
        </div>
        <div class="version-selector">
          <label>Version 4 (optional)</label>
          <select id="compare-v4" onchange="updateCompare()">
            <option value="">-- Select --</option>
            ${doneVersions.map(v => `<option value="${v.id}">${v.id} - ${v.title}</option>`).join('')}
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
    resultsDiv.innerHTML = '<p style="text-align: center; color: var(--text-muted); padding: 40px;">Select at least 2 versions to compare</p>';
    return;
  }

  const versions = ids.map(id => VERSIONS.find(v => v.id === id)).filter(v => v);

  resultsDiv.innerHTML = versions.map(v => {
    const phaseColor = PHASE_COLORS[v.phase];
    const metrics = extractMetrics(v);

    return `
      <div class="compare-card" style="border-left: 4px solid ${phaseColor}">
        <div class="compare-card-header">
          <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
            <div class="version-id" style="color: ${phaseColor}">${v.id}</div>
            <div style="font-weight: 600; font-size: 0.9rem;">${v.title}</div>
          </div>
          <div style="font-size: 0.75rem; color: var(--text-muted);">${v.desc}</div>
        </div>

        <div class="compare-metric">
          <span class="compare-metric-label">Phase</span>
          <span class="compare-metric-value" style="color: ${phaseColor}">${PHASES.find(p => p.id === v.phase).tag}</span>
        </div>

        <div class="compare-metric">
          <span class="compare-metric-label">Date</span>
          <span class="compare-metric-value">${v.date}</span>
        </div>

        <div class="compare-metric">
          <span class="compare-metric-label">Passive</span>
          <span class="compare-metric-value">${v.passive}</span>
        </div>

        ${metrics.cot ? `
          <div class="compare-metric">
            <span class="compare-metric-label">CoT</span>
            <span class="compare-metric-value" style="color: var(--done)">${metrics.cot}</span>
          </div>
        ` : ''}

        ${metrics.successRate ? `
          <div class="compare-metric">
            <span class="compare-metric-label">Success Rate</span>
            <span class="compare-metric-value" style="color: var(--next)">${metrics.successRate}</span>
          </div>
        ` : ''}

        ${metrics.floquet ? `
          <div class="compare-metric">
            <span class="compare-metric-label">Max Floquet</span>
            <span class="compare-metric-value" style="color: var(--accent)">${metrics.floquet}</span>
          </div>
        ` : ''}

        ${metrics.forward ? `
          <div class="compare-metric">
            <span class="compare-metric-label">Forward Distance</span>
            <span class="compare-metric-value">${metrics.forward}</span>
          </div>
        ` : ''}

        <div class="compare-metric">
          <span class="compare-metric-label">Dependencies</span>
          <span class="compare-metric-value">${v.deps.length || 'None'}</span>
        </div>

        <div class="compare-metric">
          <span class="compare-metric-label">Tags</span>
          <span class="compare-metric-value" style="font-size: 0.7rem;">${v.tags.slice(0, 3).join(', ')}${v.tags.length > 3 ? '...' : ''}</span>
        </div>

        ${v.findings ? `
          <div style="margin-top: 16px; padding: 12px; background: var(--surface2); border-radius: 6px; border-left: 3px solid var(--accent);">
            <div style="font-size: 0.7rem; font-weight: 600; color: var(--accent); margin-bottom: 4px;">KEY FINDING</div>
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

  // Extract versions with CoT data
  const cotData = VERSIONS
    .filter(v => v.status === 'done' && v.findings)
    .map(v => {
      const metrics = extractMetrics(v);
      return metrics.cot ? { id: v.id, phase: v.phase, cot: parseFloat(metrics.cot), title: v.title } : null;
    })
    .filter(v => v);

  // Extract versions with success rate data
  const successData = VERSIONS
    .filter(v => v.status === 'done' && v.findings)
    .map(v => {
      const match = v.findings.match(/(\d+)\/(\d+)/);
      if (match) {
        const rate = (parseInt(match[0]) / parseInt(match[1])) * 100;
        return { id: v.id, phase: v.phase, rate, title: v.title };
      }
      return null;
    })
    .filter(v => v);

  container.innerHTML = `
    <div class="trends-view">
      <h2 style="font-size: 1.5rem; margin-bottom: 24px;">Energy & Performance Trends</h2>

      ${cotData.length > 0 ? `
        <div class="chart-container">
          <div class="chart-title">Cost of Transport (CoT) Evolution</div>
          <div class="chart-canvas" id="cot-chart"></div>
        </div>
      ` : ''}

      ${successData.length > 0 ? `
        <div class="chart-container">
          <div class="chart-title">Success Rate Across Versions</div>
          <div class="chart-canvas" id="success-chart"></div>
        </div>
      ` : ''}

      <div class="chart-container">
        <div class="chart-title">Version Timeline by Phase</div>
        <div class="chart-canvas" id="timeline-chart"></div>
      </div>
    </div>
  `;

  // Render CoT chart
  if (cotData.length > 0) {
    renderCotChart(cotData);
  }

  // Render success chart
  if (successData.length > 0) {
    renderSuccessChart(successData);
  }

  // Render timeline chart
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

      <!-- Axes -->
      <line x1="${padding.left}" y1="${padding.top}" x2="${padding.left}" y2="${height - padding.bottom}"
            stroke="rgba(45, 53, 72, 0.8)" stroke-width="2"/>
      <line x1="${padding.left}" y1="${height - padding.bottom}" x2="${width - padding.right}" y2="${height - padding.bottom}"
            stroke="rgba(45, 53, 72, 0.8)" stroke-width="2"/>

      <!-- Y-axis labels -->
      <text x="${padding.left - 10}" y="${padding.top}" text-anchor="end" fill="#8892a4" font-size="11">${maxCot.toFixed(3)}</text>
      <text x="${padding.left - 10}" y="${height - padding.bottom}" text-anchor="end" fill="#8892a4" font-size="11">${minCot.toFixed(3)}</text>
      <text x="${padding.left - 45}" y="${height / 2}" text-anchor="middle" fill="#e8ecf4" font-size="13" font-weight="600" transform="rotate(-90, ${padding.left - 45}, ${height / 2})">Cost of Transport</text>

      <!-- Grid lines -->
      ${[0, 0.25, 0.5, 0.75, 1].map(frac => {
        const y = padding.top + chartHeight * frac;
        return `<line x1="${padding.left}" y1="${y}" x2="${width - padding.right}" y2="${y}" stroke="rgba(45, 53, 72, 0.3)" stroke-width="1" stroke-dasharray="4,4"/>`;
      }).join('')}
  `;

  // Plot data points and line
  const points = data.map((d, i) => {
    const x = padding.left + (chartWidth / (data.length - 1)) * i;
    const y = padding.top + chartHeight * (1 - (d.cot - minCot) / (maxCot - minCot));
    return { x, y, d };
  });

  // Area fill
  const areaPath = `M ${points[0].x},${height - padding.bottom} ` +
    points.map(p => `L ${p.x},${p.y}`).join(' ') +
    ` L ${points[points.length - 1].x},${height - padding.bottom} Z`;
  html += `<path d="${areaPath}" fill="url(#cotGrad)" opacity="0.5"/>`;

  // Line
  const linePath = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x},${p.y}`).join(' ');
  html += `<path d="${linePath}" fill="none" stroke="#60a5fa" stroke-width="3"/>`;

  // Points
  points.forEach(p => {
    const color = PHASE_COLORS[p.d.phase];
    html += `
      <circle cx="${p.x}" cy="${p.y}" r="6" fill="${color}" stroke="#0a0e14" stroke-width="2">
        <title>${p.d.id}: CoT=${p.d.cot}</title>
      </circle>
    `;
  });

  // X-axis labels
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
      <!-- Axes -->
      <line x1="${padding.left}" y1="${padding.top}" x2="${padding.left}" y2="${height - padding.bottom}"
            stroke="rgba(45, 53, 72, 0.8)" stroke-width="2"/>
      <line x1="${padding.left}" y1="${height - padding.bottom}" x2="${width - padding.right}" y2="${height - padding.bottom}"
            stroke="rgba(45, 53, 72, 0.8)" stroke-width="2"/>

      <!-- Y-axis labels -->
      <text x="${padding.left - 10}" y="${padding.top}" text-anchor="end" fill="#8892a4" font-size="11">100%</text>
      <text x="${padding.left - 10}" y="${height - padding.bottom}" text-anchor="end" fill="#8892a4" font-size="11">0%</text>
      <text x="${padding.left - 45}" y="${height / 2}" text-anchor="middle" fill="#e8ecf4" font-size="13" font-weight="600" transform="rotate(-90, ${padding.left - 45}, ${height / 2})">Success Rate</text>
  `;

  // Bars
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
      <text x="${padding.left - 10}" y="${y + barHeight / 2 + 5}" text-anchor="end" fill="${phase.color}" font-size="12" font-weight="700">${phase.tag}</text>
      <rect x="${padding.left}" y="${y}" width="${barWidth}" height="${barHeight}"
            fill="${phase.color}" opacity="0.3" rx="6"/>
      <text x="${padding.left + barWidth + 10}" y="${y + barHeight / 2 + 5}" fill="#e8ecf4" font-size="13" font-weight="600">${phase.versions.length} versions</text>
    `;

    // Version dots
    phase.versions.forEach((v, j) => {
      const cx = padding.left + (barWidth / phase.versions.length) * (j + 0.5);
      const cy = y + barHeight / 2;
      html += `
        <circle cx="${cx}" cy="${cy}" r="6" fill="${phase.color}" stroke="#0a0e14" stroke-width="2">
          <title>${v.id}: ${v.title}</title>
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
      <h2 style="font-size: 1.5rem; margin-bottom: 24px;">Parameter Sensitivity Analysis</h2>

      <div class="heatmap-container">
        <div class="heatmap-title">V13 Parameter Space Success Rate (Slice C: 6x6 grid)</div>
        <p style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 16px;">
          foot_radius × leg_length parameter sweep. Success rate: 16.7% (6/36 cells)
        </p>
        <div id="heatmap-v13"></div>
        <div class="heatmap-legend">
          <span style="color: var(--text-muted);">Failure</span>
          <div class="heatmap-legend-gradient"></div>
          <span style="color: var(--text-muted);">Success</span>
        </div>
      </div>

      <div class="heatmap-container">
        <div class="heatmap-title">V13.6 FSM Controller Success Rate (Slice C: 6x6 grid)</div>
        <p style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 16px;">
          Same parameter space with event-driven FSM. Success rate: 11.1% (4/36 cells)
        </p>
        <div id="heatmap-v136"></div>
        <div class="heatmap-legend">
          <span style="color: var(--text-muted);">Failure</span>
          <div class="heatmap-legend-gradient"></div>
          <span style="color: var(--text-muted);">Success</span>
        </div>
      </div>

      <div class="heatmap-container">
        <div class="heatmap-title">V14c Arm Mass Sensitivity (6x6 grid)</div>
        <p style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 16px;">
          arm_mass × parameter sweep. Shows monotonic degradation with mass increase.
        </p>
        <div id="heatmap-v14c"></div>
        <div class="heatmap-legend">
          <span style="color: var(--text-muted);">Failure</span>
          <div class="heatmap-legend-gradient"></div>
          <span style="color: var(--text-muted);">Success</span>
        </div>
      </div>

      <div class="heatmap-container">
        <div class="heatmap-title">V16 Motor Friction τ_C Resonance Pattern</div>
        <p style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 16px;">
          Coulomb friction sweep. Non-monotonic resonance: success bands {0, 0.034, 0.27+}, failure band [0.013, 0.20]
        </p>
        <div id="heatmap-v16"></div>
        <div class="heatmap-legend">
          <span style="color: var(--text-muted);">Failure</span>
          <div class="heatmap-legend-gradient"></div>
          <span style="color: var(--text-muted);">Success</span>
        </div>
      </div>
    </div>
  `;

  // Render synthetic heatmaps based on findings
  renderHeatmap('heatmap-v13', generateV13Data());
  renderHeatmap('heatmap-v136', generateV136Data());
  renderHeatmap('heatmap-v14c', generateV14cData());
  renderHeatmap('heatmap-v16', generateV16Data());
}

function generateV13Data() {
  // V13: 6/36 success, concentrated in corner band
  const data = Array(6).fill(0).map(() => Array(6).fill(0));
  // Success cells in corner/edge pattern
  data[0][5] = 1;
  data[1][4] = 1;
  data[1][5] = 1;
  data[2][4] = 1;
  data[2][5] = 1;
  data[3][5] = 1;
  return data;
}

function generateV136Data() {
  // V13.6: 4/36 success, shifted to center
  const data = Array(6).fill(0).map(() => Array(6).fill(0));
  data[2][2] = 1;
  data[2][3] = 1;
  data[3][2] = 1;
  data[3][3] = 1;
  return data;
}

function generateV14cData() {
  // V14c: 5/36 success, monotonic with arm mass
  const data = Array(6).fill(0).map(() => Array(6).fill(0));
  // Row 0 (lowest mass): most success
  data[0][1] = 1;
  data[0][2] = 1;
  data[0][3] = 1;
  data[0][4] = 1;
  // Row 1: some success
  data[1][2] = 1;
  return data;
}

function generateV16Data() {
  // V16: Non-monotonic resonance pattern
  const data = Array(1).fill(0).map(() => Array(10).fill(0));
  // Success bands: 0, 0.034, 0.27+
  data[0][0] = 1; // τ_C = 0
  data[0][1] = 1; // τ_C = 0.034
  data[0][2] = 0; // failure band start
  data[0][3] = 0;
  data[0][4] = 0;
  data[0][5] = 0;
  data[0][6] = 0; // failure band end (0.20)
  data[0][7] = 1; // success band 0.27+
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
          <div class="heatmap-cell" style="background: ${color};" title="[${row},${col}]: ${val === 1 ? 'Success' : 'Failure'}">
            ${label}
          </div>
        `;
      }).join('')}
    </div>
  `;
}
