# fn_generate_fatture_righe (Django) — opzionale
  
## Scopo
Portare in Django la logica di calcolo/importi delle righe fattura, lasciando in DB le insert.

## Contesto
In DB `vendite.fn_generate_fatture_righe()` genera righe fattura da `attivita_fatturabili`.
L’eventuale migrazione in Django riguarda solo la **logica di calcolo**.

## Input
- set righe fatturabili (lockato in DB)
- parametri fiscali e di pricing

## Output
- payload righe fattura da inserire (via DB)

## Regole
- Idempotenza per riga.
- Importi congelati come snapshot.

## Dipendenze DB
- Tabelle `vendite.attivita_fatturabili`, `vendite.fatture_righe`
- Funzioni di supporto (IVA, UoM, registri)

## Note di migrazione
- Migrazione consigliata solo se la logica cambia spesso.
