# CrowdLens brand and rebrand plan

Date: 2026-10-01

## Product identity

- Name: **CrowdLens** (one word, capital C and L).
- Tagline: **Explore how people respond.**
- Descriptor: **AI scenario simulation**.
- Positioning: Turn documents into simulated conversations and reactions, compare
  scenario assumptions, and inspect evidence behind the resulting analysis.
- Voice: Clear, curious, and grounded. Say “explore,” “simulate,” and “compare.”
  Avoid promises such as “predict everything” or guaranteed real-world outcomes.
- Privacy language: Local-first, with optional hosted providers. Do not promise
  that all data stays local regardless of configuration.

## Visual identity

The mark uses a lens framing three people to represent examining multiple
perspectives. Retain the existing black, white, and orange interface palette for
continuity: ink `#171717`, white `#ffffff`, accent `#ff4500`, and pale accent
`#fff5ef`. The favicon simplifies the mark for small sizes. SVG assets scale
without raster blur and require no external image service.

Assets:

- `frontend/public/crowdlens-mark.svg`: home-page mark.
- `frontend/public/crowdlens-icon.svg`: browser favicon.
- `static/image/crowdlens-banner.svg`: README banner.

## Implementation sequence

1. Update workflow headers, landing-page copy, browser title, metadata, and assets.
2. Rename package metadata and backend display labels together with lockfiles.
3. Update README, current architecture, roadmap, and migration documentation.
   Preserve upstream attribution and historical audit records.
4. Run existing test suites and a production build; check rendered desktop and
   mobile pages and audit remaining legacy references.

This pass completes steps 1–4. Verification results are recorded below.

## Compatibility and provenance

This is a product rebrand, with no storage migration required. Retain:

- Existing SQLite database filenames, uploads, and generated run artifacts.
- Existing Compose service names, container names, and volumes.
- Existing logger namespaces and configuration keys,
  persisted IDs, and any legacy browser settings.
- The existing `origin` remote remains available for the original checkout.
  The `crowdlens` remote points to the new CrowdLens repository.
- Docker releases from the new repository use the `crowdlens` image namespace.
  Existing deployed images and runtime service names are unaffected.

The AGPL license, original author metadata, and credits remain intact. Old
Legacy artwork remains in the repository as legacy material and is no longer
referenced by the active landing page or README. Historical specs and plans use CrowdLens terminology in this documentation
revision; their dates and recorded measurements remain unchanged. Historical
checkout paths in audit metadata are expressed relative to the repository root.

## Release follow-up

Domain and trademark availability have not been checked. Before a public launch,
check the intended markets and domain, and capture fresh screenshots from the
released app. The code is published separately at
[alinojoumi8/crowdlens](https://github.com/alinojoumi8/crowdlens); the original
repository remains intact.

## Verification

- `UV_PYTHON=3.11 npm run check`: 251 backend tests, 11 frontend unit tests,
  and 4 component tests passed; Vite production build succeeded.
- Browser review: CrowdLens title, loaded mark, desktop home page, and Cases
  navigation/header verified. At 390 × 844 the home page fits the viewport
  without horizontal overflow; navigation wraps and the dashboard stacks.
- Current frontend source and generated bundle contain no active legacy
  display labels. Remaining references are repository links, attribution,
  historical records, or documented compatibility identifiers.
- Relative links in updated documentation and SVG XML validated;
  `git diff --check` passed.
- No simulation or hosted-model evaluation was triggered for this rebrand.
  Existing test results verify application behavior, not forecasting accuracy.
