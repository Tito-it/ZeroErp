## 📘 Documentazione Trigger Function – `pratiche.trgfn_flussi_autochiusura_pratica`

> 👀 **Vedi anche**
>
Funzioni / oggetti collegati:
>
> [pratiche.flussi](flussi.md)
> [pratiche.fn_check_pratica_chiudibile](fn_check_pratica_chiudibile.md)
> [pratiche.fn_pratica_flussi_aperti](fn_pratica_flussi_aperti.md)
> [pratiche.trgfn_flussi_guard_chiusura_prematura](trgfn_flussi_guard_chiusura_prematura.md)
> [pratiche.trgfn_pratiche_guard_chiusura_flussi](trgfn_pratiche_guard_chiusura_flussi.md)

---
### 🎯 Scopo Principale

**Chiusura guidata dal workflow**: la pratica non si chiude con un'azione manuale,
ma in automatico al completamento dei flussi. Al passaggio di un flusso a
`COMPLETATO`, questo trigger chiude la pratica padre (`APERTA → CHIUSA`) secondo un
**modello misto**.

---

### Trigger associato

| Trigger | Timing | Evento | Tabella |
|---|---|---|---|
| `trg_flussi_z90_autochiusura_pratica_upd` | AFTER | UPDATE OF `stato_id` | `pratiche.flussi` |

Fase `_z90_` (effetto a valle del completamento). Indipendente da
`trgfn_flussi_generazione` (genera la pratica figlia): ordine non vincolato.

---

### Regole (modello misto)

1. Scatta solo alla **transizione** di stato verso `COMPLETATO`.
2. Solo da pratica **APERTA** (SOSPESA/BOZZA/terminale non si auto-chiudono).
3. Tipo prestazione **con flusso di chiusura** (`template_flussi.chiude_pratica`):
   chiude **sse** il flusso completato e' quello.
4. Tipo prestazione **senza flusso di chiusura ma con ≥1 obbligatorio**: chiude
   **sse** [fn_check_pratica_chiudibile](fn_check_pratica_chiudibile.md) — predicato
   **D1**: nessun obbligatorio bloccante **e** nessun flusso istanziato aperto (escluso
   `NEW.id`, gia' terminale).
5. Tipo **senza obbligatori e senza flusso di chiusura**: **no-op** (nessun percorso
   di chiusura deterministico — la pratica resta APERTA).
6. La chiusura e' un `UPDATE pratiche → CHIUSA` che riusa i guard transizione/chiusura
   e il **giornale** esistenti: l'evento `STATO_CAMBIATO` e' registrato come per la
   chiusura manuale.

---

### Note operative

* La `UPDATE` chiude solo se la pratica e' ancora APERTA (sicurezza concorrenza).
* Nessuna ricorsione: l'UPDATE su `pratiche` non riscrive `flussi`.
* **Resta AFTER (eager), niente deferral (D2 scartato)**: i rami condizionali si
  modellano come **bivio-per-esito** (obbligatori-su-ramo via prerequisito esito-aware),
  cosi' il predicato template-based blocca **prima** che serva creare istanze a valle.
  Se un flusso a valle venisse creato su pratica gia' chiusa, il guard pratica-terminale
  fallisce in modo **rumoroso** (err 490): rete fail-safe che rende inutile il deferral.
* Test: `db/pgtap/pratiche/test-autochiusura-pratica.sql` (modelli A/B) e
  `test-chiusura-nessun-lavoro-pendente.sql` (bivio + D1).

---
{% include-markdown "signature-core.md" %}
