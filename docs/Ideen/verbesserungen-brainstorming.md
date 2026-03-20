# Verbesserungen — Brainstorming

Gesammelt am 2026-03-19. Status: Ideen zur Diskussion.

---

## 1. Heute-in-30-Sekunden: Weniger Interpretation, mehr Fakten

**Problem:** Der "Heute in 30 Sekunden"-Bereich enthält teilweise Interpretationen und Risikobewertungen, die nicht direkt aus den Artikeln stammen. Beispiel: *"Keine unmittelbaren Auswirkungen auf die Kreditwürdigkeit"* — das ist eine Einschätzung des Modells, kein Fakt.

**Ideen:**
- Prompt-Anpassung: Nur Fakten aus dem Artikel wiedergeben, keine eigene Risikobewertung
- Beispiele für gute vs. schlechte Zusammenfassungen im Prompt ergänzen (bereits teilweise umgesetzt am 19.03.)
- Eventuell zweistufig: erst zusammenfassen, dann in einem separaten Schritt prüfen ob Interpretationen enthalten sind
- "Heute in 30 Sekunden" Einträge kürzer und telegrafischer formulieren

**Priorität:** Hoch — betrifft die Glaubwürdigkeit des Digests.

---

## 2. E-Mail-Betreff: Abschneiden verhindern

**Problem:** Der Betreff ist manchmal zu lang und wird in Outlook mit "..." abgeschnitten. Empfänger sehen nicht den vollständigen Betreff.

**Ideen:**
- Maximale Länge auf ~60 Zeichen begrenzen (Outlook zeigt je nach Ansicht 50-80 Zeichen)
- Format vereinfachen, z.B.: `News-Digest 19.03. — 3 Themen, 12 Artikel`
- Auf das Wesentliche beschränken: Datum + Anzahl Themen
- Eventuell das wichtigste Thema des Tages im Betreff nennen (kurz)
- Betreff-Generierung im Prompt oder Template anpassen mit striktem Zeichenlimit

**Priorität:** Mittel — einfach umzusetzen, verbessert den ersten Eindruck.

---

## 3. Duplikaterkennung verbessern

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

**Priorität:** Hoch — Duplikate im Digest wirken unprofessionell.

---

## 4. Bereits verschickte Themen erkennen

**Problem:** Wenn ein Thema gestern bereits im Digest war und heute wieder erscheint (z.B. Fortlaufende Berichterstattung zu einem Thema), wird es erneut gleich prominent dargestellt, ohne den Kontext, dass es gestern schon behandelt wurde.

**Ideen:**
- **Themen-History:** Beim Digest-Generieren prüfen, ob ein Thema/Entity in den letzten X Tagen bereits verschickt wurde
- **Kennzeichnung:** "Bereits am 18.03. berichtet" oder "Update" Label im Digest
- **Zusammenfassung der Entwicklung:** Bei wiederkehrenden Themen die neuen Fakten hervorheben statt alles nochmal zusammenzufassen
- **Deduplizierung über Tage:** Artikel, die nichts Neues bringen, gar nicht mehr aufnehmen
- **Relevanz-Decay:** Wiederkehrende Themen ohne neue Fakten automatisch tiefer einstufen

**Priorität:** Mittel — verbessert die Nützlichkeit des Digests erheblich, aber komplexer umzusetzen.

---

## 5. Darstellung im Digest verbessern

**Ideen:**
- **Visuelle Hierarchie:** Wichtige Artikel visuell stärker hervorheben (grössere Überschrift, Farbakzent)
- **Kompaktere Darstellung:** Weniger Whitespace, mehr Artikel auf einen Blick
- **Mobile-Optimierung:** Digest auf dem Handy gut lesbar? (Outlook Mobile)
- **Quellenangabe:** Quellen prominenter anzeigen (Vertrauen)
- **Artikel-Anzahl pro Thema:** Bei vielen Artikeln zum gleichen Thema nur den besten zeigen + "X weitere Quellen"
- **Lesezeit-Schätzung:** "~2 Min. Lesezeit" für den gesamten Digest

**Priorität:** Niedrig — nice-to-have, aktuelle Darstellung funktioniert.

---

## Nächste Schritte

1. **Quick Wins:** Betreff-Länge begrenzen, Prompt weiter verfeinern
2. **Mittelfristig:** Themen-History implementieren, Cross-Language-Dedup tunen
3. **Langfristig:** Embedding-basierte Dedup, Darstellungsverbesserungen
