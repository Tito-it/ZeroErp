## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_ordini_guard_transizione()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> [vendite.ordini](/dbzero/vendite/tabelle/ordini)
> [vendite.ordini_righe](/dbzero/vendite/tabelle/ordini_righe)
> [config.stati_doc_ordini](/dbzero/config/tabelle/stati_doc_ordini)
> [config.transizioni_stati_ordini](/dbzero/config/tabelle/transizioni_stati_ordini)
> [config.messaggi_errore](/dbzero/config/tabelle/messaggi_errore)
>
Approfondimento funzioni:
> [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)
> [script.fn_available_actions_ordine](/dbzero/script/funzioni/fn_available_actions_ordine)
> [`script.fn_check_prezzi_autorizzati`](/dbzero/script/funzioni/fn_check_prezzi_autorizzati) — i prezzi non autorizzati, Regola 5 (dal 2026-09-24)
>
Pattern correlato (domini gemelli):
> [vendite.trgfn_contratti_guard_transizione_stato](/dbzero/vendite/funzioni/trgfn_contratti_guard_transizione_stato)
> [vendite.trgfn_offerte_commerciali_guard_transizione](/dbzero/vendite/funzioni/trgfn_offerte_commerciali_guard_transizione)
> `vendite.trgfn_ordini_guard_transizione_approvazione` — **ritirata** (DROP `20260512-28`)

### 🎯 Scopo Principale

(rev 2026-09-24 — Regola 5, il prezzo non autorizzato; rev 2026-06-05)

La trigger function **`vendite.trgfn_ordini_guard_transizione()`** è
l'**enforcement DB-first del grafo transizioni** dell'ordine di vendita. È applicata dal
trigger `trg_ordini_a10_guard_transizione_upd` (fase `_a10_`,
`BEFORE UPDATE OF stato_doc_ordine_id`).

A differenza dei guard gemelli (`trgfn_contratti_guard_transizione_stato`,
`trgfn_offerte_commerciali_guard_transizione`), che **codificano il grafo dentro il
trigger**, questa funzione **legge la matrice** `config.transizioni_stati_ordini`: una
sola fonte verità condivisa con il lato lettura `fn_available_actions_ordine`. Intercetta
**ogni chiamante** (non solo `ordini_service.conferma()`), garantendo che nessun UPDATE
diretto possa forzare una transizione illegale.

---

### Regole applicate

| # | Regola | Errore |
|---|--------|--------|
| 1 | La coppia `(stato_da, stato_a)` deve esistere in `config.transizioni_stati_ordini` con `attivo=true` | `E_ORDINE_TRANSIZIONE_NON_AMMESSA` |
| 2 | Precondizione `DRAFT → CONFERMATO`: l'ordine deve avere **almeno una riga** | `E_ORDINE_CONFERMA_SENZA_RIGHE` |
| 3 | Verso `ANNULLATO`: i motivi di `script.fn_check_ordine_annullabile` (rev 2026-08-04) | primo motivo |
| 4 | Verso `CONFERMATO`: i motivi di `script.fn_check_ordine_confermabile` — l'aliquota sulle righe che portano un prezzo (rev 2026-08-29) | primo motivo |
| 5 | **Solo `DRAFT → CONFERMATO`**: nessun componente BoM attivo con il prezzo in attesa o rifiutato — [`script.fn_check_prezzi_autorizzati`](/dbzero/script/funzioni/fn_check_prezzi_autorizzati) (rev 2026-09-24) | `E_DOC_PREZZO_PENDENTE` / `E_DOC_PREZZO_RIFIUTATO` |

La **regola 2** è stata spostata da `ordini_service.py` (ex `E_ORD_NESSUNA_RIGA` inline)
per coerenza DB-first: vale per ogni chiamante, non solo per `conferma()`.

### Matrice transizioni (letta da `config.transizioni_stati_ordini`)

| Da | A | Ammessa | Condizione aggiuntiva |
|----|---|:-------:|-----------------------|
| DRAFT | CONFERMATO | sì | ≥1 riga ordine (regola 2) |
| DRAFT | ANNULLATO | sì | — |
| CONFERMATO | ANNULLATO | **no** | riga in matrice ma `attivo=false` |
| (qualsiasi) | (stesso stato) | sì | no-op (filtrato all'inizio della funzione) |
| CONFERMATO → ALLOCATO/SPEDITO/... | **no** | stati a valle fuori matrice (nessun driver) |

```text
DRAFT ──conferma──> CONFERMATO
  │
  └──annulla──> ANNULLATO
```

> Gli stati a valle (`ALLOCATO/SPEDITO/CONSEGNATO/FATTURATO`) non sono in matrice:
> oggi nessun processo li valorizza sull'ordine. Quando arriverà il modulo magazzino/DDT,
> le relative transizioni andranno aggiunte alla matrice (e questo guard le ammetterà
> automaticamente, senza modifiche al codice).

---

### Il prezzo non autorizzato: Regola 5 (rev 2026-09-24)

Regola decisa da Tid: *un prezzo che nessuno ha autorizzato non esce dalla bozza*. Un ordine
con un componente BoM **attivo** in attesa di approvazione (`PENDING`) o **rifiutato**
(`REJECTED`) non si conferma: la Regola 5 solleva il primo motivo di [`script.fn_check_prezzi_autorizzati`](/dbzero/script/funzioni/fn_check_prezzi_autorizzati). La riga d'ordine
lo stato di approvazione non lo porta, quindi contano i soli componenti.

⛔ **Solo dalla bozza.** La matrice fa rientrare l'ordine in `CONFERMATO` da `EVASO` e
`PARZIALMENTE_EVASO`, in automatico, quando l'evasione torna indietro (un DDT annullato).
Quel rientro non conferma niente di nuovo: un prezzo rimasto non autorizzato lo
bloccherebbe, e con lui l'annullamento a valle. Per questo la regola **non** sta in
`fn_check_ordine_confermabile`, che vale per ogni ingresso in `CONFERMATO`: l'aliquota
(Regola 4) protegge il riepilogo IVA, che non sa da dove si arriva, e ha un perimetro
diverso di proposito.

Gli stessi motivi spengono «Conferma» in
[`script.fn_available_actions_ordine`](/dbzero/script/funzioni/fn_available_actions_ordine),
anche lì solo dalla bozza. (changeSet `20260924-29`, brief
`brief-db-preventivi-congelamento-pricing`.)

> Storia: il vecchio guard `trgfn_ordini_guard_transizione_approvazione` (trigger
> `trg_ordini_a10_guard_transizione_approvazione_upd`, `20260512-19`/`-20`) bloccava
> `CONFERMATO` con un componente `PENDING` o senza prezzo; è stato ritirato con il DROP
> `20260512-28`. Dal ritiro al 2026-09-24 l'ordine non guardava il prezzo.

---

### Algoritmo

1. **No-op** — se `NEW.stato_doc_ordine_id IS NOT DISTINCT FROM OLD.stato_doc_ordine_id`
   → `RETURN NEW` (UPDATE su altre colonne dello stesso set).
2. **Lookup codici** — `codice_interno` di stato origine e destinazione da
   `config.stati_doc_ordini` (un'unica query con `max(CASE ...)`).
3. **Regola 1 (grafo)** — `EXISTS` su `config.transizioni_stati_ordini` con
   `stato_da_id = OLD AND stato_a_id = NEW AND attivo IS TRUE`. Se falso →
   `E_ORDINE_TRANSIZIONE_NON_AMMESSA` (con `stato_da`/`stato_a` nel contesto).
4. **Regola 2 (righe)** — se `DRAFT → CONFERMATO`: `NOT EXISTS` su `vendite.ordini_righe`
   per l'ordine → `E_ORDINE_CONFERMA_SENZA_RIGHE`.
5. `RETURN NEW`.

Gli errori sono sollevati via `script.fn_log_and_raise_error` (codici registrati in
`config.messaggi_errore`, ids 470-471; nessun `E_GENERICO`).

---

### Codici errore

| Codice | id | Quando |
|--------|----|--------|
| `E_ORDINE_TRANSIZIONE_NON_AMMESSA` | 470 | Transizione assente o `attivo=false` in matrice |
| `E_ORDINE_CONFERMA_SENZA_RIGHE` | 471 | `DRAFT → CONFERMATO` su ordine senza righe |
| `E_DOC_PREZZO_PENDENTE` | — | `DRAFT → CONFERMATO` con un componente attivo col prezzo in attesa (Regola 5, dal 2026-09-24) |
| `E_DOC_PREZZO_RIFIUTATO` | — | `DRAFT → CONFERMATO` con un componente attivo col prezzo rifiutato (Regola 5, dal 2026-09-24) |

---

### Note operative

- **Lookup via `codice_interno`** stabile rispetto al relabelling del codice
  business-visible (`codice_interno` immutabile per `script.trgfn_lock_columns`).
- **INSERT liberi**: il trigger è solo `BEFORE UPDATE OF stato_doc_ordine_id`. Un ordine
  può nascere già CONFERMATO via INSERT (es. import); il grafo vincola solo i cambi di
  stato successivi.
- **Test**: `db/pgtap/vendite/test-ordini-guard-transizione-v1.sql` (6 test: transizioni
  ammesse/negate + precondizione righe).
