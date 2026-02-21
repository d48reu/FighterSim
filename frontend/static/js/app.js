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
  tbody.innerHTML = '<tr><td colspan="12" class="muted">Loading...</td></tr>';
  try {
    const params = new URLSearchParams();
    if (weightClass) params.set('weight_class', weightClass);
    const fighters = await api(`/api/fighters?${params}`);
    if (fighters.length === 0) {
      tbody.innerHTML = '<tr><td colspan="12" class="muted">No fighters found.</td></tr>';
      return;
    }
    tbody.innerHTML = fighters.map(f => `
      <tr>
        <td>${esc(f.name)}</td>
        <td>${f.age}</td>
        <td><span class="badge">${esc(f.weight_class)}</span></td>
        <td>${esc(f.style)}</td>
        <td>${f.striking}</td>
        <td>${f.grappling}</td>
        <td>${f.wrestling}</td>
        <td>${f.cardio}</td>
        <td>${f.chin}</td>
        <td>${f.speed}</td>
        <td><strong>${f.overall}</strong></td>
        <td>${esc(f.record)}</td>
      </tr>
    `).join('');
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="12" class="muted">Error: ${esc(err.message)}</td></tr>`;
  }
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

  navigate('dashboard');
});
