## 📘 Documentazione Concettuale – Trigger function `documenti.trgfn_template_asset_protect_file`

> **Ultimo aggiornamento**: 17 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [documenti.template_asset](/dbzero/documenti/tabelle/template_asset) — la tabella protetta
>
> Approfondimento funzioni:
>
> * [script.trgfn_prevent_modification_generic](/dbzero/script/funzioni/trgfn_prevent_modification_generic) — un asset non si cancella
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — la registrazione dell'errore
>
> Guide:
>
> * [Documenti e stampe](/guide/documenti-e-stampe) — gli asset nella stampa

---

### 🎯 Scopo Principale

Impedisce di cambiare il **file** di un asset documentale: chiave nello storage, impronta SHA-256,
peso, tipo MIME e nome del file restano quelli del caricamento. È montata `BEFORE UPDATE` su
`documenti.template_asset`.

---

### Il file è l'identità dell'asset

Un asset è il file caricato per un'azienda. Cambiare sul posto il file, o anche solo la sua impronta,
vorrebbe dire che lo stesso asset indica byte diversi da quelli con cui un documento è stato
stampato, e la ristampa fedele non ritroverebbe il file di allora. Per un file diverso si carica un
asset nuovo.

La regola vale da subito, anche per un asset che nessun template ha ancora usato.

Restano liberi descrizione, codice, il tipo (se ammette il formato del file), meta, attivo e le
date: spegnere l'asset o chiuderne la validità è il modo di ritirarlo. Il codice interno non cambia per un'altra ragione (il lock di colonna).

Il trigger scatta su ogni UPDATE e confronta le cinque colonne nel corpo: tutte e cinque sono
obbligatorie, quindi il confronto non incontra valori vuoti.

---

### Codici errore

* `E_DOCUMENTI_ASSET_FILE_IMMUTABILE` — almeno una delle cinque colonne del file è cambiata. Il
  contesto porta id, azienda e codice interno dell'asset.

---

### Test

* `db/pgtap/documenti/test-documenti-template-asset.sql` — ognuna delle cinque colonne del file è
  ferma, anche su un asset spento; il codice interno lo ferma il lock; codice, descrizione, date,
  attivo e `meta` sono liberi.

---

### Note di migrazione

* 2026-05-01 — nasce il guard.
* 2026-08-05 — il guard solleva il suo codice: fino ad allora chiamava la registrazione dell'errore
  con una firma che non esisteva, e moriva con un errore tecnico.

---

{% include-markdown "signature-core.md" %}
