# Smart EDA Interface System

Updated: 2026-06-12

## Direction

Smart EDA should feel like a data-quality command center for analysts and data engineers. The first scan should answer: what ran, what verdict was returned, which risks matter, which schema links were inferred, and where the full report/artifacts are.

## Domain Cues

- Pipeline layers: ingest, profile, detect, verdict, report.
- Evidence objects: findings, severity, relationships, safe joins, guardrail status.
- Output surfaces: JSON artifacts, HTML report, markdown fallback, diagnostic charts.
- Data engineering concepts: schema, primary key, foreign key, fact table, cross-table analysis.
- Quality signals: READY, WARN, NOT_READY, critical/high/warn/info distribution.

## Foundation

- Layout: dense workbench, not landing page. Left control rail, right result review surface on desktop; stacked flow on mobile.
- Depth: border-first with subtle surface shifts and restrained shadows for major panels only.
- Radius: 8px panels/cards, 6px compact controls, pill radius only for status chips/badges.
- Spacing: 4px/8px scale; 12-18px panel padding, 8-14px dense component gaps.
- Typography: Inter for UI text; monospace tabular numbers for IDs, file names, counts, timestamps, and schema paths.

## Color Tokens

- Canvas: light neutral grid surface `#f4f6f8`.
- Surface: white panels with soft inset `#f8fafb` and `#eef4f2`.
- Brand: teal `#0f766e` for primary action and accepted evidence.
- Warning: amber `#b45309`; High: orange `#c45a08`; Danger: red `#b42318`.
- Info accent: restrained blue `#334e9f` only for non-blocking metadata.
- Dark mode mirrors the same roles with surface shifts instead of heavy shadows.

## Reusable Patterns

- Result hero: verdict mark + rationale + dataset meta + severity distribution.
- Severity map: horizontal bars driven by real summary counts, never hard-coded.
- Pipeline rail: L0-L4 layer context in the control panel.
- Evidence panels: bordered sections with compact headings, fact grids, tables, and warnings.
- Report shell: top guardrail chip, verdict banner, metadata grid, two-tab AI/ydata structure.
- Statistical workbench: before embedding ydata, show a data-science overview with real metric cards, log-scaled shape bars, missingness/duplicate meters, severity distribution, and an interactive profile viewer frame.
- Data science report narrative: start with an executive brief, immediate-attention issue cards, guardrail provenance, editor interpretation cards, then analyst evidence cards with emphasized code tokens and bullet blocks.
