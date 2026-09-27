# emfau Game Ops Dashboard

Static, mobile-first dashboard for game projects, portal submissions, portal research and performance snapshots.

**Live dashboard:** [emfau88.github.io/dashboard](https://emfau88.github.io/dashboard/)

## Why this structure

- `index.html` = presentation and rendering logic.
- `data.json` = the information you maintain.
- Public GitHub repository, branch, commit and workflow data is loaded automatically and cached briefly in the browser.
- No framework, build process or database.
- Works on GitHub Pages or any static host.

## Update routine

Most maintenance should happen only in `data.json`.

GitHub activity does not need to be copied into the dashboard. For each portal upload, only pin the uploaded commit once as `deployedCommit` or `submittedCommit`; the dashboard compares that immutable commit with the current configured branch.

### Record a new submission

Find the game and portal:

```json
"gamemonetize": {
  "status": "submitted",
  "submitted": "2026-09-27",
  "notes": "Initial submission"
}
```

### Record approval / release

```json
"gamemonetize": {
  "status": "live",
  "submitted": "2026-09-27",
  "published": "2026-09-29",
  "latestPlays": 245,
  "playsAsOf": "2026-10-02",
  "rating": null,
  "notes": "Approved and distributed"
}
```

### Add a performance snapshot

Append to `metricsHistory`:

```json
{"date":"2026-10-02","platform":"kongregate","plays":1400,"rating":2.9}
```

### Change portal research

Keep `qualityRange`, `qualityRangeConfidence`, `reach` and `researchNote` separate. Never turn an operator marketing claim into a measured fact.

## Status values

Use these consistently:

- `development`
- `planned`
- `not_submitted`
- `submitted`
- `review`
- `live`
- `rejected`

## Portal-fit values

- `very_good`
- `good`
- `test`
- `weak`
- `unknown`
- `rejected`

## GitHub Pages

Put the folder contents at the repository root and enable GitHub Pages for that branch. Because `index.html` fetches `data.json`, do not test by double-clicking the HTML file. Run a local web server instead:

```bash
python -m http.server 8000
```

Then open `http://localhost:8000`.

## Recommended next upgrades

1. Automatic daily Kongregate/Y8 snapshots where public metrics can be fetched reliably.
2. Revenue / RPM fields per portal.
3. Build/version hash per submission so every portal can be tied to an exact game build.
4. Small edit form that writes JSON through GitHub later, if manual JSON editing becomes annoying.
