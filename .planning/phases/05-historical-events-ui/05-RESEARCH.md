# Phase 5: Historical Events UI - Research

**Researched:** 2026-03-03
**Domain:** Frontend UI (Vanilla JS SPA) + minor Flask API enhancement
**Confidence:** HIGH

## Summary

This phase adds a frontend consumer for the existing `GET /api/events/all-history` endpoint. The API already returns full event+fight data; the gap is purely frontend (no UI exists to browse it) plus two minor backend adjustments (offset pagination and player-org exclusion).

The implementation is straightforward because it follows established patterns: the codebase already has `loadScheduledEvents()` and `loadCompletedEvents()` as models for event list rendering, `loadEventCard()` for event detail rendering, and `renderCompletedEvent()` for completed fight results. The new "League History" tab reuses all of these with minor adaptations (hide revenue/action sections for historical events, add org name display, add org filter dropdown).

**Primary recommendation:** Add a third section ("League History") to the events-left sidebar, wire it to `GET /api/events/all-history` with offset/limit pagination, reuse existing `loadEventCard()` + `renderCompletedEvent()` for detail display, and conditionally hide revenue/action UI elements for non-player-org events.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Navigation placement:** Add a "League History" tab inside the existing Events view, alongside the Scheduled and Completed sections. No new sidebar nav item. Tab should be visually distinct as a separate section.
- **Org filtering:** Dropdown/select above the historical events list for filtering by organization. Options: "All Orgs", "UCC", "Bellator", "One Championship" (populated from event data or hardcoded from known orgs). Default to "All Orgs" on load. Player org events are excluded.
- **Event detail depth:** Reuse the existing `loadEventCard()` rendering for historical events -- same fight card layout. Hide action buttons (add fight, remove fight, simulate) since historical events are read-only. Consistent look between player events and historical events.
- **Pagination / volume:** Load first 20-30 events on initial tab activation. "Load More" button at the bottom for next batch. Uses the existing `limit` query param. No infinite scroll, no page numbers.

### Claude's Discretion
- Exact batch size (20 vs 25 vs 30)
- How to visually distinguish the League History tab from Scheduled/Completed
- Whether to show org name/logo on each event in the list
- Empty state messaging if no historical events exist
- How to pass offset/pagination to the API (may need a new `offset` param)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| HIST-05 | Historical events with results are browsable from day one | Already satisfied at API level (`GET /api/events/all-history`). This phase adds UI access: League History tab in events view, org filter dropdown, Load More pagination, reuse of `loadEventCard()` + `renderCompletedEvent()` for fight card display. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Vanilla JS | ES2020+ | All frontend logic | Project convention -- no frameworks, no React, no build step |
| Flask | 3.0+ | API routes | Existing backend, thin controller pattern |
| SQLAlchemy | 2.0+ | Query with offset/limit | Existing ORM, `.offset()` method built-in |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| CSS Custom Properties | Native | Design tokens | All new styling uses `--color-*`, `--spacing-*`, `--font-*` variables |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| "Load More" button | Infinite scroll (IntersectionObserver) | User decided against it -- "Load More" is simpler and already established in the codebase pattern |
| Hardcoded org list | Dynamic org list API | No `/api/organizations` endpoint exists; hardcoding 3 AI orgs is acceptable since they're seeded constants |

**Installation:**
No new dependencies required. Fully self-contained.

## Architecture Patterns

### Recommended Changes by File

```
frontend/templates/index.html   # Add League History section HTML to events-left sidebar
frontend/static/js/app.js       # Add loadLeagueHistory(), loadMoreHistory(), org filter handler
frontend/static/css/style.css   # Add League History section styles (tab header, org filter, load-more button)
api/app.py                      # Add offset param to /api/events/all-history route
api/services.py                 # Add offset param + player-org exclusion to get_all_event_history()
```

### Pattern 1: Event List Rendering (Existing)
**What:** Event list items use `.event-list-item` with `.event-list-name` and `.event-list-meta` sub-elements. Click handlers set `state.selectedEventId` and call `loadEventCard()`.
**When to use:** Rendering the League History event list -- follow exact same pattern.
**Example:**
```javascript
// Source: app.js:1125-1137 (loadScheduledEvents)
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
    loadLeagueHistory(); // re-render to update selected state
  });
});
```

### Pattern 2: Event Detail Rendering (Existing)
**What:** `loadEventCard(eventId)` fetches `/api/events/:id`, then branches on `event.status === 'Completed'` to call `renderCompletedEvent()`.
**When to use:** Clicking a historical event list item -- call `loadEventCard()` directly.
**Key detail:** For historical events, the code path hits `renderCompletedEvent()` which shows fight results with method badges, narratives, and revenue. Revenue will show $0 for historical events (fabricated with zero revenue). Action buttons (simulate, press conference) are already hidden for completed events.

### Pattern 3: Tab/Section Headers (Existing)
**What:** Events sidebar uses `<div class="events-section"><h3>Title</h3><div class="events-list">...</div></div>` pattern.
**When to use:** The League History section follows this exact structure with an added org filter dropdown.
**Example:**
```html
<!-- Source: index.html:151-162 -->
<div class="events-section" style="margin-top:16px">
  <h3>Completed</h3>
  <div id="events-completed-list" class="events-list">
    <p class="muted">No completed events.</p>
  </div>
</div>
```

### Pattern 4: API Helper (Existing)
**What:** `api(path)` is the fetch wrapper that returns parsed JSON or throws on error.
**When to use:** All API calls from the League History feature.
**Example:**
```javascript
// Source: app.js:30-37
async function api(path, options = {}) {
  const res = await fetch(path, options);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json();
}
```

### Anti-Patterns to Avoid
- **Adding a new sidebar nav item:** User decision is "League History" inside the Events view, not a top-level nav item.
- **Building a separate detail view for historical events:** Reuse `loadEventCard()` + the existing center column. Do not create a parallel rendering path.
- **Fetching fight details per-event on list load:** `get_all_event_history()` already includes `include_fights=True`. The list uses `main_event_result` from this data. Event detail is fetched via `loadEventCard()` on click.
- **Using `include_fights=False` for list fetch:** Tempting for performance, but the existing API already returns fights and `_event_dict` computes `main_event_result` from fights data. Changing this would break `main_event_result`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Event list rendering | Custom list component | Copy `loadCompletedEvents()` pattern | Exact same structure, proven working |
| Event detail display | Separate historical event renderer | `loadEventCard()` + `renderCompletedEvent()` | Already handles completed events perfectly |
| Offset pagination | Custom cursor-based pagination | SQLAlchemy `.offset(n).limit(n)` | Simple, proven, small dataset (~390 events) |
| HTML escaping | Custom sanitizer | Existing `esc()` function | Already used throughout codebase |
| Currency formatting | Custom formatter | Existing `formatCurrency()` | Already handles USD formatting |

**Key insight:** This phase is 90% wiring -- connecting existing backend data to existing frontend patterns. The only new UI element is the org filter dropdown and Load More button. Do not over-engineer.

## Common Pitfalls

### Pitfall 1: Revenue Display for Historical Events
**What goes wrong:** Historical events have $0 gate revenue, $0 PPV, $0 broadcast. `renderCompletedEvent()` shows a revenue summary section that would display "$0 / $0 / $0" -- looks broken.
**Why it happens:** `fabricate_history()` creates events with `gate_revenue=0.0, ppv_buys=0, broadcast_revenue=0.0, tickets_sold=0` (simulation/history.py:993-997). Revenue was never the point of fabricated history.
**How to avoid:** Conditionally hide the revenue/attendance section when the event is not from the player org, or when all revenue values are zero. Check: `event.tickets_sold === 0 && event.gate_revenue === 0`.
**Warning signs:** Event detail cards showing "$0" revenue and "0 / 0 (0%)" attendance for every historical event.

### Pitfall 2: Player Org Events in League History
**What goes wrong:** `get_all_event_history()` currently returns ALL completed events including player org events. Player org events already appear in the "Completed" section -- showing them again in League History is confusing.
**Why it happens:** The API was built for general browsing. The frontend distinction (player vs. league) was deferred to this phase.
**How to avoid:** Add `Event.organization_id != player_org.id` filter to `get_all_event_history()` when no specific `organization_id` filter is applied. Or always exclude the player org.
**Warning signs:** Same events appearing in both "Completed" and "League History" lists.

### Pitfall 3: loadEventCard() Action Buttons on Historical Events
**What goes wrong:** `loadEventCard()` shows simulation/press-conference buttons for scheduled events. For completed events, it already hides them via `event.status === 'Completed'` check (app.js:1181-1183). Historical events are all Completed, so this is already handled.
**Why it happens:** Non-issue due to existing status-based branching.
**How to avoid:** No action needed -- the existing code path handles this. But verify after wiring up.
**Warning signs:** If somehow a historical event had status != Completed, action buttons would appear.

### Pitfall 4: Missing org_name in Event Data
**What goes wrong:** `_event_dict()` does not include `organization_id` or org name. The org filter dropdown needs to filter by org, and each event list item should show which org it belongs to.
**Why it happens:** `_event_dict()` was built for player-org events where org identity was implicit.
**How to avoid:** Add `organization_id` and `organization_name` fields to `_event_dict()` (read from `event.organization` relationship). Alternatively, add them only in `get_all_event_history()`.
**Warning signs:** No way to display or filter events by org on the frontend.

### Pitfall 5: Heavy Initial Load
**What goes wrong:** ~390 historical events exist across 3 orgs over 5 years. Loading all at once with `include_fights=True` would be slow.
**Why it happens:** The existing `limit=50` default helps, but the frontend needs explicit pagination.
**How to avoid:** Use `limit=25` per batch with offset-based "Load More" pagination. First load fetches 25 events. Each "Load More" fetches the next 25 and appends.
**Warning signs:** Long load times on tab activation, browser memory issues.

### Pitfall 6: Scroll Position in Events Left Sidebar
**What goes wrong:** The `.events-list` container has `max-height: 300px; overflow-y: auto;` (style.css:1713). League History with 25+ events in the list may overflow this container awkwardly alongside the Scheduled and Completed sections.
**Why it happens:** The left sidebar is 250px wide with a fixed height based on viewport. Three sections (Scheduled, Completed, League History) compete for vertical space.
**How to avoid:** Give the League History section its own scroll container with adequate height. Consider collapsing Scheduled/Completed sections or giving League History more vertical space since it's the largest dataset.
**Warning signs:** League History section is tiny and requires excessive scrolling, or pushes other sections off-screen.

## Code Examples

Verified patterns from the existing codebase:

### League History HTML Structure
```html
<!-- Add after the Completed events-section in index.html:157-162 -->
<div class="events-section league-history-section" style="margin-top:16px">
  <h3>League History</h3>
  <select id="history-org-filter" class="history-org-filter">
    <option value="">All Orgs</option>
    <option value="UCC">Ultimate Combat Championship</option>
    <option value="Bellator">Bellator MMA</option>
    <option value="One">One Championship</option>
  </select>
  <div id="events-history-list" class="events-list">
    <p class="muted">Loading league history...</p>
  </div>
  <button id="btn-load-more-history" class="btn btn-secondary load-more-btn hidden">Load More</button>
</div>
```

### League History Load Function
```javascript
// Follow loadCompletedEvents() pattern (app.js:1141-1163)
let historyOffset = 0;
const HISTORY_BATCH = 25;

async function loadLeagueHistory(append = false) {
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

    // Show/hide Load More
    loadMoreBtn.classList.toggle('hidden', events.length < HISTORY_BATCH);

    // Attach click handlers
    el.querySelectorAll('.event-list-item').forEach(item => {
      item.addEventListener('click', () => {
        state.selectedEventId = Number(item.dataset.eventId);
        loadEventCard(state.selectedEventId);
        loadLeagueHistory(); // re-render for selected state
      });
    });
  } catch (err) { /* silent */ }
}
```

### Backend: Add offset and player-org exclusion
```python
# In api/app.py, update all_event_history route:
@app.route("/api/events/all-history")
def all_event_history():
    org_id = request.args.get("organization_id", type=int)
    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)
    return jsonify(services.get_all_event_history(
        organization_id=org_id, limit=limit, offset=offset
    ))

# In api/services.py, update get_all_event_history:
def get_all_event_history(organization_id=None, limit=50, offset=0):
    with _SessionFactory() as session:
        # Exclude player org events
        player_org = session.execute(
            select(Organization).where(Organization.is_player == True)
        ).scalar_one_or_none()

        query = select(Event).where(Event.status == EventStatus.COMPLETED)
        if player_org:
            query = query.where(Event.organization_id != player_org.id)
        if organization_id:
            query = query.where(Event.organization_id == organization_id)
        query = query.order_by(Event.event_date.desc()).offset(offset).limit(limit)

        events = session.execute(query).scalars().all()
        return [_event_dict(e, session, include_fights=True) for e in events]
```

### Backend: Add org fields to _event_dict
```python
# In api/services.py, add to _event_dict after existing fields:
def _event_dict(event, session, include_fights=True):
    d = {
        # ... existing fields ...
        "organization_id": event.organization_id,
        "organization_name": event.organization.name if event.organization else None,
    }
    # ... rest unchanged
```

### Org Filter by ID (not name)
```html
<!-- Organization IDs are dynamic (assigned at seed time), so populate from API or use names -->
<!-- Since no /api/organizations endpoint exists, two options: -->
<!-- Option A: Hardcode org names, pass as organization_name filter (requires backend change) -->
<!-- Option B: Add organization_id to event data, extract unique orgs client-side from first fetch -->
<!-- Recommendation: Option B -- extract unique orgs from the first batch of events -->
```

```javascript
// Extract unique orgs from event data for filter dropdown
function populateOrgFilter(events) {
  const orgs = new Map();
  events.forEach(ev => {
    if (ev.organization_id && ev.organization_name) {
      orgs.set(ev.organization_id, ev.organization_name);
    }
  });
  const select = document.getElementById('history-org-filter');
  select.innerHTML = '<option value="">All Orgs</option>';
  for (const [id, name] of orgs) {
    select.innerHTML += `<option value="${id}">${esc(name)}</option>`;
  }
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No history browsing | API-only via `GET /api/events/all-history` | Phase 2 (2026-03-02) | API exists, no frontend consumer |
| No org filtering | `organization_id` query param on endpoint | Phase 2 (2026-03-02) | Backend ready, frontend needs wiring |

**Deprecated/outdated:**
- None -- this is greenfield frontend work on top of existing backend.

## Open Questions

1. **Org filter: by ID or by name?**
   - What we know: Organization IDs are assigned dynamically at seed time (autoincrement). Org names are constant strings ("Ultimate Combat Championship", "Bellator MMA", "One Championship").
   - What's unclear: The frontend doesn't know org IDs until it fetches event data.
   - Recommendation: Add `organization_id` and `organization_name` to `_event_dict()`. Populate the org filter dropdown dynamically from the first batch of events (extract unique org IDs/names). Pass `organization_id` to the API. This avoids hardcoding IDs and handles any future org additions.

2. **Revenue display for historical events**
   - What we know: All fabricated events have zero revenue/attendance data.
   - What's unclear: Should the revenue section be hidden entirely, or shown with zeros?
   - Recommendation: Hide the revenue/attendance section when `event.tickets_sold === 0 && event.gate_revenue === 0`. This is a simple conditional in `renderCompletedEvent()` or handled by checking if the event belongs to the player org.

3. **Sidebar vertical space allocation**
   - What we know: Events left sidebar is 250px wide with three sections competing for vertical space. The `.events-list` class has `max-height: 300px`.
   - What's unclear: Whether 300px is enough for League History alongside the other two sections.
   - Recommendation: Use a separate `max-height` for the League History list (e.g., 250px) since the Load More button limits visible items to 25 at a time.

## Sources

### Primary (HIGH confidence)
- `frontend/static/js/app.js:1110-1307` -- Events view JavaScript: loadEventsView, loadScheduledEvents, loadCompletedEvents, loadEventCard, renderCompletedEvent
- `frontend/templates/index.html:146-247` -- Events view HTML structure
- `frontend/static/css/style.css:1038-1713` -- Events CSS: layout, list items, result cards
- `api/app.py:155-160` -- `/api/events/all-history` route definition
- `api/services.py:1638-1653` -- `get_all_event_history()` implementation
- `api/services.py:1172-1201` -- `_event_dict()` serialization
- `api/services.py:1151-1169` -- `_fight_dict()` serialization
- `simulation/history.py:861-960` -- `fabricate_history()` event generation (confirms ~390 events, zero revenue data)
- `simulation/seed.py:326-335` -- `seed_organizations()` (3 AI orgs + 1 player org)
- `models/models.py:213-234` -- Organization model (name, is_player fields)
- `models/models.py:268-302` -- Event model (organization_id FK, organization relationship)

### Secondary (MEDIUM confidence)
- None -- all findings are from direct codebase inspection.

### Tertiary (LOW confidence)
- None -- no external research needed for this frontend wiring phase.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- No new dependencies. Vanilla JS, Flask, SQLAlchemy already in use.
- Architecture: HIGH -- Direct codebase inspection reveals exact patterns to follow, exact functions to reuse, exact HTML structure to extend.
- Pitfalls: HIGH -- All pitfalls identified from reading actual code (zero revenue data, missing org fields, player org inclusion, sidebar height).

**Research date:** 2026-03-03
**Valid until:** 2026-04-03 (stable -- no external dependencies, fully internal codebase knowledge)
