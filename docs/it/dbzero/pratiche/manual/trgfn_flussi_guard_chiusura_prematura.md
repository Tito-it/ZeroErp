## 📘 Documentazione Trigger Function – `pratiche.trgfn_flussi_guard_chiusura_prematura`

> 👀 **Vedi anche**
>
Funzioni / oggetti collegati:
>
> [pratiche.flussi](flussi.md)
> [pratiche.fn_check_pratica_chiudibile](fn_check_pratica_chiudibile.md)
> [pratiche.trgfn_flussi_autochiusura_pratica](trgfn_flussi_autochiusura_pratica.md)

---
### 🎯 Scopo Principale

Il **flusso "di chiusura"** (`template_flussi.chiude_pratica`) e' lo step che chiude la
pratica: non puo' essere completato finche' la pratica **non e' chiudibile**. Coerente
col guard di chiusura della pratica; evita che l'auto-chiusura conseguente fallisca (e
quindi un rollback della transazione di completamento).

---

### Trigger associato

| Trigger | Timing | Evento | Tabella |
|---|---|---|---|
| `trg_flussi_a10_guard_chiusura_prematura_upd` | BEFORE | UPDATE OF `stato_id` | `pratiche.flussi` |

Fase `_a10_` (guard). Convive con gli altri guard `_a10_` del flusso
(`esito_completato`, `pratica_terminale`, `transizione`).

---

### Regole

1. Scatta solo alla **transizione** di stato verso `COMPLETATO`.
2. Solo se il template del flusso ha `chiude_pratica = true`.
3. Ammette il completamento **sse** [fn_check_pratica_chiudibile](fn_check_pratica_chiudibile.md)
   **escludendo il flusso di chiusura stesso** — il suo **template** dai bloccanti
   (clausola a) e la sua **istanza** (`NEW.id`) dai flussi aperti (clausola b, D1): il
   flusso, ancora `IN_CORSO` in `BEFORE`, non deve contare né bloccare sé stesso. Se
   `false` → errore parlante.

---

### ⚠️ Errori sollevati

| Codice errore | Condizione |
|---------------|------------|
| `PRATICHE_CHIUSURA_FLUSSO_PREMATURO` (492) | Completamento del flusso di chiusura con altri obbligatori bloccanti o altri flussi ancora aperti |

---

### Note operative

* Il flusso di chiusura va eseguito **per ultimo**: completare (o annullare) prima gli
  altri obbligatori e chiudere i flussi aperti.
* L'esclusione per **istanza** (`p_escludi_flusso_id = NEW.id`) e' ciò che consente al
  flusso di chiusura di completarsi senza che la clausola (b) di D1 lo veda come "flusso
  aperto": senza di essa il completamento fallirebbe sempre.
* Test: `db/pgtap/pratiche/test-autochiusura-pratica.sql` (modello B).
