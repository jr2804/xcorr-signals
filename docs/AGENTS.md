# docs/ — Documentation DOX

## Purpose

Site content, navigation, and figure assets for the xcorr-signals
documentation. Owned by the root AGENTS.md contract; this file adds local
rules only.

## Local Contracts

- Authoring standards: `.agents/skills/project-docs/SKILL.md` (Diátaxis,
  nav registration, frontmatter `title`).
- Figures: `docs/assets/images/*.svg` are **generated** by
  `scripts/gen_examples.py` and `scripts/gen_math_figures.py` — never
  hand-edit; rerun the relevant script instead. Keep each SVG under 10 MB
  (rasterize heatmaps, downsample grids).
- Example figures use **Hilbert envelope** (`hilbert_envelope=True`) for
  clean, single-peak visualisations; raw CCF side-lobes would clutter the
  documentation plots.
- Diagrams: Mermaid fences (`pymdownx.superfences` custom fence
  `mermaid`), defined in `zensical.toml`.
- Navigation: every `.md` page must appear in `nav` in `zensical.toml`.
- Links: all intra-doc references are `relative` (no `docs/` prefix), so
  pages work both in the raw markdown and in the rendered GitHub Pages site.
- Signals in examples: deterministic noise bursts with silence margins at
  48 kHz — no periodic tones (ambiguous xcorr peaks). Degradation keeps
  peaks below 100 %.

## Verification

```bash
mise run format-md   # rumdl across docs/
mise run docs        # zensical build (strict)
```

## Child DOX Index

None — no subdirectories own their own contracts.
