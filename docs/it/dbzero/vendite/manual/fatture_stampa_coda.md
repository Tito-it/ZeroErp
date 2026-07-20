## 📘 Documentazione Concettuale – Tabella `vendite.fatture_stampa_coda`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture)  
> • [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti)  
> • [vendite.fatturazione_pipeline](/dbzero/vendite/tabelle/fatturazione_pipeline)  
>

### 🎯 Scopo Principale
`vendite.fatture_stampa_coda` è la **coda (outbox) della stampa massiva delle fatture**.
Il task di pipeline `stampa_documenti_lotto` vi **accoda** un work-item per fattura al momento
della numerazione (step DEFINITIVA), poi lo step chiude subito la transazione; un **worker**
esterno drena la coda, garantisce la numerazione (backstop idempotente) e delega il render al
processo di stampa generico. Così il rendering dei PDF **non** avviene dentro la transazione
di numerazione e **non** tiene il lock del registro fiscale.

---

### Campi chiave (semantica)

* **Sorgente (satellite fattura)**: `sorgente_tipo_id` (= FATTURA da `config.sorgenti`),
  `sorgente_id` (= `vendite.fatture.id`, FK), `sorgente_uid` (`id::text`) — colonne "a forma
  di" `documenti.genera_documento`.
* **Provenienza**: `lotto_id` (FK, `ON DELETE SET NULL`; `NULL` per ristampa on-demand).
* **Lavorazione**: `stato` (`PENDING` → `IN_CORSO` → `FATTO`/`ERRORE`), `tentativi`,
  `ultimo_errore` (dettaglio JSONB dell'ultimo fallimento).
* **Esito**: `documento_id` (documento prodotto a `FATTO`).
* **Override**: `template_documento_id` (opzionale; `NULL` = default per sorgente/emittente/output).
* **Governance**: audit standard + `tx_id`.

---

### Regole principali

* **Un solo work-item "vivo" per fattura**: indice unico **parziale**
  `uq_fatture_stampa_coda_vivo` su `(sorgente_tipo_id, sorgente_id)` limitato a
  `PENDING`/`IN_CORSO`. Rende l'accodamento (`vendite.fn_accoda_stampe_lotto`) **idempotente**
  (`ON CONFLICT DO NOTHING`) e consente il ri-accodamento dopo `FATTO`/`ERRORE` (ristampa).
* **Stati ammessi** (CHECK `chk_fatture_stampa_coda_stato`): `PENDING`, `IN_CORSO`, `FATTO`,
  `ERRORE`. **Tentativi** `>= 0` (CHECK `chk_fatture_stampa_coda_tentativi`).
* **Satellite della fattura**: `sorgente_id` FK a `vendite.fatture` (`ON DELETE CASCADE`). La
  RLS operatori (scope emittente) **delega alla fattura** via
  `script.fn_scope_ef_whitelist_via_fattura(sorgente_id)`, senza colonna emittente
  denormalizzata; l'attivazione RLS segue il playbook della famiglia fatture con ondata
  dedicata (in G1 la coda non ha superficie di lettura → nessuna policy).

---

### Utilizzo previsto

* disaccoppiare il **render dei PDF** dalla transazione di numerazione fiscale (nessun lock
  del registro tenuto durante l'I/O di generazione);
* garantire che ogni fattura stampata sia **numerata** (backstop idempotente
  `vendite.fn_numera_fattura_opz_emessa` nel worker);
* base per il **monitoraggio** della stampa massiva (filtro per lotto) e per la **ristampa**
  on-demand di una singola fattura;
* **polling FIFO** del worker sui soli da-lavorare via indice parziale
  `ix_fatture_stampa_coda_da_lavorare`.

---

{% include-markdown "signature-core.md" %}
