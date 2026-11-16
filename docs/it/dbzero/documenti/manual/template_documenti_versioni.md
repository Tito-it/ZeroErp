## 📘 Documentazione Concettuale – Tabella `documenti.template_documenti_versioni`

> **Ultimo aggiornamento**: 15 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [documenti.template_documenti](/dbzero/documenti/tabelle/template_documenti) — il modello a cui la versione appartiene
> * [documenti.render_engine_documento](/dbzero/documenti/tabelle/render_engine_documento) — il motore che la rende
> * [documenti.formati_template](/dbzero/documenti/tabelle/formati_template) — i formati della sorgente
> * [documenti.formati_pagina](/dbzero/documenti/tabelle/formati_pagina) — i formati di pagina
> * [documenti.orientamenti_pagina](/dbzero/documenti/tabelle/orientamenti_pagina) — gli orientamenti di pagina
> * [documenti.documenti_generati](/dbzero/documenti/tabelle/documenti_generati) — le stampe fatte con la versione
> * [dbops.automazione_overlap](/dbzero/dbops/tabelle/automazione_overlap) — il registro del vincolo di non sovrapposizione
>
> Approfondimento viste:
>
> * [documenti.vw_template_versioni_stampabili](/dbzero/documenti/views/vw_template_versioni_stampabili) — la sede unica di «questa versione stampa oggi»
>
> Approfondimento funzioni:
>
> * [documenti.fn_pubblica_template_documento_versione](/dbzero/documenti/funzioni/fn_pubblica_template_documento_versione) — la pubblicazione
> * [documenti.fn_crea_bozza_da_versione](/dbzero/documenti/funzioni/fn_crea_bozza_da_versione) — la copia di una versione in una bozza
> * [documenti.fn_guard_versione_contesto](/dbzero/documenti/funzioni/fn_guard_versione_contesto) — il patto sulla forma dei dati
> * [documenti.trgfn_template_documenti_versioni_protect_pubblicata](/dbzero/documenti/funzioni/trgfn_template_documenti_versioni_protect_pubblicata) — fuori bozza la versione non cambia
> * [documenti.trgfn_template_documenti_versioni_block_delete](/dbzero/documenti/funzioni/trgfn_template_documenti_versioni_block_delete) — quali versioni si cancellano
> * [documenti.trgfn_template_documenti_versioni_guard_derivata_da](/dbzero/documenti/funzioni/trgfn_template_documenti_versioni_guard_derivata_da) — l'origine di una copia
> * [documenti.trgfn_template_standard_guard_sola_lettura](/dbzero/documenti/funzioni/trgfn_template_standard_guard_sola_lettura) — le versioni dello standard in sola lettura
> * [script.trgfn_guard_date_validita](/dbzero/script/funzioni/trgfn_guard_date_validita) — l'ordine delle due date
>
> Guide:
>
> * [Documenti e stampe](/guide/documenti-e-stampe) — versioni, stati e date

---

### 🎯 Scopo Principale

`documenti.template_documenti_versioni` contiene le **versioni da stampare** di un modello: il
corpo (HTML, CSS, markdown), il motore che lo rende, la pagina del PDF, la forma dei dati che legge,
lo stato e il periodo di validità.

Un modello ha più versioni nel tempo, numerate da 1 (`versione`, unica per modello). Una versione
nuova non cancella le precedenti: restano per la ristampa e per l'audit.

---

### Tre stati: bozza, pubblicata, obsoleta

* **`BOZZA`**: in preparazione. Si modifica liberamente e non stampa.
* **`PUBBLICATA`**: si usa per stampare nel suo periodo di validità. Ha sempre una data di inizio.
* **`OBSOLETA`**: superata da una pubblicazione successiva, chiusa al giorno prima della nuova.
  Stampa ancora fino all'ultimo giorno della sua validità.

⛔ **Fuori bozza la versione non cambia.** Una versione pubblicata o obsoleta non si modifica, e il
suo stato non torna indietro: corpo, motore, pagina, margini, date, forma dei dati, modello, numero e
stato sono quelli della pubblicazione. Per cambiare il layout si crea una bozza nuova e la si
pubblica. Restano liberi solo `titolo`, `meta` e `attivo`. L'unica scrittura ammessa è la chiusura
che fa la pubblicazione della versione successiva
([protect_pubblicata](/dbzero/documenti/funzioni/trgfn_template_documenti_versioni_protect_pubblicata)).

Si pubblica con
[fn_pubblica_template_documento_versione](/dbzero/documenti/funzioni/fn_pubblica_template_documento_versione),
che chiude e rende obsolete le versioni pubblicate che la nuova supera, nella stessa transazione.

---

### ⭐ Che cosa stampa lo decidono le date, non lo stato

Una versione stampa a una data se è attiva, fuori bozza (pubblicata o obsoleta), il suo modello è
attivo e la sua validità contiene la data operativa. La sede unica di questo predicato è
[vw_template_versioni_stampabili](/dbzero/documenti/views/vw_template_versioni_stampabili).

Per questo una versione pubblicata in anticipo non lascia il modello senza stampa: la precedente,
già obsoleta, stampa fino alla vigilia, e la nuova dal giorno di partenza.

`validita` è un intervallo generato da `valido_dal` e `valido_al`, estremi compresi; una data vuota
vuol dire «senza limite» da quel lato. L'ordine delle due date lo verifica il guard comune delle date
(`E_DATA_AL_MINORE_DAL`).

---

### Per ogni data, al più una versione che stampa

Due versioni attive fuori bozza dello stesso modello non si sovrappongono nel tempo
(`ex_template_documenti_versioni_no_overlap_pubblicata`): le bozze e le versioni spente restano fuori
dal vincolo. Il predicato è dichiarato anche nel registro `dbops.automazione_overlap`, da cui il
framework ricrea il vincolo. Il backend traduce la violazione per nome in `E_DOCUMENTI_VERSIONE_OVERLAP`.

---

### Il patto con la forma dei dati

Un PDF nasce dal template (questa riga) e dai dati che un builder del backend prepara. Se la forma
dei dati cambia e il template no, le chiavi che il template non trova diventano vuote e il documento
esce incompleto senza errore. Il patto chiude questo caso.

* Ogni versione dichiara in `versione_contesto` la forma che legge: obbligatoria, da 1, **senza
  default**, perché chi crea la versione deve dichiararla.
* Il builder dichiara la forma che produce, nel contesto della stampa.
* Si stampa solo se i due numeri coincidono. La regola sta in
  [fn_guard_versione_contesto](/dbzero/documenti/funzioni/fn_guard_versione_contesto), che la
  chiamano il backend prima del render, il trigger sull'inserimento di una stampa e la pubblicazione.
* In bozza la forma si cambia, anche verso una che il builder non produce ancora: è così che si
  prepara la versione per la forma successiva. Fuori bozza non si cambia.
* Il numero è del tipo di documento, non globale: la forma 2 del preventivo non è la forma 2 del DDT.

Un cambio di forma si fa insieme: la forma nuova nel builder e una versione che la dichiara,
pubblicata. La ristampa dei documenti già emessi non cambia: rilegge il contesto congelato e la
versione usata allora.

`context_schema` è oggi un oggetto vuoto che nessuno controlla: le singole variabili del template
non si validano.

---

### La pagina: tre vocabolari che non si configurano

Formato della sorgente (`formato_template`), formato e orientamento della pagina (`page_format`,
`page_orientation`) sono legati per FK al `codice_interno` di tre vocabolari
(`formati_template`, `formati_pagina`, `orientamenti_pagina`). Si leggono per riempire le tendine e
non si configurano: un valore nuovo nasce insieme al motore di stampa che lo sa onorare. I margini,
in millimetri, sono numeri finiti e non negativi.

---

### L'origine di una copia

`derivata_da_versione_id` dice da quale versione di uno standard è partita una copia personalizzata.
Punta solo a una versione di uno standard dello stesso tipo e della stessa sorgente, e cambia solo in
bozza ([guard_derivata_da](/dbzero/documenti/funzioni/trgfn_template_documenti_versioni_guard_derivata_da)).
Vuota vuol dire versione scritta da zero, oppure versione successiva della stessa copia, che eredita
l'origine dalla più recente che la dichiara. La legge
[vw_template_personalizzati_scarto](/dbzero/documenti/views/vw_template_personalizzati_scarto).

L'origine è la provenienza della copia, non un padre vivo: la sua chiave è un'eccezione della regola ATTIVO
(`dbops.automazione_attivo_eccezioni`). Una versione dello standard da cui deriva una copia si spegne lo
stesso, e così una versione che ha stampato: le stampe sono storia.

---

### Cancellare una versione

Si cancella solo una bozza che nessuna stampa ha usato
([block_delete](/dbzero/documenti/funzioni/trgfn_template_documenti_versioni_block_delete)). Le
versioni dello standard non si cancellano dall'applicazione.

---

### ⚠️ Che cosa oggi non copre

* **Si può pubblicare senza la pubblicazione.** La protezione scatta solo quando la versione è già
  fuori bozza: un UPDATE che porta una bozza a `PUBBLICATA`, o un INSERT che la fa nascere
  `PUBBLICATA` o `OBSOLETA`, passa senza il controllo della forma dei dati e senza la chiusura della
  precedente. Il vincolo di non sovrapposizione resta, e la forma la ricontrolla la stampa.
* `chk_template_documenti_versioni_valido_dal_pubblicata` pretende la data di inizio solo da una
  `PUBBLICATA`: una versione che nasce `OBSOLETA` senza inizio vale «da sempre».

---

### Codici errore

* `E_DOCUMENTI_VERSIONE_PUBBLICATA_IMMUTABILE` — modifica di una versione fuori bozza, o della sua
  origine.
* `E_DOCUMENTI_VERSIONE_DELETE_BLOCKED` — cancellazione di una versione fuori bozza o già usata.
* `E_DOCUMENTI_TEMPLATE_DERIVAZIONE_INVALIDA` — origine che non è una versione dello standard dello
  stesso documento.
* `E_DOCUMENTI_TEMPLATE_STANDARD_SOLA_LETTURA` — scrittura dall'applicazione su una versione dello
  standard.
* `E_DATA_AL_MINORE_DAL` — fine che precede l'inizio.

---

### Test

* `db/pgtap/documenti/test-documenti-template-versioni.sql` — validità generata, non
  sovrapposizione, immutabilità fuori bozza, cancellazione, forma dei dati in bozza.
* `db/pgtap/documenti/test-fn-pubblica-template-documento-versione-v1.sql` — pubblicazione,
  chiusura, stampabilità dalla validità, immutabilità delle obsolete.
* `db/pgtap/documenti/test-documenti-versione-contesto-v1.sql` — il patto sulla forma dei dati.
* `db/pgtap/documenti/test-documenti-vocabolari-versione-v1.sql` — i tre vocabolari della pagina.
* `db/pgtap/documenti/test-documenti-template-standard-v1.sql` — l'origine di una copia.

---

### Note di migrazione

* 2026-04-29 — nasce la tabella.
* 2026-05-14 — `validita` diventa una colonna generata.
* 2026-09-30 — nasce `versione_contesto`, obbligatoria.
* 2026-10-04 — formato e orientamento passano da tre CHECK a tre vocabolari con FK.
* 2026-10-20 — nasce `derivata_da_versione_id`.
* 2026-11-14 — il vincolo di non sovrapposizione e la stampabilità comprendono le `OBSOLETA`, che da
  allora non si modificano e non tornano in bozza.
* 2026-11-15 — una versione si spegne anche se ha stampato o se una copia ne deriva.

---

{% include-markdown "signature-core.md" %}
