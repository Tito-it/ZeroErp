## Documentazione – `script.trgfn_guard_sorgente_polimorfa()` (SOSTITUITA)

> **Stato**: funzione **rinominata** il 2026-07-18 (migration 20260718-16,
> brief-db-guard-sorgente-polimorfa). Il nome generico lasciava intendere una
> copertura di tutto il meccanismo polimorfo, ma la funzione validava solo il
> **modello A** (colonne tipizzate `sorgente_riga`/`sorgente_uid` uuid) e non era
> agganciata ad alcuna tabella.

Le funzioni attuali sono **due sorelle**, una per modello di colonne-sorgente:

* [`trgfn_guard_sorgente_polimorfa_tipizzata`](/dbzero/script/funzioni/trgfn_guard_sorgente_polimorfa_tipizzata)
  — modello A (colonne tipizzate alternative); corpo identico alla vecchia funzione.
* [`trgfn_guard_sorgente_polimorfa_testuale`](/dbzero/script/funzioni/trgfn_guard_sorgente_polimorfa_testuale)
  — modello B (chiave unica testuale di `pratiche_sorgenti`/`commesse_sorgenti`);
  **attiva** su entrambe le tabelle.

Convenzione e mappa dei due modelli:
[config.sorgenti — §Convenzione chiave sorgente](/dbzero/config/tabelle/sorgenti).
