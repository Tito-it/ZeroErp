## 📘 Documentazione Concettuale – Trigger Function `vendite.trgfn_contratti_freeze_listino_versione()`

> 👀 **Vedi anche**
>
> Tabelle correlate:
>
> [vendite.contratti](/dbzero/vendite/tabelle/contratti) — tabella guardata
> [vendite.listini_versioni](/dbzero/vendite/tabelle/listini_versioni) — versioni del listino
> [vendite.contratti_righe](/dbzero/vendite/tabelle/contratti_righe) — righe eccezioni (verifica AGGIUNTA)
>
> Funzioni correlate:
>
> [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)
> [vendite.trgfn_contratti_guard_transizione_stato](/dbzero/vendite/funzioni/trgfn_contratti_guard_transizione_stato) — guard complementare (scatta dopo)
>
> Trigger correlati:
>
> [vendite.trgfn_doc_testata_lock_fuori_bozza](/dbzero/vendite/funzioni/trgfn_doc_testata_lock_fuori_bozza) — il lock di testata: fuori bozza la versione congelata non si cambia

La trigger function **`vendite.trgfn_contratti_freeze_listino_versione()`** gestisce due responsabilità al momento dell'attivazione di un contratto (DRAFT→ATTIVO):

1. **Freeze versione listino**: fissa `listino_versione_id` sulla versione attiva al momento dell'attivazione.
2. **Guard negoziato puro**: impedisce l'attivazione di contratti senza listino che non hanno righe AGGIUNTA con prezzo.

---

### 🎯 Scopo Principale

Il modello unificato prevede che un contratto ATTIVO abbia una versione listino **fissa e immutabile**: dal momento dell'attivazione il resolver prezzi legge sempre quella versione, anche se il listino ha versioni successive. Questo garantisce stabilità del pricing per tutta la durata del contratto.

---

### Logica

Attiva solo sulla transizione DRAFT→ATTIVO (verifica via `codice_interno` dei due stati). Su qualsiasi altra transizione ritorna senza effetti.

| Scenario | Condizione | Comportamento |
| --- | --- | --- |
| **Negoziato puro** | `listino_id IS NULL` | Verifica presenza almeno una riga AGGIUNTA con `prezzo_unitario IS NOT NULL` e `attivo = TRUE`. Se assente: raise `E_CONTRATTO_NEGOZIATO_PURO_SENZA_RIGHE`. |
| **Con listino, senza versione** | `listino_id IS NOT NULL` + `listino_versione_id IS NULL` | Cerca versione con `validita @> CURRENT_DATE AND attivo = TRUE`. Se trovata: imposta `NEW.listino_versione_id`. Se non trovata: attivazione consentita, versione resta NULL (§4.4). |
| **Con listino, versione già fissata** | `listino_versione_id IS NOT NULL` | Nessuna azione. |

---

### Applicazione

Trigger creato dalla migration `20260515-13`:

* **`trg_contratti_a10_freeze_listino_versione_upd`** su `vendite.contratti`
* Timing: **BEFORE UPDATE OF `stato_doc_contratto_id`**
* Fase: **_a10_**
* Scope: **FOR EACH ROW**

Ordine lessicografico: `freeze` < `guard_transizione_stato` → questo trigger scatta **prima** del guard di transizione stato. Se raise, il guard non esegue.

---

### Codice errore sollevato

**`E_CONTRATTO_NEGOZIATO_PURO_SENZA_RIGHE`** (id 451) — `config.messaggi_errore`.

HTTP mapping (BE): `422 Unprocessable Entity`.

---

### Nota §4.4 — Listino senza versione attiva

Se il listino esiste ma non ha versioni con `validita @> CURRENT_DATE AND attivo = TRUE`, l'attivazione è consentita con `listino_versione_id = NULL`. La UI dovrà mostrare un warning ("listino senza versione attiva"). Il resolver prezzi in questo caso seguirà il comportamento di fallback (nessuna riga listino trovata).

---

### Relazione con altri trigger

| Trigger | Ordine | Cosa fa |
| --- | --- | --- |
| **Questo trigger** (`freeze_listino_versione`) | 1° (lex.) | Freeze versione + guard negoziato puro |
| `guard_transizione_stato` | 2° (lex.) | Valida matrice transizioni + check componenti PENDING |
| `a05_lock_fuori_bozza` (BB di testata) | prima (`a05`) | Fuori bozza blocca listino, versione e variazioni (dal 2026-10-10; ha ritirato `lock_post_attivazione`) |

<!-- rev-2026-09-28-liste-righe -->
### 🔄 rev 2026-09-28 — brief-db-liste-righe-documento

La versione del listino in vigore da fissare all'attivazione non è più scelta qui: la dice [vendite.fn_listino_versione_in_vigore](/dbzero/vendite/funzioni/fn_listino_versione_in_vigore) (`20260928-38`). Per ogni data la versione in vigore è **al più una**, per costruzione (nessuna sovrapposizione fra versioni ATTIVE e CHIUSE, date di una CHIUSA bloccate), quindi «la prima» e «tutte le valide» sono la stessa cosa. Stesso esito, provato sui dati di dev.

---

{% include-markdown "signature-core.md" %}

---
