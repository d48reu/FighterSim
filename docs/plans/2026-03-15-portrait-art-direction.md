# Fighter Portrait Art Direction Spec

Goal: replace the starter SVG portrait pack with a stronger, consistent portrait library that makes FighterSim feel premium instead of procedurally cheap.

Recommended style: stylized sports-broadcast illustrated headshots.

Not recommended for v1:
- full photoreal faces
- multiple competing art styles
- full-body character art
- fantasy-comic exaggeration

---

## Visual North Star

The portraits should look like:
- premium fight-card profile art
- TV broadcast shoulder-up athlete headshots
- slightly posterized / illustrated realism
- dramatic but controlled lighting
- clean silhouette and face readability at small sizes
- consistent background treatment across the whole roster

They should not look like:
- Midjourney face soup
- random influencer photos
- glossy mobile-game fantasy cards
- highly detailed oil paintings
- uncanny fake photography

---

## Composition Rules

Every portrait should follow the same basic composition:
- framing: shoulders-up
- camera: straight-on or slight 3/4 angle
- crop: face centered, top of hair not clipped, shoulders visible
- eyes roughly in the upper third
- background: dark neutral studio or subtle arena-broadcast backdrop
- no text baked into image
- no logos baked into image
- no belt/champion props in base portraits
- no gloves raised unless the whole library uses that convention

Canvas target:
- 192x240 minimum for starter pack
- larger source art okay, but crop consistently to portrait card ratio

---

## Lighting Rules

Lighting should feel like televised combat-sports media day:
- dark base environment
- one strong key light
- subtle rim/accent light
- mild color accent allowed
- no blown highlights
- no deep horror shadows

Weight-class accent guidance:
- Flyweight: violet accent
- Lightweight: cyan accent
- Welterweight: emerald accent
- Middleweight: amber accent
- Heavyweight: red accent

This accent should be subtle. It should feel like branded lighting, not a neon nightclub.

---

## Face / Styling Rules

Aim for:
- strong facial structure
- athletic presence
- believable age band
- neutral to intense expression
- direct, readable likeness archetypes

Avoid:
- huge toothy smiles
- weird teeth detail
- glossy plastic skin
- over-rendered pores
- asymmetrical nightmare eyes
- random facial tattoos unless metadata supports it later
- random jewelry / chains / hats / props

Expression range:
- calm focused
- stern
- slightly confrontational

Do not use:
- comedy expressions
- yelling faces
- exaggerated smirks

---

## Wardrobe Rules

Base portrait wardrobe should be minimal and consistent:
- dark athletic top, hoodie, or neutral fight-camp apparel
- no brand marks
- no championship belts in the default pack
- no busy costume elements

We are selling the fighter identity, not fashion styling.

---

## Variation Strategy

Use controlled variation only through these axes:
- age band: prospect / prime / veteran
- style vibe: striker / wrestler / grappler
- region flavor: broad, subtle, non-caricatured

Do not overfit every nationality literally.
Do not create exotic costume shorthand.
Subtle phenotype/background variation is enough.

The game still lacks a gender field, so keep the first production pass safely broad and consistent.

---

## Prompt Framework

Base prompt template:

"Stylized broadcast-sports illustrated portrait of a professional MMA fighter, shoulders-up headshot, athletic build, intense calm expression, clean face readability, dark studio background with subtle arena lighting, premium sports game profile art, posterized realism, controlled dramatic rim light, no text, no logo, no props, high consistency, centered composition"

Age-band modifiers:
- prospect: "younger adult fighter, fresher face, lean athletic presence"
- prime: "prime-age fighter, sharp confident presence, peak athletic look"
- veteran: "older experienced fighter, slightly weathered face, seasoned presence"

Style modifiers:
- striker: "slightly sharper posture, quick hands vibe, cleaner angular energy"
- wrestler: "compact powerful neck and shoulders, grounded powerful posture"
- grappler: "calm calculating presence, technical composed look"

Weight-class accent modifier:
- "subtle [violet/cyan/emerald/amber/red] broadcast lighting accent"

Negative prompt / exclusions:
- "no text, no watermark, no extra fingers, no gloves in frame, no championship belt, no tattoos unless intentional, no jewelry, no screaming, no grin, no crowd scene, no photo-real skin pores, no fashion photoshoot styling"

---

## Example Prompt Set

Prospect striker:
"Stylized broadcast-sports illustrated portrait of a professional MMA fighter, younger adult fighter, shoulders-up headshot, lean athletic presence, intense calm expression, dark studio background, subtle cyan broadcast lighting accent, premium sports game profile art, posterized realism, controlled dramatic rim light, centered composition, no text, no logos, no props"

Prime wrestler:
"Stylized broadcast-sports illustrated portrait of a professional MMA fighter, prime-age fighter, shoulders-up headshot, compact powerful neck and shoulders, grounded powerful posture, stern expression, dark studio background, subtle emerald broadcast lighting accent, premium sports game profile art, posterized realism, controlled dramatic rim light, centered composition, no text, no logos, no props"

Veteran grappler:
"Stylized broadcast-sports illustrated portrait of a professional MMA fighter, older experienced fighter, slightly weathered face, shoulders-up headshot, calm calculating presence, dark studio background, subtle amber broadcast lighting accent, premium sports game profile art, posterized realism, controlled dramatic rim light, centered composition, no text, no logos, no props"

---

## Quality Bar

A portrait is acceptable only if:
- it reads clearly at small size
- the face is not uncanny
- the crop matches the library
- it feels like the same game as the other portraits
- it does not distract from the UI

Kill a portrait if:
- sameface is obvious
- eyes/teeth are weird
- lighting is inconsistent with the pack
- it looks too photographic next to the rest
- it looks like generic AI fantasy slop

---

## Packaging Guidance

Build the next real portrait pack in batches:
- Batch 1: 24 portraits
- Batch 2: expand to 48
- Batch 3: expand toward 80+

Review portraits in-game, not only as loose images.
A portrait that looks fine alone can still look bad in the panel.

---

## Final Rule

Consistency beats ambition.
A smaller coherent library will make FighterSim feel more premium than a giant photoreal mess.
