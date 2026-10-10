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
  "status": "review",
  "portalTitle": "Abweichender Titel im Portal",
  "submitted": "2026-09-27",
  "sourceBranch": "main",
  "submittedCommit": "vollständige-commit-sha",
  "notes": "Erste Einreichung"
}
```

`portalTitle` wird nur gepflegt, wenn ein Spiel im Portal unter einem anderen Namen als im Dashboard eingereicht oder veröffentlicht wurde. Der abweichende Name erscheint dann in Distribution und Verlauf.

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

`accepted` und `published` können identisch sein. Ist die Annahme bestätigt, aber ihr genaues Datum unbekannt, wird zusätzlich `"acceptanceConfirmed": true` gepflegt. Das Dashboard weist dann ausdrücklich auf das fehlende Datum hin, statt eines zu schätzen.

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
- `review`
- `changes_requested`
- `scheduled`
- `approved`
- `live`
- `rejected`

Eine Einreichung ist ein datiertes Ereignis (`submitted`), kein dauerhafter Status. Solange die Entscheidung ohne Rückmeldung aussteht, lautet der aktuelle Status `review` („In Prüfung“). Verlangt das Portal eine Korrektur, wird `changes_requested` verwendet. Ist ein Spiel freigegeben, aber noch nicht veröffentlicht, lautet der Status `approved`. Hat ein Portal die Veröffentlichung bereits eingeplant, ist sie aber noch nicht öffentlich bestätigt, wird `scheduled` verwendet. Erst sobald die öffentliche Spielseite samt Player ohne Entwicklerzugang erreichbar ist, gilt `live`.

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

1. Weitere Spieleplattformen mit verlässlich auslesbaren öffentlichen Kennzahlen ergänzen.
2. Umsatz- und RPM-Felder je Portal.
3. Kleines Bearbeitungsformular, falls die direkte JSON-Pflege zu umständlich wird.

## Kongregate: tägliche Performance-Daten (automatisiert)

Das Dashboard zeigt unter **Übersicht → Kongregate · Performance** die drei aktiven Kongregate-Spiele (HEXFRONT, GALALAXY, ROOSTER RAGE). Pro Spiel werden kumulative Plays, Favoriten, Bewertung, Veränderung gegenüber dem **vorherigen vorhandenen Messpunkt** und eine Verlaufskurve angezeigt.

- Datenquelle: öffentliches Kongregate-Metrics-JSON unter `https://www.kongregate.com/games/emfau/<spiel-slug>/metrics.json`.
- Abrufskript: `scripts/sync_kongregate.py` (Python-Standardbibliothek; kein API-Schlüssel).
- Zeitreihe: `analytics/kongregate.json`. Historische ältere Messwerte sind als `existing_dashboard` oder `user_reported` markiert; neue Abrufe als `kongregate_metrics` mit tatsächlichem UTC-Zeitstempel.
- Automatik: `.github/workflows/deploy-pages.yml` sammelt täglich um **07:17 UTC** (bei GitHub eventuell verzögert), committed geänderte öffentliche KPI-Daten und stellt das Dashboard im **selben Workflow-Lauf** bereit. Der Zeitplan beginnt erst, wenn die Änderung in `main` übernommen wurde.
- Manuell auslösen: **Actions → Game-Ops-Dashboard veröffentlichen → Run workflow**. Ein manueller Durchlauf aktualisiert ebenfalls die Daten.
- Lokal prüfen: `python -m unittest discover -s tests -v`; nur die Feeds prüfen: `python scripts/sync_kongregate.py --check-live`; Tageswert speichern: `python scripts/sync_kongregate.py`.
- Ein wiederholter Lauf am selben Kalendertag (Zeitzone Europe/Berlin) erzeugt keinen doppelten Datensatz. Bei einer neuen Zahl wird der Tagesdatensatz aktualisiert. Fehlende Tage werden **nicht** als 0 Plays nachgetragen; ein fehlgeschlagener Feed behält den letzten belegten Wert. Der Abruf meldet Fehler in den Actions-Logs.

Die bisherigen `data.json`-Felder `latestPlays` und `metricsHistory` sind **historische manuell gepflegte Angaben** und werden bewusst nicht überschrieben. Für die neue automatische Performance-Ansicht ist `analytics/kongregate.json` maßgeblich. Alle dort gespeicherten Daten sind **öffentlich**; vertrauliche Umsatzwerte und Zugangsdaten gehören weder in die Datei noch ins Repository.

Das Skript ruft die **öffentlichen kumulativen Gameplays** ab, nicht die internen Kongregate-Developer-KPIs wie DAU, Retention oder geschätzten Werbeumsatz. Ein Tageszuwachs zwischen zwei Snapshots ist nicht automatisch eine vollständig gemessene tägliche Spielerzahl.

## Y8: öffentliche Spielestatistiken automatisch erfassen

Für **Galalaxy** ist die öffentliche Y8-Spielseite unter [y8.com/games/galalaxy](https://www.y8.com/games/galalaxy) die Datenquelle. Der bereits über GitHub Actions getestete HTML-Abruf liefert kumulierte **Plays**, **Likes** und die sichtbare **Bewertung auf einer Skala von 0 bis 10**. Die Y8-Werte sind nicht auf Kongregates 5-Punkte-Skala umgerechnet.

- Abrufskript: `scripts/sync_y8.py` (Python-Standardbibliothek, ohne Entwicklerkonto, Cookies oder API-Schlüssel).
- Historisches Archiv: `analytics/y8.json` mit einem datierten Messpunkt pro Berlin-Kalendertag, UTC-Abrufzeitpunkt und Herkunft `y8_public_page`.
- Dashboard: eigene **Y8 · Performance**-Ansicht auf der Übersicht. Veränderungen und Diagramme beziehen sich auf die **vorhandenen** Snapshots.
- Automatik: derselbe geplante Workflow wie bei Kongregate (`.github/workflows/deploy-pages.yml`) ruft beide Plattformen ab und speichert die öffentlichen KPI-Dateien. Über **Actions → Game-Ops-Dashboard veröffentlichen → Run workflow** kann der Abruf zusätzlich manuell ausgelöst werden.
- Prüfen: `python -m unittest discover -s tests -v`; `python scripts/sync_y8.py --check-live` testet die Webseite ohne Änderung; `python scripts/sync_y8.py` speichert den aktuellen Snapshot lokal.
- Fehlerfälle: falsche/fehlende Titel oder Zählwerte, widersprüchliche Desktop-/Mobilanzeigen, abnehmende kumulative Plays, HTML-Änderungen oder fehlgeschlagene HTTP-Aufrufe werden **nicht** zu 0 umgedeutet. Bei Y8-Abrufproblemen bleibt Kongregates Workflow unabhängig lauffähig; der letzte gespeicherte Y8-Stand bleibt bestehen. Eine fehlende Like-Zahl wird als **unbekannt**, nicht als null, gekennzeichnet.
- Neue Y8-Spiele erst aufnehmen, wenn die öffentliche Spielseite tatsächlich live ist. Dann die Konfiguration `GAMES` und das Archiv ergänzen und die Darstellung erweitern.

**Wichtige Einschränkung:** Das Auslesen einer öffentlichen HTML-Seite ist kein offizieller, stabil garantierter Reporting-API-Vertrag. Änderungen an Y8s Markup können eine Skriptkorrektur erfordern. Das ist **nicht** der Zugriff auf interne Y8-Studio-Statistiken (DAU, Retention, Umsatz). Einmal täglich wird nur die konkrete Spielseite abgerufen. 
