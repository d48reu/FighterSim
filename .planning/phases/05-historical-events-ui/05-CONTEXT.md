# Phase 5: Historical Events UI - Context

**Gathered:** 2026-03-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Build a frontend consumer for the existing `GET /api/events/all-history` endpoint so players can browse pre-generated fight history from the UI. Historical events from all orgs (UCC, Bellator, One) become browsable with fight cards and results. No new API work needed — the endpoint already exists with org filtering and full fight details.

</domain>

<decisions>
## Implementation Decisions

### Navigation placement
- Add a "League History" tab inside the existing Events view, alongside the Scheduled and Completed sections
- No new sidebar nav item — keeps event-related content together
- Tab should be visually distinct as a separate section (not mixed into player org events)

### Org filtering
- Dropdown/select above the historical events list for filtering by organization
- Options: "All Orgs", "UCC", "Bellator", "One Championship" (populated from event data or hardcoded from known orgs)
- Default to "All Orgs" on load
- Player org events are excluded (those already appear in the Completed section)

### Event detail depth
- Reuse the existing `loadEventCard()` rendering for historical events — same fight card layout showing fighters, method, round, narrative
- Hide action buttons (add fight, remove fight, simulate) since historical events are read-only
- Consistent look between player events and historical events — just no interactivity on historical ones

### Pagination / volume
- Load first 20-30 events on initial tab activation
- "Load More" button at the bottom to fetch the next batch
- Uses the existing `limit` query param on `GET /api/events/all-history`
- No infinite scroll, no page numbers

### Claude's Discretion
- Exact batch size (20 vs 25 vs 30)
- How to visually distinguish the League History tab from Scheduled/Completed
- Whether to show org name/logo on each event in the list
- Empty state messaging if no historical events exist
- How to pass offset/pagination to the API (may need a new `offset` param)

</decisions>

<specifics>
## Specific Ideas

- Historical events should feel like browsing a real MMA promotion's event archive — "UCC 45", "Bellator 78" with dates and results
- The existing event card already shows fight narratives from Phase 2 — those should render naturally once wired up
- This closes the HIST-05 gap: historical events are API-browsable but have no frontend consumer

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `GET /api/events/all-history`: Already exists in `api/app.py:155`, supports `organization_id` and `limit` query params
- `get_all_event_history()` in `api/services.py:1638`: Returns events with `include_fights=True` — full fight details included
- `loadEventCard(eventId)` in `app.js:1166`: Renders full event detail card with fight results — reuse directly
- `loadScheduledEvents()` / `loadCompletedEvents()` in `app.js:1117-1163`: Pattern for populating event list items with click handlers
- Event list item HTML pattern: `.event-list-item` with `.event-list-name` and `.event-list-meta` sub-elements

### Established Patterns
- SPA view switching via `navigate()` function in `app.js:78` — Events view loads via `loadEventsView()`
- Event lists use `api()` helper for fetch calls, render with template literals
- Click handlers on list items set `state.selectedEventId` and call `loadEventCard()`
- CSS design tokens (Rajdhani + Inter fonts, `--color-*`, `--spacing-*` variables)

### Integration Points
- `loadEventsView()` in `app.js:1110`: Entry point — add League History tab loading here
- `index.html`: Events view HTML section needs a new tab/section for League History
- Event card rendering: conditionally hide action buttons when event is historical (not player org)
- API may need an `offset` param added to `get_all_event_history()` for load-more pagination

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 05-historical-events-ui*
*Context gathered: 2026-03-03*
