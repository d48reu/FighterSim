'use strict';

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

const state = {
  currentView: 'dashboard',
  currentWeightClass: 'Middleweight',
};

// ---------------------------------------------------------------------------
// API helper
// ---------------------------------------------------------------------------

async function api(path, options = {}) {
  const res = await fetch(path, options);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Task polling
// ---------------------------------------------------------------------------

function pollTask(taskId, onDone, onError) {
  const iv = setInterval(async () => {
    try {
      const task = await api(`/api/tasks/${taskId}`);
      if (task.status === 'done') {
        clearInterval(iv);
        onDone(task.result);
      } else if (task.status === 'error') {
        clearInterval(iv);
        onError(task.error || 'Unknown error');
      }
    } catch (err) {
      clearInterval(iv);
      onError(err.message);
    }
  }, 500);
}

// ---------------------------------------------------------------------------
// Navigation
// ---------------------------------------------------------------------------

function navigate(view) {
  state.currentView = view;
  document.querySelectorAll('.nav-item').forEach(el => {
    el.classList.toggle('active', el.dataset.view === view);
  });
  document.querySelectorAll('.view').forEach(el => {
    el.classList.toggle('hidden', el.id !== `view-${view}`);
  });
  loadView(view);
}

function loadView(view) {
  if (view === 'dashboard') loadDashboard();
  if (view === 'fighters')  loadFighters();
  if (view === 'rankings')  loadRankings(state.currentWeightClass);
  if (view === 'hof')       loadHallOfFame();
}

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------

async function loadDashboard() {
  try {
    const org = await api('/api/organization');
    document.getElementById('org-name').textContent    = org.name;
    document.getElementById('org-prestige').textContent = org.prestige;
    document.getElementById('org-balance').textContent  = formatCurrency(org.bank_balance);
    document.getElementById('org-roster').textContent   = org.roster_count;
  } catch (err) {
    setStatus('Could not load org data: ' + err.message, true);
  }
}

// ---------------------------------------------------------------------------
// Fighters
// ---------------------------------------------------------------------------

async function loadFighters(weightClass = null) {
  const tbody = document.getElementById('fighters-tbody');
  tbody.innerHTML = '<tr><td colspan="13" class="muted">Loading...</td></tr>';
  try {
    const params = new URLSearchParams();
    if (weightClass) params.set('weight_class', weightClass);
    const fighters = await api(`/api/fighters?${params}`);
    if (fighters.length === 0) {
      tbody.innerHTML = '<tr><td colspan="13" class="muted">No fighters found.</td></tr>';
      return;
    }
    tbody.innerHTML = fighters.map(f => `
      <tr data-fighter-id="${f.id}">
        <td>${esc(f.name)}</td>
        <td>${f.age}</td>
        <td><span class="badge">${esc(f.weight_class)}</span></td>
        <td><span class="badge">${esc(f.archetype || '—')}</span></td>
        <td>${f.striking}</td>
        <td>${f.grappling}</td>
        <td>${f.wrestling}</td>
        <td>${f.cardio}</td>
        <td>${f.chin}</td>
        <td>${f.speed}</td>
        <td><strong>${f.overall}</strong></td>
        <td>${esc(f.record)}</td>
        <td>${f.goat_score > 0 ? f.goat_score.toFixed(1) : '—'}</td>
      </tr>
    `).join('');

    // Wire row clicks to open side panel
    tbody.querySelectorAll('tr[data-fighter-id]').forEach(row => {
      row.addEventListener('click', () => showFighterPanel(Number(row.dataset.fighterId)));
    });
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="13" class="muted">Error: ${esc(err.message)}</td></tr>`;
  }
}

// ---------------------------------------------------------------------------
// Fighter side panel
// ---------------------------------------------------------------------------

async function showFighterPanel(fighterId) {
  const panel = document.getElementById('fighter-panel');
  panel.classList.remove('hidden');

  // Reset content while loading
  document.getElementById('panel-name').textContent    = 'Loading…';
  document.getElementById('panel-subtitle').textContent = '';
  document.getElementById('panel-archetype').textContent = '';
  document.getElementById('panel-record').textContent  = '—';
  document.getElementById('panel-overall').textContent = '—';
  document.getElementById('panel-goat').textContent    = '—';
  document.getElementById('panel-tags').innerHTML      = '';
  document.getElementById('panel-bio').textContent     = 'Loading…';
  document.getElementById('bar-popularity').style.width = '0%';
  document.getElementById('bar-hype').style.width       = '0%';
  document.getElementById('val-popularity').textContent = '';
  document.getElementById('val-hype').textContent       = '';

  try {
    const [fighter, bioData, tagsData] = await Promise.all([
      api(`/api/fighters/${fighterId}`),
      api(`/api/fighters/${fighterId}/bio`),
      api(`/api/fighters/${fighterId}/tags`),
    ]);

    document.getElementById('panel-name').textContent     = fighter.name;
    document.getElementById('panel-subtitle').textContent = `${fighter.weight_class} · ${fighter.style} · Age ${fighter.age}`;
    document.getElementById('panel-archetype').textContent = fighter.archetype || '';
    document.getElementById('panel-record').textContent   = fighter.record;
    document.getElementById('panel-overall').textContent  = fighter.overall;
    document.getElementById('panel-goat').textContent     = fighter.goat_score > 0 ? fighter.goat_score.toFixed(1) : '—';

    const popPct = Math.min(100, fighter.popularity);
    const hypePct = Math.min(100, fighter.hype);
    document.getElementById('bar-popularity').style.width = `${popPct}%`;
    document.getElementById('bar-hype').style.width       = `${hypePct}%`;
    document.getElementById('val-popularity').textContent = fighter.popularity.toFixed(1);
    document.getElementById('val-hype').textContent       = fighter.hype.toFixed(1);

    const tagsEl = document.getElementById('panel-tags');
    const tags = tagsData.tags || [];
    tagsEl.innerHTML = tags.length
      ? tags.map(t => `<span class="tag-chip">${esc(t.replace(/_/g, ' '))}</span>`).join('')
      : '<span class="muted" style="font-size:12px">No narrative tags yet</span>';

    document.getElementById('panel-bio').textContent = bioData.bio || '—';

  } catch (err) {
    document.getElementById('panel-name').textContent = 'Error';
    document.getElementById('panel-bio').textContent  = err.message;
  }
}

function closeFighterPanel() {
  document.getElementById('fighter-panel').classList.add('hidden');
}

// ---------------------------------------------------------------------------
// Rankings
// ---------------------------------------------------------------------------

async function loadRankings(weightClass) {
  state.currentWeightClass = weightClass;
  document.querySelectorAll('.wc-tab').forEach(el => {
    el.classList.toggle('active', el.dataset.wc === weightClass);
  });

  const tbody = document.getElementById('rankings-tbody');
  tbody.innerHTML = '<tr><td colspan="5" class="muted">Loading...</td></tr>';
  try {
    const rankings = await api(`/api/rankings/${encodeURIComponent(weightClass)}`);
    if (rankings.length === 0) {
      tbody.innerHTML = '<tr><td colspan="5" class="muted">No rankings available.</td></tr>';
      return;
    }
    tbody.innerHTML = rankings.map(r => `
      <tr>
        <td><strong>#${r.rank}</strong></td>
        <td>${esc(r.name)}</td>
        <td>${esc(r.record)}</td>
        <td>${r.overall}</td>
        <td>${r.score.toFixed(1)}</td>
      </tr>
    `).join('');
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="5" class="muted">Error: ${esc(err.message)}</td></tr>`;
  }
}

// ---------------------------------------------------------------------------
// Hall of Fame
// ---------------------------------------------------------------------------

async function loadHallOfFame() {
  await Promise.all([loadGoat(), loadRivalries()]);
}

async function loadGoat() {
  const tbody = document.getElementById('goat-tbody');
  tbody.innerHTML = '<tr><td colspan="7" class="muted">Loading...</td></tr>';
  try {
    const goat = await api('/api/goat?top=10');
    if (goat.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" class="muted">No data yet — simulate some events first.</td></tr>';
      return;
    }
    tbody.innerHTML = goat.map(g => `
      <tr>
        <td><strong>#${g.rank}</strong></td>
        <td>${esc(g.name)}</td>
        <td><span class="badge">${esc(g.weight_class)}</span></td>
        <td><span class="badge">${esc(g.archetype || '—')}</span></td>
        <td>${esc(g.record)}</td>
        <td>${g.overall}</td>
        <td><strong>${g.goat_score}</strong></td>
      </tr>
    `).join('');
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" class="muted">Error: ${esc(err.message)}</td></tr>`;
  }
}

async function loadRivalries() {
  const container = document.getElementById('rivalries-list');
  container.innerHTML = '<p class="muted">Loading...</p>';
  try {
    const rivalries = await api('/api/rivalries');
    if (rivalries.length === 0) {
      container.innerHTML = '<p class="muted">No active rivalries yet — rivalries form after repeated encounters.</p>';
      return;
    }
    container.innerHTML = rivalries.map(r => `
      <div class="rivalry-card">
        <span class="rivalry-names">${esc(r.fighter_a.name)}</span>
        <span class="rivalry-vs">VS</span>
        <span class="rivalry-names">${esc(r.fighter_b.name)}</span>
        <span class="rivalry-wc">${esc(r.weight_class)}</span>
      </div>
    `).join('');
  } catch (err) {
    container.innerHTML = `<p class="muted">Error: ${esc(err.message)}</p>`;
  }
}

// ---------------------------------------------------------------------------
// Advance Month
// ---------------------------------------------------------------------------

async function advanceMonth() {
  const btn = document.getElementById('btn-advance-month');
  btn.disabled = true;
  btn.textContent = 'Simulating…';
  setStatus('Advancing simulation by one month…');

  try {
    const { task_id } = await api('/api/sim/month', { method: 'POST' });
    pollTask(
      task_id,
      result => {
        btn.disabled = false;
        btn.textContent = 'Advance Month';
        setStatus(
          `Month advanced — ${result.fighters_aged} fighters aged, ` +
          `${result.events_simulated} AI events simulated.`
        );
        if (state.currentView === 'dashboard') loadDashboard();
        if (state.currentView === 'hof') loadHallOfFame();
      },
      error => {
        btn.disabled = false;
        btn.textContent = 'Advance Month';
        setStatus('Error: ' + error, true);
      }
    );
  } catch (err) {
    btn.disabled = false;
    btn.textContent = 'Advance Month';
    setStatus('Error: ' + err.message, true);
  }
}

// ---------------------------------------------------------------------------
// Simulate Event
// ---------------------------------------------------------------------------

async function simulateEvent() {
  const btn = document.getElementById('btn-simulate-event');
  btn.disabled = true;
  btn.textContent = 'Simulating…';
  setStatus('Simulating fight card…');

  try {
    const { task_id } = await api('/api/events/simulate', { method: 'POST' });
    pollTask(
      task_id,
      result => {
        btn.disabled = false;
        btn.textContent = 'Simulate Event';
        setStatus(`${result.event_name} — ${result.fights_simulated} fights.`);
        renderEventResults(result.fights);
        if (state.currentView !== 'dashboard') navigate('dashboard');
      },
      error => {
        btn.disabled = false;
        btn.textContent = 'Simulate Event';
        setStatus('Error: ' + error, true);
      }
    );
  } catch (err) {
    btn.disabled = false;
    btn.textContent = 'Simulate Event';
    setStatus('Error: ' + err.message, true);
  }
}

function renderEventResults(fights) {
  const container = document.getElementById('event-results');
  if (!fights || fights.length === 0) {
    container.innerHTML = '<p class="muted">No fights to display.</p>';
    return;
  }
  container.innerHTML = fights.map(f => `
    <div class="fight-card">
      <div class="fight-matchup">${esc(f.fighter_a)} vs ${esc(f.fighter_b)}</div>
      <div class="fight-result">
        <span class="winner">${esc(f.winner)}</span>
        <span class="method">${esc(f.method)}</span>
        <span class="fight-time">R${f.round} ${esc(f.time)}</span>
      </div>
      <div class="fight-narrative">${esc(f.narrative)}</div>
    </div>
  `).join('');
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatCurrency(n) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency', currency: 'USD', maximumFractionDigits: 0,
  }).format(n);
}

function setStatus(msg, isError = false) {
  const el = document.getElementById('status-bar');
  el.textContent = msg;
  el.className = isError ? 'status-bar error' : 'status-bar';
}

function esc(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.nav-item').forEach(el => {
    el.addEventListener('click', () => navigate(el.dataset.view));
  });

  document.getElementById('fighters-wc-filter').addEventListener('change', e => {
    loadFighters(e.target.value || null);
  });

  document.querySelectorAll('.wc-tab').forEach(el => {
    el.addEventListener('click', () => loadRankings(el.dataset.wc));
  });

  document.getElementById('btn-advance-month').addEventListener('click', advanceMonth);
  document.getElementById('btn-simulate-event').addEventListener('click', simulateEvent);
  document.getElementById('btn-close-panel').addEventListener('click', closeFighterPanel);

  navigate('dashboard');
});
