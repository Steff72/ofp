OO-Bank
---------------------------------------------------------
Ziel:
  - Kleine Bankanwendung, die Konten führt und Buchungen ausführt
  - Unterstützte Operationen:
      1) Konto eröffnen (mit Konto-ID und Kontotyp)
      2) Bareinzahlung (nur positive Beträge, ohne Gegenkonto)
      3) Überweisung von Konto A nach Konto B (optional Verwendungszweck)
      4) Kontostand abfragen
      5) Letzte Buchungen eines Kontos abfragen (optional Anzahl)
      6) Letzte Buchungen der Bank abfragen (optional Anzahl)
      7) Konto schliessen (nur wenn Saldo == 0)

  - Kontotypen (Beispiele):
      * Jugendkonto: nie negativ, keine Gebühren
      * Privatkonto: Überziehung bis Limit erlaubt, Gebühren auf Abbuchungen
      * Sparkonto: nie negativ, zinsbar (Zinsbuchung = normale Buchung von Bank-Zinskonto)

  - Qualitätsanforderungen:
      * Konsistenz: Jede Buchung hat Gegenbuchung (Ausnahme: Bareinzahlung)
      * Bank-Journal konsistent zu Konto-Journalen und Kontoständen
      * Offen für neue Kontotypen (Open-Closed)

Umsetzungshinweise:
  - Decimal für Beträge (Geldwerte sollten nicht mit float gerechnet werden).
  - Zentrale Klassen: Bank, Account (Basisklasse), YouthAccount, PrivateAccount, SavingsAccount
  - Transaktionen werden im Bankjournal gespeichert; Konten führen ein eigenes Konto-Journal.
  - Gebühren-/Zinsbuchungen laufen über spezielle interne Bankkonten.


Game of Life
---------------------------------------------------------
Ziel:
  - Simulation von Conways Game of Life auf einem Grid
  - Auswahl zwischen Conway-Regel (Standard) und HighLife-Variante
  - Unendliches Grid, gespeichert als Menge lebender Zellen (Alive-Set)

Bausteine (`game_of_life.py`):
  - `conway_rule` / `highlife_rule`: bestimmen für jede Zelle den nächsten Zustand
  - `step_func`: Factory für eine Step-Funktion auf Basis der gewählten Regel
  - `generations`: Generator, der fortlaufend neue Generationen liefert
  - `alive_from_strings`: wandelt ASCII-Patterns in ein Alive-Set um
  - `display` / `bbox`: Ausgabe eines Ausschnitts via Bounding Box

Ausführen:
  - `python3 game_of_life.py` startet die Demo und simuliert 50 Generationen (0,5 s Pause)
  - Regel im `main()`-Block anpassen (z.B. `rule = highlife_rule`)
