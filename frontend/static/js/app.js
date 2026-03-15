'use strict';

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

const state = {
  currentView: 'dashboard',
  currentWeightClass: 'Middleweight',
  panelContext: null,  // 'fighters' | 'free-agents' | 'roster'
  notifications: [],
  gameDate: null,
  // Events state
  selectedEventId: null,
  selectedFighterA: null,
  selectedFighterB: null,
  poolFilter: '',
  poolWc: '',
  bookableFighters: [],
  // Show state
  activeShowId: null,
  showFormatSize: 8,
  showSelectedFighters: [],
  matchupCompareExpanded: false,
  tableSorts: {
    fighters: { key: 'name', direction: 'asc' },
    roster: { key: 'overall', direction: 'desc' },
    freeAgents: { key: 'overall', direction: 'desc' },
    rankings: { key: 'rank', direction: 'asc' },
    goat: { key: 'goat_score', direction: 'desc' },
    retiredLegends: { key: 'legacy_score', direction: 'desc' },
  },
};

// League History pagination
let historyOffset = 0;
const HISTORY_BATCH = 25;

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

function parseRecordValue(record) {
  if (!record) return 0;
  const [wins = 0, losses = 0, draws = 0] = String(record).split('-').map(v => Number(v) || 0);
  return wins * 10000 - losses * 100 + draws;
}

function getSortValue(item, key) {
  if (key === 'trajectory') return item.trajectory?.label || '';
  if (key === 'market_booking') {
    return window.MarketUi?.getBookingSortValue
      ? window.MarketUi.getBookingSortValue(item.market_context?.booking_value)
      : 0;
  }
  if (key === 'market_ai_heat') return Number(item.market_context?.ai_interest_score || 0);
  if (key === 'record') return parseRecordValue(item.record);
  if (key === 'rank' && item.rank == null) return 0;
  if (item[key] == null) return '';
  return item[key];
}

function sortCollection(items, tableName) {
  const sort = state.tableSorts[tableName];
  if (!sort) return items;

  const direction = sort.direction === 'asc' ? 1 : -1;
  return [...items].sort((a, b) => {
    const aVal = getSortValue(a, sort.key);
    const bVal = getSortValue(b, sort.key);

    if (typeof aVal === 'number' && typeof bVal === 'number') {
      return (aVal - bVal) * direction;
    }

    const aStr = String(aVal).toLowerCase();
    const bStr = String(bVal).toLowerCase();
    if (aStr < bStr) return -1 * direction;
    if (aStr > bStr) return 1 * direction;
    return 0;
  });
}

function updateSortableHeaders() {
  document.querySelectorAll('.sortable-header').forEach(header => {
    const tableName = header.dataset.table;
    const key = header.dataset.key;
    const sort = state.tableSorts[tableName];
    header.classList.remove('sorted-asc', 'sorted-desc');
    if (sort && sort.key === key) {
      header.classList.add(sort.direction === 'asc' ? 'sorted-asc' : 'sorted-desc');
    }
  });
}

function setTableSort(tableName, key) {
  const current = state.tableSorts[tableName];
  if (current?.key === key) {
    current.direction = current.direction === 'asc' ? 'desc' : 'asc';
  } else {
    state.tableSorts[tableName] = {
      key,
      direction: (key === 'name' || key === 'weight_class' || key === 'style' || key === 'archetype' || key === 'trajectory' || key === 'retired_date') ? 'asc' : 'desc',
    };
  }

  if (tableName === 'freeAgents') {
    const select = document.getElementById('fa-sort');
    if (select) {
      const reverseMap = {
        overall: 'overall',
        asking_salary: 'salary',
        age: 'age',
        hype: 'hype',
        market_booking: 'market_booking',
        market_ai_heat: 'market_ai_heat',
      };
      if (reverseMap[key]) select.value = reverseMap[key];
    }
  }

  if (tableName === 'roster') {
    const select = document.getElementById('roster-sort');
    if (select) {
      const reverseMap = {
        overall: 'overall',
        salary: 'salary',
        expiry_date: 'expiry_date',
        market_booking: 'market_booking',
        market_ai_heat: 'market_ai_heat',
      };
      if (reverseMap[key]) select.value = reverseMap[key];
    }
  }

  updateSortableHeaders();
  if (tableName === 'fighters') loadFighters(document.getElementById('fighters-wc-filter').value || null);
  if (tableName === 'roster') loadRoster();
  if (tableName === 'freeAgents') loadFreeAgents();
  if (tableName === 'rankings') loadRankings(state.currentWeightClass);
  if (tableName === 'goat' || tableName === 'retiredLegends') loadHallOfFame();
}

function initSortableTables() {
  document.querySelectorAll('.sortable-header').forEach(header => {
    header.addEventListener('click', () => setTableSort(header.dataset.table, header.dataset.key));
  });
  updateSortableHeaders();
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
  if (view === 'dashboard')    loadDashboard();
  if (view === 'events')       loadEventsView();
  if (view === 'fighters')     loadFighters();
  if (view === 'roster')       loadRoster();
  if (view === 'development')  loadDevelopmentView();
  if (view === 'broadcast')    loadBroadcastView();
  if (view === 'show')          loadShowView();
  if (view === 'free-agents')  loadFreeAgents();
  if (view === 'scouting')     loadScoutingView();
  if (view === 'rankings')     loadRankings(state.currentWeightClass);
  if (view === 'hof')          loadHallOfFame();
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
  loadDashUpcoming();
  loadDashRecentResults();
  loadCornerstones();
  loadBroadcastWidget();
  loadRivalWidget();
  loadSponsorshipWidget();
  loadShowWidget();
  loadNewsWidget();
  loadMediaWidget();
  loadObjectivesWidget();
  loadAssistantWidget();
}

async function loadDashUpcoming() {
  try {
    const events = await api('/api/events/scheduled');
    const el = document.getElementById('dash-upcoming');
    if (events.length === 0) {
      el.innerHTML = '<p class="muted">No upcoming events. Go to Events to create one.</p>';
      return;
    }
    const ev = events[0];
    el.innerHTML = `
      <div class="dash-event-card" onclick="navigate('events')">
        <div class="dash-event-name">${esc(ev.name)}</div>
        <div class="dash-event-meta">${esc(ev.venue)} &middot; ${ev.event_date} &middot; ${ev.fight_count} fights</div>
      </div>
    `;
  } catch (err) { /* silent */ }
}

async function loadDashRecentResults() {
  try {
    const events = await api('/api/events/history?limit=3');
    const el = document.getElementById('dash-recent-results');
    if (events.length === 0) {
      el.innerHTML = '<p class="muted">No completed events yet.</p>';
      return;
    }
    el.innerHTML = events.map(ev => `
      <div class="dash-result-card">
        <div class="dash-event-name">${esc(ev.name)}</div>
        <div class="dash-event-meta">${ev.event_date} &middot; ${ev.fight_count} fights &middot; ${formatCurrency(ev.total_revenue)}</div>
        ${ev.main_event_result ? `<div class="dash-main-result">${esc(ev.main_event_result)}</div>` : ''}
      </div>
    `).join('');
  } catch (err) { /* silent */ }
}

async function loadFinances() {
  try {
    const fin = await api('/api/finances');
    document.getElementById('dash-payroll').textContent = formatCurrency(fin.monthly_payroll);
    document.getElementById('dash-fight-costs').textContent = formatCurrency(fin.projected_fight_costs);
    document.getElementById('dash-broadcast-status').textContent = fin.broadcast_deal
      ? `${fin.broadcast_tier || 'Active'} Deal`
      : 'No Deal';
    document.getElementById('dash-sponsorship-income').textContent = `${formatCurrency(fin.monthly_sponsorship_income || 0)}/mo`;
  } catch (err) {
    // silently fail — cards stay at "—"
  }
}

async function loadObjectivesWidget() {
  try {
    const data = await api('/api/objectives');
    const widget = document.getElementById('objectives-widget');
    const content = document.getElementById('objectives-widget-content');
    if (!data.objectives || data.objectives.length === 0) {
      widget.classList.add('hidden');
      return;
    }
    widget.classList.remove('hidden');
    content.innerHTML = window.MarketUi?.renderObjectivesWidget
      ? window.MarketUi.renderObjectivesWidget(data)
      : '';
  } catch (err) {
    // silent
  }
}

async function loadAssistantWidget() {
  try {
    const data = await api('/api/assistant/actions');
    const widget = document.getElementById('assistant-widget');
    const content = document.getElementById('assistant-widget-content');
    if (!data || !Object.keys(data).length) {
      widget.classList.add('hidden');
      return;
    }
    widget.classList.remove('hidden');
    content.innerHTML = window.MarketUi?.renderSmartAssistantWidget
      ? window.MarketUi.renderSmartAssistantWidget(data)
      : '';
    content.querySelectorAll('.assistant-execute-btn').forEach(btn => {
      btn.addEventListener('click', () => executeAssistantAction({
        kind: btn.dataset.actionKind,
        fighter_id: btn.dataset.fighterId ? Number(btn.dataset.fighterId) : null,
        fighter_a_id: btn.dataset.fighterAId ? Number(btn.dataset.fighterAId) : null,
        fighter_b_id: btn.dataset.fighterBId ? Number(btn.dataset.fighterBId) : null,
      }));
    });
  } catch (err) {
    // silent
  }
}

async function executeAssistantAction(action) {
  if (!action?.kind) return;
  try {
    if (action.kind === 'open_free_agent' && action.fighter_id) {
      const agents = await api('/api/free-agents');
      const fighter = agents.find(f => f.id === action.fighter_id);
      navigate('free-agents');
      if (!fighter) {
        setStatus('Assistant target is no longer available.', true);
        return;
      }
      state.panelContext = 'free-agents';
      await showFighterPanel(action.fighter_id, {
        asking_salary: fighter.asking_salary,
        asking_fights: fighter.asking_fights,
        asking_length_months: fighter.asking_length_months,
        market_context: fighter.market_context || null,
        recommendation: fighter.recommendation || null,
      });
      setStatus('Opened the recommended signing target.');
      return;
    }

    if (action.kind === 'open_renewal' && action.fighter_id) {
      const roster = await api('/api/roster');
      const fighter = roster.find(f => f.id === action.fighter_id);
      navigate('roster');
      if (!fighter) {
        setStatus('Assistant renewal target is no longer on roster.', true);
        return;
      }
      state.panelContext = 'roster';
      await showFighterPanel(action.fighter_id, {
        salary: fighter.salary,
        fights_remaining: fighter.fights_remaining,
        fight_count_total: fighter.fight_count_total,
        expiry_date: fighter.expiry_date,
        market_context: fighter.market_context || null,
        recommendation: fighter.recommendation || null,
      });
      setTimeout(() => document.getElementById('btn-show-renew')?.click(), 0);
      setStatus('Opened the recommended renewal target.');
      return;
    }

    if (action.kind === 'prepare_booking' && action.fighter_a_id && action.fighter_b_id) {
      navigate('events');
      await loadEventsView();
      state.selectedFighterA = action.fighter_a_id;
      state.selectedFighterB = action.fighter_b_id;
      renderFighterPool();
      updateMatchupButton();
      await loadMatchupCompare();
      setStatus('Prepared the recommended matchup in the event builder.');
      return;
    }

    if (action.kind === 'open_roster_fighter' && action.fighter_id) {
      const roster = await api('/api/roster');
      const fighter = roster.find(f => f.id === action.fighter_id);
      navigate('roster');
      if (!fighter) {
        setStatus('Assistant risk target is no longer on roster.', true);
        return;
      }
      state.panelContext = 'roster';
      await showFighterPanel(action.fighter_id, {
        salary: fighter.salary,
        fights_remaining: fighter.fights_remaining,
        fight_count_total: fighter.fight_count_total,
        expiry_date: fighter.expiry_date,
        market_context: fighter.market_context || null,
        recommendation: fighter.recommendation || null,
      });
      setStatus('Opened the highest-risk roster situation.');
    }
  } catch (err) {
    setStatus('Assistant action failed: ' + err.message, true);
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
        <td>
          <div>${esc(f.name)}</div>
          ${window.MarketUi?.renderRecommendationBadge ? window.MarketUi.renderRecommendationBadge(f.recommendation) : ''}
        </td>
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
    const fighters = sortCollection(await api(`/api/fighters?${params}`), 'fighters');
    if (fighters.length === 0) {
      tbody.innerHTML = '<tr><td colspan="13" class="muted">No fighters found.</td></tr>';
      return;
    }
    tbody.innerHTML = fighters.map(f => `
      <tr data-fighter-id="${f.id}">
        <td>${esc(f.name)}</td>
        <td>${f.age}</td>
        <td><span class="badge wc-badge-color" data-wc="${esc(f.weight_class)}">${esc(f.weight_class)}</span></td>
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

function trajectoryBadgeHtml(trajectory) {
  if (!trajectory || !trajectory.label) return '<span class="trajectory-badge stalled">Stalled</span>';
  const cls = trajectory.label.toLowerCase();
  return `<span class="trajectory-badge ${esc(cls)}">${esc(trajectory.label)}</span>`;
}

function summarizeBio(text, limit = 220) {
  if (!text) return 'No scouting bio available yet.';
  if (text.length <= limit) return text;
  return text.slice(0, limit).trimEnd() + '…';
}

function matchupBadge(label, type) {
  return `<span class="matchup-badge ${esc(type)}">${esc(label)}</span>`;
}

function renderMatchupCompareCard(a, b, analysis) {
  const compare = document.getElementById('pool-compare');
  if (!a || !b) {
    compare.classList.add('hidden');
    compare.innerHTML = '';
    return;
  }

  const expanded = state.matchupCompareExpanded;
  const card = fighter => {
    const bio = expanded ? (fighter.bio || 'No scouting bio available yet.') : summarizeBio(fighter.bio);
    const tags = fighter.tags || [];
    const traits = fighter.traits || [];
    const chips = [...traits.slice(0, 2), ...tags.slice(0, 2)].slice(0, 3);
    return `
      <div class="compare-fighter-card" data-wc="${esc(fighter.weight_class)}">
        <div class="compare-fighter-top">
          <div>
            <div class="compare-fighter-name">${esc(fighter.name)}</div>
            <div class="compare-fighter-meta">
              ${fighter.nickname ? `"${esc(fighter.nickname)}" · ` : ''}${esc(fighter.record)} · OVR ${fighter.overall}
            </div>
          </div>
          ${trajectoryBadgeHtml(fighter.trajectory)}
        </div>
        <div class="compare-fighter-submeta">${esc(fighter.weight_class)} · ${esc(fighter.style)} · Age ${fighter.age}</div>
        <div class="compare-stat-grid">
          <div class="compare-stat-chip"><span>STR</span><strong>${fighter.striking}</strong></div>
          <div class="compare-stat-chip"><span>GRP</span><strong>${fighter.grappling}</strong></div>
          <div class="compare-stat-chip"><span>WR</span><strong>${fighter.wrestling}</strong></div>
          <div class="compare-stat-chip"><span>CRD</span><strong>${fighter.cardio}</strong></div>
        </div>
        ${chips.length ? `<div class="compare-chip-row">${chips.map(c => `<span class="compare-chip">${esc(String(c).replace(/_/g, ' '))}</span>`).join('')}</div>` : ''}
        <div class="compare-bio">${esc(bio)}</div>
      </div>
    `;
  };

  compare.innerHTML = `
    <div class="pool-compare-header">
      <span class="pool-compare-title">Matchup Compare</span>
      <button id="btn-toggle-compare-bio" class="btn btn-secondary compare-toggle-btn">${expanded ? 'Compact View' : 'Full Bios'}</button>
    </div>
    ${analysis ? `
      <div class="matchup-analysis-box">
        <div class="matchup-analysis-top">
          <span class="matchup-analysis-title">${esc(analysis.booking_value)}</span>
          <span class="matchup-analysis-meta">OVR gap ${analysis.overall_gap} · Draw ${Number(analysis.combined_draw).toFixed(1)}</span>
        </div>
        <div class="matchup-analysis-badges">
          ${matchupBadge(analysis.competitiveness, 'competitive')}
          ${matchupBadge(`${analysis.star_power} Star Power`, 'star')}
          ${matchupBadge(`${analysis.prospect_risk} Prospect Risk`, 'risk')}
        </div>
        <div class="matchup-analysis-reasons">
          ${(analysis.reasons || []).map(r => `<div class="matchup-analysis-reason">${esc(r)}</div>`).join('')}
        </div>
      </div>
    ` : ''}
    <div class="pool-compare-grid">
      ${card(a)}
      <div class="pool-compare-vs">vs</div>
      ${card(b)}
    </div>
  `;
  compare.classList.toggle('expanded-bios', expanded);
  compare.classList.remove('hidden');
  document.getElementById('btn-toggle-compare-bio').addEventListener('click', () => {
    state.matchupCompareExpanded = !state.matchupCompareExpanded;
    renderMatchupCompareCard(a, b);
  });
}

async function loadMatchupCompare() {
  const compare = document.getElementById('pool-compare');
  if (!state.selectedFighterA || !state.selectedFighterB) {
    compare.classList.add('hidden');
    compare.innerHTML = '';
    state.matchupCompareExpanded = false;
    return;
  }

  const fighterIds = [state.selectedFighterA, state.selectedFighterB];
  compare.classList.remove('hidden');
  compare.innerHTML = '<div class="muted" style="padding:12px">Loading matchup breakdown...</div>';

  try {
    const [a, aBio, aTags, b, bBio, bTags, analysis] = await Promise.all([
      api(`/api/fighters/${fighterIds[0]}`),
      api(`/api/fighters/${fighterIds[0]}/bio`),
      api(`/api/fighters/${fighterIds[0]}/tags`),
      api(`/api/fighters/${fighterIds[1]}`),
      api(`/api/fighters/${fighterIds[1]}/bio`),
      api(`/api/fighters/${fighterIds[1]}/tags`),
      api('/api/matchups/analysis', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ fighter_a_id: fighterIds[0], fighter_b_id: fighterIds[1] }),
      }),
    ]);
    a.bio = aBio.bio || '';
    a.tags = aTags.tags || [];
    b.bio = bBio.bio || '';
    b.tags = bTags.tags || [];

    if (state.selectedFighterA !== fighterIds[0] || state.selectedFighterB !== fighterIds[1]) {
      return;
    }
    renderMatchupCompareCard(a, b, analysis);
  } catch (err) {
    compare.innerHTML = `<div class="muted" style="padding:12px">Could not load matchup compare: ${esc(err.message)}</div>`;
  }
}

async function showFighterPanel(fighterId, extraData) {
  const panel = document.getElementById('fighter-panel');
  panel.classList.remove('hidden');
  panel.setAttribute('data-wc', '');
  state.panelExtraData = extraData;

  // Reset content
  document.getElementById('panel-name').textContent    = 'Loading\u2026';
  document.getElementById('panel-nickname').innerHTML   = '';
  document.getElementById('panel-subtitle').textContent = '';
  document.getElementById('panel-archetype').textContent = '';
  document.getElementById('panel-trajectory').classList.add('hidden');
  document.getElementById('panel-trajectory-badge').textContent = '—';
  document.getElementById('panel-trajectory-summary').textContent = '';
  document.getElementById('panel-trajectory-reasons').innerHTML = '';
  document.getElementById('panel-negotiation').innerHTML = '';
  document.getElementById('panel-negotiation').classList.add('hidden');
  document.getElementById('panel-relationship').innerHTML = '';
  document.getElementById('panel-relationship').classList.add('hidden');
  document.getElementById('panel-record').textContent  = '\u2014';
  document.getElementById('panel-overall').textContent = '\u2014';
  document.getElementById('panel-goat').textContent    = '\u2014';
  document.getElementById('panel-tags').innerHTML      = '';
  document.getElementById('panel-bio').textContent     = 'Loading\u2026';
  document.getElementById('panel-stat-bars').innerHTML = '';
  document.getElementById('panel-actions').innerHTML   = '';
  document.getElementById('panel-actions').classList.add('hidden');
  document.getElementById('panel-cs-badge').classList.add('hidden');
  document.getElementById('panel-market-context').innerHTML = '';
  document.getElementById('panel-market-context').classList.add('hidden');
  document.getElementById('panel-offer-result').innerHTML = '';
  document.getElementById('panel-sponsorships').innerHTML = '';
  document.getElementById('panel-sponsorships').classList.add('hidden');
  document.getElementById('panel-highlights').classList.add('hidden');
  document.getElementById('highlights-list').innerHTML = '';
  document.getElementById('panel-timeline').classList.add('hidden');
  document.getElementById('timeline-list').innerHTML = '';
  document.getElementById('bar-popularity').style.width = '0%';
  document.getElementById('bar-hype').style.width       = '0%';
  document.getElementById('val-popularity').textContent = '';
  document.getElementById('val-hype').textContent       = '';

  try {
    const [fighter, bioData, tagsData, highlightsData] = await Promise.all([
      api(`/api/fighters/${fighterId}`),
      api(`/api/fighters/${fighterId}/bio`),
      api(`/api/fighters/${fighterId}/tags`),
      api(`/api/fighters/${fighterId}/highlights`),
    ]);

    document.getElementById('panel-name').textContent     = fighter.name;
    // Retired badge
    const retiredBadgeEl = document.getElementById('panel-retired-badge');
    if (retiredBadgeEl) retiredBadgeEl.classList.toggle('hidden', !fighter.is_retired);
    // Cornerstone badge
    document.getElementById('panel-cs-badge').classList.toggle('hidden', !fighter.is_cornerstone);
    // Nickname display with edit pencil
    const nickEl = document.getElementById('panel-nickname');
    if (fighter.nickname) {
      nickEl.innerHTML = `<span class="nick-display">"${esc(fighter.nickname)}"</span> <button class="nick-edit" title="Edit nickname">&#9998;</button>`;
    } else {
      nickEl.innerHTML = `<button class="nick-edit" title="Set nickname">&#9998; Set Nickname</button>`;
    }
    nickEl.querySelector('.nick-edit').addEventListener('click', () => openNicknameEditor(fighterId));
    document.getElementById('panel-subtitle').textContent = `${fighter.weight_class} \xB7 ${fighter.style} \xB7 Age ${fighter.age}`;
    panel.setAttribute('data-wc', fighter.weight_class);
    document.getElementById('panel-archetype').textContent = fighter.archetype || '';
    const trajectory = fighter.trajectory || {};
    const trajectoryWrap = document.getElementById('panel-trajectory');
    const trajectoryBadge = document.getElementById('panel-trajectory-badge');
    trajectoryWrap.classList.remove('hidden');
    trajectoryBadge.textContent = trajectory.label || 'Stalled';
    trajectoryBadge.className = `trajectory-badge ${(trajectory.label || 'stalled').toLowerCase()}`;
    document.getElementById('panel-trajectory-summary').textContent =
      `${trajectory.recent_form || 'No recent fights'} \u00b7 ${trajectory.market_value_hint || 'Current value looks stable.'}`;
    document.getElementById('panel-trajectory-reasons').innerHTML =
      (trajectory.reasons || []).map(r => `<div class="panel-trajectory-reason">${esc(r)}</div>`).join('');
    const negotiationEl = document.getElementById('panel-negotiation');
    if (fighter.negotiation_profile && window.MarketUi?.renderNegotiationProfile) {
      negotiationEl.classList.remove('hidden');
      negotiationEl.innerHTML = window.MarketUi.renderNegotiationProfile(fighter.negotiation_profile);
    }
    const relationshipEl = document.getElementById('panel-relationship');
    if (fighter.relationship_memory && window.MarketUi?.renderRelationshipMemory) {
      relationshipEl.classList.remove('hidden');
      relationshipEl.innerHTML = window.MarketUi.renderRelationshipMemory(fighter.relationship_memory);
    }
    document.getElementById('panel-record').textContent   = fighter.record;
    document.getElementById('panel-overall').textContent  = fighter.overall;
    document.getElementById('panel-goat').textContent     = fighter.goat_score > 0 ? fighter.goat_score.toFixed(1) : '\u2014';
    // Legacy score (retired fighters)
    const legacyEl = document.getElementById('panel-legacy');
    if (legacyEl) {
      if (fighter.is_retired && fighter.legacy_score > 0) {
        legacyEl.textContent = fighter.legacy_score.toFixed(1);
        legacyEl.parentElement.classList.remove('hidden');
      } else {
        legacyEl.parentElement.classList.add('hidden');
      }
    }

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

    // Career Highlights
    const highlightsSection = document.getElementById('panel-highlights');
    const highlightsList = document.getElementById('highlights-list');
    const highlights = (highlightsData && highlightsData.highlights) || [];
    if (highlights.length > 0) {
        highlightsSection.classList.remove('hidden');
        highlightsList.innerHTML = highlights.map(h =>
            `<li class="highlight-item">${esc(h.text)}</li>`
        ).join('');
    } else {
        highlightsSection.classList.add('hidden');
        highlightsList.innerHTML = '';
    }

    const marketEl = document.getElementById('panel-market-context');
    if (extraData?.market_context && window.MarketUi?.renderMarketContextCard) {
      marketEl.classList.remove('hidden');
      const recommendationHtml = window.MarketUi?.renderRecommendationBadge
        ? window.MarketUi.renderRecommendationBadge(extraData.recommendation)
        : '';
      marketEl.innerHTML = `${recommendationHtml}${window.MarketUi.renderMarketContextCard(extraData.market_context)}`;
    } else {
      marketEl.classList.add('hidden');
      marketEl.innerHTML = '';
    }

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
          <button class="${fighter.is_cornerstone ? 'btn-secondary' : 'btn-cs'}" id="btn-cs-toggle">
            ${fighter.is_cornerstone ? 'Remove Cornerstone' : '\u{1F451} Designate Cornerstone'}
          </button>
        </div>
        <div id="renew-form-area"></div>
      `;
      document.getElementById('btn-release').addEventListener('click', () => releaseFighter(fighterId));
      document.getElementById('btn-cs-toggle').addEventListener('click', () => toggleCornerstone(fighterId, fighter.is_cornerstone));
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

    // Load sponsorships for roster fighters
    if (state.panelContext === 'roster') {
      loadPanelSponsorships(fighterId);
    }

    // Load career timeline
    loadFighterTimeline(fighterId);

  } catch (err) {
    document.getElementById('panel-name').textContent = 'Error';
    document.getElementById('panel-bio').textContent  = err.message;
  }
}

async function openNicknameEditor(fighterId) {
  const nickEl = document.getElementById('panel-nickname');
  nickEl.innerHTML = '<span class="muted" style="font-size:12px">Loading suggestions...</span>';
  try {
    const data = await api(`/api/fighters/${fighterId}/nickname-suggestions`);
    const suggestions = data.suggestions || [];
    let html = '<div class="nick-editor">';
    html += suggestions.map(s => `<span class="nick-chip" data-nick="${esc(s)}">${esc(s)}</span>`).join('');
    html += '<div class="nick-custom"><input type="text" class="nick-input" placeholder="Custom nickname..." maxlength="30"><button class="btn btn-primary nick-save-btn">Save</button></div>';
    html += '</div>';
    nickEl.innerHTML = html;
    nickEl.querySelectorAll('.nick-chip').forEach(chip => {
      chip.addEventListener('click', () => {
        nickEl.querySelector('.nick-input').value = chip.dataset.nick;
        nickEl.querySelectorAll('.nick-chip').forEach(c => c.classList.remove('selected'));
        chip.classList.add('selected');
      });
    });
    nickEl.querySelector('.nick-save-btn').addEventListener('click', async () => {
      const val = nickEl.querySelector('.nick-input').value.trim();
      if (!val) return;
      try {
        const result = await api(`/api/fighters/${fighterId}/nickname`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ nickname: val }),
        });
        if (result.success) {
          setStatus(result.message);
          showFighterPanel(fighterId);
        } else {
          setStatus(result.message, true);
        }
      } catch (err) {
        setStatus('Error: ' + err.message, true);
      }
    });
  } catch (err) {
    nickEl.innerHTML = `<span class="muted" style="font-size:12px">Error loading suggestions</span>`;
  }
}

async function loadFighterTimeline(fighterId) {
  try {
    const data = await api(`/api/fighters/${fighterId}/timeline`);
    const container = document.getElementById('panel-timeline');
    const list = document.getElementById('timeline-list');
    const toggle = document.getElementById('timeline-toggle');

    if (!data.timeline || data.timeline.length === 0) {
      container.classList.add('hidden');
      return;
    }

    container.classList.remove('hidden');
    toggle.textContent = `Career Timeline (${data.timeline.length} fights)`;
    list.classList.add('hidden');

    toggle.onclick = () => list.classList.toggle('hidden');

    list.innerHTML = data.timeline.map(t => `
      <div class="timeline-entry ${t.result === 'W' ? 'timeline-win' : 'timeline-loss'}">
        <div class="timeline-date">${t.event_date}</div>
        <div class="timeline-main">
          <span class="timeline-result-badge ${t.result === 'W' ? 'badge-win' : 'badge-loss'}">${t.result}</span>
          <span class="timeline-opponent">${esc(t.opponent_name)}</span>
          ${t.is_title_fight ? '<span class="timeline-title-badge">TITLE</span>' : ''}
        </div>
        <div class="timeline-detail">
          ${esc(t.method)}${t.round ? ' R' + t.round : ''}${t.time ? ' ' + t.time : ''} &middot; ${t.running_record}
        </div>
      </div>
    `).join('');
  } catch (err) { /* silent */ }
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
  tbody.innerHTML = '<tr><td colspan="10" class="muted">Loading...</td></tr>';

  const params = new URLSearchParams();
  const wc = document.getElementById('fa-wc-filter').value;
  const style = document.getElementById('fa-style-filter').value;
  const minOvr = document.getElementById('fa-ovr-filter').value;
  const trajectoryFilter = document.getElementById('fa-trajectory-filter').value;
  const activeSortKey = state.tableSorts.freeAgents?.key || 'overall';

  if (wc) params.set('weight_class', wc);
  if (style) params.set('style', style);
  if (minOvr && parseInt(minOvr) > 0) params.set('min_overall', minOvr);
  const serverSortMap = {
    overall: 'overall',
    asking_salary: 'salary',
    age: 'age',
    hype: 'hype',
  };
  if (serverSortMap[activeSortKey]) params.set('sort_by', serverSortMap[activeSortKey]);

  try {
    let agents = await api(`/api/free-agents?${params}`);
    agents = agents.filter((agent) => window.MarketUi?.matchesTrajectoryFilter
      ? window.MarketUi.matchesTrajectoryFilter(agent.market_context, trajectoryFilter)
      : true);
    agents = sortCollection(agents, 'freeAgents');
    if (agents.length === 0) {
      tbody.innerHTML = '<tr><td colspan="10" class="muted">No free agents found.</td></tr>';
      return;
    }
    tbody.innerHTML = agents.map(f => `
      <tr data-fighter-id="${f.id}"
          data-asking-salary="${f.asking_salary}"
          data-asking-fights="${f.asking_fights}"
          data-asking-length="${f.asking_length_months}">
        <td>
          <div>${esc(f.name)}</div>
          ${window.MarketUi?.renderCompactMarketLine ? window.MarketUi.renderCompactMarketLine(f.market_context, f.recommendation) : ''}
        </td>
        <td>${f.age}</td>
        <td><span class="badge wc-badge-color" data-wc="${esc(f.weight_class)}">${esc(f.weight_class)}</span></td>
        <td>${esc(f.style)}</td>
        <td><strong>${f.overall}</strong></td>
        <td>${esc(f.record)}</td>
        <td>${trajectoryBadgeHtml(f.trajectory)}</td>
        <td>${f.hype.toFixed(1)}</td>
        <td>${formatCurrency(f.asking_salary)}</td>
        <td>${f.asking_fights}</td>
      </tr>
    `).join('');

    tbody.querySelectorAll('tr[data-fighter-id]').forEach(row => {
      row.addEventListener('click', () => {
        const fighter = agents.find(f => f.id === Number(row.dataset.fighterId));
        state.panelContext = 'free-agents';
        showFighterPanel(Number(row.dataset.fighterId), {
          asking_salary: Number(row.dataset.askingSalary),
          asking_fights: Number(row.dataset.askingFights),
          asking_length_months: Number(row.dataset.askingLength),
          market_context: fighter?.market_context || null,
          recommendation: fighter?.recommendation || null,
        });
      });
    });
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="10" class="muted">Error: ${esc(err.message)}</td></tr>`;
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
    const evaluationHtml = window.MarketUi?.renderOfferEvaluation
      ? window.MarketUi.renderOfferEvaluation(result.offer_evaluation)
      : '';
    resultEl.innerHTML = `
      <div class="offer-result ${result.accepted ? 'success' : 'rejected'}">${esc(result.message)}</div>
      ${evaluationHtml}
    `;
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
  tbody.innerHTML = '<tr><td colspan="10" class="muted">Loading...</td></tr>';

  const trajectoryFilter = document.getElementById('roster-trajectory-filter')?.value || '';

  try {
    const [rosterData, fin] = await Promise.all([
      api('/api/roster'),
      api('/api/finances'),
    ]);
    let roster = rosterData.filter((fighter) => window.MarketUi?.matchesTrajectoryFilter
      ? window.MarketUi.matchesTrajectoryFilter(fighter.market_context, trajectoryFilter)
      : true);
    roster = sortCollection(roster, 'roster');

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

    loadRosterDecisionCenter();

    if (roster.length === 0) {
      tbody.innerHTML = '<tr><td colspan="10" class="muted">No fighters on roster. Sign some free agents!</td></tr>';
      return;
    }

    tbody.innerHTML = roster.map(f => `
      <tr data-fighter-id="${f.id}"
          data-salary="${f.salary}"
          data-fights-remaining="${f.fights_remaining}"
          data-fight-count-total="${f.fight_count_total}"
          data-expiry-date="${f.expiry_date || ''}">
        <td>
          <div>${esc(f.name)}</div>
          ${window.MarketUi?.renderCompactMarketLine ? window.MarketUi.renderCompactMarketLine(f.market_context, f.recommendation) : ''}
        </td>
        <td>${f.age}</td>
        <td><span class="badge wc-badge-color" data-wc="${esc(f.weight_class)}">${esc(f.weight_class)}</span></td>
        <td>${esc(f.style)}</td>
        <td><strong>${f.overall}</strong></td>
        <td>${esc(f.record)}</td>
        <td>${trajectoryBadgeHtml(f.trajectory)}</td>
        <td>${f.fights_remaining} / ${f.fight_count_total}</td>
        <td>${formatCurrency(f.salary)}</td>
        <td>${f.expiry_date || '\u2014'}</td>
      </tr>
    `).join('');

    tbody.querySelectorAll('tr[data-fighter-id]').forEach(row => {
      row.addEventListener('click', () => {
        const fighter = roster.find(f => f.id === Number(row.dataset.fighterId));
        state.panelContext = 'roster';
        showFighterPanel(Number(row.dataset.fighterId), {
          salary: Number(row.dataset.salary),
          fights_remaining: Number(row.dataset.fightsRemaining),
          fight_count_total: Number(row.dataset.fightCountTotal),
          expiry_date: row.dataset.expiryDate,
          market_context: fighter?.market_context || null,
          recommendation: fighter?.recommendation || null,
        });
      });
    });
    loadCornerstones();
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="10" class="muted">Error: ${esc(err.message)}</td></tr>`;
  }
}

async function loadRosterDecisionCenter() {
  const el = document.getElementById('roster-decision-center');
  if (!el) return;
  try {
    const data = await api('/api/roster/decision-center');
    if (!window.MarketUi?.renderDecisionCenterColumn) {
      el.innerHTML = '';
      return;
    }
    el.innerHTML = [
      window.MarketUi.renderDecisionCenterColumn('Renewal Pressure', data.expiring_contracts),
      window.MarketUi.renderDecisionCenterColumn('Sell / Replace', data.sell_candidates),
      window.MarketUi.renderDecisionCenterColumn('Buy Targets', data.buy_targets),
      window.MarketUi.renderDecisionCenterColumn('Division Outlook', data.division_outlook),
    ].join('');
  } catch (err) {
    el.innerHTML = '<div class="decision-center-column"><div class="decision-center-title">Decision Center</div><div class="decision-center-empty">Error loading decision center.</div></div>';
  }
}

async function loadScoutingView() {
  const el = document.getElementById('scouting-board');
  if (!el) return;
  try {
    const board = await api('/api/scouting/board');
    if (!window.MarketUi?.renderScoutingBoard) {
      el.innerHTML = '';
      return;
    }
    el.innerHTML = window.MarketUi.renderScoutingBoard(board);
  } catch (err) {
    el.innerHTML = '<div class="decision-center-column"><div class="decision-center-title">Scouting</div><div class="decision-center-empty">Error loading scouting board.</div></div>';
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

async function toggleCornerstone(fighterId, isCurrentlyCornerstone) {
  try {
    const endpoint = isCurrentlyCornerstone ? '/api/cornerstones/remove' : '/api/cornerstones/designate';
    const result = await api(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ fighter_id: fighterId }),
    });
    if (result.error) {
      setStatus(result.error, true);
      return;
    }
    setStatus(isCurrentlyCornerstone ? 'Cornerstone removed.' : 'Fighter designated as cornerstone!');
    showFighterPanel(fighterId, state.panelExtraData);
    loadRoster();
    loadCornerstones();
  } catch (err) {
    setStatus('Error: ' + err.message, true);
  }
}

async function loadCornerstones() {
  try {
    const cornerstones = await api('/api/cornerstones');
    // Dashboard widget
    const widget = document.getElementById('cs-widget');
    const widgetList = document.getElementById('cs-widget-list');
    if (cornerstones.length > 0) {
      widget.classList.remove('hidden');
      widgetList.innerHTML = cornerstones.map(f => `
        <div class="cs-card" data-id="${f.id}">
          <span class="cs-crown">&#128081;</span>
          <div class="cs-card-info">
            <strong>${esc(f.name)}</strong>
            ${f.nickname ? `<span class="nick-inline">"${esc(f.nickname)}"</span>` : ''}
            <span class="muted">${esc(f.weight_class)} &middot; ${esc(f.record)} &middot; OVR ${f.overall}</span>
          </div>
        </div>
      `).join('');
      widgetList.querySelectorAll('.cs-card').forEach(card => {
        card.addEventListener('click', () => showFighterPanel(Number(card.dataset.id)));
      });
    } else {
      widget.classList.add('hidden');
    }

    // Roster cornerstone section
    const section = document.getElementById('cs-section');
    const cards = document.getElementById('cs-cards');
    const countEl = document.getElementById('cs-count');
    if (section) {
      if (cornerstones.length > 0) {
        section.classList.remove('hidden');
        countEl.textContent = `${cornerstones.length}/3`;
        cards.innerHTML = cornerstones.map(f => `
          <div class="cs-card" data-id="${f.id}">
            <span class="cs-crown">&#128081;</span>
            <div class="cs-card-info">
              <strong>${esc(f.name)}</strong>
              ${f.nickname ? `<span class="nick-inline">"${esc(f.nickname)}"</span>` : ''}
              <span class="muted">${esc(f.weight_class)} &middot; ${esc(f.record)}</span>
            </div>
          </div>
        `).join('');
        cards.querySelectorAll('.cs-card').forEach(card => {
          card.addEventListener('click', () => {
            state.panelContext = 'roster';
            showFighterPanel(Number(card.dataset.id));
          });
        });
      } else {
        section.classList.add('hidden');
      }
    }
  } catch (err) { /* silent */ }
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
    const evaluationHtml = window.MarketUi?.renderOfferEvaluation
      ? window.MarketUi.renderOfferEvaluation(result.offer_evaluation)
      : '';
    resultEl.innerHTML = `
      <div class="offer-result ${result.accepted ? 'success' : 'rejected'}">${esc(result.message)}</div>
      ${evaluationHtml}
    `;
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
  const titlePictureEl = document.getElementById('title-picture');
  tbody.innerHTML = '<tr><td colspan="5" class="muted">Loading...</td></tr>';
  try {
    const [rankingsRaw, titlePicture] = await Promise.all([
      api(`/api/rankings/${encodeURIComponent(weightClass)}`),
      api(`/api/title-picture/${encodeURIComponent(weightClass)}`),
    ]);
    const rankings = sortCollection(rankingsRaw, 'rankings');
    if (window.MarketUi?.renderTitlePicture) {
      titlePictureEl.innerHTML = window.MarketUi.renderTitlePicture(titlePicture);
    }
    if (rankings.length === 0) {
      tbody.innerHTML = '<tr><td colspan="5" class="muted">No rankings available.</td></tr>';
      return;
    }
    tbody.innerHTML = rankings.map(r => `
      <tr>
        <td><strong>#${r.rank}</strong></td>
        <td>${esc(r.name)}${r.nickname ? ' <span class="nick-inline">"' + esc(r.nickname) + '"</span>' : ''}</td>
        <td>${esc(r.record)}</td>
        <td>${r.overall}</td>
        <td>${r.score.toFixed(1)}</td>
      </tr>
    `).join('');
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="5" class="muted">Error: ${esc(err.message)}</td></tr>`;
    titlePictureEl.innerHTML = `<div class="decision-center-empty">Error: ${esc(err.message)}</div>`;
  }
}

// ---------------------------------------------------------------------------
// Hall of Fame
// ---------------------------------------------------------------------------

async function loadHallOfFame() {
  await Promise.all([loadGoat(), loadRivalries(), loadRetiredLegends(), loadLegendCoaches()]);
}

async function loadGoat() {
  const tbody = document.getElementById('goat-tbody');
  tbody.innerHTML = '<tr><td colspan="7" class="muted">Loading...</td></tr>';
  try {
    const goat = sortCollection(await api('/api/goat?top=10'), 'goat');
    if (goat.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" class="muted">No data yet \u2014 simulate some events first.</td></tr>';
      return;
    }
    tbody.innerHTML = goat.map(g => `
      <tr>
        <td><strong>#${g.rank}</strong></td>
        <td>${esc(g.name)}</td>
        <td><span class="badge wc-badge-color" data-wc="${esc(g.weight_class)}">${esc(g.weight_class)}</span></td>
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

async function loadRetiredLegends() {
  const tbody = document.getElementById('retired-legends-tbody');
  if (!tbody) return;
  tbody.innerHTML = '<tr><td colspan="7" class="muted">Loading...</td></tr>';
  try {
    const legends = sortCollection(await api('/api/retired-legends?top=20'), 'retiredLegends');
    if (!legends || legends.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" class="muted">No retired fighters yet \u2014 legends will appear here as careers end.</td></tr>';
      return;
    }
    tbody.innerHTML = legends.map((l, i) => `
      <tr style="cursor:pointer" onclick="showFighterPanel(${l.id})">
        <td>${i + 1}</td>
        <td><strong>${esc(l.name)}</strong>${l.nickname ? ' <span class="muted">"' + esc(l.nickname) + '"</span>' : ''}</td>
        <td><span class="badge wc-badge-color" data-wc="${esc(l.weight_class)}">${esc(l.weight_class)}</span></td>
        <td>${esc(l.record)}</td>
        <td>${l.peak_overall}</td>
        <td><strong>${l.legacy_score}</strong></td>
        <td>${l.retired_date || '\u2014'}</td>
      </tr>
    `).join('');
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" class="muted">Error: ${esc(err.message)}</td></tr>`;
  }
}

async function loadLegendCoaches() {
  const hiredContainer = document.getElementById('legend-coaches-list');
  const availContainer = document.getElementById('legend-coaches-available-list');
  if (!hiredContainer || !availContainer) return;

  try {
    const [coaches, available, camps] = await Promise.all([
      api('/api/legends/coaches'),
      api('/api/legends/available'),
      api('/api/development/camps'),
    ]);

    // Hired coaches
    if (!coaches || coaches.length === 0) {
      hiredContainer.innerHTML = '<p class="muted">No legend coaches hired yet.</p>';
    } else {
      hiredContainer.innerHTML = coaches.map(c => `
        <div class="legend-coach-card">
          <div style="display:flex;justify-content:space-between;align-items:center">
            <div>
              <strong>${esc(c.fighter_name)}</strong>
              <span class="badge-retired">LEGEND</span>
              <span class="muted" style="margin-left:6px">Legacy ${c.legacy_score}</span>
            </div>
            <button class="btn btn-small btn-danger" onclick="fireLegendCoach(${c.id}, '${esc(c.fighter_name)}')">Fire</button>
          </div>
          <div style="margin-top:6px;font-size:12px;color:#aaa">
            ${c.weight_class || ''} &bull; $${c.salary.toLocaleString()}/mo &bull; +${(c.specialty_bonus * 100).toFixed(0)}% training bonus
          </div>
          <div style="margin-top:6px;font-size:12px">
            Camp: ${c.camp_name ? '<strong>' + esc(c.camp_name) + '</strong> (T' + c.camp_tier + ')' : '<span class="muted">Unassigned</span>'}
            <select style="margin-left:8px;font-size:11px;padding:2px 4px;background:#1a1a2e;color:#ccc;border:1px solid #333;border-radius:3px"
              onchange="assignLegendCamp(${c.id}, this.value)">
              <option value="">-- No Camp --</option>
              ${(camps || []).map(camp => `<option value="${camp.id}" ${c.camp_id === camp.id ? 'selected' : ''}>${esc(camp.name)} (T${camp.tier})</option>`).join('')}
            </select>
          </div>
        </div>
      `).join('');
    }

    // Available legends
    if (!available || available.length === 0) {
      availContainer.innerHTML = '<p class="muted">No retired legends available for hiring.</p>';
    } else {
      availContainer.innerHTML = available.map(l => `
        <div class="legend-coach-card" style="opacity:0.85">
          <div style="display:flex;justify-content:space-between;align-items:center">
            <div>
              <strong>${esc(l.name)}</strong>
              <span class="muted" style="margin-left:6px">${esc(l.weight_class)} &bull; ${esc(l.record)}</span>
            </div>
            <button class="btn btn-small" onclick="hireLegendCoach(${l.id})">Hire</button>
          </div>
          <div style="margin-top:4px;font-size:12px;color:#aaa">
            Legacy ${l.legacy_score} &bull; $${l.monthly_salary.toLocaleString()}/mo &bull; +${(l.specialty_bonus * 100).toFixed(0)}% bonus
          </div>
        </div>
      `).join('');
    }
  } catch (err) {
    hiredContainer.innerHTML = `<p class="muted">Error: ${esc(err.message)}</p>`;
    availContainer.innerHTML = '';
  }
}

async function hireLegendCoach(fighterId) {
  try {
    const result = await api('/api/legends/hire', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ fighter_id: fighterId }) });
    if (result.success) {
      showNotification(result.message, 'success');
      loadLegendCoaches();
    } else {
      showNotification(result.error || 'Failed to hire', 'error');
    }
  } catch (err) {
    showNotification(err.message, 'error');
  }
}

async function fireLegendCoach(coachId, name) {
  if (!confirm(`Fire ${name} from coaching staff?`)) return;
  try {
    const result = await api('/api/legends/fire', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ coach_id: coachId }) });
    if (result.success) {
      showNotification(result.message, 'success');
      loadLegendCoaches();
    } else {
      showNotification(result.error || 'Failed to fire', 'error');
    }
  } catch (err) {
    showNotification(err.message, 'error');
  }
}

async function assignLegendCamp(coachId, campId) {
  try {
    const result = await api('/api/legends/assign-camp', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ coach_id: coachId, camp_id: campId ? parseInt(campId) : null }) });
    if (result.success) {
      showNotification(result.message, 'success');
    } else {
      showNotification(result.error || 'Failed to assign', 'error');
      loadLegendCoaches();
    }
  } catch (err) {
    showNotification(err.message, 'error');
    loadLegendCoaches();
  }
}

// ---------------------------------------------------------------------------
// Game Date
// ---------------------------------------------------------------------------

async function loadGameDate() {
  try {
    const gs = await api('/api/gamestate');
    state.gameDate = gs.current_date;
    const d = new Date(gs.current_date + 'T00:00:00');
    const formatted = d.toLocaleDateString('en-US', { year: 'numeric', month: 'long' });
    document.getElementById('game-date-display').textContent = `Game Date: ${formatted}`;
  } catch (err) { /* silent */ }
}

// ---------------------------------------------------------------------------
// Events View
// ---------------------------------------------------------------------------

async function loadEventsView() {
  state.selectedFighterA = null;
  state.selectedFighterB = null;
  await Promise.all([loadScheduledEvents(), loadCompletedEvents(), loadLeagueHistory(), loadBookableFighters()]);
  if (state.selectedEventId) loadEventCard(state.selectedEventId);
}

async function loadScheduledEvents() {
  try {
    const events = await api('/api/events/scheduled');
    const el = document.getElementById('events-scheduled-list');
    if (events.length === 0) {
      el.innerHTML = '<p class="muted">No scheduled events.</p>';
      return;
    }
    el.innerHTML = events.map(ev => `
      <div class="event-list-item ${state.selectedEventId === ev.id ? 'selected' : ''}" data-event-id="${ev.id}">
        <div class="event-list-name">${esc(ev.name)}</div>
        <div class="event-list-meta">${ev.event_date} &middot; ${ev.fight_count} fights</div>
      </div>
    `).join('');
    el.querySelectorAll('.event-list-item').forEach(item => {
      item.addEventListener('click', () => {
        state.selectedEventId = Number(item.dataset.eventId);
        loadEventCard(state.selectedEventId);
        loadScheduledEvents();
      });
    });
  } catch (err) { /* silent */ }
}

async function loadCompletedEvents() {
  try {
    const events = await api('/api/events/history?limit=10');
    const el = document.getElementById('events-completed-list');
    if (events.length === 0) {
      el.innerHTML = '<p class="muted">No completed events.</p>';
      return;
    }
    el.innerHTML = events.map(ev => `
      <div class="event-list-item completed ${state.selectedEventId === ev.id ? 'selected' : ''}" data-event-id="${ev.id}">
        <div class="event-list-name">${esc(ev.name)}</div>
        <div class="event-list-meta">${ev.event_date} &middot; ${ev.main_event_result || ''}</div>
      </div>
    `).join('');
    el.querySelectorAll('.event-list-item').forEach(item => {
      item.addEventListener('click', () => {
        state.selectedEventId = Number(item.dataset.eventId);
        loadEventCard(state.selectedEventId);
        loadCompletedEvents();
        loadScheduledEvents();
      });
    });
  } catch (err) { /* silent */ }
}

async function loadLeagueHistory(append) {
  try {
    const orgFilter = document.getElementById('history-org-filter').value;
    let url = `/api/events/all-history?limit=${HISTORY_BATCH}&offset=${historyOffset}`;
    if (orgFilter) url += `&organization_id=${orgFilter}`;
    const events = await api(url);
    const el = document.getElementById('events-history-list');
    const loadMoreBtn = document.getElementById('btn-load-more-history');

    if (events.length === 0 && !append) {
      el.innerHTML = '<p class="muted">No historical events found.</p>';
      loadMoreBtn.classList.add('hidden');
      return;
    }

    const html = events.map(ev => `
      <div class="event-list-item completed ${state.selectedEventId === ev.id ? 'selected' : ''}" data-event-id="${ev.id}">
        <div class="event-list-name">${esc(ev.name)}</div>
        <div class="event-list-meta">${ev.event_date} &middot; ${ev.organization_name || ''}</div>
      </div>
    `).join('');

    if (append) {
      el.insertAdjacentHTML('beforeend', html);
    } else {
      el.innerHTML = html;
    }

    // Show/hide Load More based on whether we got a full batch
    loadMoreBtn.classList.toggle('hidden', events.length < HISTORY_BATCH);

    // Populate org filter dropdown on first load (not append, not filtered)
    if (!append && !orgFilter) {
      const orgs = new Map();
      events.forEach(ev => {
        if (ev.organization_id && ev.organization_name) {
          orgs.set(ev.organization_id, ev.organization_name);
        }
      });
      const sel = document.getElementById('history-org-filter');
      sel.innerHTML = '<option value="">All Orgs</option>';
      for (const [id, name] of orgs) {
        sel.innerHTML += `<option value="${id}">${esc(name)}</option>`;
      }
    }

    // Attach click handlers
    el.querySelectorAll('.event-list-item').forEach(item => {
      item.addEventListener('click', () => {
        state.selectedEventId = Number(item.dataset.eventId);
        loadEventCard(state.selectedEventId);
        loadLeagueHistory();
      });
    });
  } catch (err) { /* silent */ }
}

async function loadEventCard(eventId) {
  try {
    const event = await api(`/api/events/${eventId}`);
    const header = document.getElementById('event-header');
    const resultsView = document.getElementById('event-results-view');
    const cardBuilder = document.getElementById('event-card-builder');
    header.classList.remove('hidden');

    document.getElementById('event-card-name').textContent = event.name;
    document.getElementById('event-card-venue').textContent = event.venue;
    document.getElementById('event-card-date').textContent = event.event_date;
    const statusBadge = document.getElementById('event-card-status');
    statusBadge.textContent = event.status;
    statusBadge.className = `event-status-badge ${event.status.toLowerCase()}`;

    if (event.status === 'Completed') {
      cardBuilder.querySelector('#event-fights-list').classList.add('hidden');
      cardBuilder.querySelector('#event-sim-area').classList.add('hidden');
      document.getElementById('event-projection').classList.add('hidden');
      document.getElementById('pc-container').classList.add('hidden');
      resultsView.classList.remove('hidden');
      renderCompletedEvent(event, resultsView);
    } else {
      resultsView.classList.add('hidden');
      cardBuilder.querySelector('#event-fights-list').classList.remove('hidden');
      renderScheduledFights(event);
      loadEventProjection(eventId);

      const simArea = document.getElementById('event-sim-area');
      const simBtn = document.getElementById('btn-simulate-card');
      const pcBtn = document.getElementById('btn-press-conference');
      if (event.fights.length >= 2) {
        simArea.classList.remove('hidden');
        simBtn.disabled = false;
        pcBtn.classList.toggle('hidden', event.has_press_conference);
      } else {
        simArea.classList.remove('hidden');
        simBtn.disabled = true;
        pcBtn.classList.add('hidden');
      }

      // Show existing press conference if present
      const pcContainer = document.getElementById('pc-container');
      if (event.has_press_conference) {
        const mainFight = event.fights.reduce((a, b) => (a.card_position > b.card_position ? a : b), event.fights[0]);
        if (mainFight && mainFight.press_conference) {
          renderPressConference(mainFight.press_conference, mainFight.fighter_a, mainFight.fighter_b, false);
        } else {
          pcContainer.classList.add('hidden');
        }
      } else {
        pcContainer.classList.add('hidden');
      }
    }
  } catch (err) {
    setStatus('Error loading event: ' + err.message, true);
  }
}

function renderScheduledFights(event) {
  const el = document.getElementById('event-fights-list');
  if (event.fights.length === 0) {
    el.innerHTML = '<p class="muted" style="text-align:center;padding:40px 0">Add fights using the fighter panel &rarr;</p>';
    return;
  }
  el.innerHTML = event.fights.map(f => `
    <div class="event-fight-card ${f.is_title_fight ? 'title-fight' : ''}">
      ${f.is_title_fight ? '<div class="title-banner">TITLE FIGHT</div>' : ''}
      <div class="event-fight-matchup">
        <span class="event-fighter-name">${esc(f.fighter_a.name)}${f.fighter_a.nickname ? ' <span class="nick-inline">"' + esc(f.fighter_a.nickname) + '"</span>' : ''}</span>
        <span class="event-vs">VS</span>
        <span class="event-fighter-name">${esc(f.fighter_b.name)}${f.fighter_b.nickname ? ' <span class="nick-inline">"' + esc(f.fighter_b.nickname) + '"</span>' : ''}</span>
      </div>
      <div class="event-fight-meta">
        <span class="badge wc-badge-color" data-wc="${esc(f.weight_class)}">${esc(f.weight_class)}</span>
        <span class="muted">${esc(f.fighter_a.record)} vs ${esc(f.fighter_b.record)}</span>
      </div>
      <button class="event-fight-remove" data-fight-id="${f.id}" title="Remove fight">&times;</button>
    </div>
  `).join('');

  el.querySelectorAll('.event-fight-remove').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      const fightId = Number(btn.dataset.fightId);
      try {
        await api(`/api/events/${event.id}/fights/${fightId}`, { method: 'DELETE' });
        loadEventCard(event.id);
        loadBookableFighters();
      } catch (err) {
        setStatus('Error: ' + err.message, true);
      }
    });
  });
}

function renderTopDraws(financials) {
  const draws = financials?.top_draws || [];
  if (!draws.length) return '';
  return `
    <div class="event-top-draws-title">Top Draws</div>
    <div class="event-top-draws-chips">
      ${draws.map(d => `
        <span class="event-top-draw-chip">
          ${esc(d.name)}
          <span class="event-top-draw-meta">Hype ${Number(d.hype).toFixed(1)}</span>
        </span>
      `).join('')}
    </div>
  `;
}

function renderTopMatchups(financials) {
  const matchups = financials?.top_matchups || [];
  if (!matchups.length) return '';
  return `
    <div class="event-top-draws-title">Top Matchups</div>
    <div class="event-matchup-list">
      ${matchups.map(m => `
        <div class="event-matchup-item">
          <div class="event-matchup-top">
            <span class="event-matchup-name">${esc(m.matchup)}</span>
            <span class="event-matchup-score">${Number(m.score).toFixed(1)}</span>
          </div>
          <div class="event-matchup-meta">${esc(m.booking_value)} · ${esc(m.competitiveness)} · ${esc(m.star_power)} Star Power</div>
        </div>
      `).join('')}
    </div>
  `;
}

function renderDrivers(financials) {
  const drivers = financials?.performance_drivers || [];
  if (!drivers.length) return '';
  return drivers.map(d => `<div class="event-driver-item">${esc(d)}</div>`).join('');
}

function buildEventEconomicsHtml(financials, fallback = {}) {
  if (!financials && !fallback.totalRevenue && !fallback.gate) return '';

  const revenue = financials?.revenue_breakdown || {
    gate: fallback.gate || 0,
    ppv: fallback.ppv || 0,
    broadcast: fallback.broadcast || 0,
    total: fallback.totalRevenue || 0,
  };
  const costs = financials?.cost_breakdown || {
    fighter_payroll: fallback.fighterPayroll || 0,
    venue_rental: fallback.venueRental || 0,
    total: fallback.totalCosts || fallback.venueRental || 0,
  };
  const profit = fallback.profit ?? financials?.projected_profit ?? (revenue.total - costs.total);
  const topDrawsHtml = renderTopDraws(financials);
  const topMatchupsHtml = renderTopMatchups(financials);
  const driversHtml = renderDrivers(financials);
  const cardQuality = financials?.card_quality;
  const avgHype = financials?.avg_hype;
  const avgPopularity = financials?.avg_popularity;

  return `
    <div class="event-revenue-summary">
      <div class="rev-item"><span class="rev-label">Gate</span><span class="rev-value">${formatCurrency(revenue.gate)}</span></div>
      <div class="rev-item"><span class="rev-label">PPV</span><span class="rev-value">${formatCurrency(revenue.ppv)}</span></div>
      ${revenue.broadcast > 0 ? `<div class="rev-item"><span class="rev-label">Broadcast</span><span class="rev-value">${formatCurrency(revenue.broadcast)}</span></div>` : ''}
      <div class="rev-item"><span class="rev-label">Fighter Payroll</span><span class="rev-value negative">-${formatCurrency(costs.fighter_payroll)}</span></div>
      ${costs.venue_rental > 0 ? `<div class="rev-item"><span class="rev-label">Venue Rental</span><span class="rev-value negative">-${formatCurrency(costs.venue_rental)}</span></div>` : ''}
      <div class="rev-item"><span class="rev-label">Total Revenue</span><span class="rev-value">${formatCurrency(revenue.total)}</span></div>
      <div class="rev-item"><span class="rev-label">Profit</span><span class="rev-value ${profit >= 0 ? 'positive' : 'negative'}">${formatCurrency(profit)}</span></div>
    </div>
    ${(cardQuality !== undefined || avgHype !== undefined || avgPopularity !== undefined) ? `
      <div class="event-econ-meta">
        ${cardQuality !== undefined ? `<div class="event-econ-meta-item"><span class="event-econ-meta-label">Card Quality</span><span class="event-econ-meta-value">${Number(cardQuality).toFixed(1)}</span></div>` : ''}
        ${avgHype !== undefined ? `<div class="event-econ-meta-item"><span class="event-econ-meta-label">Avg Hype</span><span class="event-econ-meta-value">${Number(avgHype).toFixed(1)}</span></div>` : ''}
        ${avgPopularity !== undefined ? `<div class="event-econ-meta-item"><span class="event-econ-meta-label">Avg Popularity</span><span class="event-econ-meta-value">${Number(avgPopularity).toFixed(1)}</span></div>` : ''}
      </div>
    ` : ''}
    ${topDrawsHtml ? `<div class="event-top-draws">${topDrawsHtml}</div>` : ''}
    ${topMatchupsHtml ? `<div class="event-top-draws">${topMatchupsHtml}</div>` : ''}
    ${driversHtml ? `<div class="event-driver-list">${driversHtml}</div>` : ''}
  `;
}

function renderCompletedEvent(event, container) {
  const fights = event.fights || [];
  let html = '<div class="completed-fights">';
  for (const f of fights) {
    const isWinnerA = f.winner_id === f.fighter_a.id;
    const winnerName = isWinnerA ? f.fighter_a.name : f.fighter_b.name;
    const methodClass = (f.method || '').includes('KO') ? 'ko' : (f.method || '').includes('Sub') ? 'sub' : 'dec';
    html += `
      <div class="result-fight-card ${f.is_title_fight ? 'title-fight' : ''}">
        ${f.is_title_fight ? '<div class="title-banner gold">TITLE FIGHT</div>' : ''}
        <div class="result-matchup">
          <span class="result-fighter ${isWinnerA ? 'winner' : 'loser'}">${esc(f.fighter_a.name)}</span>
          <span class="result-vs">VS</span>
          <span class="result-fighter ${!isWinnerA ? 'winner' : 'loser'}">${esc(f.fighter_b.name)}</span>
        </div>
        <div class="result-details">
          <span class="method-badge ${methodClass}">${esc(f.method || '')}</span>
          <span class="muted">R${f.round_ended || '?'} ${esc(f.time_ended || '')}</span>
        </div>
        ${f.narrative ? `<div class="result-narrative">${esc(f.narrative)}</div>` : ''}
      </div>
    `;
  }
  html += '</div>';

  // Only show attendance/revenue for player-org events (historical events have zero data)
  if (event.tickets_sold > 0 || event.gate_revenue > 0) {
    // Sellout banner
    if (event.tickets_sold >= event.venue_capacity) {
      html += '<div class="sellout-banner">SELLOUT!</div>';
    }
    // Attendance
    const fillPct = event.venue_capacity > 0 ? (event.tickets_sold / event.venue_capacity * 100).toFixed(0) : 0;
    html += `<div class="event-attendance">Attendance: ${event.tickets_sold.toLocaleString()} / ${event.venue_capacity.toLocaleString()} (${fillPct}%)</div>`;
    html += buildEventEconomicsHtml(event.financials, {
      gate: event.gate_revenue,
      ppv: event.ppv_buys * 45,
      broadcast: event.broadcast_revenue,
      venueRental: event.venue_rental_cost,
      totalRevenue: event.total_revenue,
    });
  }
  container.innerHTML = html;
}

async function loadEventProjection(eventId) {
  try {
    const proj = await api(`/api/events/${eventId}/projection`);
    const el = document.getElementById('event-projection');
    if (proj.fight_count === 0) {
      el.classList.add('hidden');
      return;
    }
    el.classList.remove('hidden');
    document.getElementById('proj-gate').textContent = formatCurrency(proj.gate_projection);
    document.getElementById('proj-ppv').textContent = formatCurrency(proj.ppv_projection);
    document.getElementById('proj-costs').textContent = formatCurrency(proj.total_costs);
    document.getElementById('proj-venue-cost').textContent = formatCurrency(proj.venue_rental_cost);
    document.getElementById('proj-fighter-payroll').textContent =
      formatCurrency(proj.financials?.cost_breakdown?.fighter_payroll || 0);
    document.getElementById('proj-card-quality').textContent =
      proj.financials ? Number(proj.financials.card_quality || 0).toFixed(1) : '0.0';

    // Attendance
    const fillPct = proj.fill_pct || 0;
    document.getElementById('proj-attendance').textContent =
      `${(proj.est_tickets_sold || 0).toLocaleString()} / ${(proj.venue_capacity || 0).toLocaleString()} (${fillPct.toFixed(0)}%)`;

    // Broadcast
    const broadcastItem = document.getElementById('proj-broadcast-item');
    if (proj.broadcast_projection > 0) {
      broadcastItem.style.display = '';
      document.getElementById('proj-broadcast').textContent = formatCurrency(proj.broadcast_projection);
    } else {
      broadcastItem.style.display = 'none';
    }

    const profitEl = document.getElementById('proj-profit');
    profitEl.textContent = formatCurrency(proj.projected_profit);
    profitEl.className = 'proj-value ' + (proj.projected_profit >= 0 ? 'positive' : 'negative');

    const topDrawsEl = document.getElementById('proj-top-draws');
    const topDrawsHtml = renderTopDraws(proj.financials);
    topDrawsEl.innerHTML = topDrawsHtml;
    topDrawsEl.classList.toggle('hidden', !topDrawsHtml);

    const topMatchupsEl = document.getElementById('proj-top-matchups');
    const topMatchupsHtml = renderTopMatchups(proj.financials);
    topMatchupsEl.innerHTML = topMatchupsHtml;
    topMatchupsEl.classList.toggle('hidden', !topMatchupsHtml);

    const driversEl = document.getElementById('proj-drivers');
    const driversHtml = renderDrivers(proj.financials);
    driversEl.innerHTML = driversHtml;
    driversEl.classList.toggle('hidden', !driversHtml);
  } catch (err) { /* silent */ }
}

// Fighter Pool
async function loadBookableFighters() {
  try {
    state.bookableFighters = await api('/api/events/bookable-fighters');
    renderFighterPool();
    loadBookingRecommendations();
  } catch (err) { /* silent */ }
}

async function loadBookingRecommendations() {
  const el = document.getElementById('booking-recommendations');
  if (!el) return;
  try {
    const data = await api('/api/events/recommendations');
    if (!window.MarketUi?.renderBookingRecommendations) {
      el.classList.add('hidden');
      return;
    }
    const html = window.MarketUi.renderBookingRecommendations(data);
    el.innerHTML = html;
    el.classList.toggle('hidden', !html);
  } catch (err) {
    el.classList.add('hidden');
  }
}

function renderFighterPool() {
  const el = document.getElementById('pool-fighters');
  let fighters = state.bookableFighters;
  if (state.poolWc) fighters = fighters.filter(f => f.weight_class === state.poolWc);
  if (state.poolFilter) {
    const q = state.poolFilter.toLowerCase();
    fighters = fighters.filter(f => f.name.toLowerCase().includes(q));
  }
  if (fighters.length === 0) {
    el.innerHTML = '<p class="muted" style="padding:12px">No available fighters.</p>';
    return;
  }
  el.innerHTML = fighters.map(f => {
    const isSelA = state.selectedFighterA === f.id;
    const isSelB = state.selectedFighterB === f.id;
    const cutBadge = f.cut_severity && f.cut_severity !== 'easy'
      ? `<span class="cut-badge cut-${f.cut_severity}">${f.cut_severity === 'moderate' ? 'MOD CUT' : f.cut_severity === 'severe' ? 'HARD CUT' : 'EXTREME CUT'}</span>`
      : '';
    return `
      <div class="pool-fighter-card ${isSelA || isSelB ? 'selected' : ''}" data-fighter-id="${f.id}" data-wc="${esc(f.weight_class)}">
        <div class="pool-fighter-top">
          <span class="pool-fighter-name">${esc(f.name)}</span>
          ${cutBadge}
          <span class="pool-ovr-badge">${f.overall}</span>
        </div>
        <div class="pool-fighter-meta">
          <span>${esc(f.record)}</span>
          <span class="badge wc-badge-color" data-wc="${esc(f.weight_class)}" style="font-size:10px">${esc(f.weight_class)}</span>
          ${f.days_since_last_fight < 999 ? `<span class="muted">${f.days_since_last_fight}d ago</span>` : ''}
        </div>
      </div>
    `;
  }).join('');

  el.querySelectorAll('.pool-fighter-card').forEach(card => {
    card.addEventListener('click', () => toggleFighterSelection(Number(card.dataset.fighterId)));
  });
}

function toggleFighterSelection(fighterId) {
  if (state.selectedFighterA === fighterId) {
    state.selectedFighterA = null;
  } else if (state.selectedFighterB === fighterId) {
    state.selectedFighterB = null;
  } else if (!state.selectedFighterA) {
    state.selectedFighterA = fighterId;
  } else if (!state.selectedFighterB) {
    state.selectedFighterB = fighterId;
  } else {
    // Both selected, replace B
    state.selectedFighterB = fighterId;
  }
  renderFighterPool();
  updateMatchupButton();
  loadMatchupCompare();
}

function updateMatchupButton() {
  const area = document.getElementById('pool-matchup-area');
  if (state.selectedFighterA && state.selectedFighterB) {
    const fa = state.bookableFighters.find(f => f.id === state.selectedFighterA);
    const fb = state.bookableFighters.find(f => f.id === state.selectedFighterB);
    if (fa && fb && fa.weight_class === fb.weight_class) {
      area.classList.remove('hidden');
      return;
    }
  }
  area.classList.add('hidden');
}

async function addMatchup() {
  if (!state.selectedEventId || !state.selectedFighterA || !state.selectedFighterB) return;
  const isTitleFight = document.getElementById('pool-title-check').checked;
  try {
    const result = await api(`/api/events/${state.selectedEventId}/add-fight`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        fighter_a_id: state.selectedFighterA,
        fighter_b_id: state.selectedFighterB,
        is_title_fight: isTitleFight,
      }),
    });
    if (result.error) {
      setStatus(result.error, true);
      return;
    }
    state.selectedFighterA = null;
    state.selectedFighterB = null;
    state.matchupCompareExpanded = false;
    document.getElementById('pool-title-check').checked = false;
    document.getElementById('pool-matchup-area').classList.add('hidden');
    document.getElementById('pool-compare').classList.add('hidden');
    document.getElementById('pool-compare').innerHTML = '';
    loadEventCard(state.selectedEventId);
    loadBookableFighters();
    setStatus('Fight added to card.');
  } catch (err) {
    setStatus('Error: ' + err.message, true);
  }
}

// Create Event Modal
async function openCreateEventModal() {
  const overlay = document.getElementById('modal-overlay');
  overlay.classList.remove('hidden');
  document.getElementById('modal-event-name').value = '';
  // Populate venues
  try {
    const venues = await api('/api/events/venues');
    const sel = document.getElementById('modal-event-venue');
    sel.innerHTML = venues.map(v => {
      const locked = v.locked;
      const label = locked
        ? `[LOCKED] ${esc(v.name)} — ${esc(v.locked_reason)}`
        : `${esc(v.name)} (${v.capacity.toLocaleString()} cap, ${formatCurrency(v.rental_cost)} rental)`;
      return `<option value="${esc(v.name)}" ${locked ? 'disabled' : ''}>${label}</option>`;
    }).join('');
  } catch (err) { /* silent */ }
  // Set min date to game date
  if (state.gameDate) {
    const d = new Date(state.gameDate + 'T00:00:00');
    d.setDate(d.getDate() + 1);
    document.getElementById('modal-event-date').min = d.toISOString().split('T')[0];
    document.getElementById('modal-event-date').value = d.toISOString().split('T')[0];
  }
}

function closeModal() {
  document.getElementById('modal-overlay').classList.add('hidden');
}

async function createEvent() {
  const name = document.getElementById('modal-event-name').value.trim();
  const venue = document.getElementById('modal-event-venue').value;
  const eventDate = document.getElementById('modal-event-date').value;
  if (!name) { setStatus('Event name is required.', true); return; }
  if (!eventDate) { setStatus('Event date is required.', true); return; }
  try {
    const result = await api('/api/events/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, venue, event_date: eventDate }),
    });
    if (result.error) {
      setStatus(result.error, true);
      return;
    }
    closeModal();
    state.selectedEventId = result.id;
    loadEventsView();
    setStatus(`Event "${name}" created.`);
  } catch (err) {
    setStatus('Error: ' + err.message, true);
  }
}

// Press Conference
async function holdPressConference() {
  if (!state.selectedEventId) return;
  const btn = document.getElementById('btn-press-conference');
  btn.disabled = true;
  btn.textContent = 'Setting up...';
  try {
    const result = await api(`/api/events/${state.selectedEventId}/press-conference`, { method: 'POST' });
    if (result.error) {
      setStatus(result.error, true);
      btn.disabled = false;
      btn.textContent = 'Hold Press Conference';
      return;
    }
    btn.classList.add('hidden');
    renderPressConference(result.press_conference, result.fighter_a, result.fighter_b, true);
    loadEventProjection(state.selectedEventId);
    setStatus('Press conference held! Hype generated.');
  } catch (err) {
    setStatus('Error: ' + err.message, true);
    btn.disabled = false;
    btn.textContent = 'Hold Press Conference';
  }
}

function renderPressConference(pc, fighterA, fighterB, animate) {
  const container = document.getElementById('pc-container');
  const exchangesEl = document.getElementById('pc-exchanges');
  const hypeEl = document.getElementById('pc-hype-result');
  container.classList.remove('hidden');
  exchangesEl.innerHTML = '';

  const exchanges = pc.exchanges || [];
  const nameA = fighterA.name || 'Fighter A';
  const nameB = fighterB.name || 'Fighter B';

  if (animate) {
    let i = 0;
    const showNext = () => {
      if (i >= exchanges.length) {
        // Show hype results
        hypeEl.classList.remove('hidden');
        hypeEl.innerHTML = `
          <div class="pc-hype-bar">
            <span class="pc-hype-label">${esc(nameA)}</span>
            <div class="pc-hype-fill" style="width:${Math.min(100, (fighterA.hype || 0))}%">${fighterA.hype || 0}</div>
          </div>
          <div class="pc-hype-bar">
            <span class="pc-hype-label">${esc(nameB)}</span>
            <div class="pc-hype-fill" style="width:${Math.min(100, (fighterB.hype || 0))}%">${fighterB.hype || 0}</div>
          </div>
          <div class="pc-ppv-boost">+${pc.ppv_boost || 0} PPV buys from press conference</div>
        `;
        return;
      }
      const ex = exchanges[i];
      const div = document.createElement('div');
      div.className = 'pc-exchange pc-fade-in';
      div.innerHTML = `
        <div class="pc-quote pc-quote-a"><strong>${esc(nameA)}:</strong> "${esc(ex.fighter_a)}"</div>
        <div class="pc-quote pc-quote-b"><strong>${esc(nameB)}:</strong> "${esc(ex.fighter_b)}"</div>
      `;
      exchangesEl.appendChild(div);
      i++;
      setTimeout(showNext, 800);
    };
    showNext();
  } else {
    // Static render (loading existing press conference)
    for (const ex of exchanges) {
      exchangesEl.innerHTML += `
        <div class="pc-exchange">
          <div class="pc-quote pc-quote-a"><strong>${esc(nameA)}:</strong> "${esc(ex.fighter_a)}"</div>
          <div class="pc-quote pc-quote-b"><strong>${esc(nameB)}:</strong> "${esc(ex.fighter_b)}"</div>
        </div>
      `;
    }
    hypeEl.classList.remove('hidden');
    hypeEl.innerHTML = `
      <div class="pc-ppv-boost">+${pc.ppv_boost || 0} PPV buys from press conference</div>
    `;
  }
}

// Simulate Event
function confirmSimulate() {
  document.getElementById('confirm-overlay').classList.remove('hidden');
}

function cancelSimulate() {
  document.getElementById('confirm-overlay').classList.add('hidden');
}

async function simulateCard() {
  document.getElementById('confirm-overlay').classList.add('hidden');
  if (!state.selectedEventId) return;

  const btn = document.getElementById('btn-simulate-card');
  btn.disabled = true;
  btn.textContent = 'Simulating...';
  setStatus('Simulating event...');

  try {
    const { task_id } = await api(`/api/events/${state.selectedEventId}/simulate`, { method: 'POST' });
    pollTask(
      task_id,
      result => {
        btn.textContent = 'Simulate Event';
        setStatus(`${result.event_name} simulated \u2014 ${result.fights_simulated} fights.`);
        showAnimatedResults(result);
        loadScheduledEvents();
        loadCompletedEvents();
        loadBookableFighters();
        loadGameDate();
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

function buildScorecardHtml(f) {
  if (!f.judge_breakdown || f.judge_breakdown.length === 0) return '';
  let rows = f.judge_breakdown.map(j => {
    const aWin = j.score_a > j.score_b;
    return `<tr>
      <td>${esc(j.judge)}</td>
      <td class="${aWin ? 'sc-winner' : ''}">${j.score_a}</td>
      <td class="${!aWin ? 'sc-winner' : ''}">${j.score_b}</td>
    </tr>`;
  }).join('');
  return `<div class="scorecard-table"><table>
    <thead><tr><th>Judge</th><th>${esc(f.fighter_a)}</th><th>${esc(f.fighter_b)}</th></tr></thead>
    <tbody>${rows}</tbody>
  </table></div>`;
}

function buildRoundStatsHtml(f) {
  if (!f.round_stats || f.round_stats.length === 0) return '';
  const rounds = f.round_stats;
  const nameA = rounds[0].fighters[0].name;
  const nameB = rounds[0].fighters[1].name;

  // Round tabs
  let tabs = '<div class="rviz-rounds">';
  for (let i = 0; i < rounds.length; i++) {
    const isFinish = (i === rounds.length - 1 && f.round === rounds.length && f.method && !f.method.includes('Decision'));
    tabs += `<div class="rviz-round-tab${i === 0 ? ' rviz-active' : ''}${isFinish ? ' rviz-finish' : ''}" data-round="${i}">R${i + 1}</div>`;
  }
  tabs += '</div>';

  // Panels for each round
  let panels = '';
  for (let i = 0; i < rounds.length; i++) {
    const rd = rounds[i];
    const fa = rd.fighters[0];
    const fb = rd.fighters[1];

    // Momentum: convert from [-1,1] per fighter to a tug-of-war percentage
    // Positive momentum for A shifts bar left (more blue), positive for B shifts right (more red)
    const momDiff = fa.momentum - fb.momentum;  // range -2 to 2
    const momPctA = Math.round(Math.max(5, Math.min(95, 50 + momDiff * 25)));

    // Stat comparison helper
    function statBar(label, valA, valB, icon) {
      const total = (valA + valB) || 1;
      const pctA = Math.round((valA / total) * 100);
      const pctB = 100 - pctA;
      return `<div class="rviz-stat-row">
        <span class="rviz-val rviz-val-a">${valA}</span>
        <div class="rviz-bar-track"><div class="rviz-bar rviz-bar-a" style="width:${pctA}%"></div></div>
        <span class="rviz-stat-label">${icon ? icon + ' ' : ''}${label}</span>
        <div class="rviz-bar-track"><div class="rviz-bar rviz-bar-b" style="width:${pctB}%"></div></div>
        <span class="rviz-val rviz-val-b">${valB}</span>
      </div>`;
    }

    // Stamina level
    function stamLevel(val) {
      if (val >= 70) return 'high';
      if (val >= 40) return 'mid';
      return 'low';
    }

    // Total damage dealt this round
    const dmgA = Math.round(fa.standing_damage_dealt + fa.ground_damage_dealt);
    const dmgB = Math.round(fb.standing_damage_dealt + fb.ground_damage_dealt);

    // Events
    let eventsHtml = '';
    if (rd.events && rd.events.length > 0) {
      eventsHtml = '<div class="rviz-events">';
      for (const evt of rd.events) {
        let icon = '⚡', cls = 'sig';
        const el = evt.toLowerCase();
        if (el.includes('knockdown') || el.includes('drops')) { icon = '💀'; cls = 'kd'; }
        else if (el.includes('submits') || el.includes('submission') || el.includes('locks')) { icon = '🔒'; cls = 'sub'; }
        else if (el.includes('drags') || el.includes('takedown')) { icon = '⬇'; cls = 'td'; }
        else if (el.includes('escapes')) { icon = '🔓'; cls = 'td'; }
        else if (el.includes('stops') || el.includes('finishes')) { icon = '🏆'; cls = 'kd'; }
        eventsHtml += `<div class="rviz-event"><span class="rviz-event-icon rviz-event-${cls}">${icon}</span><span class="rviz-event-text">${esc(evt)}</span></div>`;
      }
      eventsHtml += '</div>';
    }

    panels += `<div class="rviz-panel${i === 0 ? ' rviz-visible' : ''}" data-round="${i}">
      <div class="rviz-section-label">MOMENTUM</div>
      <div class="rviz-momentum-track">
        <div class="rviz-momentum-fill" style="width:${momPctA}%"></div>
        <div class="rviz-momentum-center"></div>
      </div>
      <div class="rviz-momentum-names">
        <span class="rviz-name-a">${esc(nameA)}</span>
        <span class="rviz-name-b">${esc(nameB)}</span>
      </div>

      <div class="rviz-section-label" style="margin-top:8px">ROUND STATS</div>
      ${statBar('Sig. Strikes', fa.sig_strikes, fb.sig_strikes, '')}
      ${statBar('Damage', dmgA, dmgB, '')}
      ${statBar('Takedowns', fa.takedowns, fb.takedowns, '')}
      ${fa.knockdowns + fb.knockdowns > 0 ? statBar('Knockdowns', fa.knockdowns, fb.knockdowns, '') : ''}

      <div class="rviz-section-label" style="margin-top:8px">STAMINA</div>
      <div class="rviz-stamina-row">
        <span class="rviz-stamina-label rviz-name-a">${Math.round(fa.stamina)}%</span>
        <div class="rviz-stamina-track"><div class="rviz-stamina-bar rviz-stamina-a" data-level="${stamLevel(fa.stamina)}" style="width:${fa.stamina}%"></div></div>
        <div class="rviz-stamina-track"><div class="rviz-stamina-bar rviz-stamina-b" data-level="${stamLevel(fb.stamina)}" style="width:${fb.stamina}%"></div></div>
        <span class="rviz-stamina-label rviz-name-b">${Math.round(fb.stamina)}%</span>
      </div>

      ${eventsHtml}
    </div>`;
  }

  return `<div class="rviz-container">
    ${tabs}
    ${panels}
  </div>`;
}

function initRoundStatsTabHandlers(container) {
  container.querySelectorAll('.rviz-container').forEach(rviz => {
    const tabs = rviz.querySelectorAll('.rviz-round-tab');
    const panels = rviz.querySelectorAll('.rviz-panel');
    tabs.forEach(tab => {
      tab.addEventListener('click', () => {
        const rd = tab.dataset.round;
        tabs.forEach(t => t.classList.remove('rviz-active'));
        panels.forEach(p => p.classList.remove('rviz-visible'));
        tab.classList.add('rviz-active');
        const panel = rviz.querySelector(`.rviz-panel[data-round="${rd}"]`);
        if (panel) panel.classList.add('rviz-visible');
      });
    });
  });
}

async function showAnimatedResults(result) {
  const header = document.getElementById('event-header');
  const cardBuilder = document.getElementById('event-card-builder');
  const resultsView = document.getElementById('event-results-view');

  // Hide card builder parts
  document.getElementById('event-fights-list').classList.add('hidden');
  document.getElementById('event-sim-area').classList.add('hidden');
  document.getElementById('event-projection').classList.add('hidden');

  // Update status badge
  const statusBadge = document.getElementById('event-card-status');
  statusBadge.textContent = 'Completed';
  statusBadge.className = 'event-status-badge completed';

  resultsView.classList.remove('hidden');
  resultsView.innerHTML = '<div class="sim-pulse">Simulating ' + esc(result.event_name) + '...</div>';

  let skipRequested = false;
  const skipHandler = () => { skipRequested = true; };
  resultsView.addEventListener('click', skipHandler);

  await sleep(1000);
  if (skipRequested) { renderFinalResults(result, resultsView); resultsView.removeEventListener('click', skipHandler); return; }

  let html = '';
  resultsView.innerHTML = '<div class="completed-fights" id="anim-fights"></div>';
  const container = document.getElementById('anim-fights');

  for (let i = 0; i < result.fights.length; i++) {
    if (skipRequested) break;
    const f = result.fights[i];
    const methodClass = (f.method || '').includes('KO') ? 'ko' : (f.method || '').includes('Sub') ? 'sub' : 'dec';
    const isWinnerA = f.winner_id === f.fighter_a_id;

    if (f.is_title_fight && !skipRequested) {
      const banner = document.createElement('div');
      banner.className = 'title-pulse';
      banner.textContent = 'TITLE FIGHT';
      container.appendChild(banner);
      await sleep(2000);
      if (skipRequested) break;
      banner.remove();
    }

    const card = document.createElement('div');
    card.className = 'result-fight-card anim-enter';
    const missedHtml = f.missed_weight ? f.missed_weight.map(m => `<div class="missed-weight-warning">MISSED WEIGHT: ${esc(m.fighter)} (fined ${formatCurrency(m.fine)})</div>`).join('') : '';
    const scorecardHtml = f.judge_breakdown ? buildScorecardHtml(f) : '';
    const roundStatsHtml = buildRoundStatsHtml(f);
    card.innerHTML = `
      ${f.is_title_fight ? '<div class="title-banner gold">TITLE FIGHT</div>' : ''}
      ${missedHtml}
      <div class="result-matchup">
        <span class="result-fighter ${isWinnerA ? 'winner' : 'loser'}">${esc(f.fighter_a)}</span>
        <span class="result-vs">VS</span>
        <span class="result-fighter ${!isWinnerA ? 'winner' : 'loser'}">${esc(f.fighter_b)}</span>
      </div>
      <div class="result-details">
        <span class="method-badge ${methodClass} fade-in">${esc(f.method || '')}</span>
        <span class="muted">R${f.round || '?'} ${esc(f.time || '')}</span>
      </div>
      <div class="result-narrative typewriter" data-text="${esc(f.narrative || '')}"></div>
      ${scorecardHtml}
      ${roundStatsHtml}
    `;
    container.appendChild(card);
    initRoundStatsTabHandlers(card);

    // Trigger enter animation
    requestAnimationFrame(() => card.classList.add('entered'));

    // Typewriter effect
    if (!skipRequested && f.narrative) {
      const tw = card.querySelector('.typewriter');
      const text = f.narrative;
      for (let c = 0; c <= text.length && !skipRequested; c++) {
        tw.textContent = text.slice(0, c);
        await sleep(20);
      }
    }

    if (!skipRequested) await sleep(1200);
  }

  if (skipRequested) {
    renderFinalResults(result, resultsView);
  } else {
    // Sellout banner
    if (result.is_sellout) {
      const sellout = document.createElement('div');
      sellout.className = 'sellout-banner anim-enter';
      sellout.textContent = 'SELLOUT!';
      container.parentElement.appendChild(sellout);
      requestAnimationFrame(() => sellout.classList.add('entered'));
      await sleep(600);
    }
    // Attendance
    if (result.tickets_sold) {
      const att = document.createElement('div');
      att.className = 'event-attendance anim-enter';
      att.textContent = `Attendance: ${result.tickets_sold.toLocaleString()} / ${result.venue_capacity.toLocaleString()} (${result.fill_pct}%)`;
      container.parentElement.appendChild(att);
      requestAnimationFrame(() => att.classList.add('entered'));
    }
    // Add revenue summary
    const summary = document.createElement('div');
    summary.className = 'anim-enter';
    summary.innerHTML = buildEventEconomicsHtml(result.financials, {
      gate: result.gate_revenue,
      ppv: result.ppv_revenue,
      broadcast: result.broadcast_revenue,
      venueRental: result.venue_rental_cost,
      totalRevenue: result.total_revenue,
      totalCosts: result.total_costs,
      profit: result.profit,
    });
    container.parentElement.appendChild(summary);
    requestAnimationFrame(() => summary.classList.add('entered'));
  }

  resultsView.removeEventListener('click', skipHandler);
}

function renderFinalResults(result, container) {
  let html = '<div class="completed-fights">';
  for (const f of result.fights) {
    const methodClass = (f.method || '').includes('KO') ? 'ko' : (f.method || '').includes('Sub') ? 'sub' : 'dec';
    const isWinnerA = f.winner_id === f.fighter_a_id;
    const missedHtml = f.missed_weight ? f.missed_weight.map(m => `<div class="missed-weight-warning">MISSED WEIGHT: ${esc(m.fighter)} (fined ${formatCurrency(m.fine)})</div>`).join('') : '';
    const scorecardHtml = f.judge_breakdown ? buildScorecardHtml(f) : '';
    const roundStatsHtml = buildRoundStatsHtml(f);
    html += `
      <div class="result-fight-card entered ${f.is_title_fight ? 'title-fight' : ''}">
        ${f.is_title_fight ? '<div class="title-banner gold">TITLE FIGHT</div>' : ''}
        ${missedHtml}
        <div class="result-matchup">
          <span class="result-fighter ${isWinnerA ? 'winner' : 'loser'}">${esc(f.fighter_a)}</span>
          <span class="result-vs">VS</span>
          <span class="result-fighter ${!isWinnerA ? 'winner' : 'loser'}">${esc(f.fighter_b)}</span>
        </div>
        <div class="result-details">
          <span class="method-badge ${methodClass}">${esc(f.method || '')}</span>
          <span class="muted">R${f.round || '?'} ${esc(f.time || '')}</span>
        </div>
        ${f.narrative ? `<div class="result-narrative">${esc(f.narrative)}</div>` : ''}
        ${scorecardHtml}
        ${roundStatsHtml}
      </div>
    `;
  }
  html += '</div>';
  if (result.is_sellout) {
    html += '<div class="sellout-banner">SELLOUT!</div>';
  }
  if (result.tickets_sold) {
    html += `<div class="event-attendance">Attendance: ${result.tickets_sold.toLocaleString()} / ${result.venue_capacity.toLocaleString()} (${result.fill_pct}%)</div>`;
  }
  html += buildEventEconomicsHtml(result.financials, {
    gate: result.gate_revenue,
    ppv: result.ppv_revenue,
    broadcast: result.broadcast_revenue,
    venueRental: result.venue_rental_cost,
    totalRevenue: result.total_revenue,
    totalCosts: result.total_costs,
    profit: result.profit,
  });
  container.innerHTML = html;
  initRoundStatsTabHandlers(container);
}

function sleep(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }

// ---------------------------------------------------------------------------
// Broadcast / TV Deals View
// ---------------------------------------------------------------------------

async function loadBroadcastView() {
  try {
    const [activeData, availData] = await Promise.all([
      api('/api/broadcast/active'),
      api('/api/broadcast/available'),
    ]);

    // Active deal section
    const activeSection = document.getElementById('broadcast-active-section');
    if (activeData.deal) {
      const d = activeData.deal;
      const warnClass = d.compliance_warnings > 0 ? 'broadcast-dash-warn' : '';
      activeSection.innerHTML = `
        <div class="deal-active-card">
          <div class="deal-active-header">
            <div class="deal-active-tier">${esc(d.tier)}</div>
            <div class="deal-active-network">${esc(d.network_name)}</div>
          </div>
          <div class="deal-active-details">
            <div class="deal-detail"><span class="deal-detail-label">Fee/Event</span><span>${formatCurrency(d.fee_per_event)}</span></div>
            <div class="deal-detail"><span class="deal-detail-label">PPV Multiplier</span><span>${d.ppv_multiplier}x</span></div>
            <div class="deal-detail"><span class="deal-detail-label">Months Left</span><span>${d.months_remaining}</span></div>
            <div class="deal-detail"><span class="deal-detail-label">Events Delivered</span><span>${d.events_delivered}</span></div>
            <div class="deal-detail"><span class="deal-detail-label">Prestige/Month</span><span>+${d.prestige_per_month}</span></div>
            <div class="deal-detail"><span class="deal-detail-label">On Pace</span><span class="${d.on_pace ? 'positive' : 'negative'}">${d.on_pace ? 'Yes' : 'Behind!'}</span></div>
            ${d.compliance_warnings > 0 ? `<div class="deal-detail ${warnClass}"><span class="deal-detail-label">Warnings</span><span>${d.compliance_warnings}/2</span></div>` : ''}
          </div>
        </div>
      `;
    } else {
      activeSection.innerHTML = '<p class="muted" style="margin-bottom:8px">No active broadcast deal. Negotiate one below to earn extra revenue per event.</p>';
    }

    // Org stats
    const statsEl = document.getElementById('broadcast-org-stats');
    if (availData.tiers) {
      statsEl.innerHTML = `
        <span>Prestige: <strong>${availData.org_prestige}</strong></span>
        <span>Events (12mo): <strong>${availData.events_last_year}</strong></span>
        <span>Avg Card Quality: <strong>${availData.avg_card_quality}</strong></span>
      `;
    }

    // Tier cards
    const tiersEl = document.getElementById('broadcast-tiers');
    if (availData.tiers) {
      tiersEl.innerHTML = availData.tiers.map(t => `
        <div class="deal-tier-card ${!t.eligible ? 'locked' : ''}">
          <div class="deal-tier-name">${esc(t.tier)}</div>
          <div class="deal-tier-details">
            <div class="deal-tier-row"><span>Fee/Event</span><span>${formatCurrency(t.fee_per_event)}</span></div>
            <div class="deal-tier-row"><span>PPV Mult</span><span>${t.ppv_multiplier}x</span></div>
            <div class="deal-tier-row"><span>Duration</span><span>${t.duration_months} months</span></div>
            <div class="deal-tier-row"><span>Prestige/Mo</span><span>+${t.prestige_per_month}</span></div>
          </div>
          <div class="deal-requirements">
            <div class="${t.prestige_met ? 'met' : 'unmet'}">Prestige: ${t.min_prestige}+ ${t.prestige_met ? '\u2713' : '\u2717'}</div>
            <div class="${t.events_met ? 'met' : 'unmet'}">Events/yr: ${t.min_events_per_year}+ ${t.events_met ? '\u2713' : '\u2717'}</div>
            <div class="${t.quality_met ? 'met' : 'unmet'}">Card Quality: ${t.min_avg_card_quality}+ ${t.quality_met ? '\u2713' : '\u2717'}</div>
            ${t.already_has_deal ? '<div class="unmet">Already have a deal</div>' : ''}
          </div>
          ${t.eligible ? `<button class="btn btn-primary" style="width:100%;margin-top:8px" onclick="negotiateDeal('${esc(t.tier)}')">Negotiate</button>` : ''}
        </div>
      `).join('');
    }
  } catch (err) {
    setStatus('Error loading broadcast deals: ' + err.message, true);
  }
}

async function negotiateDeal(tier) {
  try {
    const result = await api('/api/broadcast/negotiate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tier }),
    });
    if (result.success) {
      setStatus(result.message);
    } else {
      setStatus(result.message, true);
    }
    loadBroadcastView();
  } catch (err) {
    try {
      const errData = JSON.parse(err.message);
      setStatus(errData.message || 'Negotiation failed.', true);
    } catch (_) {
      setStatus('Error: ' + err.message, true);
    }
    loadBroadcastView();
  }
}

async function loadBroadcastWidget() {
  try {
    const data = await api('/api/broadcast/active');
    const widget = document.getElementById('broadcast-widget');
    const content = document.getElementById('broadcast-widget-content');
    if (data.deal) {
      widget.classList.remove('hidden');
      const d = data.deal;
      content.innerHTML = `
        <div class="broadcast-widget-info">
          <div><strong>${esc(d.network_name)}</strong> (${esc(d.tier)})</div>
          <div class="muted">${d.months_remaining} months left &middot; ${formatCurrency(d.fee_per_event)}/event</div>
          ${!d.on_pace ? '<div class="broadcast-dash-warn">Behind schedule on events!</div>' : ''}
        </div>
      `;
    } else {
      widget.classList.add('hidden');
    }
  } catch (err) { /* silent */ }
}

// ---------------------------------------------------------------------------
// Rival Widget
// ---------------------------------------------------------------------------

async function loadRivalWidget() {
  try {
    const data = await api('/api/rival');
    const widget = document.getElementById('rival-widget');
    const content = document.getElementById('rival-widget-content');
    if (!data.rival) {
      widget.classList.add('hidden');
      return;
    }
    widget.classList.remove('hidden');
    const r = data.rival;
    const playerP = data.player_prestige;
    const maxP = Math.max(playerP, r.prestige, 1);

    // Top fighters list
    const topHtml = r.top_fighters.map(f =>
      `<div class="rival-fighter-row">
        <span class="rival-fighter-name">${esc(f.name)}</span>
        <span class="muted">${esc(f.weight_class)}</span>
        <span class="rival-fighter-ovr">${f.overall} OVR</span>
        <span class="muted">${f.record}</span>
      </div>`
    ).join('');

    // Last event
    const lastEvtHtml = r.last_event
      ? `<div class="rival-last-event">${esc(r.last_event.name)} &middot; ${r.last_event.date} &middot; ${r.last_event.fight_count} fights</div>`
      : '<div class="muted">No events yet</div>';

    // Standings
    const standingsHtml = data.standings.map(s => {
      let cls = 'standing-row';
      if (s.is_player) cls += ' standing-player';
      else if (s.is_rival) cls += ' standing-rival';
      return `<div class="${cls}">
        <span class="standing-name">${esc(s.name)}</span>
        <span class="standing-prestige">${s.prestige}</span>
        <span class="standing-roster muted">${s.roster_count} fighters</span>
      </div>`;
    }).join('');

    content.innerHTML = `
      <div class="rival-header">
        <span class="rival-name">${esc(r.name)}</span>
        <span class="muted">${r.roster_count} fighters</span>
      </div>
      <div class="rival-prestige-compare">
        <div class="rival-bar-row">
          <span class="rival-bar-label">You</span>
          <div class="rival-bar-track">
            <div class="rival-bar-fill player" style="width:${(playerP / maxP * 100).toFixed(1)}%"></div>
          </div>
          <span class="rival-bar-value">${playerP}</span>
        </div>
        <div class="rival-bar-row">
          <span class="rival-bar-label">${esc(r.name)}</span>
          <div class="rival-bar-track">
            <div class="rival-bar-fill rival" style="width:${(r.prestige / maxP * 100).toFixed(1)}%"></div>
          </div>
          <span class="rival-bar-value">${r.prestige}</span>
        </div>
      </div>
      ${window.MarketUi?.renderRivalIntel ? window.MarketUi.renderRivalIntel(r) : ''}
      <div class="rival-section">
        <div class="rival-section-title">Top Fighters</div>
        ${topHtml || '<div class="muted">No fighters</div>'}
      </div>
      <div class="rival-section">
        <div class="rival-section-title">Last Event</div>
        ${lastEvtHtml}
      </div>
      <div class="rival-section">
        <div class="rival-section-title">League Standings</div>
        ${standingsHtml}
      </div>
    `;
  } catch (err) { /* silent */ }
}

// ---------------------------------------------------------------------------
// Development View
// ---------------------------------------------------------------------------

const devState = {
  selectedFighterId: null,
  selectedCampId: null,
  selectedFocus: 'Balanced',
  rosterDev: [],
  camps: [],
};

async function loadDevelopmentView() {
  devState.selectedFighterId = null;
  devState.selectedCampId = null;
  devState.selectedFocus = 'Balanced';
  document.getElementById('dev-manager').classList.add('hidden');
  document.getElementById('dev-empty').classList.remove('hidden');

  try {
    const [roster, camps] = await Promise.all([
      api('/api/development/roster'),
      api('/api/development/camps'),
    ]);
    devState.rosterDev = roster;
    devState.camps = camps;
    renderDevFighterList();
  } catch (err) {
    setStatus('Error loading development: ' + err.message, true);
  }
}

function renderDevFighterList() {
  const el = document.getElementById('dev-fighter-list');
  if (devState.rosterDev.length === 0) {
    el.innerHTML = '<p class="muted">No fighters on roster.</p>';
    return;
  }
  el.innerHTML = devState.rosterDev.map(f => {
    let statusIcon, statusClass;
    if (f.status === 'training') {
      statusIcon = '\u25B2'; statusClass = 'dev-up';
    } else if (f.status === 'declining') {
      statusIcon = '\u25BC'; statusClass = 'dev-down';
    } else {
      statusIcon = '\u2014'; statusClass = 'dev-idle';
    }
    const isSelected = devState.selectedFighterId === f.id;
    return `
      <div class="dev-fighter-card ${isSelected ? 'selected' : ''}" data-fighter-id="${f.id}">
        <div class="dev-card-top">
          <span class="dev-card-name">${esc(f.name)}</span>
          <span class="dev-card-ovr">${f.overall}</span>
        </div>
        <div class="dev-card-mid">
          <span>${f.age}y</span>
          <span class="badge wc-badge-color" data-wc="${esc(f.weight_class)}" style="font-size:10px">${esc(f.weight_class)}</span>
          <span class="dev-status ${statusClass}">${statusIcon}</span>
        </div>
        <div class="dev-card-bottom">
          ${f.camp_name
            ? `<span class="dev-camp-tag">${esc(f.camp_name)}</span><span class="muted">${esc(f.focus)} \xB7 ${f.months_at_camp}mo</span>`
            : '<span class="muted">Unassigned</span>'
          }
        </div>
      </div>
    `;
  }).join('');

  el.querySelectorAll('.dev-fighter-card').forEach(card => {
    card.addEventListener('click', () => selectDevFighter(Number(card.dataset.fighterId)));
  });
}

function selectDevFighter(fighterId) {
  devState.selectedFighterId = fighterId;
  devState.selectedCampId = null;
  devState.selectedFocus = 'Balanced';
  renderDevFighterList();

  const f = devState.rosterDev.find(r => r.id === fighterId);
  if (!f) return;

  document.getElementById('dev-empty').classList.add('hidden');
  document.getElementById('dev-manager').classList.remove('hidden');

  // Header
  document.getElementById('dev-name').textContent = f.name;
  document.getElementById('dev-meta').textContent = `${f.weight_class} \xB7 ${f.style} \xB7 Age ${f.age} \xB7 OVR ${f.overall} \xB7 ${f.record}`;

  // Current assignment
  const assignEl = document.getElementById('dev-current-assignment');
  if (f.camp_name) {
    devState.selectedCampId = devState.camps.find(c => c.name === f.camp_name)?.id || null;
    devState.selectedFocus = f.focus || 'Balanced';
    assignEl.innerHTML = `
      <div class="dev-assign-info">
        <div class="dev-assign-row"><span class="dev-assign-label">Camp</span><span>${esc(f.camp_name)} ${'&#9733;'.repeat(f.camp_tier)}</span></div>
        <div class="dev-assign-row"><span class="dev-assign-label">Focus</span><span>${esc(f.focus)}</span></div>
        <div class="dev-assign-row"><span class="dev-assign-label">Months</span><span>${f.months_at_camp}</span></div>
        <div class="dev-assign-row"><span class="dev-assign-label">Monthly Cost</span><span>${formatCurrency(f.camp_cost)}</span></div>
        <div class="dev-assign-row"><span class="dev-assign-label">Total Spent</span><span>${formatCurrency(f.total_development_spend)}</span></div>
      </div>
      <button class="btn-danger" id="btn-dev-remove" style="margin-top:8px">Remove from Camp</button>
    `;
    document.getElementById('btn-dev-remove').addEventListener('click', () => removeFromCamp(fighterId));
  } else {
    assignEl.innerHTML = '<p class="muted">No camp assigned</p>';
  }

  // Render camps
  renderDevCamps(f);

  // Set focus buttons
  document.querySelectorAll('.focus-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.focus === devState.selectedFocus);
  });

  // Focus hint
  updateFocusHint(f);

  // Load projection if camp selected
  if (devState.selectedCampId) {
    loadDevProjection(fighterId, devState.selectedCampId, devState.selectedFocus);
  } else {
    document.getElementById('dev-projection-section').style.display = 'none';
  }

  // Development history
  const histEl = document.getElementById('dev-history');
  histEl.innerHTML = `
    <div class="dev-assign-info">
      <div class="dev-assign-row"><span class="dev-assign-label">Total Spend</span><span>${formatCurrency(f.total_development_spend)}</span></div>
    </div>
  `;
}

function renderDevCamps(fighter) {
  const el = document.getElementById('dev-camp-grid');
  el.innerHTML = devState.camps.map(c => {
    const isSelected = devState.selectedCampId === c.id;
    const locked = c.locked;
    return `
      <div class="dev-camp-card ${isSelected ? 'selected' : ''} ${locked ? 'locked' : ''}" data-camp-id="${c.id}">
        <div class="dev-camp-top">
          <span class="dev-camp-name">${esc(c.name)}</span>
          <span class="dev-camp-tier">${'&#9733;'.repeat(c.tier)}</span>
        </div>
        <div class="dev-camp-specialty"><span class="badge">${esc(c.specialty)}</span></div>
        <div class="dev-camp-info">
          <span>${formatCurrency(c.cost_per_month)}/mo</span>
          <span>${c.available}/${c.slots} slots</span>
        </div>
        ${locked ? `<div class="dev-camp-lock">Requires ${c.prestige_required} prestige</div>` : ''}
      </div>
    `;
  }).join('');

  el.querySelectorAll('.dev-camp-card:not(.locked)').forEach(card => {
    card.addEventListener('click', () => {
      devState.selectedCampId = Number(card.dataset.campId);
      renderDevCamps(fighter);
      loadDevProjection(devState.selectedFighterId, devState.selectedCampId, devState.selectedFocus);
    });
  });
}

function updateFocusHint(fighter) {
  const hintEl = document.getElementById('dev-focus-hint');
  const attrs = [
    { name: 'Striking', val: fighter.striking },
    { name: 'Grappling', val: fighter.grappling },
    { name: 'Wrestling', val: fighter.wrestling },
    { name: 'Cardio', val: fighter.cardio },
  ];
  attrs.sort((a, b) => a.val - b.val);
  hintEl.textContent = `Recommended: ${attrs[0].name} (lowest at ${attrs[0].val})`;
}

async function loadDevProjection(fighterId, campId, focus) {
  const section = document.getElementById('dev-projection-section');
  const tbody = document.getElementById('dev-projection-tbody');

  try {
    const data = await api(`/api/development/projection?fighter_id=${fighterId}&camp_id=${campId}&focus=${focus}&months=12`);
    if (data.error) {
      section.style.display = 'none';
      return;
    }

    section.style.display = '';
    const now = data.now;
    const p3 = data.projections['3'] || {};
    const p6 = data.projections['6'] || {};
    const p12 = data.projections['12'] || {};

    const labels = { striking: 'STR', grappling: 'GRP', wrestling: 'WR', cardio: 'CRD', chin: 'CHN', speed: 'SPD', overall: 'OVR' };
    const keys = ['striking', 'grappling', 'wrestling', 'cardio', 'chin', 'speed', 'overall'];

    tbody.innerHTML = keys.map(k => {
      const n = now[k];
      const v3 = p3[k] ?? n;
      const v6 = p6[k] ?? n;
      const v12 = p12[k] ?? n;
      return `
        <tr class="${k === 'overall' ? 'dev-proj-ovr' : ''}">
          <td>${labels[k]}</td>
          <td>${n}</td>
          <td class="${v3 > n ? 'dev-gain' : ''}">${v3}</td>
          <td class="${v6 > n ? 'dev-gain' : ''}">${v6}</td>
          <td class="${v12 > n ? 'dev-gain' : ''}">${v12}</td>
        </tr>
      `;
    }).join('');
  } catch (err) {
    section.style.display = 'none';
  }
}

async function assignToCamp() {
  if (!devState.selectedFighterId || !devState.selectedCampId) {
    setStatus('Select a camp first.', true);
    return;
  }
  try {
    const result = await api('/api/development/assign', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        fighter_id: devState.selectedFighterId,
        camp_id: devState.selectedCampId,
        focus: devState.selectedFocus,
      }),
    });
    if (result.error) {
      setStatus(result.error, true);
      return;
    }
    setStatus(result.message);
    // Reload development view
    const fighterId = devState.selectedFighterId;
    const [roster, camps] = await Promise.all([
      api('/api/development/roster'),
      api('/api/development/camps'),
    ]);
    devState.rosterDev = roster;
    devState.camps = camps;
    renderDevFighterList();
    selectDevFighter(fighterId);
  } catch (err) {
    setStatus('Error: ' + err.message, true);
  }
}

async function removeFromCamp(fighterId) {
  try {
    const result = await api('/api/development/remove', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ fighter_id: fighterId }),
    });
    if (result.error) {
      setStatus(result.error, true);
      return;
    }
    setStatus(result.message);
    const [roster, camps] = await Promise.all([
      api('/api/development/roster'),
      api('/api/development/camps'),
    ]);
    devState.rosterDev = roster;
    devState.camps = camps;
    renderDevFighterList();
    selectDevFighter(fighterId);
  } catch (err) {
    setStatus('Error: ' + err.message, true);
  }
}

// ---------------------------------------------------------------------------
// Advance Month
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Sponsorship Widget & Panel
// ---------------------------------------------------------------------------

async function loadSponsorshipWidget() {
  try {
    const data = await api('/api/sponsorships/summary');
    const widget = document.getElementById('sponsorship-widget');
    const content = document.getElementById('sponsorship-widget-content');
    if (data.active_count > 0) {
      widget.classList.remove('hidden');
      const earnersHtml = data.top_earners.map(e =>
        `<div class="sponsor-earner-row">
          <span class="sponsor-earner-name">${esc(e.name)}</span>
          <span class="sponsor-earner-amount">${formatCurrency(e.monthly)}/mo</span>
        </div>`
      ).join('');
      content.innerHTML = `
        <div class="sponsor-widget-summary">
          <div class="sponsor-widget-total">${formatCurrency(data.total_monthly)}<span class="sponsor-widget-label">/month</span></div>
          <div class="sponsor-widget-count">${data.active_count} active deal${data.active_count !== 1 ? 's' : ''}</div>
        </div>
        ${earnersHtml ? `<div class="sponsor-widget-earners">${earnersHtml}</div>` : ''}
      `;
    } else {
      widget.classList.add('hidden');
    }
  } catch (err) { /* silent */ }
}

async function loadPanelSponsorships(fighterId) {
  const el = document.getElementById('panel-sponsorships');
  try {
    const data = await api(`/api/sponsorships/fighter/${fighterId}`);
    if (data.error) {
      el.classList.add('hidden');
      return;
    }
    el.classList.remove('hidden');

    let html = '<div class="sponsor-panel-title">Sponsorships</div>';

    // Active sponsorships
    if (data.active_sponsorships.length > 0) {
      html += data.active_sponsorships.map(sp => `
        <div class="sponsor-active-item">
          <div class="sponsor-active-top">
            <span class="sponsor-tier-badge">${esc(sp.tier)}</span>
            <span class="sponsor-brand-name">${esc(sp.brand_name)}</span>
          </div>
          <div class="sponsor-active-details">
            <span>${formatCurrency(sp.monthly_stipend)}/mo</span>
            <span class="muted">${sp.months_remaining} months left</span>
            <span class="muted">Paid: ${formatCurrency(sp.total_paid)}</span>
          </div>
        </div>
      `).join('');
      html += `<div class="sponsor-total-income">Total: ${formatCurrency(data.total_monthly_income)}/mo</div>`;
    }

    // Cornerstone note
    if (data.is_cornerstone) {
      html += '<div class="sponsor-cs-note">Cornerstone: +20% stipend, +10% acceptance</div>';
    }

    // Available tiers
    html += '<div class="sponsor-available-title">Available Sponsors</div>';
    html += data.available_tiers.map(t => {
      const locked = !t.eligible;
      return `
        <div class="sponsor-tier-item ${locked ? 'locked' : ''}">
          <div class="sponsor-tier-top">
            <span class="sponsor-tier-badge">${esc(t.tier)}</span>
            <span class="muted">${formatCurrency(t.monthly_stipend)}/mo &middot; ${t.duration_months}mo</span>
          </div>
          <div class="sponsor-requirements">
            <span class="${t.hype_met ? 'met' : 'unmet'}">Hype: ${t.min_hype}+ ${t.hype_met ? '\u2713' : '\u2717'}</span>
            <span class="${t.popularity_met ? 'met' : 'unmet'}">Pop: ${t.min_popularity}+ ${t.popularity_met ? '\u2713' : '\u2717'}</span>
            ${t.already_has ? '<span class="unmet">Already active</span>' : ''}
          </div>
          ${t.eligible ? `<button class="btn btn-primary sponsor-seek-btn" data-tier="${esc(t.tier)}" data-fighter="${fighterId}" style="width:100%;margin-top:6px">Seek Sponsor</button>` : ''}
        </div>
      `;
    }).join('');

    el.innerHTML = html;

    // Attach seek buttons
    el.querySelectorAll('.sponsor-seek-btn').forEach(btn => {
      btn.addEventListener('click', () => seekSponsorship(Number(btn.dataset.fighter), btn.dataset.tier));
    });
  } catch (err) {
    el.classList.add('hidden');
  }
}

async function seekSponsorship(fighterId, tier) {
  try {
    const result = await api('/api/sponsorships/seek', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ fighter_id: fighterId, tier: tier }),
    });
    if (result.success) {
      setStatus(result.message);
    } else {
      setStatus(result.message, true);
    }
    // Reload the sponsorship panel
    loadPanelSponsorships(fighterId);
    loadSponsorshipWidget();
  } catch (err) {
    try {
      const errData = JSON.parse(err.message);
      setStatus(errData.message || 'Sponsorship attempt failed.', true);
    } catch (_) {
      setStatus('Error: ' + err.message, true);
    }
    loadPanelSponsorships(fighterId);
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
        loadGameDate();
        if (state.currentView === 'dashboard') loadDashboard();
        if (state.currentView === 'roster') loadRoster();
        if (state.currentView === 'development') loadDevelopmentView();
        if (state.currentView === 'events') loadEventsView();
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

// (old simulateEvent removed — events now handled via Events view)

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
// Reality Show
// ---------------------------------------------------------------------------

async function loadShowView() {
  try {
    const data = await api('/api/show/active');
    if (data.show) {
      state.activeShowId = data.show.id;
      if (data.show.status === 'In Progress') {
        showActiveState(data.show);
      } else {
        showCompletedState(data.show);
      }
    } else {
      showSetupState();
    }
    loadShowHistory();
  } catch (err) {
    setStatus('Error loading show: ' + err.message, true);
  }
}

function showSetupState() {
  document.getElementById('show-setup').classList.remove('hidden');
  document.getElementById('show-active').classList.add('hidden');
  document.getElementById('show-completed').classList.add('hidden');
  state.showSelectedFighters = [];
  updateShowFormatUI();
  loadShowEligibleFighters();
}

function updateShowFormatUI() {
  const size = state.showFormatSize;
  const episodes = size === 8 ? 4 : 5;
  const cost = 75000 * episodes;
  document.getElementById('show-cost-preview').textContent =
    `Cost: $75,000/episode x ${episodes} episodes = $${cost.toLocaleString()} total`;
  document.getElementById('show-format-target').textContent = size;
  renderShowSelected();
}

async function loadShowEligibleFighters() {
  const wc = document.getElementById('show-wc-select').value;
  try {
    const fighters = await api(`/api/show/eligible-fighters?weight_class=${encodeURIComponent(wc)}`);
    const pool = document.getElementById('show-fighter-pool');
    document.getElementById('show-pool-count').textContent = `(${fighters.length})`;
    if (fighters.length === 0) {
      pool.innerHTML = '<p class="muted">No eligible fighters in this weight class.</p>';
      return;
    }
    pool.innerHTML = fighters.map(f => `
      <div class="show-pool-fighter ${state.showSelectedFighters.some(s => s.id === f.id) ? 'selected' : ''}"
           data-id="${f.id}" onclick="toggleShowFighter(${f.id})">
        <div class="show-fighter-info">
          <span class="show-fighter-ovr">${f.overall}</span>
          <div class="show-fighter-copy">
            <span>${esc(f.name)}</span>
            <span style="color:var(--muted);font-size:12px">${f.age}y ${f.record}</span>
            ${window.MarketUi?.renderCompactMarketLine ? window.MarketUi.renderCompactMarketLine(f.market_context, f.recommendation) : ''}
          </div>
        </div>
        <span class="show-fighter-salary">$${f.asking_salary?.toLocaleString() || '?'}</span>
      </div>
    `).join('');
  } catch (err) {
    document.getElementById('show-fighter-pool').innerHTML = '<p class="muted">Error loading fighters.</p>';
  }
}

function toggleShowFighter(id) {
  const idx = state.showSelectedFighters.findIndex(f => f.id === id);
  if (idx !== -1) {
    state.showSelectedFighters.splice(idx, 1);
  } else {
    if (state.showSelectedFighters.length >= state.showFormatSize) return;
    // Find fighter data from pool
    const el = document.querySelector(`.show-pool-fighter[data-id="${id}"]`);
    if (!el) return;
    const name = el.querySelector('.show-fighter-info span:nth-child(2)')?.textContent || 'Unknown';
    const ovr = el.querySelector('.show-fighter-ovr')?.textContent || '0';
    state.showSelectedFighters.push({ id, name, overall: parseInt(ovr) });
  }
  // Refresh pool selection state
  document.querySelectorAll('.show-pool-fighter').forEach(el => {
    const fId = parseInt(el.dataset.id);
    el.classList.toggle('selected', state.showSelectedFighters.some(f => f.id === fId));
  });
  renderShowSelected();
}

function renderShowSelected() {
  const list = document.getElementById('show-selected-list');
  document.getElementById('show-selected-count').textContent = state.showSelectedFighters.length;
  const btn = document.getElementById('btn-start-show');
  btn.disabled = state.showSelectedFighters.length !== state.showFormatSize;

  if (state.showSelectedFighters.length === 0) {
    list.innerHTML = '<p class="muted">Click fighters to add them.</p>';
    return;
  }
  // Sort by overall desc (seed preview)
  const sorted = [...state.showSelectedFighters].sort((a, b) => b.overall - a.overall);
  list.innerHTML = sorted.map((f, i) => `
    <div class="show-selected-fighter" onclick="toggleShowFighter(${f.id})">
      <span class="contestant-seed">#${i + 1}</span>
      <span>${esc(f.name)}</span>
      <span class="show-fighter-ovr">${f.overall}</span>
    </div>
  `).join('');
}

async function startShowProduction() {
  const name = document.getElementById('show-name-input').value.trim();
  if (!name) { setStatus('Please enter a show name.', true); return; }
  const wc = document.getElementById('show-wc-select').value;
  const ids = state.showSelectedFighters.map(f => f.id);

  try {
    setStatus('Creating show...');
    const result = await api('/api/show/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name,
        weight_class: wc,
        format_size: state.showFormatSize,
        fighter_ids: ids,
      }),
    });
    if (result.error) { setStatus(result.error, true); return; }
    setStatus('Show created!');
    state.activeShowId = result.id;
    loadShowView();
  } catch (err) {
    setStatus('Error: ' + err.message, true);
  }
}

function showActiveState(show) {
  document.getElementById('show-setup').classList.add('hidden');
  document.getElementById('show-active').classList.remove('hidden');
  document.getElementById('show-completed').classList.add('hidden');

  document.getElementById('show-active-name').textContent = show.name;
  document.getElementById('show-active-wc').textContent = show.weight_class;
  document.getElementById('show-ep-progress').textContent =
    `Episode ${show.episodes_aired}/${show.total_episodes}`;
  document.getElementById('show-hype-fill').style.width = `${show.show_hype}%`;
  document.getElementById('show-hype-val').textContent = Math.round(show.show_hype);

  // Render bracket
  renderShowBracket(show.id, 'show-bracket-container');

  // Render latest episode
  renderLatestEpisode(show);

  // Render contestants
  renderContestants(show.contestants);
}

async function renderShowBracket(showId, containerId) {
  try {
    const data = await api(`/api/show/${showId}/bracket`);
    const container = document.getElementById(containerId);
    if (!data.rounds || data.rounds.length === 0) {
      container.innerHTML = '<p class="muted">Bracket not yet available.</p>';
      return;
    }
    let html = '<div class="show-bracket">';
    for (const round of data.rounds) {
      html += '<div class="bracket-round">';
      html += `<div class="bracket-round-title">${esc(round.round_name)}</div>`;
      for (const m of round.matchups) {
        html += '<div class="bracket-matchup">';
        const aWinner = m.winner === m.fighter_a?.id;
        const bWinner = m.winner === m.fighter_b?.id;
        const aClass = m.winner ? (aWinner ? 'winner' : 'loser') : '';
        const bClass = m.winner ? (bWinner ? 'winner' : 'loser') : '';
        const aName = m.fighter_a?.name || 'TBD';
        const bName = m.fighter_b?.name || 'TBD';
        const aSeed = m.fighter_a?.seed || '?';
        const bSeed = m.fighter_b?.seed || '?';
        html += `<div class="bracket-fighter ${aClass} ${m.is_walkover && !aWinner ? 'bye' : ''}">
          <span><span class="bracket-seed">${aSeed}</span> ${esc(aName)}</span>
          ${aWinner ? '<span>&#x2714;</span>' : ''}
        </div>`;
        html += `<div class="bracket-fighter ${bClass} ${m.is_walkover && !bWinner ? 'bye' : ''}">
          <span><span class="bracket-seed">${bSeed}</span> ${esc(bName)}</span>
          ${bWinner ? '<span>&#x2714;</span>' : ''}
        </div>`;
        html += '</div>';
      }
      html += '</div>';
    }
    // Winner column
    if (data.winner) {
      html += '<div class="bracket-round">';
      html += '<div class="bracket-round-title">Champion</div>';
      html += `<div class="bracket-matchup"><div class="bracket-fighter winner" style="text-align:center;font-size:15px">
        ${esc(data.winner.name)}
      </div></div>`;
      html += '</div>';
    }
    html += '</div>';
    container.innerHTML = html;
  } catch (err) {
    document.getElementById(containerId).innerHTML = '<p class="muted">Error loading bracket.</p>';
  }
}

function renderLatestEpisode(show) {
  const el = document.getElementById('show-latest-episode');
  if (!show.episodes || show.episodes.length === 0) {
    el.innerHTML = '<p class="muted">No episodes aired yet. Advance month to air the next episode.</p>';
    return;
  }
  const ep = show.episodes[show.episodes.length - 1];
  let html = `<div class="latest-ep-header">Latest: Episode ${ep.episode_number} — ${ep.episode_type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</div>`;

  // Shenanigans
  const shenanigans = ep.shenanigans || [];
  if (shenanigans.length > 0) {
    for (const s of shenanigans) {
      const cls = s.category === 'positive' ? 'positive' : 'negative';
      const icon = s.category === 'positive' ? '&#x2B50;' : '&#x26A0;';
      html += `<div class="shenanigan-card ${cls}">
        <div class="shenanigan-header">
          <span class="shenanigan-icon">${icon}</span>
          <strong>${esc(s.fighter_name)}</strong>
          ${s.tag ? `<span class="shenanigan-tag-badge">${esc(s.tag)}</span>` : ''}
        </div>
        <div class="shenanigan-desc">${esc(s.description)}</div>
      </div>`;
    }
  }

  // Fight results
  const fights = ep.fight_results || [];
  for (const fr of fights) {
    const method = fr.is_walkover ? 'Walkover' : `${fr.method} R${fr.round}`;
    html += `<div class="result-fight-card" style="margin-bottom:8px">
      <div style="display:flex;justify-content:space-between;align-items:center">
        <span><strong>${esc(fr.winner)}</strong> def. ${esc(fr.loser || fr.fighter_b)}</span>
        <span style="color:var(--muted);font-size:12px">${method}</span>
      </div>
      ${fr.narrative ? `<div style="font-size:12px;color:var(--muted);margin-top:4px">${esc(fr.narrative)}</div>` : ''}
    </div>`;
  }

  el.innerHTML = html;
}

function renderContestants(contestants) {
  const el = document.getElementById('show-contestants-list');
  if (!contestants || contestants.length === 0) {
    el.innerHTML = '<p class="muted">No contestants.</p>';
    return;
  }
  const sorted = [...contestants].sort((a, b) => a.seed - b.seed);
  el.innerHTML = sorted.map(c => `
    <div class="show-contestant-row ${c.contestant_status !== 'active' ? 'eliminated' : ''}">
      <div style="display:flex;align-items:center;gap:8px">
        <span class="contestant-seed">#${c.seed}</span>
        <span>${esc(c.name)}</span>
      </div>
      <div style="display:flex;align-items:center;gap:12px">
        <span class="contestant-record">${c.show_wins}-${c.show_losses}</span>
        <span style="font-size:11px;color:var(--muted)">${c.contestant_status}</span>
        ${c.shenanigan_count > 0 ? `<span style="font-size:11px;color:var(--accent)">${c.shenanigan_count} drama</span>` : ''}
      </div>
    </div>
  `).join('');
}

async function showCompletedState(show) {
  document.getElementById('show-setup').classList.add('hidden');
  document.getElementById('show-active').classList.add('hidden');
  document.getElementById('show-completed').classList.remove('hidden');

  // Champion banner
  const winner = show.contestants?.find(c => c.id === show.winner_id || c.id === show.winner_id);
  const winnerFighter = show.contestants?.find(c => {
    return c.id === show.winner_id;
  });
  // Try to find winner by fighter_id matching show.winner_id
  const winnerContestant = show.contestants?.find(c => c.id === show.winner_id)
    || show.contestants?.find(c => c.fighter_id === show.winner_id);
  document.getElementById('show-champion-name').textContent =
    winnerContestant?.name || 'Champion';

  // Bracket
  renderShowBracket(show.id, 'show-completed-bracket');

  // Signing list
  try {
    const contestants = await api(`/api/show/${show.id}/contestants`);
    const list = document.getElementById('show-signing-list');
    if (contestants.length === 0) {
      list.innerHTML = '<p class="muted">All contestants already signed.</p>';
    } else {
      list.innerHTML = contestants.map((c, idx) => `
        <div class="show-signing-row">
          <div class="signing-info">
            <span class="signing-name">${esc(c.name)}</span>
            <span class="signing-meta">OVR ${c.overall} | ${c.show_wins}-${c.show_losses} show record | Seed #${c.seed}</span>
            ${c.discount_pct > 0 ? `<span class="signing-discount">${c.placement} — ${c.discount_pct}% discount</span>` : `<span class="signing-meta">${c.placement}</span>`}
            ${window.MarketUi?.renderRecommendationBadge ? window.MarketUi.renderRecommendationBadge(c.recommendation) : ''}
          </div>
          <div style="display:flex;align-items:center;gap:12px">
            <span>$${c.modified_asking_salary?.toLocaleString()}/yr</span>
            ${c.placement === 'Winner' ?
              `<button class="btn btn-primary" onclick="signShowWinner(${show.id})">Sign Winner</button>` :
              `<button class="btn btn-secondary show-signing-view" data-index="${idx}">View</button>`
            }
          </div>
        </div>
      `).join('');
      list.querySelectorAll('.show-signing-view').forEach(btn => {
        btn.addEventListener('click', () => {
          const contestant = contestants[Number(btn.dataset.index)];
          if (!contestant) return;
          state.panelContext = 'free-agents';
          showFighterPanel(contestant.id, {
            asking_salary: contestant.modified_asking_salary || contestant.asking_salary,
            asking_fights: contestant.asking_fights || 4,
            asking_length_months: contestant.asking_length_months || 12,
            market_context: contestant.market_context || null,
            recommendation: contestant.recommendation || null,
          });
        });
      });
    }
  } catch (err) {
    document.getElementById('show-signing-list').innerHTML = '<p class="muted">Error loading contestants.</p>';
  }

  // Summary
  const profit = show.total_revenue - show.total_production_spend;
  document.getElementById('show-summary').innerHTML = `
    <div class="show-summary-item">
      <div class="show-summary-label">Total Cost</div>
      <div class="show-summary-value">$${Math.round(show.total_production_spend).toLocaleString()}</div>
    </div>
    <div class="show-summary-item">
      <div class="show-summary-label">Total Revenue</div>
      <div class="show-summary-value">$${Math.round(show.total_revenue).toLocaleString()}</div>
    </div>
    <div class="show-summary-item">
      <div class="show-summary-label">Profit</div>
      <div class="show-summary-value" style="color:${profit >= 0 ? '#4caf50' : 'var(--accent)'}">$${Math.round(profit).toLocaleString()}</div>
    </div>
    <div class="show-summary-item">
      <div class="show-summary-label">Show Hype</div>
      <div class="show-summary-value">${Math.round(show.show_hype)}</div>
    </div>
  `;
}

async function signShowWinner(showId) {
  try {
    setStatus('Offering contract to winner...');
    const result = await api(`/api/show/${showId}/sign-winner`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    setStatus(result.message || (result.accepted ? 'Contract signed!' : 'Offer rejected.'));
    loadShowView();
  } catch (err) {
    setStatus('Error: ' + err.message, true);
  }
}

async function cancelShow() {
  if (!state.activeShowId) return;
  if (!confirm('Cancel the show? This will cost -3 prestige with no refund.')) return;
  try {
    const result = await api(`/api/show/${state.activeShowId}/cancel`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    setStatus(result.message || 'Show cancelled.');
    state.activeShowId = null;
    loadShowView();
  } catch (err) {
    setStatus('Error: ' + err.message, true);
  }
}

async function loadShowHistory() {
  try {
    const history = await api('/api/show/history');
    const el = document.getElementById('show-history-list');
    if (history.length === 0) {
      el.innerHTML = '<p class="muted">No past shows.</p>';
      return;
    }
    el.innerHTML = history.map(h => `
      <div class="show-history-item" onclick="viewShowDetails(${h.id})" style="cursor:pointer">
        <div>
          <div class="show-hist-name">${esc(h.name)}</div>
          <div class="show-hist-meta">${h.weight_class} | ${h.format_size} fighters | ${h.start_date || '?'} — ${h.end_date || '?'}</div>
        </div>
        <div style="text-align:right">
          <div>${h.winner_name ? esc(h.winner_name) : h.status}</div>
          <div class="show-hist-meta">Hype: ${Math.round(h.show_hype)}</div>
        </div>
      </div>
    `).join('');
  } catch (err) {
    document.getElementById('show-history-list').innerHTML = '<p class="muted">Error loading history.</p>';
  }
}

async function viewShowDetails(showId) {
  try {
    const show = await api(`/api/show/${showId}`);
    if (show.error) return;
    state.activeShowId = showId;
    if (show.status === 'Completed' || show.status === 'Cancelled') {
      showCompletedState(show);
    } else {
      showActiveState(show);
    }
  } catch (err) {
    setStatus('Error: ' + err.message, true);
  }
}

async function loadShowWidget() {
  try {
    const data = await api('/api/show/active');
    const widget = document.getElementById('show-widget');
    if (!data.show) {
      widget.classList.add('hidden');
      return;
    }
    widget.classList.remove('hidden');
    const show = data.show;
    document.getElementById('show-widget-content').innerHTML = `
      <div class="show-widget-info">
        <div><strong>${esc(show.name)}</strong></div>
        <div>Episode ${show.episodes_aired}/${show.total_episodes} | ${show.weight_class}</div>
        <div class="show-hype-bar" style="margin-top:4px">
          <span style="font-size:12px">Hype</span>
          <div class="hype-bar-track" style="width:100px">
            <div class="hype-bar-fill" style="width:${show.show_hype}%"></div>
          </div>
          <span style="font-size:12px">${Math.round(show.show_hype)}</span>
        </div>
      </div>
    `;
  } catch (err) {
    document.getElementById('show-widget').classList.add('hidden');
  }
}


const NEWS_ICONS = {
  fight_result: '\u{1F94A}',
  signing: '\u{1F4DD}',
  upset: '\u26A1',
  title: '\u{1F3C6}',
  streak: '\u{1F525}',
  retirement_concern: '\u23F0',
  retirement: '\u{1F3C6}',
  show: '\u{1F3AC}',
};

async function loadNewsWidget() {
  try {
    const headlines = await api('/api/news?limit=10');
    const widget = document.getElementById('news-widget');
    const content = document.getElementById('news-widget-content');
    if (!headlines || headlines.length === 0) {
      widget.classList.add('hidden');
      return;
    }
    widget.classList.remove('hidden');
    content.innerHTML = headlines.map(h => `
      <div class="news-item" ${h.fighter_id ? `onclick="showFighterPanel(${h.fighter_id})"` : ''}>
        <span class="news-icon">${NEWS_ICONS[h.category] || '\u{1F4F0}'}</span>
        <span class="news-text">${esc(h.headline)}</span>
        <span class="news-date">${h.game_date}</span>
      </div>
    `).join('');
  } catch (err) {
    document.getElementById('news-widget').classList.add('hidden');
  }
}

async function loadMediaWidget() {
  try {
    const storylines = await api('/api/media/storylines');
    const widget = document.getElementById('media-widget');
    const content = document.getElementById('media-widget-content');
    if (!storylines || storylines.length === 0) {
      widget.classList.add('hidden');
      return;
    }
    widget.classList.remove('hidden');
    content.innerHTML = window.MarketUi?.renderMediaStorylines
      ? window.MarketUi.renderMediaStorylines(storylines)
      : '';
  } catch (err) {
    document.getElementById('media-widget').classList.add('hidden');
  }
}


// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------

document.addEventListener('DOMContentLoaded', () => {
  // Nav
  document.querySelectorAll('.nav-item').forEach(el => {
    el.addEventListener('click', () => navigate(el.dataset.view));
  });
  initSortableTables();

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
  document.getElementById('fa-trajectory-filter').addEventListener('change', () => loadFreeAgents());
  document.getElementById('fa-sort').addEventListener('change', (e) => {
    const sortKeyMap = {
      overall: 'overall',
      salary: 'asking_salary',
      age: 'age',
      hype: 'hype',
      market_booking: 'market_booking',
      market_ai_heat: 'market_ai_heat',
    };
    state.tableSorts.freeAgents = {
      key: sortKeyMap[e.target.value] || 'overall',
      direction: e.target.value === 'age' ? 'asc' : 'desc',
    };
    loadFreeAgents();
  });

  // Roster market controls
  document.getElementById('roster-trajectory-filter').addEventListener('change', () => loadRoster());
  document.getElementById('roster-sort').addEventListener('change', (e) => {
    state.tableSorts.roster = {
      key: e.target.value || 'overall',
      direction: e.target.value === 'expiry_date' ? 'asc' : 'desc',
    };
    loadRoster();
  });

  // Rankings tabs
  document.querySelectorAll('.wc-tab').forEach(el => {
    el.addEventListener('click', () => loadRankings(el.dataset.wc));
  });

  // Actions
  document.getElementById('btn-advance-month').addEventListener('click', advanceMonth);
  document.getElementById('btn-close-panel').addEventListener('click', closeFighterPanel);

  // Event booking
  document.getElementById('btn-create-event').addEventListener('click', openCreateEventModal);
  document.getElementById('btn-modal-close').addEventListener('click', closeModal);
  document.getElementById('btn-modal-create').addEventListener('click', createEvent);
  document.getElementById('btn-press-conference').addEventListener('click', holdPressConference);
  document.getElementById('btn-simulate-card').addEventListener('click', confirmSimulate);
  document.getElementById('btn-confirm-sim').addEventListener('click', simulateCard);
  document.getElementById('btn-cancel-sim').addEventListener('click', cancelSimulate);
  document.getElementById('btn-add-matchup').addEventListener('click', addMatchup);

  // League History filter and pagination
  document.getElementById('history-org-filter').addEventListener('change', () => {
    historyOffset = 0;
    loadLeagueHistory();
  });
  document.getElementById('btn-load-more-history').addEventListener('click', () => {
    historyOffset += HISTORY_BATCH;
    loadLeagueHistory(true);
  });

  // Pool search and filter
  document.getElementById('pool-search').addEventListener('input', e => {
    state.poolFilter = e.target.value;
    renderFighterPool();
  });
  document.querySelectorAll('#pool-wc-tabs .pool-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('#pool-wc-tabs .pool-tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      state.poolWc = tab.dataset.wc;
      renderFighterPool();
    });
  });

  // Development
  document.querySelectorAll('.focus-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      devState.selectedFocus = btn.dataset.focus;
      document.querySelectorAll('.focus-btn').forEach(b => b.classList.toggle('active', b.dataset.focus === devState.selectedFocus));
      if (devState.selectedFighterId && devState.selectedCampId) {
        loadDevProjection(devState.selectedFighterId, devState.selectedCampId, devState.selectedFocus);
      }
    });
  });
  document.getElementById('btn-dev-assign').addEventListener('click', assignToCamp);

  // Notifications
  document.getElementById('notif-bell').addEventListener('click', toggleNotifDropdown);
  document.addEventListener('click', e => {
    const bell = document.getElementById('notif-bell');
    const dropdown = document.getElementById('notif-dropdown');
    if (!bell.contains(e.target) && !dropdown.contains(e.target)) {
      dropdown.classList.add('hidden');
    }
  });

  // Reality Show
  document.getElementById('show-wc-select').addEventListener('change', () => {
    state.showSelectedFighters = [];
    loadShowEligibleFighters();
    renderShowSelected();
  });
  document.querySelectorAll('.format-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      state.showFormatSize = parseInt(btn.dataset.size);
      state.showSelectedFighters = [];
      document.querySelectorAll('.format-btn').forEach(b => b.classList.toggle('active', b === btn));
      updateShowFormatUI();
      loadShowEligibleFighters();
    });
  });
  document.getElementById('btn-start-show').addEventListener('click', startShowProduction);
  document.getElementById('btn-cancel-show').addEventListener('click', cancelShow);
  document.getElementById('show-widget').addEventListener('click', () => navigate('show'));

  // Close modals on overlay click
  document.getElementById('modal-overlay').addEventListener('click', e => {
    if (e.target === e.currentTarget) closeModal();
  });
  document.getElementById('confirm-overlay').addEventListener('click', e => {
    if (e.target === e.currentTarget) cancelSimulate();
  });

  // Initial load
  loadGameDate();
  loadNotifications();
  setInterval(loadNotifications, 30000);
  navigate('dashboard');
});
