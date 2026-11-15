## 📘 Documentazione Concettuale – Trigger function `documenti.trgfn_documenti_generati_protect_snapshot`

> **Ultimo aggiornamento**: 14 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [documenti.documenti_generati](/dbzero/documenti/tabelle/documenti_generati) — la stampa che il trigger protegge
>
> Approfondimento funzioni:
>
> * [documenti.trgfn_documenti_generati_block_delete](/dbzero/documenti/funzioni/trgfn_documenti_generati_block_delete) — il blocco della cancellazione
> * [documenti.trgfn_documenti_generati_check_coerenza](/dbzero/documenti/funzioni/trgfn_documenti_generati_check_coerenza) — la coerenza col modello
> * [documenti.trgfn_documenti_generati_file_protect_file](/dbzero/documenti/funzioni/trgfn_documenti_generati_file_protect_file) — la stessa protezione sul file
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — il rifiuto
>
> Guide:
>
> * [Documenti e stampe](/guide/documenti-e-stampe) — le garanzie del modulo

---

### 🎯 Scopo Principale

Trigger function `BEFORE UPDATE` su `documenti.documenti_generati` che rifiuta la modifica di qualunque campo dello
snapshot di una stampa: dopo l'inserimento cambiano solo `stato` e `meta`.

Una stampa è l'istantanea del momento in cui il documento è stato prodotto: il contesto, le impronte, il modello e
la versione, la provenienza, l'azienda, chi e quando. Cambiarne un pezzo la renderebbe un'altra stampa, e l'audit
della generazione non sarebbe più riproducibile.

---

### Che cosa è fermo

Il trigger confronta tutti i campi dello snapshot: il modello, la versione e il tipo di output, la provenienza
(tipo, le due chiavi del documento, la riga, il progressivo), l'azienda, il contesto e le tre impronte, il titolo e
il nome del file, l'`uid`, il momento e l'autore della generazione. Se uno solo è cambiato rifiuta; altrimenti
l'`UPDATE` passa, e con lui i campi di audit.

⚠️ **I campi che possono essere vuoti si confrontano con `IS DISTINCT FROM`.** Le due chiavi del documento (se ne
valorizza una sola), la riga e l'autore ammettono `NULL`: un confronto con `<>` lascerebbe passare in silenzio il
passaggio da vuoto a un valore, o il contrario.

⭐ **Un confronto per campo, non `UPDATE OF`.** Così i campi vuoti si coprono bene, e non c'è un secondo elenco di
colonne da tenere allineato con la regola.

---

### ⚠️ Che cosa oggi non copre

* **L'`id` non è fra i campi confrontati.** Un cambio dell'`id` si propaga ai file e agli eventi, che lo rifiutano
  con i loro blocchi; su una stampa senza file né eventi, però, passa.

---

### Codici errore

* `E_DOCUMENTI_GENERATO_SNAPSHOT_IMMUTABILE` — si è cercato di cambiare un campo dello snapshot; il contesto porta
  l'id e l'`uid` della stampa.

---

### Test

* `db/pgtap/documenti/test-documenti-generati.sql` — contesto e versione rifiutati, `stato` e `meta` ammessi;
* `db/pgtap/documenti/test-sorgente-documenti-generati-v1.sql` — la stampa spostata su un altro documento,
  rifiutata.

---

### Note di migrazione

* 2026-05-01 — nasce il blocco.
* 2026-11-07 — lo snapshot comprende anche `sorgente_id`, la chiave dei documenti a chiave `id`; `sorgente_uid`,
  prima la chiave in testo di ogni tipo, diventa `uuid` e nullable, perché del documento se ne valorizza una sola.

---

{% include-markdown "signature-core.md" %}
