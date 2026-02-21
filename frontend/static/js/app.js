'use strict';

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

const state = {
  currentView: 'dashboard',
  currentWeightClass: 'Middleweight',
  panelContext: null,  // 'fighters' | 'free-agents' | 'roster'
  notifications: [],
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
  if (view === 'dashboard')   loadDashboard();
  if (view === 'fighters')    loadFighters();
  if (view === 'roster')      loadRoster();
  if (view === 'free-agents') loadFreeAgents();
  if (view === 'rankings')    loadRankings(state.currentWeightClass);
  if (view === 'hof')         loadHallOfFame();
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
  loadFinances();
  loadExpiringContracts();
}

async function loadFinances() {
  try {
    const fin = await api('/api/finances');
    document.getElementById('dash-payroll').textContent    = formatCurrency(fin.monthly_payroll);
    document.getElementById('dash-balance').textContent    = formatCurrency(fin.bank_balance);
    document.getElementById('dash-roster-size').textContent = fin.roster_size;
    document.getElementById('dash-fight-costs').textContent = formatCurrency(fin.projected_fight_costs);
  } catch (err) {
    // silently fail — cards stay at "—"
  }
}

async function loadExpiringContracts() {
  try {
    const expiring = await api('/api/contracts/expiring');
    const widget = document.getElementById('expiring-widget');
    const tbody = document.getElementById('expiring-tbody');
    if (expiring.length === 0) {
      widget.classList.add('hidden');
      return;
    }
    widget.classList.remove('hidden');
    tbody.innerHTML = expiring.map(f => `
      <tr>
        <td>${esc(f.name)}</td>
        <td>${f.expiry_date || '—'}</td>
        <td>${f.fights_remaining}</td>
      </tr>
    `).join('');
  } catch (err) {
    // silently fail
  }
}

// ---------------------------------------------------------------------------
// Fighters
// ---------------------------------------------------------------------------

async function loadFighters(weightClass = null) {
  state.panelContext = 'fighters';
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
        <td>${(f.traits || []).map(t => {
          const label = t.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
          return `<span class="trait-badge" style="font-size:10px;padding:2px 6px">${esc(label)}</span>`;
        }).join(' ') || '<span class="badge">' + esc(f.archetype || '\u2014') + '</span>'}</td>
        <td>${f.striking}</td>
        <td>${f.grappling}</td>
        <td>${f.wrestling}</td>
        <td>${f.cardio}</td>
        <td>${f.chin}</td>
        <td>${f.speed}</td>
        <td><strong>${f.overall}</strong></td>
        <td>${esc(f.record)}</td>
        <td>${f.goat_score > 0 ? f.goat_score.toFixed(1) : '\u2014'}</td>
      </tr>
    `).join('');

    tbody.querySelectorAll('tr[data-fighter-id]').forEach(row => {
      row.addEventListener('click', () => {
        state.panelContext = 'fighters';
        showFighterPanel(Number(row.dataset.fighterId));
      });
    });
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="13" class="muted">Error: ${esc(err.message)}</td></tr>`;
  }
}

// ---------------------------------------------------------------------------
// Fighter side panel
// ---------------------------------------------------------------------------

async function showFighterPanel(fighterId, extraData) {
  const panel = document.getElementById('fighter-panel');
  panel.classList.remove('hidden');

  // Reset content
  document.getElementById('panel-name').textContent    = 'Loading\u2026';
  document.getElementById('panel-subtitle').textContent = '';
  document.getElementById('panel-archetype').textContent = '';
  document.getElementById('panel-record').textContent  = '\u2014';
  document.getElementById('panel-overall').textContent = '\u2014';
  document.getElementById('panel-goat').textContent    = '\u2014';
  document.getElementById('panel-tags').innerHTML      = '';
  document.getElementById('panel-bio').textContent     = 'Loading\u2026';
  document.getElementById('panel-stat-bars').innerHTML = '';
  document.getElementById('panel-actions').innerHTML   = '';
  document.getElementById('panel-actions').classList.add('hidden');
  document.getElementById('panel-offer-result').innerHTML = '';
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
    document.getElementById('panel-subtitle').textContent = `${fighter.weight_class} \xB7 ${fighter.style} \xB7 Age ${fighter.age}`;
    document.getElementById('panel-archetype').textContent = fighter.archetype || '';
    document.getElementById('panel-record').textContent   = fighter.record;
    document.getElementById('panel-overall').textContent  = fighter.overall;
    document.getElementById('panel-goat').textContent     = fighter.goat_score > 0 ? fighter.goat_score.toFixed(1) : '\u2014';

    const popPct = Math.min(100, fighter.popularity);
    const hypePct = Math.min(100, fighter.hype);
    document.getElementById('bar-popularity').style.width = `${popPct}%`;
    document.getElementById('bar-hype').style.width       = `${hypePct}%`;
    document.getElementById('val-popularity').textContent = fighter.popularity.toFixed(1);
    document.getElementById('val-hype').textContent       = fighter.hype.toFixed(1);

    // Attribute stat bars
    const bars = [
      { label: 'STR', value: fighter.striking },
      { label: 'GRP', value: fighter.grappling },
      { label: 'WR',  value: fighter.wrestling },
      { label: 'CRD', value: fighter.cardio },
      { label: 'CHN', value: fighter.chin },
      { label: 'SPD', value: fighter.speed },
    ];
    document.getElementById('panel-stat-bars').innerHTML = bars.map(b => `
      <div class="stat-bar-row">
        <span class="stat-bar-label">${b.label}</span>
        <div class="stat-bar-track">
          <div class="stat-bar-fill" style="width:${b.value}%"></div>
        </div>
        <span class="stat-bar-value">${b.value}</span>
      </div>
    `).join('');

    // Traits
    const traitsEl = document.getElementById('panel-traits');
    const traits = fighter.traits || [];
    traitsEl.innerHTML = traits.length
      ? traits.map(t => {
          const label = t.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
          return `<span class="trait-badge">${esc(label)}</span>`;
        }).join('')
      : '';

    // Tags
    const tagsEl = document.getElementById('panel-tags');
    const tags = tagsData.tags || [];
    tagsEl.innerHTML = tags.length
      ? tags.map(t => `<span class="tag-chip">${esc(t.replace(/_/g, ' '))}</span>`).join('')
      : '<span class="muted" style="font-size:12px">No narrative tags yet</span>';

    document.getElementById('panel-bio').textContent = bioData.bio || '\u2014';

    // Context-specific actions
    const actionsEl = document.getElementById('panel-actions');
    if (state.panelContext === 'free-agents' && extraData) {
      actionsEl.classList.remove('hidden');
      actionsEl.innerHTML = `
        <div class="panel-form">
          <label>Salary Offer
            <input type="number" id="offer-salary" value="${extraData.asking_salary}" min="1000" step="500">
          </label>
          <label>Fight Count
            <select id="offer-fights">
              ${[2,3,4,5,6].map(n => `<option value="${n}" ${n === extraData.asking_fights ? 'selected' : ''}>${n} fights</option>`).join('')}
            </select>
          </label>
          <label>Contract Length
            <select id="offer-length">
              <option value="12" ${extraData.asking_length_months === 12 ? 'selected' : ''}>12 months</option>
              <option value="18" ${extraData.asking_length_months === 18 ? 'selected' : ''}>18 months</option>
              <option value="24" ${extraData.asking_length_months === 24 ? 'selected' : ''}>24 months</option>
            </select>
          </label>
          <button class="btn-success" id="btn-make-offer">Make Offer</button>
        </div>
      `;
      document.getElementById('btn-make-offer').addEventListener('click', () => makeOffer(fighterId));
    } else if (state.panelContext === 'roster' && extraData) {
      actionsEl.classList.remove('hidden');
      actionsEl.innerHTML = `
        <div class="panel-stat-row">
          <span class="panel-stat-label">Salary</span>
          <span class="panel-stat-value">${formatCurrency(extraData.salary)}</span>
        </div>
        <div class="panel-stat-row">
          <span class="panel-stat-label">Fights Left</span>
          <span class="panel-stat-value">${extraData.fights_remaining} / ${extraData.fight_count_total}</span>
        </div>
        <div class="panel-stat-row">
          <span class="panel-stat-label">Expires</span>
          <span class="panel-stat-value">${extraData.expiry_date || '\u2014'}</span>
        </div>
        <div class="panel-actions-row" style="margin-top:10px">
          <button class="btn-danger" id="btn-release">Release Fighter</button>
          <button class="btn-success" id="btn-show-renew">Renew Contract</button>
        </div>
        <div id="renew-form-area"></div>
      `;
      document.getElementById('btn-release').addEventListener('click', () => releaseFighter(fighterId));
      document.getElementById('btn-show-renew').addEventListener('click', () => {
        const area = document.getElementById('renew-form-area');
        if (area.innerHTML) { area.innerHTML = ''; return; }
        area.innerHTML = `
          <div class="panel-form">
            <label>New Salary
              <input type="number" id="renew-salary" value="${extraData.salary}" min="1000" step="500">
            </label>
            <label>Fight Count
              <select id="renew-fights">
                ${[2,3,4,5,6].map(n => `<option value="${n}" ${n === 4 ? 'selected' : ''}>${n} fights</option>`).join('')}
              </select>
            </label>
            <label>Contract Length
              <select id="renew-length">
                <option value="12">12 months</option>
                <option value="18" selected>18 months</option>
                <option value="24">24 months</option>
              </select>
            </label>
            <button class="btn-success" id="btn-renew-submit">Submit Renewal</button>
          </div>
        `;
        document.getElementById('btn-renew-submit').addEventListener('click', () => renewContract(fighterId));
      });
    } else {
      actionsEl.classList.add('hidden');
    }

  } catch (err) {
    document.getElementById('panel-name').textContent = 'Error';
    document.getElementById('panel-bio').textContent  = err.message;
  }
}

function closeFighterPanel() {
  document.getElementById('fighter-panel').classList.add('hidden');
}

// ---------------------------------------------------------------------------
// Free Agents
// ---------------------------------------------------------------------------

async function loadFreeAgents() {
  state.panelContext = 'free-agents';
  const tbody = document.getElementById('free-agents-tbody');
  tbody.innerHTML = '<tr><td colspan="9" class="muted">Loading...</td></tr>';

  const params = new URLSearchParams();
  const wc = document.getElementById('fa-wc-filter').value;
  const style = document.getElementById('fa-style-filter').value;
  const minOvr = document.getElementById('fa-ovr-filter').value;
  const sortBy = document.getElementById('fa-sort').value;

  if (wc) params.set('weight_class', wc);
  if (style) params.set('style', style);
  if (minOvr && parseInt(minOvr) > 0) params.set('min_overall', minOvr);
  if (sortBy) params.set('sort_by', sortBy);

  try {
    const agents = await api(`/api/free-agents?${params}`);
    if (agents.length === 0) {
      tbody.innerHTML = '<tr><td colspan="9" class="muted">No free agents found.</td></tr>';
      return;
    }
    tbody.innerHTML = agents.map(f => `
      <tr data-fighter-id="${f.id}"
          data-asking-salary="${f.asking_salary}"
          data-asking-fights="${f.asking_fights}"
          data-asking-length="${f.asking_length_months}">
        <td>${esc(f.name)}</td>
        <td>${f.age}</td>
        <td><span class="badge">${esc(f.weight_class)}</span></td>
        <td>${esc(f.style)}</td>
        <td><strong>${f.overall}</strong></td>
        <td>${esc(f.record)}</td>
        <td>${f.hype.toFixed(1)}</td>
        <td>${formatCurrency(f.asking_salary)}</td>
        <td>${f.asking_fights}</td>
      </tr>
    `).join('');

    tbody.querySelectorAll('tr[data-fighter-id]').forEach(row => {
      row.addEventListener('click', () => {
        state.panelContext = 'free-agents';
        showFighterPanel(Number(row.dataset.fighterId), {
          asking_salary: Number(row.dataset.askingSalary),
          asking_fights: Number(row.dataset.askingFights),
          asking_length_months: Number(row.dataset.askingLength),
        });
      });
    });
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="9" class="muted">Error: ${esc(err.message)}</td></tr>`;
  }
}

async function makeOffer(fighterId) {
  const salary = Number(document.getElementById('offer-salary').value);
  const fightCount = Number(document.getElementById('offer-fights').value);
  const lengthMonths = Number(document.getElementById('offer-length').value);
  const resultEl = document.getElementById('panel-offer-result');

  try {
    const result = await api('/api/contracts/offer', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ fighter_id: fighterId, salary, fight_count: fightCount, length_months: lengthMonths }),
    });
    resultEl.innerHTML = `<div class="offer-result ${result.accepted ? 'success' : 'rejected'}">${esc(result.message)}</div>`;
    if (result.accepted) {
      // Remove row from free agents table
      const row = document.querySelector(`#free-agents-tbody tr[data-fighter-id="${fighterId}"]`);
      if (row) row.remove();
      setStatus(result.message);
    }
  } catch (err) {
    resultEl.innerHTML = `<div class="offer-result rejected">Error: ${esc(err.message)}</div>`;
  }
}

// ---------------------------------------------------------------------------
// Roster
// ---------------------------------------------------------------------------

async function loadRoster() {
  state.panelContext = 'roster';
  const tbody = document.getElementById('roster-tbody');
  tbody.innerHTML = '<tr><td colspan="9" class="muted">Loading...</td></tr>';

  try {
    const [roster, fin] = await Promise.all([
      api('/api/roster'),
      api('/api/finances'),
    ]);

    // Payroll bar
    document.getElementById('roster-count').textContent   = fin.roster_size;
    document.getElementById('roster-payroll').textContent  = formatCurrency(fin.monthly_payroll);
    document.getElementById('roster-balance').textContent  = formatCurrency(fin.bank_balance);

    const pctUsed = fin.bank_balance > 0
      ? Math.min(100, (fin.total_annual_salaries / fin.bank_balance) * 100)
      : 100;
    const fill = document.getElementById('roster-progress-fill');
    fill.style.width = `${pctUsed}%`;
    fill.className = 'payroll-progress-fill' + (pctUsed > 80 ? ' danger' : pctUsed > 50 ? ' warning' : '');

    if (roster.length === 0) {
      tbody.innerHTML = '<tr><td colspan="9" class="muted">No fighters on roster. Sign some free agents!</td></tr>';
      return;
    }

    tbody.innerHTML = roster.map(f => `
      <tr data-fighter-id="${f.id}"
          data-salary="${f.salary}"
          data-fights-remaining="${f.fights_remaining}"
          data-fight-count-total="${f.fight_count_total}"
          data-expiry-date="${f.expiry_date || ''}">
        <td>${esc(f.name)}</td>
        <td>${f.age}</td>
        <td><span class="badge">${esc(f.weight_class)}</span></td>
        <td>${esc(f.style)}</td>
        <td><strong>${f.overall}</strong></td>
        <td>${esc(f.record)}</td>
        <td>${f.fights_remaining} / ${f.fight_count_total}</td>
        <td>${formatCurrency(f.salary)}</td>
        <td>${f.expiry_date || '\u2014'}</td>
      </tr>
    `).join('');

    tbody.querySelectorAll('tr[data-fighter-id]').forEach(row => {
      row.addEventListener('click', () => {
        state.panelContext = 'roster';
        showFighterPanel(Number(row.dataset.fighterId), {
          salary: Number(row.dataset.salary),
          fights_remaining: Number(row.dataset.fightsRemaining),
          fight_count_total: Number(row.dataset.fightCountTotal),
          expiry_date: row.dataset.expiryDate,
        });
      });
    });
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="9" class="muted">Error: ${esc(err.message)}</td></tr>`;
  }
}

async function releaseFighter(fighterId) {
  if (!confirm('Are you sure you want to release this fighter?')) return;
  try {
    const result = await api('/api/contracts/release', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ fighter_id: fighterId }),
    });
    if (result.success) {
      setStatus(result.message);
      closeFighterPanel();
      loadRoster();
    } else {
      setStatus(result.message, true);
    }
  } catch (err) {
    setStatus('Error: ' + err.message, true);
  }
}

async function renewContract(fighterId) {
  const salary = Number(document.getElementById('renew-salary').value);
  const fightCount = Number(document.getElementById('renew-fights').value);
  const lengthMonths = Number(document.getElementById('renew-length').value);
  const resultEl = document.getElementById('panel-offer-result');

  try {
    const result = await api('/api/contracts/renew', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ fighter_id: fighterId, salary, fight_count: fightCount, length_months: lengthMonths }),
    });
    resultEl.innerHTML = `<div class="offer-result ${result.accepted ? 'success' : 'rejected'}">${esc(result.message)}</div>`;
    if (result.accepted) {
      setStatus(result.message);
      loadRoster();
    }
  } catch (err) {
    resultEl.innerHTML = `<div class="offer-result rejected">Error: ${esc(err.message)}</div>`;
  }
}

// ---------------------------------------------------------------------------
// Notifications
// ---------------------------------------------------------------------------

async function loadNotifications() {
  try {
    const notifs = await api('/api/notifications');
    state.notifications = notifs;
    const badge = document.getElementById('notif-badge');
    if (notifs.length > 0) {
      badge.textContent = notifs.length;
      badge.classList.remove('hidden');
    } else {
      badge.classList.add('hidden');
    }
  } catch (err) {
    // silently fail
  }
}

function toggleNotifDropdown() {
  const dropdown = document.getElementById('notif-dropdown');
  const isHidden = dropdown.classList.contains('hidden');
  if (isHidden) {
    if (state.notifications.length === 0) {
      dropdown.innerHTML = '<div class="notif-empty">No new notifications</div>';
    } else {
      dropdown.innerHTML = state.notifications.map(n => `
        <div class="notif-item" data-notif-id="${n.id}">
          <span>${esc(n.message)}</span>
          <span class="notif-item-date">${n.created_date}</span>
        </div>
      `).join('');
      dropdown.querySelectorAll('.notif-item').forEach(el => {
        el.addEventListener('click', () => markNotifRead(Number(el.dataset.notifId), el));
      });
    }
    dropdown.classList.remove('hidden');
  } else {
    dropdown.classList.add('hidden');
  }
}

async function markNotifRead(id, el) {
  try {
    await api(`/api/notifications/${id}/read`, { method: 'POST' });
    if (el) el.remove();
    state.notifications = state.notifications.filter(n => n.id !== id);
    const badge = document.getElementById('notif-badge');
    if (state.notifications.length > 0) {
      badge.textContent = state.notifications.length;
    } else {
      badge.classList.add('hidden');
      document.getElementById('notif-dropdown').innerHTML = '<div class="notif-empty">No new notifications</div>';
    }
  } catch (err) {
    // silently fail
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
      tbody.innerHTML = '<tr><td colspan="7" class="muted">No data yet \u2014 simulate some events first.</td></tr>';
      return;
    }
    tbody.innerHTML = goat.map(g => `
      <tr>
        <td><strong>#${g.rank}</strong></td>
        <td>${esc(g.name)}</td>
        <td><span class="badge">${esc(g.weight_class)}</span></td>
        <td><span class="badge">${esc(g.archetype || '\u2014')}</span></td>
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
      container.innerHTML = '<p class="muted">No active rivalries yet \u2014 rivalries form after repeated encounters.</p>';
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
  btn.textContent = 'Simulating\u2026';
  setStatus('Advancing simulation by one month\u2026');

  try {
    const { task_id } = await api('/api/sim/month', { method: 'POST' });
    pollTask(
      task_id,
      result => {
        btn.disabled = false;
        btn.textContent = 'Advance Month';
        setStatus(
          `Month advanced \u2014 ${result.fighters_aged} fighters aged, ` +
          `${result.events_simulated} AI events simulated.`
        );
        loadNotifications();
        if (state.currentView === 'dashboard') loadDashboard();
        if (state.currentView === 'roster') loadRoster();
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
  btn.textContent = 'Simulating\u2026';
  setStatus('Simulating fight card\u2026');

  try {
    const { task_id } = await api('/api/events/simulate', { method: 'POST' });
    pollTask(
      task_id,
      result => {
        btn.disabled = false;
        btn.textContent = 'Simulate Event';
        setStatus(`${result.event_name} \u2014 ${result.fights_simulated} fights.`);
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
  // Nav
  document.querySelectorAll('.nav-item').forEach(el => {
    el.addEventListener('click', () => navigate(el.dataset.view));
  });

  // Fighters filter
  document.getElementById('fighters-wc-filter').addEventListener('change', e => {
    loadFighters(e.target.value || null);
  });

  // Free agents filters
  document.getElementById('fa-wc-filter').addEventListener('change', () => loadFreeAgents());
  document.getElementById('fa-style-filter').addEventListener('change', () => loadFreeAgents());
  document.getElementById('fa-ovr-filter').addEventListener('input', e => {
    document.getElementById('fa-ovr-val').textContent = e.target.value;
  });
  document.getElementById('fa-ovr-filter').addEventListener('change', () => loadFreeAgents());
  document.getElementById('fa-sort').addEventListener('change', () => loadFreeAgents());

  // Rankings tabs
  document.querySelectorAll('.wc-tab').forEach(el => {
    el.addEventListener('click', () => loadRankings(el.dataset.wc));
  });

  // Actions
  document.getElementById('btn-advance-month').addEventListener('click', advanceMonth);
  document.getElementById('btn-simulate-event').addEventListener('click', simulateEvent);
  document.getElementById('btn-close-panel').addEventListener('click', closeFighterPanel);

  // Notifications
  document.getElementById('notif-bell').addEventListener('click', toggleNotifDropdown);
  // Close dropdown when clicking outside
  document.addEventListener('click', e => {
    const bell = document.getElementById('notif-bell');
    const dropdown = document.getElementById('notif-dropdown');
    if (!bell.contains(e.target) && !dropdown.contains(e.target)) {
      dropdown.classList.add('hidden');
    }
  });

  // Initial load
  loadNotifications();
  setInterval(loadNotifications, 30000);
  navigate('dashboard');
});
