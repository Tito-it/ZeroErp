## 📘 Documentazione Concettuale – Trigger Function `vendite.trgfn_contratti_righe_guard_aggiunta_fuori_listino()`

> 👀 **Vedi anche**
>
> Tabelle correlate:
>
> [vendite.contratti_righe](/dbzero/vendite/tabelle/contratti_righe) — tabella guardata
> [vendite.contratti](/dbzero/vendite/tabelle/contratti) — contratto padre (listino_id, listino_versione_id)
> [vendite.listini_versioni](/dbzero/vendite/tabelle/listini_versioni) — versioni del listino
> [vendite.listini_righe](/dbzero/vendite/tabelle/listini_righe) — righe del listino
>
> Funzioni correlate:
>
> [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)
>
> Tipo ENUM:
>
> [vendite.tipo_eccezione_contratto](/dbzero/vendite/tabelle/contratti_righe) — OVERRIDE / ESCLUSIONE / AGGIUNTA

La trigger function **`vendite.trgfn_contratti_righe_guard_aggiunta_fuori_listino()`** impedisce di usare `tipo_eccezione = 'AGGIUNTA'` per un articolo **già presente nel listino del contratto**. Garantisce che la semantica di AGGIUNTA (articolo fuori listino) sia rispettata a livello DB, indipendentemente dal chiamante.

---

### 🎯 Scopo Principale

Un operatore che vuole modificare il prezzo di un articolo già in listino deve usare `OVERRIDE`, non `AGGIUNTA`. Questo guard è la **barriera DB-first** che rende impossibile la confusione tra i due tipi, anche da psql diretto o da chiamate API non validate.

---

### Logica a 3 branch

Il trigger legge `listino_id` e `listino_versione_id` dal contratto padre via JOIN su `vendite.contratti`.

| Branch | Condizione | Comportamento |
| --- | --- | --- |
| **1 — Senza listino** | `listino_id IS NULL` | AGGIUNTA sempre valida, nessun check |
| **2 — Contratto DRAFT** | `listino_id IS NOT NULL` + `listino_versione_id IS NULL` | Verifica l'articolo nella versione attiva a `CURRENT_DATE` (`listini_versioni WHERE validita @> CURRENT_DATE AND attivo = TRUE`) |
| **3 — Contratto ATTIVO** | `listino_id IS NOT NULL` + `listino_versione_id IS NOT NULL` | Verifica l'articolo nella versione fissata all'attivazione |

Per i branch 2 e 3: se l'articolo è trovato in `listini_righe` con `attivo = TRUE` → raise `E_CONTRATTO_AGGIUNTA_GIA_IN_LISTINO`.

Il trigger scatta anche su UPDATE: se si cambia `articolo_id` su una riga AGGIUNTA esistente, il nuovo articolo viene riverificato.

---

### Applicazione

Trigger creato dalla migration `20260515-12`:

* **`trg_contratti_righe_a10_guard_aggiunta_fuori_listino_ins_upd`** su `vendite.contratti_righe`
* Timing: **BEFORE INSERT OR UPDATE**
* Fase: **_a10_**
* Scope: **FOR EACH ROW**
* Filtro: **`WHEN (NEW.tipo_eccezione = 'AGGIUNTA')`** — il trigger non scatta per OVERRIDE o ESCLUSIONE

---

### Codice errore sollevato

**`E_CONTRATTO_AGGIUNTA_GIA_IN_LISTINO`** (id 450) — `config.messaggi_errore`.

Contesto JSONB registrato nel log: `contratto_id`, `articolo_id`, `listino_id`, `listino_versione_id`.

HTTP mapping (BE): `422 Unprocessable Entity`.

---

### Quando NON scatta

* `NEW.tipo_eccezione <> 'AGGIUNTA'` (OVERRIDE, ESCLUSIONE): filtrato dalla clausola `WHEN`.
* `contratto.listino_id IS NULL` (branch 1): early return, AGGIUNTA sempre ammessa.
* Articolo presente in `listini_righe` con `attivo = FALSE`: non è considerato "in listino".

---

### Relazione con altri vincoli

| Vincolo | Livello | Cosa garantisce |
| --- | --- | --- |
| `CHECK chk_contrighe_prezzo_per_tipo_eccezione` | CHECK declarativo | AGGIUNTA richiede `prezzo_unitario IS NOT NULL` |
| `uq_contrighe_one_aggiunta_per_articolo` | UNIQUE INDEX parziale | Al più 1 AGGIUNTA per coppia `(contratto, articolo)` |
| **Questo trigger** | BEFORE trigger _a10_ | Articolo AGGIUNTA deve essere fuori listino |
| `trg_contratti_righe_a10_lock_post_attivazione` (Step 2.3) | BEFORE trigger _a10_ | Nessuna modifica alle righe post-attivazione |

<!-- rev-2026-09-28-liste-righe -->
### 🔄 rev 2026-09-28 — brief-db-liste-righe-documento

La versione del listino in vigore per il contratto in bozza non è più scelta qui: la dice [vendite.fn_listino_versione_in_vigore](/dbzero/vendite/funzioni/fn_listino_versione_in_vigore) (`20260928-37`). Per ogni data la versione in vigore è **al più una**, per costruzione (nessuna sovrapposizione fra versioni ATTIVE e CHIUSE, date di una CHIUSA bloccate), quindi «la prima» e «tutte le valide» sono la stessa cosa. Stesso esito, provato sui dati di dev.

---

{% include-markdown "signature-core.md" %}

---
