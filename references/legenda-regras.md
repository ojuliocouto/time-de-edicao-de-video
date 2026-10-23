# Regras da legenda cinematográfica

Vindas da antiga skill `cinematic-caption` (de terceiros, licença em
`references/legenda-LICENSE.txt`), que esta absorveu, com as mudanças pedidas
depois (modo trilho, mapa de planos, portão de aprovação). O texto
original é em inglês e foi mantido. **Nesta skill o modo é sempre `rail`
(trilho)**, e o motor `scripts/gerar_legenda.py` + `scripts/montar_legenda.py`
já implementa o caminho de camadas com alfa descrito em "Delivery". A
transcrição é a do `scripts/transcrever.py` sobre o montado (não a do
`hyperframes transcribe`, que destrói português sem `-m large-v3 -l pt`).

## Placement modes` section below overrides any conflicting instruction in the reference files. The references describe the `free` mode; where they assume roving placement, `rail` mode wins.

Read `references/legenda-hyperframes-commands.md` before running any CLI command; it carries the verified flags and the traps that silently ruin a pass. Read `references/legenda-style-system.md` completely before designing or editing captions. When the passage contains three or more designed cues, also read `references/legenda-dynamic-layout-recipes.md` completely before writing the caption plan.

## Inputs

Accept the active HyperFrames project plus any combination of:

- a source video or existing composition;
- a transcript, SRT/VTT, or word-level timing JSON;
- a requested time range;
- brand fonts, colors, or tone;
- optional requests for glow, graphic inserts, or sound effects.

Treat `$ARGUMENTS` as project, media, range, and style guidance. Discover missing project details locally when safe. Ask only when a missing choice would materially change the result.

## Placement modes

Two modes. Default to `free`. Switch to `rail` when the user asks for a calmer, more anchored caption, in any wording: "modo trilho", "legenda mais estática", "mantém a legenda embaixo", "anchored", "rail". Never mix the two inside one piece.

### `free` (default)

The original behaviour: every semantic group picks its own subject-relative anchor zone, and the passage moves through three to five layout states.

### `rail`

Ordinary captions live in **one fixed lower band for the whole piece** and step out of it only for a deliberate break-out.

- Choose the rail band once, from the intersection of every shot's safe area, and never move it. Same x, same alignment, every ordinary cue, every shot.
- **Anchor the band by its bottom edge, not its top.** The mode requires scale to change inside the rail, and a top-anchored block grows downward, so the band visibly drifts exactly when the emphasis lands. Bottom anchoring is the only reading under which "never drift" and "change scale inside the band" both hold.
- **The rail is anchored, not flat.** Keep the entire emphasis vocabulary working inside it: support-to-anchor weight steps, scale growth on the decisive word, a display face on one word inside the line, progressive builds at word starts. Only the position is frozen. A rail that never changes weight or scale has failed this mode.
- Roughly **75% of the runtime stays on the rail**.
- The other ~25% is the break-out: about **seven break-outs per minute of speech**, each holding 1.5-2.5 s.
- **The rate governs; the percentage is a consequence, not a second rule.** They diverge on short pieces, where the two produce different counts and neither is obviously right. An **argument beat** is a move in the reasoning, not a grammatical unit: a claim, its reversal, the evidence, the payoff, the offer, the call to action. One beat usually spans several sentences and several semantic groups, so counting semantic groups instead will overshoot badly, a ten-second passage can hold four groups and still be one or two beats. Below roughly 20 s, ignore both numbers and use one break-out per argument beat, with a floor of one: a ten-second piece carrying two distinct beats gets two, and the runtime share lands where it lands. Record the beat count as the justification.
- A break-out places its hero word **above the subject**, measured against the subject in that shot, not against an absolute top band. "Above" means above the eye line and clear of the face; it does **not** mean clear of the hair. A break-out without depth clears the whole silhouette; a break-out with depth deliberately lets the hair and outer head contour cross its lower strokes, which is the 10-22% overlap the depth rules ask for. The face and the mouth are off limits in both cases.
- **Position against the worst frame, not the average.** The subject drifts vertically inside a single break-out, 72 px over 1.65 s in one measured take, so no single height holds the overlap band across the whole cue. Take the highest subject top in the range as the reference, accept that other frames overlap less, and confirm the result with `scripts/occlusion.py` instead of assuming. A tight shot may put it near the frame top; a wide shot may put it near the middle. Re-measure per shot.
- The rail clears while a break-out is on screen. One idea per moment.
- After the break-out, return to the exact same rail position. Never drift.
- Break-outs are still chosen by the hero score in `references/legenda-style-system.md`. When a passage yields more candidates than the budget allows, keep the highest scores and demote the rest to an in-rail emphasis rather than raising the break-out count.
- **Depth is opportunistic, never a requirement.** A break-out does not have to sit behind the subject; it earns that only when the shot map marks it `depthEligible`, the matte passes `## Matte fitness test`, and the overlap can respect the occlusion budget and preserve identifying glyphs. On an insert, a tight shot, or a shot with no clean matte, the same break-out simply plays in front.

## Shot map

Required whenever the source is an edited piece rather than one continuous take. Build it before designing any cue.

1. Detect the hard cuts and record every shot's in and out point.
2. Classify each shot: `talking-head` (subject in frame, matte usable), `insert` (b-roll, screen capture, graphic, product), or `mixed`.
3. For every shot record: existing burned-in text, titles, lower thirds or UI; the usable negative space; and `depthEligible: true|false`.
4. Never place a caption over an insert's own text, interface, or the detail the insert exists to show. Move it to that shot's verified safe area, or leave the beat uncaptioned.
5. Generate subject cutouts only for the `talking-head` ranges that actually carry a break-out, following `## Subject cutout cost control`.

Refuse to design over footage that already carries burned-in captions or burned-in lettering. Ask for the export without them; captions layered over captions cannot be rescued. When the footage still needs cutting, trimming, or inserts, that belongs to the editing stage that runs before this one (etapas 1 a 5 desta skill): this skill preserves the edit it receives and never changes it.

## Subject cutout cost control

Applies to both modes. The examples below count break-outs because `rail` bounds them explicitly; in `free` mode, count the cues that actually carry depth instead.

Segmentation is the slowest step in the pipeline and runs at roughly 1.2 frames per second on Apple Silicon with CoreML, so its cost is set entirely by how many frames reach it. Fix the render frame rate, cut the frame count down, quote the user a time, then start.

- **Fix the render frame rate before generating any cutout.** Every rule here is relative to it, so deciding it afterwards means regenerating.
- **Match the render to the source when the source is slower than 30 fps.** HyperFrames defaults to 30 regardless of the footage, and 24 or 25 fps is the common case for camera and PAL material. Going from 25 to 30 has no honest operation: you cannot drop frames to gain frames, and interpolating is forbidden below. Set `data-fps` on the composition root, or pass `-f` to `render`.
- **Probe before committing.** Cut out one short range first, around a second, and put it through `## Matte fitness test`. Only generate the remaining ranges once that one passes. Segmentation is the most expensive step in the pipeline and a footage-wide failure looks identical on every range: discovering it on the first one costs a minute, discovering it on the last one costs the whole pass.
- **Cut out only the ranges that carry a depth cue.** Each range must fully contain its cue plus a half-second handle on each side, so the occlusion never drops out mid-word. A minute of footage with seven two-second break-outs needs about twenty seconds of cutout, not sixty.
- **Match the cutout to the render frame rate, not the source frame rate.** The composition samples the matte once per rendered frame, so a 60 fps cutout feeding a 30 fps render computes half its frames for nothing. Build a reduced working copy of the range for this step only.
- **Reduce the frame rate by dropping frames, never by interpolating or blending them.** A blended frame belongs to no instant of the source and will ghost against the footage under it.
- **Encode the working copy visually losslessly.** Dropping frames costs nothing, but re-compressing does, and the subject in the composite comes entirely from the cutout: a cheap working copy reads as a soft person over a sharp background.
- What has to match the base footage is the **sampled instant, not the declared frame rate**. At every rendered frame the cutout must show the same moment as the footage beneath it. A 30 fps cutout built by dropping every other frame of a 60 fps source satisfies this at a 30 fps render. Confirm it at three moving frames instead of trusting the numbers.
- **Never modify, re-encode, or replace the user's source file.** Working copies live beside it under their own names.
- Place a range cutout with `data-start` at the range in point, `data-duration` at its length, and `data-media-start` at 0.
- Start the cutout in the background and design the captions while it runs. The two do not compete for the same work.
- When the render frame rate is deliberately raised to match a high-frame-rate source, the cutout must match it too. Say what that costs before committing to it.

## Matte fitness test

Applies to both modes; `rail` only changes where the oversized word goes, never whether the matte can carry it.

> **Nesta skill (decidido com ela):** com o recorte da Vision (Mac), quem decide é
> o quadro ampliado (`snapshot --zoom`), não o número: o teste reprova por
> contraste cabelo escuro em parede escura mesmo quando a borda segue o cabelo,
> e heróis atrás da cabeça foram aprovados nesses casos em 5 anúncios. Com o
> remove-background (Windows e Linux), siga o número.

Generating a cutout is not the same as having usable depth. **Run `scripts/matte_fitness.py` on three frames with movement and let it decide.** It answers all three criteria below with numbers, and it exists because the alternative failed in practice: producing an unreadable diagnostic image, looking at it, and concluding something anyway. Its thresholds are calibrated against real footage, a shelf background scored 1.5-3.5 on edge contrast and is rejected, an acoustic-foam background scored 12.8-16.0 and passes, a flat wall scored 46.

The three criteria, for when you need to reason about a borderline result:

1. **The mask's top boundary follows the subject's real contour.** Brighten the source frame and read where the hair actually starts, then read where the mask starts. A mask that begins well above the hair is inflated; the word would be cut by a line floating in empty air, which reads as a smudge rather than as a person.
2. **The mask contains only the subject.** `u2net_human_seg` reads bright vertical shapes in a blurred background (a shelf, a lamp, a lit column) as a second person and welds them onto the silhouette. `scripts/clean_matte.py` removes those, and `--report-only` quantifies the damage before you commit.
3. **No hero word crosses a boundary that `clean_matte.py` created.** Its `--clip-above` line is a straight horizontal edge. It is invisible where nothing overlaps it and obvious where type does: the occlusion then reads as a horizontal wipe, not as hair. Keep the word entirely above that line, or drop depth for that shot.

When any of the three fails, the break-out plays in front. That is a full-strength result, not a fallback, verified on real footage, a foreground hero word carries the beat just as well.

A flat background wall gives a clean matte. A busy or blurred background with bright vertical shapes usually does not. Run the test rather than predicting from the look of the shot.

## Tooling

Three scripts ship with this skill. Use them instead of rebuilding the commands by hand: each one already carries a flag that took a wasted round to discover. `references/legenda-hyperframes-commands.md` holds the rest of the verified CLI flags and their traps.

```bash
# onde a silhueta do sujeito esta em cada instante: decide onde a palavra-heroi cabe
python3 ~/.claude/skills/time-de-edicao-de-video/scripts/subject_envelope.py cc-subject.webm --at 13.5,14.3,14.9 --bands 200,300,400

# recorte de um trecho, ja na taxa de quadros do render e com folga nas pontas
python3 ~/.claude/skills/time-de-edicao-de-video/scripts/make_cutout.py bruto.mp4 --start 13.2 --end 15.0 --fps 30 -o recorte.webm
python3 ~/.claude/skills/time-de-edicao-de-video/scripts/make_cutout.py bruto.mp4 --start 13.2 --end 15.0 --fps 30 -o recorte.webm --dry-run

# aprova ou reprova o recorte antes de confiar nele
python3 ~/.claude/skills/time-de-edicao-de-video/scripts/matte_fitness.py --fonte bruto.mp4 --matte recorte.webm --at 8.5,9.0,9.6 --matte-offset 7.55

# mede quanto da palavra o sujeito cobre de verdade
python3 ~/.claude/skills/time-de-edicao-de-video/scripts/occlusion.py --tipo camada-tras.webm --matte recorte.webm --at 8.5,9.0 --matte-offset 7.55

# limpa manchas que a segmentacao inventou no fundo
python3 ~/.claude/skills/time-de-edicao-de-video/scripts/clean_matte.py recorte.webm -o recorte-limpo.webm --clip-above 415
python3 ~/.claude/skills/time-de-edicao-de-video/scripts/clean_matte.py recorte.webm -o /tmp/x.webm --report-only

# composicao em camadas, de baixo para cima; @SEGUNDO posiciona um recorte de trecho
python3 ~/.claude/skills/time-de-edicao-de-video/scripts/composite_overlay.py bruto.mp4 tras.webm recorte-a.webm@7.55 recorte-b.webm@27.87 frente.webm -o final.mp4
```

Depois de qualquer edição nesta skill, rode os testes:
`python3 ~/.claude/skills/time-de-edicao-de-video/tests/rodar.py`.

`make_cutout.py --dry-run` prints the frame count and the time estimate without doing the work. Run it and quote that number to the user before starting a long segmentation.

## Required workflow

0. **When there is no project yet**, create one: `npx hyperframes init <nome> --video <arquivo>` from the parent directory. `init` refuses a directory that already holds files, so never point it at the folder the source video is sitting in; create a sibling and let it copy the video in. Then fix two things the scaffold gets wrong before anything else, both verified: set `data-width`/`data-height` to the source's own dimensions, because `init` always scaffolds 1920x1080; and add `data-start="0"` to the `<video>` and `<audio>` it wrote, because it omits it and `lint` fails immediately with `media_missing_data_start`.
1. Read the active project's instructions and the mandatory `hyperframes` skill. **This skill is the owning workflow for the pass; take only the domain-skill map from the router and skip its intent layer.** Its routing table will try to hand a captioning request to `/embedded-captions` or `/talking-head-recut` and ask for a `BRIEF.md`; do not follow that when the user asked for this skill by name. Load `talking-head-recut`, `hyperframes-core`, `hyperframes-animation`, `hyperframes-creative`, and `hyperframes-cli` when available. **When they are not installed, do not stop and do not install them mid-pass** (installing needs a session restart): read what you need straight off disk under `~/.claude/skills/<name>/`, which is where their references live anyway. If adding or changing audio, also load `media-use` and `hyperframes-audio`.
2. Inspect the existing composition, duration, dimensions, tracks, media paths, typography, palette, and motion sidecar. Do not rewrite unrelated scenes. Resolve the placement mode now, and when the source is an edited piece build the shot map before anything else.
3. Transcribe the media being captioned to word-level timing with the documented HyperFrames transcription workflow, and keep the transcript as a project artifact. Timing must come from the exact file in hand, so that every word start matches what is audible in it. If a long-pass transcript drifts from the audible speech, retranscribe short overlapping segments and align their local timestamps; never proportionally stretch inaccurate word timings across the media duration.
4. Edit speech into semantic groups and ordered display fragments, then assign each cue a role and emphasis level using `references/legenda-style-system.md`. Score hero candidates for semantic importance, proof value, rhetorical stress, and legibility; record why the chosen word is the hero. Do not promote a word merely because it is a noun or sounds visually interesting.
5. Inspect the start, midpoint, and end of every designed cue. Record the motion envelope of the face, mouth, hair, shoulders, hands, products, UI, existing text, and usable negative space. Choose a coherent sequence of subject-relative anchor zones. Vary layouts between argument beats, but keep one stable anchor for fragments that belong to the same sentence or parallel list.
   When using a foreground subject cutout, run `## Matte fitness test` first and drop depth for that shot if it fails. Then verify the cutout's start time, duration, scale, crop, and that its frames land on the same instants as the base footage at the render frame rate (see `## Subject cutout cost control`). Inspect moving hair, hands, and shoulders at multiple timestamps. If a faint duplicate edge remains despite matching timing, rebuild the cutout from the original source pixels plus the matte alpha instead of overlaying independently compressed RGB.
6. Write `cinematic-caption-plan.json` before implementation. Include the active `mode`, the `shotMap`, the chosen `railAnchor` when in rail mode, `breakOut` true/false and `depthEligible` per cue, plus cue timing, exact displayed text, `semanticGroupId`, `orderIndex`, role, emphasis, `heroReason`, placement, `anchorZone`, `layoutState`, `buildMode`, `flowDirection`, optional `persistenceGroup`, `foregroundText`, `heroText`, `stackGap`, subject motion envelope, depth strategy, `fillSource`, palette, `occlusionBudget`, motion preset, optional graphic support, and optional audio accent. In `rail` mode several of these have no meaning on most cues: write `persistenceGroup`, `foregroundText`, `heroText`, `graphic` and `audioAccent` as `null` rather than inventing content for them, and drop `stackGap` on any cue that is a single line.
7. Search the local HyperFrames catalog for relevant caption blocks before hand-authoring. Adapt strong matches to the current composition and brand; never copy another creator's logo, identity, or proprietary assets. **Expect to find nothing usable and move on quickly.** Verified: the catalog's `caption-*` components implement almost exactly what the guardrails below forbid, karaoke pills, colour sweeps, permanent neon, gradient fills, chromatic glitch. The closest relative ships landscape, pulls fonts from a remote CDN, and hardcodes its demo transcript. Take the structural contract if it helps and write the rest by hand.
8. Implement captions as the least invasive change: either a dedicated high-numbered overlay track in the current composition or a reusable `compositions/cinematic-captions.html` sub-composition. Namespace new IDs and variables with `cc-`.
9. Keep outer clip elements responsible for timing and layout. Animate inner wrappers. Use one paused, seek-safe timeline driven by HyperFrames time. Add or update the motion sidecar for every animated selector: it is an `index.motion.json` sitting next to the composition, which `check` discovers on its own, holding `{duration, assertions[]}` with the kinds `appearsBy`, `before`, `staysInFrame` and `keepsMoving`. `hyperframes-cli/references/lint-validate-inspect.md` carries the full contract. When the spoken phrase builds progressively, reveal its words or semantic fragments at their actual word starts instead of landing the completed lockup early.
10. If sound accents are requested, source local files through `media-use`, place them on dedicated audio tracks, synchronize their transient to the visual landing, and mix them under intelligible narration. Silence is an intentional option.
11. Run HyperFrames lint/check at cue midpoints and motion boundaries. Capture early, midpoint, and late frames for subject-layered heroes plus one chronological contact sheet. Review semantic timing, reading order, within-group spacing, controlled variation, face clearance, occlusion, and legibility, then iterate until checks pass.
12. Start a local preview and give the user the URL. Render only after the normal HyperFrames preview-and-approval gate.

## Outputs

Leave the project with:

- `cinematic-caption-plan.json`;
- caption markup or a reusable caption sub-composition;
- a complete motion sidecar;
- local media and SFX references only;
- representative cue snapshots;
- a chronological caption contact sheet for judging variation;
- a passing HyperFrames check;
- a preview URL and a short note describing hero and audio-accent choices.

## Review and approval gate

Never composite or hand over a final file before the user has approved the captions. Passing HyperFrames checks means the composition is valid, not that the design is right.

1. **Contact sheet first.** One chronological image of every cue midpoint. It is the cheapest way for the user to judge rhythm, placement and variation in a few seconds.
   **Judge rhythm on it, never defects.** At thumbnail width a soft matte edge, a straight clip line and a real hair contour are the same smudge, and chasing one costs more than the whole pass. Before changing anything because of something you saw on the sheet, confirm it with `snapshot --zoom` on that region at full resolution.
2. **Then a fast preview render**, draft quality, of the whole piece or of the range the user cares about.
3. **Present both together** with a short note: which words became heroes and why, where the break-outs landed, and anything the footage forced.
4. **Iterate.** Text, colour, position, timing, promoting or demoting a hero are all cheap. Re-render only what changed and show it again. Repeat until the user approves.
5. **Only after an explicit approval**, produce the final file.

## Delivery

Default to rendering the full composite to MP4 with `-q high --crf 18`. It is the simplest path and the source is compressed exactly once, which is visually transparent for camera footage. Measured references, which vary more than they look: 15 s at 1080x1350 without cutouts took about 82 s, while 10 s at 1080x1920 with two cutouts took 103 s, more than double the cost per second of footage. Resolution and cutout count drive it, so measure your own first pass instead of planning off these.

**Exception, verified: a long piece carrying subject cutouts does not finish this way.** At 94 s with four cutouts the capture stalls on a frame where a cutout is active, twice, at different points; `--workers 3` gets further and still stops. Short pieces with one cutout render fine. When the piece is long and uses depth, switch to the layered path below, it is also faster.

The alpha-layer path exists for when the user needs the captions as a separate asset, or wants the source to pass through ffmpeg rather than the capture pipeline. It has two hard constraints, both verified:

- The layer needs its own composition: `background: transparent` on `html, body` and **no base video**. With the base video the output is fully opaque and useless as an overlay.
- **An alpha render cannot contain the subject cutout video.** It stalls mid-capture and times out, in both `webm` and `mov`, with no compile error. When the piece uses depth, split it: one alpha layer for the type behind the subject, one for the type in front, and composite them around the cutout with `scripts/composite_overlay.py` in the order back type, cutout, front type. That composite was verified visually identical to the full render.

Do not sell the alpha path as the faster one on short pieces: on a 15 s piece it came to about 71 s against 82 s. On a long piece with cutouts it is not a preference, it is the only path that finishes, and there it wins outright: 94 s composed in about 4.6 min against a full render that never completes. `scripts/composite_overlay.py` handles this: pass a range cutout as `arquivo.webm@INICIO` and it derives the offset and the `enable` window from the file's own duration. `references/legenda-hyperframes-commands.md` carries the equivalent hand-written call.

Whichever path is used, the user's source file is never modified, renamed, or replaced.

## Guardrails

- Keep phrases concise and semantic; do not reproduce every filler word.
- Use mixed case for ordinary support captions. All caps belongs to hero words, acronyms, short proof labels, and a deliberately chosen CTA keyword. A hero in mixed case is a valid choice when the word is a brand or a proper name whose casing carries meaning, `Claude` and `iPhone` among them; everywhere else the hero goes uppercase.
- Build typography as a hierarchy: a clean sans for support, a genuine heavy or condensed display face for hero words, and an occasional editorial serif or italic accent for conversational actions such as a CTA. Bundle every chosen face locally: this skill ships `assets/fonts/Inter-Variable.ttf` (support and anchor, real weights 100-900) and `assets/fonts/Anton-Regular.ttf` (hero display), both covering the Portuguese accented set. Copy them into the project rather than downloading anything, so a pass never depends on the network. Offline fallbacks already on macOS, if a different look is wanted: `Impact.ttf`, `Arial Black.ttf`, `DIN Condensed Bold.ttf`.
- Declare only font weights that exist in the bundled file. Never synthesize a heavy weight from a lighter font, force thickness with oversized strokes, or tighten tracking until adjacent glyphs merge. Inspect repeated, narrow, and crossbar-heavy letters at full resolution.
- Spacing given as a multiple of the support size is a **computed pixel value**, not a CSS `em`. Writing `gap: 0.28em` resolves against the container's own font size, which is usually the inherited 16 px, so a 17 px gap silently becomes 4.5 px and words run together into `masdeixaeu`. Do the multiplication and write the px.
- Keep one primary visual idea per cue and one dominant hero moment per sentence or argument beat.
- Prefer white for normal support captions, carried by the layered halo in `references/legenda-style-system.md`, applied to every caption rather than switched on per shot. Use black only when the actual frame makes white illegible even with the halo. Never protect captions with a full-width gradient plate: it reads as a subtitle bar and darkens inserts that are not yours to alter.
- Do not cover a face, mouth, key gesture, product, UI, or important property detail.
- When a clean matte exists, create power through proximity: place important hero words close enough to the subject for intentional depth instead of floating them high in unused negative space. Prefer 10–22% overlap around hair or outer head contours and reposition whenever identifying letters become ambiguous.
- Do not repeat a complete layout recipe across unrelated argument beats. When adjacent fragments form one sentence or parallel grammatical list, lock them to one anchor zone and treatment unless the subject or shot changes; vary timing or scale subtly instead of making the viewer chase the text.
- Choose one reading direction for each semantic group. Later fragments must continue that path; do not jump down, back up, and down again for the sake of variety.
- Keep captions level by default. Use rotation only when the source brand or explicit direction makes the angle meaningful; arbitrary tilting is not a substitute for composition.
- Preserve identifying letters in hero words. Subject depth may cross outer strokes, but reposition or resize whenever the overlap makes the spelling uncertain.
- For sequential instructional graphics, keep completed evidence visible when the next action depends on it. Place standalone screenshots, folders, and files natively; do not wrap every asset in a generic card.
- Build CTAs as one compact ordered cluster whose setup, action, keyword, and closing line reveal in reading order.
- Keep the CTA action word visually adjacent to its keyword; treat them as one unit rather than two labels in competing zones.
- Do not default to bottom-center karaoke, word pills, rainbow coloring, permanent neon, or a large word on every cue. `rail` mode is not an exception to this: an anchored band that still steps weight, scale and emphasis is a designed rail, and word-by-word karaoke highlighting stays forbidden in both modes.
- Use glow as a brief emphasis treatment, not as the base caption style.
- Default translucent hero words to neutral silver-white tinted glass with visible source footage, a fine rim, and an optional soft light sweep. Introduce a restrained hue only when the brand, footage, or meaning justifies it. Do not add repeating scan lines or banded textures unless the user explicitly requests that graphic treatment. Avoid pastel rainbow fills, heavy bevel/extrusion, and decorative depth that makes the word feel like a detached title.
- Do not claim that text is behind a person unless a real subject matte, cutout, or defensible occlusion mask creates that depth, and it passes `## Matte fitness test`. Without one, place the oversized word in verified negative space. Existing is not the same as usable: an inflated or invented matte produces a worse result than no depth at all.
- A subject cutout must be frame-locked to the base footage and free of visible halos, doubled silhouettes, shadows, or color shifts. Do not add drop shadow to the subject layer. Prefer original source RGB recombined with the matte alpha and an alpha-capable high-quality local encode. A cutout may legitimately declare a lower frame rate than the source when `## Subject cutout cost control` applies; what must never differ is the instant each rendered frame shows.
- Use sound effects as punctuation, not wallpaper. Do not add an effect to every phrase. Rotate the palette across adjacent hero beats: reserve shimmer for one luminous reveal, use no more than one primary accent per landing, and stack effects only when the combination has a specific narrative purpose.
- Write only caption-stage files. Leave every other file already in the project untouched.
- Preserve creator-safe margins and the project's platform safe zone.
- In `rail` mode, do not let the rail go visually flat: if no cue in a passage changes weight, scale, or emphasis, the mode is being applied wrong.
- In `rail` mode, do not exceed the break-out budget to "make it dynamic". Dynamism inside the rail comes from hierarchy, not from moving the text around.
- Do not tie the break-out to depth. A hero word in front of the subject is a valid break-out; faking depth without a matte is not.
- Match the user's brand before the reference aesthetic.
- Do not publish, upload, or replace source media without explicit approval.

## Completion standard

The result is complete when the captions are timed to meaning, visually integrated with the subject, restrained enough to preserve hierarchy, seek-safe, locally reproducible, and verified in HyperFrames. A technically valid fixed subtitle strip is not a cinematic-caption result. In `rail` mode the band is fixed by design, so the same standard is met through hierarchy inside the band plus the break-outs, never through an undesigned uniform strip.
