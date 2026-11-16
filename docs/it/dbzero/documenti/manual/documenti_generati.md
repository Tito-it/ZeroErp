## 📘 Documentazione Concettuale – Tabella `documenti.documenti_generati`

> **Ultimo aggiornamento**: 15 novembre 2026
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
> * [documenti.trgfn_documenti_generati_guard_file_principale](/dbzero/documenti/funzioni/trgfn_documenti_generati_guard_file_principale) — la stampa nasce col suo PDF principale
> * [script.trgfn_prevent_modification_generic](/dbzero/script/funzioni/trgfn_prevent_modification_generic) — la stampa non si cancella
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

Alla nascita tre controlli guardano la stessa riga da tre lati:

* **il modello va bene per il documento**: la versione appartiene al modello indicato, e il modello ha la stessa
  sorgente, lo stesso tipo di output e la stessa azienda della stampa, oppure è un modello standard
  (`trgfn_documenti_generati_check_coerenza`);
* **i dati hanno la forma che la versione legge**: la forma dichiarata dal contesto congelato è quella della
  versione usata (`trgfn_documenti_generati_guard_versione_contesto`);
* **l'azienda è nel perimetro di chi scrive** (`script.trgfn_guard_emittente_scope`).

La coerenza si giudica **solo alla nascita**, sul modello com'è in quel momento. Se dopo il modello cambia
sorgente, tipo o azienda, la stampa vecchia non è sbagliata: è la fotografia di allora, e sull'`UPDATE` le
colonne che decidevano la coerenza le tiene ferme lo snapshot.

Quale modello e quale versione possono stampare oggi lo decide la risoluzione, prima del render
(`documenti.fn_risolvi_template_applicabile`): un modello spento o senza versione valida non viene scelto.

---

### ⭐ Una stampa nasce col suo PDF principale

A fine transazione ogni stampa nata ha il suo file principale, il PDF che si scarica e si ristampa
(`trgfn_documenti_generati_guard_file_principale`, differito: il servizio scrive prima la stampa e poi il
file). Basta il controllo alla nascita: il file non si cancella e il flag del principale non cambia. Il
controllo legge il file fuori dalla row security di chi chiude la transazione.

---

### ⭐ La stampa non cambia e non si cancella

Dopo l'inserimento cambia solo `meta`: ogni altro campo dello snapshot è fermo, `id` e `uid` compresi
(`trgfn_documenti_generati_protect_snapshot`), e la riga non si cancella mai, da nessun ruolo (il rifiuto
sempre attivo di `script.trgfn_prevent_modification_generic`). Le impronte (`context_hash`, `template_hash`, `pdf_hash`) sono
SHA-256 di 64 caratteri, e permettono di verificare che il PDF conservato sia quello prodotto.

Per questo lo storico standard su questa tabella è spento: la tabella è essa stessa il registro, e lo storico
ripeterebbe solo `meta`. Ciò che succede alla stampa dopo (scaricamenti, allegati aggiunti,
ristampe fedeli) sta in `documenti_generati_eventi`; i file in `documenti_generati_file`.

---

### Lo stato ha un valore solo

`stato` vale sempre `GENERATO`, il valore con cui la stampa nasce (`chk_documenti_generati_stato`). Una
stampa non si annulla e non si archivia: un annullo, quando un processo lo chiederà, nascerà col suo verbo e con
la regola dei suoi passaggi.

---

### ⭐ Una stampa non tiene accesi i suoi padri

La stampa è storia, non un figlio vivo. Le sue chiavi verso il modello, la versione, il tipo di output, il tipo
di sorgente e l'azienda sono eccezioni della regola ATTIVO (`dbops.automazione_attivo_eccezioni`): un modello,
una versione o un'azienda che hanno stampato si spengono come gli altri, e spegnere i propri modelli di un tipo
riporta l'azienda allo standard. Per la stessa ragione la regola ATTIVO non chiede che quei padri siano accesi
quando la stampa nasce: lo decide la risoluzione.

---

### Chi vede le stampe

La riga segue il perimetro delle aziende: un operatore vede e scrive solo le stampe delle aziende del suo
perimetro (`rls_documenti_generati_ef_whitelist`). I file e gli eventi seguono il perimetro della stampa a cui
appartengono.

---

### ⚠️ Che cosa oggi non copre

* **Una stampa nata da un modello spento la ferma solo il servizio.** Il database non chiede che modello,
  versione, tipo e azienda siano accesi quando la stampa nasce: lo garantisce la risoluzione che il servizio fa
  prima del render. Un `INSERT` diretto con un modello spento passa la coerenza.
* **Le stampe nate prima del controllo del PDF principale** non sono state giudicate: il controllo guarda le
  nascite, non le righe già scritte.

---

### Codici errore

* `E_DOCUMENTI_GENERATO_COERENZA` — il modello o la versione non vanno bene per la stampa;
* `E_DOCUMENTI_VERSIONE_CONTESTO_DIVERSA`, `E_DOCUMENTI_VERSIONE_CONTESTO_NON_VERIFICABILE` — la forma dei dati;
* `E_DOCUMENTI_GENERATO_SNAPSHOT_IMMUTABILE` — si è cercato di cambiare lo snapshot;
* `E_DOCUMENTI_GENERATO_SENZA_FILE_PRINCIPALE` — a fine transazione la stampa nata non ha il suo PDF
  principale: è un difetto di chi scrive, non un dato dell'operatore;
* `E_DOCUMENTI_GENERATO_DELETE_BLOCKED` — si è cercato di cancellare la stampa.

---

### Test

* `db/pgtap/documenti/test-documenti-generati.sql` — coerenza, numerazione, cancellazione, snapshot, lo stato
  con un valore solo;
* `db/pgtap/documenti/test-documenti-stampa-e-storia-v1.sql` — il PDF principale, l'`id` nello snapshot, la
  coerenza solo alla nascita, i padri che si spengono, il rifiuto sempre attivo;
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
* 2026-11-15 — lo stato perde `ARCHIVIATO` e `ANNULLATO`, che nessuno scriveva; la coerenza si giudica solo alla
  nascita; `id` entra nello snapshot; ogni stampa nuova deve avere il suo PDF principale; le chiavi verso i
  padri diventano eccezioni della regola ATTIVO; il rifiuto della cancellazione passa al building block comune.

---

{% include-markdown "signature-core.md" %}
