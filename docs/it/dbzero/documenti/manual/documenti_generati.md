## 📘 Documentazione Concettuale – Tabella `documenti.documenti_generati`

> **Ultimo aggiornamento**: 14 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [documenti.documenti_generati_file](/dbzero/documenti/tabelle/documenti_generati_file) — i file della stampa (il PDF, gli allegati)
> * [documenti.documenti_generati_eventi](/dbzero/documenti/tabelle/documenti_generati_eventi) — la storia di ciò che è successo alla stampa dopo
> * [documenti.template_documenti](/dbzero/documenti/tabelle/template_documenti) — il modello usato
> * [documenti.template_documenti_versioni](/dbzero/documenti/tabelle/template_documenti_versioni) — la versione del modello usata
> * [config.sorgenti](/dbzero/config/tabelle/sorgenti) — i tipi di documento che si stampano
>
> Approfondimento funzioni:
>
> * [documenti.trgfn_documenti_generati_check_coerenza](/dbzero/documenti/funzioni/trgfn_documenti_generati_check_coerenza) — il modello va bene per il documento
> * [documenti.trgfn_documenti_generati_guard_versione_contesto](/dbzero/documenti/funzioni/trgfn_documenti_generati_guard_versione_contesto) — i dati hanno la forma che la versione legge
> * [documenti.trgfn_documenti_generati_protect_snapshot](/dbzero/documenti/funzioni/trgfn_documenti_generati_protect_snapshot) — la stampa non cambia dopo
> * [documenti.trgfn_documenti_generati_block_delete](/dbzero/documenti/funzioni/trgfn_documenti_generati_block_delete) — la stampa non si cancella
> * [script.trgfn_guard_sorgente](/dbzero/script/funzioni/trgfn_guard_sorgente) — il guard unico della provenienza
> * [script.fn_sorgente_chiave](/dbzero/script/funzioni/fn_sorgente_chiave) — la coppia di chiavi da scrivere
>
> Guide:
>
> * [Documenti e stampe](/guide/documenti-e-stampe) — il modulo documenti, dal modello alla stampa
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — il modello della provenienza: tipo, documento, riga

---

### 🎯 Scopo Principale

`documenti.documenti_generati` è il registro delle stampe emesse: una riga per ogni documento prodotto dal
motore documentale, con il contesto congelato, le impronte di contenuto, template e PDF, e il modello e la
versione con cui è nato.

La riga descrive un fatto già accaduto. Non è il modello vivo: se il modello cambia dopo, la stampa resta
com'era, e la ristampa fedele la riproduce dallo stesso contesto e dalla stessa versione.

---

### Ogni stampa nasce da un documento

La provenienza è la grammatica comune della sorgente: il tipo del documento stampato (`sorgente_tipo_id`, da
`config.sorgenti`) c'è sempre, e con lui **una sola** chiave del documento, quella che il tipo dichiara:
`sorgente_uid` per preventivo e offerta, `sorgente_id` per gli altri. `sorgente_riga` è vuota quando si stampa
il documento intero.

* La forma (tipo più una sola chiave) la tiene `chk_documenti_generati_sorgente_forma`.
* Che il tipo sia attivo, che la chiave sia quella giusta, che il documento esista e che la riga gli appartenga
  lo verifica `script.trgfn_guard_sorgente`, che **blocca** anche la cancellazione di un documento finché una
  sua stampa lo cita.
* Le stampe dello stesso documento (o della stessa riga) si numerano con `progressivo_sorgente`, da 1, in una
  serie sola qualunque strada stampi: lo tiene `uq_documenti_generati_sorgente_progressivo`, con
  `NULLS NOT DISTINCT` perché la chiave che non si usa e la riga di una stampa intera sono vuote.

---

### Una stampa si registra solo se è coerente con il suo modello

All'inserimento tre controlli guardano la stessa riga da tre lati:

* **il modello va bene per il documento**: la versione appartiene al modello indicato, e il modello ha la stessa
  sorgente, lo stesso tipo di output e la stessa azienda della stampa, oppure è un modello standard
  (`trgfn_documenti_generati_check_coerenza`);
* **i dati hanno la forma che la versione legge**: la forma dichiarata dal contesto congelato è quella della
  versione usata (`trgfn_documenti_generati_guard_versione_contesto`);
* **l'azienda è nel perimetro di chi scrive** (`script.trgfn_guard_emittente_scope`).

Il modello, la versione, il tipo di output, il tipo di sorgente e l'azienda devono essere attivi quando la
stampa nasce: lo verificano a fine transazione i controlli generati dalla regola ATTIVO.

---

### ⭐ La stampa non cambia e non si cancella

Dopo l'inserimento cambiano solo `stato` e `meta`: ogni altro campo dello snapshot è fermo
(`trgfn_documenti_generati_protect_snapshot`), e la riga non si cancella mai
(`trgfn_documenti_generati_block_delete`). Le impronte (`context_hash`, `template_hash`, `pdf_hash`) sono
SHA-256 di 64 caratteri, e permettono di verificare che il PDF conservato sia quello prodotto.

Per questo lo storico standard su questa tabella è spento: la tabella è essa stessa il registro, e lo storico
ripeterebbe solo `stato` e `meta`. Ciò che succede alla stampa dopo (scaricamenti, allegati aggiunti,
ristampe fedeli) sta in `documenti_generati_eventi`; i file in `documenti_generati_file`.

---

### Lo stato

`stato` ammette `GENERATO` (il valore con cui la stampa nasce), `ARCHIVIATO` e `ANNULLATO`, con un `CHECK`. Lo
stato è l'unico modo previsto per chiudere la vita di una stampa, perché la riga non si cancella.

---

### Chi vede le stampe

La riga segue il perimetro delle aziende: un operatore vede e scrive solo le stampe delle aziende del suo
perimetro (`rls_documenti_generati_ef_whitelist`). I file e gli eventi seguono il perimetro della stampa a cui
appartengono.

---

### ⚠️ Che cosa oggi non copre

* **Nessuno cambia lo stato.** Né il database né il backend hanno una strada che porti una stampa ad
  `ARCHIVIATO` o ad `ANNULLATO`: oggi ogni stampa resta `GENERATO`. Il `CHECK` ammette i tre valori, ma non c'è
  una regola sui passaggi: un `UPDATE` diretto può riportare una stampa annullata a `GENERATO`.
* **La coerenza col modello si ricontrolla anche a ogni modifica, sul modello di oggi.** Il controllo gira anche
  sull'`UPDATE` di `stato` e `meta`, e legge sorgente, tipo e azienda del modello come sono adesso. Quelle
  colonne del modello non sono bloccate: se cambiano dopo la stampa, la stampa vecchia non accetta più nemmeno
  un cambio di `meta`.
* **Una stampa non si spegne, e tiene acceso il modello.** La tabella non ha `attivo`, quindi ogni stampa conta
  come figlio vivo per i blocchi della regola ATTIVO: un modello, una versione, un tipo di output, un tipo di
  sorgente o un'azienda che hanno anche una sola stampa non si possono più disattivare. I controlli dal lato
  della stampa, invece, scattano solo quando nasce o quando cambia la chiave, che è ferma: la stampa non ha
  bisogno che il padre resti acceso dopo.

---

### Codici errore

* `E_DOCUMENTI_GENERATO_COERENZA` — il modello o la versione non vanno bene per la stampa;
* `E_DOCUMENTI_VERSIONE_CONTESTO_DIVERSA`, `E_DOCUMENTI_VERSIONE_CONTESTO_NON_VERIFICABILE` — la forma dei dati;
* `E_DOCUMENTI_GENERATO_SNAPSHOT_IMMUTABILE` — si è cercato di cambiare lo snapshot;
* `E_DOCUMENTI_GENERATO_DELETE_BLOCKED` — si è cercato di cancellare la stampa.

---

### Test

* `db/pgtap/documenti/test-documenti-generati.sql` — coerenza, numerazione, cancellazione, snapshot;
* `db/pgtap/documenti/test-sorgente-documenti-generati-v1.sql` — la provenienza e il guard unico;
* `db/pgtap/documenti/test-documenti-versione-contesto-v1.sql` — la forma dei dati;
* `db/pgtap/documenti/test-documenti-storico-disabled.sql` — lo storico spento;
* `db/pgtap/rls/test-rls-documenti-satelliti.sql` — il perimetro di file ed eventi.

---

### Note di migrazione

* 2026-04-29 — nasce la tabella, con lo storico standard spento dal 2026-05-01.
* 2026-09-30 — una stampa si registra solo se la forma del contesto è quella che la versione del template legge.
* 2026-10-20 — un modello standard va bene per la stampa di qualunque azienda.
* 2026-10-21 — la coerenza con il modello passa alla regola comune che usa anche la risoluzione del modello.
* 2026-11-06 — nasce `sorgente_id`, per i documenti a chiave `id`.
* 2026-11-07 — la chiave del documento, prima scritta come testo in `sorgente_uid` per ogni tipo, passa al
  modello comune: `sorgente_id` per i tipi a chiave `id`, `sorgente_uid` (ora `uuid`, nullable) per preventivo e
  offerta, una sola delle due; il guard unico; l'unicità del progressivo anche su `sorgente_id`, che entra nello
  snapshot.

---

{% include-markdown "signature-core.md" %}
