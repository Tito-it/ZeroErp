## 📘 Documentazione Concettuale – Trigger function `documenti.trgfn_template_documenti_versioni_block_delete`

> **Ultimo aggiornamento**: 14 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [documenti.template_documenti_versioni](/dbzero/documenti/tabelle/template_documenti_versioni) — la tabella protetta
> * [documenti.documenti_generati](/dbzero/documenti/tabelle/documenti_generati) — le stampe che usano una versione
>
> Approfondimento funzioni:
>
> * [documenti.trgfn_template_documenti_versioni_protect_pubblicata](/dbzero/documenti/funzioni/trgfn_template_documenti_versioni_protect_pubblicata) — fuori bozza la versione non cambia
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — la registrazione dell'errore
>
> Guide:
>
> * [Documenti e stampe](/guide/documenti-e-stampe) — versioni e stati

---

### 🎯 Scopo Principale

Permette di cancellare solo una **bozza che nessuna stampa ha usato**. È montata `BEFORE DELETE` su
`documenti.template_documenti_versioni`.

---

### Due rifiuti

* Una versione **pubblicata o obsoleta** non si cancella: la storia delle pubblicazioni resta, per la
  ristampa e per l'audit.
* Una versione che **una stampa ha usato** non si cancella, qualunque sia il suo stato.

Il caso tipico che passa è la bozza creata per errore. Il secondo controllo ripete quello della FK di
`documenti_generati` verso la versione, che già impedisce la cancellazione: qui il rifiuto arriva
con un codice che dice il perché.

Una versione di uno standard, anche in bozza, dall'applicazione non si cancella comunque: lo
impedisce prima il guard di sola lettura.

---

### Codici errore

* `E_DOCUMENTI_VERSIONE_DELETE_BLOCKED` — versione fuori bozza, oppure usata da una stampa. Il
  contesto porta modello, numero e lo stato, oppure il numero di stampe che la usano.

---

### Test

* `db/pgtap/documenti/test-documenti-template-versioni.sql` — una pubblicata non si cancella, una
  bozza non usata sì.

---

### Note di migrazione

* 2026-05-01 — nasce il guard.
* 2026-08-05 — il guard solleva il suo codice: fino ad allora chiamava la registrazione dell'errore
  con una firma che non esisteva, e moriva con un errore tecnico.

---

{% include-markdown "signature-core.md" %}
