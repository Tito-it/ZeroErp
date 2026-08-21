## 📘 Documentazione Concettuale – Funzione `pagamenti.trgfn_vendite_contabili_guard_transizione`

### 🎯 Scopo Principale
(rev 2026-08-21)

Enforcement **DB-first** del grafo degli stati della **distinta contabile**: il
passaggio `OLD.stato_id -> NEW.stato_id` è ammesso solo se presente e **attivo** in
`pagamenti.transizioni_stati_contabile`.

⛔ **Nessun grafo scritto nel codice**: la regola sta in una tabella, così si legge
e si cambia senza una migrazione di codice. È il mirror di
`vendite.trgfn_commesse_guard_transizione` e `config.trgfn_resi_guard_transizione`.

### Regole applicate
* No-op se lo stato non cambia davvero (`IS NOT DISTINCT FROM`), anche quando
  l'`UPDATE` nomina comunque la colonna.
* La transizione deve **esistere** ed essere **attiva** in matrice.
* Il messaggio nomina i **codici di stato**, non gli id — e usa `codice_interno`,
  che è immutabile, non `codice`, che l'utente può rinominare.

### Quando si attiva
* `BEFORE UPDATE OF stato_id` su `pagamenti.vendite_contabili`.

⚠️ **Mai sull'INSERT**, ed è una regola del progetto: una distinta deve poter
**nascere** in uno stato qualunque. Non è teorico — il giro dei fondi fattura crea
le sue distinte direttamente in `VALIDATA`, perché lì non c'è digitazione e nascono
già finite.

### ⚠️ Error handling
* `E_CONTABILE_TRANSIZIONE_NON_AMMESSA` (`CONFLITTO_STATO`, 409) via
  `script.fn_log_and_raise_error`.
* Codice **distinto** da quello della riga: le due macchine hanno stati diversi, e
  con un codice solo il messaggio manderebbe a guardare il documento sbagliato.

{% include-markdown "signature-core.md" %}
