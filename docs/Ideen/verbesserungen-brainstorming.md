# Verbesserungen — Brainstorming

Gesammelt am 2026-03-19. Zuletzt aktualisiert: 2026-03-21.

---

## 1. ✅ Heute-in-30-Sekunden: Weniger Interpretation, mehr Fakten

> **Status: Umgesetzt am 19.03.2026** — Story: `20260319124500-fix-summarization-no-interpretations.md`

**Problem:** Der "Heute in 30 Sekunden"-Bereich enthält teilweise Interpretationen und Risikobewertungen, die nicht direkt aus den Artikeln stammen. Beispiel: *"Keine unmittelbaren Auswirkungen auf die Kreditwürdigkeit"* — das ist eine Einschätzung des Modells, kein Fakt.

**Ideen:**
- Prompt-Anpassung: Nur Fakten aus dem Artikel wiedergeben, keine eigene Risikobewertung
- Beispiele für gute vs. schlechte Zusammenfassungen im Prompt ergänzen (bereits teilweise umgesetzt am 19.03.)
- Eventuell zweistufig: erst zusammenfassen, dann in einem separaten Schritt prüfen ob Interpretationen enthalten sind
- "Heute in 30 Sekunden" Einträge kürzer und telegrafischer formulieren

**Was umgesetzt wurde:**
- CRITICAL RULES im Summarization-Prompt gegen Interpretationen
- Konkrete Bad/Good Examples (z.B. "Keine unmittelbaren Auswirkungen..." als Bad Example)
- Telegrafischer Stil wird erzwungen

**Priorität:** ~~Hoch~~ Erledigt.

---

## 2. ✅ E-Mail-Betreff: Abschneiden verhindern

> **Status: Umgesetzt** — Story: `20260110204501--dynamic-subject-line.md`

**Problem:** Der Betreff ist manchmal zu lang und wird in Outlook mit "..." abgeschnitten. Empfänger sehen nicht den vollständigen Betreff.

**Ideen:**
- Maximale Länge auf ~60 Zeichen begrenzen (Outlook zeigt je nach Ansicht 50-80 Zeichen)
- Format vereinfachen, z.B.: `News-Digest 19.03. — 3 Themen, 12 Artikel`
- Auf das Wesentliche beschränken: Datum + Anzahl Themen
- Eventuell das wichtigste Thema des Tages im Betreff nennen (kurz)
- Betreff-Generierung im Prompt oder Template anpassen mit striktem Zeichenlimit

**Was umgesetzt wurde:**
- Dynamischer Betreff mit Top-Artikel-Titel, begrenzt auf `max_length=47`
- Prefix gekürzt: `News-Digest: {top_title}` statt `Creditreform News-Digest: {top_title}`
- Gesamtlänge auf **60 Zeichen** begrenzt (Outlook-safe, kein Abschneiden)
- Fallback auf Datum wenn keine Artikel vorhanden

**Priorität:** ~~Mittel~~ Erledigt.

---

## 3. ✅ Duplikaterkennung verbessern (Cross-Language)

> **Status: Umgesetzt am 19.03.2026** — Story: `20260319133000-cross-language-deduplication.md`

**Problem:** Gewisse Duplikate werden nicht erkannt, insbesondere bei:
- **Cross-Language:** FR/IT-Artikel zum gleichen Thema wie DE-Artikel (z.B. SNB/BNS Leitzinsentscheid)
- **Umformulierte Titel:** Gleicher Inhalt, aber unterschiedliche Überschrift
- **Zeitversetztes Publizieren:** Agenturen-Meldung wird von verschiedenen Medien zu unterschiedlichen Zeiten aufgegriffen

**Ideen:**
- Cross-Language-Dedup: FR/IT-Artikel direkt gegen DE-Kanonische vergleichen (umgesetzt am 19.03., erste Version)
- Entity-Mapping für bekannte Institutionen: SNB ↔ BNS, Bundesrat ↔ Conseil fédéral ↔ Consiglio federale
- Embedding-basierter Vergleich statt rein LLM-basiert (schneller, günstiger bei vielen Paaren)
- Threshold für Cross-Language-Vergleiche eventuell tiefer setzen als für Same-Language
- Zeitfenster für Duplikaterkennung erweitern (aktuell nur innerhalb eines Runs?)

**Was umgesetzt wurde:**
- `language`-Feld in Artikel-Modell und Feeds (`config/feeds.yaml`)
- DB-Migration v5→v6 mit `language`-Spalte
- Zweiter Dedup-Pass: `detect_cross_language_duplicates()` vergleicht FR/IT gegen DE-Kanonicals via LLM
- Ohne Entity-Prefilter (umgeht SNB↔BNS-Problem)

**Noch offen:**
- Entity-Mapping für bekannte Institutionen
- Embedding-basierter Vergleich (günstiger bei vielen Paaren)
- Threshold-Tuning für Cross-Language

**Priorität:** ~~Hoch~~ Grundversion erledigt, Tuning-Potential vorhanden.

---

## 4. Bereits verschickte Themen erkennen

**Problem:** Wenn ein Thema gestern bereits im Digest war und heute wieder erscheint (z.B. Fortlaufende Berichterstattung zu einem Thema), wird es erneut gleich prominent dargestellt, ohne den Kontext, dass es gestern schon behandelt wurde.

**Ideen:**
- **Themen-History:** Beim Digest-Generieren prüfen, ob ein Thema/Entity in den letzten X Tagen bereits verschickt wurde
- **Kennzeichnung:** "Bereits am 18.03. berichtet" oder "Update" Label im Digest
- **Zusammenfassung der Entwicklung:** Bei wiederkehrenden Themen die neuen Fakten hervorheben statt alles nochmal zusammenzufassen
- **Deduplizierung über Tage:** Artikel, die nichts Neues bringen, gar nicht mehr aufnehmen
- **Relevanz-Decay:** Wiederkehrende Themen ohne neue Fakten automatisch tiefer einstufen

- **Frühere Artikel anzeigen:** Unter einem Artikel im Digest die verwandten früheren Meldungen auflisten, z.B. "Frühere Berichte: 15.03., 16.03." mit Titel/Link. So sieht der Leser sofort den zeitlichen Verlauf.

**Konkretes Beispiel:** "Kanton Wallis schliesst 13 Campingplätze sofort wegen Naturgefahren" — dieses Thema wurde bereits vor mehreren Tagen gemeldet. Der heutige Artikel enthält vermutlich neue Fakten und gehört darum zurecht in den Digest. Aber ohne Kontext fehlt dem Leser der Bezug zur laufenden Geschichte. Ideal wäre: Unter dem Artikel eine Zeile wie *"Siehe auch: 15.03. — Wallis prüft Schliessung von Campingplätzen"*.

**Herausforderungen:**
- **Erkennung verwandter Artikel:** Nicht trivial — gleiches Thema ≠ gleicher Titel oder gleiche Entities. Mögliche Ansätze:
  - Entity-Overlap (gleiche Firmen/Organisationen/Orte + ähnliches Thema)
  - Embedding-Similarity gegen die letzten 7-14 Tage
  - LLM-basiert: "Ist dieser Artikel eine Fortsetzung von einem der folgenden?"
- **Zeitfenster:** Wie weit zurückschauen? 7 Tage? 14 Tage? Konfigurierbar?
- **Darstellung:** Wo genau im Digest? Unter dem Artikel? Als Fussnote? Wie viele frühere Artikel maximal?
- **Performance/Kosten:** Jeder neue Artikel müsste gegen potenziell hunderte alte verglichen werden

**Priorität:** Mittel — verbessert die Nützlichkeit des Digests erheblich, aber komplexer umzusetzen. Erkennung verwandter Artikel ist der schwierigste Teil.

---

## 5. ⚠️ Darstellung im Digest verbessern (teilweise umgesetzt)

**Ideen:**
- **Visuelle Hierarchie:** Wichtige Artikel visuell stärker hervorheben (grössere Überschrift, Farbakzent)
- **Kompaktere Darstellung:** Weniger Whitespace, mehr Artikel auf einen Blick
- **Mobile-Optimierung:** Digest auf dem Handy gut lesbar? (Outlook Mobile)
- **Quellenangabe:** Quellen prominenter anzeigen (Vertrauen)
- **Artikel-Anzahl pro Thema:** Bei vielen Artikeln zum gleichen Thema nur den besten zeigen + "X weitere Quellen"
- **Lesezeit-Schätzung:** "~2 Min. Lesezeit" für den gesamten Digest

**Was bereits umgesetzt wurde:**
- ✅ **Dynamische Themengruppierung via LLM** (20.03.) — 3–10 Cluster statt 13 statische Kategorien, mit BMP-sicheren Icons
- ✅ **Credit-Impact-Styling** (14.03.) — 4-Farben-Schema (negative/neutral/positive/elevated_risk), Risiko-Radar Sektion
- ✅ **AVIF-zu-JPEG Konvertierung** (14.03.) — Outlook-kompatible Bildformate

**Noch offen:**
- Mobile-Optimierung
- Lesezeit-Schätzung
- "X weitere Quellen"-Zusammenfassung bei vielen Artikeln

**Priorität:** Niedrig — nice-to-have, aktuelle Darstellung funktioniert.

---

## 6. Finaler Digest-Review per LLM (Quality Gate)

**Problem:** Trotz Duplikaterkennung auf Artikelebene können im fertigen Digest inhaltlich redundante Zusammenfassungen stehen — z.B. wenn zwei Artikel zum SNB-Entscheid beide durch die Dedup kommen, weil sie leicht unterschiedliche Schwerpunkte haben, aber im Digest praktisch dasselbe sagen.

**Idee:**
- **Letzter API-Call** nach der Digest-Generierung: Das gesamte Mail (oder alle Zusammenfassungen) wird nochmals einem LLM übergeben
- Das LLM prüft auf:
  - **Inhaltliche Duplikate:** Zusammenfassungen, die im Wesentlichen dasselbe sagen → zusammenführen
  - **Widersprüche:** Artikel, die sich widersprechen → kennzeichnen oder harmonisieren
  - **Redundante Key Points:** Gleiche Fakten in verschiedenen Artikeln → konsolidieren
- Ergebnis: Ein bereinigter, kompakterer Digest ohne Wiederholungen
- Optional: LLM kann auch den "Heute in 30 Sekunden"-Bereich nochmals auf Interpretationen prüfen

**Vorteile:**
- Fängt Duplikate ab, die die Artikel-Level-Dedup nicht erkennt (unterschiedliche Quellen, gleiche Story)
- Verbessert die Lesequalität: kein Déjà-vu-Effekt beim Lesen
- Kann mehrere Probleme gleichzeitig lösen (Duplikate + Interpretationen + Konsistenz)

**Nachteile / Risiken:**
- Zusätzliche API-Kosten (ein grosser Call mit dem gesamten Digest)
- Latenz: ein weiterer Schritt in der Pipeline
- LLM könnte beim Zusammenführen Fakten verlieren oder verfälschen

**Umsetzung:**
- Neuer Pipeline-Schritt nach `digest_generator`, vor E-Mail-Versand
- Input: alle Zusammenfassungen + Key Points als JSON
- Output: bereinigte Version mit Merge-Hinweisen
- Konfigurierbar: an/aus via Config, damit Kosten kontrollierbar

**Priorität:** Mittel — elegante Lösung, die mehrere Probleme auf einmal adressiert.

---

## Nächste Schritte

~~1. **Quick Wins:** Betreff-Länge begrenzen, Prompt weiter verfeinern~~ ✅ Erledigt

2. **Mittelfristig:**
   - Themen-History implementieren (Idee 4) — wiederkehrende Themen erkennen, frühere Artikel verlinken
   - Digest-Review Quality Gate (Idee 6) — finaler LLM-Call gegen Redundanzen/Widersprüche
   - Cross-Language-Dedup tunen — Entity-Mapping, Threshold-Optimierung

3. **Langfristig:**
   - Embedding-basierte Dedup (günstiger/schneller bei vielen Vergleichen)
   - Darstellungsverbesserungen (Mobile, Lesezeit, "X weitere Quellen")
