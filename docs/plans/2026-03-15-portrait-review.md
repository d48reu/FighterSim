# How to Review Fighter Portraits

1. Start the game normally.
2. Open the save you want to inspect.
3. Go to one of these surfaces:
   - Roster
   - Fighters
   - Free Agents
4. Click individual fighters to open the side panel.
5. Review at least 10-15 fighters across different buckets:
   - young prospects
   - prime fighters
   - veterans
   - strikers
   - wrestlers
   - grapplers
   - at least 3 weight classes
6. Look for these failure modes:
   - sameface repetition
   - awkward crop
   - portrait too small / weak in panel
   - face feels uncanny
   - style clashes with arena UI
   - weight-class accent border feels too loud or too weak
7. Ask these yes/no questions:
   - does this make the game feel more premium?
   - does it feel like one coherent art pack?
   - do any portraits actively cheapen the game?
8. If you find bad examples, note:
   - fighter name
   - portrait bucket feel (prospect/prime/veteran, striker/wrestler/grappler)
   - what specifically looks wrong

Current implementation notes:
- portraits are deterministic, so the same fighter should keep the same portrait
- current pack is a starter stylized SVG library, not final production art
- side panel is the first portrait surface; broader rollout can come later
