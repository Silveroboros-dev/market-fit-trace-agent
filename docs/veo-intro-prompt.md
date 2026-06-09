# Veo Intro Clip — Prompt and Direction

An optional ~8-second Veo-generated clip used as the **visual bed under the
0:00-0:18 hook** of the demo video (see `docs/final-demo-script.md`). It is a
production-value flourish; it plays *while the narration runs*, so it costs no
extra time.

The clip **poses the problem only** (a thesis lost in a field of look-alike
markets) and lets the live demo deliver the resolution. The amber accent appears
only on the person's thesis, never on a resolved "winner." The clip carries **no
text** — the title is added in post (see "Title overlay" below).

## Where it sits (shot list)

```text
0:00  Veo clip fills the screen; the hook narration starts immediately over it.
0:06  Title overlay fades into the clip's empty top third (added in your editor).
0:08  CUT to the live app; type the TPU thesis in. Same narration continues.
0:18  Still on the app: "what it is + why it matters" (unit tests for beliefs).
0:30  CUT to docs/assets/mfta-spine.svg (propose -> decide -> observe).
0:42  CUT back to the app: the TPU trace-repair demo (it catches itself).
```

Because there is no amber "winner" to cut on, cut from the unresolved gray grid
straight to the live app as you type the thesis — the product becomes the
resolution the clip withholds.

## Prompt (use this — hardened, text-free)

```text
Clean, modern, premium minimal motion-graphic on a flat solid warm cream
background (hex #F2ECE0) - no paper texture, no grunge, no vintage, no sepia,
evenly lit and crisp. About two dozen identical blank rounded-rectangle cards in
soft muted gray float and gently drift in a calm grid, softly overlapping; the
card surfaces are completely smooth and empty - no charts, no bars, no symbols,
no markings. One card near the center carries a single thin glowing amber line
(hex #C8861E) - the one "belief" - and slowly gets surrounded and visually lost
among the identical gray cards. The camera slowly dollies forward through the
floating cards with shallow depth of field. Absolutely no text anywhere: no
letters, words, numbers, percentages, labels, titles, captions, watermarks, or
logos of any kind; every surface stays blank. Smooth, calm, slightly suspenseful
pacing over 8 seconds, ending on the full grid of identical drifting gray cards,
none highlighted, with the upper third left clean and empty. Strict palette:
cream, ink black, muted gray, and a single amber accent used only on the one
belief card. Flat modern editorial style, cinematic, 16:9.
```

Negative prompt (paste into Veo's negative-prompt field if it has one):

```text
text, letters, words, numbers, percentages, labels, captions, title, watermark,
signature, logo, UI, charts, graphs, bars, paper texture, grunge, vintage, sepia,
distressed, torn paper, faces, hands
```

## Lesson: cues that produced a mess (avoid them)

An early, more literal "prediction-market tiles" take came back with a garbled
hallucinated title ("PEMEST / B12FEELCCLY") and broken labels ("Ynarket",
"50/No") on grungy sepia parchment. Causes, all now removed from the prompt:

- `Yes/No`, `probability`, `percentages`, `two-bar`, `market` labels, `monospace
  tick marks`, `charts/graphs/bars` -> Veo renders (broken) text on the tiles.
- `paper texture` / `matte paper` -> grungy vintage sepia instead of clean cream.
  Use "flat solid cream, no texture."
- the word `title` in the prompt -> it hallucinates a (gibberish) title. Leave the
  top third empty and add the real title in post.

Generated video cannot render legible text. Keep every surface blank.

## Title overlay (added in post, not by Veo)

```text
MARKET FIT TRACE AGENT
an Epistemic Ledger project
```

Use **Market Fit Trace Agent** (the submission / repo name), not "Epistemic
Ledger" — that is the parent project, and PUBLIC_REPO_BOUNDARY.md says not to
present this public artifact as the full Epistemic Ledger product. The "an
Epistemic Ledger project" kicker nods to the parent without overclaiming.

Style reference: `docs/assets/mfta-title-card.svg`. Add it in Google Vids with
the live text tool (recommended) or as a transparent PNG overlay — see the demo
notes. Place it in the clip's empty top third, fade in around 0:06.

## Optional: resolution ending (not used)

We chose the problem-only ending. If you ever want the clip to also show the
answer, replace the ending sentence with:

```text
It ends decisively on one card resolving into a crisp, confident amber glow
(hex #C8861E), lifted above the others while the rest desaturate and blur into
shallow depth of field, with the upper third left clean and empty.
```

Trade-off: prettier final frame, but it previews the payoff before the live demo
earns it.

## Generation tips

- 16:9, ~8 seconds.
- Keep the "no text / no faces / no logos" guards and the negative prompt: gen
  video renders text as gibberish and faces as uncanny.
- Generate 3-4 takes and pick the cleanest; gen-video is a slot machine.
- Keep audio out from under the voiceover (or a single soft ambient swell, low).
- If no take is clearly good, cut it and open live. A clean product open beats a
  mediocre generated one — these are Arize-track judges, not a Veo showcase.

## Palette reference (match the diagrams)

```text
cream background  #F2ECE0
ink / text        #1E1B16
muted gray        #8A8175
amber accent      #C8861E   (thesis only; never a "winner")
```
