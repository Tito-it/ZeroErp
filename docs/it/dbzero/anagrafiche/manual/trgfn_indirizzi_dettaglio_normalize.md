## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_indirizzi_dettaglio_normalize`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.indirizzi_dettaglio](/dbzero/anagrafiche/tabelle/indirizzi_dettaglio) — il civico che scrive
>
> Approfondimento viste:
>
> * [script.vw_indirizzo_completo](/dbzero/script/views/vw_indirizzo_completo) — la via risolta, da cui si normalizza
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_build_indirizzo_normalizzato](/dbzero/anagrafiche/funzioni/fn_build_indirizzo_normalizzato) — dove stanno le regole che applica
> * [anagrafiche.trgfn_indirizzi_dettaglio_guard_chiave](/dbzero/anagrafiche/funzioni/trgfn_indirizzi_dettaglio_guard_chiave) — gira dopo, e giudica i valori che scrive
> * [maintenance.proc_bump_indirizzi_dettaglio](/dbzero/maintenance/funzioni/proc_bump_indirizzi_dettaglio) — riscrive i civici di una via perché questo trigger li rinormalizzi

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_indirizzi_dettaglio_normalize` scrive il civico come si salva: a ogni nascita e a ogni
modifica sostituisce il dettaglio coi valori normalizzati e ricalcola via, civico e indirizzo normalizzati.

---

### ⭐ Nessuna regola sua

Il trigger chiede tutto a `anagrafiche.fn_build_indirizzo_normalizzato` e copia il risultato sulla riga: il
dettaglio (estensione, palazzina, scala, piano, interno) normalizzato, e le tre colonne derivate `via_norm`,
`civico_norm`, `indirizzo_normalizzato`. Le regole stanno lì, perché la stessa normalizzazione la usa chi cerca
il civico: se il trigger ne avesse una sua, chi cerca e chi salva prima o poi direbbero due cose diverse.

Le colonne derivate sono sempre il riflesso della via e del dettaglio: un valore passato da chi scrive è
sostituito. Il ricalcolo avviene a ogni scrittura, anche quella che riscrive la riga senza cambiarla: è così che
`maintenance.proc_bump_indirizzi_dettaglio` rinormalizza i civici di una via dopo il cambio del suo nome o del
toponimo.

Il trigger non solleva errori: il giudizio sui valori lo dà dopo, in fascia `z10`, il guard della chiave.

---

### ⚠️ Che cosa oggi non copre

* **Una via che non si risolve** (il comune senza provincia, per esempio) fa restituire alla normalizzazione
  tutti valori vuoti. Il trigger li copia sulla riga, dettaglio compreso, e la scrittura fallisce con l'errore
  tecnico della colonna obbligatoria `via_norm`, senza un codice che dica qual è il problema. Il «trova o crea»
  si ferma prima, con `E_INDIRIZZO_VIA_NON_RISOLTA`; un inserimento diretto, o la modifica di un civico la cui
  via ha smesso di risolversi, no.

---

### Test

* `db/pgtap/anagrafiche/test-indirizzi-dettaglio-unicita-v1.sql` — i valori come li salva il trigger (maiuscolo,
  vuoto uguale a nessun valore, estensione col `/`).
* `db/pgtap/anagrafiche/test-fn-get-or-create-indirizzo-dettaglio.sql` — l'indirizzo normalizzato scritto dal
  trigger.
* `db/pgtap/maintenance/test-bump-toponomastica-v1.sql` — via e indirizzo normalizzati riscritti dopo il cambio
  di un toponimo.

---

### Note di migrazione

* 2026-03-17 — le regole passano in `anagrafiche.fn_build_indirizzo_normalizzato`, e il trigger le applica
  soltanto.
* 2026-10-25 — il testo vuoto del dettaglio diventa nessun valore, e il civico zero smette di essere un modo di
  dire `SNC`.

---

{% include-markdown "signature-core.md" %}
