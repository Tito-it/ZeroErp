## 📘 Documentazione Concettuale – Trigger Function `vendite.trgfn_preventivi_guard_transizione_approvazione()`

> 👀 **Vedi anche**
>
> Tabelle correlate:
>
> [vendite.preventivi](/dbzero/vendite/tabelle/preventivi) — tabella guardata
> [vendite.preventivi_righe](/dbzero/vendite/tabelle/preventivi_righe) — fonte del check EXISTS (colonna `stato_approvazione_prezzo`)
> [config.stati_doc_preventivi](/dbzero/config/tabelle/stati_doc_preventivi) — lookup `codice_interno='ACCETTATO'`
>
> Funzioni correlate:
>
> [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)
> [vendite.trgfn_preventivi_righe_guard_pending](/dbzero/vendite/funzioni/trgfn_preventivi_righe_guard_pending) — guard complementare lato riga
>
> Guide:
>
> [Sviluppo Listini v5 §14.6](/dev/work-in-progress/sviluppo-listini-v5) — workflow L3 approvazione out-of-policy

La trigger function **`vendite.trgfn_preventivi_guard_transizione_approvazione()`** blinda la finalizzazione commerciale del preventivo: **impedisce la transizione allo stato `ACCETTATO` se esistono righe con `stato_approvazione_prezzo = 'PENDING'`**, ovvero richieste L3 di override prezzo ancora in attesa di esito.

---

### 🎯 Scopo Principale

(latest revision 22-04-2026, Sprint E listini v5 §14.6)

- **Garanzia di coerenza commerciale** — un preventivo ACCETTATO e' un impegno vincolante: non puo' essere finalizzato mentre ci sono prezzi "proposti ma non approvati". Il workflow L3 deve esitare (APPROVED o REJECTED) o essere annullato (clear a NULL) prima della accettazione.
- **Point-of-no-return** — l'accettazione apre la pipeline commerciale (ordini, fatturazione, commesse). Richieste pendenti su prezzi sarebbero ambigue downstream.
- **Separation of concerns con DB-E-5** — questo trigger presidia il livello preventivo (transizione di stato). Il trigger sorella [`trgfn_preventivi_righe_guard_pending`](/dbzero/vendite/funzioni/trgfn_preventivi_righe_guard_pending) presidia il livello riga (frozen durante PENDING). Insieme garantiscono l'invariante "nessun ACCETTATO con pricing ancora da decidere".

---

### Logica

1. Risolve il `codice_interno` dello stato target (`NEW.stato_doc_preventivo_id`) via lookup su `config.stati_doc_preventivi`.
2. **Early return** se il nuovo stato e' diverso da `'ACCETTATO'` — il guard ha scopo limitato alla transizione finale. Transizioni a `DRAFT`, `EMESSO`, `RIFIUTATO`, `SCADUTO`, `ANNULLATO` non hanno vincoli su workflow approvazione.
3. Se nuovo stato e' `ACCETTATO`: controlla `EXISTS` righe in `preventivi_righe` con `preventivo_id = NEW.id` e `stato_approvazione_prezzo = 'PENDING'`. Se esistono, raise.

Context payload JSONB:

- `preventivo_id` — l'id del preventivo che sta tentando la transizione
- `hint` — suggerimento UX (attendi esito / rifiuta richiesta)

Il messaggio include il `preventivo_id` formattato via `%s` dal CSV `messaggi_errore`.

---

### Perche' `codice_interno` invece di `codice`

Il lookup usa la colonna `config.stati_doc_preventivi.codice_interno` (valore `'ACCETTATO'`), non `codice`. Motivazione:

- `codice_interno` e' **stabile per dominio**: riflette il significato business del record e cambia solo con refactor architetturale esplicito.
- `codice` e' potenzialmente **visibile/ritraduceable** (UX, localizzazione) e piu' soggetto a relabelling.

Questa scelta e' la regola di progetto "sempre codice_interno quando esiste" (memoria feedback DB).

---

### Applicazione

Trigger creato dalla migration `20260422-06-02`:

- **`trg_preventivi_a10_guard_transizione_approvazione_upd`** su `vendite.preventivi`

Specifiche:

- Timing: **BEFORE UPDATE OF stato_doc_preventivo_id**
- Fase: **_a10_** (guard/block)
- Scope: **FOR EACH ROW**

`UPDATE OF stato_doc_preventivo_id` scatta il trigger **solo quando quella colonna e' esplicitamente nel SET** dell'UPDATE, evitando overhead su UPDATE di altre colonne (totali, meta, righe associate).

---

### Codice errore sollevato

**`E_PREVENTIVO_RIGHE_PRICING_PENDENTI`** (id 389) — `config.messaggi_errore` CSV. Seminato in `20260422` con il trigger.

Messaggio: `"Preventivo <id>: impossibile transire ad ACCETTATO, esistono righe con prezzo in attesa di approvazione."`.

Causa (CSV): Il workflow approvazione prezzo out-of-policy richiede che tutte le richieste L3 siano esitate prima della finalizzazione.

Soluzione suggerita (CSV): attendere l'esito dell'approvazione pendente (dashboard approvazioni) oppure rifiutare la richiesta.

---

### Quando NON scatta

- **UPDATE di altre colonne**: `UPDATE OF stato_doc_preventivo_id` isola il trigger alle transizioni di stato. Modifiche a `totale_documento`, `meta`, `validita_dal`, ecc. non innescano il guard.
- **Transizione a stato != ACCETTATO**: early return silenzioso. Es. passaggio `DRAFT → EMESSO` con righe PENDING e' ammesso (il commerciale pre-consegna puo' avvenire, ma il deal non e' ancora chiuso).
- **Nessuna riga PENDING**: se tutte le righe sono APPROVED, REJECTED o NULL, la transizione ad ACCETTATO procede.
- **ID stato inesistente**: `v_stato_codice IS NULL` → confronto `IS DISTINCT FROM 'ACCETTATO'` vero → early return. Fail-soft: un id errato non blocca ma neanche sovrascrive la semantica — e' un caso che la FK normalmente impedisce.
- **DELETE / INSERT**: scope `BEFORE UPDATE OF`, non scatta.

---

### Note implementative

- `LANGUAGE plpgsql` — necessario per la SELECT INTO + condizionale.
- **STABLE non dichiarato**: e' una trigger function, la volatilita' non e' dichiarabile.
- Variabile locale `v_stato_codice` tipata via `%TYPE` su `config.stati_doc_preventivi.codice_interno` per resilienza a cambio tipo colonna.
- Passaggio `NEW.id::text` come valore variadic per placeholder `%s` del messaggio errore.
