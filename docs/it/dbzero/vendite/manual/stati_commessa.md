## 📘 Documentazione Concettuale – Tabella `vendite.stati_commessa`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.commesse](/dbzero/vendite/tabelle/commesse)  
> • [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)  
>
**Approfondimento funzioni:**
>
• [vendite.fn_get_or_create_commessa](/dbzero/vendite/funzioni/fn_get_or_create_commessa)  
> • [vendite.fn_upsert_commessa_attivita](/dbzero/vendite/funzioni/fn_upsert_commessa_attivita)  
> • [vendite.fn_list_commesse_emittibili](/dbzero/vendite/funzioni/fn_list_commesse_emittibili)  
>
### 🎯 Scopo Principale
(latest review 26-10-2026)  
`vendite.stati_commessa` e` la lookup centrale degli stati lifecycle della commessa.

Oltre al codice stato, espone tre flag operativi usati in runtime:

* `chiude_commessa`: stato terminale (no riuso)
* `emittibile`: abilita emissione verso AF
* `modificabile`: abilita upsert su `commesse_attivita`

---

### Regole principali

* PK tecnica su `id`.
* Unicita` su `codice` e `codice_interno`.
* `codice_interno` bloccato in update tramite trigger.
* Trigger di protezione: se uno stato e` usato da `commesse`, non puo` essere disattivato (`attivo = false`).
* Indice su `attivo` per filtri applicativi e controlli di governance.

---

### Seed di base

Seed iniziale previsto:

* `BOZZA`
* `APERTA`
* `IN_ESECUZIONE` — ⛔ ritirato il 2026-10-26 (`attivo = false`, `brief-modello-documento-vendita` §14): «una lavorazione in corso» è lo stato del processo, non della commessa
* `PRONTA_FATTURAZIONE`
* `CHIUSA`
* `ANNULLATA`

Con flag configurati per distinguere stati riusabili, emittibili e terminali.

---

{% include-markdown "signature-core.md" %}
