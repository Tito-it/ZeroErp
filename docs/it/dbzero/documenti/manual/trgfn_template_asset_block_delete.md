## 📘 Documentazione Concettuale – Trigger function `documenti.trgfn_template_asset_block_delete`

> **Ultimo aggiornamento**: 14 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [documenti.template_asset](/dbzero/documenti/tabelle/template_asset) — la tabella protetta
>
> Approfondimento funzioni:
>
> * [documenti.trgfn_template_asset_protect_file](/dbzero/documenti/funzioni/trgfn_template_asset_protect_file) — il file di un asset non cambia
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — la registrazione dell'errore
>
> Guide:
>
> * [Documenti e stampe](/guide/documenti-e-stampe) — gli asset nella stampa

---

### 🎯 Scopo Principale

Rifiuta **sempre** la cancellazione di un asset documentale. È montata `BEFORE DELETE` su
`documenti.template_asset`.

---

### ⛔ Un asset non si cancella, si ritira

La regola non ha eccezioni: non guarda se l'asset è attivo, scaduto o citato da un template. Un
asset che non serve più si ritira chiudendone la validità o spegnendolo, e la riga resta.

La ragione è la ristampa fedele: un documento già emesso si ristampa con l'asset di allora, cercato
per codice fra gli asset della sua azienda. Se l'asset sparisse, la ristampa non ritroverebbe il
file. Nessuna FK lo impedirebbe: fra un asset e i template o le stampe che lo usano non c'è un
riferimento, ma solo il codice scritto nel corpo della versione.

Insieme a [protect_file](/dbzero/documenti/funzioni/trgfn_template_asset_protect_file), che
impedisce di cambiare il file, fa di ogni asset un'istantanea stabile.

---

### Codici errore

* `E_DOCUMENTI_ASSET_DELETE_BLOCKED` — ogni DELETE. Il contesto porta id, azienda e codice interno
  dell'asset.

---

### Test

* `db/pgtap/documenti/test-documenti-template-asset.sql` — la cancellazione di un asset è rifiutata.

---

### Note di migrazione

* 2026-05-01 — nasce il guard.
* 2026-08-05 — il guard solleva il suo codice: fino ad allora chiamava la registrazione dell'errore
  con una firma che non esisteva, e moriva con un errore tecnico.

---

{% include-markdown "signature-core.md" %}
