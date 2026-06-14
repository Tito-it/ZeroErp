## 📘 Documentazione Trigger Function – `pratiche.trgfn_flussi_autochiusura_pratica`

> 👀 **Vedi anche**
>
Funzioni / oggetti collegati:
>
> [pratiche.flussi](flussi.md)
> [pratiche.fn_check_pratica_chiudibile](fn_check_pratica_chiudibile.md)
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
   **sse** [fn_check_pratica_chiudibile](fn_check_pratica_chiudibile.md) (nessun
   obbligatorio bloccante).
5. Tipo **senza obbligatori e senza flusso di chiusura**: **no-op** (nessun percorso
   di chiusura deterministico — la pratica resta APERTA).
6. La chiusura e' un `UPDATE pratiche → CHIUSA` che riusa i guard transizione/chiusura
   e il **giornale** esistenti: l'evento `STATO_CAMBIATO` e' registrato come per la
   chiusura manuale.

---

### Note operative

* La `UPDATE` chiude solo se la pratica e' ancora APERTA (sicurezza concorrenza).
* Nessuna ricorsione: l'UPDATE su `pratiche` non riscrive `flussi`.
* Conseguenza del punto 5 (decisione D3): un tipo prestazione senza percorso di
  chiusura non si chiude mai in automatico; e' responsabilita' di configurazione
  prevedere obbligatori o un flusso di chiusura.
* Test: `db/pgtap/pratiche/test-autochiusura-pratica.sql` (+ regressione bivi in
  `test-bivi-condizionali.sql`).

---
{% include-markdown "signature-core.md" %}
