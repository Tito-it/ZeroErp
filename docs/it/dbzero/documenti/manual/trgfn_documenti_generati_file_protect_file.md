## 📘 Documentazione Concettuale – Trigger function `documenti.trgfn_documenti_generati_file_protect_file`

> **Ultimo aggiornamento**: 14 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [documenti.documenti_generati_file](/dbzero/documenti/tabelle/documenti_generati_file) — i file che il trigger protegge
> * [documenti.documenti_generati](/dbzero/documenti/tabelle/documenti_generati) — la stampa a cui il file appartiene
>
> Approfondimento funzioni:
>
> * [documenti.trgfn_documenti_generati_protect_snapshot](/dbzero/documenti/funzioni/trgfn_documenti_generati_protect_snapshot) — la stessa protezione sulla stampa
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — il rifiuto
>
> Guide:
>
> * [Documenti e stampe](/guide/documenti-e-stampe) — le garanzie del modulo

---

### 🎯 Scopo Principale

Trigger function `BEFORE UPDATE` su `documenti.documenti_generati_file` che rifiuta la modifica del file salvato e
del suo ruolo: un file registrato non si sostituisce.

Cambiare la posizione nello storage, l'impronta o la dimensione vorrebbe dire puntare a un altro file e dire il
falso su ciò che è stato emesso. È la controparte, sul file, dell'immutabilità dello snapshot della stampa.

---

### Che cosa è fermo, che cosa no

Sono fermi la stampa e il ruolo del file (`documento_generato_id`, `file_tipo_id`), il file (`storage_key`,
`sha256`, `file_size_bytes`, `mime_type`, `file_name`) e `is_principale`: il file principale si sceglie quando la
stampa nasce, e chi cerca «il» file di una stampa deve trovare sempre lo stesso. Insieme all'indice che ammette un
solo principale per stampa, la scelta resta stabile e unica.

Restano modificabili `ordinamento`, `meta` e i campi di audit.

Un PDF sbagliato non si corregge sul posto: la stampa si rigenera, e la nuova ha il suo progressivo e i suoi file.

---

### Codici errore

* `E_DOCUMENTI_GENERATO_FILE_IMMUTABILE` — si è cercato di cambiare il file o il suo ruolo; il contesto porta la
  stampa e il ruolo.

---

### Test

* `db/pgtap/documenti/test-documenti-generati-file.sql` — `storage_key` e `is_principale` rifiutati, `meta`
  ammesso.

---

### Note di migrazione

* 2026-05-01 — nasce il blocco, insieme a `is_principale`.
* 2026-08-05 — il rifiuto arriva col suo codice, invece di un errore generico.

---

{% include-markdown "signature-core.md" %}
