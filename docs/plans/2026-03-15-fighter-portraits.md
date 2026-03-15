# Fighter Portraits Implementation Plan

> For Hermes: use subagent-driven-development skill to implement this plan task-by-task.

Goal: add portraits that materially improve FighterSim's perceived quality without making the roster look like cursed sameface AI slop.

Architecture: ship a curated stylized portrait library first, not bespoke photoreal generation. Add a deterministic portrait assignment layer at seed time, store a stable portrait key on each Fighter, expose a portrait_url in the API, and render portraits in the fighter side panel first. Treat custom hero portraits for champions/cornerstones as a later phase.

Tech Stack: SQLAlchemy model update, Python seed helpers, static image assets under frontend/static, Flask API payload updates, existing JS/CSS frontend, pytest.

---

## Product Decision

Recommended style:
- stylized sports-broadcast / posterized illustrated headshots
- shoulders-up framing
- consistent dark or neutral background
- subtle archetype / weight-class visual flavor
- realistic anatomy, but not photoreal skin-detail worship

Do NOT ship first:
- bespoke photoreal portraits for the whole roster
- multiple unrelated art styles
- full-body character art
- "just generate one per fighter live" nonsense

Why:
- the current game has strong typography and arena UI, so broadcast-card headshots fit the product
- there is no gender field on Fighter, which makes bespoke photoreal prompting much riskier
- a curated library is controllable, seed-stable, and easy to QA

---

## Existing Code Reality

Current codebase facts:
- no Fighter portrait field exists today
- no API portrait key/url exists today
- no frontend <img> / avatar / portrait slot exists today
- best insertion point is the fighter side panel header in `frontend/templates/index.html`
- seed-time hook exists naturally in `simulation/seed.py` right after fighter core metadata is assembled
- useful metadata already exists for assignment: age, nationality, weight_class, style, archetype, traits, nickname
- roadmap references portraits as a library assigned at seed time

That means the clean first version is:
1. add portrait_key to Fighter
2. assign portrait_key deterministically in seed
3. expose portrait_url via API
4. render in fighter panel
5. optionally expand to compare cards and table thumbnails later

---

## Asset Strategy

Use a controlled portrait library rather than free-form generation.

Recommended directory shape:
- Create: `frontend/static/assets/portraits/manifest.json`
- Create: `frontend/static/assets/portraits/README.md`
- Create: `frontend/static/assets/portraits/<bucket>/<file>.webp`

Suggested bucket axes for v1:
- age_band: `prospect`, `prime`, `veteran`
- style: `striker`, `wrestler`, `grappler`
- region flavor: `europe`, `mena_caucasus`, `east_asia`, `latam`, `north_america`, `africa`, `oceania`

Do not overfit to exact nationality in v1. Region-level flavor is enough.

Manifest shape:
```json
{
  "version": 1,
  "style": "broadcast-illustrated-v1",
  "buckets": {
    "prime/striker/latam": [
      "prime/striker/latam_01.webp",
      "prime/striker/latam_02.webp"
    ]
  }
}
```

Use `.webp` for size sanity.

Target size:
- 160x200 or 192x240 for panel use
- render smaller in UI as needed

---

## Task 1: Add portrait field to Fighter

Objective: give Fighter a stable persistent portrait reference.

Files:
- Modify: `models/models.py`
- Test: `tests/test_seed_validation.py`

Step 1: Write failing test

Add to `tests/test_seed_validation.py`:
```python
def test_all_seeded_fighters_get_portrait_keys(seeded_session):
    fighters = seeded_session.execute(select(Fighter)).scalars().all()
    assert fighters
    assert all(getattr(f, "portrait_key", None) for f in fighters)
```

Step 2: Run test to verify failure

Run:
`pytest tests/test_seed_validation.py::test_all_seeded_fighters_get_portrait_keys -v`

Expected: FAIL because `portrait_key` does not exist yet.

Step 3: Minimal implementation

In `models/models.py`, add:
```python
portrait_key: Mapped[Optional[str]] = Column(String(255), nullable=True)
```

Place it near other presentation/narrative fields, not buried in finance or relationships.

Step 4: Run test to verify improved failure mode

Run:
`pytest tests/test_seed_validation.py::test_all_seeded_fighters_get_portrait_keys -v`

Expected: FAIL because keys are still unset, which is correct progress.

Step 5: Commit

`git add models/models.py tests/test_seed_validation.py && git commit -m "feat: add fighter portrait key field"`

---

## Task 2: Create deterministic portrait assignment module

Objective: centralize bucket logic and keep seed code clean.

Files:
- Create: `simulation/portraits.py`
- Modify: `simulation/seed.py`
- Test: `tests/test_seed_validation.py`

Step 1: Write failing test

Add tests like:
```python
def test_portrait_assignment_is_deterministic_for_same_seed():
    # seed twice, compare sorted portrait keys
```

and
```python
def test_portrait_key_uses_known_bucket_prefixes(seeded_session):
    fighters = seeded_session.execute(select(Fighter)).scalars().all()
    assert all("/" in f.portrait_key for f in fighters)
```

Step 2: Run tests to verify failure

Run:
`pytest tests/test_seed_validation.py -k portrait -v`

Expected: FAIL.

Step 3: Write minimal implementation

Create `simulation/portraits.py` with helpers:
```python
def age_band_for_fighter(fighter: Fighter) -> str: ...
def region_bucket_for_nationality(nationality: str) -> str: ...
def style_bucket(style: FighterStyle | str) -> str: ...
def portrait_bucket(age_band: str, style: str, region: str) -> str: ...
def assign_portrait_key(fighter: Fighter, rng: random.Random) -> str: ...
```

Important rule:
- assignment must be deterministic from fighter attributes plus seeded RNG
- do not depend on filesystem ordering at runtime
- do not randomly scan directories every seed

Recommended approach:
- keep a Python dict or manifest-backed registry of available counts per bucket
- pick an index via seeded RNG or stable hash from `fighter.name + fighter.nationality + fighter.age`

Example output:
```python
"prime/striker/latam_02.webp"
```

In `simulation/seed.py`, after nickname assignment:
```python
from simulation.portraits import assign_portrait_key
f.portrait_key = assign_portrait_key(f, py_rng)
```

Step 4: Run tests to verify pass

Run:
`pytest tests/test_seed_validation.py -k portrait -v`

Step 5: Commit

`git add simulation/portraits.py simulation/seed.py tests/test_seed_validation.py && git commit -m "feat: assign deterministic fighter portrait keys at seed time"`

---

## Task 3: Add portrait assets and manifest

Objective: create the v1 portrait library structure.

Files:
- Create: `frontend/static/assets/portraits/manifest.json`
- Create: `frontend/static/assets/portraits/README.md`
- Create: `frontend/static/assets/portraits/.../*.webp`

Step 1: Add README documenting conventions

Include:
- art style statement
- required resolution
- naming convention
- bucket list
- how to add new portraits without breaking determinism

Step 2: Add manifest

Manifest should enumerate available files by bucket. Avoid hidden filesystem magic.

Step 3: Add initial asset batch

Start smaller than the roadmap fantasy. Good v1 target:
- 24 to 36 portraits
- enough to prove the system
- then expand later to 80+

Suggested first spread:
- 3 age bands × 3 styles × 3-4 high-value region buckets, one or two portraits each

Step 4: Manual verification

Check files load directly in browser.

Step 5: Commit

`git add frontend/static/assets/portraits && git commit -m "feat: add v1 fighter portrait library assets"`

---

## Task 4: Expose portrait_url in API payloads

Objective: make portraits available to the frontend without leaking storage details everywhere.

Files:
- Modify: `api/services.py`
- Test: `tests/test_market_api.py` or new `tests/test_fighter_portraits_api.py`

Step 1: Write failing test

Create a focused test file:
- Create: `tests/test_fighter_portraits_api.py`

Test:
```python
def test_get_fighter_exposes_portrait_url(tmp_path):
    ...
    fighter = services.get_fighter(fighter_id)
    assert fighter["portrait_key"]
    assert fighter["portrait_url"].startswith("/static/assets/portraits/")
```

Step 2: Run test to verify failure

Run:
`pytest tests/test_fighter_portraits_api.py -v`

Step 3: Minimal implementation

In `_fighter_dict()` in `api/services.py`, add:
```python
"portrait_key": f.portrait_key,
"portrait_url": f"/static/assets/portraits/{f.portrait_key}" if f.portrait_key else None,
```

Do not hardcode full hostnames.

Step 4: Run test to verify pass

Run:
`pytest tests/test_fighter_portraits_api.py -v`

Step 5: Commit

`git add api/services.py tests/test_fighter_portraits_api.py && git commit -m "feat: expose fighter portrait urls in api payloads"`

---

## Task 5: Add portrait slot to fighter side panel

Objective: put portraits where they immediately improve perceived quality.

Files:
- Modify: `frontend/templates/index.html`
- Modify: `frontend/static/css/style.css`
- Modify: `frontend/static/js/app.js`
- Test: `tests/test_dashboard_ui.py` or new frontend string test

Step 1: Write failing test

Add a simple template presence test:
```python
def test_fighter_panel_template_includes_portrait_slot():
    html = Path("frontend/templates/index.html").read_text(encoding="utf-8")
    assert 'id="panel-portrait"' in html
```

Step 2: Run test to verify failure

Run:
`pytest tests/test_dashboard_ui.py -k portrait -v`

Step 3: Minimal implementation

In `frontend/templates/index.html`, inside `.panel-header`, add a portrait block before the name:
```html
<div class="panel-portrait-wrap">
  <img id="panel-portrait" class="panel-portrait hidden" alt="Fighter portrait" />
  <div id="panel-portrait-fallback" class="panel-portrait-fallback">NO PHOTO</div>
</div>
```

In `frontend/static/js/app.js` within `showFighterPanel()`:
```javascript
const portraitEl = document.getElementById('panel-portrait');
const fallbackEl = document.getElementById('panel-portrait-fallback');
if (fighter.portrait_url) {
  portraitEl.src = fighter.portrait_url;
  portraitEl.alt = `${fighter.name} portrait`;
  portraitEl.classList.remove('hidden');
  fallbackEl.classList.add('hidden');
} else {
  portraitEl.classList.add('hidden');
  fallbackEl.classList.remove('hidden');
}
```

In CSS, make it look like a premium card element, not a random web avatar.

Step 4: Run tests to verify pass

Run:
`pytest tests/test_dashboard_ui.py -k portrait -v`

Step 5: Manual browser verification

Run app and confirm:
- portrait loads in side panel
- fallback looks intentional if missing
- image crop is stable across multiple fighters

Step 6: Commit

`git add frontend/templates/index.html frontend/static/css/style.css frontend/static/js/app.js tests/test_dashboard_ui.py && git commit -m "feat: render fighter portraits in side panel"`

---

## Task 6: Add compare-card and table thumbnail support

Objective: extend portraits beyond the side panel once the panel presentation is proven.

Files:
- Modify: `frontend/static/js/app.js`
- Modify: `frontend/static/css/style.css`
- Test: targeted template/JS string tests

Step 1: Add portraits to compare cards

Only add if it improves clarity and does not create layout slop.

Step 2: Add optional tiny thumbnails to roster/free-agent rows

Guardrails:
- keep rows readable
- do not inflate table height too much
- use tiny square or narrow vertical crop

Step 3: Verify in browser

Check dense screens for clutter.

Step 4: Commit

`git add frontend/static/js/app.js frontend/static/css/style.css tests/... && git commit -m "feat: extend fighter portraits to comparison and list surfaces"`

---

## Task 7: Add fallback + regeneration strategy

Objective: avoid brittle asset handling and make future art expansion sane.

Files:
- Modify: `simulation/portraits.py`
- Modify: `frontend/static/assets/portraits/README.md`
- Optional: create helper script under `scripts/`

Step 1: Define fallback order

If a bucket is missing assets:
1. same age band + style, broader region fallback
2. same age band only
3. generic fallback portrait

Step 2: Optional helper script

Create:
- `scripts/validate_portrait_manifest.py`

Responsibilities:
- ensure manifest files exist
- ensure no broken references
- report underfilled buckets

Step 3: Add test or validation invocation

Run:
`python3 scripts/validate_portrait_manifest.py`

Step 4: Commit

`git add simulation/portraits.py frontend/static/assets/portraits/README.md scripts/validate_portrait_manifest.py && git commit -m "chore: validate portrait library and fallback behavior"`

---

## Art Direction Spec

Portrait prompt target:
- MMA fighter broadcast headshot
- stylized illustrated realism
- shoulders-up framing
- neutral dark studio or arena-lite backdrop
- strong rim lighting
- sharp jaw/face silhouette
- sports-broadcast color grading
- no text, no logos, no gloves unless subtle
- no belts unless explicitly doing champion variants later
- no cinematic overkill, no fantasy debris

Style constraints:
- all assets must look like one game, not a Pinterest board
- same crop and camera height across the library
- same lighting family across the library
- same background treatment family across the library

Negative constraints:
- no exaggerated teeth grin sludge
- no hyper-detailed pores/skin shine
- no weird jewelry/props unless intentional archetype variant set exists
- no facial tattoos unless later supported by fighter metadata

---

## What NOT to Build Yet

Do not add in v1:
- live image generation inside the app
- champion-specific alt portraits
- injury-state portraits
- dynamic expression variants
- portrait editing UI
- portrait generation tied to nickname text

Those are all later luxuries.

---

## Verification Checklist

Must be true before calling the feature done:
- all seeded fighters have portrait_key
- portrait assignment is deterministic under the same seed
- API returns portrait_url cleanly
- fighter panel renders portrait without layout breakage
- missing assets fall back gracefully
- test suite passes
- browser QA confirms portraits increase perceived quality rather than visual chaos

Core verification commands:
- `pytest tests/test_seed_validation.py -k portrait -v`
- `pytest tests/test_fighter_portraits_api.py -v`
- `pytest tests/test_dashboard_ui.py -k portrait -v`
- `pytest tests -q`

Manual verification:
- open fighters from at least 10 different nationalities / ages / styles
- inspect side panel crop consistency
- inspect compare view clutter
- inspect free-agent and roster scanability if thumbnails are added

---

## Final Recommendation

Best execution order:
1. model field
2. deterministic assignment module
3. manifest + starter asset library
4. API exposure
5. side panel rendering
6. optional compare/list expansion

If you want only one high-ROI slice first, do this:
- portrait_key
- deterministic seed assignment
- portrait_url in API
- side panel portrait only

That gives the biggest perceived upgrade with the least chance of turning the UI into garbage.
