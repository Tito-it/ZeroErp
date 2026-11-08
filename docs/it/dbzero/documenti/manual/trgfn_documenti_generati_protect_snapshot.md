## 📘 Documentazione Concettuale – Trigger function `documenti.trgfn_documenti_generati_protect_snapshot`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [documenti.documenti_generati](/dbzero/documenti/tabelle/documenti_generati) — la tabella che il trigger protegge
>
> Approfondimento funzioni:
>
> * [documenti.trgfn_documenti_generati_block_delete](/dbzero/documenti/funzioni/trgfn_documenti_generati_block_delete) — il blocco della cancellazione
> * [documenti.trgfn_documenti_generati_check_coerenza](/dbzero/documenti/funzioni/trgfn_documenti_generati_check_coerenza) — la coerenza dei riferimenti
> * [documenti.trgfn_documenti_generati_file_protect_file](/dbzero/documenti/funzioni/trgfn_documenti_generati_file_protect_file) — la stessa protezione sul file
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — il rifiuto

---

### 🎯 Scopo Principale

Trigger function `BEFORE UPDATE` su `documenti.documenti_generati` che blocca la modifica di
**tutti i campi snapshot** del record di generazione.

`documenti_generati` è un'**istantanea immutabile** del momento in cui un PDF (o un output
equivalente) è stato prodotto: `context_json`, gli hash, i riferimenti al template, la
provenienza, l'emittente, l'autore, il momento, gli identificatori pubblici. Modificare uno di
questi campi corromperebbe l'istantanea, e l'audit della generazione non sarebbe più
riproducibile.

Restano modificabili solo `stato`, per il ciclo di vita (`GENERATO → ARCHIVIATO/ANNULLATO`), e
`meta`, il canale per le annotazioni applicative.

---

### Che cosa è fermo

Il trigger (`trg_documenti_generati_a10_protect_snapshot_upd`, fascia `a10`, per riga)
confronta tutti i campi dello snapshot: gli identificatori (`uid` e le colonne `*_id`), la
provenienza (`sorgente_tipo_id`, `sorgente_id`, `sorgente_uid`, `sorgente_riga`,
`progressivo_sorgente`), la generazione (`generato_at`, `generato_da_user_id`), il contenuto
(`context_json`, `context_hash`, `template_hash`, `pdf_hash`) e i nomi (`titolo`, `nome_file`).
Se uno solo è cambiato rifiuta; altrimenti l'`UPDATE` passa, e con lui i campi di audit.

⚠️ **I campi che possono essere vuoti si confrontano con `IS DISTINCT FROM`.** Le due chiavi del
documento (`sorgente_id`, `sorgente_uid`: se ne valorizza una sola, quella del tipo),
`sorgente_riga` e `generato_da_user_id` ammettono `NULL`: un confronto con `<>` lascerebbe
passare in silenzio il passaggio da `NULL` a un valore, o il contrario.

⭐ **Un `OR` di confronti, non `UPDATE OF`.** Così i campi nullable si coprono bene, non c'è una
seconda lista di colonne da tenere allineata con la logica, e un campo nuovo dello snapshot è
una riga sola.

---

### Tre guard insieme

Il blocco della cancellazione, la coerenza dei riferimenti e l'immutabilità dello snapshot
rendono la tabella davvero append-only e coerente. Per questo lo storico standard su
`documenti_generati` non c'è: produrrebbe solo righe che ripetono `stato` e `meta`, gli unici
campi che cambiano.

---

### Codici errore

* `E_DOCUMENTI_GENERATO_SNAPSHOT_IMMUTABILE` — si è cercato di cambiare un campo dello snapshot;
  il contesto porta `documento_generato_id` e `uid`.

---

### Note di migrazione

* 2026-11-07 — lo snapshot comprende anche `sorgente_id`, la chiave dei documenti a chiave `id`;
  `sorgente_uid`, prima la chiave in testo di ogni tipo, diventa `uuid` e nullable, perché del
  documento se ne valorizza una sola.

---

{% include-markdown "signature-core.md" %}
