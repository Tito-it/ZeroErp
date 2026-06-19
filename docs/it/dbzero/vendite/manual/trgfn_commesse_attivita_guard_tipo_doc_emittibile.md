## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_commesse_attivita_guard_tipo_doc_emittibile()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)
> [config.tipi_doc_fiscale](/dbzero/config/tabelle/tipi_doc_fiscale)
> [config.sorgenti](/dbzero/config/tabelle/sorgenti)
> [config.messaggi_errore](/dbzero/config/tabelle/messaggi_errore)
>
Approfondimento funzioni:
> [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)
> [vendite.fn_upsert_commessa_attivita](/dbzero/vendite/funzioni/fn_upsert_commessa_attivita)
> [vendite.fn_list_emittibili_lane](/dbzero/vendite/funzioni/fn_list_emittibili_lane)
>
Guard di testata correlato:
> [vendite.trgfn_commesse_guard_transizione](/dbzero/vendite/funzioni/trgfn_commesse_guard_transizione)

### 🎯 Scopo Principale

(rev 2026-06-19)

La trigger function **`vendite.trgfn_commesse_attivita_guard_tipo_doc_emittibile()`** impone un
**invariante di riga** su `vendite.commesse_attivita`. È applicata dal trigger
`trg_commesse_attivita_a10_guard_tipo_doc_emittibile_ins_upd` (fase `_a10_`,
`BEFORE INSERT OR UPDATE OF stato_approvazione, stato_emissione, tipo_doc_fiscale_id`).

**Invariante:**

> una riga in stato `(stato_approvazione = 'APPROVATA' AND stato_emissione = 'NON_EMESSA')`
> **deve** avere `tipo_doc_fiscale_id IS NOT NULL`.

**Perché.** Una riga *emittibile* con `tipo_doc` NULL è **invisibile alla discovery delle
corsie** (`vendite.fn_list_emittibili_lane` richiede `tipo_doc_fiscale_id NOT NULL`, perché il
lotto lo esige) e **nessun altro processo la ripesca** → fatturato perso in silenzio. Il guard
sposta il fallimento sulla **creazione/approvazione** (dove è osservabile e correggibile),
invece che a valle dove scomparirebbe (pattern *normalize + guard simmetrico*; il *normalize*
vive in `fn_upsert_commessa_attivita`).

---

### Regole applicate

* Scatta su **INSERT** (riga creata direttamente in stato emittibile) e su **UPDATE OF** delle
  tre colonne rilevanti: approvazione di una riga (`stato_approvazione`), emissione, o
  azzeramento del `tipo_doc` su una riga già emittibile.
* È un invariante **di riga**, non *"almeno una riga della commessa"*: **ogni** riga che
  raggiunge lo stato emittibile deve avere il `tipo_doc`. Indipendente dal path di scrittura
  (`fn_upsert_commessa_attivita`, `fn_approva_commessa_attivita`, UPDATE diretto).
* Righe in altri stati (`BOZZA`, oppure `EMESSA`/`ANNULLATA`) con `tipo_doc` NULL sono
  **ammesse**: l'invariante vincola solo lo stato emittibile.

**Catena con il guard di testata.** Si incatena con
[`E_COMMESSA_NESSUNA_RIGA_APPROVATA`](/dbzero/vendite/funzioni/trgfn_commesse_guard_transizione)
(473): una commessa con sole righe a `tipo_doc` NULL non porta righe ad `APPROVATA`, quindi
fallisce già il 473 al passaggio a `PRONTA_FATTURAZIONE`. I due guard sono complementari.

---

### Codici errore

| Codice | Quando |
|--------|--------|
| `E_COMMESSA_ATTIVITA_TIPO_DOC_OBBLIGATORIO` (497) | Riga `(APPROVATA, NON_EMESSA)` con `tipo_doc_fiscale_id IS NULL` |

Sollevato via `script.fn_log_and_raise_error` (`SQLSTATE 'P0001'`, nessun `E_GENERICO`). Il
context jsonb riporta `commessa_id`, `attivita_id`, `segment_key`; i due `%s` del messaggio
sono `commessa_id` e `attivita_id`.

---

### Note di design

* **Difesa in profondità + perché `BEFORE`**: il guard dà l'errore *parlante* (497); il CHECK
  constraint `chk_commesse_attivita_tipo_doc_emittibile` (`NOT VALID`) è la rete di sicurezza
  dichiarativa su ogni path (errore non parlante, `SQLSTATE 23514`). In PostgreSQL i CHECK sono
  valutati **dopo i BEFORE trigger ma prima degli AFTER**: per questo il guard è `BEFORE` — così
  l'errore parlante è il primario e il CHECK resta un vero backstop (un guard `AFTER` verrebbe
  sempre preempato dal 23514 del CHECK). Coerente con `trgfn_commesse_guard_transizione`
  (anch'esso `BEFORE` `_a10_`).
* La validazione è pura (legge `NEW`, raises, `RETURN NEW`; non modifica la riga).
* **`UPDATE OF` mirato**: il trigger non scatta sugli UPDATE che non toccano stato/tipo_doc,
  per non gravare sul percorso di scrittura.

---

{% include-markdown "signature-core.md" %}
