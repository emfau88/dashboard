# emfau Game Ops Dashboard

Statisches, mobile-first Dashboard für Spieleprojekte, Portal-Einreichungen, Portal-Recherche und Performance-Snapshots.

**Live-Dashboard:** [emfau88.github.io/dashboard](https://emfau88.github.io/dashboard/)

## Aufbau

- `index.html` enthält Darstellung und Rendering-Logik.
- `data.json` enthält die manuell gepflegten Informationen.
- Öffentliche GitHub-Daten zu Repositories, Branches, Commits und Workflows werden automatisch geladen und kurzzeitig im Browser zwischengespeichert.
- Kein Framework, keine Datenbank und kein lokaler Build-Prozess.
- Bereitstellung über GitHub Pages oder jeden anderen statischen Hoster.

## Pflege

Die meisten Änderungen erfolgen ausschließlich in `data.json`.

`qualityScore` ist eine manuelle interne Orientierung auf einer Skala von 0 bis 100. Er ist kein Messwert eines Portals und wird deshalb im Dashboard ausdrücklich als interner Qualitätsscore bezeichnet. Ein weiterer prozentualer Reife-Score wird nicht geführt, weil dafür keine objektive Berechnungsgrundlage vorlag.

GitHub-Aktivitäten müssen nicht in das Dashboard kopiert werden. Bei einem Portal-Upload wird nur einmal der hochgeladene Commit als `deployedCommit` oder `submittedCommit` festgehalten. Das Dashboard vergleicht diesen unveränderlichen Commit anschließend automatisch mit dem aktuellen konfigurierten Branch.

### Neue Einreichung erfassen

Beim jeweiligen Spiel und Portal:

```json
"gamemonetize": {
  "status": "submitted",
  "submitted": "2026-09-27",
  "sourceBranch": "main",
  "submittedCommit": "vollständige-commit-sha",
  "notes": "Erste Einreichung"
}
```

### Annahme oder Veröffentlichung erfassen

```json
"gamemonetize": {
  "status": "live",
  "submitted": "2026-09-27",
  "accepted": "2026-09-29",
  "published": "2026-09-30",
  "sourceBranch": "main",
  "deployedCommit": "vollständige-commit-sha",
  "notes": "Angenommen und veröffentlicht"
}
```

`accepted` und `published` können identisch sein. Wenn nur das Veröffentlichungsdatum bekannt ist, reicht `published`; das Dashboard zeigt es als „Akzeptiert/Live“ an.

### Ablehnung erfassen

```json
"coolmath": {
  "status": "rejected",
  "submitted": "2026-08-16",
  "rejected": "2026-08-22",
  "submittedCommit": "vollständige-commit-sha",
  "notes": "Lizenzanfrage abgelehnt"
}
```

Fehlt ein historisches Entscheidungsdatum, wird im Dashboard bewusst „Datum fehlt“ angezeigt. Es wird kein Datum geschätzt.

### Performance-Snapshot ergänzen

An `metricsHistory` anhängen:

```json
{"date":"2026-10-02","platform":"kongregate","plays":1400,"rating":2.9}
```

### Portal-Recherche ändern

`qualityRange`, `qualityRangeConfidence`, `reach` und `researchNote` getrennt halten. Eine Marketingangabe des Betreibers darf nicht als gemessener Fakt dargestellt werden.

## Statuswerte

Diese internen Werte konsistent verwenden:

- `development`
- `planned`
- `not_submitted`
- `submitted`
- `review`
- `live`
- `rejected`

## Portal-Eignung

- `very_good`
- `good`
- `test`
- `weak`
- `unknown`
- `rejected`

## Lokal öffnen

Da `index.html` die Datei `data.json` lädt, funktioniert ein Doppelklick auf die HTML-Datei nicht zuverlässig. Stattdessen im Repository starten:

```bash
python -m http.server 8000
```

Danach [http://localhost:8000](http://localhost:8000) öffnen.

## Mögliche spätere Erweiterungen

1. Automatische tägliche Kongregate-/Y8-Snapshots, sofern öffentliche Metriken zuverlässig abrufbar sind.
2. Umsatz- und RPM-Felder je Portal.
3. Kleines Bearbeitungsformular, falls die direkte JSON-Pflege zu umständlich wird.
