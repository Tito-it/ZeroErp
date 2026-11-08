## 📘 Documentazione Concettuale – Tabella `documenti.documenti_generati`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [documenti.template_documenti](/dbzero/documenti/tabelle/template_documenti)  
> • [documenti.template_documenti_versioni](/dbzero/documenti/tabelle/template_documenti_versioni)  
> • [documenti.documenti_generati_file](/dbzero/documenti/tabelle/documenti_generati_file)  
> • [documenti.documenti_generati_eventi](documenti_generati_eventi.md) — timeline append-only del ciclo vita documento (anticipata da Fase B a v1)
> • [config.sorgenti](/dbzero/config/manual/sorgenti)  
>
> **Approfondimento funzioni:**
>
> • [script.trgfn_guard_sorgente](/dbzero/script/funzioni/trgfn_guard_sorgente) — il guard unico della provenienza  
> • [script.fn_sorgente_chiave](/dbzero/script/funzioni/fn_sorgente_chiave) — la coppia di chiavi da scrivere  
>
> **Guide:**
>
> • [Sorgente polimorfa](/guide/sorgente-polimorfa) — il modello della provenienza: tipo, documento, riga

---

### 🎯 Scopo Principale

`documenti.documenti_generati` è il **registro storico delle generazioni
persistite** del motore documentale. Ogni riga rappresenta un documento
prodotto, con snapshot del contesto, hash di audit e collegamento alla
versione template usata.

---

### Ruolo nel processo

* garantisce tracciabilità del documento effettivamente generato;
* conserva il collegamento al documento stampato (preventivo, offerta, ordine,
  bolla, contratto, fattura), ed eventualmente alla sua riga;
* disaccoppia lo storico prodotto dalle successive evoluzioni del template.

---

### Campi chiave (semantica)

* **Identita` storica**: `id`, `uid`.
* **Origine**: `sorgente_tipo_id` (il tipo del documento stampato, da
  `config.sorgenti`), una sola fra `sorgente_id` e `sorgente_uid` (la chiave del
  documento, quella che il tipo dichiara: `uid` per preventivo e offerta, `id` per
  gli altri), `sorgente_riga` (vuota se la stampa è del documento intero),
  `progressivo_sorgente` (la versione stampata, da 1).
* **Template usato**: `template_documento_id`, `template_versione_id`,
  `tipo_documento_output_id`.
* **Snapshot di audit**: `context_json`, `context_hash`, `template_hash`,
  `pdf_hash`.
* **Tracciamento operativo**: `generato_da_user_id`, `generato_at`, `stato`.

---

### Regole principali

* `uid` è un identificatore esterno stabile e univoco;
* ogni stampa nasce da un documento: il tipo è obbligatorio e c'è sempre **una**
  chiave del documento (`chk_documenti_generati_sorgente_forma`); documento e
  riga li verifica il guard unico `script.trgfn_guard_sorgente`, che **blocca** la
  cancellazione del documento finché una sua stampa lo cita;
* il progressivo è univoco per documento e riga
  (`sorgente_tipo + sorgente_id + sorgente_uid + sorgente_riga + progressivo_sorgente`),
  con `NULLS NOT DISTINCT`, perché la chiave che non si usa e la riga di una stampa
  del documento intero sono vuote;
* gli hash SHA-256 consentono verifica di integrità e audit del contenuto
  generato;
* lo storico non va interpretato come template "vivo": descrive un fatto già
  accaduto.
* ⭐ **una stampa si registra solo se è fedele al template**: il
  contesto congelato dichiara la sua forma in `context_json -> '_meta' -> 'context_version'`
  (un intero), e deve essere la forma che la versione usata legge
  (`template_documenti_versioni.versione_contesto`). Lo verifica all'INSERT
  [`trgfn_documenti_generati_guard_versione_contesto`](/dbzero/documenti/funzioni/trgfn_documenti_generati_guard_versione_contesto),
  che delega a [`fn_guard_versione_contesto`](/dbzero/documenti/funzioni/fn_guard_versione_contesto):
  forme diverse → `E_DOCUMENTI_VERSIONE_CONTESTO_DIVERSA`, forma assente o non intera →
  `E_DOCUMENTI_VERSIONE_CONTESTO_NON_VERIFICABILE`. Solo all'INSERT: contesto e versione non
  cambiano dopo (guard A7), e la ristampa fedele non scrive una riga nuova.

---

### Stato documento

* `GENERATO`: documento creato e registrato;
* `ARCHIVIATO`: documento consolidato nel suo ciclo di vita applicativo;
* `ANNULLATO`: storico mantenuto, ma record non più valido per uso operativo.

Nella Fase A lo stato ha semantica leggera; il cuore del valore tabellare è la
tracciabilità del render eseguito.

I cambi di stato (`GENERATO → ARCHIVIATO`/`ANNULLATO`) e gli eventi
applicativi (download, cleanup file orfani) sono tracciati nella timeline
append-only [`documenti_generati_eventi`](documenti_generati_eventi.md),
anticipata da Fase B a v1.

---

### Uso tipico nel processo

1. il backend seleziona template e versione;
2. genera il PDF e il relativo snapshot di contesto;
3. inserisce una riga storica in `documenti.documenti_generati`;
4. collega i file fisici prodotti in `documenti.documenti_generati_file`.

---

### Note di migrazione

* 2026-09-30 — una stampa si registra solo se la forma del contesto è quella che la versione
  del template legge.
* 2026-11-06 — nasce `sorgente_id`, per i documenti a chiave `id`.
* 2026-11-07 — la chiave del documento, prima scritta come testo in `sorgente_uid` per ogni tipo,
  passa al modello comune: `sorgente_id` per i tipi a chiave `id`, `sorgente_uid` (ora `uuid`,
  nullable) per preventivo e offerta, una sola delle due (`chk_documenti_generati_sorgente_forma`);
  il guard unico; l'unicità del progressivo anche su `sorgente_id`, che entra nello snapshot.

---

{% include-markdown "signature-core.md" %}
